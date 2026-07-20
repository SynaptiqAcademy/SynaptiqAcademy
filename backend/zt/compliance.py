"""
Compliance Framework — Phase XXXV.8

Readiness checks for GDPR, FERPA, ISO 27001, SOC 2, NIS2, and Research Data Governance.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    GDPR     = "GDPR"
    FERPA    = "FERPA"
    ISO27001 = "ISO27001"
    SOC2     = "SOC2"
    NIS2     = "NIS2"
    RDG      = "RDG"     # Research Data Governance


class ComplianceStatus(str, Enum):
    COMPLIANT     = "compliant"
    PARTIAL       = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED  = "not_assessed"


@dataclass
class ComplianceControl:
    control_id:  str
    name:        str
    framework:   ComplianceFramework
    description: str
    status:      ComplianceStatus  = ComplianceStatus.NOT_ASSESSED
    evidence:    list[str]         = field(default_factory=list)
    gap:         str               = ""

    def to_dict(self) -> dict:
        return {
            "control_id":  self.control_id,
            "name":        self.name,
            "framework":   self.framework,
            "description": self.description,
            "status":      self.status,
            "evidence":    self.evidence,
            "gap":         self.gap,
        }


# ── Built-in controls ─────────────────────────────────────────────────────────

_CONTROLS: list[ComplianceControl] = [
    # GDPR
    ComplianceControl("GDPR-01", "Lawful Basis", ComplianceFramework.GDPR,
        "Processing has documented lawful basis", ComplianceStatus.COMPLIANT,
        evidence=["consent_records collection", "user registration consent flow"]),
    ComplianceControl("GDPR-02", "Data Minimisation", ComplianceFramework.GDPR,
        "Only necessary data collected", ComplianceStatus.COMPLIANT,
        evidence=["registration form limited to essential fields"]),
    ComplianceControl("GDPR-03", "Data Subject Rights", ComplianceFramework.GDPR,
        "Access, portability, erasure, rectification implemented", ComplianceStatus.COMPLIANT,
        evidence=["PrivacyCenter endpoints", "zt_privacy_requests collection"]),
    ComplianceControl("GDPR-04", "Immutable Audit Log", ComplianceFramework.GDPR,
        "Processing activities logged and immutable", ComplianceStatus.COMPLIANT,
        evidence=["obs_audit collection (no TTL)", "zt_audit collection"]),
    ComplianceControl("GDPR-05", "Encryption at Rest", ComplianceFramework.GDPR,
        "Personal data encrypted at rest", ComplianceStatus.PARTIAL,
        evidence=["EncryptionEngine field-level encryption"],
        gap="Database-level encryption requires Atlas M10+ cluster"),
    ComplianceControl("GDPR-06", "Data Retention Policy", ComplianceFramework.GDPR,
        "Retention periods defined and enforced", ComplianceStatus.PARTIAL,
        evidence=["DataClassifier max_retention_days per level"],
        gap="Automated deletion scheduler not yet implemented"),
    ComplianceControl("GDPR-07", "Breach Notification", ComplianceFramework.GDPR,
        "Security breach detection and 72h notification capability", ComplianceStatus.PARTIAL,
        evidence=["SecurityMonitor anomaly detection", "obs/security event tracking"],
        gap="External DPA notification workflow not automated"),

    # FERPA
    ComplianceControl("FERPA-01", "Education Record Protection", ComplianceFramework.FERPA,
        "Student education records protected", ComplianceStatus.COMPLIANT,
        evidence=["student role field restrictions", "PERSONAL classification on user data"]),
    ComplianceControl("FERPA-02", "Parent/Guardian Access Control", ComplianceFramework.FERPA,
        "Access transfer when student reaches 18", ComplianceStatus.NOT_ASSESSED,
        gap="Age-based access transfer not implemented"),
    ComplianceControl("FERPA-03", "Directory Information Policy", ComplianceFramework.FERPA,
        "Directory information opt-out capability", ComplianceStatus.PARTIAL,
        evidence=["profile_visibility field on users"],
        gap="FERPA-specific directory opt-out UI not added"),

    # ISO 27001
    ComplianceControl("ISO-A.5", "Information Security Policy", ComplianceFramework.ISO27001,
        "Security policy documented", ComplianceStatus.COMPLIANT,
        evidence=["Zero Trust policy engine", "zt_policies collection"]),
    ComplianceControl("ISO-A.8", "Asset Management", ComplianceFramework.ISO27001,
        "Data assets classified and inventoried", ComplianceStatus.COMPLIANT,
        evidence=["DataClassifier 10 classification levels", "zt_governance collection"]),
    ComplianceControl("ISO-A.9", "Access Control", ComplianceFramework.ISO27001,
        "Role-based access with least privilege", ComplianceStatus.COMPLIANT,
        evidence=["AuthorizationEngine RBAC + ABAC", "12 identity types"]),
    ComplianceControl("ISO-A.10", "Cryptography", ComplianceFramework.ISO27001,
        "Encryption in transit and at rest", ComplianceStatus.COMPLIANT,
        evidence=["Fernet AES-256 field encryption", "HTTPS enforced via SecurityHeadersMiddleware"]),
    ComplianceControl("ISO-A.12", "Operations Security", ComplianceFramework.ISO27001,
        "Operational monitoring and logging", ComplianceStatus.COMPLIANT,
        evidence=["obs/ observability platform", "structured logging", "distributed tracing"]),
    ComplianceControl("ISO-A.16", "Incident Management", ComplianceFramework.ISO27001,
        "Security incident detection and response", ComplianceStatus.PARTIAL,
        evidence=["AlertEngine 12 built-in rules", "SecurityMonitor"],
        gap="Formal incident response playbooks not automated"),

    # SOC 2
    ComplianceControl("SOC2-CC6", "Logical and Physical Access", ComplianceFramework.SOC2,
        "Access controls with MFA and session management", ComplianceStatus.COMPLIANT,
        evidence=["admin_mfa router", "trusted_devices collection", "session management"]),
    ComplianceControl("SOC2-CC7", "System Operations Monitoring", ComplianceFramework.SOC2,
        "Continuous monitoring for anomalies", ComplianceStatus.COMPLIANT,
        evidence=["HealthEngine 12 checkers", "RiskEngine", "SecurityMonitor"]),
    ComplianceControl("SOC2-CC8", "Change Management", ComplianceFramework.SOC2,
        "Changes tracked and audited", ComplianceStatus.COMPLIANT,
        evidence=["obs_audit immutable log", "zt_audit collection"]),
    ComplianceControl("SOC2-CC9", "Risk Mitigation", ComplianceFramework.SOC2,
        "Risk assessment and mitigation", ComplianceStatus.COMPLIANT,
        evidence=["RiskEngine dynamic scoring", "PolicyEngine", "AISecurityEngine"]),

    # NIS2
    ComplianceControl("NIS2-01", "Network Security", ComplianceFramework.NIS2,
        "Network segmentation and access control", ComplianceStatus.PARTIAL,
        evidence=["IP allowlist (admin_hardening)", "CORS policy"],
        gap="Network-level segmentation is infrastructure concern"),
    ComplianceControl("NIS2-02", "Incident Reporting", ComplianceFramework.NIS2,
        "24/72h incident reporting capability", ComplianceStatus.PARTIAL,
        gap="Automated NIS2 authority notification not implemented"),
    ComplianceControl("NIS2-03", "Supply Chain Security", ComplianceFramework.NIS2,
        "Third-party and dependency security", ComplianceStatus.PARTIAL,
        evidence=["API key security", "webhook HMAC verification"],
        gap="SBOM and vendor risk assessment process not documented"),

    # Research Data Governance
    ComplianceControl("RDG-01", "Research Data Lineage", ComplianceFramework.RDG,
        "Full lineage tracking for research outputs", ComplianceStatus.COMPLIANT,
        evidence=["DataGovernanceEngine", "zt_lineage collection", "AI evidence tracking"]),
    ComplianceControl("RDG-02", "AI Output Evidence", ComplianceFramework.RDG,
        "All AI outputs have evidence chain", ComplianceStatus.COMPLIANT,
        evidence=["evidence[] required on all AI recommendations", "confidence basis required"]),
    ComplianceControl("RDG-03", "Human Approval for Scientific Decisions", ComplianceFramework.RDG,
        "Agents cannot publish conclusions without human approval", ComplianceStatus.COMPLIANT,
        evidence=["AUTONOMY SAFETY POLICY enforced in all agent code", "approval workflows"]),
]


class ComplianceChecker:

    def __init__(self) -> None:
        self._controls = list(_CONTROLS)

    def status(self, framework: ComplianceFramework | None = None) -> dict:
        controls = self._controls
        if framework:
            controls = [c for c in controls if c.framework == framework]

        total     = len(controls)
        compliant = sum(1 for c in controls if c.status == ComplianceStatus.COMPLIANT)
        partial   = sum(1 for c in controls if c.status == ComplianceStatus.PARTIAL)
        non_comp  = sum(1 for c in controls if c.status == ComplianceStatus.NON_COMPLIANT)
        not_ass   = sum(1 for c in controls if c.status == ComplianceStatus.NOT_ASSESSED)

        score_pct = round(((compliant + 0.5 * partial) / total * 100), 1) if total else 0
        overall   = (
            ComplianceStatus.COMPLIANT if score_pct >= 90 else
            ComplianceStatus.PARTIAL   if score_pct >= 50 else
            ComplianceStatus.NON_COMPLIANT
        )

        return {
            "framework":    framework or "ALL",
            "total":        total,
            "compliant":    compliant,
            "partial":      partial,
            "non_compliant":non_comp,
            "not_assessed": not_ass,
            "score_pct":    score_pct,
            "overall":      overall,
            "assessed_at":  datetime.now(timezone.utc).isoformat(),
        }

    def controls(
        self,
        framework: ComplianceFramework | None = None,
        status:    ComplianceStatus | None    = None,
    ) -> list[dict]:
        result = self._controls
        if framework:
            result = [c for c in result if c.framework == framework]
        if status:
            result = [c for c in result if c.status == status]
        return [c.to_dict() for c in result]

    def gaps(self) -> list[dict]:
        return [
            c.to_dict() for c in self._controls
            if c.gap and c.status != ComplianceStatus.COMPLIANT
        ]

    def all_frameworks(self) -> list[dict]:
        return [self.status(f) for f in ComplianceFramework]


# ── Singleton ─────────────────────────────────────────────────────────────────

_checker: ComplianceChecker | None = None


def get_compliance() -> ComplianceChecker:
    global _checker
    if _checker is None:
        _checker = ComplianceChecker()
    return _checker
