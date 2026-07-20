import os
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response, Depends

import jwt

from auth_utils import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, serialize_user, get_current_user,
    get_optional_user, JWT_ALGORITHM, set_csrf_cookie, clear_csrf_cookie,
)
from db import get_db, is_db_down, db_down_reason
from models import RegisterIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, ChangePasswordIn
from plans_catalogue import get_plan
from rate_limit import limiter, AUTH_RATE
from services.admin_audit import log_event as _audit, write_security_event as _sec_event, request_meta as _req_meta
from services.token_service import (
    store_refresh_jti, is_jti_revoked, revoke_jti, revoke_all_user_tokens,
    get_refresh_record, list_active_sessions, revoke_session,
)
from services.ua_parser import parse_user_agent
from services.security_event_service import emit_security_event as _emit_sec
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.auth")

_PROTECTED_ADMIN_EMAIL  = "admin@synaptiq.academy"
_MFA_PENDING_TTL_MINUTES = 5

# AUTH-BUG-003: fail-fast message shown when the circuit breaker (db.py) already
# knows Mongo is unreachable — avoids making the user wait out the full 10-30s
# connection timeout just to get the same answer everyone else in this window
# would get. Internal diagnostics (Atlas IP allowlist, DNS, etc.) go to the
# server log via db_down_reason(); this string is the only thing the client sees.
_AUTH_SERVICE_UNAVAILABLE = "Authentication service is temporarily unavailable. Please try again in a moment."


def _raise_if_db_down() -> None:
    if is_db_down():
        logger.warning("Auth request rejected fast — circuit breaker open: %s", db_down_reason())
        raise HTTPException(status_code=503, detail=_AUTH_SERVICE_UNAVAILABLE)


def _make_mfa_pending_token(user_id: str, remember: bool = True) -> str:
    """Short-lived token proving password was verified; MFA still required.

    Carries the "remember me" choice from the original /auth/login call
    through to /auth/mfa-verify, which is a separate request with no
    knowledge of the original form state otherwise.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub":      user_id,
        "type":     "mfa_pending",
        "remember": bool(remember),
        "iat":      int(now.timestamp()),
        "exp":      now + timedelta(minutes=_MFA_PENDING_TTL_MINUTES),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def _decode_mfa_pending(token: str) -> Optional[dict]:
    """Returns {"user_id": ..., "remember": ...} from MFA-pending token, or None."""
    try:
        p = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if p.get("type") != "mfa_pending":
            return None
        return {"user_id": p["sub"], "remember": p.get("remember", True)}
    except Exception:
        return None

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Disposable / temporary email domain blocklist
_DISPOSABLE_DOMAINS: frozenset = frozenset({
    "mailinator.com", "guerrillamail.com", "guerrillamail.net", "guerrillamail.org",
    "guerrillamail.de", "guerrillamail.biz", "guerrillamail.info",
    "tempmail.com", "temp-mail.org", "10minutemail.com", "10minutemail.net",
    "10minutemail.org", "10minutemail.de", "10minemail.com", "yopmail.com",
    "yopmail.fr", "yopmail.net", "trashmail.com", "trashmail.me", "trashmail.at",
    "trashmail.io", "trashmail.net", "dispostable.com", "disposablemail.com",
    "throwam.com", "throwam.net", "getnada.com", "mailnull.com", "maildrop.cc",
    "sharklasers.com", "guerrillamailblock.com", "spam4.me", "notmailinator.com",
    "trashmail.de", "mailnesia.com", "discard.email", "fakeinbox.com",
    "mailforspam.com", "spamgourmet.com", "spamgourmet.net", "spamgourmet.org",
    "mytemp.email", "tempinbox.com", "tempinbox.co.uk", "throwaway.email",
    "wegwerfmail.de", "nwytg.net", "mintemail.com", "mailtemp.info",
    "mailtemp.net", "1secmail.com", "1secmail.org", "1secmail.net",
    "mohmal.com", "harakirimail.com", "spambog.com", "spam.la",
    "deadaddress.com", "despam.it", "moncourrier.fr.nf", "monemail.fr.nf",
    "monmail.fr.nf", "filzmail.com", "sendspamhere.com", "jourrapide.com",
    "armyspy.com", "cuvox.de", "dayrep.com", "einrot.com", "fleckens.hu",
    "gustr.com", "rhyta.com", "superrito.com", "teleworm.us", "zetmail.com",
})


def _is_disposable_email(email: str) -> bool:
    domain = email.split("@")[-1].lower() if "@" in email else ""
    return domain in _DISPOSABLE_DOMAINS

RESET_TOKEN_TTL_MIN = 30
VERIFICATION_TTL_HOURS = int(os.environ.get("EMAIL_VERIFICATION_TTL_HOURS", "24"))

# Lockout thresholds (AUTH-006)
LOCKOUT_THRESHOLD_SOFT = 5   # → 15 minutes
LOCKOUT_THRESHOLD_HARD = 10  # → 24 hours
LOCKOUT_SOFT_MINUTES = 15
LOCKOUT_HARD_HOURS = 24


def _is_prod() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


def _expose_reset_token() -> bool:
    if _is_prod():
        return False
    return os.environ.get("EXPOSE_RESET_TOKEN", "0") == "1"


def _validate_password(pw: str) -> None:
    if len(pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise HTTPException(status_code=400, detail="Password must contain at least one letter and one digit")


def _now():
    return datetime.now(timezone.utc)


def _email_verification_required() -> bool:
    return os.environ.get("EMAIL_VERIFICATION_REQUIRED", "0") == "1"


# ─── Account lockout helpers (AUTH-006) ──────────────────────────────────────

async def _check_lockout(user: dict) -> None:
    locked_until = user.get("locked_until")
    if not locked_until:
        return
    if isinstance(locked_until, str):
        locked_until = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if _now() < locked_until:
        remaining = int((locked_until - _now()).total_seconds() / 60)
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked due to too many failed login attempts. "
                   f"Try again in {remaining} minute(s).",
        )


async def _record_failed_login(db, user_id, ip: str) -> None:
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return
    count = (user.get("failed_login_count") or 0) + 1
    update: dict = {
        "failed_login_count": count,
        "last_failed_login": _now().isoformat(),
    }
    if count >= LOCKOUT_THRESHOLD_HARD:
        locked_until = _now() + timedelta(hours=LOCKOUT_HARD_HOURS)
        update["locked_until"] = locked_until.isoformat()
        logger.warning("Account %s hard-locked (24h) after %d failures from %s", user_id, count, ip)
    elif count >= LOCKOUT_THRESHOLD_SOFT:
        locked_until = _now() + timedelta(minutes=LOCKOUT_SOFT_MINUTES)
        update["locked_until"] = locked_until.isoformat()
        logger.warning("Account %s soft-locked (15m) after %d failures from %s", user_id, count, ip)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update})


async def _record_successful_login(db, user_id) -> None:
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "failed_login_count": 0,
            "locked_until": None,
            "last_successful_login": _now().isoformat(),
        }},
    )


# ─── Token creation helpers ───────────────────────────────────────────────────

async def _issue_tokens_and_cookies(
    response: Response, uid: str, email: str,
    request: Request = None, session_id: str = None, remember: bool = True,
) -> tuple[str, str]:
    """Issue access + refresh tokens, store jti (+ session_id for Active Sessions),
    set all cookies. Returns (access, refresh)."""
    access = create_access_token(uid, email)
    refresh, jti = create_refresh_token(uid)
    meta = _req_meta(request) if request else {"ip": None, "user_agent": None}
    await store_refresh_jti(jti, uid, session_id=session_id, ip=meta["ip"], user_agent=meta["user_agent"])
    set_auth_cookies(response, access, refresh, remember=remember)
    set_csrf_cookie(response)
    return access, refresh


# ─── Email verification helpers ───────────────────────────────────────────────

def _make_verification_token(user_id: str) -> tuple[str, str]:
    """Returns (encoded_token, jti)."""
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "email_verification",
        "exp": _now() + timedelta(hours=VERIFICATION_TTL_HOURS),
    }
    token = jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)
    return token, jti


# ─── Password reset helpers ───────────────────────────────────────────────────

def _make_reset_token(user_id: str) -> tuple[str, str]:
    """Returns (encoded_token, jti)."""
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "password_reset",
        "exp": _now() + timedelta(minutes=RESET_TOKEN_TTL_MIN),
    }
    token = jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)
    return token, jti


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/register")
@limiter.limit(AUTH_RATE)
async def register(request: Request, payload: RegisterIn, response: Response):
    _raise_if_db_down()
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    email = payload.email.lower().strip()
    logger.info("[STEP 4] register() called for %s", email)
    _validate_password(payload.password)
    if _is_disposable_email(email):
        raise HTTPException(
            status_code=400,
            detail="Temporary and disposable email addresses are not accepted. Please use a permanent institutional or personal email address."
        )
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    ref_code = (payload.model_dump().get("referral_code") if hasattr(payload, "model_dump") else None)
    if not ref_code:
        ref_code = request.query_params.get("ref")
    parts = payload.full_name.strip().split(" ", 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    user_doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "full_name": payload.full_name,
        "first_name": first_name,
        "last_name": last_name,
        "role": "user",
        "institution": "", "department": "", "country": "", "academic_role": "",
        "biography": "",
        "orcid": "", "google_scholar": "", "researchgate": "", "scopus_id": "",
        "linkedin": "", "website": "",
        "research_areas": [], "research_interests": [], "research_keywords": [],
        "skills": [], "can_contribute": [], "looking_for": [],
        "availability": "Available", "avatar_url": "",
        "h_index": 0, "publications_count": 0, "conferences_count": 0,
        "collaboration_score": 50, "publication_score": 0,
        "expertise_score": 50, "community_score": 50,
        "connections": [],
        "user_type": None,
        "primary_domain": None,
        "teaching_areas": [],
        "professional_expertise": [],
        "onboarded": False,
        "plan_code": "free",
        "credits_balance": get_plan("free")["credits_per_month"],
        "credits_monthly_allowance": get_plan("free")["credits_per_month"],
        "credits_reset_at": (_now() + timedelta(days=30)).isoformat(),
        "email_verified": False, "email_verified_at": None,
        "welcome_email_sent": False,
        "failed_login_count": 0, "locked_until": None,
        "last_failed_login": None, "last_successful_login": None,
        "created_at": _now().isoformat(),
    }
    result = await db.users.insert_one(user_doc)
    uid = str(result.inserted_id)
    logger.info("[STEP 5] user inserted uid=%s", uid)
    meta = _req_meta(request)
    await _audit("auth.register", actor_id=uid, actor_email=email, ip=meta["ip"], user_agent=meta["user_agent"])
    try:
        from services.realtime import manager
        await manager.broadcast_admin({"type": "user_registered", "user_id": uid, "email": email})
    except Exception:
        pass
    try:
        from services.referrals import attribute_signup
        await attribute_signup(referee_id=uid, code=ref_code)
    except Exception:
        logger.exception("Referral attribution failed (non-fatal)")
    token, jti = _make_verification_token(uid)
    await db.email_verifications.insert_one({
        "user_id": uid, "jti": jti, "used": False,
        "created_at": _now(),
        "expires_at": _now() + timedelta(hours=VERIFICATION_TTL_HOURS),
    })

    # Emails must never block registration: queue the send instead of awaiting
    # Resend inline (previously up to ~30s worst case — 3 retries x 10s timeout).
    from worker import enqueue_job, Job
    email_queued = True
    try:
        logger.info("[STEP 6] queuing verification email to %s (user=%s)", email, uid)
        await enqueue_job(Job(
            job_type="email.send",
            payload={"kind": "verification", "args": {
                "user_id": uid, "token": token, "expires_in_hours": VERIFICATION_TTL_HOURS,
            }},
            user_id=uid,
        ), db)
    except Exception:
        logger.exception("[register] Failed to queue verification email for user %s", uid)
        email_queued = False

    # Welcome email — send exactly once. The atomic check-and-set below only
    # succeeds for the first request that reaches it, so a client retry (or
    # any future duplicate call) can never queue a second welcome email.
    try:
        welcome_flip = await db.users.update_one(
            {"_id": result.inserted_id, "welcome_email_sent": {"$ne": True}},
            {"$set": {"welcome_email_sent": True}},
        )
        if welcome_flip.modified_count == 1:
            await enqueue_job(Job(
                job_type="email.send",
                payload={"kind": "welcome", "args": {"user_id": uid}},
                user_id=uid,
            ), db)
    except Exception:
        logger.exception("[register] Failed to queue welcome email for user %s", uid)

    # Getting Started — scheduled once, 24h out. The handler re-checks
    # eligibility against real, current data at run time (not here), so it
    # never fires for a user who has since become active.
    try:
        from worker import get_scheduler
        sched = get_scheduler()
        if sched:
            await sched.add_once(
                job_type="email.getting_started_check",
                payload={"user_id": uid},
                run_at=_now() + timedelta(hours=24),
                schedule_id=f"getting_started:{uid}",
            )
    except Exception:
        logger.exception("[register] Failed to schedule getting-started email for user %s", uid)

    if not _email_verification_required():
        await _issue_tokens_and_cookies(response, uid, email, request=request)
    user_doc["_id"] = result.inserted_id
    out = serialize_user(user_doc)
    out["verification_email_sent"] = email_queued
    out["email_send_mode"] = "queued" if email_queued else "queue_failed"
    if _expose_reset_token():
        out["debug_verification_token"] = token
    return out


@router.post("/login")
@limiter.limit(AUTH_RATE)
async def login(request: Request, payload: LoginIn, response: Response):
    _raise_if_db_down()
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    email = payload.email.lower().strip()
    meta  = _req_meta(request)
    user  = await db.users.find_one({"email": email})

    # Check lockout BEFORE password verification so brute-force protection
    # applies even when the attacker keeps guessing wrong passwords.
    if user:
        await _check_lockout(user)

    if not user or not verify_password(payload.password, user.get("password_hash") or ""):
        if user:
            await _record_failed_login(db, str(user["_id"]), meta["ip"])
        await _sec_event("login_failed", ip=meta["ip"], user_agent=meta["user_agent"], extra={"email": email})
        await _emit_sec("login_failed", ip=meta["ip"], user_agent=meta["user_agent"], extra={"email": email})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended. Please contact support.")
    if user.get("status") == "banned":
        raise HTTPException(status_code=403, detail="Account has been banned.")
    if _email_verification_required() and not user.get("email_verified"):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address before signing in. Check your inbox or request a new link.",
        )

    uid = str(user["_id"])

    # ── MFA gate ─────────────────────────────────────────────────────────────
    # If this account has MFA enabled, issue a short-lived pending token and
    # return {mfa_required: true} instead of full auth cookies.
    if user.get("mfa_enabled"):
        mfa_token = _make_mfa_pending_token(uid, remember=payload.remember)
        await _audit("auth.mfa_challenge_issued", actor_id=uid, actor_email=email,
                     ip=meta["ip"], user_agent=meta["user_agent"])
        return {
            "mfa_required":  True,
            "mfa_token":     mfa_token,
            "expires_in_seconds": _MFA_PENDING_TTL_MINUTES * 60,
        }

    # ── No MFA — issue full auth cookies ─────────────────────────────────────
    await _record_successful_login(db, uid)
    await _issue_tokens_and_cookies(response, uid, email, request=request, remember=payload.remember)
    await _audit("auth.login", actor_id=uid, actor_email=email, ip=meta["ip"], user_agent=meta["user_agent"])

    # Run risk assessment asynchronously (non-blocking)
    try:
        from services.device_service import build_fingerprint, is_trusted_device
        from services.risk_engine import assess_login_risk, geolocate, update_user_geo_state
        fp  = build_fingerprint(request)
        geo = await geolocate(meta["ip"])
        trusted = await is_trusted_device(uid, fp)
        risk = await assess_login_risk(user, meta["ip"], trusted, geo)
        if risk["factors"]:
            await _emit_sec(
                "suspicious_activity" if risk["score"] >= 60 else "login_new_device",
                actor_id=uid, actor_email=email,
                ip=meta["ip"], user_agent=meta["user_agent"],
                extra={"risk": risk},
            )
        await update_user_geo_state(uid, geo)
    except Exception:
        pass

    return serialize_user(user)


@router.post("/mfa-verify")
@limiter.limit(AUTH_RATE)
async def mfa_verify(
    request: Request,
    response: Response,
    mfa_token: str,
    code: str,
    trust_device: bool = False,
):
    """Complete the MFA challenge after a successful password authentication."""

    meta    = _req_meta(request)
    pending = _decode_mfa_pending(mfa_token)
    if not pending:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA session. Please log in again.")
    user_id  = pending["user_id"]
    remember = pending["remember"]

    from services.mfa_service import verify_mfa_code
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    ok, method = await verify_mfa_code(user_id, code)
    if not ok:
        await _record_failed_login(db, user_id, meta["ip"])
        await _emit_sec("mfa_failed", actor_id=user_id, actor_email=user.get("email"),
                        ip=meta["ip"], user_agent=meta["user_agent"])
        raise HTTPException(status_code=401, detail="Invalid authentication code")

    email = user.get("email", "")
    await _record_successful_login(db, user_id)
    await _issue_tokens_and_cookies(response, user_id, email, request=request, remember=remember)
    await _audit("auth.mfa_verified", actor_id=user_id, actor_email=email,
                 ip=meta["ip"], user_agent=meta["user_agent"],
                 extra={"method": method})
    await _emit_sec("login_new_device" if method == "totp" else "mfa_recovery_used",
                    severity="low" if method == "totp" else "high",
                    actor_id=user_id, actor_email=email,
                    ip=meta["ip"], user_agent=meta["user_agent"])

    # Optionally trust this device so future logins skip MFA challenge
    device_id = None
    if trust_device:
        try:
            from services.device_service import build_fingerprint, trust_device as _trust
            from services.risk_engine import geolocate
            fp  = build_fingerprint(request)
            geo = await geolocate(meta["ip"])
            device_id = await _trust(user_id, fp, request,
                                     country=geo.get("countryCode"),
                                     city=geo.get("city"))
        except Exception:
            pass

    result = serialize_user(user)
    result["mfa_method"] = method
    if device_id:
        result["device_trusted"] = True
    return result


@router.post("/logout")
async def logout(request: Request, response: Response, _user: Optional[dict] = Depends(get_optional_user)):
    if _user:
        meta = _req_meta(request)
        await _audit("auth.logout", actor_id=_user.get("id"), actor_email=_user.get("email"),
                     ip=meta["ip"], user_agent=meta["user_agent"])
    # Revoke the refresh token jti if present (AUTH-005)
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM],
                                 options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                await revoke_jti(jti)
        except Exception:
            pass
    clear_auth_cookies(response)
    clear_csrf_cookie(response)
    return {"ok": True}


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload["sub"]
        old_jti = payload.get("jti")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired — please sign in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # AUTH-005: Check server-side revocation
    if old_jti and await is_jti_revoked(old_jti):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # AUTH-005: Revoke old JTI and issue fresh pair (rotation) — carry the same
    # session_id forward so this remains "the same session" in Active Sessions.
    old_record = await get_refresh_record(old_jti) if old_jti else None
    session_id = old_record.get("session_id") if old_record else None
    if old_jti:
        await revoke_jti(old_jti)

    uid = str(user["_id"])
    email = user.get("email") or ""
    await _issue_tokens_and_cookies(response, uid, email, request=request, session_id=session_id)
    return serialize_user(user)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.get("/csrf-token")
async def get_csrf_token(response: Response):
    """Endpoint for the frontend to obtain a CSRF token before making state-changing requests."""
    token = set_csrf_cookie(response)
    return {"csrf_token": token}


# ══ EMAIL VERIFICATION ═══════════════════════════════════════════════════════

@router.post("/verify-email")
@limiter.limit(AUTH_RATE)
async def verify_email(request: Request, payload: dict):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    token = (payload or {}).get("token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
    try:
        data = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if data.get("type") != "email_verification":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = data["sub"]
        jti = data.get("jti")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Verification link has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    # Lookup by proper UUID JTI (AUTH-009)
    query = {"user_id": user_id}
    if jti:
        query["jti"] = jti
    else:
        # Legacy: fall back to token[-32:] for tokens issued before the upgrade
        query["jti"] = token[-32:]

    record = await db.email_verifications.find_one(query)
    if record and record.get("used"):
        u = await db.users.find_one({"_id": ObjectId(user_id)})
        if u and u.get("email_verified"):
            return {"ok": True, "already_verified": True}
        raise HTTPException(status_code=400, detail="Verification link already used")

    verified_user = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": {"email_verified": True, "email_verified_at": _now().isoformat()}},
        return_document=True,
    )
    if record:
        await db.email_verifications.update_one(
            {"_id": record["_id"]},
            {"$set": {"used": True, "used_at": _now().isoformat()}},
        )
    meta = _req_meta(request)
    await _audit(
        "auth.email_verified",
        actor_id=user_id,
        actor_email=(verified_user or {}).get("email"),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return {"ok": True, "verified": True}


@router.post("/resend-verification")
@limiter.limit(AUTH_RATE)
async def resend_verification(request: Request, payload: dict):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    email = ((payload or {}).get("email") or "").lower().strip()
    if not email:
        return {"ok": True}
    user = await db.users.find_one({"email": email})
    if not user:
        return {"ok": True}
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    uid = str(user["_id"])
    await db.email_verifications.update_many(
        {"user_id": uid, "used": False}, {"$set": {"used": True, "superseded": True}},
    )
    token, jti = _make_verification_token(uid)
    await db.email_verifications.insert_one({
        "user_id": uid, "jti": jti, "used": False,
        "created_at": _now(),
        "expires_at": _now() + timedelta(hours=VERIFICATION_TTL_HOURS),
    })
    from services.email_service import send_email_verification
    try:
        logger.info("[resend-verification] Sending to user %s", uid)
        email_result = await send_email_verification(
            user_id=uid, token=token, expires_in_hours=VERIFICATION_TTL_HOURS
        )
        logger.info("[resend-verification] Result: ok=%s mode=%s id=%s error=%s",
                    email_result.get("ok"), email_result.get("mode"),
                    email_result.get("id"), email_result.get("error"))
    except Exception:
        logger.exception("[resend-verification] Email raised for user %s", uid)
        raise HTTPException(status_code=503,
                            detail="Could not send verification email — please try again in a moment.")

    if not email_result.get("ok") and email_result.get("mode") not in ("dry_run", "unconfigured"):
        logger.error("[resend-verification] LIVE send failed for user %s: %s", uid, email_result.get("error"))
        raise HTTPException(status_code=503,
                            detail=f"Could not send verification email: {email_result.get('error', 'unknown error')}")

    out: dict = {"ok": True}
    if _expose_reset_token():
        out["debug_verification_token"] = token
    return out


# ══ PASSWORD RESET ════════════════════════════════════════════════════════════

@router.post("/forgot-password")
@limiter.limit(AUTH_RATE)
async def forgot_password(request: Request, payload: ForgotPasswordIn):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        return {"ok": True, "message": "If an account exists, a reset link has been sent."}
    token, jti = _make_reset_token(str(user["_id"]))
    await db.password_resets.insert_one({
        "user_id": str(user["_id"]),
        "jti": jti,
        "used": False,
        "created_at": _now(),
        "expires_at": _now() + timedelta(minutes=RESET_TOKEN_TTL_MIN),
    })
    from services.email_service import send_password_reset
    try:
        logger.info("[forgot-password] Sending reset email to %s", email)
        email_result = await send_password_reset(
            user_id=str(user["_id"]), token=token, expires_in_minutes=RESET_TOKEN_TTL_MIN
        )
        logger.info("[forgot-password] Result: ok=%s mode=%s id=%s error=%s",
                    email_result.get("ok"), email_result.get("mode"),
                    email_result.get("id"), email_result.get("error"))
    except Exception:
        logger.exception("[forgot-password] Reset email raised for %s", email)
        raise HTTPException(status_code=503,
                            detail="Could not send password reset email — please try again in a moment.")

    if not email_result.get("ok") and email_result.get("mode") not in ("dry_run", "unconfigured"):
        logger.error("[forgot-password] LIVE send failed for %s: %s", email, email_result.get("error"))
        raise HTTPException(status_code=503,
                            detail=f"Could not send password reset email: {email_result.get('error', 'unknown error')}")

    out = {"ok": True, "message": "If an account exists, a reset link has been sent."}
    if _expose_reset_token():
        out["debug_reset_token"] = token
    return out


@router.post("/reset-password")
@limiter.limit(AUTH_RATE)
async def reset_password(request: Request, payload: ResetPasswordIn):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        data = jwt.decode(payload.token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if data.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = data["sub"]
        jti = data.get("jti")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset link has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    _validate_password(payload.new_password)

    query = {"user_id": user_id}
    if jti:
        query["jti"] = jti
    else:
        query["jti"] = payload.token[-32:]

    record = await db.password_resets.find_one(query)
    if record and record.get("used"):
        raise HTTPException(status_code=400, detail="Reset link already used")

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    if record:
        await db.password_resets.update_one(
            {"_id": record["_id"]}, {"$set": {"used": True, "used_at": _now().isoformat()}}
        )
    # AUTH-005: Revoke all refresh tokens after password reset
    await revoke_all_user_tokens(user_id)
    reset_user = await db.users.find_one({"_id": ObjectId(user_id)}, {"email": 1})
    meta = _req_meta(request)
    await _audit(
        "auth.password_reset_completed",
        actor_id=user_id,
        actor_email=(reset_user or {}).get("email"),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return {"ok": True}


@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, request: Request, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    full_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not full_user or not verify_password(payload.current_password, full_user.get("password_hash") or ""):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    _validate_password(payload.new_password)
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    # AUTH-005: Revoke all OTHER refresh tokens (user stays logged in on current device)
    # To be conservative, revoke all and let the client re-authenticate
    await revoke_all_user_tokens(user["id"])
    meta = _req_meta(request)
    await _audit("auth.change_password", actor_id=user["id"], actor_email=user.get("email"),
                 ip=meta["ip"], user_agent=meta["user_agent"])
    await _emit_sec("password_changed", actor_id=user["id"], actor_email=user.get("email"),
                     ip=meta["ip"], user_agent=meta["user_agent"])
    return {"ok": True}


# ─── Active Sessions ───────────────────────────────────────────────────────────

@router.get("/sessions")
async def get_sessions(request: Request, user: dict = Depends(get_current_user)):
    """List this user's active (non-revoked, non-expired) sessions, one row per
    device login — token rotation carries the same session_id forward so a
    session doesn't multiply every time the access token silently refreshes."""
    current_jti = None
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
            current_jti = payload.get("jti")
        except jwt.InvalidTokenError:
            pass
    current_session_id = None
    if current_jti:
        rec = await get_refresh_record(current_jti)
        current_session_id = (rec.get("session_id") or rec.get("jti")) if rec else None

    sessions = await list_active_sessions(user["id"])
    out = []
    for s in sessions:
        ua = parse_user_agent(s.get("user_agent", ""))
        session_id = s.get("session_id") or s.get("jti")
        out.append({
            "session_id": session_id,
            "os": ua["os"],
            "browser": ua["browser"],
            "label": ua["label"],
            "is_mobile": ua["is_mobile"],
            "ip": s.get("ip"),
            "issued_at": s.get("issued_at").isoformat() if s.get("issued_at") else None,
            "last_seen_at": s.get("last_seen_at").isoformat() if s.get("last_seen_at") else None,
            "is_current": session_id == current_session_id,
        })
    return out


@router.post("/sessions/{session_id}/revoke")
async def revoke_one_session(session_id: str, user: dict = Depends(get_current_user)):
    count = await revoke_session(user["id"], session_id)
    if count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


# ─── Security Activity ─────────────────────────────────────────────────────────

_SECURITY_ACTIONS = {
    "auth.login": "Successful login",
    "auth.register": "Account created",
    "auth.logout": "Signed out",
    "auth.change_password": "Password changed",
    "auth.password_reset_completed": "Password reset",
    "auth.mfa_verified": "Two-factor authentication used",
    "auth.email_verified": "Email verified",
    "auth.mfa.enabled": "Two-factor authentication enabled",
    "auth.mfa.disabled": "Two-factor authentication disabled",
}


@router.get("/security-events")
async def get_security_events(limit: int = 20, user: dict = Depends(get_current_user)):
    """Real per-user security activity feed, read from the same audit_log
    collection every login/logout/password-change already writes to."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.audit_log.find({
        "actor_id": user["id"],
        "action": {"$in": list(_SECURITY_ACTIONS.keys())},
    }).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return [{
        "id": str(d.get("_id", "")),
        "action": d.get("action"),
        "label": _SECURITY_ACTIONS.get(d.get("action"), d.get("action")),
        "ip": d.get("ip"),
        "user_agent": parse_user_agent(d.get("user_agent", ""))["label"] if d.get("user_agent") else None,
        "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else d.get("created_at"),
    } for d in docs]
