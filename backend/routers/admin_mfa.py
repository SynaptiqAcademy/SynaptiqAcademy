"""Admin MFA Management — enrollment, verification, recovery codes, status.

All endpoints require super_admin.  The MFA secret is only returned during
enrollment (never again after that).  Recovery codes are shown once on
completion and once on regeneration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from services.permissions import require_super_admin
from services.mfa_service import (
    get_mfa_config, mfa_is_enabled, begin_enrollment, complete_enrollment,
    verify_mfa_code, disable_mfa, regenerate_recovery_codes,
)
from services.admin_audit import log_event, request_meta
from services.security_event_service import emit_security_event

router = APIRouter(prefix="/api/admin/mfa", tags=["admin-mfa"])
_GATE = [Depends(require_super_admin)]


class VerifyBody(BaseModel):
    code: str


class DisableBody(BaseModel):
    code: str       # must prove current OTP to disable


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/mfa/status
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status", dependencies=_GATE)
async def mfa_status(admin: dict = Depends(require_super_admin)):
    cfg = await get_mfa_config(admin["id"])
    enabled = bool(cfg and cfg.get("enabled"))
    recovery_remaining = len(cfg.get("recovery_codes", [])) if cfg else 0
    return {
        "enabled":              enabled,
        "configured_at":        cfg.get("configured_at") if cfg else None,
        "last_used_at":         cfg.get("last_used_at")  if cfg else None,
        "use_count":            cfg.get("use_count", 0)  if cfg else 0,
        "recovery_codes_remaining": recovery_remaining,
        "enrollment_pending":   bool(cfg and not cfg.get("enabled") and cfg.get("secret")),
        "email":                admin.get("email"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/admin/mfa/enroll
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/enroll", dependencies=_GATE)
async def enroll_mfa(admin: dict = Depends(require_super_admin), request: Request = None):
    """Begin MFA enrollment. Returns TOTP secret and QR code PNG (base64)."""
    if await mfa_is_enabled(admin["id"]):
        raise HTTPException(status_code=400, detail="MFA is already enabled. Disable it first to re-enroll.")
    data = await begin_enrollment(admin["id"], admin.get("email", ""))
    meta = request_meta(request) if request else {}
    await log_event("admin.mfa.enrollment_started", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {
        "secret":       data["secret"],
        "qr_png_b64":   data["qr_b64"],
        "issuer":       "Synaptiq",
        "account":      admin.get("email"),
        "instructions": [
            "Open Google Authenticator, Microsoft Authenticator, or Authy.",
            "Tap the + button and choose 'Scan QR code'.",
            "Scan the QR code or enter the secret manually.",
            "Enter the 6-digit code below to confirm enrollment.",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/admin/mfa/confirm
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/confirm", dependencies=_GATE)
async def confirm_mfa(body: VerifyBody, admin: dict = Depends(require_super_admin), request: Request = None):
    """Verify the first TOTP code and activate MFA. Returns plaintext recovery codes (shown once)."""
    ok, recovery_codes = await complete_enrollment(admin["id"], body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid code. Make sure your authenticator app's time is correct.")
    meta = request_meta(request) if request else {}
    await log_event("admin.mfa.enabled", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    await emit_security_event("mfa_enabled", actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {
        "ok":              True,
        "recovery_codes":  recovery_codes,
        "warning":         "Store these recovery codes in a safe place. They will not be shown again.",
        "codes_count":     len(recovery_codes),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/admin/mfa/disable
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/disable", dependencies=_GATE)
async def disable_mfa_endpoint(body: DisableBody, admin: dict = Depends(require_super_admin), request: Request = None):
    """Disable MFA. Requires a valid TOTP code as proof of possession."""
    if not await mfa_is_enabled(admin["id"]):
        raise HTTPException(status_code=400, detail="MFA is not currently enabled.")
    ok, method = await verify_mfa_code(admin["id"], body.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid code. MFA not disabled.")
    await disable_mfa(admin["id"])
    meta = request_meta(request) if request else {}
    await log_event("admin.mfa.disabled", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    await emit_security_event("mfa_disabled", severity="high",
                               actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {"ok": True, "message": "MFA has been disabled. Your account is now password-only."}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/admin/mfa/recovery-codes/regenerate
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/recovery-codes/regenerate", dependencies=_GATE)
async def regen_recovery_codes(body: VerifyBody, admin: dict = Depends(require_super_admin), request: Request = None):
    """Regenerate all recovery codes. Requires current TOTP as proof. Old codes invalidated."""
    ok, method = await verify_mfa_code(admin["id"], body.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid authentication code.")
    success, new_codes = await regenerate_recovery_codes(admin["id"])
    if not success:
        raise HTTPException(status_code=400, detail="MFA not enabled.")
    meta = request_meta(request) if request else {}
    await log_event("admin.mfa.recovery_codes_regenerated", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    await emit_security_event("mfa_codes_regenerated",
                               actor_id=admin["id"], actor_email=admin.get("email"),
                               ip=meta.get("ip"), user_agent=meta.get("user_agent"))
    return {
        "ok":             True,
        "recovery_codes": new_codes,
        "warning":        "Old recovery codes are now invalidated. Store the new codes safely.",
        "codes_count":    len(new_codes),
    }
