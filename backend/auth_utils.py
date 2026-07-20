import os
import secrets
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from bson import ObjectId
from cachetools import TTLCache
from fastapi import HTTPException, Request

from db import get_db
from repo.shim import make_db_proxy

# ─────────────────── Per-request auth cache ──────────────────────────────────
# Caches the raw MongoDB user document keyed by user_id string.
# TTL=60s bounds maximum stale-permission window.
# Call invalidate_user_cache() after any security-relevant profile mutation.
_user_cache: TTLCache = TTLCache(maxsize=2000, ttl=60)
_user_cache_lock = threading.Lock()


def invalidate_user_cache(user_id: str) -> None:
    """Remove a user's cached document immediately (e.g. after suspend/update)."""
    with _user_cache_lock:
        _user_cache.pop(user_id, None)

JWT_ALGORITHM = "HS256"
ACCESS_MIN = 15          # 15 minutes — short-lived; refresh rotation handles silent renewal
REFRESH_DAYS = 14
CSRF_MAX_AGE = ACCESS_MIN * 60  # same lifetime as access token

# ─────────────────── JWT secret validation ───────────────────────────────────

_WEAK_SECRETS = {
    "secret", "password", "changeme", "jwt_secret", "your_secret",
    "synaptiq", "development", "1234567890", "abc123",
}


def validate_jwt_secret(secret: str) -> None:
    """Raise RuntimeError if the JWT secret is weak (AUTH-001)."""
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    lower = secret.lower()
    for weak in _WEAK_SECRETS:
        if weak in lower:
            raise RuntimeError(
                f"JWT_SECRET appears to contain a predictable value ('{weak}'). "
                "Generate a secure secret with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
    # Require at least 64 bits of entropy: must have mixed characters
    has_upper = any(c.isupper() for c in secret)
    has_lower = any(c.islower() for c in secret)
    has_digit = any(c.isdigit() for c in secret)
    has_special = any(not c.isalnum() for c in secret)
    variety = sum([has_upper, has_lower, has_digit, has_special])
    if variety < 2:
        raise RuntimeError(
            "JWT_SECRET must contain at least two character classes (upper, lower, digit, special). "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )


def _is_prod() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


def _secret() -> str:
    s = os.environ["JWT_SECRET"]
    if _is_prod():
        validate_jwt_secret(s)
    return s


# ─────────────────── Password ─────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─────────────────── Token creation ──────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "jti": str(uuid.uuid4()),   # AUTH-009: proper UUID JTI
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=ACCESS_MIN),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (encoded_jwt, jti). Caller must persist the jti via token_service."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,                 # AUTH-009 + AUTH-005
        "iat": int(now.timestamp()),
        "exp": now + timedelta(days=REFRESH_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM), jti


# ─────────────────── Cookies ─────────────────────────────────────────────────

def _cookie_flags() -> dict:
    secure = os.environ.get("COOKIE_SECURE", "0") == "1"
    samesite = os.environ.get("COOKIE_SAMESITE", "lax").lower()
    if samesite not in ("lax", "strict", "none"):
        samesite = "lax"
    return {"secure": secure, "samesite": samesite}


def set_auth_cookies(response, access_token: str, refresh_token: str, remember: bool = True) -> None:
    """Set the access/refresh cookies.

    `remember` controls whether the refresh cookie survives a browser
    restart: when True it gets an explicit Max-Age (REFRESH_DAYS); when
    False it's set as a session cookie (no Max-Age) so the browser drops it
    on close, while the underlying JWT keeps the same server-side validity
    window either way. Previously every login always got the persistent
    cookie regardless of the "Remember me" checkbox, which had no effect.
    """
    f = _cookie_flags()
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        max_age=ACCESS_MIN * 60, path="/", **f,
    )
    refresh_kwargs = dict(key="refresh_token", value=refresh_token, httponly=True, path="/", **f)
    if remember:
        refresh_kwargs["max_age"] = REFRESH_DAYS * 86400
    response.set_cookie(**refresh_kwargs)


def clear_auth_cookies(response) -> None:
    f = _cookie_flags()
    response.delete_cookie("access_token", path="/", httponly=True, **f)
    response.delete_cookie("refresh_token", path="/", httponly=True, **f)


def set_csrf_cookie(response) -> str:
    """Generate and set the double-submit CSRF cookie. Returns the token value (AUTH-007)."""
    token = secrets.token_urlsafe(32)
    f = _cookie_flags()
    # CSRF cookie must NOT be HttpOnly — JS needs to read it.
    response.set_cookie(
        key="csrf_token", value=token,
        httponly=False, max_age=CSRF_MAX_AGE, path="/",
        secure=f["secure"], samesite=f["samesite"],
    )
    return token


def clear_csrf_cookie(response) -> None:
    f = _cookie_flags()
    response.delete_cookie("csrf_token", path="/", httponly=False,
                           secure=f["secure"], samesite=f["samesite"])


# ─────────────────── User serialization ──────────────────────────────────────

def _scrub_orcid(orcid):
    """Return public-safe ORCID representation (strips tokens)."""
    if isinstance(orcid, dict):
        return {
            "orcid_id":     orcid.get("orcid_id"),
            "verified_at":  orcid.get("verified_at"),
            "last_sync_at": orcid.get("last_sync_at"),
        }
    return orcid


def serialize_user(user: dict) -> dict:
    """Full serialisation for the authenticated user's own /me endpoint."""
    if not user:
        return None
    out = dict(user)
    out["id"] = str(out.pop("_id"))
    out.pop("password_hash", None)
    out["orcid"] = _scrub_orcid(out.get("orcid"))
    _sa_emails = {
        e.strip().lower()
        for e in os.environ.get("SUPER_ADMIN_EMAILS", "admin@synaptiq.academy").split(",")
        if e.strip()
    }
    out["is_super_admin"] = (
        out.get("role") == "super_admin"
        or (out.get("email") or "").lower() in _sa_emails
    )
    return out


def _compute_dashboard_mode(primary_domain: str | None) -> str:
    if primary_domain == "teaching": return "teaching"
    if primary_domain == "both":     return "hybrid"
    return "research"


def serialize_public_user(user: dict) -> dict:
    """Public-safe serialisation for profile/directory endpoints.

    Strips: email, password_hash, is_super_admin, role, status, auth metadata,
    and the full connections array (replaced by a count to prevent harvesting).
    """
    if not user:
        return None
    return {
        # Identity
        "id":                  str(user["_id"]),
        "full_name":           user.get("full_name") or "",
        "first_name":          user.get("first_name") or "",
        "last_name":           user.get("last_name") or "",
        "institution":         user.get("institution") or "",
        "department":          user.get("department") or "",
        "country":             user.get("country") or "",
        "city":                user.get("city") or "",
        "academic_role":       user.get("academic_role") or "",
        "career_stage":        user.get("career_stage") or "",
        "user_type":              user.get("user_type") or None,
        "primary_domain":         user.get("primary_domain") or None,
        "dashboard_mode":         _compute_dashboard_mode(user.get("primary_domain")),
        "teaching_areas":         user.get("teaching_areas") or [],
        "professional_expertise": user.get("professional_expertise") or [],
        "biography":           user.get("biography") or "",
        # Academic identifiers
        "orcid":               _scrub_orcid(user.get("orcid")),
        "google_scholar":      user.get("google_scholar") or "",
        "researchgate":        user.get("researchgate") or "",
        "scopus_id":           user.get("scopus_id") or "",
        "linkedin":            user.get("linkedin") or "",
        "website":             user.get("website") or "",
        "openalex_author_id":  user.get("openalex_author_id") or "",
        "openalex_profile_url": user.get("openalex_profile_url") or "",
        # Media
        "avatar_url":          user.get("avatar_url"),
        "cover_photo":         user.get("cover_photo"),
        # Research profile
        "research_areas":      user.get("research_areas") or [],
        "research_interests":  user.get("research_interests") or [],
        "research_keywords":   user.get("research_keywords") or [],
        "methods":             user.get("methods") or [],
        "methodological_expertise": user.get("methodological_expertise") or [],
        "software_skills":     user.get("software_skills") or [],
        "languages":           user.get("languages") or [],
        "skills":              user.get("skills") or [],
        "can_contribute":      user.get("can_contribute") or [],
        "looking_for":         user.get("looking_for") or [],
        "expertise_role_tags": user.get("expertise_role_tags") or [],
        # Availability
        "availability":        user.get("availability") or "",
        "available_for_collaboration": bool(user.get("available_for_collaboration", True)),
        "available_for_supervision":   bool(user.get("available_for_supervision", False)),
        "available_for_reviewing":     bool(user.get("available_for_reviewing", False)),
        "available_for_consulting":    bool(user.get("available_for_consulting", False)),
        # ORCID-imported records (scrubbed — tokens never exposed)
        "orcid_employments":   user.get("orcid_employments") or [],
        "orcid_educations":    user.get("orcid_educations") or [],
        "orcid_fundings":      user.get("orcid_fundings") or [],
        # Career
        "awards":              user.get("awards") or [],
        "certifications":      user.get("certifications") or [],
        "memberships":         user.get("memberships") or [],
        # Metrics
        "h_index":             user.get("h_index") or 0,
        "publications_count":  user.get("publications_count") or 0,
        "conferences_count":   user.get("conferences_count") or 0,
        "connections_count":   len(user.get("connections") or []),
        "collaboration_score": user.get("collaboration_score") or 0,
        "publication_score":   user.get("publication_score") or 0,
        "expertise_score":     user.get("expertise_score") or 0,
        "community_score":     user.get("community_score") or 0,
        "onboarded":           bool(user.get("onboarded")),
        "created_at":          user.get("created_at") or "",
    }


# ─────────────────── Request dependencies ────────────────────────────────────

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id_str = payload["sub"]
        # L1 cache: avoid a DB round-trip on every authenticated request.
        with _user_cache_lock:
            user = _user_cache.get(user_id_str)
        if user is None:
            user = await make_db_proxy(get_db(), system=True).users.find_one({"_id": ObjectId(user_id_str)})
            if user:
                with _user_cache_lock:
                    _user_cache[user_id_str] = user
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # C2: platform-wide session invalidation via force_logout_at.
        # Admin sets this timestamp; any token issued BEFORE it is rejected.
        _fla = user.get("force_logout_at")
        if _fla:
            try:
                _fla_dt = datetime.fromisoformat(_fla.replace("Z", "+00:00"))
                if payload.get("iat", 0) < int(_fla_dt.timestamp()):
                    raise HTTPException(
                        status_code=401,
                        detail="Session invalidated by administrator. Please log in again.",
                    )
            except HTTPException:
                raise
            except Exception:
                pass

        # BLOCKER-2: server-side account status enforcement on every request.
        # These checks are intentionally after the DB fetch so any admin action
        # (suspend, ban) takes effect on the very next API call — not at token expiry.
        status = user.get("status")
        if status == "suspended":
            raise HTTPException(status_code=403, detail="Account suspended. Contact support.")
        if status == "banned":
            raise HTTPException(status_code=403, detail="Account has been banned.")

        # Email verification gate — enforced when EMAIL_VERIFICATION_REQUIRED=1.
        # Super admins are exempt (their accounts are pre-verified in seed).
        _sa_emails = {
            e.strip().lower()
            for e in os.environ.get("SUPER_ADMIN_EMAILS", "admin@synaptiq.academy").split(",")
            if e.strip()
        }
        is_super = user.get("role") == "super_admin" or (user.get("email") or "").lower() in _sa_emails
        if (
            not is_super
            and os.environ.get("EMAIL_VERIFICATION_REQUIRED", "0") == "1"
            and not user.get("email_verified")
            and user.get("email")  # email-less ORCID users cannot be verified; allow through
        ):
            raise HTTPException(
                status_code=403,
                detail="Email not verified. Please check your inbox or request a new verification link.",
            )

        return serialize_user(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
