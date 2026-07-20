"""Orchestrator — routes user messages to the correct specialist agent."""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("synaptiq.ai.orchestrator")

AGENT_TYPES = {
    "research": "ResearchAgent",
    "publication": "PublicationAgent",
    "journal": "JournalAgent",
    "grant": "GrantAgent",
    "collaboration": "CollaborationAgent",
    "teaching": "TeachingAgent",
    "analytics": "AnalyticsAgent",
    "profile": "ProfileAgent",
    "general": "GeneralAgent",
}

# ── Keyword routing patterns ──────────────────────────────────────────────────
# Ordered from most specific to least specific.
# Each entry: (agent_type, list_of_keyword_patterns)
_ROUTING_RULES: list[tuple[str, list[str]]] = [
    ("analytics", [
        r"\bcitation[s]?\b", r"\bh[\-\s]?index\b", r"\banalytic[s]?\b",
        r"\bimpact score\b", r"\bsis\b", r"\bbenchmark\b", r"\bproductivity\b",
        r"\bmetric[s]?\b", r"\bcitation[s]?\s+growth\b", r"\bperformance\b",
        r"\bcareer roadmap\b", r"\bgrowth analysis\b",
    ]),
    ("journal", [
        r"\bjournal\b", r"\bpublish\s+where\b", r"\bsubmit\s+to\b",
        r"\bpredatory\b", r"\bimpact factor\b", r"\bquartile\b",
        r"\bopen access\b", r"\bdesk rejection\b", r"\bjournals\b",
        r"\bscimago\b", r"\bwhere\s+to\s+publish\b", r"\bsubmission\s+strategy\b",
        r"\bjcr\b", r"\bq1\b", r"\bq2\b", r"\bq3\b", r"\bq4\b",
    ]),
    ("grant", [
        r"\bgrant\b", r"\bfunding\b", r"\bproposal\b", r"\bfellowship\b",
        r"\bscholarship\b", r"\baward\b", r"\bnsf\b", r"\bnih\b", r"\bercg\b",
        r"\bhorizon\s+europe\b", r"\bgrant\s+application\b", r"\bfund[s]?\b",
        r"\bgrant\s+writing\b", r"\bgrant\s+readiness\b",
    ]),
    ("collaboration", [
        r"\bcollaborat\w*\b", r"\bpartner\b", r"\bteam\b", r"\bmentor\b",
        r"\breviewer\b", r"\bexpert\b", r"\bco[\-\s]?author\b",
        r"\bcollaborator[s]?\b", r"\bnetwork\b", r"\bfind\s+researchers\b",
        r"\bjoin\s+a\s+team\b", r"\bteam\s+building\b",
    ]),
    ("teaching", [
        r"\bteach\w*\b", r"\blesson\b", r"\bcourse\b", r"\bstudent\b",
        r"\bcurriculum\b", r"\bassessment\b", r"\brubric\b", r"\bpedagog\w*\b",
        r"\blearning outcome\b", r"\bbloom\b", r"\bclassroom\b", r"\blecture\b",
        r"\bsyllabus\b", r"\bteaching\s+portfolio\b",
    ]),
    ("profile", [
        r"\bcareer\b", r"\bpromotion\b", r"\btenure\b", r"\bcv\b",
        r"\bportfolio\b", r"\breadiness\b", r"\bbrand\w*\b",
        r"\bphd\s+completion\b", r"\bpostdoc\b", r"\bcareer\s+strategy\b",
        r"\bprofile\s+optim\w*\b", r"\bacademic\s+position\b",
        r"\bvisibility\b", r"\bjob\s+market\b",
    ]),
    ("publication", [
        r"\bmanuscript\b", r"\bpaper\b", r"\babstract\b", r"\bwriting\b",
        r"\bsection\b", r"\bconclusion\b", r"\bintroduction\b",
        r"\bliterature\s+review\b", r"\bresults\b", r"\bdiscussion\b",
        r"\bmethod\w*\b", r"\breviewer\s+comment\b", r"\breview\s+response\b",
        r"\bpublication\b", r"\bsubmit\s+my\b", r"\bwrite\b",
        r"\bdraft\b", r"\bcitation\s+style\b", r"\breferences\b",
    ]),
    ("research", [
        r"\bresearch\s+idea\b", r"\bresearch\s+gap\b", r"\bresearch\s+question\b",
        r"\bhypothes\w*\b", r"\bmethodology\b", r"\bvariable\b",
        r"\bsampl\w*\b", r"\bstatistic\w*\b", r"\bnovelty\b",
        r"\bfeasibility\b", r"\btheoretical\s+framework\b",
        r"\bconceptual\s+framework\b", r"\bmixed\s+method\b",
        r"\bqualitative\b", r"\bquantitative\b", r"\bdata\s+collection\b",
        r"\bresearch\s+design\b", r"\bresearch\s+plan\b",
    ]),
]


async def detect_agent(user_message: str, context: dict) -> str:
    """
    Use a lightweight heuristic + keyword matching to detect the appropriate agent.
    Does NOT call LLM — this must be fast and free.

    Returns agent type string.
    """
    msg_lower = user_message.lower()

    # Score each agent type by counting matching patterns
    scores: dict[str, int] = {agent: 0 for agent in AGENT_TYPES}

    for agent_type, patterns in _ROUTING_RULES:
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                scores[agent_type] += 1

    # Find the highest score
    best_agent = "general"
    best_score = 0
    for agent_type, score in scores.items():
        if agent_type == "general":
            continue
        if score > best_score:
            best_score = score
            best_agent = agent_type

    # Only route to specialist if we have at least one confident match
    if best_score == 0:
        return "general"

    return best_agent


def _get_agent_instance(agent_type: str):
    """Lazily import and return the correct agent instance."""
    # Import here to avoid circular imports and keep the module lightweight
    if agent_type == "research":
        from services.synaptiq_ai.agents.research_agent import ResearchAgent
        return ResearchAgent()
    if agent_type == "publication":
        from services.synaptiq_ai.agents.publication_agent import PublicationAgent
        return PublicationAgent()
    if agent_type == "journal":
        from services.synaptiq_ai.agents.journal_agent import JournalAgent
        return JournalAgent()
    if agent_type == "grant":
        from services.synaptiq_ai.agents.grant_agent import GrantAgent
        return GrantAgent()
    if agent_type == "collaboration":
        from services.synaptiq_ai.agents.collaboration_agent import CollaborationAgent
        return CollaborationAgent()
    if agent_type == "teaching":
        from services.synaptiq_ai.agents.teaching_agent import TeachingAgent
        return TeachingAgent()
    if agent_type == "analytics":
        from services.synaptiq_ai.agents.analytics_agent import AnalyticsAgent
        return AnalyticsAgent()
    if agent_type == "profile":
        from services.synaptiq_ai.agents.profile_agent import ProfileAgent
        return ProfileAgent()
    # Default: general
    from services.synaptiq_ai.agents.general_agent import GeneralAgent
    return GeneralAgent()


async def route_and_respond(
    user_message: str,
    conversation_history: list[dict],
    context: dict,
    db,
    agent_type: str | None = None,
) -> dict:
    """
    Main orchestration entry point.

    1. Detect agent (or use override)
    2. Get agent instance
    3. Call agent.respond()
    4. Return structured response

    Returns:
    {
      "response": str,
      "agent_type": str,
      "suggested_actions": list[dict],
      "sources": list[dict],
      "tokens_used": int,
    }
    """
    # Step 1: detect or use override
    if agent_type and agent_type in AGENT_TYPES:
        resolved_type = agent_type
    else:
        resolved_type = await detect_agent(user_message, context)

    logger.info(
        "orchestrator routing: agent_type=%s override=%s message_len=%d",
        resolved_type, agent_type, len(user_message),
    )

    # Step 2: get agent instance
    agent = _get_agent_instance(resolved_type)

    # Step 3: call agent
    result = await agent.respond(
        user_message=user_message,
        conversation_history=conversation_history,
        context=context,
        db=db,
    )

    # Step 4: return structured response (agent.respond already returns the right shape)
    return result
