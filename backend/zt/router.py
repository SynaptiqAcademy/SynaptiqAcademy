"""
Zero Trust Admin Router — Phase XXXV.8

All endpoints at /api/zt/* are super-admin only.
Provides dashboards for identity, authorization, risk, AI security,
compliance, governance, privacy, and monitoring.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from db import get_db
from services.permissions import require_super_admin
from api.response import wrap

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/zt",
    tags=["zero-trust"],
    dependencies=[Depends(require_super_admin)],
)


# ── Identity ──────────────────────────────────────────────────────────────────

@router.get("/identity/types")
async def list_identity_types():
    from .identity import IdentityType, AuthMethod
    return wrap({
        "identity_types": [t.value for t in IdentityType],
        "auth_methods":   [m.value for m in AuthMethod],
    })


# ── Authorization ─────────────────────────────────────────────────────────────

@router.get("/authorization/roles")
async def list_roles():
    from .authorization import get_authz_engine
    engine = get_authz_engine()
    return wrap({"roles": engine.all_roles()})


@router.get("/authorization/check")
async def check_permission(
    subject_id:    str = Query(...),
    identity_type: str = Query("researcher"),
    action:        str = Query(...),
    resource:      str = Query(...),
):
    from .identity import IdentityContext, IdentityType, AuthMethod
    from .authorization import get_authz_engine
    try:
        id_type = IdentityType(identity_type)
    except ValueError:
        id_type = IdentityType.RESEARCHER
    identity = IdentityContext(
        subject_id    = subject_id,
        identity_type = id_type,
        auth_method   = AuthMethod.PASSWORD,
        roles         = [id_type.value],
    )
    decision = get_authz_engine().check(identity, action, resource)
    return wrap({"allowed": decision.allowed, "reason": decision.reason})


# ── Policy engine ─────────────────────────────────────────────────────────────

@router.get("/policies")
async def list_policies(db: Any = Depends(get_db)):
    from .policy import get_policy_engine
    engine = get_policy_engine()
    return wrap({"policies": engine.list_cached(), "total": len(engine.list_cached())})


@router.post("/policies")
async def create_policy(body: dict, db: Any = Depends(get_db)):
    from .policy import get_policy_engine, PolicyEffect, PolicyScope
    engine = get_policy_engine()
    policy = await engine.create_policy(
        name        = body["name"],
        effect      = PolicyEffect(body.get("effect", "allow")),
        actions     = body.get("actions", ["*"]),
        resources   = body.get("resources", ["*"]),
        scope       = PolicyScope(body.get("scope", "global")),
        conditions  = body.get("conditions", {}),
        priority    = body.get("priority", 100),
        description = body.get("description", ""),
        created_by  = body.get("created_by", "admin"),
    )
    return wrap(policy.to_dict(), message="Policy created")


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str, db: Any = Depends(get_db)):
    from .policy import get_policy_engine
    ok = await get_policy_engine().delete_policy(policy_id)
    return wrap({"deleted": ok})


@router.patch("/policies/{policy_id}/toggle")
async def toggle_policy(policy_id: str, body: dict, db: Any = Depends(get_db)):
    from .policy import get_policy_engine
    ok = await get_policy_engine().toggle_policy(policy_id, body.get("enabled", True))
    return wrap({"updated": ok})


# ── Data classification ───────────────────────────────────────────────────────

@router.get("/classification/levels")
async def list_classification_levels():
    from .classification import get_classifier
    return wrap({"levels": get_classifier().all_levels()})


@router.get("/classification/infer")
async def infer_classification(collection: str = Query(...)):
    from .classification import get_classifier
    level = get_classifier().classify_collection(collection)
    return wrap({"collection": collection, "level": level})


# ── Encryption ────────────────────────────────────────────────────────────────

@router.post("/encryption/encrypt")
async def encrypt_field(body: dict):
    from .encryption import get_encryption
    value  = body.get("value", "")
    key_id = body.get("key_id", "default")
    ct     = get_encryption().encrypt_field(value, key_id)
    return wrap({"ciphertext": ct, "key_id": key_id})


@router.post("/encryption/decrypt")
async def decrypt_field(body: dict):
    from .encryption import get_encryption
    ct     = body.get("ciphertext", "")
    key_id = body.get("key_id", "default")
    try:
        pt = get_encryption().decrypt_field(ct, key_id)
        return wrap({"plaintext": pt})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


# ── Key management ────────────────────────────────────────────────────────────

@router.get("/keys/metadata")
async def list_key_metadata(key_type: str | None = Query(None)):
    from .key_management import get_key_manager, KeyType
    km = get_key_manager()
    kt = KeyType(key_type) if key_type else None
    return wrap({"keys": km.list_metadata(kt)})


@router.post("/keys/rotate/{key_id}")
async def rotate_key(key_id: str):
    from .key_management import get_key_manager
    new_meta = await get_key_manager().rotate_key(key_id)
    if not new_meta:
        return JSONResponse(status_code=404, content={"ok": False, "error": "key not found"})
    return wrap(new_meta.to_dict(), message="Key rotated")


@router.delete("/keys/revoke/{key_id}")
async def revoke_key(key_id: str):
    from .key_management import get_key_manager
    ok = await get_key_manager().revoke_key(key_id)
    return wrap({"revoked": ok})


# ── Risk engine ───────────────────────────────────────────────────────────────

@router.get("/risk/stats")
async def risk_stats():
    from .risk_engine import get_risk_engine
    return wrap(get_risk_engine().stats())


@router.get("/risk/recent")
async def risk_recent(limit: int = Query(50, ge=1, le=500)):
    from .risk_engine import get_risk_engine
    return wrap({"events": get_risk_engine().recent(limit)})


# ── AI security ───────────────────────────────────────────────────────────────

@router.post("/ai-security/scan")
async def scan_prompt(body: dict):
    from .ai_security import get_ai_security
    prompt = body.get("prompt", "")
    result = get_ai_security().scan(prompt)
    return wrap(result.to_dict())


@router.get("/ai-security/stats")
async def ai_security_stats():
    from .ai_security import get_ai_security
    return wrap(get_ai_security().stats())


# ── Governance ────────────────────────────────────────────────────────────────

@router.get("/governance/records")
async def list_governance_records(
    owner_id: str | None = Query(None),
    limit:    int        = Query(100, ge=1, le=500),
    db: Any = Depends(get_db),
):
    from .governance import get_governance
    if owner_id:
        docs = await get_governance().list_by_owner(owner_id, limit)
    else:
        docs: list[dict] = []
        async for doc in db["zt_governance"].find({}).sort("created_at", -1).limit(limit):
            doc.pop("_id", None)
            docs.append(doc)
    return wrap({"records": docs, "count": len(docs)})


@router.get("/governance/lineage/{object_id}")
async def get_lineage(object_id: str, limit: int = Query(50), db: Any = Depends(get_db)):
    from .governance import get_governance
    lineage = await get_governance().get_lineage(object_id, limit)
    return wrap({"object_id": object_id, "lineage": lineage})


# ── Privacy ───────────────────────────────────────────────────────────────────

@router.get("/privacy/requests")
async def list_privacy_requests(
    user_id:      str | None = Query(None),
    status:       str | None = Query(None),
    request_type: str | None = Query(None),
    limit:        int        = Query(100),
    db: Any = Depends(get_db),
):
    from .privacy import get_privacy_center, RequestStatus, PrivacyRequestType
    center = get_privacy_center()
    reqs   = await center.list_requests(
        user_id      = user_id,
        status       = RequestStatus(status) if status else None,
        request_type = PrivacyRequestType(request_type) if request_type else None,
        limit        = limit,
    )
    return wrap({"requests": reqs, "total": len(reqs)})


@router.post("/privacy/requests")
async def submit_privacy_request(body: dict, db: Any = Depends(get_db)):
    from .privacy import get_privacy_center, PrivacyRequestType
    center = get_privacy_center()
    req    = await center.submit_request(
        user_id      = body["user_id"],
        request_type = PrivacyRequestType(body["request_type"]),
        details      = body.get("details", {}),
        legal_basis  = body.get("legal_basis", ""),
    )
    return wrap(req.to_dict(), message="Privacy request submitted")


@router.patch("/privacy/requests/{request_id}")
async def process_privacy_request(request_id: str, body: dict, db: Any = Depends(get_db)):
    from .privacy import get_privacy_center, RequestStatus
    center = get_privacy_center()
    ok     = await center.process_request(
        request_id = request_id,
        status     = RequestStatus(body["status"]),
        response   = body.get("response", ""),
    )
    return wrap({"updated": ok})


# ── Compliance ────────────────────────────────────────────────────────────────

@router.get("/compliance/status")
async def compliance_status(framework: str | None = Query(None)):
    from .compliance import get_compliance, ComplianceFramework
    checker = get_compliance()
    fw      = ComplianceFramework(framework) if framework else None
    return wrap(checker.status(fw))


@router.get("/compliance/controls")
async def compliance_controls(
    framework: str | None = Query(None),
    status:    str | None = Query(None),
):
    from .compliance import get_compliance, ComplianceFramework, ComplianceStatus
    checker = get_compliance()
    fw      = ComplianceFramework(framework) if framework else None
    st      = ComplianceStatus(status) if status else None
    return wrap({"controls": checker.controls(fw, st)})


@router.get("/compliance/gaps")
async def compliance_gaps():
    from .compliance import get_compliance
    return wrap({"gaps": get_compliance().gaps()})


@router.get("/compliance/all-frameworks")
async def all_framework_status():
    from .compliance import get_compliance
    return wrap({"frameworks": get_compliance().all_frameworks()})


# ── Security monitoring ───────────────────────────────────────────────────────

@router.get("/monitoring/events")
async def list_security_events(
    subject_id: str | None = Query(None),
    event_type: str | None = Query(None),
    severity:   str | None = Query(None),
    limit:      int        = Query(100),
    db: Any = Depends(get_db),
):
    from .monitoring import get_monitor, AnomalyType, EventSeverity
    monitor = get_monitor()
    events  = await monitor.list_events(
        subject_id = subject_id,
        event_type = AnomalyType(event_type) if event_type else None,
        severity   = EventSeverity(severity) if severity else None,
        limit      = limit,
    )
    return wrap({"events": events, "total": len(events)})


@router.get("/monitoring/summary")
async def monitoring_summary():
    from .monitoring import get_monitor
    return wrap(get_monitor().summary())


@router.patch("/monitoring/events/{event_id}/resolve")
async def resolve_security_event(event_id: str, db: Any = Depends(get_db)):
    from .monitoring import get_monitor
    ok = await get_monitor().resolve_event(event_id)
    return wrap({"resolved": ok})


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def zt_dashboard():
    """Zero Trust security overview dashboard."""
    from .risk_engine import get_risk_engine
    from .ai_security import get_ai_security
    from .monitoring import get_monitor
    from .compliance import get_compliance

    return wrap({
        "risk":       get_risk_engine().stats(),
        "ai_security": get_ai_security().stats(),
        "monitoring": get_monitor().summary(),
        "compliance": get_compliance().status(),
    })
