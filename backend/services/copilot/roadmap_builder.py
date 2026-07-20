"""Academic Copilot — Roadmap Builder (Phase XI).

Generates structured academic roadmaps using rule-based phase templates
plus an optional AI narrative layer. All roadmap types return an
AcademicRoadmap ready to be serialised to JSON.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from .models import AcademicRoadmap, RoadmapMilestone, RoadmapPhase, RoadmapType

logger = logging.getLogger("synaptiq.copilot.roadmap")


# ── Phase templates ───────────────────────────────────────────────────────────

def _research_phases(topic: str, career_stage: str = "phd") -> list[RoadmapPhase]:
    return [
        RoadmapPhase(
            phase=1, title="Topic Definition & Scoping", duration_weeks=3,
            objectives=["Finalise research topic", "Define research questions", "Identify key constructs"],
            tasks=["Brainstorm 5–10 potential research angles", "Write 1-page scope document",
                   "Consult with supervisor/mentor", "Search databases for existing reviews"],
            milestones=[RoadmapMilestone(3, "Approved research topic", "Signed scope document", True)],
            risks=["Topic too broad", "No clear novelty", "Supervisor disagreement"],
        ),
        RoadmapPhase(
            phase=2, title="Literature Review", duration_weeks=6,
            objectives=["Synthesise existing research", "Identify gaps", "Build theoretical framework"],
            tasks=["Search 5+ databases (Scopus, WoS, PubMed, ERIC, PsycINFO)",
                   "Import references into Zotero/Mendeley", "Write synthesis matrix",
                   "Identify 3+ underexplored gaps"],
            milestones=[
                RoadmapMilestone(5, "Database search complete", "PRISMA flowchart", True),
                RoadmapMilestone(9, "Literature review draft", "Synthesis matrix", True),
            ],
            risks=["Literature too vast", "Missing seminal papers", "Poor keyword strategy"],
        ),
        RoadmapPhase(
            phase=3, title="Research Design & Methodology", duration_weeks=4,
            objectives=["Select research paradigm", "Design data collection", "Plan analysis"],
            tasks=["Justify methodology choice", "Design instruments (survey/interview guide)",
                   "Plan sampling strategy", "Select statistical methods",
                   "Write methodology chapter draft"],
            milestones=[RoadmapMilestone(13, "Methodology chapter draft", "Ethics application", True)],
            risks=["Inappropriate methodology", "Ethics delays", "Instrument validity issues"],
        ),
        RoadmapPhase(
            phase=4, title="Data Collection", duration_weeks=8,
            objectives=["Collect primary data", "Ensure sample adequacy", "Manage data quality"],
            tasks=["Pilot test instrument", "Recruit participants", "Collect data",
                   "Monitor response rate", "Clean and code data"],
            milestones=[
                RoadmapMilestone(16, "Pilot complete", "Revised instrument", False),
                RoadmapMilestone(21, "Data collection complete", "Clean dataset", True),
            ],
            risks=["Low response rate", "Data quality issues", "Recruitment failure", "Ethical breaches"],
        ),
        RoadmapPhase(
            phase=5, title="Data Analysis", duration_weeks=5,
            objectives=["Execute statistical analyses", "Test hypotheses", "Interpret findings"],
            tasks=["Run descriptive statistics", "Test assumptions", "Execute main analyses",
                   "Produce tables and figures", "Interpret effect sizes and CIs"],
            milestones=[RoadmapMilestone(26, "Analysis complete", "Results chapter draft", True)],
            risks=["Violated assumptions", "Underpowered study", "Software issues"],
        ),
        RoadmapPhase(
            phase=6, title="Write-up & Submission", duration_weeks=8,
            objectives=["Draft full manuscript", "Incorporate feedback", "Submit to target journal"],
            tasks=["Write results chapter", "Write discussion", "Complete introduction",
                   "Format to target journal style", "Address co-author feedback",
                   "Submit manuscript"],
            milestones=[
                RoadmapMilestone(30, "Full draft complete", "Draft manuscript", True),
                RoadmapMilestone(34, "Manuscript submitted", "Submission confirmation", True),
            ],
            risks=["Desk rejection", "Co-author delays", "Poor discussion", "Formatting errors"],
        ),
    ]


def _publication_phases(journal: str = "target journal") -> list[RoadmapPhase]:
    return [
        RoadmapPhase(
            phase=1, title="Manuscript Readiness Assessment", duration_weeks=2,
            objectives=["Evaluate manuscript quality", "Identify gaps and weaknesses"],
            tasks=["Run Manuscript Intelligence review", "Check all required sections",
                   "Assess literature coverage", "Check statistical reporting"],
            milestones=[RoadmapMilestone(2, "Readiness report", "Prioritised issue list", True)],
            risks=["Major gaps identified", "Statistical errors", "Weak theoretical contribution"],
        ),
        RoadmapPhase(
            phase=2, title="Critical Revisions", duration_weeks=4,
            objectives=["Fix critical and major issues", "Strengthen contribution"],
            tasks=["Address each critical issue", "Expand literature review if needed",
                   "Fix statistical reporting (effect sizes, CIs, power)",
                   "Strengthen discussion and limitations"],
            milestones=[RoadmapMilestone(6, "Revised manuscript", "Tracked-changes version", True)],
            risks=["Scope creep", "New analyses needed", "Co-author delays"],
        ),
        RoadmapPhase(
            phase=3, title="Journal Selection & Formatting", duration_weeks=1,
            objectives=[f"Confirm {journal}", "Format to submission requirements"],
            tasks=["Run Journal Matching engine", "Check author guidelines",
                   "Format references (APA/Vancouver/etc.)", "Prepare cover letter",
                   "Prepare supplementary materials"],
            milestones=[RoadmapMilestone(7, "Submission package ready", "Formatted manuscript + cover letter", True)],
            risks=["Wrong format", "Missed requirements", "Predatory journal risk"],
        ),
        RoadmapPhase(
            phase=4, title="Submission & Review", duration_weeks=16,
            objectives=["Submit manuscript", "Respond to reviewers"],
            tasks=["Submit via journal portal", "Track submission status",
                   "Prepare reviewer response template", "Address reviewer comments methodically"],
            milestones=[
                RoadmapMilestone(8, "Manuscript submitted", "Submission ID", True),
                RoadmapMilestone(24, "Revision submitted (if required)", "Revision document", False),
            ],
            risks=["Desk rejection", "Major revision required", "Long review time"],
        ),
        RoadmapPhase(
            phase=5, title="Acceptance & Post-Publication", duration_weeks=4,
            objectives=["Finalise proofs", "Maximise impact"],
            tasks=["Review proofs carefully", "Register article in ORCID",
                   "Share on ResearchGate / academia.edu", "Tweet/LinkedIn announcement",
                   "Monitor early citations"],
            milestones=[RoadmapMilestone(28, "Article published", "DOI / Published URL", True)],
            risks=["Proof errors missed", "Low discoverability", "Altmetric gap"],
        ),
    ]


def _grant_phases(funder: str = "target funder") -> list[RoadmapPhase]:
    return [
        RoadmapPhase(
            phase=1, title="Opportunity Identification", duration_weeks=2,
            objectives=["Identify matching funding calls", "Assess eligibility"],
            tasks=["Search grant databases", "Read eligibility criteria",
                   f"Confirm alignment with {funder} priorities",
                   "Identify required collaborators/institutions"],
            milestones=[RoadmapMilestone(2, "Target grant confirmed", "Eligibility checklist", True)],
            risks=["Ineligibility discovered late", "Multiple competing calls"],
        ),
        RoadmapPhase(
            phase=2, title="Proposal Development", duration_weeks=8,
            objectives=["Draft all required sections", "Build budget", "Secure co-applicants"],
            tasks=["Write project narrative", "Develop work packages",
                   "Build Gantt chart", "Prepare budget justification",
                   "Write impact statement", "Collect institutional approvals"],
            milestones=[
                RoadmapMilestone(6, "First draft complete", "Full proposal draft", True),
                RoadmapMilestone(10, "Internal review complete", "Reviewed proposal", True),
            ],
            risks=["Budget errors", "Missing sections", "Weak impact statement"],
        ),
        RoadmapPhase(
            phase=3, title="Review & Refinement", duration_weeks=3,
            objectives=["Incorporate feedback", "Strengthen proposal"],
            tasks=["Share with 2+ internal reviewers", "Revise narrative",
                   "Check submission system requirements", "Finalsie CV/biographies"],
            milestones=[RoadmapMilestone(13, "Final proposal ready", "Submission-ready package", True)],
            risks=["Last-minute changes", "System upload issues"],
        ),
        RoadmapPhase(
            phase=4, title="Submission & Wait", duration_weeks=24,
            objectives=["Submit on time", "Prepare for interviews if required"],
            tasks=["Submit via funder portal", "Prepare interview presentation",
                   "Plan project start-up activities"],
            milestones=[
                RoadmapMilestone(14, "Grant submitted", "Submission confirmation", True),
                RoadmapMilestone(38, "Decision received", "Award / Rejection letter", True),
            ],
            risks=["Portal issues", "Missing co-applicant signatures", "Interview underperformance"],
        ),
    ]


def _career_phases(career_stage: str = "phd") -> list[RoadmapPhase]:
    stage_lower = career_stage.lower()

    if "phd" in stage_lower or "doctoral" in stage_lower:
        return [
            RoadmapPhase(phase=1, title="Foundation", duration_weeks=12,
                objectives=["Complete coursework", "Pass qualifying exam", "Form committee"],
                tasks=["Meet weekly with supervisor", "Attend 2 conferences this year",
                       "Identify dissertation topic", "Begin literature review"],
                milestones=[RoadmapMilestone(12, "Qualifying exam passed", "Committee formed", True)]),
            RoadmapPhase(phase=2, title="Research Execution", duration_weeks=52,
                objectives=["Collect and analyse data", "Submit 2 journal articles"],
                tasks=["Implement research plan", "Submit chapter 1 by month 9",
                       "Present at 1 international conference"],
                milestones=[
                    RoadmapMilestone(26, "First journal submission", "Paper submitted", True),
                    RoadmapMilestone(52, "Two publications submitted", "Preprints / submissions", True),
                ]),
            RoadmapPhase(phase=3, title="Write-up & Defence", duration_weeks=26,
                objectives=["Complete thesis", "Defend successfully"],
                tasks=["Write dissertation", "Thesis review with committee",
                       "Submit 3 months before defence", "Prepare defence presentation"],
                milestones=[
                    RoadmapMilestone(20, "Thesis submitted", "Full thesis", True),
                    RoadmapMilestone(26, "PhD awarded", "Degree certificate", True),
                ]),
        ]
    elif "postdoc" in stage_lower:
        return [
            RoadmapPhase(phase=1, title="Establish Research Programme", duration_weeks=12,
                objectives=["Publish from PhD", "Apply for first grant", "Build network"],
                tasks=["Submit 2 publications", "Apply for 3 fellowships",
                       "Attend and present at 2 conferences", "Build mentorship relationships"],
                milestones=[RoadmapMilestone(12, "First postdoc grant submitted", "Application", True)]),
            RoadmapPhase(phase=2, title="Independence & Impact", duration_weeks=52,
                objectives=["Secure independent funding", "Mentor junior researchers"],
                tasks=["Lead research group projects", "Co-supervise PhD students",
                       "Build institutional profile", "Apply for faculty positions"],
                milestones=[RoadmapMilestone(52, "Faculty application submitted", "Job application", True)]),
        ]
    else:  # faculty/general
        return [
            RoadmapPhase(phase=1, title="Establish Research Identity", duration_weeks=24,
                objectives=["Define research niche", "Build publication record"],
                tasks=["Publish 2 high-impact papers per year", "Apply for 2+ grants",
                       "Build international collaborations", "Establish lab/research group"],
                milestones=[RoadmapMilestone(24, "Research identity established", "ORCID profile + 5 publications", True)]),
            RoadmapPhase(phase=2, title="Recognition & Influence", duration_weeks=52,
                objectives=["Achieve H-index target", "Lead funded research programme"],
                tasks=["Secure major grant", "Review for top journals", "Keynote invitation",
                       "PhD student completions"],
                milestones=[RoadmapMilestone(52, "Promotion application ready", "Portfolio document", True)]),
        ]


# ── Roadmap type dispatch ──────────────────────────────────────────────────────

def _build_phases(
    roadmap_type: RoadmapType,
    context: dict,
    params: dict,
) -> list[RoadmapPhase]:
    profile = context.get("profile") or {}
    career_stage = params.get("career_stage") or profile.get("academic_role") or "researcher"
    topic        = params.get("topic") or (context.get("memory") or [{"content": "your research topic"}])[0].get("content", "your research topic")
    journal      = params.get("journal") or "target journal"
    funder       = params.get("funder") or "target funder"

    if roadmap_type == RoadmapType.RESEARCH:
        return _research_phases(topic, career_stage)
    if roadmap_type == RoadmapType.PUBLICATION:
        return _publication_phases(journal)
    if roadmap_type == RoadmapType.GRANT:
        return _grant_phases(funder)
    if roadmap_type in (RoadmapType.CAREER, RoadmapType.DOCTORAL):
        return _career_phases(career_stage)
    if roadmap_type == RoadmapType.CONFERENCE:
        return [
            RoadmapPhase(phase=1, title="Select Conference", duration_weeks=1,
                tasks=["Run Conference Matching", "Check CFP deadlines"],
                milestones=[RoadmapMilestone(1, "Conference selected", "CFP noted", True)]),
            RoadmapPhase(phase=2, title="Abstract Submission", duration_weeks=2,
                tasks=["Write abstract (250–500 words)", "Submit by CFP deadline"],
                milestones=[RoadmapMilestone(3, "Abstract submitted", "Confirmation email", True)]),
            RoadmapPhase(phase=3, title="Paper / Poster Preparation", duration_weeks=8,
                tasks=["Write full paper or design poster", "Practise presentation"],
                milestones=[RoadmapMilestone(11, "Presentation ready", "Final slide deck / poster", True)]),
        ]
    return _research_phases(topic, career_stage)


async def build_roadmap(
    roadmap_type: RoadmapType,
    context: dict,
    params: dict,
    use_ai: bool = False,
) -> AcademicRoadmap:
    phases = _build_phases(roadmap_type, context, params)
    total_weeks = sum(p.duration_weeks for p in phases)

    title_map = {
        RoadmapType.RESEARCH:    "Research Roadmap",
        RoadmapType.PUBLICATION: "Publication Roadmap",
        RoadmapType.GRANT:       "Grant Application Roadmap",
        RoadmapType.CONFERENCE:  "Conference Strategy Roadmap",
        RoadmapType.CAREER:      "Academic Career Roadmap",
        RoadmapType.DOCTORAL:    "Doctoral Completion Roadmap",
        RoadmapType.INSTITUTION: "Institution Strategy Roadmap",
    }

    roadmap = AcademicRoadmap(
        roadmap_type=roadmap_type,
        title=title_map.get(roadmap_type, "Academic Roadmap"),
        description=(
            f"A personalised {total_weeks}-week roadmap "
            f"across {len(phases)} phases."
        ),
        phases=phases,
        total_weeks=total_weeks,
        key_milestones=[
            m.title
            for p in phases
            for m in p.milestones
            if m.is_critical
        ],
        success_indicators=_success_indicators(roadmap_type),
        risk_factors=list({risk for p in phases for risk in p.risks})[:8],
    )

    if use_ai:
        roadmap.ai_narrative = await _ai_narrative(roadmap, context)

    return roadmap


def _success_indicators(rt: RoadmapType) -> list[str]:
    if rt == RoadmapType.RESEARCH:
        return ["Research question approved", "Literature review complete",
                "Data collected within schedule", "At least 1 peer-reviewed publication"]
    if rt == RoadmapType.PUBLICATION:
        return ["Manuscript accepted by target journal", "No desk rejections",
                "Positive reviewer feedback", "Altmetric score ≥ 5"]
    if rt == RoadmapType.GRANT:
        return ["Grant submitted on time", "Score in top 30%",
                "Funded on first or second attempt"]
    if rt in (RoadmapType.CAREER, RoadmapType.DOCTORAL):
        return ["Thesis submitted on time", "All publications submitted",
                "Positive viva outcome", "Secured next position"]
    return ["All milestones achieved on schedule", "Goals met without scope reduction"]


async def _ai_narrative(roadmap: AcademicRoadmap, context: dict) -> str:
    try:
        from services.ai.llm import call_llm
        system = (
            "You are an expert academic mentor. Generate a brief (3–4 paragraph) "
            "narrative for the following academic roadmap. Be specific, actionable, "
            "and encouraging. Do not fabricate data."
        )
        phase_summary = "\n".join(
            f"Phase {p.phase} ({p.duration_weeks}w): {p.title} — {', '.join(p.objectives[:2])}"
            for p in roadmap.phases
        )
        profile = context.get("profile") or {}
        name = profile.get("full_name") or "Researcher"
        msg = (
            f"Roadmap type: {roadmap.roadmap_type.value}\n"
            f"Researcher: {name}\n"
            f"Total duration: {roadmap.total_weeks} weeks\n\n"
            f"Phases:\n{phase_summary}"
        )
        narrative = await call_llm(system=system, messages=[{"role": "user", "content": msg}], feature="copilot.roadmap", max_tokens=600)
        return narrative
    except Exception as exc:
        logger.warning("roadmap AI narrative failed: %s", exc)
        return ""
