"""LiteratureIntelligenceEngine — main orchestrator for Phase VII.

Session lifecycle:
  1. create_session()
  2. add_papers() — ingest from any source
  3. analyze_papers() — 19-field AI analysis per paper
  4. compare_papers() — cross-paper comparative analysis
  5. cluster_papers() — thematic clustering
  6. detect_evolution() — chronological research evolution
  7. detect_gaps() — research gap identification
  8. generate_review() — AI-written full academic review
  9. export() — in any of 6 formats
 10. get_visualizations() — all visualization data for frontend

All sessions and papers persist in MongoDB across requests.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from services.literature.analysis.clustering import cluster_papers, label_clusters_with_ai_hint
from services.literature.analysis.comparative import run_comparative_analysis
from services.literature.analysis.evolution import build_evolution
from services.literature.analysis.gap_detector import detect_gaps
from services.literature.analysis.paper_analyzer import analyze_batch
from services.literature.citation.citation_engine import (
    build_citation_network, compute_author_collaboration_graph,
    identify_foundational_works,
)
from services.literature.export.export_engine import export_session
from services.literature.ingestion.ingestion_engine import IngestionEngine
from services.literature.models import (
    ExportFormat, Paper, PaperAnalysis, PaperSource,
    ReviewSession, ReviewType, SessionStatus,
)
from services.literature.synthesis.review_generator import generate_review
from services.literature.synthesis.templates import all_templates
from services.literature.telemetry import LiteratureIntelligenceTelemetry, get_literature_telemetry
from services.literature.visualization.graph_builder import build_all_visualizations
from repo.shim import make_db_proxy

log = logging.getLogger("synaptiq.literature.engine")

_COL_SESSIONS = "lit_sessions"
_COL_PAPERS = "lit_papers"


class LiteratureIntelligenceEngine:
    """Orchestrates all literature intelligence operations."""

    def __init__(self, db: Any) -> None:
        self._db = make_db_proxy(db, system=True)
        self._ingestion = IngestionEngine()
        self._telemetry = get_literature_telemetry()
        log.info("LiteratureIntelligenceEngine initialized")

    # ── Session management ─────────────────────────────────────────────────────

    async def create_session(
        self,
        user_id: str,
        title: str,
        review_type: ReviewType = ReviewType.NARRATIVE,
        description: str = "",
    ) -> ReviewSession:
        session = ReviewSession(
            user_id=user_id,
            title=title,
            review_type=review_type,
            description=description,
        )
        await self._db[_COL_SESSIONS].insert_one({
            "session_id": session.session_id,
            "user_id": user_id,
            "title": title,
            "review_type": review_type.value,
            "description": description,
            "status": SessionStatus.CREATED.value,
            "paper_ids": [],
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "credits_used": 0,
        })
        self._telemetry.record_session_created()
        return session

    async def get_session(self, session_id: str, user_id: str) -> ReviewSession | None:
        doc = await self._db[_COL_SESSIONS].find_one(
            {"session_id": session_id, "user_id": user_id}
        )
        if not doc:
            return None
        return self._doc_to_session(doc)

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[dict]:
        docs = await (
            self._db[_COL_SESSIONS]
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
            .to_list(limit)
        )
        return [self._doc_to_session_summary(d) for d in docs]

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        result = await self._db[_COL_SESSIONS].delete_one(
            {"session_id": session_id, "user_id": user_id}
        )
        if result.deleted_count:
            await self._db[_COL_PAPERS].delete_many({"session_id": session_id})
            await self._db["lit_paper_analyses"].delete_many({"session_id": session_id})
            return True
        return False

    # ── Paper ingestion ────────────────────────────────────────────────────────

    async def add_paper_by_source(
        self,
        session_id: str,
        user_id: str,
        source: PaperSource,
        source_id: str,
    ) -> dict:
        """Ingest a single paper from an API source."""
        result = await self._ingestion.ingest_one(source, source_id, session_id)
        if not result.success or not result.paper:
            return {"ok": False, "error": result.error}

        paper = result.paper
        await self._save_paper(paper)
        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {
                "$addToSet": {"paper_ids": paper.paper_id},
                "$set": {"updated_at": _now()},
            },
        )
        self._telemetry.record_papers_ingested(1, source.value)
        return {"ok": True, "paper": paper.to_dict()}

    async def add_paper_from_file(
        self,
        session_id: str,
        user_id: str,
        content: bytes,
        filename: str,
    ) -> dict:
        result = await self._ingestion.ingest_file(content, filename, session_id)
        if not result.success or not result.paper:
            return {"ok": False, "error": result.error}

        paper = result.paper
        await self._save_paper(paper)
        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {
                "$addToSet": {"paper_ids": paper.paper_id},
                "$set": {"updated_at": _now()},
            },
        )
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        self._telemetry.record_papers_ingested(1, ext)
        return {"ok": True, "paper": paper.to_dict()}

    async def add_papers_batch(
        self,
        session_id: str,
        user_id: str,
        items: list[dict],   # [{source, source_id}]
    ) -> dict:
        tuples = [(PaperSource(item["source"]), item["source_id"]) for item in items]
        results = await self._ingestion.ingest_batch(tuples, session_id)

        saved_ids = []
        errors = []
        for r in results:
            if r.success and r.paper:
                await self._save_paper(r.paper)
                saved_ids.append(r.paper.paper_id)
                self._telemetry.record_papers_ingested(1, r.source.value)
            else:
                errors.append(r.error)
                self._telemetry.record_papers_ingested(0, r.source.value, errors=1)

        if saved_ids:
            await self._db[_COL_SESSIONS].update_one(
                {"session_id": session_id, "user_id": user_id},
                {
                    "$addToSet": {"paper_ids": {"$each": saved_ids}},
                    "$set": {"updated_at": _now()},
                },
            )
        return {"ok": True, "added": len(saved_ids), "errors": errors}

    async def remove_paper(self, session_id: str, user_id: str, paper_id: str) -> bool:
        result = await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$pull": {"paper_ids": paper_id}, "$set": {"updated_at": _now()}},
        )
        return result.modified_count > 0

    async def search_papers(self, query: str, sources: list[str] | None = None, limit: int = 20) -> list[dict]:
        papers = await self._ingestion.search(query, sources, limit)
        return [p.to_dict() for p in papers]

    # ── Analysis pipeline ──────────────────────────────────────────────────────

    async def analyze_papers(self, session_id: str, user_id: str) -> dict:
        """Run 19-field AI analysis on all papers in session."""
        papers = await self._get_session_papers(session_id, user_id)
        if not papers:
            return {"ok": False, "error": "No papers in session"}

        await self._set_status(session_id, SessionStatus.ANALYZING)
        t0 = time.monotonic()

        analyses = await analyze_batch(papers, self._db, max_concurrent=5)

        elapsed_ms = (time.monotonic() - t0) * 1000
        self._telemetry.record_papers_analyzed(len(analyses), elapsed_ms)

        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"analyzed_count": len(analyses), "updated_at": _now(),
                      "status": SessionStatus.CREATED.value}},
        )
        return {
            "ok": True,
            "analyzed": len(analyses),
            "elapsed_ms": int(elapsed_ms),
        }

    async def compare_papers(self, session_id: str, user_id: str) -> dict:
        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        if len(papers) < 2:
            return {"ok": False, "error": "Need at least 2 papers to compare"}

        await self._set_status(session_id, SessionStatus.COMPARING)
        ca = await run_comparative_analysis(session_id, papers, analyses)

        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {
                "comparative_analysis": ca.to_dict(),
                "updated_at": _now(),
                "status": SessionStatus.CREATED.value,
            }},
        )
        return {"ok": True, "comparative_analysis": ca.to_dict()}

    async def cluster_papers_session(self, session_id: str, user_id: str) -> dict:
        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        clusters = cluster_papers(papers, analyses)
        clusters = label_clusters_with_ai_hint(clusters, papers)

        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {
                "clusters": [c.to_dict() for c in clusters],
                "updated_at": _now(),
            }},
        )
        return {"ok": True, "clusters": [c.to_dict() for c in clusters]}

    async def detect_evolution_session(self, session_id: str, user_id: str) -> dict:
        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        evolution = build_evolution(session_id, papers, analyses)

        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"evolution": evolution.to_dict(), "updated_at": _now()}},
        )
        return {"ok": True, "evolution": evolution.to_dict()}

    async def detect_gaps_session(
        self, session_id: str, user_id: str, topic: str = ""
    ) -> dict:
        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        gaps = await detect_gaps(papers, analyses, topic)

        self._telemetry.record_gaps_detected(len(gaps))
        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"gaps": [g.to_dict() for g in gaps], "updated_at": _now()}},
        )
        return {"ok": True, "gaps": [g.to_dict() for g in gaps]}

    async def generate_review_session(
        self,
        session_id: str,
        user_id: str,
        topic: str = "",
        additional_instructions: str = "",
    ) -> dict:
        session = await self.get_session(session_id, user_id)
        if not session:
            return {"ok": False, "error": "Session not found"}

        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        if not papers:
            return {"ok": False, "error": "No papers in session"}

        await self._set_status(session_id, SessionStatus.GENERATING)

        review = await generate_review(
            session=session,
            papers=papers,
            analyses=analyses,
            topic=topic,
            additional_instructions=additional_instructions,
        )

        self._telemetry.record_review_generated(session.review_type.value)
        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {
                "generated_review": review.to_dict(),
                "status": SessionStatus.COMPLETE.value,
                "updated_at": _now(),
            }},
        )
        return {"ok": True, "review": review.to_dict()}

    async def export_session_data(
        self,
        session_id: str,
        user_id: str,
        fmt: ExportFormat,
    ) -> tuple[str, str, str]:
        session = await self.get_session(session_id, user_id)
        if not session:
            return "", "error.txt", "text/plain"
        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        content, filename, content_type = export_session(session, papers, analyses, fmt)
        self._telemetry.record_export(fmt.value)
        return content, filename, content_type

    async def get_visualizations(self, session_id: str, user_id: str) -> dict:
        doc = await self._db[_COL_SESSIONS].find_one(
            {"session_id": session_id, "user_id": user_id}
        )
        if not doc:
            return {"error": "Session not found"}

        papers, analyses = await self._get_papers_and_analyses(session_id, user_id)
        clusters = self._doc_to_clusters(doc.get("clusters", []))
        evolution = self._doc_to_evolution(doc.get("evolution"), session_id)

        return build_all_visualizations(papers, analyses, clusters, evolution)

    async def get_citation_network(self, session_id: str, user_id: str) -> dict:
        papers, _ = await self._get_papers_and_analyses(session_id, user_id)
        return build_citation_network(papers)

    async def get_author_collaboration(self, session_id: str, user_id: str) -> dict:
        papers, _ = await self._get_papers_and_analyses(session_id, user_id)
        return compute_author_collaboration_graph(papers)

    # ── Admin ─────────────────────────────────────────────────────────────────

    def get_telemetry_stats(self) -> dict:
        return self._telemetry.get_stats()

    def get_supported_templates(self) -> dict:
        return all_templates()

    async def admin_list_sessions(self, limit: int = 50) -> list[dict]:
        docs = await self._db[_COL_SESSIONS].find({}).sort("created_at", -1).limit(limit).to_list(limit)
        return [self._doc_to_session_summary(d) for d in docs]

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _save_paper(self, paper: Paper) -> None:
        doc = paper.to_dict()
        doc["full_text"] = paper.full_text   # not in to_dict() for size reasons
        doc["abstract"] = paper.abstract
        await self._db[_COL_PAPERS].update_one(
            {"paper_id": paper.paper_id},
            {"$set": doc},
            upsert=True,
        )

    async def _get_session_papers(self, session_id: str, user_id: str) -> list[Paper]:
        doc = await self._db[_COL_SESSIONS].find_one(
            {"session_id": session_id, "user_id": user_id}
        )
        if not doc:
            return []
        paper_ids = doc.get("paper_ids", [])
        if not paper_ids:
            return []
        paper_docs = await self._db[_COL_PAPERS].find(
            {"paper_id": {"$in": paper_ids}}
        ).to_list(len(paper_ids))
        return [self._doc_to_paper(d) for d in paper_docs]

    async def _get_papers_and_analyses(
        self, session_id: str, user_id: str
    ) -> tuple[list[Paper], list[PaperAnalysis]]:
        papers = await self._get_session_papers(session_id, user_id)
        if not papers:
            return [], []
        paper_ids = [p.paper_id for p in papers]
        analysis_docs = await self._db["lit_paper_analyses"].find(
            {"paper_id": {"$in": paper_ids}}
        ).to_list(len(paper_ids))
        analyses = [self._doc_to_analysis(d) for d in analysis_docs]
        return papers, analyses

    async def _set_status(self, session_id: str, status: SessionStatus) -> None:
        await self._db[_COL_SESSIONS].update_one(
            {"session_id": session_id},
            {"$set": {"status": status.value, "updated_at": _now()}},
        )

    def _doc_to_paper(self, doc: dict) -> Paper:
        doc = dict(doc)
        doc.pop("_id", None)
        source = PaperSource(doc.pop("source", "manual"))
        return Paper(
            source=source,
            paper_id=doc.get("paper_id", ""),
            session_id=doc.get("session_id", ""),
            source_id=doc.get("source_id", ""),
            title=doc.get("title", ""),
            authors=doc.get("authors", []),
            year=doc.get("year", 0),
            abstract=doc.get("abstract", ""),
            full_text=doc.get("full_text", ""),
            keywords=doc.get("keywords", []),
            journal=doc.get("journal", ""),
            doi=doc.get("doi", ""),
            pmid=doc.get("pmid", ""),
            arxiv_id=doc.get("arxiv_id", ""),
            openalex_id=doc.get("openalex_id", ""),
            citation_count=doc.get("citation_count", 0),
            reference_count=doc.get("reference_count", 0),
            institution=doc.get("institution", ""),
            url=doc.get("url", ""),
            open_access=doc.get("open_access", False),
        )

    def _doc_to_analysis(self, doc: dict) -> PaperAnalysis:
        from services.literature.models import EvidenceQuality, EvidenceGrade
        doc = dict(doc)
        doc.pop("_id", None)
        eq_data = doc.pop("evidence_quality", {}) or {}
        eq = EvidenceQuality(
            methodological_quality=eq_data.get("methodological_quality", 0.0),
            scientific_rigor=eq_data.get("scientific_rigor", 0.0),
            citation_impact=eq_data.get("citation_impact", 0.0),
            novelty_score=eq_data.get("novelty_score", 0.0),
            reproducibility_score=eq_data.get("reproducibility_score", 0.0),
            publication_credibility=eq_data.get("publication_credibility", 0.0),
            overall_score=eq_data.get("overall_score", 0.0),
            grade=EvidenceGrade(eq_data.get("grade", "C")),
            study_design=eq_data.get("study_design", ""),
            quality_notes=eq_data.get("quality_notes", []),
        )
        known_fields = set(PaperAnalysis.__dataclass_fields__)
        return PaperAnalysis(**{k: v for k, v in doc.items() if k in known_fields},
                             evidence_quality=eq)

    def _doc_to_session(self, doc: dict) -> ReviewSession:
        doc = dict(doc)
        doc.pop("_id", None)
        return ReviewSession(
            session_id=doc.get("session_id", ""),
            user_id=doc.get("user_id", ""),
            title=doc.get("title", ""),
            description=doc.get("description", ""),
            review_type=ReviewType(doc.get("review_type", "narrative")),
            paper_ids=doc.get("paper_ids", []),
            status=SessionStatus(doc.get("status", "created")),
            analyzed_count=doc.get("analyzed_count", 0),
            created_at=doc.get("created_at", _now()),
            updated_at=doc.get("updated_at", _now()),
            credits_used=doc.get("credits_used", 0),
        )

    def _doc_to_session_summary(self, doc: dict) -> dict:
        return {
            "session_id": doc.get("session_id", ""),
            "title": doc.get("title", ""),
            "review_type": doc.get("review_type", "narrative"),
            "status": doc.get("status", "created"),
            "paper_count": len(doc.get("paper_ids", [])),
            "analyzed_count": doc.get("analyzed_count", 0),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
        }

    def _doc_to_clusters(self, raw: list[dict]) -> list:
        from services.literature.models import ThematicCluster
        clusters = []
        for d in raw:
            c = ThematicCluster(
                cluster_id=d.get("cluster_id", ""),
                label=d.get("label", ""),
                description=d.get("description", ""),
                paper_ids=d.get("paper_ids", []),
                top_keywords=d.get("top_keywords", []),
                dominant_methodology=d.get("dominant_methodology", ""),
                year_range=tuple(d.get("year_range", [0, 0])),
                coherence_score=d.get("coherence_score", 0.0),
            )
            clusters.append(c)
        return clusters

    def _doc_to_evolution(self, raw: dict | None, session_id: str):
        if not raw:
            return None
        from services.literature.models import ResearchEvolution, Milestone
        milestones = [
            Milestone(year=m["year"], description=m["description"],
                      paper_ids=m.get("paper_ids", []), significance=m.get("significance", "normal"))
            for m in raw.get("milestones", [])
        ]
        return ResearchEvolution(
            session_id=session_id,
            milestones=milestones,
            emerging_topics=raw.get("emerging_topics", []),
            declining_topics=raw.get("declining_topics", []),
            future_directions=raw.get("future_directions", []),
            earliest_year=raw.get("year_range", [0, 0])[0],
            latest_year=raw.get("year_range", [0, 0])[1],
            evolution_summary=raw.get("evolution_summary", ""),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: LiteratureIntelligenceEngine | None = None
_engine_lock = threading.Lock()


async def get_literature_engine() -> LiteratureIntelligenceEngine:
    global _engine
    if _engine is not None:
        return _engine
    from db import get_db
    from repo.shim import make_db_proxy
    db = make_db_proxy(get_db(), system=True)
    with _engine_lock:
        if _engine is None:
            _engine = LiteratureIntelligenceEngine(db)
    return _engine


def reset_literature_engine() -> None:
    global _engine
    with _engine_lock:
        _engine = None
