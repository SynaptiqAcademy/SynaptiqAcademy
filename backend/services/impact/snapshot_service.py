"""Snapshot and caching service for the Research Impact Dashboard.

Responsibilities:
  - compute_and_store_research_impact  — full SIS + h-index + benchmarks
  - get_research_impact                — serve from cache or recompute
  - save_impact_snapshot               — write a history record
  - get_history                        — fetch time-series records
  - get_platform_impact_summary        — admin aggregate

Collections used:
  - research_impact          — per-user upserted document (cached)
  - research_impact_history  — time-series snapshots
  - research_impact_snapshots — named user-created comparison snapshots

No FastAPI dependencies — pure async service functions.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId

from services.impact.synaptiq_score import compute_synaptiq_impact_score
from services.impact.h_index_calculator import compute_publication_metrics
from services.impact.benchmarking import compute_benchmarks

log = logging.getLogger("synaptiq.impact.snapshot")

# Cache TTL: 12 hours
_CACHE_TTL_HOURS = 12


# ─────────────────────────── helpers ─────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _is_stale(doc: dict) -> bool:
    """Return True if the document's computed_at is older than the cache TTL."""
    computed_at = doc.get("computed_at")
    if not computed_at:
        return True
    if isinstance(computed_at, str):
        try:
            computed_at = datetime.fromisoformat(computed_at)
        except ValueError:
            return True
    if computed_at.tzinfo is None:
        computed_at = computed_at.replace(tzinfo=timezone.utc)
    return _now() - computed_at > timedelta(hours=_CACHE_TTL_HOURS)


# ─────────────────────────── core computation ────────────────────────────────

async def compute_and_store_research_impact(user_id: str, db) -> dict:
    """Full computation: SIS + h-index + benchmarks + raw counts.

    Runs all three sub-computations concurrently, then upserts the result
    into the research_impact collection and appends a snapshot to
    research_impact_history.

    Args:
        user_id: str — MongoDB ObjectId string of the user.
        db:      Motor database instance.

    Returns:
        The full research_impact document (without _id).
    """
    import asyncio

    uid = user_id

    sis_result, pub_metrics, benchmarks = await asyncio.gather(
        compute_synaptiq_impact_score(uid, db),
        compute_publication_metrics(uid, db),
        compute_benchmarks(uid, db),
    )

    now_iso = _now_iso()

    doc: dict = {
        "user_id":       uid,
        "sis_total":     sis_result["total"],
        "sis_label":     sis_result["label"],
        "sis_components": sis_result["components"],
        "h_index":       pub_metrics["h_index"],
        "i10_index":     pub_metrics["i10_index"],
        "total_publications":  pub_metrics["total_publications"],
        "published_count":     pub_metrics["published_count"],
        "submitted_count":     pub_metrics["submitted_count"],
        "draft_count":         pub_metrics["draft_count"],
        "total_citations":     pub_metrics["total_citations"],
        "avg_citations_per_pub": pub_metrics["avg_citations_per_pub"],
        "citations_last_12_months": pub_metrics["citations_last_12_months"],
        "citation_data_source": pub_metrics["data_source"],
        "active_collaborations": (
            sis_result["components"]["collaboration"]["details"].get("active_collaborations", 0)
        ),
        "benchmarks":    benchmarks,
        "computed_at":   now_iso,
        "updated_at":    now_iso,
    }

    # Upsert into research_impact (one doc per user)
    await db.research_impact.update_one(
        {"user_id": uid},
        {"$set": doc},
        upsert=True,
    )

    # Append to research_impact_history for trend tracking
    history_record = {
        "user_id":             uid,
        "sis_total":           doc["sis_total"],
        "sis_label":           doc["sis_label"],
        "h_index":             doc["h_index"],
        "total_publications":  doc["total_publications"],
        "total_citations":     doc["total_citations"],
        "active_collaborations": doc["active_collaborations"],
        "global_percentile":   (benchmarks.get("global") or {}).get("user_percentile", 0),
        "global_rank":         (benchmarks.get("global") or {}).get("user_rank", 0),
        "created_at":          now_iso,
    }
    await db.research_impact_history.insert_one(history_record)

    return doc


# ─────────────────────────── cache-aware getter ───────────────────────────────

async def get_research_impact(
    user_id: str,
    db,
    force_refresh: bool = False,
) -> dict:
    """Return the cached research_impact document if < 12 hours old,
    else recompute and store.

    Args:
        user_id:       str — MongoDB ObjectId string of the user.
        db:            Motor database instance.
        force_refresh: bool — bypass the cache and recompute unconditionally.

    Returns:
        The full research_impact document (without MongoDB _id).
    """
    uid = user_id

    if not force_refresh:
        cached = await db.research_impact.find_one(
            {"user_id": uid},
            {"_id": 0},
        )
        if cached and not _is_stale(cached):
            return cached

    return await compute_and_store_research_impact(uid, db)


# ─────────────────────────── named snapshot ───────────────────────────────────

async def save_impact_snapshot(
    user_id: str,
    db,
    label: Optional[str] = None,
) -> dict:
    """Compute current impact metrics and save to research_impact_history.

    Also writes a named record to research_impact_snapshots so the user can
    compare two points in time side-by-side.

    Args:
        user_id: str — MongoDB ObjectId string of the user.
        db:      Motor database instance.
        label:   Optional human-readable name (e.g., "Before EMNLP 2026").

    Returns:
        The saved snapshot document (without MongoDB _id).
    """
    uid = user_id

    # Force a fresh computation so the snapshot is always accurate
    impact_doc = await compute_and_store_research_impact(uid, db)

    snapshot: dict = {
        "user_id":             uid,
        "label":               label or f"Snapshot {_now().strftime('%Y-%m-%d %H:%M')} UTC",
        "sis_total":           impact_doc["sis_total"],
        "sis_label":           impact_doc["sis_label"],
        "h_index":             impact_doc["h_index"],
        "i10_index":           impact_doc["i10_index"],
        "total_publications":  impact_doc["total_publications"],
        "total_citations":     impact_doc["total_citations"],
        "active_collaborations": impact_doc["active_collaborations"],
        "global_percentile":   (impact_doc.get("benchmarks") or {}).get(
            "global", {}
        ).get("user_percentile", 0),
        "sis_components":      impact_doc.get("sis_components"),
        "created_at":          _now_iso(),
    }

    await db.research_impact_snapshots.insert_one(snapshot)

    # Return without _id (motor adds it in-place after insert)
    return {k: v for k, v in snapshot.items() if k != "_id"}


# ─────────────────────────── history reader ───────────────────────────────────

async def get_history(user_id: str, db, limit: int = 24) -> list[dict]:
    """Return the last N historical snapshots for the user, sorted ascending.

    Args:
        user_id: str — MongoDB ObjectId string of the user.
        db:      Motor database instance.
        limit:   int — maximum number of records to return (default 24).

    Returns:
        List of history documents (without MongoDB _id), oldest first.
    """
    uid = user_id
    docs = await db.research_impact_history.find(
        {"user_id": uid},
        {"_id": 0},
    ).sort("created_at", 1).limit(limit).to_list(limit)
    return docs


# ─────────────────────────── admin aggregate ──────────────────────────────────

async def get_platform_impact_summary(db) -> dict:
    """Admin aggregate: platform-wide impact stats.

    Uses the research_impact collection (one doc per user) to compute:
      - total researchers with impact data
      - average and median SIS
      - top researchers (by SIS)
      - top institutions and countries (by average SIS)

    Returns:
        {
          "total_researchers":     int,
          "avg_sis":               float,
          "median_sis":            float,
          "top_researchers":       list[dict],
          "top_institutions":      list[dict],
          "top_countries":         list[dict],
          "computed_at":           str,
        }
    """
    # Overall stats
    stats_agg = await db.research_impact.aggregate([
        {
            "$group": {
                "_id":   None,
                "count": {"$sum": 1},
                "avg":   {"$avg": "$sis_total"},
                "all_scores": {"$push": "$sis_total"},
            }
        }
    ]).to_list(1)

    if not stats_agg:
        return {
            "total_researchers": 0,
            "avg_sis":           0.0,
            "median_sis":        0.0,
            "top_researchers":   [],
            "top_institutions":  [],
            "top_countries":     [],
            "computed_at":       _now_iso(),
        }

    row         = stats_agg[0]
    total       = int(row.get("count") or 0)
    avg_sis     = round(float(row.get("avg") or 0), 2)
    all_scores: list[float] = [float(s) for s in (row.get("all_scores") or [])]
    all_scores.sort()
    if all_scores:
        mid        = len(all_scores) // 2
        median_sis = (all_scores[mid] if len(all_scores) % 2 != 0
                      else (all_scores[mid - 1] + all_scores[mid]) / 2)
        median_sis = round(median_sis, 2)
    else:
        median_sis = 0.0

    # Top 10 researchers
    top_docs = await db.research_impact.find(
        {},
        {"user_id": 1, "sis_total": 1, "sis_label": 1, "h_index": 1,
         "total_publications": 1, "_id": 0},
    ).sort("sis_total", -1).limit(10).to_list(10)

    # Enrich with user display name
    top_user_ids = [d["user_id"] for d in top_docs]
    valid_ids    = [ObjectId(i) for i in top_user_ids if len(i) == 24]
    user_map: dict[str, dict] = {}
    if valid_ids:
        user_docs = await db.users.find(
            {"_id": {"$in": valid_ids}},
            {"full_name": 1, "institution": 1, "country": 1, "avatar_url": 1},
        ).to_list(10)
        for ud in user_docs:
            user_map[str(ud["_id"])] = ud

    top_researchers = []
    for rank, d in enumerate(top_docs, start=1):
        uid = d["user_id"]
        u   = user_map.get(uid) or {}
        top_researchers.append({
            "rank":             rank,
            "user_id":          uid,
            "full_name":        u.get("full_name") or "Unknown",
            "institution":      u.get("institution"),
            "country":          u.get("country"),
            "avatar_url":       u.get("avatar_url"),
            "sis_total":        d.get("sis_total", 0),
            "sis_label":        d.get("sis_label"),
            "h_index":          d.get("h_index", 0),
            "total_publications": d.get("total_publications", 0),
        })

    # Top institutions by average SIS
    inst_agg = await db.research_impact.aggregate([
        {
            "$lookup": {
                "from":         "users",
                "localField":   "user_id",
                "foreignField": "_id",  # won't work directly — need string match
                "as":           "_user",
            }
        },
        # Since user_id is stored as string and users._id is ObjectId,
        # we use a pipeline-style lookup with $toString.
        # Motor supports pipeline lookups (MongoDB 3.6+).
    ]).to_list(0)  # placeholder — use separate aggregation below

    # Simpler approach: join via Python after fetching both collections
    all_impact = await db.research_impact.find(
        {},
        {"user_id": 1, "sis_total": 1, "_id": 0},
    ).to_list(5000)

    all_user_ids  = [d["user_id"] for d in all_impact]
    valid_all_ids = [ObjectId(i) for i in all_user_ids if len(i) == 24]
    inst_country_map: dict[str, dict] = {}
    if valid_all_ids:
        uc_docs = await db.users.find(
            {"_id": {"$in": valid_all_ids}},
            {"institution": 1, "country": 1},
        ).to_list(5000)
        for ud in uc_docs:
            inst_country_map[str(ud["_id"])] = ud

    # Compute institution averages
    from collections import defaultdict
    inst_scores:    dict[str, list[float]] = defaultdict(list)
    country_scores: dict[str, list[float]] = defaultdict(list)

    for d in all_impact:
        uid  = d["user_id"]
        sis  = float(d.get("sis_total") or 0)
        meta = inst_country_map.get(uid) or {}
        inst = (meta.get("institution") or "").strip()
        ctry = (meta.get("country")     or "").strip()
        if inst:
            inst_scores[inst].append(sis)
        if ctry:
            country_scores[ctry].append(sis)

    def _top_n(score_map: dict[str, list[float]], n: int) -> list[dict]:
        result = []
        for name, scores in score_map.items():
            result.append({
                "name":        name,
                "avg_sis":     round(sum(scores) / len(scores), 2),
                "researchers": len(scores),
            })
        result.sort(key=lambda x: x["avg_sis"], reverse=True)
        return result[:n]

    return {
        "total_researchers": total,
        "avg_sis":           avg_sis,
        "median_sis":        median_sis,
        "top_researchers":   top_researchers,
        "top_institutions":  _top_n(inst_scores, 10),
        "top_countries":     _top_n(country_scores, 10),
        "computed_at":       _now_iso(),
    }
