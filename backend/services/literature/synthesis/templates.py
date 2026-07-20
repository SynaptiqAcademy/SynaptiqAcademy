"""Academic review structure templates for all 6 review types."""
from __future__ import annotations

from services.literature.models import ReviewType


class ReviewTemplate:
    """Defines section structure and AI guidance for a review type."""

    def __init__(
        self,
        review_type: ReviewType,
        title_template: str,
        sections: list[str],
        system_prompt: str,
        word_target: int = 2500,
    ) -> None:
        self.review_type = review_type
        self.title_template = title_template
        self.sections = sections
        self.system_prompt = system_prompt
        self.word_target = word_target


_SHARED_ACCURACY_RULES = """\
ACCURACY RULES (strictly followed):
1. Reference only authors and works present in the provided corpus summaries.
2. Every claim must be attributable to a specific paper in the corpus.
3. Use hedged language when evidence is limited: "evidence suggests", "preliminary findings indicate".
4. Do not invent statistics, p-values, sample sizes, or effect sizes.
5. Use in-text citations in the format (Author, Year) using the paper metadata provided.
6. Where corpus papers directly conflict, acknowledge both positions.
"""


NARRATIVE_TEMPLATE = ReviewTemplate(
    review_type=ReviewType.NARRATIVE,
    title_template="A Narrative Review of {topic}",
    sections=[
        "Introduction",
        "Search Strategy",
        "Major Themes",
        "Key Authors and Theoretical Contributions",
        "Methodological Landscape",
        "Current Debates and Controversies",
        "Research Gaps",
        "Future Directions",
        "Conclusion",
    ],
    system_prompt=f"""\
You are an expert academic writer producing a publication-quality narrative literature review.
Narrative reviews synthesise and interpret the literature rather than enumerate studies.

{_SHARED_ACCURACY_RULES}

STRUCTURE REQUIREMENTS:
- Write in flowing, scholarly prose with strong paragraph transitions.
- Each section should be 150-300 words.
- The Introduction must contextualise the topic's importance and scope.
- Major Themes: identify 3-5 thematic clusters and synthesise findings within each.
- Current Debates: present opposing views with specific evidence.
- Conclusion: summarise contributions and limitations of current evidence.
- Include (Author, Year) citations throughout.
""",
    word_target=2500,
)

SYSTEMATIC_TEMPLATE = ReviewTemplate(
    review_type=ReviewType.SYSTEMATIC,
    title_template="A Systematic Review of {topic}",
    sections=[
        "Abstract (PRISMA format)",
        "Introduction",
        "Methods — Search Strategy",
        "Methods — Inclusion and Exclusion Criteria",
        "Methods — Quality Assessment",
        "Results — Study Characteristics",
        "Results — Data Synthesis",
        "Discussion",
        "Conclusions",
        "Declarations",
    ],
    system_prompt=f"""\
You are an expert academic writer producing a publication-quality systematic literature review.
Systematic reviews follow strict PRISMA reporting standards.

{_SHARED_ACCURACY_RULES}

STRUCTURE REQUIREMENTS:
- Abstract: follow PRISMA format (Background, Objectives, Search Methods, Eligibility Criteria, Results, Conclusions).
- Methods: describe explicit inclusion/exclusion criteria, quality assessment approach, and data extraction.
- Results: report study characteristics in structured narrative (design, sample, outcomes).
- Discussion: interpret findings in context, discuss heterogeneity.
- Declarations: state limitations, potential bias, funding (mark as [author to complete]).
- Use PRISMA language and systematic review conventions throughout.
""",
    word_target=3500,
)

SCOPING_TEMPLATE = ReviewTemplate(
    review_type=ReviewType.SCOPING,
    title_template="A Scoping Review of {topic}",
    sections=[
        "Introduction",
        "Research Question",
        "Search Strategy and Sources",
        "Eligibility Criteria",
        "Charting the Evidence",
        "Results — Scope of Literature",
        "Results — Key Concepts and Definitions",
        "Discussion",
        "Conclusions and Implications for Practice",
    ],
    system_prompt=f"""\
You are an expert academic writer producing a scoping review following Arksey & O'Malley / JBI methodology.
Scoping reviews map the extent, range, and nature of evidence — without quality assessment.

{_SHARED_ACCURACY_RULES}

STRUCTURE REQUIREMENTS:
- Clearly state the overarching research question in the Introduction.
- Charting section: present data in thematic groupings, not individual study descriptions.
- Identify conceptual and definitional variations in the literature.
- Do not conduct risk of bias or quality appraisal (scoping review convention).
- Conclusions must address evidence gaps and research implications.
""",
    word_target=2500,
)

CRITICAL_TEMPLATE = ReviewTemplate(
    review_type=ReviewType.CRITICAL,
    title_template="A Critical Review of {topic}",
    sections=[
        "Introduction and Context",
        "Theoretical and Conceptual Analysis",
        "Critical Evaluation of Methodologies",
        "Critical Synthesis of Findings",
        "Contradictions and Limitations in the Literature",
        "Alternative Interpretations",
        "Implications for Theory and Practice",
        "Recommendations for Future Research",
    ],
    system_prompt=f"""\
You are a rigorous academic scholar producing a critical literature review.
Critical reviews go beyond description to evaluate, challenge, and reinterpret existing work.

{_SHARED_ACCURACY_RULES}

STRUCTURE REQUIREMENTS:
- Critically evaluate methodological choices, not just describe them.
- Identify assumptions, biases, and limitations in specific papers from the corpus.
- Challenge consensus views where evidence is weak or conflicting.
- Propose alternative theoretical frameworks where relevant.
- Use evaluative language: "This approach overlooks...", "The evidence does not support...",
  "A more rigorous interpretation suggests...".
- Do NOT simply summarise — every paragraph should contain critical evaluation.
""",
    word_target=3000,
)

INTEGRATIVE_TEMPLATE = ReviewTemplate(
    review_type=ReviewType.INTEGRATIVE,
    title_template="An Integrative Review of {topic}",
    sections=[
        "Introduction",
        "Purpose and Objectives",
        "Method — Literature Search and Inclusion",
        "Critical Appraisal",
        "Data Extraction and Synthesis",
        "Results — Integrated Findings",
        "Discussion — Conceptual Integration",
        "Conclusions and Recommendations",
    ],
    system_prompt=f"""\
You are an expert academic writer producing an integrative literature review (Whittemore & Knafl methodology).
Integrative reviews synthesise both empirical and theoretical literature.

{_SHARED_ACCURACY_RULES}

STRUCTURE REQUIREMENTS:
- Include both qualitative and quantitative studies in synthesis.
- Data Extraction section: describe how key data was coded and grouped.
- Integrated Findings: present unified themes that cut across study types.
- Conceptual Integration: connect findings to broader theoretical frameworks.
- Acknowledge when findings from different study types produce conflicting conclusions.
""",
    word_target=3000,
)

STATE_OF_ART_TEMPLATE = ReviewTemplate(
    review_type=ReviewType.STATE_OF_ART,
    title_template="State of the Art in {topic}: A Comprehensive Review",
    sections=[
        "Introduction",
        "Historical Development",
        "Current State of Knowledge",
        "Leading Research Groups and Contributions",
        "Emerging Technologies and Approaches",
        "Open Challenges",
        "Benchmarks and Standards",
        "Future Roadmap",
        "Conclusions",
    ],
    system_prompt=f"""\
You are an expert academic writer producing a state-of-the-art review for a high-impact journal.
State-of-the-art reviews comprehensively map the current frontier of a field.

{_SHARED_ACCURACY_RULES}

STRUCTURE REQUIREMENTS:
- Historical Development: trace the field's trajectory chronologically from the corpus.
- Current State: describe what is definitively known today.
- Leading Contributors: attribute key advances to specific researchers from the corpus.
- Emerging Approaches: describe newest methodological or conceptual developments.
- Open Challenges: list specific unsolved problems backed by corpus evidence.
- Future Roadmap: propose concrete 5-year directions based on trends.
- Write with the precision and confidence of a domain expert.
""",
    word_target=4000,
)


_TEMPLATES: dict[ReviewType, ReviewTemplate] = {
    ReviewType.NARRATIVE: NARRATIVE_TEMPLATE,
    ReviewType.SYSTEMATIC: SYSTEMATIC_TEMPLATE,
    ReviewType.SCOPING: SCOPING_TEMPLATE,
    ReviewType.CRITICAL: CRITICAL_TEMPLATE,
    ReviewType.INTEGRATIVE: INTEGRATIVE_TEMPLATE,
    ReviewType.STATE_OF_ART: STATE_OF_ART_TEMPLATE,
}


def get_template(review_type: ReviewType) -> ReviewTemplate:
    return _TEMPLATES[review_type]


def all_templates() -> dict[str, dict]:
    return {
        rt.value: {
            "sections": t.sections,
            "word_target": t.word_target,
            "title_template": t.title_template,
        }
        for rt, t in _TEMPLATES.items()
    }
