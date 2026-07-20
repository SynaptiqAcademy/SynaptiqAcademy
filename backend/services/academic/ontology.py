"""Academic ontology — taxonomy constants, keyword maps, and reasoning frameworks.

All classification rules and feature-specific guidance live here.
The engine reads this file to know HOW to reason about each feature and domain.
"""
from __future__ import annotations

from services.academic.models import (
    AcademicDomain, MethodologyType, ResearchDesign, WeaknessType,
)


# ── Domain keyword mapping ─────────────────────────────────────────────────────

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    AcademicDomain.COMPUTER_SCIENCE.value: [
        "algorithm", "neural network", "deep learning", "machine learning", "AI", "artificial intelligence",
        "software", "model", "dataset", "accuracy", "benchmark", "architecture", "training",
        "classification", "detection", "segmentation", "NLP", "computer vision", "reinforcement learning",
        "optimization", "performance", "computational", "transformer", "LLM", "embedding",
        "BERT", "GPT", "CNN", "RNN", "GAN", "attention", "encoder", "decoder",
    ],
    AcademicDomain.MEDICINE_HEALTH.value: [
        "patient", "clinical", "treatment", "diagnosis", "hospital", "drug", "therapy",
        "randomized", "controlled trial", "RCT", "cohort", "survival", "mortality",
        "prevalence", "incidence", "risk factor", "intervention", "placebo", "double-blind",
        "healthcare", "medical", "disease", "chronic", "acute", "symptom", "biomarker",
        "MRI", "CT scan", "biopsy", "surgery", "pharmaceutical",
    ],
    AcademicDomain.SOCIAL_SCIENCES.value: [
        "society", "culture", "behavior", "attitude", "perception", "social", "community",
        "interview", "focus group", "ethnography", "qualitative", "thematic analysis",
        "grounded theory", "discourse", "narrative", "identity", "inequality", "gender",
        "race", "policy", "governance", "organization", "institution",
    ],
    AcademicDomain.EDUCATION.value: [
        "student", "teacher", "learning", "curriculum", "pedagogy", "school", "university",
        "assessment", "performance", "motivation", "engagement", "teaching", "classroom",
        "higher education", "e-learning", "blended learning", "STEM",
    ],
    AcademicDomain.ENGINEERING.value: [
        "design", "system", "prototype", "implementation", "simulation", "hardware",
        "sensor", "IoT", "circuit", "signal", "mechanical", "structural", "electrical",
        "thermal", "fluid", "manufacturing", "material", "tensile", "fatigue",
    ],
    AcademicDomain.BUSINESS_MANAGEMENT.value: [
        "organization", "management", "strategy", "performance", "leadership", "firm",
        "market", "revenue", "ROI", "customer", "supply chain", "innovation",
        "entrepreneurship", "startup", "competitive advantage", "stakeholder",
    ],
    AcademicDomain.NATURAL_SCIENCES.value: [
        "experiment", "specimen", "species", "biology", "chemistry", "physics",
        "reaction", "compound", "molecule", "cell", "gene", "protein", "evolution",
        "ecology", "climate", "atmosphere", "geology",
    ],
    AcademicDomain.PSYCHOLOGY.value: [
        "cognitive", "behavior", "emotion", "perception", "personality", "mental health",
        "depression", "anxiety", "stress", "wellbeing", "therapy", "psychotherapy",
        "CBT", "psychometric", "scale", "inventory",
    ],
    AcademicDomain.ECONOMICS.value: [
        "GDP", "inflation", "market", "monetary", "fiscal", "macroeconomic", "microeconomic",
        "elasticity", "demand", "supply", "equilibrium", "regression", "panel data",
        "econometric", "income", "wealth",
    ],
}

# ── Methodology keyword mapping ────────────────────────────────────────────────

METHODOLOGY_KEYWORDS: dict[str, list[str]] = {
    MethodologyType.QUANTITATIVE.value: [
        "survey", "questionnaire", "statistical", "regression", "ANOVA", "t-test",
        "chi-square", "correlation", "factor analysis", "SEM", "random sample",
        "population", "n=", "participants", "hypothesis testing", "p-value", "significance",
        "mean", "standard deviation", "confidence interval",
    ],
    MethodologyType.QUALITATIVE.value: [
        "interview", "focus group", "observation", "ethnography", "thematic analysis",
        "grounded theory", "discourse analysis", "narrative inquiry", "case study",
        "phenomenology", "coding", "themes", "saturation", "purposive sampling",
    ],
    MethodologyType.MIXED_METHODS.value: [
        "mixed methods", "triangulation", "convergent", "sequential explanatory",
        "sequential exploratory", "concurrent", "quantitative and qualitative",
    ],
    MethodologyType.EXPERIMENTAL.value: [
        "experiment", "controlled", "treatment group", "control group", "randomization",
        "intervention", "pre-test", "post-test", "baseline", "manipulation",
    ],
    MethodologyType.COMPUTATIONAL.value: [
        "simulation", "model", "algorithm", "dataset", "training", "validation",
        "test set", "cross-validation", "hyperparameter", "GPU", "training epochs",
    ],
}

DESIGN_KEYWORDS: dict[str, list[str]] = {
    ResearchDesign.RANDOMIZED_CONTROLLED_TRIAL.value: [
        "randomized controlled trial", "RCT", "randomization", "allocation", "blinding",
        "placebo", "double-blind", "single-blind", "CONSORT",
    ],
    ResearchDesign.SYSTEMATIC_REVIEW.value: [
        "systematic review", "PRISMA", "inclusion criteria", "exclusion criteria",
        "database search", "Cochrane", "evidence synthesis",
    ],
    ResearchDesign.META_ANALYSIS.value: [
        "meta-analysis", "effect size", "heterogeneity", "I-squared", "forest plot",
        "funnel plot", "publication bias",
    ],
    ResearchDesign.SURVEY.value: [
        "survey", "questionnaire", "Likert scale", "cross-sectional", "response rate",
        "pilot test",
    ],
    ResearchDesign.CASE_STUDY.value: [
        "case study", "single case", "multiple case", "embedded", "holistic",
        "Yin", "within-case", "cross-case",
    ],
    ResearchDesign.GROUNDED_THEORY.value: [
        "grounded theory", "open coding", "axial coding", "selective coding",
        "constant comparison", "theoretical saturation", "memoing",
    ],
}

# ── Structural section keywords ────────────────────────────────────────────────

SECTION_KEYWORDS: dict[str, list[str]] = {
    "abstract": ["abstract", "summary"],
    "introduction": ["introduction", "background", "motivation", "context"],
    "hypothesis": ["hypothesis", "we hypothesize", "we propose", "research question",
                   "the aim", "this study aims", "objective"],
    "literature_review": ["related work", "literature review", "background", "prior work",
                          "previous studies", "existing research"],
    "methodology": ["methodology", "methods", "materials and methods", "research design",
                    "data collection", "participants", "procedure", "instruments"],
    "results": ["results", "findings", "outcomes", "experiments"],
    "discussion": ["discussion", "interpretation", "implications"],
    "limitations": ["limitation", "limitations", "not generalizable", "boundary"],
    "conclusion": ["conclusion", "concluding", "in conclusion", "summary"],
    "future_work": ["future work", "future research", "future studies", "next steps"],
    "ethics": ["ethics", "ethical approval", "IRB", "Helsinki", "consent"],
    "conflicts_of_interest": ["conflict of interest", "declaration", "competing interests"],
    "data_availability": ["data availability", "data access", "code availability",
                          "reproducibility", "GitHub", "Zenodo"],
}

# ── Reasoning frameworks per feature ──────────────────────────────────────────
# Each entry is injected into the system prompt as structured guidance.

FEATURE_REASONING_FRAMEWORKS: dict[str, str] = {
    "manuscript_review": """You are reviewing as a senior journal editor and peer reviewer.
Apply IMRAD structure validation. Evaluate:
1. Research question clarity and significance
2. Methodology rigor and appropriateness
3. Statistical analysis correctness
4. Results-conclusions alignment
5. Discussion depth and interpretation
6. Limitations acknowledgment
7. Novelty and contribution to the field
8. Writing quality and academic tone
9. Reference completeness and recency
10. Ethical compliance""",

    "literature_review": """You are synthesizing literature as a senior researcher.
Apply systematic review principles. Evaluate:
1. Comprehensiveness of coverage
2. Quality of source selection
3. Critical analysis (not just description)
4. Identification of gaps and contradictions
5. Temporal coverage (recent + foundational works)
6. Thematic organization
7. Synthesis and comparison across studies
8. Clear research gap articulation
9. Future research directions""",

    "research_gap_finder": """You are identifying research gaps as a domain expert.
Apply structured gap analysis. Look for:
1. Methodological gaps (understudied approaches)
2. Population/sample gaps (unstudied groups)
3. Geographical gaps (understudied regions)
4. Temporal gaps (short-term vs. long-term studies)
5. Theoretical gaps (missing frameworks)
6. Application gaps (theory-to-practice)
7. Interdisciplinary gaps
8. Replication/validation gaps""",

    "statistical_review": """You are reviewing statistical methods as a biostatistician.
Evaluate:
1. Appropriate test selection for data type and distribution
2. Sample size and statistical power
3. Effect size reporting (Cohen's d, r, η²)
4. Confidence intervals (not just p-values)
5. Multiple comparisons correction
6. Assumptions testing (normality, homoscedasticity)
7. Missing data handling
8. Reproducibility (random seeds, software versions)
9. Visual representation of data""",

    "research_design_advisor": """You are advising on research design as a methodology expert.
Evaluate alignment between:
1. Research question and design type
2. Design and data collection methods
3. Sampling strategy and population
4. Variables (independent, dependent, confounders)
5. Internal validity threats (bias, confounding)
6. External validity (generalizability)
7. Feasibility (time, resources, access)
8. Ethical considerations""",

    "abstract_generator": """You are writing/reviewing an academic abstract.
Apply IMRAD-abstract structure:
1. Background/Context (1-2 sentences)
2. Objective/Aim (1 sentence)
3. Methods summary (2-3 sentences)
4. Key results with statistics (2-3 sentences)
5. Conclusion and implications (1-2 sentences)
Keywords: 4-6 terms matching indexed vocabulary""",

    "journal_matching": """You are recommending journals as an experienced author.
Match based on:
1. Scope and aims alignment
2. Audience fit (practitioners vs. academics)
3. Impact factor and ranking (Q1-Q4, SJR, Scopus)
4. Submission requirements (word limit, open access)
5. Rejection risk (based on quality match)
6. Time to first decision and publication
7. Special issues and thematic fit""",

    "conference_matching": """You are recommending conferences as a senior researcher.
Match based on:
1. Topical alignment (main tracks and workshops)
2. Prestige tier (A*, A, B, C for CS; H-index for others)
3. Submission deadline and timeline
4. Acceptance rate
5. Networking opportunity
6. Location and travel feasibility
7. Proceedings indexing (IEEE, ACM, Springer)""",

    "grant_matching": """You are advising on grant applications as a research office expert.
Evaluate alignment with:
1. Funding agency priorities and strategic objectives
2. Eligibility requirements (PI qualifications, institution type)
3. Project budget and duration fit
4. Methodology and impact alignment
5. Collaboration requirements
6. Novelty and transformative potential
7. Track record requirements""",

    "grant_gap_detection": """You are identifying gaps in a grant application as a program officer.
Check for:
1. Clear problem statement and significance
2. Measurable objectives and milestones
3. Feasibility (team capacity, timeline, budget)
4. Innovation and novelty justification
5. Impact pathway and dissemination plan
6. Risk management and contingency
7. Ethical compliance statement
8. Budget justification completeness""",

    "teaching_lesson_generation": """You are creating educational content as a curriculum designer.
Apply backward design principles:
1. Learning objectives (Bloom's taxonomy)
2. Assessment alignment
3. Content scaffolding
4. Active learning elements
5. Differentiation for diverse learners
6. Formative assessment checkpoints
7. Real-world application examples""",

    "teaching_assessment_generation": """You are designing assessment as an educational measurement expert.
Apply:
1. Validity (measures intended learning outcomes)
2. Reliability (consistent results)
3. Authenticity (real-world tasks)
4. Rubric clarity and transparency
5. Bloom's taxonomy alignment
6. Accessibility and inclusivity
7. Academic integrity safeguards""",

    "collaboration_intelligence": """You are analyzing research collaboration as an innovation strategist.
Evaluate:
1. Complementarity of expertise
2. Publication overlap and common ground
3. Institutional diversity
4. Geographic diversity
5. Track record of collaborative work
6. Grant compatibility
7. Communication and timezone factors""",

    "ai_assistant": """You are assisting academic research with expert knowledge.
Always:
1. Provide evidence-based responses
2. Cite principles, frameworks, or guidelines
3. Distinguish between established knowledge and speculation
4. Suggest next steps or resources
5. Flag uncertainties explicitly""",

    "ai_chat": """You are an academic research assistant.
Maintain:
1. Academic tone and precision
2. Evidence-based claims
3. Appropriate hedging for uncertain claims
4. Reference to established frameworks where relevant
5. Practical, actionable guidance""",

    "general": """Respond with academic rigor appropriate for a research context.
Use precise language, support claims with reasoning, and maintain scholarly standards.""",
}

# Default for features without a specific framework
_DEFAULT_FRAMEWORK = FEATURE_REASONING_FRAMEWORKS["general"]

# ── Quality thresholds per feature ─────────────────────────────────────────────

FEATURE_QUALITY_THRESHOLDS: dict[str, float] = {
    "manuscript_review": 0.78,
    "literature_review": 0.75,
    "research_gap_finder": 0.72,
    "statistical_review": 0.80,
    "research_design_advisor": 0.75,
    "abstract_generator": 0.72,
    "journal_matching": 0.70,
    "conference_matching": 0.68,
    "grant_matching": 0.72,
    "grant_gap_detection": 0.75,
    "teaching_lesson_generation": 0.70,
    "teaching_assessment_generation": 0.72,
    "collaboration_intelligence": 0.68,
    "ai_assistant": 0.65,
    "ai_chat": 0.60,
    "summarization": 0.65,
    "academic_proofreading": 0.70,
    "academic_tone": 0.68,
    "paraphrasing": 0.65,
    "writing_improvement": 0.68,
}
_DEFAULT_QUALITY_THRESHOLD = 0.65

# ── Academic feature set (all features that trigger AIE enrichment) ────────────

ACADEMIC_FEATURES: frozenset[str] = frozenset({
    "research_gap_finder", "literature_review", "manuscript_review",
    "statistical_review", "research_design_advisor", "abstract_generator",
    "collaboration_intelligence", "ai_assistant", "ai_chat",
    "journal_matching", "conference_matching", "grant_matching",
    "reviewer_matching", "teaching_lesson_generation",
    "teaching_assessment_generation", "teaching_assistant",
    "grant_gap_detection", "recommendation_engine",
    "research_brainstorming", "academic_proofreading",
    "academic_tone", "writing_improvement",
    "plain_language_explanation", "summarization",
})


def get_reasoning_framework(feature: str) -> str:
    return FEATURE_REASONING_FRAMEWORKS.get(feature, _DEFAULT_FRAMEWORK)


def get_quality_threshold(feature: str) -> float:
    return FEATURE_QUALITY_THRESHOLDS.get(feature, _DEFAULT_QUALITY_THRESHOLD)
