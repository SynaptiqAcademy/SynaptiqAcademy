"""Research Ethics Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_ETHICS_RE      = re.compile(r"\bethics\s+(?:approval|committee|review|statement|board)\b|\birb\b|\binstitutional\s+review\b", re.IGNORECASE)
_CONSENT_RE     = re.compile(r"\binformed\s+consent\b|\bconsent\s+form\b|\bvoluntary\s+participation\b", re.IGNORECASE)
_PRIVACY_RE     = re.compile(r"\banonymis(?:ed|ation)\b|\bdeidentif\w+\b|\bpseudonyms?\b|\bprivacy\b|\bgdpr\b", re.IGNORECASE)
_CONFLICT_RE    = re.compile(r"\bconflict[s]?\s+of\s+interest\b|\bcompeting\s+interest\b|\bdisclosure\b", re.IGNORECASE)
_FUNDING_RE     = re.compile(r"\bfunding\b|\bsupported\s+by\b|\bgrant\s+(?:no|number|#)\b", re.IGNORECASE)
_DATA_SHARING_RE= re.compile(r"\bdata\s+(?:availability|access|sharing|open)\b|\brepository\b|\bosf\b", re.IGNORECASE)
_ANIMAL_RE      = re.compile(r"\banimal\s+(?:study|model|ethics|research|care)\b|\barrive\s+guidelines\b", re.IGNORECASE)
_HUMAN_RE       = re.compile(r"\bparticipant[s]?\b|\bsubject[s]?\b|\bpatient[s]?\b|\brespondent[s]?\b", re.IGNORECASE)


@AgentRegistry.register
class ResearchEthicsAgent(AcademicAgent):
    agent_id = "research_ethics_agent_v1"
    agent_type = AgentType.RESEARCH_ETHICS
    name = "Research Ethics Agent"
    domain = "Research Ethics & Compliance"
    capabilities = [
        "ethics_compliance_check", "consent_verification", "privacy_assessment",
        "conflict_of_interest_detection", "data_ethics_review",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content

        has_ethics      = bool(_ETHICS_RE.search(text))
        has_consent     = bool(_CONSENT_RE.search(text))
        has_privacy     = bool(_PRIVACY_RE.search(text))
        has_conflict    = bool(_CONFLICT_RE.search(text))
        has_funding     = bool(_FUNDING_RE.search(text))
        has_data_sharing= bool(_DATA_SHARING_RE.search(text))
        involves_animal = bool(_ANIMAL_RE.search(text))
        involves_human  = bool(_HUMAN_RE.search(text))

        issues: list[str] = []
        critical: list[str] = []

        if involves_human:
            if not has_ethics:
                critical.append("CRITICAL: Research involves humans — ethics/IRB approval not declared")
            if not has_consent:
                critical.append("CRITICAL: Informed consent statement missing")
            if not has_privacy:
                issues.append("Anonymisation/privacy statement missing")

        if involves_animal and not has_ethics:
            critical.append("CRITICAL: Animal research — ethics approval must be declared")

        if not has_conflict:
            issues.append("Conflict of interest statement missing")
        if not has_funding:
            issues.append("Funding acknowledgement missing")
        if not has_data_sharing and involves_human:
            issues.append("Data availability statement missing — declare where data can be accessed")

        compliance_score = (
            has_ethics * 0.30
            + has_consent * 0.20
            + has_privacy * 0.15
            + has_conflict * 0.15
            + has_funding * 0.10
            + has_data_sharing * 0.10
        )
        confidence = min(0.95, 0.35 + 0.6 * compliance_score)

        output = {
            "involves_human_participants": involves_human,
            "involves_animal_research": involves_animal,
            "has_ethics_approval": has_ethics,
            "has_informed_consent": has_consent,
            "has_privacy_protections": has_privacy,
            "has_conflict_statement": has_conflict,
            "has_funding_statement": has_funding,
            "has_data_availability": has_data_sharing,
            "compliance_score": round(compliance_score, 3),
            "critical_issues": critical,
            "compliance_issues": issues,
            "is_compliant": len(critical) == 0,
            "recommendations": [
                "Obtain and cite IRB/ethics committee approval before data collection",
                "Include a signed consent statement for all human participants",
                "Declare all competing interests (financial and non-financial)",
                "Deposit data in OSF/Zenodo/Dryad with a DOI",
                "Follow ARRIVE guidelines for animal research",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Ethics compliance score: {compliance_score:.0%}. "
                f"{len(critical)} critical issues, {len(issues)} minor issues."
            ),
            evidence=critical[:3] + issues[:3],
            t0=t0,
        )
