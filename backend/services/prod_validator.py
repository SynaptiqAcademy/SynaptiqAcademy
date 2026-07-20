"""Production environment validation — AUTH-001 / AUTH-010 / AUTH-015.

Runs at FastAPI startup. In PRODUCTION mode (APP_ENV=production), the app
REFUSES to start when critical security/integration env vars are missing or
unsafe. In dev/staging, it logs warnings only.

New checks added in this revision:
  AUTH-001 — JWT_SECRET entropy (not just length; rejects predictable values)
  AUTH-010 — SUPER_ADMIN_EMAILS must not be the hard-coded default in prod
  AUTH-012 — ENCRYPTION_KEY required in production
  AUTH-013 — Google OAuth credentials (warn-level)
  AUTH-015 — EXPOSE_RESET_TOKEN enforced off; EMAIL_VERIFICATION_REQUIRED on
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger("synaptiq.prod_validator")

_WEAK_JWT_SUBSTRINGS = {
    "secret", "password", "changeme", "jwt_secret", "your_secret",
    "synaptiq", "development", "1234567890", "abc123", "example",
}

_DEFAULT_SUPER_ADMIN_EMAIL = "synaptiq.academy@gmail.com"


def _is_prod() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("prod", "production")


def _jwt_secret_strong(secret: str) -> bool:
    if not secret or len(secret) < 32:
        return False
    lower = secret.lower()
    for weak in _WEAK_JWT_SUBSTRINGS:
        if weak in lower:
            return False
    has_upper = any(c.isupper() for c in secret)
    has_lower = any(c.islower() for c in secret)
    has_digit = any(c.isdigit() for c in secret)
    has_special = any(not c.isalnum() for c in secret)
    return sum([has_upper, has_lower, has_digit, has_special]) >= 2


def _super_admin_not_default() -> bool:
    val = os.environ.get("SUPER_ADMIN_EMAILS", "").strip().lower()
    return bool(val) and val != _DEFAULT_SUPER_ADMIN_EMAIL


def _encryption_key_valid() -> bool:
    import base64
    raw = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not raw:
        return False
    try:
        return len(base64.b64decode(raw)) == 32
    except Exception:
        return False


def _checks() -> List[Tuple[str, str, callable, str]]:
    has = lambda key: bool(os.environ.get(key, "").strip())
    eq = lambda key, val: os.environ.get(key, "").strip() == val

    def _mongo_uri_valid() -> bool:
        uri = (
            os.environ.get("MONGODB_URI", "").strip()
            or os.environ.get("MONGO_URL", "").strip()
        )
        if not uri:
            return False
        # In production, reject any localhost / plain mongodb:// URI
        if _is_prod():
            if not uri.startswith("mongodb+srv://"):
                return False
            if "localhost" in uri or "127.0.0.1" in uri:
                return False
        return True

    def _mongo_db_name_set() -> bool:
        return bool(
            os.environ.get("MONGODB_DB_NAME", "").strip()
            or os.environ.get("DB_NAME", "").strip()
        )

    def _redis_url_valid() -> bool:
        url = os.environ.get("REDIS_URL", "").strip()
        if not url:
            return False
        if _is_prod() and ("localhost" in url or "127.0.0.1" in url):
            return False
        return True

    def _redis_password_set() -> bool:
        # Either REDIS_PASSWORD is explicit, or the URL embeds credentials
        pw = os.environ.get("REDIS_PASSWORD", "").strip()
        if pw:
            return True
        url = os.environ.get("REDIS_URL", "").strip()
        # redis://:password@host — credentials embedded
        return "://" in url and "@" in url and url.split("://")[1].startswith(":")

    def _stripe_plan_price_ids_set() -> bool:
        # "enterprise" is intentionally excluded — it's fulfilled via custom
        # Stripe invoices, not self-serve Checkout, and has no price IDs by
        # design. "free" has no price at all. Only self-serve paid plans need
        # both monthly and annual price IDs filled in for checkout to work.
        try:
            from plans_catalogue import PLANS
        except Exception:
            return False
        for p in PLANS:
            if p["code"] in ("free", "enterprise"):
                continue
            if not p.get("stripe_price_id_monthly") or not p.get("stripe_price_id_annual"):
                return False
        return True

    return [
        # ---- Core ----
        ("MONGODB_URI", "error", _mongo_uri_valid,
         "Atlas connection string required. "
         "Set MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/ "
         "(plain mongodb:// or localhost rejected in production)"),
        ("MONGODB_DB_NAME", "error", _mongo_db_name_set,
         "Database name required — set MONGODB_DB_NAME=synaptiq"),

        # ---- Redis ----
        ("REDIS_URL", "error", _redis_url_valid,
         "Redis URL must be set and must not point to localhost in production. "
         "Set REDIS_URL=redis://:password@synaptiq_redis:6379/0"),
        ("REDIS_PASSWORD", "error", _redis_password_set,
         "Redis must be password-protected in production. "
         "Set REDIS_PASSWORD and ensure REDIS_URL embeds it"),

        # AUTH-001: JWT_SECRET entropy validation
        ("JWT_SECRET", "error",
            lambda: _jwt_secret_strong(os.environ.get("JWT_SECRET", "")),
            "JWT_SECRET must be ≥32 chars, not contain predictable substrings, "
            "and have at least 2 character classes. "
            "Generate: python -c \"import secrets; print(secrets.token_hex(32))\""),

        # FRONTEND_BASE_URL is canonical; APP_BASE_URL is a deprecated backward-
        # compatible alias, still accepted here so existing deployments aren't
        # broken by this rename (see ENVIRONMENT_VARIABLES.md).
        ("FRONTEND_BASE_URL", "error",
            lambda: has("FRONTEND_BASE_URL") or has("APP_BASE_URL"),
            "Public frontend base URL required for emails + OAuth callbacks. "
            "Set FRONTEND_BASE_URL (APP_BASE_URL accepted as a deprecated alias)"),

        # ---- Security ----
        ("CORS_ORIGINS", "error",
            lambda: has("CORS_ORIGINS") and os.environ.get("CORS_ORIGINS", "").strip() != "*",
            "Explicit comma-separated origin allowlist; wildcard rejected"),
        ("COOKIE_SECURE", "error", lambda: eq("COOKIE_SECURE", "1"),
            "Must be '1' in production (HTTPS-only cookies)"),
        ("COOKIE_SAMESITE", "warn",
            lambda: os.environ.get("COOKIE_SAMESITE", "lax").lower() in ("lax", "strict"),
            "Recommended 'strict' or 'lax' in production"),

        # AUTH-003: EXPOSE_RESET_TOKEN must be off
        ("EXPOSE_RESET_TOKEN", "error",
            lambda: os.environ.get("EXPOSE_RESET_TOKEN", "0") == "0",
            "MUST be '0' in production — debug tokens expose reset links"),

        # AUTH-002: Email verification must be on
        ("EMAIL_VERIFICATION_REQUIRED", "error",
            lambda: eq("EMAIL_VERIFICATION_REQUIRED", "1"),
            "Must be '1' in production to gate sign-in until email is verified"),

        # AUTH-010: Super admin email must not be the hard-coded default
        ("SUPER_ADMIN_EMAILS", "error",
            _super_admin_not_default,
            f"SUPER_ADMIN_EMAILS must be set to a real email (not the default '{_DEFAULT_SUPER_ADMIN_EMAIL}')"),

        # AUTH-012: Encryption key for field-level encryption
        ("ENCRYPTION_KEY", "error",
            _encryption_key_valid,
            "ENCRYPTION_KEY must be set to a 32-byte base64-encoded key. "
            "Generate: python -c \"import os,base64; print(base64.b64encode(os.urandom(32)).decode())\""),

        # ---- AI ----
        ("ANTHROPIC_API_KEY", "warn", lambda: has("ANTHROPIC_API_KEY"),
            "Required for AI matching + assistant features"),

        # ---- Stripe ----
        ("STRIPE_SECRET_KEY", "warn", lambda: has("STRIPE_SECRET_KEY"),
            "Required for billing checkout endpoints"),
        ("STRIPE_WEBHOOK_SECRET", "warn", lambda: has("STRIPE_WEBHOOK_SECRET"),
            "Required to verify Stripe webhooks"),
        # NOTE: checkout price IDs are not environment variables — they live on
        # each plan in plans_catalogue.PLANS (stripe_price_id_monthly/_annual).
        # This check inspects that real runtime source of truth directly,
        # rather than a STRIPE_PRICE_* env var that nothing in the app reads.
        ("STRIPE_PLAN_PRICE_IDS", "warn", _stripe_plan_price_ids_set,
            "One or more paid plans in plans_catalogue.PLANS is missing a "
            "stripe_price_id_monthly/_annual — checkout will 503 for that plan "
            "until it's filled in (see STRIPE_SETUP.md)"),

        # ---- Resend ----
        ("EMAIL_PROVIDER", "error", lambda: eq("EMAIL_PROVIDER", "resend"), "Must be 'resend' — only supported email provider"),
        ("RESEND_API_KEY", "error", lambda: has("RESEND_API_KEY"), "Required for live transactional emails (auth, invitations, resets)"),
        ("EMAIL_FROM",     "error", lambda: has("EMAIL_FROM"),     "Required From-address on verified Resend domain (set to admin@synaptiq.academy)"),
        ("EMAIL_DRY_RUN",  "error", lambda: eq("EMAIL_DRY_RUN", "0"), "Must be '0' to send emails in production — dry-run silently drops all outbound mail"),

        # ---- ORCID ----
        ("ORCID_CLIENT_ID",     "warn", lambda: has("ORCID_CLIENT_ID"),     "Required for ORCID OAuth"),
        ("ORCID_CLIENT_SECRET", "warn", lambda: has("ORCID_CLIENT_SECRET"), "Required for ORCID OAuth"),
        ("ORCID_REDIRECT_URI",  "warn", lambda: has("ORCID_REDIRECT_URI"),  "Must match the URI in the ORCID app"),
        ("ORCID_BASE_URL", "warn",
            lambda: os.environ.get("ORCID_BASE_URL", "").rstrip("/") in
                    ("https://orcid.org", "https://sandbox.orcid.org"),
            "Set to https://orcid.org in production; sandbox.orcid.org in staging"),

        # AUTH-013: Google OAuth
        ("GOOGLE_CLIENT_ID",     "warn", lambda: has("GOOGLE_CLIENT_ID"),     "Required for Google OAuth"),
        ("GOOGLE_CLIENT_SECRET", "warn", lambda: has("GOOGLE_CLIENT_SECRET"), "Required for Google OAuth"),
        ("GOOGLE_REDIRECT_URI",  "warn", lambda: has("GOOGLE_REDIRECT_URI"),  "Must match registered Google redirect URI"),

        # ---- Discovery ----
        ("DISCOVERY_CONTACT_EMAIL", "warn", lambda: has("DISCOVERY_CONTACT_EMAIL"),
            "Polite User-Agent for OpenAlex/Crossref"),

        # ---- Backup / DR ----
        ("AWS_ACCESS_KEY_ID", "warn", lambda: has("AWS_ACCESS_KEY_ID"),
            "Required for automated S3 backups (deploy/backup.sh)"),
        ("AWS_SECRET_ACCESS_KEY", "warn", lambda: has("AWS_SECRET_ACCESS_KEY"),
            "Required for automated S3 backups (deploy/backup.sh)"),
        ("S3_BACKUP_BUCKET", "warn", lambda: has("S3_BACKUP_BUCKET"),
            "S3 bucket name for encrypted MongoDB backups — set S3_BACKUP_BUCKET=synaptiq-backups"),
        ("BACKUP_ENCRYPTION_PASSPHRASE", "warn",
            lambda: has("BACKUP_ENCRYPTION_PASSPHRASE") and len(os.environ.get("BACKUP_ENCRYPTION_PASSPHRASE","")) >= 24,
            "AES-256 backup encryption passphrase — min 24 chars. "
            "Generate: python -c \"import secrets; print(secrets.token_urlsafe(48))\""),
        ("ALERT_WEBHOOK_URL", "warn", lambda: has("ALERT_WEBHOOK_URL"),
            "Slack/Discord webhook for backup success/failure and disk space alerts"),

        # ---- OAuth state secrets ----
        ("ORCID_STATE_SECRET", "warn", lambda: has("ORCID_STATE_SECRET"),
            "ORCID OAuth CSRF state secret — defaults to JWT_SECRET if unset, but should be explicit"),
    ]


def evaluate_env() -> Dict:
    results = {
        "app_env": os.environ.get("APP_ENV", "development"),
        "is_production": _is_prod(),
        "checks": [], "errors": [], "warnings": [],
    }
    for name, sev, pred, hint in _checks():
        try:
            passed = bool(pred())
        except Exception:
            passed = False
        entry = {"name": name, "severity": sev, "passed": passed, "hint": hint}
        results["checks"].append(entry)
        if not passed:
            (results["errors"] if sev == "error" else results["warnings"]).append(entry)
    results["ready_for_production"] = len(results["errors"]) == 0
    return results


def validate_on_startup():
    r = evaluate_env()
    if not _is_prod():
        if r["warnings"] or r["errors"]:
            names = [c["name"] for c in r["warnings"] + r["errors"]]
            logger.info("Env checks (non-blocking in dev/staging): %s", names)
        return
    if r["errors"]:
        bullets = "\n".join(f"  - {c['name']}: {c['hint']}" for c in r["errors"])
        msg = (
            f"\n*** PRODUCTION STARTUP REFUSED ***\n"
            f"{len(r['errors'])} required env var(s) are missing/invalid:\n{bullets}\n"
            f"Either fix the env, OR set APP_ENV=staging to bypass strict mode."
        )
        logger.error(msg)
        raise RuntimeError(msg)
    logger.info("Production env validation passed (%d warnings)", len(r["warnings"]))
