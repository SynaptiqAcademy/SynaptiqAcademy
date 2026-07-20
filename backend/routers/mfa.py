"""Self-service Multi-Factor Authentication — any authenticated user, not just
admins. Reuses the exact same TOTP logic as backend/routers/admin_mfa.py
(services/mfa_service.py was already generic/per-user, just previously only
wired up behind require_super_admin).

The MFA secret is only returned during enrollment (never again after that).
Recovery codes are shown once on completion and once on regeneration.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth_utils import get_current_user
from services.mfa_service import (
    get_mfa_config, mfa_is_enabled, begin_enrollment, complete_enrollment,
    verify_mfa_code, disable_mfa, regenerate_recovery_codes,
)
from services.admin_audit import log_event, request_meta
from services.security_event_service import emit_security_event

router = APIRouter(prefix="/api/mfa", tags=["mfa"])


class VerifyBody(BaseModel):
    code: str


class DisableBody(BaseModel):
    code: str       # must prove current OTP to disable


@router.get("/status")
async def mfa_status(user: dict = Depends(get_current_user)):
    cfg = await get_mfa_config(user["id"])
    enabled = bool(cfg and cfg.get("enabled"))
    recovery_remaining = len(cfg.get("recovery_codes", [])) if cfg else 0
    return {
        "enabled":              enabled,
        "configured_at":        cfg.get("configured_at") if cfg else None,
        "last_used_at":         cfg.get("last_used_at")  if cfg else None,
        "use_count":            cfg.get("use_count", 0)  if cfg else 0,
        "recovery_codes_remaining": recovery_remaining,
        "enrollment_pending":   bool(cfg and not cfg.get("enabled") and cfg.get("secret")),
        "email":                user.get("email"),
    }


@router.post("/enroll")
async def enroll_mfa(user: dict = Depends(get_current_user), request: Request = None):
    """Begin MFA enrollment. Returns TOTP secret and QR code PNG (base64)."""
    if await mfa_is_enabled(user["id"]):
        raise HTTPException(status_code=400, detail="MFA is already enabled. Disable it first to re-enroll.")
    data = await begin_enrollment(user["id"], user.get("email", ""))
    meta = request_meta(request) if request else {}
    await log_event("auth.mfa.enrollment_started", actor_id=user["id"], actor_email=user.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {
        "secret":       data["secret"],
        "qr_png_b64":   data["qr_b64"],
        "issuer":       "Synaptiq",
        "account":      user.get("email"),
        "instructions": [
            "Open Google Authenticator, Microsoft Authenticator, or Authy.",
            "Tap the + button and choose 'Scan QR code'.",
            "Scan the QR code or enter the secret manually.",
            "Enter the 6-digit code below to confirm enrollment.",
        ],
    }


@router.post("/confirm")
async def confirm_mfa(body: VerifyBody, user: dict = Depends(get_current_user), request: Request = None):
    """Verify the first TOTP code and activate MFA. Returns plaintext recovery codes (shown once)."""
    ok, recovery_codes = await complete_enrollment(user["id"], body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid code. Make sure your authenticator app's time is correct.")
    meta = request_meta(request) if request else {}
    await log_event("auth.mfa.enabled", actor_id=user["id"], actor_email=user.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    await emit_security_event("mfa_enabled", actor_id=user["id"], actor_email=user.get("email"),
                               ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {
        "ok":              True,
        "recovery_codes":  recovery_codes,
        "warning":         "Store these recovery codes in a safe place. They will not be shown again.",
        "codes_count":     len(recovery_codes),
    }


@router.post("/disable")
async def disable_mfa_endpoint(body: DisableBody, user: dict = Depends(get_current_user), request: Request = None):
    """Disable MFA. Requires a valid TOTP code as proof of possession."""
    if not await mfa_is_enabled(user["id"]):
        raise HTTPException(status_code=400, detail="MFA is not currently enabled.")
    ok, method = await verify_mfa_code(user["id"], body.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid code. MFA not disabled.")
    await disable_mfa(user["id"])
    meta = request_meta(request) if request else {}
    await log_event("auth.mfa.disabled", actor_id=user["id"], actor_email=user.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    await emit_security_event("mfa_disabled", severity="high",
                               actor_id=user["id"], actor_email=user.get("email"),
                               ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {"ok": True, "message": "MFA has been disabled. Your account is now password-only."}


@router.post("/recovery-codes/regenerate")
async def regen_recovery_codes(body: VerifyBody, user: dict = Depends(get_current_user), request: Request = None):
    """Regenerate all recovery codes. Requires current TOTP as proof. Old codes invalidated."""
    ok, method = await verify_mfa_code(user["id"], body.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid authentication code.")
    success, new_codes = await regenerate_recovery_codes(user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="MFA is not enabled.")
    meta = request_meta(request) if request else {}
    await log_event("auth.mfa.recovery_codes_regenerated", actor_id=user["id"], actor_email=user.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {
        "ok":             True,
        "recovery_codes": new_codes,
        "warning":        "Store these recovery codes in a safe place. Old codes no longer work.",
        "codes_count":    len(new_codes),
    }
