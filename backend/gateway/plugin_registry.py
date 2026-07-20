"""
Enterprise AI Gateway — Plugin Registry.

Every AI capability is a plugin. The Gateway loads plugins dynamically.
Adding a new AI capability never requires changes to the Gateway itself.

A plugin:
  - Has a unique name (matches feature_id in engine registry where possible)
  - Declares which prompt_ids it uses
  - Declares which context types it needs (twin, lkg, workspace, etc.)
  - Declares whether evidence is required
  - Optionally provides a custom handler for non-standard execution

All ~20 existing AI modules are auto-registered here at import time.
They work without any code changes — the plugin descriptor is metadata only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("gateway.plugin_registry")


@dataclass
class AIPlugin:
    """Descriptor for one AI capability (thin metadata — no business logic)."""
    name:            str
    label:           str
    description:     str
    prompt_ids:      list[str] = field(default_factory=list)  # from prompt_registry
    output_schema:   dict      = field(default_factory=dict)
    requires_context: list[str] = field(default_factory=list)  # ["twin","lkg","workspace"]
    require_evidence: bool      = False
    cost_estimate_credits: float = 2.0
    category:        str        = "general"   # research/writing/analytics/admin
    internal:        bool       = False       # True = system plugins, not user-selectable
    handler:         Optional[Callable] = None  # custom execution handler (optional)


class PluginRegistry:

    def __init__(self):
        self._plugins: dict[str, AIPlugin] = {}

    def register(self, plugin: AIPlugin) -> None:
        self._plugins[plugin.name] = plugin
        logger.debug("Plugin registered: %s", plugin.name)

    def get(self, name: str) -> Optional[AIPlugin]:
        return self._plugins.get(name)

    def list_plugins(self, include_internal: bool = False) -> list[dict]:
        return [
            {
                "name":          p.name,
                "label":         p.label,
                "description":   p.description,
                "category":      p.category,
                "cost_estimate": p.cost_estimate_credits,
                "requires_context": p.requires_context,
                "require_evidence": p.require_evidence,
            }
            for p in self._plugins.values()
            if include_internal or not p.internal
        ]

    def categories(self) -> list[str]:
        return sorted({p.category for p in self._plugins.values() if not p.internal})


# ── Process-level singleton ───────────────────────────────────────────────────

plugin_registry = PluginRegistry()


# ── Built-in plugin registrations ─────────────────────────────────────────────
# One entry per major existing AI module. These replace the scattered,
# feature-specific AI invocations with a single canonical descriptor.

_PLUGINS = [
    # ── Research core ─────────────────────────────────────────────────────────
    AIPlugin(
        name="literature_review",
        label="Literature Review",
        description="Synthesize academic literature and identify research gaps",
        prompt_ids=["ara.step.literature", "general.synthesis"],
        requires_context=["twin", "lkg"],
        require_evidence=True,
        cost_estimate_credits=3.0,
        category="research",
    ),
    AIPlugin(
        name="manuscript_review",
        label="Manuscript Review",
        description="AI-driven manuscript quality and peer-review simulation",
        prompt_ids=["ara.step.writing", "ara.step.reviewer"],
        requires_context=["workspace"],
        require_evidence=False,
        cost_estimate_credits=4.0,
        category="research",
    ),
    AIPlugin(
        name="statistical_review",
        label="Statistical Review",
        description="Review statistical methodology and results sections",
        prompt_ids=["ara.step.statistics"],
        require_evidence=True,
        cost_estimate_credits=3.0,
        category="research",
    ),
    AIPlugin(
        name="research_gap_finder",
        label="Research Gap Finder",
        description="Identify research gaps and novel contribution opportunities",
        prompt_ids=["general.analysis"],
        requires_context=["twin", "lkg"],
        require_evidence=True,
        cost_estimate_credits=4.0,
        category="research",
    ),
    AIPlugin(
        name="journal_matching",
        label="Journal Matching",
        description="Match manuscripts to appropriate journals",
        prompt_ids=["ara.step.journal"],
        require_evidence=True,
        cost_estimate_credits=2.0,
        category="research",
    ),
    AIPlugin(
        name="citation_agent",
        label="Citation Agent",
        description="Verify, format, and suggest citations",
        prompt_ids=["ara.step.citation"],
        require_evidence=True,
        cost_estimate_credits=2.0,
        category="research",
    ),

    # ── Writing tools ─────────────────────────────────────────────────────────
    AIPlugin(
        name="ai_rewriting",
        label="AI Rewriting",
        description="Rewrite and improve academic text quality",
        prompt_ids=["general.analysis"],
        cost_estimate_credits=2.0,
        category="writing",
    ),
    AIPlugin(
        name="abstract_generator",
        label="Abstract Generator",
        description="Generate structured academic abstracts",
        cost_estimate_credits=1.5,
        category="writing",
    ),

    # ── AI assistant interfaces ───────────────────────────────────────────────
    AIPlugin(
        name="ai_assistant",
        label="AI Research Assistant",
        description="General-purpose academic research assistant",
        prompt_ids=["general.analysis"],
        requires_context=["twin", "recent_ai"],
        cost_estimate_credits=2.0,
        category="assistant",
    ),
    AIPlugin(
        name="ai_chat",
        label="Synaptiq AI OS Chat",
        description="Multi-turn AI assistant with specialist domain agents",
        requires_context=["twin", "lkg", "recent_ai"],
        cost_estimate_credits=2.5,
        category="assistant",
    ),
    AIPlugin(
        name="copilot",
        label="Multi-Agent Copilot",
        description="Coordinates multiple specialized agents for complex research workflows",
        prompt_ids=["copilot.planning"],
        requires_context=["twin", "lkg", "workspace"],
        cost_estimate_credits=5.0,
        category="assistant",
    ),

    # ── Autonomous agents ─────────────────────────────────────────────────────
    AIPlugin(
        name="ara_step",
        label="ARA Mission Step",
        description="Autonomous Research Agent step execution",
        requires_context=["twin"],
        require_evidence=True,
        cost_estimate_credits=3.0,
        category="autonomous",
        internal=True,
    ),

    # ── Twin & personalization ────────────────────────────────────────────────
    AIPlugin(
        name="twin_recommendation",
        label="Twin Recommendations",
        description="Personalized recommendations from Digital Research Twin",
        prompt_ids=["twin.recommendation"],
        requires_context=["twin", "lkg"],
        require_evidence=True,
        cost_estimate_credits=2.0,
        category="personalization",
    ),
    AIPlugin(
        name="proactive_briefing",
        label="Proactive Briefing",
        description="AI-generated daily research briefing",
        prompt_ids=["proactive.briefing"],
        requires_context=["twin", "recent_ai"],
        require_evidence=True,
        cost_estimate_credits=1.5,
        category="personalization",
    ),
    AIPlugin(
        name="proactive_recommendation",
        label="Proactive Recommendation",
        description="Context-aware proactive research recommendation",
        prompt_ids=["proactive.recommendation"],
        requires_context=["twin", "lkg"],
        require_evidence=True,
        cost_estimate_credits=1.5,
        category="personalization",
    ),

    # ── Analytics ─────────────────────────────────────────────────────────────
    AIPlugin(
        name="collaboration_intelligence",
        label="Collaboration Intelligence",
        description="Analyze collaboration potential and research synergies",
        requires_context=["lkg"],
        require_evidence=True,
        cost_estimate_credits=3.0,
        category="analytics",
    ),
    AIPlugin(
        name="institution_intelligence",
        label="Institution Intelligence",
        description="AI-driven institutional research analytics",
        requires_context=["institution"],
        cost_estimate_credits=3.0,
        category="analytics",
    ),
    AIPlugin(
        name="career_intelligence",
        label="Career Intelligence",
        description="Career trajectory analysis and milestone recommendations",
        requires_context=["twin"],
        require_evidence=True,
        cost_estimate_credits=3.0,
        category="analytics",
    ),

    # ── Funding ───────────────────────────────────────────────────────────────
    AIPlugin(
        name="grant_matching",
        label="Grant Matching",
        description="Match researchers to funding opportunities",
        requires_context=["twin"],
        require_evidence=True,
        cost_estimate_credits=2.0,
        category="funding",
    ),
    AIPlugin(
        name="grant_writer",
        label="Grant Writer",
        description="Draft grant application sections",
        requires_context=["twin"],
        cost_estimate_credits=6.0,
        category="funding",
    ),

    # ── Teaching ──────────────────────────────────────────────────────────────
    AIPlugin(
        name="teaching_assistant",
        label="Teaching Assistant",
        description="Lesson generation, assessment creation, teaching support",
        cost_estimate_credits=2.0,
        category="teaching",
    ),

    # ── Validation (internal) ─────────────────────────────────────────────────
    AIPlugin(
        name="response_validator",
        label="Response Validator",
        description="Evidence grounding and quality check for AI outputs",
        cost_estimate_credits=0.5,
        category="governance",
        internal=True,
    ),
]

for _p in _PLUGINS:
    plugin_registry.register(_p)
