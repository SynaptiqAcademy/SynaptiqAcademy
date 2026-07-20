"""Base agent class for all Synaptiq AI agents."""
from __future__ import annotations

import logging
import re

from services.ai.llm import call_llm

logger = logging.getLogger("synaptiq.ai.agents.base")

SYNAPTIQ_MISSION = """You are Synaptiq AI — the central intelligence layer of Synaptiq Academy, an academic research platform.
You are not a generic chatbot. You are a specialized academic AI that understands the user's research profile,
publications, projects, collaborations, grants, and career goals.
You behave like a combination of: Research Director, Academic Mentor, Publication Strategist, Grant Advisor,
Reviewer, Research Analyst, Collaboration Broker, Teaching Advisor.
You always:
- Reference the user's specific profile data when relevant
- Give concrete, actionable, evidence-based advice
- Cite specific platform data (their manuscripts, collaborations, etc.)
- Never make up citations, publications, or data not in the provided context
- Keep responses structured with clear headers and bullet points when appropriate
- Be direct, expert-level, and research-focused
"""


class BaseAgent:
    agent_type: str = "general"
    specialization: str = ""

    def build_system_prompt(self, context: dict) -> str:
        """Combine SYNAPTIQ_MISSION + specialization + user context summary."""
        summary = context.get("summary", "")
        profile = context.get("profile") or {}
        memory_items = context.get("memory") or []

        memory_section = ""
        if memory_items:
            memory_lines = "\n".join(
                f"  - [{m.get('memory_type', 'general')}] {m.get('content', '')}"
                for m in memory_items[:10]
            )
            memory_section = f"\n\nUSER MEMORY (saved goals and preferences):\n{memory_lines}"

        # Build a concise profile section for additional grounding
        manuscripts = context.get("manuscripts") or []
        projects = context.get("projects") or []
        collabs = context.get("collaborations") or []
        grants = context.get("grants_applied") or []
        impact = context.get("impact") or {}
        reputation = context.get("reputation") or {}

        data_section_parts = []
        if manuscripts:
            ms_lines = "; ".join(
                f"\"{m.get('title', 'Untitled')}\" ({m.get('status', '')})"
                for m in manuscripts[:5]
            )
            data_section_parts.append(f"Manuscripts: {ms_lines}")
        if projects:
            proj_lines = "; ".join(
                f"\"{p.get('title', 'Untitled')}\" ({p.get('status', '')})"
                for p in projects[:5]
            )
            data_section_parts.append(f"Projects: {proj_lines}")
        if collabs:
            collab_lines = "; ".join(
                f"\"{c.get('title', 'Untitled')}\""
                for c in collabs[:5]
            )
            data_section_parts.append(f"Collaborations: {collab_lines}")
        if grants:
            grant_lines = "; ".join(
                f"\"{g.get('grant_title', 'Unknown')}\" ({g.get('status', '')})"
                for g in grants[:5]
            )
            data_section_parts.append(f"Grant Applications: {grant_lines}")
        if impact.get("sis_total") is not None:
            data_section_parts.append(
                f"Impact: SIS={impact.get('sis_total', 0)}/10000, "
                f"H-index={impact.get('h_index', 0)}, "
                f"Publications={impact.get('publication_count', 0)}"
            )
        if reputation.get("overall_score") is not None:
            data_section_parts.append(
                f"Reputation: score={reputation.get('overall_score', 0)}, "
                f"level={reputation.get('level', 'N/A')}, "
                f"badges={len(reputation.get('badges') or [])}"
            )

        data_section = ""
        if data_section_parts:
            data_section = "\n\nUSER PLATFORM DATA:\n" + "\n".join(f"  - {p}" for p in data_section_parts)

        return (
            f"{SYNAPTIQ_MISSION}\n\n"
            f"SPECIALIZATION:\n{self.specialization}\n\n"
            f"USER CONTEXT SUMMARY:\n{summary}"
            f"{data_section}"
            f"{memory_section}"
        )

    async def respond(
        self,
        user_message: str,
        conversation_history: list[dict],
        context: dict,
        db=None,
    ) -> dict:
        """
        Build full message list with system prompt + history + user message.
        Call call_llm() with multi-turn messages.
        Extract suggested_actions and sources from response.
        Return {response, agent_type, suggested_actions, sources, tokens_used}.
        """
        system_prompt = self.build_system_prompt(context)

        # Build message list: history + current user message
        messages: list[dict] = []
        for msg in (conversation_history or []):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        try:
            response_text = await call_llm(
                system=system_prompt,
                messages=messages,
                max_tokens=3000,
                feature=f"ara.agent.{self.agent_type}",
            )
        except Exception as exc:
            logger.error("agent.respond failed agent=%s err=%s", self.agent_type, exc)
            response_text = (
                "I encountered an error processing your request. Please try again in a moment."
            )

        # Approximate token count
        tokens_used = len(response_text) // 4

        # Extract suggested actions and sources from the response
        suggested_actions = self._extract_suggested_actions(response_text, context)
        sources = self._extract_sources(response_text, context)

        return {
            "response": response_text,
            "agent_type": self.agent_type,
            "suggested_actions": suggested_actions,
            "sources": sources,
            "tokens_used": tokens_used,
        }

    def _extract_suggested_actions(self, response: str, context: dict) -> list[dict]:
        """
        Heuristically detect actionable suggestions in the response.
        Returns a list of {action_type, label, params} dicts.
        """
        actions: list[dict] = []
        lower = response.lower()

        # Detect project creation suggestion
        if any(phrase in lower for phrase in [
            "create a project", "start a project", "new project", "set up a project"
        ]):
            actions.append({
                "action_type": "create_project",
                "label": "Create Project",
                "params": {},
            })

        # Detect collaboration creation suggestion
        if any(phrase in lower for phrase in [
            "create a collaboration", "post a collaboration", "collaboration opportunity",
            "seek collaborators", "find collaborators"
        ]):
            actions.append({
                "action_type": "create_collaboration",
                "label": "Create Collaboration",
                "params": {},
            })

        # Detect manuscript creation suggestion
        if any(phrase in lower for phrase in [
            "start writing", "draft a manuscript", "create a manuscript",
            "begin writing", "write a paper"
        ]):
            actions.append({
                "action_type": "create_manuscript",
                "label": "Create Manuscript",
                "params": {},
            })

        # Detect memory save suggestion
        if any(phrase in lower for phrase in [
            "remember this", "save this goal", "keep this in mind",
            "track this", "note this"
        ]):
            actions.append({
                "action_type": "save_memory",
                "label": "Save to Memory",
                "params": {"memory_type": "general", "content": ""},
            })

        return actions[:3]  # cap at 3

    def _extract_sources(self, response: str, context: dict) -> list[dict]:
        """
        Extract platform items referenced in the response context.
        Returns a list of {type, title, id} dicts.
        """
        sources: list[dict] = []
        lower = response.lower()

        # Check manuscripts
        for m in (context.get("manuscripts") or []):
            title = m.get("title", "")
            if title and title.lower() in lower:
                sources.append({"type": "manuscript", "title": title, "id": m.get("id", "")})

        # Check projects
        for p in (context.get("projects") or []):
            title = p.get("title", "")
            if title and title.lower() in lower:
                sources.append({"type": "project", "title": title, "id": p.get("id", "")})

        # Check collaborations
        for c in (context.get("collaborations") or []):
            title = c.get("title", "")
            if title and title.lower() in lower:
                sources.append({"type": "collaboration", "title": title, "id": c.get("id", "")})

        # Check applied grants
        for g in (context.get("grants_applied") or []):
            title = g.get("grant_title", "")
            if title and title.lower() in lower:
                sources.append({"type": "grant", "title": title, "id": g.get("grant_id", "")})

        return sources[:5]  # cap at 5
