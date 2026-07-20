"""Citation Agent — citation quality, missing references, DOI validation via CrossRef."""
from __future__ import annotations

import logging
import re
import httpx

from .base_agent import AgentOutput, AgentTask, BaseAgent
from .registry import REGISTRY

logger = logging.getLogger("copilot.citation")

CROSSREF_WORKS = "https://api.crossref.org/works"
DOI_PATTERN    = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


class CitationAgent(BaseAgent):
    name         = "citation"
    description  = "Validates citations, finds missing references, and assesses citation quality."
    mission      = "Ensure all citations are real, retrievable, and appropriate for the research context."
    capabilities = [
        "DOI validation via CrossRef",
        "Missing citation identification",
        "Reference freshness analysis",
        "Citation diversity assessment",
        "Self-citation monitoring",
        "Influential paper discovery",
    ]

    async def execute(self, task: AgentTask, memory, db) -> AgentOutput:
        manuscripts = memory.get("manuscripts") or []
        user_input  = task.user_input

        evidence   = []
        dois_found = []
        validated  = []

        # Extract DOIs from user input or manuscript text
        search_text = user_input
        if manuscripts:
            ms = manuscripts[0]
            ms_title    = ms.get("title", "Untitled")[:60]
            ms_abstract = ms.get("abstract") or ms.get("content") or ""
            search_text += " " + ms_abstract
            if ms_abstract:
                evidence.append(self._ev(
                    "database_query", "Synaptiq platform database — manuscripts",
                    f"Manuscript retrieved for citation analysis: '{ms_title}'"
                ))

        dois_found = list(set(DOI_PATTERN.findall(search_text)))[:5]

        # Validate extracted DOIs via CrossRef
        if dois_found:
            async with httpx.AsyncClient(timeout=8.0) as client:
                for doi in dois_found[:5]:
                    try:
                        resp = await client.get(
                            f"{CROSSREF_WORKS}/{doi}",
                            headers={"User-Agent": "Synaptiq/1.0 (mailto:contact@synaptiq.io)"},
                        )
                        if resp.status_code == 200:
                            item = resp.json().get("message") or {}
                            title = (item.get("title") or [""])[0][:60]
                            year  = (item.get("issued") or {}).get("date-parts", [[None]])[0][0]
                            validated.append({"doi": doi, "title": title, "year": year, "valid": True})
                            evidence.append(self._ev(
                                "external_api", "CrossRef (doi.org)",
                                f"DOI validated: '{title}' ({year})" if title else f"DOI {doi} confirmed valid",
                                url=f"https://doi.org/{doi}"
                            ))
                        else:
                            validated.append({"doi": doi, "valid": False, "status": resp.status_code})
                            evidence.append(self._ev(
                                "external_api", "CrossRef (doi.org)",
                                f"DOI not found or invalid: {doi} (HTTP {resp.status_code})",
                                verified=False
                            ))
                    except Exception as exc:
                        logger.debug("CrossRef error for %s: %s", doi, exc)

        # Literature agent output for related paper suggestions
        lit_out = memory.get_agent_output("literature")
        lit_context = ""
        if lit_out and lit_out.status in ("success", "partial"):
            lit_context = f"\nRelated papers found:\n{lit_out.content[:400]}"
            evidence.append(self._ev(
                "agent_output", "Literature Agent (OpenAlex)",
                "Related papers used to identify potential missing citations"
            ))

        if not evidence:
            return self._insufficient(task.id, [
                "Citation list or manuscript with DOIs",
                "Research context for missing citation identification",
            ])

        from services.ai.llm import call_llm
        citation_advice = await call_llm(
            system=(
                "You are a Citation Quality Specialist. "
                "Your role is to help researchers improve the quality and completeness of their references. "
                "Only reference papers that are explicitly provided in the context. "
                "Never fabricate DOIs, authors, or journal names. "
                "If no citations were provided, advise on citation best practices and how to find missing references."
            ),
            user_msg=(
                f"Citation analysis request: {task.user_input}\n"
                + (f"\nDOI validation results:\n" + "\n".join(
                    f"  • {v['doi']}: {'VALID — ' + (v.get('title') or '') if v['valid'] else 'NOT FOUND (HTTP ' + str(v.get('status', '?')) + ')'}"
                    for v in validated
                ) if validated else "No DOIs found in provided text.\n")
                + lit_context
                + "\n\nProvide: (1) DOI validation summary, "
                "(2) Citation gap analysis based on available literature, "
                "(3) Self-citation risk indicators, "
                "(4) Recommendations for strengthening the reference list."
            ),
            feature="copilot_citation",
        )

        conf, conf_basis = self._conf(evidence)
        return AgentOutput(
            agent_name=self.name,
            task_id=task.id,
            status="success",
            content=citation_advice,
            structured_data={"dois_checked": len(validated), "valid_count": sum(1 for v in validated if v["valid"])},
            evidence=evidence,
            confidence=conf,
            confidence_basis=conf_basis,
            data_quality="sufficient" if validated else "partial",
            limitations=[
                "DOI validation limited to 5 DOIs per request.",
                "Only DOIs explicitly present in text are validated — missing references require manual review.",
                "CrossRef does not index all journals.",
            ],
        )


REGISTRY.register(CitationAgent())
