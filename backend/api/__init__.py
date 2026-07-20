"""
Enterprise API Platform — Phase XXXV.7

Public package API.

Lifecycle (server.py):
    await init_api_platform(app, db)
    await stop_api_platform()        # on shutdown
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)

# ── Re-exports ────────────────────────────────────────────────────────────────

from .versioning import (
    V1CompatMiddleware,
    DeprecationRegistry,
    deprecate,
    get_deprecation_registry,
    get_version_info,
    API_VERSION_CURRENT,
    API_VERSIONS,
)

from .response import (
    ApiResponse,
    PaginatedResponse,
    wrap,
    wrap_error,
)

from .errors import (
    ApiError,
    ValidationError,
    AuthRequiredError,
    PermissionDeniedError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    PaymentRequiredError,
    InternalError,
    ServiceUnavailableError,
    ApiKeyInvalidError,
    ApiKeyExpiredError,
    register_exception_handlers,
    EC,
)

from .pagination import (
    PaginationParams,
    PageResult,
    paginate_list,
    paginate_query,
    encode_cursor,
    decode_cursor,
)

from .keys import (
    ApiKeyManager,
    ApiKeyRecord,
    get_key_manager,
    init_key_manager,
    SCOPE_READ,
    SCOPE_WRITE,
    SCOPE_ADMIN,
)

from .webhooks import (
    WebhookEngine,
    WebhookEvent,
    get_webhook_engine,
    init_webhook_engine,
    sign_payload,
    verify_signature,
)

from .sdk_gen import generate_python_sdk, generate_typescript_sdk

from .contracts import (
    EndpointContract,
    ContractRegistry,
    get_contract_registry,
    contract,
)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def init_api_platform(app: Any, db: Any) -> None:
    """
    Initialise the Enterprise API Platform.
    Called from server.py @app.on_event("startup").

    Registers:
    - V1CompatMiddleware (ASGI path rewriting)
    - ApiError exception handlers
    - /api/platform/* router
    - Key manager + webhook engine
    """
    # ASGI middleware — must be added BEFORE the app starts handling requests
    app.add_middleware(V1CompatMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Subsystem init
    init_key_manager(db)
    init_webhook_engine(db)

    # MongoDB indexes
    try:
        await get_key_manager().ensure_indexes()
        await get_webhook_engine().ensure_indexes()
    except Exception as exc:
        _log.debug("API platform index creation (non-fatal): %s", exc)

    _log.info("Enterprise API Platform initialised (Phase XXXV.7)")


async def stop_api_platform() -> None:
    """Graceful shutdown hook — currently a no-op placeholder."""
    _log.info("Enterprise API Platform stopped")
