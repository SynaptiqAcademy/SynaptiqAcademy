"""Research Collaboration Intelligence — Academic Competency Graph (Phase XIV).

Identifies expertise levels across research domains, methodologies, statistical
techniques, software, programming languages, lab skills, and teaching.
All classification is keyword-based, requiring no LLM calls.
"""
from __future__ import annotations

import re

from .models import CompetencyGraph, CompetencyNode

# ── Taxonomy ──────────────────────────────────────────────────────────────────

_DOMAINS: dict[str, list[str]] = {
    "machine_learning": ["machine learning", "deep learning", "neural network", "nlp",
                         "computer vision", "artificial intelligence", "ai", "ml"],
    "bioinformatics":   ["bioinformatics", "genomics", "proteomics", "transcriptomics",
                         "sequencing", "metagenomics", "single-cell"],
    "clinical_medicine":["clinical", "medicine", "cardiology", "oncology", "neurology",
                         "pathology", "surgery", "patient", "medical"],
    "public_health":    ["public health", "epidemiology", "epidemiological", "population health",
                         "health policy", "social determinants"],
    "psychology":       ["psychology", "cognitive", "behavioral", "mental health",
                         "neuroscience", "brain", "psychiatric"],
    "education":        ["education", "pedagogy", "curriculum", "learning", "teaching",
                         "instructional design", "e-learning"],
    "economics":        ["economics", "econometrics", "finance", "market", "policy",
                         "macroeconomics", "microeconomics"],
    "environmental":    ["environmental", "ecology", "climate", "sustainability",
                         "conservation", "biodiversity", "ecosystem"],
    "chemistry":        ["chemistry", "organic", "inorganic", "biochemistry",
                         "analytical chemistry", "synthesis"],
    "physics":          ["physics", "quantum", "optics", "mechanics", "thermodynamics",
                         "astrophysics", "condensed matter"],
    "engineering":      ["engineering", "mechanical", "electrical", "civil",
                         "chemical engineering", "biomedical"],
    "social_sciences":  ["sociology", "anthropology", "political science", "communication",
                         "cultural studies", "geography"],
    "mathematics":      ["mathematics", "algebra", "topology", "number theory",
                         "combinatorics", "analysis", "mathematical"],
}

_METHODS: dict[str, list[str]] = {
    "rct":               ["randomized controlled trial", "rct", "randomised"],
    "cohort_study":      ["cohort study", "longitudinal study", "prospective", "retrospective"],
    "case_control":      ["case-control", "case control"],
    "systematic_review": ["systematic review", "meta-analysis", "scoping review", "cochrane"],
    "qualitative":       ["qualitative", "grounded theory", "thematic analysis",
                          "ethnography", "phenomenology", "interview"],
    "survey":            ["survey", "questionnaire", "cross-sectional"],
    "experiment":        ["experimental", "laboratory experiment", "randomized experiment"],
    "computational":     ["computational", "simulation", "agent-based", "modelling"],
    "mixed_methods":     ["mixed methods", "mixed-methods"],
    "observational":     ["observational study", "observational"],
}

_STATS: dict[str, list[str]] = {
    "regression":     ["regression", "linear model", "logistic regression", "glm", "glmm"],
    "anova":          ["anova", "analysis of variance", "ancova"],
    "bayesian":       ["bayesian", "mcmc", "posterior", "prior", "credible interval"],
    "survival":       ["survival analysis", "cox model", "kaplan-meier", "time to event"],
    "sem":            ["structural equation", "sem", "path analysis"],
    "multilevel":     ["multilevel", "hierarchical model", "mixed effects", "random effects"],
    "machine_learning_stats": ["random forest", "svm", "gradient boosting", "xgboost",
                               "cross-validation", "hyperparameter"],
    "time_series":    ["time series", "arima", "forecasting", "longitudinal analysis"],
    "factor_analysis":["factor analysis", "pca", "principal component", "cluster analysis"],
    "network_analysis":["network analysis", "graph theory", "social network"],
}

_SOFTWARE: dict[str, list[str]] = {
    "spss":    ["spss"],
    "stata":   ["stata"],
    "r_stats": ["r statistical", " r programming", "rstudio", "tidyverse", "ggplot"],
    "sas":     [" sas "],
    "matlab":  ["matlab"],
    "nvivo":   ["nvivo"],
    "atlas_ti":["atlas.ti"],
    "excel":   ["excel", "spreadsheet"],
}

_PROGRAMMING: dict[str, list[str]] = {
    "python":     ["python", "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow"],
    "r":          ["r language", "r programming", "r package", "rstudio"],
    "java":       ["java"],
    "javascript": ["javascript", "nodejs", "react", "typescript"],
    "matlab":     ["matlab"],
    "c_cpp":      [" c++ ", " c programming"],
    "julia":      ["julia programming", "julia language"],
    "sql":        ["sql", "postgresql", "mysql", "database query"],
}

_TEACHING: dict[str, list[str]] = {
    "curriculum_design": ["curriculum design", "course development", "syllabus"],
    "supervision":       ["supervision", "doctoral supervision", "thesis supervision",
                          "mentoring phd"],
    "lecturing":         ["lecture", "teaching undergraduate", "teaching postgraduate"],
    "online_teaching":   ["online teaching", "e-learning", "moodle", "canvas"],
    "assessment":        ["assessment design", "exam", "rubric"],
}

_LAB: dict[str, list[str]] = {
    "pcr":              ["pcr", "polymerase chain reaction"],
    "cell_culture":     ["cell culture", "in vitro"],
    "flow_cytometry":   ["flow cytometry", "facs"],
    "microscopy":       ["microscopy", "confocal", "electron microscopy"],
    "spectroscopy":     ["spectroscopy", "nmr", "mass spectrometry"],
    "sequencing":       ["sequencing", "next-generation sequencing", "ngs", "illumina"],
    "chromatography":   ["chromatography", "hplc", "gc-ms"],
}


def _score(text: str, signals: list[str]) -> float:
    """Count keyword hits in text, return 0-1 score."""
    t = text.lower()
    hits = sum(1 for s in signals if s in t)
    return min(hits / max(len(signals) * 0.3, 1.0), 1.0)


def _to_nodes(taxonomy: dict[str, list[str]], combined_text: str) -> list[CompetencyNode]:
    nodes: list[CompetencyNode] = []
    for concept, signals in taxonomy.items():
        level = _score(combined_text, signals)
        if level > 0:
            hits = sum(1 for s in signals if s in combined_text.lower())
            nodes.append(CompetencyNode(concept=concept, level=level, evidence_count=hits))
    return sorted(nodes, key=lambda n: -n.level)


def build_competency_graph(
    user_id: str,
    domains: list[str],
    keywords: list[str],
    methods: list[str],
    stats: list[str],
    progs: list[str],
    peer_review_count: int = 0,
    grant_success_rate: float = 0.0,
    h_index: float = 0.0,
) -> CompetencyGraph:
    combined = " ".join(domains + keywords + methods + stats + progs).lower()

    domain_nodes = _to_nodes(_DOMAINS, combined)
    method_nodes = _to_nodes(_METHODS, combined)
    stat_nodes   = _to_nodes(_STATS, combined)
    sw_nodes     = _to_nodes(_SOFTWARE, combined)
    prog_nodes   = _to_nodes(_PROGRAMMING, combined)
    lab_nodes    = _to_nodes(_LAB, combined)
    teach_nodes  = _to_nodes(_TEACHING, combined)

    # Writing quality proxy: peer review experience normalised
    writing_quality = min(peer_review_count / 20.0, 1.0) * 0.5 + 0.5
    leadership_score = min(h_index / 20.0, 1.0) * 0.5 + grant_success_rate * 0.5

    total_nodes = (len(domain_nodes) + len(method_nodes) + len(stat_nodes) +
                   len(sw_nodes) + len(prog_nodes) + len(lab_nodes) + len(teach_nodes))
    overall = min(total_nodes / 15.0, 1.0)

    return CompetencyGraph(
        user_id=user_id,
        research_domains=domain_nodes,
        methodologies=method_nodes,
        statistical_techniques=stat_nodes,
        software_tools=sw_nodes,
        programming_languages=prog_nodes,
        lab_skills=lab_nodes,
        teaching_skills=teach_nodes,
        peer_review_count=peer_review_count,
        grant_success_rate=grant_success_rate,
        writing_quality=round(writing_quality, 3),
        leadership_score=round(leadership_score, 3),
        overall_score=round(overall, 3),
    )
