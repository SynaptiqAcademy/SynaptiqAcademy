"""
Zero Trust Security Platform — Phase XXXV.8

Provides enterprise-grade Zero Trust security for every request,
AI execution, database operation, and mission.

Lifecycle:
    await init_zero_trust(app, db)
    await stop_zero_trust()
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)

# ── Public re-exports ─────────────────────────────────────────────────────────

from .identity import (
    IdentityContext,
    IdentityType,
    AuthMethod,
    ANONYMOUS_IDENTITY,
    build_identity_context,
    identity_type_from_user,
)

from .authorization import (
    AuthorizationEngine,
    AuthzDecision,
    Action,
    Resource,
    get_authz_engine,
    init_authz_engine,
)

from .policy import (
    Policy,
    PolicyEngine,
    PolicyEffect,
    PolicyScope,
    get_policy_engine,
    init_policy_engine,
)

from .classification import (
    ClassificationLevel,
    ClassificationPolicy,
    DataClassifier,
    get_classifier,
)

from .field_security import (
    FieldVisibility,
    FieldRule,
    FieldSecurityEngine,
    get_field_security,
)

from .encryption import (
    EncryptionEngine,
    get_encryption,
    init_encryption,
)

from .key_management import (
    KeyManager,
    KeyType,
    KeyStatus,
    KeyMetadata,
    get_key_manager as get_zt_key_manager,
    init_key_management,
)

from .governance import (
    DataGovernanceEngine,
    GovernanceRecord,
    LineageRecord,
    get_governance,
    init_governance,
)

from .privacy import (
    PrivacyCenter,
    PrivacyRequest,
    PrivacyRequestType,
    RequestStatus,
    get_privacy_center,
    init_privacy_center,
)

from .ai_security import (
    AISecurityEngine,
    ThreatType,
    ThreatSeverity,
    ScanResult,
    get_ai_security,
)

from .risk_engine import (
    RiskEngine,
    RiskScore,
    RiskLevel,
    RiskFactor,
    get_risk_engine,
)

from .compliance import (
    ComplianceFramework,
    ComplianceStatus,
    ComplianceControl,
    ComplianceChecker,
    get_compliance,
)

from .monitoring import (
    SecurityMonitor,
    SecurityEvent,
    AnomalyType,
    EventSeverity,
    get_monitor,
    init_monitoring,
)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def init_zero_trust(app: Any, db: Any) -> None:
    """
    Initialise the Zero Trust Security Platform.
    Called from server.py @app.on_event("startup").
    """
    # Register ZT middleware (inner — wraps after observability)
    try:
        from .middleware import ZeroTrustMiddleware
        app.add_middleware(ZeroTrustMiddleware)
        _log.info("ZeroTrustMiddleware registered")
    except Exception as exc:
        _log.warning("ZeroTrustMiddleware registration skipped: %s", exc)

    # Initialise all subsystems
    init_authz_engine()
    init_encryption()

    policy_engine = init_policy_engine(db)
    init_key_management(db)
    init_governance(db)
    init_privacy_center(db)
    init_monitoring(db)

    # Ensure MongoDB indexes
    try:
        await policy_engine.ensure_indexes()
        await get_zt_key_manager().ensure_indexes()
        await get_governance().ensure_indexes()
        await get_privacy_center().ensure_indexes()
        await get_monitor().ensure_indexes()
        await db["zt_audit"].create_index("timestamp")
        await db["zt_audit"].create_index("actor_id")
    except Exception as exc:
        _log.debug("ZT index creation (non-fatal): %s", exc)

    # Load persisted policies
    try:
        await policy_engine.load_policies()
        _log.debug("Loaded %d ZT policies", len(policy_engine.list_cached()))
    except Exception as exc:
        _log.debug("Policy load: %s", exc)

    _log.info("Zero Trust Security Platform initialised (Phase XXXV.8)")


async def stop_zero_trust() -> None:
    _log.info("Zero Trust Security Platform stopped")
