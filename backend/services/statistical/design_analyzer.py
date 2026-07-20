"""Statistical Intelligence 2.0 — Research design analyzer (Phase X).

Identifies study type, variables (DV/IV/control), moderators, mediators,
sampling strategy and research discipline from text and parsed data.
"""
from __future__ import annotations

import re
from .models import AnalysisMethod, ParsedData, ResearchDesign, StudyType

# ── Study type signals ────────────────────────────────────────────────────────

_STUDY_SIGNALS: list[tuple[StudyType, list[str]]] = [
    (StudyType.RCT,               ["randomized controlled trial", "rct", "randomly assigned",
                                    "random allocation", "double-blind", "placebo"]),
    (StudyType.EXPERIMENTAL,      ["experimental design", "laboratory experiment",
                                    "controlled experiment", "treatment group", "control group"]),
    (StudyType.QUASI_EXPERIMENTAL,["quasi-experimental", "quasi experimental",
                                    "non-randomized", "nonequivalent groups"]),
    (StudyType.LONGITUDINAL,      ["longitudinal", "panel data", "repeated measures",
                                    "follow-up", "prospective", "time series", "over time"]),
    (StudyType.COHORT,            ["cohort study", "cohort design", "prospective cohort",
                                    "retrospective cohort"]),
    (StudyType.CASE_CONTROL,      ["case-control", "case control", "odds ratio",
                                    "cases and controls"]),
    (StudyType.META_ANALYSIS,     ["meta-analysis", "meta analysis", "pooled effect",
                                    "systematic review and meta"]),
    (StudyType.SYSTEMATIC_REVIEW, ["systematic review", "literature review",
                                    "scoping review", "narrative review"]),
    (StudyType.MIXED_METHODS,     ["mixed methods", "mixed-methods", "quantitative and qualitative",
                                    "convergent design", "sequential design"]),
    (StudyType.SURVEY,            ["survey", "questionnaire", "self-reported",
                                    "self-report", "likert scale", "cross-sectional survey"]),
    (StudyType.CROSS_SECTIONAL,   ["cross-sectional", "cross sectional", "at a single point",
                                    "one-time data collection"]),
    (StudyType.QUALITATIVE,       ["qualitative", "grounded theory", "thematic analysis",
                                    "phenomenological", "ethnographic", "interview"]),
    (StudyType.OBSERVATIONAL,     ["observational study", "naturalistic", "no intervention",
                                    "without intervention"]),
    (StudyType.CASE_STUDY,        ["case study", "single case", "multiple case",
                                    "instrumental case"]),
]

# ── Method detection patterns ─────────────────────────────────────────────────

_METHOD_PATTERNS: list[tuple[AnalysisMethod, list[str]]] = [
    (AnalysisMethod.PLS_SEM,            ["pls-sem", "pls sem", "partial least squares sem",
                                          "smartpls", "pls path"]),
    (AnalysisMethod.SEM,                ["structural equation model", "sem", "lisrel", "amos",
                                          "latent variable", "path analysis"]),
    (AnalysisMethod.CFA,                ["confirmatory factor analysis", "cfa",
                                          "measurement model", "factor loading"]),
    (AnalysisMethod.FACTOR_ANALYSIS,    ["exploratory factor analysis", "efa", "factor analysis",
                                          "principal axis factoring", "kmo", "bartlett"]),
    (AnalysisMethod.PCA,                ["principal component analysis", "pca",
                                          "dimensionality reduction", "principal components"]),
    (AnalysisMethod.LOGISTIC_REGRESSION,["logistic regression", "logit", "binary logistic",
                                          "multinomial logistic", "odds ratio"]),
    (AnalysisMethod.ORDINAL_REGRESSION, ["ordinal regression", "ordered logit",
                                          "proportional odds"]),
    (AnalysisMethod.MULTIPLE_REGRESSION,["multiple regression", "multiple linear regression",
                                          "ordinary least squares", "ols regression",
                                          "hierarchical regression", "stepwise regression"]),
    (AnalysisMethod.LINEAR_REGRESSION,  ["linear regression", "simple regression",
                                          "slr", "bivariate regression"]),
    (AnalysisMethod.MIXED_MODELS,       ["linear mixed model", "mixed effects", "multilevel",
                                          "hierarchical linear model", "hlm", "lme4"]),
    (AnalysisMethod.MANOVA,             ["manova", "multivariate analysis of variance"]),
    (AnalysisMethod.ANCOVA,             ["ancova", "analysis of covariance"]),
    (AnalysisMethod.REPEATED_ANOVA,     ["repeated measures anova", "within-subjects anova",
                                          "rm-anova", "sphericity"]),
    (AnalysisMethod.ANOVA,              ["anova", "analysis of variance", "one-way anova",
                                          "two-way anova", "factorial anova", "f-test"]),
    (AnalysisMethod.PAIRED_T_TEST,      ["paired t-test", "paired t test", "dependent t-test",
                                          "paired samples t"]),
    (AnalysisMethod.ONE_SAMPLE_T,       ["one-sample t", "one sample t-test"]),
    (AnalysisMethod.T_TEST,             ["t-test", "t test", "student's t", "independent samples t",
                                          "two-sample t"]),
    (AnalysisMethod.FISHER_EXACT,       ["fisher's exact", "fisher exact"]),
    (AnalysisMethod.CHI_SQUARE,         ["chi-square", "chi square", "χ²", "chi²",
                                          "contingency table", "cross-tabulation"]),
    (AnalysisMethod.SPEARMAN_CORRELATION,["spearman", "rank correlation", "ρ =", "rho ="]),
    (AnalysisMethod.PEARSON_CORRELATION, ["pearson", "correlation coefficient", "r =",
                                           "pearson r"]),
    (AnalysisMethod.SURVIVAL_ANALYSIS,  ["survival analysis", "kaplan-meier", "cox regression",
                                          "hazard ratio", "time-to-event"]),
    (AnalysisMethod.TIME_SERIES,        ["time series", "arima", "autoregressive",
                                          "stationarity", "acf", "pacf"]),
    (AnalysisMethod.CLUSTER_ANALYSIS,   ["cluster analysis", "k-means", "hierarchical clustering",
                                          "dendrogram", "ward's method"]),
    (AnalysisMethod.META_ANALYSIS,      ["meta-analysis", "pooled effect", "forest plot",
                                          "heterogeneity i²", "funnel plot"]),
    (AnalysisMethod.MANN_WHITNEY,       ["mann-whitney", "mann whitney", "wilcoxon rank-sum"]),
    (AnalysisMethod.KRUSKAL_WALLIS,     ["kruskal-wallis", "kruskal wallis"]),
    (AnalysisMethod.WILCOXON,           ["wilcoxon signed-rank", "wilcoxon test"]),
    (AnalysisMethod.FRIEDMAN,           ["friedman test", "friedman's anova"]),
    (AnalysisMethod.BAYESIAN,           ["bayesian", "bayes factor", "posterior distribution",
                                          "credible interval", "mcmc"]),
    (AnalysisMethod.MACHINE_LEARNING,   ["machine learning", "random forest", "neural network",
                                          "gradient boosting", "svm", "deep learning", "xgboost"]),
]

# ── Variable patterns ─────────────────────────────────────────────────────────

_DV_SIGNALS = re.compile(
    r"(?:dependent variable[s]?|outcome variable[s]?|response variable[s]?|"
    r"criterion variable[s]?|dv\b)[:\s]+([^\n.]+)", re.IGNORECASE
)
_IV_SIGNALS = re.compile(
    r"(?:independent variable[s]?|predictor[s]?|explanatory variable[s]?|"
    r"iv\b|regressor[s]?)[:\s]+([^\n.]+)", re.IGNORECASE
)
_MODERATOR_RE = re.compile(r"moderator[s]?[:\s]+([^\n.]+)", re.IGNORECASE)
_MEDIATOR_RE = re.compile(r"mediator[s]?[:\s]+([^\n.]+)", re.IGNORECASE)
_CONFOUNDER_RE = re.compile(r"confounder[s]?|covariate[s]?[:\s]+([^\n.]+)", re.IGNORECASE)

_SAMPLE_SIZE_RE = re.compile(r"\b[Nn]\s*[=:]\s*([\d,]+)")

_SAMPLING_PATTERNS: list[tuple[str, list[str]]] = [
    ("random sampling",       ["random sample", "simple random", "systematic random"]),
    ("stratified sampling",   ["stratified", "proportional stratified"]),
    ("cluster sampling",      ["cluster sampling", "cluster sample"]),
    ("purposive sampling",    ["purposive", "purposeful", "judgmental sampling"]),
    ("convenience sampling",  ["convenience sampling", "convenient sample", "availability sampling"]),
    ("snowball sampling",     ["snowball", "chain-referral"]),
    ("census",                ["entire population", "census", "all members"]),
]

_DISCIPLINE_SIGNALS: dict[str, list[str]] = {
    "medicine":    ["patient", "clinical", "treatment", "disease", "hospital", "diagnosis",
                    "mortality", "survival", "therapy", "physician"],
    "psychology":  ["behavior", "behaviour", "cognitive", "anxiety", "depression",
                    "personality", "mental health", "well-being", "attitude"],
    "education":   ["student", "academic performance", "learning", "curriculum",
                    "teacher", "school", "university", "achievement"],
    "management":  ["organization", "firm", "employee", "performance", "leadership",
                    "management", "strategy", "innovation", "productivity"],
    "social":      ["social", "community", "poverty", "inequality", "demographic"],
    "engineering": ["system", "algorithm", "model performance", "accuracy", "precision",
                    "recall", "machine learning", "optimization"],
}


# ── Main function ─────────────────────────────────────────────────────────────

def analyze_design(text: str, parsed: ParsedData) -> ResearchDesign:
    lower = text.lower()
    design = ResearchDesign()

    # Study type (first match wins in priority order)
    for study_type, signals in _STUDY_SIGNALS:
        if any(s in lower for s in signals):
            design.study_type = study_type
            if study_type in (StudyType.LONGITUDINAL, StudyType.COHORT):
                design.is_longitudinal = True
            if study_type in (StudyType.RCT, StudyType.EXPERIMENTAL):
                design.has_control_group = True
                design.has_randomisation = (study_type == StudyType.RCT)
            break

    # Detect methods (all matches)
    for method, signals in _METHOD_PATTERNS:
        if any(s in lower for s in signals):
            design.detected_methods.append(method)

    if not design.detected_methods:
        design.detected_methods = [AnalysisMethod.UNKNOWN]

    # Primary method — most specific non-unknown first
    non_unknown = [m for m in design.detected_methods if m != AnalysisMethod.UNKNOWN]
    design.primary_method = non_unknown[0] if non_unknown else AnalysisMethod.UNKNOWN

    # Variables from text
    dv_m = _DV_SIGNALS.search(text)
    if dv_m:
        design.dependent_variables = [v.strip() for v in re.split(r"[,;]", dv_m.group(1))
                                       if v.strip()][:5]

    iv_m = _IV_SIGNALS.search(text)
    if iv_m:
        design.independent_variables = [v.strip() for v in re.split(r"[,;]", iv_m.group(1))
                                         if v.strip()][:5]

    mod_m = _MODERATOR_RE.search(text)
    if mod_m:
        design.moderators = [v.strip() for v in re.split(r"[,;]", mod_m.group(1)) if v.strip()][:3]

    med_m = _MEDIATOR_RE.search(text)
    if med_m:
        design.mediators = [v.strip() for v in re.split(r"[,;]", med_m.group(1)) if v.strip()][:3]

    # Variables from structured data
    if parsed.has_structured_data and not design.independent_variables:
        design.independent_variables = parsed.numeric_columns[:5]

    # Sample size
    if parsed.sample_size:
        design.sample_size = parsed.sample_size
    else:
        n_m = _SAMPLE_SIZE_RE.search(text)
        if n_m:
            try:
                design.sample_size = int(n_m.group(1).replace(",", ""))
            except ValueError:
                pass

    # Sampling strategy
    for label, signals in _SAMPLING_PATTERNS:
        if any(s in lower for s in signals):
            design.sampling_strategy = label
            break

    # Discipline
    discipline_scores: dict[str, int] = {}
    for disc, words in _DISCIPLINE_SIGNALS.items():
        discipline_scores[disc] = sum(1 for w in words if w in lower)
    if discipline_scores:
        top = max(discipline_scores, key=discipline_scores.get)
        if discipline_scores[top] >= 2:
            design.discipline = top

    return design
