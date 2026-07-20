"""Literature Agent — searches OpenAlex for real papers, synthesizes findings."""
from __future__ import annotations

import logging
import httpx

from .base_agent import AgentEvidence, AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.literature")

OPENALEX_WORKS = "https://api.openalex.org/works"


class LiteratureAgent(BaseAgent):
    name         = "literature"
    description  = "Searches real academic databases for relevant literature."
    mission      = "Find verified published papers relevant to the user's research question."
    capabilities = [
        "Literature search (OpenAlex)",
        "Related work identification",
        "Research trend analysis",
        "Reference discovery",
        "Evidence mapping",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        interests = memory.get("interests") or []
        domain    = memory.get("domain") or ""
        query_txt = task.user_input

        # Build a focused search query from user input + research interests
        search_parts = [query_txt]
        if interests:
            search_parts.extend(interests[:2])
        if domain:
            search_parts.append(domain)
        search_q = " ".join(search_parts)[:200]

        papers = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    OPENALEX_WORKS,
                    params={
                        "search":     search_q,
                        "per-page":   8,
                        "select":     "title,authorships,publication_year,doi,cited_by_count,open_access",
                        "sort":       "cited_by_count:desc",
                        "mailto":     "contact@synaptiq.io",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    papers = data.get("results") or []
        except Exception as exc:
            logger.debug("OpenAlex error: %s", exc)

        if not papers:
            return self._insufficient(task.id, [
                "Relevant papers for the given query (OpenAlex returned no results or was unreachable)"
            ])

        evidence: list[AgentEvidence] = []
        paper_lines = []
        for p in papers[:8]:
            title = p.get("title") or "Untitled"
            year  = p.get("publication_year") or "?"
            auths = ", ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in (p.get("authorships") or [])[:3]
            )
            cites = p.get("cited_by_count", 0)
            doi   = p.get("doi") or ""
            line  = f"• {title} ({year}) — {auths or 'Unknown authors'} — cited {cites}×"
            if doi:
                line += f" — doi:{doi.replace('https://doi.org/', '')}"
            paper_lines.append(line)
            evidence.append(self._ev(
                "external_api", "OpenAlex (open academic database)",
                f"'{title[:60]}' ({year}), cited {cites}×",
                url=doi or None,
            ))

        # AI synthesis of the real retrieved papers
        from services.ai.llm import call_llm
        papers_text = "\n".join(paper_lines)
        synthesis = await call_llm(
            system=(
                "You are a Literature Review Specialist. Your task is to synthesize the following "
                "verified academic papers retrieved from OpenAlex (a real academic database). "
                "ONLY reference what is listed below. Never add papers not in this list. "
                "Summarize: key themes, research directions, consensus findings, and any notable gaps visible from these results."
            ),
            user_msg=(
                f"User's research question: {task.user_input}\n\n"
                f"Papers retrieved from OpenAlex:\n{papers_text}\n\n"
                "Provide: (1) Key themes in this literature, (2) Main findings, "
                "(3) Research gaps suggested by these results, (4) Recommended reading order."
            ),
            feature="copilot_literature",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=synthesis,
            structured_data={"paper_count": len(papers), "papers": paper_lines},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient",
            limitations=[
                "Results limited to OpenAlex coverage (not all journals indexed).",
                "Full text not retrieved — analysis based on titles, authorship, and citation counts.",
            ],
        )


REGISTRY.register(LiteratureAgent())
