"""Career Development Agent (Phase XIII)."""
from __future__ import annotations

import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_CAREER_STAGE_SIGNALS = {
    "phd_student": ["phd student", "doctoral candidate", "doctoral student", "completing phd"],
    "postdoc": ["postdoc", "post-doctoral", "research associate", "research fellow"],
    "early_career": ["early career", "junior lecturer", "assistant professor", "junior researcher"],
    "mid_career": ["associate professor", "senior lecturer", "mid-career", "established researcher"],
    "senior": ["full professor", "chair", "director", "dean", "senior professor"],
}

_CAREER_GOALS = {
    "academic_position": ["tenure", "permanent position", "academic job", "faculty position"],
    "publication_record": ["publication record", "h-index", "impact factor", "citations"],
    "grant_funding": ["grant", "funding", "fellowship", "award"],
    "leadership": ["leadership", "team lead", "head of", "department"],
    "industry": ["industry", "non-academic", "private sector", "startup"],
}

_CAREER_ADVICE: dict[str, list[str]] = {
    "phd_student": [
        "Aim for 2–3 peer-reviewed publications before thesis submission",
        "Attend at least one major conference per year for networking",
        "Apply for 2–3 grants during your PhD to build funding track record",
        "Build your academic profile: ORCID, Google Scholar, ResearchGate",
        "Identify potential postdoc supervisors 12 months before graduation",
    ],
    "postdoc": [
        "Target Q1 first-author publications to strengthen your profile",
        "Apply for fellowship grants (ERC Starting Grant, MSCA) early",
        "Build international collaborations through conferences",
        "Develop teaching experience — apply to teach modules",
        "Track your h-index and citation metrics regularly",
    ],
    "early_career": [
        "Apply for NSF CAREER/ERC Starting Grant within eligibility window",
        "Establish an independent research group — recruit first PhD students",
        "Publish in Q1 journals consistently for tenure review",
        "Build editorial board and reviewer experience",
        "Develop a distinctive research identity separate from your PhD supervisor",
    ],
    "mid_career": [
        "Apply for large grants (ERC Consolidator, NIH R01)",
        "Build a research centre or flagship collaboration",
        "Take on editorial board roles and leadership positions",
        "Mentor early-career researchers strategically",
        "Write a research monograph or textbook",
    ],
    "senior": [
        "Focus on research legacy and high-impact collaborative projects",
        "Chair major conferences and editorial boards",
        "Champion open science and reproducibility practices",
        "Mentor the next generation of research leaders",
    ],
}


@AgentRegistry.register
class CareerDevelopmentAgent(AcademicAgent):
    agent_id = "career_development_agent_v1"
    agent_type = AgentType.CAREER_DEVELOPMENT
    name = "Career Development Agent"
    domain = "Academic Career Strategy"
    capabilities = [
        "career_stage_assessment", "career_goal_alignment",
        "publication_strategy", "grant_timeline_planning", "network_building",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()
        profile = context.user_profile or task.metadata.get("user_profile", {})

        # Detect career stage
        stage = next(
            (k for k, signals in _CAREER_STAGE_SIGNALS.items()
             if any(s in text_lower for s in signals)),
            profile.get("career_stage", "early_career"),
        )

        # Goals
        detected_goals = [
            g for g, signals in _CAREER_GOALS.items()
            if any(s in text_lower for s in signals)
        ]

        advice = _CAREER_ADVICE.get(stage, _CAREER_ADVICE["early_career"])

        # Publication context from other agents
        pub_result = context.get_result(AgentType.PUBLICATION_STRATEGY)
        pub_note = ""
        if pub_result and pub_result.output.get("top_target_journal"):
            pub_note = f"Your target journal '{pub_result.output['top_target_journal']}' aligns with career progression."

        confidence = 0.78

        output = {
            "detected_career_stage": stage,
            "detected_goals": detected_goals,
            "career_advice": advice,
            "publication_alignment_note": pub_note,
            "priority_actions": advice[:3],
            "career_metrics_to_track": [
                "h-index (Google Scholar)", "Total citations", "Publication count (Q1/Q2)",
                "Grant funding secured", "PhD students supervised",
            ],
            "next_milestone": advice[0] if advice else "Define your career goals",
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Career stage detected: {stage}. "
                f"Goals: {', '.join(detected_goals) or 'not specified'}. "
                f"Generated {len(advice)} tailored recommendations."
            ),
            evidence=[stage] + detected_goals[:3],
            t0=t0,
        )
