"""Public, unauthenticated research-question preview — the landing page's
"What are you researching?" moment (Phase 9A Part 2, §17-19).

Deliberately NOT the canonical Phase 8C flow (services/research_need/) and
NEVER calls it, for two structural reasons, both non-negotiable per the
Phase 9A spec:

1. Zero AI cost / zero abuse surface. This endpoint is reachable by anyone,
   with no account and no rate-limit-by-user-id available (there's no
   user). A real LLM call here would be an open, unmetered cost surface.
   So this is a small, hand-curated, purely deterministic keyword/theme
   taxonomy — no model call, ever.
2. Never retrieves or shows a real person. This module has no DB access at
   all and cannot import discovery_engine/find_relevant_people even by
   accident — an anonymous visitor may only see thematic/disciplinary
   intelligence, never a profile, name, or "match".

The taxonomy below is intentionally modest (breadth over depth) — it exists
to demonstrate "a question implies a structure of expertise", not to be a
complete classification system. A query matching nothing still gets a
useful, honest response built from its own extracted keywords rather than
an empty or fabricated one.
"""
from __future__ import annotations

import re

_MAX_QUERY_LEN = 600

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "for", "to", "in", "on",
    "with", "how", "can", "could", "would", "should", "is", "are", "be",
    "while", "this", "that", "these", "those", "it", "its", "we", "our",
    "i", "my", "without", "increasing", "reducing", "improve", "improving",
    "reduce", "reducing", "using", "what", "when", "does", "do", "did",
}

# Each entry: substrings to match in the (lowercased) query -> the themes,
# complementary disciplines, and methods a reasonable domain expert would
# associate with that area. Hand-authored reference content, not AI output
# and not a claim about any real person or dataset.
_TAXONOMY: list[dict] = [
    {
        "match": ["hospital", "patient", "clinical", "healthcare", "health care", "nurse", "physician", "treatment", "diagnos", "waiting time", "medical"],
        "themes": ["Health Services Research", "Clinical Medicine"],
        "complementary": ["Quality Management", "Operations Research", "Health Policy", "Implementation Science"],
        "methods": ["Mixed-methods evaluation", "Process mapping", "Statistical process control"],
    },
    {
        "match": ["machine learning", "neural network", "deep learning", "artificial intelligence", " ai ", "ai-", "llm", "language model"],
        "themes": ["Machine Learning", "Artificial Intelligence"],
        "complementary": ["Human-Computer Interaction", "AI Ethics", "Statistics", "Domain-Specific Applications"],
        "methods": ["Model evaluation", "Benchmark design", "Ablation studies"],
    },
    {
        "match": ["classroom", "student", "curriculum", "pedagog", "teaching", "learning outcome", "education"],
        "themes": ["Education Research", "Curriculum Design"],
        "complementary": ["Educational Psychology", "Learning Technology", "Policy & Administration"],
        "methods": ["Learning assessment design", "Classroom-based studies", "Longitudinal cohort tracking"],
    },
    {
        "match": ["climate", "carbon", "emission", "sustainab", "renewable", "environment"],
        "themes": ["Climate Science", "Environmental Studies"],
        "complementary": ["Public Policy", "Economics", "Engineering", "Behavioral Science"],
        "methods": ["Life-cycle assessment", "Climate modeling", "Policy impact evaluation"],
    },
    {
        "match": ["policy", "government", "public administration", "regulat", "legislat"],
        "themes": ["Public Policy", "Public Administration"],
        "complementary": ["Economics", "Law", "Political Science", "Data Science"],
        "methods": ["Policy analysis", "Stakeholder interviews", "Comparative case study"],
    },
    {
        "match": ["economic", "market", "finance", "trade", "gdp", "inflation", "labor market"],
        "themes": ["Economics"],
        "complementary": ["Public Policy", "Statistics", "Behavioral Science"],
        "methods": ["Econometric modeling", "Regression analysis", "Natural experiments"],
    },
    {
        "match": ["law", "legal", "regulation", "compliance", "litigation", "contract"],
        "themes": ["Law", "Legal Studies"],
        "complementary": ["Public Policy", "Ethics", "Technology Studies"],
        "methods": ["Case law analysis", "Comparative legal analysis", "Regulatory impact review"],
    },
    {
        "match": ["cybersecurity", "cyber security", "data breach", "encryption", "security vulnerability", "malware"],
        "themes": ["Cybersecurity"],
        "complementary": ["Law", "Public Policy", "Human-Computer Interaction"],
        "methods": ["Threat modeling", "Penetration testing methodology", "Risk assessment"],
    },
    {
        "match": ["engineering", "manufactur", "mechanical", "structural", "materials science"],
        "themes": ["Engineering"],
        "complementary": ["Operations Research", "Environmental Studies", "Design"],
        "methods": ["Prototyping", "Simulation modeling", "Failure analysis"],
    },
    {
        "match": ["data science", "statistics", "statistical", "dataset", "predictive model"],
        "themes": ["Data Science", "Statistics"],
        "complementary": ["Domain-Specific Applications", "Ethics", "Visualization"],
        "methods": ["Statistical modeling", "Hypothesis testing", "Data visualization"],
    },
    {
        "match": ["psycholog", "behavior", "cognit", "mental health", "wellbeing"],
        "themes": ["Psychology", "Behavioral Science"],
        "complementary": ["Public Health", "Education", "Neuroscience"],
        "methods": ["Randomized controlled trials", "Survey design", "Behavioral experiments"],
    },
    {
        "match": ["social media", "sociology", "community", "inequality", "demographic"],
        "themes": ["Sociology"],
        "complementary": ["Public Policy", "Data Science", "Communication Studies"],
        "methods": ["Survey research", "Ethnography", "Social network analysis"],
    },
    {
        "match": ["business", "management", "organization", "workforce", "staff workload", "employee"],
        "themes": ["Management Studies", "Organizational Research"],
        "complementary": ["Operations Research", "Psychology", "Economics"],
        "methods": ["Organizational case study", "Workforce analytics", "Process improvement"],
    },
    {
        "match": ["biology", "genom", "cell", "molecular", "biotech", "protein"],
        "themes": ["Molecular Biology", "Life Sciences"],
        "complementary": ["Bioinformatics", "Chemistry", "Medicine"],
        "methods": ["Wet-lab experimentation", "Sequencing analysis", "Computational modeling"],
    },
    {
        "match": ["physics", "quantum", "particle", "astrophysics"],
        "themes": ["Physics"],
        "complementary": ["Mathematics", "Computer Science", "Materials Science"],
        "methods": ["Theoretical modeling", "Experimental physics", "Computational simulation"],
    },
    {
        "match": ["chemistry", "chemical", "compound", "catalys", "synthesis"],
        "themes": ["Chemistry"],
        "complementary": ["Materials Science", "Environmental Studies", "Pharmacology"],
        "methods": ["Synthesis and characterization", "Spectroscopy", "Computational chemistry"],
    },
    {
        "match": ["software", "algorithm", "programming", "computer science", "distributed system"],
        "themes": ["Computer Science"],
        "complementary": ["Human-Computer Interaction", "Data Science", "Security"],
        "methods": ["System design and evaluation", "Algorithmic complexity analysis", "User studies"],
    },
    {
        "match": ["language", "linguistic", "translation", "speech", "nlp", "natural language"],
        "themes": ["Linguistics"],
        "complementary": ["Computer Science", "Cognitive Science", "Education"],
        "methods": ["Corpus analysis", "Computational linguistics", "Discourse analysis"],
    },
    {
        "match": ["election", "voting", "political", "democracy", "governance"],
        "themes": ["Political Science"],
        "complementary": ["Public Policy", "Sociology", "Data Science"],
        "methods": ["Survey research", "Comparative politics analysis", "Election forecasting"],
    },
    {
        "match": ["media", "journalism", "communication", "broadcast", "public relations"],
        "themes": ["Communication Studies", "Media Studies"],
        "complementary": ["Sociology", "Political Science", "Psychology"],
        "methods": ["Content analysis", "Audience research", "Discourse analysis"],
    },
    {
        "match": ["urban", "city planning", "architecture", "infrastructure", "housing"],
        "themes": ["Urban Planning", "Architecture"],
        "complementary": ["Public Policy", "Environmental Studies", "Civil Engineering"],
        "methods": ["Spatial analysis", "Urban modeling", "Participatory design"],
    },
    {
        "match": ["agricultur", "crop", "farming", "food security", "soil"],
        "themes": ["Agricultural Science"],
        "complementary": ["Environmental Studies", "Economics", "Public Policy"],
        "methods": ["Field trials", "Remote sensing", "Yield modeling"],
    },
    {
        "match": ["energy", "grid", "solar", "wind power", "battery", "electricity"],
        "themes": ["Energy Systems"],
        "complementary": ["Environmental Studies", "Economics", "Public Policy"],
        "methods": ["Systems modeling", "Techno-economic analysis", "Grid simulation"],
    },
    {
        "match": ["robot", "automation", "autonomous system", "drone"],
        "themes": ["Robotics"],
        "complementary": ["Computer Science", "Mechanical Engineering", "Ethics"],
        "methods": ["Systems testing", "Simulation", "Human-robot interaction studies"],
    },
    {
        "match": ["brain", "neuroscience", "neural", "cognitive science"],
        "themes": ["Neuroscience"],
        "complementary": ["Psychology", "Computer Science", "Medicine"],
        "methods": ["Neuroimaging", "Behavioral testing", "Computational modeling"],
    },
    {
        "match": ["epidemiolog", "public health", "disease outbreak", "vaccine", "pandemic"],
        "themes": ["Epidemiology", "Public Health"],
        "complementary": ["Health Policy", "Statistics", "Behavioral Science"],
        "methods": ["Cohort studies", "Statistical modeling", "Surveillance data analysis"],
    },
]


def _extract_keywords(query: str, limit: int = 10) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", query)
    seen: dict[str, str] = {}
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS or lw in seen:
            continue
        seen[lw] = w
    return list(seen.values())[:limit]


def preview_research_themes(query: str) -> dict:
    """Deterministic-only, zero-cost theme extraction for anonymous visitors.

    Returns a dict with `themes`, `complementary_disciplines`, `methods`,
    and `keywords` — never a person, name, institution, or match. Always
    returns something usable (falls back to the query's own keywords as
    "themes" if nothing in the taxonomy matches), matching the same
    "never collapse into an empty/error state" principle as the canonical
    Phase 8C deterministic fallback.
    """
    q = (query or "").strip()[:_MAX_QUERY_LEN]
    ql = q.lower()

    themes: dict[str, None] = {}
    complementary: dict[str, None] = {}
    methods: dict[str, None] = {}

    for entry in _TAXONOMY:
        if any(m in ql for m in entry["match"]):
            for t in entry["themes"]:
                themes[t] = None
            for c in entry["complementary"]:
                complementary[c] = None
            for me in entry["methods"]:
                methods[me] = None

    keywords = _extract_keywords(q)

    if not themes:
        # No taxonomy hit — still return something real and honest, built
        # from the query itself, not a fabricated theme.
        themes = {kw: None for kw in keywords[:5]}

    return {
        "themes": list(themes.keys())[:6],
        "complementary_disciplines": list(complementary.keys())[:6],
        "methods": list(methods.keys())[:5],
        "keywords": keywords,
        "matched_taxonomy": bool(complementary or (themes and list(themes.keys())[:6] != keywords[:5])),
    }
