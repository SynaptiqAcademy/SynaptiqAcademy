"""Research question generator for Research Gap Intelligence.

Generates research questions, objectives, hypotheses, and aims for each detected gap.
Uses template-based generation for speed, with optional AI enrichment.
"""
from __future__ import annotations

import logging

from .models import DetectedGap, GapType, ResearchQuestion
from .taxonomy import GAP_METADATA

log = logging.getLogger("synaptiq.research_gap.questions")


def enrich_gap_with_questions(gap: DetectedGap, topic: str = "") -> DetectedGap:
    """Ensure every gap has at least one high-quality research question."""
    if gap.research_questions:
        # AI already provided questions; only ensure they have objectives/hypotheses
        gap.research_questions = [_enrich_existing_rq(rq, gap, topic) for rq in gap.research_questions]
        return gap

    # Generate template-based questions if AI provided none
    generated = _generate_template_questions(gap, topic)
    gap.research_questions = generated
    return gap


def _enrich_existing_rq(rq: ResearchQuestion, gap: DetectedGap, topic: str) -> ResearchQuestion:
    """Fill in missing fields for an AI-generated research question."""
    if not rq.hypotheses and rq.question:
        rq.hypotheses = _derive_hypotheses(rq.question, gap.gap_type)
    if not rq.research_objectives:
        rq.research_objectives = _derive_objectives(rq.question, gap.gap_type, topic)
    if not rq.research_aims:
        rq.research_aims = [f"To investigate {rq.question[:80]}"]
    return rq


def _generate_template_questions(gap: DetectedGap, topic: str) -> list[ResearchQuestion]:
    """Generate research questions from gap type templates."""
    templates = _QUESTION_TEMPLATES.get(gap.gap_type, _QUESTION_TEMPLATES[GapType.FUTURE_RESEARCH])
    questions: list[ResearchQuestion] = []

    for tmpl in templates[:2]:  # max 2 template questions per gap
        question = tmpl["question"].format(topic=topic or "the phenomenon")
        rq = ResearchQuestion(
            question=question,
            rationale=tmpl["rationale"].format(topic=topic or "this area", gap_title=gap.title),
            novelty_statement=tmpl["novelty"].format(gap_type=gap.gap_type.value),
            suggested_methodology=gap.methodology_recommendation.research_design or tmpl["method"],
            expected_contribution=tmpl["contribution"].format(topic=topic or "the field"),
            publication_potential=_estimate_publication_potential(gap),
            target_journal_type=tmpl.get("journal", "domain-specific academic journal"),
            hypotheses=_derive_hypotheses(question, gap.gap_type),
            research_objectives=_derive_objectives(question, gap.gap_type, topic),
            research_aims=[f"To {tmpl['aim'].format(topic=topic or 'the phenomenon')}"],
            alternative_paths=tmpl.get("alternatives", []),
        )
        questions.append(rq)

    return questions


def _derive_hypotheses(question: str, gap_type: GapType) -> list[str]:
    """Derive testable hypotheses from a research question."""
    q_lower = question.lower()

    # Relationship hypothesis
    if "relationship" in q_lower or "effect" in q_lower or "impact" in q_lower:
        return [
            f"H1: There is a significant positive relationship between the key variables studied.",
            f"H0: There is no significant relationship between the variables.",
        ]
    # Difference hypothesis
    if "differ" in q_lower or "compare" in q_lower or "between" in q_lower:
        return [
            f"H1: Significant differences exist between the groups/conditions studied.",
            f"H0: No significant differences exist between the groups/conditions.",
        ]
    # General
    return [f"H1: The phenomenon under study exhibits the characteristics hypothesised based on existing theory."]


def _derive_objectives(question: str, gap_type: GapType, topic: str) -> list[str]:
    meta = GAP_METADATA.get(gap_type, {})
    return [
        f"To systematically review existing {topic or 'field'} literature to identify key patterns.",
        f"To develop and test a {meta.get('typical_design', 'rigorous research design')} addressing this gap.",
        f"To generate empirically grounded conclusions that advance theoretical understanding.",
    ]


def _estimate_publication_potential(gap: DetectedGap) -> str:
    score = gap.opportunity_score.publication_probability
    if score >= 0.70:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


# ── Question templates per gap type ───────────────────────────────────────────

_QUESTION_TEMPLATES: dict[GapType, list[dict]] = {
    GapType.THEORETICAL: [
        {
            "question": "What theoretical framework best explains {topic} in contemporary contexts?",
            "rationale": "No unified theory has been developed for {topic}, limiting predictive and explanatory power.",
            "novelty": "Proposes a novel {gap_type} contribution by integrating existing perspectives.",
            "method": "systematic review and theory-building",
            "contribution": "A validated conceptual model applicable to {topic} research.",
            "aim": "develop a comprehensive theoretical framework for {topic}",
            "journal": "theory-focused or review journal",
            "alternatives": ["Adapt an existing theory from an adjacent field", "Conduct a meta-analysis to synthesise existing models"],
        }
    ],
    GapType.METHODOLOGICAL: [
        {
            "question": "What measurement instrument best captures the key constructs of {topic}?",
            "rationale": "Existing instruments lack validation for the {topic} context, reducing comparability.",
            "novelty": "Develops and validates a context-specific {gap_type} solution.",
            "method": "scale development and validation study",
            "contribution": "A validated psychometric instrument for {topic} researchers.",
            "aim": "develop and validate a rigorous measurement instrument for {topic}",
            "journal": "methodological or domain-specific journal",
            "alternatives": ["Adapt an existing scale with confirmatory factor analysis", "Develop a computational measurement approach"],
        }
    ],
    GapType.EMPIRICAL: [
        {
            "question": "What is the empirical relationship between the core variables in {topic}?",
            "rationale": "The relationship has been theorised but not rigorously tested empirically in {topic}.",
            "novelty": "Provides the first large-scale {gap_type} evidence for this relationship.",
            "method": "quantitative survey or experimental study",
            "contribution": "Empirical evidence either confirming or disconfirming existing theoretical predictions.",
            "aim": "empirically test core theoretical relationships in {topic}",
            "journal": "high-impact quantitative research journal",
            "alternatives": ["Run a multi-wave longitudinal study", "Conduct a meta-analysis of existing smaller studies"],
        }
    ],
    GapType.PRACTICAL: [
        {
            "question": "How do practitioners implement {topic} strategies, and what barriers do they face?",
            "rationale": "The gap between academic recommendations and practical implementation for {topic} is understudied.",
            "novelty": "Bridges theory and practice through {gap_type} evidence.",
            "method": "case study or action research",
            "contribution": "Evidence-based guidelines for practitioners implementing {topic} strategies.",
            "aim": "document real-world implementation barriers and facilitators of {topic}",
            "journal": "applied or practitioner-oriented journal",
            "alternatives": ["Design-science research", "Participatory action research"],
        }
    ],
    GapType.TECHNOLOGICAL: [
        {
            "question": "How can emerging technologies be applied to enhance outcomes in {topic}?",
            "rationale": "No framework exists for systematic technology adoption in {topic} contexts.",
            "novelty": "First empirical assessment of {gap_type} applications in this domain.",
            "method": "design science research or prototype evaluation",
            "contribution": "A technical framework and proof-of-concept system for {topic}.",
            "aim": "develop and evaluate a technology-driven solution for {topic}",
            "journal": "technology or information systems journal",
            "alternatives": ["Systematic literature review of analogous technology applications", "Expert Delphi on technology readiness"],
        }
    ],
    GapType.REGIONAL: [
        {
            "question": "How does {topic} manifest in underrepresented geographic and cultural contexts?",
            "rationale": "Research on {topic} is disproportionately concentrated in a small number of countries.",
            "novelty": "First {gap_type} study examining {topic} in these underrepresented settings.",
            "method": "cross-national comparative study",
            "contribution": "Evidence on contextual variability of {topic} across cultures.",
            "aim": "assess the cultural and regional transferability of {topic} findings",
            "journal": "international or comparative research journal",
            "alternatives": ["Cross-cultural validation study", "Systematic review with geographic meta-analysis"],
        }
    ],
    GapType.POPULATION: [
        {
            "question": "How does {topic} affect underserved or underrepresented population groups?",
            "rationale": "Current research on {topic} has focused on dominant demographic groups, excluding key populations.",
            "novelty": "First targeted study of {topic} for this {gap_type} group.",
            "method": "targeted survey or focus groups",
            "contribution": "Inclusive evidence for {topic} applicable across diverse populations.",
            "aim": "examine {topic} experiences and outcomes in under-studied population groups",
            "journal": "inclusive or population-specific journal",
            "alternatives": ["Comparative study across multiple demographic groups", "Qualitative phenomenological study"],
        }
    ],
    GapType.INDUSTRY: [
        {
            "question": "How does the phenomenon of {topic} vary across industry sectors?",
            "rationale": "Existing {topic} research is sector-agnostic; industry-specific patterns are unknown.",
            "novelty": "First sector-specific analysis of {gap_type} dynamics in {topic}.",
            "method": "multi-industry survey or comparative case study",
            "contribution": "Industry-specific {topic} guidelines and benchmarks.",
            "aim": "identify sector-specific patterns and implications of {topic}",
            "journal": "industry-specific or management journal",
            "alternatives": ["Single-industry deep-dive case study", "Cross-sector comparative analysis"],
        }
    ],
    GapType.TEMPORAL: [
        {
            "question": "How do {topic} outcomes evolve over time, and what drives temporal change?",
            "rationale": "All identified studies are cross-sectional; {topic} trajectories are unknown.",
            "novelty": "First longitudinal {gap_type} investigation of {topic}.",
            "method": "longitudinal panel study",
            "contribution": "Evidence on {topic} trajectories enabling more accurate prediction.",
            "aim": "track {topic} dynamics longitudinally to identify change mechanisms",
            "journal": "longitudinal research or developmental journal",
            "alternatives": ["Cohort study design", "Experience sampling methodology"],
        }
    ],
    GapType.POLICY: [
        {
            "question": "What policy interventions most effectively support {topic} outcomes?",
            "rationale": "No rigorous evaluation exists of policy effectiveness for {topic}.",
            "novelty": "Evidence-based {gap_type} evaluation with direct relevance to governance.",
            "method": "policy evaluation or Delphi study",
            "contribution": "Policy recommendations grounded in systematic evidence on {topic}.",
            "aim": "evaluate policy mechanisms relevant to {topic} and recommend evidence-based interventions",
            "journal": "public policy or governance journal",
            "alternatives": ["Natural experiment exploitation", "Comparative policy analysis"],
        }
    ],
    GapType.EDUCATIONAL: [
        {
            "question": "What educational interventions most effectively build competencies in {topic}?",
            "rationale": "No rigorous evaluation of educational programs addressing {topic} competencies exists.",
            "novelty": "First {gap_type} assessment of training effectiveness in {topic}.",
            "method": "educational intervention study",
            "contribution": "Evidence-based curriculum recommendations for {topic} educators.",
            "aim": "design and evaluate {topic}-focused educational interventions",
            "journal": "educational research or training journal",
            "alternatives": ["Curriculum review and redesign study", "Comparative pedagogy study"],
        }
    ],
    GapType.HEALTHCARE: [
        {
            "question": "What clinical interventions produce the best outcomes for patients dealing with {topic}?",
            "rationale": "Clinical evidence on {topic} is based on small or non-representative samples.",
            "novelty": "Provides {gap_type} evidence from a larger or more diverse clinical population.",
            "method": "randomised controlled trial or clinical cohort study",
            "contribution": "Clinical practice guidelines and evidence-based protocols for {topic}.",
            "aim": "evaluate clinical outcomes and optimal intervention strategies for {topic}",
            "journal": "clinical or medical journal",
            "alternatives": ["Systematic review and meta-analysis of existing trials", "Real-world evidence study"],
        }
    ],
    GapType.DIGITAL_TRANSFORMATION: [
        {
            "question": "How does digital transformation affect {topic} outcomes and processes?",
            "rationale": "Digital adoption patterns and their consequences for {topic} are underexplored.",
            "novelty": "First {gap_type} study of digital change effects on {topic}.",
            "method": "survey or longitudinal study in digital contexts",
            "contribution": "Digital transformation roadmap for {topic} practitioners.",
            "aim": "assess the impact of digital transformation on {topic} performance",
            "journal": "information systems or digital transformation journal",
            "alternatives": ["Case study of digital transformation leaders", "Survey of digital maturity and {topic} outcomes"],
        }
    ],
    GapType.SUSTAINABILITY: [
        {
            "question": "What is the relationship between sustainable practices and {topic} performance?",
            "rationale": "Sustainability integration into {topic} frameworks remains theoretically underdeveloped.",
            "novelty": "First {gap_type}-focused analysis linking ESG principles to {topic}.",
            "method": "multi-case study or survey with sustainability metrics",
            "contribution": "Evidence-based sustainability integration guidelines for {topic}.",
            "aim": "examine how sustainability initiatives influence {topic} outcomes",
            "journal": "sustainability or environmental management journal",
            "alternatives": ["Life-cycle assessment study", "Multi-sector sustainability benchmark analysis"],
        }
    ],
    GapType.INNOVATION: [
        {
            "question": "How do innovation processes and knowledge transfer mechanisms shape {topic} outcomes?",
            "rationale": "Innovation dynamics within {topic} are underexplored despite their strategic importance.",
            "novelty": "First {gap_type} examination of how R&D and innovation interact with {topic}.",
            "method": "innovation survey or R&D impact evaluation",
            "contribution": "Innovation management framework applicable to {topic} contexts.",
            "aim": "investigate how innovation capabilities drive {topic} performance",
            "journal": "innovation management or R&D journal",
            "alternatives": ["Startup ecosystem case study", "Patent analysis combined with survey data"],
        }
    ],
    GapType.AI_GAP: [
        {
            "question": "How can AI/ML methods be applied to advance understanding of {topic}?",
            "rationale": "AI approaches capable of addressing {topic} challenges have not been systematically explored.",
            "novelty": "First {gap_type} study applying advanced AI methods to {topic}.",
            "method": "experimental AI study or systematic benchmark",
            "contribution": "AI-powered tools and frameworks that accelerate {topic} research.",
            "aim": "develop and evaluate AI-assisted methods for {topic} analysis",
            "journal": "AI, data science, or computational methods journal",
            "alternatives": ["Explainable AI approach for interpretability", "Human-AI collaboration framework"],
        }
    ],
    GapType.INTERDISCIPLINARY: [
        {
            "question": "How can insights from adjacent disciplines enrich theoretical understanding of {topic}?",
            "rationale": "Disciplinary silos prevent valuable cross-pollination of methods and theories relevant to {topic}.",
            "novelty": "First {gap_type} synthesis bridging disciplines for {topic}.",
            "method": "interdisciplinary systematic review or mixed-methods convergence study",
            "contribution": "An integrated conceptual model for {topic} drawing from multiple disciplines.",
            "aim": "synthesise cross-disciplinary knowledge to advance {topic} research",
            "journal": "interdisciplinary or boundary-spanning journal",
            "alternatives": ["Multi-disciplinary expert Delphi", "Bibliometric co-citation analysis"],
        }
    ],
    GapType.FUTURE_RESEARCH: [
        {
            "question": "What are the most pressing unexplored questions in {topic} for the next decade?",
            "rationale": "The {topic} field lacks a coordinated agenda for future investigation.",
            "novelty": "Maps the {gap_type} landscape for strategic research planning.",
            "method": "Delphi method or systematic horizon scanning",
            "contribution": "A prioritised research agenda for {topic} stakeholders.",
            "aim": "identify and prioritise future research directions in {topic}",
            "journal": "review or perspective journal",
            "alternatives": ["Expert panel consultation", "Bibliometric future-trajectory analysis"],
        }
    ],
}
