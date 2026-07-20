"""Research Gap Taxonomy — gap type definitions, keyword signals, scoring weights.

Rule-based detection uses these keyword signals to classify gaps from text.
The scoring engine uses the weights to compute overall opportunity scores.
"""
from __future__ import annotations

from .models import GapType, GapSeverity, CompetitionLevel

# ── Keyword signals per gap type ───────────────────────────────────────────────
# Used by rule_detector to classify text into gap types.
# Each list contains positive signals (any match triggers classification).

GAP_SIGNALS: dict[GapType, list[str]] = {
    GapType.THEORETICAL: [
        "theoretical framework", "conceptual model", "theory building", "paradigm",
        "ontology", "epistemology", "conceptual gap", "no unified theory", "lack of theory",
        "theoretical basis", "grounded theory", "conceptualisation",
    ],
    GapType.METHODOLOGICAL: [
        "methodological", "research design", "measurement instrument", "no gold standard",
        "validity", "reliability", "operationalisation", "measurement gap", "research method",
        "psychometric", "triangulation", "survey instrument", "scale development",
    ],
    GapType.EMPIRICAL: [
        "empirical evidence", "empirical study", "empirical data", "lack of evidence",
        "no empirical", "evidence gap", "experimental validation", "empirical test",
        "data-driven", "field study", "empirical research", "lack of empirical",
    ],
    GapType.PRACTICAL: [
        "practical application", "real-world implementation", "practitioner", "industry adoption",
        "practice gap", "implementation barrier", "applied research", "practical implication",
        "managerial implication", "policy implementation", "transfer to practice",
    ],
    GapType.TECHNOLOGICAL: [
        "technology gap", "technical barrier", "tool development", "software framework",
        "computational method", "algorithm", "technical limitation", "technology adoption",
        "digital infrastructure", "platform", "system development", "technological readiness",
    ],
    GapType.REGIONAL: [
        "region", "country", "geographic", "culture", "national context", "cross-cultural",
        "geographic gap", "developing countries", "global south", "under-represented region",
        "non-western", "local context", "cross-national", "cultural differences",
    ],
    GapType.POPULATION: [
        "population gap", "demographic", "under-served population", "minority", "age group",
        "gender", "ethnicity", "socioeconomic", "vulnerable population", "specific group",
        "patient population", "occupation group", "educational level",
    ],
    GapType.INDUSTRY: [
        "industry gap", "sector", "SME", "small business", "enterprise", "specific industry",
        "industrial application", "business context", "organizational", "firm-level",
        "market", "supply chain", "industry-specific", "sector analysis",
    ],
    GapType.TEMPORAL: [
        "longitudinal", "temporal", "long-term", "time series", "trend", "evolution over time",
        "diachronic", "historical", "trajectory", "panel data", "cohort", "follow-up study",
        "no longitudinal", "short-term studies only",
    ],
    GapType.POLICY: [
        "policy gap", "regulation", "governance", "legislation", "policy implication",
        "government", "public sector", "regulatory framework", "policy recommendation",
        "evidence-based policy", "policy evaluation", "policy design",
    ],
    GapType.EDUCATIONAL: [
        "education gap", "learning", "curriculum", "pedagogy", "training",
        "educational intervention", "instructional design", "student", "teacher",
        "higher education", "professional development", "competency",
    ],
    GapType.HEALTHCARE: [
        "clinical", "patient", "health outcome", "clinical trial", "clinical practice",
        "healthcare system", "clinical evidence", "treatment", "diagnosis", "prognosis",
        "healthcare gap", "medical", "clinical validation",
    ],
    GapType.DIGITAL_TRANSFORMATION: [
        "digital transformation", "digitalization", "digital strategy", "e-business",
        "online platform", "digital maturity", "digital adoption", "digital innovation",
        "Industry 4.0", "cyber-physical", "smart", "digitalisation",
    ],
    GapType.SUSTAINABILITY: [
        "sustainability", "sustainable development", "ESG", "environmental", "green",
        "carbon footprint", "circular economy", "climate change", "ecological",
        "social responsibility", "sustainable business", "net zero", "SDG",
    ],
    GapType.INNOVATION: [
        "innovation gap", "disruptive innovation", "open innovation", "knowledge transfer",
        "technology transfer", "R&D", "product development", "innovation management",
        "startup ecosystem", "entrepreneurship", "new product", "breakthrough",
    ],
    GapType.AI_GAP: [
        "artificial intelligence", "machine learning", "deep learning", "neural network",
        "natural language processing", "computer vision", "AI application", "LLM",
        "generative AI", "predictive model", "AI-assisted", "automated",
    ],
    GapType.INTERDISCIPLINARY: [
        "interdisciplinary", "cross-disciplinary", "multidisciplinary", "transdisciplinary",
        "multi-field", "bridge disciplines", "boundary spanning", "convergence",
        "interdisciplinary collaboration", "cross-sector", "multi-stakeholder",
    ],
    GapType.FUTURE_RESEARCH: [
        "future research", "future study", "future direction", "emerging area",
        "research agenda", "open question", "unexplored", "promising avenue",
        "next steps", "future investigation", "potential research", "research opportunity",
    ],
}


# ── Opportunity scoring weights ────────────────────────────────────────────────
# Must sum to 1.0

SCORE_WEIGHTS: dict[str, float] = {
    "novelty_score": 0.22,
    "publication_probability": 0.20,
    "research_impact": 0.15,
    "feasibility_score": 0.13,
    "funding_potential": 0.10,
    "citation_potential": 0.09,
    "interdisciplinary_potential": 0.05,
    "implementation_difficulty_inv": 0.03,    # 1 - difficulty
    "commercialization_potential": 0.03,
}

assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 0.01


# ── Gap type metadata ──────────────────────────────────────────────────────────

GAP_METADATA: dict[GapType, dict] = {
    GapType.THEORETICAL: {
        "label": "Theoretical Gap",
        "base_novelty": 0.80,
        "base_impact": 0.75,
        "base_funding": 0.55,
        "typical_design": "conceptual review or theory-building study",
        "description": "Missing or inadequate theoretical frameworks and conceptual models.",
    },
    GapType.METHODOLOGICAL: {
        "label": "Methodological Gap",
        "base_novelty": 0.70,
        "base_impact": 0.70,
        "base_funding": 0.50,
        "typical_design": "methodological research or scale development",
        "description": "Gaps in research methods, measurement instruments, or analytical approaches.",
    },
    GapType.EMPIRICAL: {
        "label": "Empirical Gap",
        "base_novelty": 0.60,
        "base_impact": 0.65,
        "base_funding": 0.60,
        "typical_design": "quantitative empirical study or field experiment",
        "description": "Absence of empirical evidence for theorised or assumed relationships.",
    },
    GapType.PRACTICAL: {
        "label": "Practical Gap",
        "base_novelty": 0.55,
        "base_impact": 0.72,
        "base_funding": 0.65,
        "typical_design": "case study or action research",
        "description": "Disconnect between academic knowledge and real-world practice.",
    },
    GapType.TECHNOLOGICAL: {
        "label": "Technological Gap",
        "base_novelty": 0.75,
        "base_impact": 0.70,
        "base_funding": 0.70,
        "typical_design": "design science research or prototype development",
        "description": "Missing technological tools, frameworks, or digital solutions.",
    },
    GapType.REGIONAL: {
        "label": "Regional Gap",
        "base_novelty": 0.65,
        "base_impact": 0.60,
        "base_funding": 0.55,
        "typical_design": "cross-national comparative study",
        "description": "Lack of research in specific geographic regions or cultural contexts.",
    },
    GapType.POPULATION: {
        "label": "Population Gap",
        "base_novelty": 0.65,
        "base_impact": 0.65,
        "base_funding": 0.60,
        "typical_design": "targeted survey or cohort study",
        "description": "Underrepresentation of specific demographic or population groups.",
    },
    GapType.INDUSTRY: {
        "label": "Industry Gap",
        "base_novelty": 0.60,
        "base_impact": 0.65,
        "base_funding": 0.65,
        "typical_design": "industry case study or multi-site survey",
        "description": "Missing research in specific industry sectors or business contexts.",
    },
    GapType.TEMPORAL: {
        "label": "Temporal Gap",
        "base_novelty": 0.62,
        "base_impact": 0.68,
        "base_funding": 0.52,
        "typical_design": "longitudinal cohort study",
        "description": "Absence of longitudinal data or time-series analysis.",
    },
    GapType.POLICY: {
        "label": "Policy Gap",
        "base_novelty": 0.58,
        "base_impact": 0.75,
        "base_funding": 0.80,
        "typical_design": "policy evaluation or Delphi study",
        "description": "Missing evidence to inform policy decisions or regulatory frameworks.",
    },
    GapType.EDUCATIONAL: {
        "label": "Educational Gap",
        "base_novelty": 0.60,
        "base_impact": 0.65,
        "base_funding": 0.65,
        "typical_design": "educational intervention study",
        "description": "Lack of research on educational programs, curricula, or training.",
    },
    GapType.HEALTHCARE: {
        "label": "Healthcare/Clinical Gap",
        "base_novelty": 0.65,
        "base_impact": 0.80,
        "base_funding": 0.85,
        "typical_design": "randomised controlled trial or clinical observational study",
        "description": "Missing clinical evidence for treatments, diagnoses, or health outcomes.",
    },
    GapType.DIGITAL_TRANSFORMATION: {
        "label": "Digital Transformation Gap",
        "base_novelty": 0.72,
        "base_impact": 0.70,
        "base_funding": 0.70,
        "typical_design": "survey-based or mixed-methods study in digital context",
        "description": "Lack of research on digitalization processes or digital adoption.",
    },
    GapType.SUSTAINABILITY: {
        "label": "Sustainability Gap",
        "base_novelty": 0.68,
        "base_impact": 0.75,
        "base_funding": 0.80,
        "typical_design": "multi-case study or life-cycle assessment",
        "description": "Missing research on sustainable practices, ESG, or environmental impact.",
    },
    GapType.INNOVATION: {
        "label": "Innovation Gap",
        "base_novelty": 0.75,
        "base_impact": 0.72,
        "base_funding": 0.72,
        "typical_design": "innovation study or R&D impact evaluation",
        "description": "Underexplored innovation mechanisms, knowledge transfer, or R&D processes.",
    },
    GapType.AI_GAP: {
        "label": "AI Research Gap",
        "base_novelty": 0.85,
        "base_impact": 0.78,
        "base_funding": 0.82,
        "typical_design": "experimental AI study or benchmark evaluation",
        "description": "Missing AI/ML applications, algorithms, or AI-augmented approaches.",
    },
    GapType.INTERDISCIPLINARY: {
        "label": "Interdisciplinary Gap",
        "base_novelty": 0.82,
        "base_impact": 0.78,
        "base_funding": 0.75,
        "typical_design": "interdisciplinary research project",
        "description": "Missing bridges between disciplines that study related phenomena separately.",
    },
    GapType.FUTURE_RESEARCH: {
        "label": "Future Research Opportunity",
        "base_novelty": 0.70,
        "base_impact": 0.65,
        "base_funding": 0.60,
        "typical_design": "exploratory or pilot study",
        "description": "Emerging research opportunities identified for future investigation.",
    },
}


# ── Severity thresholds ────────────────────────────────────────────────────────
# Maps opportunity score → severity classification

SEVERITY_THRESHOLDS: list[tuple[float, GapSeverity]] = [
    (0.80, GapSeverity.CRITICAL),
    (0.65, GapSeverity.HIGH),
    (0.45, GapSeverity.MEDIUM),
    (0.00, GapSeverity.LOW),
]


def score_to_severity(score: float) -> GapSeverity:
    for threshold, severity in SEVERITY_THRESHOLDS:
        if score >= threshold:
            return severity
    return GapSeverity.LOW


# ── Competition level estimation ───────────────────────────────────────────────
# Maps publication density signals → competition level

DENSITY_COMPETITION: dict[str, CompetitionLevel] = {
    "saturated": CompetitionLevel.VERY_HIGH,
    "dense": CompetitionLevel.HIGH,
    "moderate": CompetitionLevel.MEDIUM,
    "sparse": CompetitionLevel.LOW,
}
