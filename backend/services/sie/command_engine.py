"""
SIE Command Engine — natural language command processing.
Parses user intent and dispatches orchestration actions.
No LLM required: keyword-based intent classification + structured response synthesis.
"""
import asyncio
from datetime import datetime, timezone

_INTENT_PATTERNS = {
    "publication_plan": ["publish", "paper", "manuscript", "q1", "journal", "submit", "write paper", "publication roadmap"],
    "grant_strategy": ["grant", "funding", "horizon", "nsf", "nih", "erc", "proposal", "apply for funding", "grant strategy"],
    "career_plan": ["tenure", "promotion", "professor", "career", "position", "associate", "full professor", "assistant professor"],
    "citation_impact": ["citation", "h-index", "impact", "cited", "visibility", "citation impact"],
    "research_plan": ["research plan", "roadmap", "plan for", "next six months", "next year", "research strategy"],
    "collaboration": ["collaborat", "team", "partner", "joint", "co-author", "network"],
    "daily_priorities": ["today", "priorities", "daily", "what should i", "what to do"],
    "weakness_analysis": ["weakness", "weakest", "gap", "improve", "lacking", "analysis"],
    "trust_score": ["trust score", "verification", "integrity", "credibility"],
    "teaching": ["teach", "course", "student", "lesson", "portfolio"],
}

_INTENT_RESPONSES = {
    "publication_plan": {
        "title": "Publication Plan",
        "modules": ["Publishing Intelligence", "Literature Review", "Research Gap Finder", "Manuscript Review"],
        "steps": [
            "Use Synaptiq Research Gap Finder to identify an unexplored angle.",
            "Run Literature Review to understand the state of the field.",
            "Select target journals using Publishing Intelligence.",
            "Generate a full research roadmap with built-in writing schedule.",
            "Use Manuscript Review before submission to maximise acceptance probability.",
        ],
        "action_url": "/sie/planning",
    },
    "grant_strategy": {
        "title": "Grant Strategy",
        "modules": ["Grant Hub", "Grant Collaboration Hub", "Career Planner"],
        "steps": [
            "Review Grant Hub for open calls matching your research profile.",
            "Use Grant Collaboration Hub to build a consortium if required.",
            "Align your research narrative with the funder's strategic priorities.",
            "Allocate 8 weeks minimum for proposal writing and internal review.",
        ],
        "action_url": "/sie/grants",
    },
    "career_plan": {
        "title": "Career Planning",
        "modules": ["Career Planner", "Reputation System", "Teaching Hub"],
        "steps": [
            "Define your current position and target position in Career Planner.",
            "Check your promotion readiness score against institutional requirements.",
            "Build your publication, grant, and teaching portfolio systematically.",
            "Track your academic reputation score monthly.",
        ],
        "action_url": "/sie/career",
    },
    "citation_impact": {
        "title": "Citation Impact Strategy",
        "modules": ["Publishing Intelligence", "Research Impact Dashboard", "Public Profile"],
        "steps": [
            "Target journals with high visibility in your discipline.",
            "Publish preprints to reach audiences before formal publication.",
            "Ensure your Public Research Profile is complete and up to date.",
            "Monitor citations via Citation Monitoring tools.",
        ],
        "action_url": "/research-impact",
    },
    "research_plan": {
        "title": "Research Plan",
        "modules": ["Research Roadmap", "Research Gap Finder", "Literature Review"],
        "steps": [
            "Define 2-3 research questions for the next 6 months.",
            "Generate a full research roadmap with 18 milestones.",
            "Break the roadmap into weekly missions.",
            "Review progress every week using the Weekly Planner.",
        ],
        "action_url": "/sie/planning",
    },
    "collaboration": {
        "title": "Collaboration Strategy",
        "modules": ["Collaboration Intelligence", "Reviewer Marketplace", "Public Profiles"],
        "steps": [
            "Use Collaboration Intelligence to find compatible researchers.",
            "Check who has cited your work — potential collaborators already know you.",
            "Join relevant research networks on Synaptiq Discover.",
            "Propose a joint grant to formalise a collaboration.",
        ],
        "action_url": "/collaboration-intelligence",
    },
    "daily_priorities": {
        "title": "Today's Priorities",
        "modules": ["Daily Agenda", "Mission Engine", "Goal Manager"],
        "steps": [
            "Review your AI-generated Daily Agenda.",
            "Complete the highest-priority mission on your list.",
            "Check for any approaching deadlines in Goal Manager.",
            "Spend 30 minutes on a writing task.",
        ],
        "action_url": "/sie/daily",
    },
    "weakness_analysis": {
        "title": "Academic Weakness Analysis",
        "modules": ["Integrity Engine", "Research Impact", "Reputation System"],
        "steps": [
            "Check your Integrity Report for credential verification gaps.",
            "Review your Research Impact Dashboard for citation weaknesses.",
            "Use Benchmark Center to compare against institutional averages.",
            "Generate AI recommendations in the Synaptiq Intelligence Engine.",
        ],
        "action_url": "/sie/recommendations",
    },
    "trust_score": {
        "title": "Trust Score Improvement",
        "modules": ["Verification Center", "Integrity Engine", "Academic Passport"],
        "steps": [
            "Complete your Academic Passport with all credentials.",
            "Run the Integrity Engine to detect and resolve verification gaps.",
            "Connect ORCID and confirm your institutional affiliation.",
            "Request peer verifications through the Trust Center.",
        ],
        "action_url": "/trust",
    },
    "teaching": {
        "title": "Teaching Portfolio",
        "modules": ["Teaching Hub", "Teaching Analytics"],
        "steps": [
            "Create or update your lessons in Teaching Hub.",
            "Track student engagement with Teaching Analytics.",
            "Document courses for promotion portfolio evidence.",
        ],
        "action_url": "/teaching",
    },
}


def _classify_intent(command: str) -> str:
    command_lower = command.lower()
    scores: dict[str, int] = {}
    for intent, keywords in _INTENT_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in command_lower)
        if score > 0:
            scores[intent] = score
    if not scores:
        return "research_plan"
    return max(scores, key=scores.get)


def _compose_response(intent: str, user_name: str) -> dict:
    template = _INTENT_RESPONSES.get(intent, _INTENT_RESPONSES["research_plan"])
    return {
        "intent": intent,
        "title": template["title"],
        "summary": f"Here is your AI-generated {template['title']} for {user_name or 'you'}. Follow these steps using the coordinated Synaptiq modules.",
        "modules_invoked": template["modules"],
        "action_steps": template["steps"],
        "primary_action_url": template["action_url"],
    }


async def process_command(user_id: str, command: str, user_name: str, db) -> dict:
    intent = _classify_intent(command)
    response = _compose_response(intent, user_name)

    record = {
        "user_id": user_id,
        "command": command,
        "intent": intent,
        "response": response,
        "executed_at": datetime.now(timezone.utc),
    }
    await db.sie_commands.insert_one(record)

    return {
        **response,
        "command": command,
        "executed_at": record["executed_at"].isoformat(),
    }


async def get_command_history(user_id: str, db, limit: int = 20) -> list:
    cursor = db.sie_commands.find({"user_id": user_id}).sort("executed_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    result = []
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
        if hasattr(d.get("executed_at"), "isoformat"):
            d["executed_at"] = d["executed_at"].isoformat()
        result.append(d)
    return result
