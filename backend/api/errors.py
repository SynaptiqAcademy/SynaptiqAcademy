"""Standardised error hierarchy and FastAPI exception handlers — Phase XXXV.7."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .versioning import API_VERSION_CURRENT


# ── Error codes ───────────────────────────────────────────────────────────────

class EC:
    VALIDATION          = "VALIDATION_ERROR"
    AUTH_REQUIRED       = "AUTH_REQUIRED"
    PERMISSION_DENIED   = "PERMISSION_DENIED"
    NOT_FOUND           = "NOT_FOUND"
    CONFLICT            = "CONFLICT"
    RATE_LIMIT          = "RATE_LIMIT_EXCEEDED"
    PAYMENT_REQUIRED    = "PAYMENT_REQUIRED"
    INTERNAL            = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    BAD_GATEWAY         = "BAD_GATEWAY"
    TIMEOUT             = "TIMEOUT"
    NOT_IMPLEMENTED     = "NOT_IMPLEMENTED"
    DEPRECATED          = "DEPRECATED"
    API_KEY_INVALID     = "API_KEY_INVALID"
    API_KEY_EXPIRED     = "API_KEY_EXPIRED"
    WEBHOOK_INVALID     = "WEBHOOK_INVALID"


# ── Exception hierarchy ───────────────────────────────────────────────────────

class ApiError(Exception):
    status_code: int = 400
    error_code:  str = EC.INTERNAL

    def __init__(self, message: str, code: str | None = None, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.error_code = code
        self.detail = detail or {}

    def to_response(self) -> JSONResponse:
        body = {
            "ok":      False,
            "version": API_VERSION_CURRENT,
            "error": {
                "code":    self.error_code,
                "message": self.message,
                "status":  self.status_code,
            },
        }
        if self.detail:
            body["error"]["detail"] = self.detail
        return JSONResponse(status_code=self.status_code, content=body)


class ValidationError(ApiError):
    status_code = 422
    error_code  = EC.VALIDATION


class AuthRequiredError(ApiError):
    status_code = 401
    error_code  = EC.AUTH_REQUIRED


class PermissionDeniedError(ApiError):
    status_code = 403
    error_code  = EC.PERMISSION_DENIED


class NotFoundError(ApiError):
    status_code = 404
    error_code  = EC.NOT_FOUND


class ConflictError(ApiError):
    status_code = 409
    error_code  = EC.CONFLICT


class RateLimitError(ApiError):
    status_code = 429
    error_code  = EC.RATE_LIMIT


class PaymentRequiredError(ApiError):
    status_code = 402
    error_code  = EC.PAYMENT_REQUIRED


class InternalError(ApiError):
    status_code = 500
    error_code  = EC.INTERNAL


class ServiceUnavailableError(ApiError):
    status_code = 503
    error_code  = EC.SERVICE_UNAVAILABLE


class ApiKeyInvalidError(ApiError):
    status_code = 401
    error_code  = EC.API_KEY_INVALID


class ApiKeyExpiredError(ApiError):
    status_code = 401
    error_code  = EC.API_KEY_EXPIRED


# ── FastAPI exception handlers ────────────────────────────────────────────────

async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return exc.to_response()


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    body = {
        "ok":      False,
        "version": API_VERSION_CURRENT,
        "error": {
            "code":    EC.INTERNAL,
            "message": "An unexpected error occurred",
            "status":  500,
        },
    }
    return JSONResponse(status_code=500, content=body)


def register_exception_handlers(app) -> None:
    """Register all ApiError subclass handlers on a FastAPI app."""
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
