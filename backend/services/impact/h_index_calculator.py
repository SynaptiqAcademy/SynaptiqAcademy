"""H-index and publication metrics calculator.

Pure functions + async DB queries — no FastAPI dependencies.

Data source priority:
  1. publications collection (OpenAlex synced) — has per-pub citation counts
  2. users.openalex_metrics — aggregated h_index / citations already computed
  3. manuscripts collection — status/type only, no citation data

When real citation data is absent the function returns 0/empty values rather
than raising exceptions, so the dashboard renders correctly on a fresh account.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId

log = logging.getLogger("synaptiq.impact.h_index")


# ─────────────────────────── pure math ───────────────────────────────────────

def compute_h_index(citation_counts: list[int]) -> int:
    """Standard H-index: largest h such that h papers each have >= h citations.

    Args:
        citation_counts: list of citation counts per publication (can be 0).

    Returns:
        h-index as an integer (0 when the list is empty or all zeros).
    """
    if not citation_counts:
        return 0
    sorted_desc = sorted(citation_counts, reverse=True)
    h = 0
    for i, c in enumerate(sorted_desc, start=1):
        if c >= i:
            h = i
        else:
            break
    return h


def compute_i10_index(citation_counts: list[int]) -> int:
    """Count publications with >= 10 citations."""
    return sum(1 for c in citation_counts if c >= 10)


# ─────────────────────────── async DB query ───────────────────────────────────

async def compute_publication_metrics(user_id: str, db) -> dict:
    """Compute H-index, i10-index, and citation stats from available data.

    Data sources (in priority order):
      1. publications collection (openalex synced) — field: citations
      2. manuscripts collection — status/type only, no citations
      3. users.openalex_metrics — aggregated h_index, citations

    Returns:
        {
          "h_index": int,
          "i10_index": int,
          "total_publications": int,
          "published_count": int,
          "submitted_count": int,
          "draft_count": int,
          "citation_counts": list[int],   # per-publication
          "total_citations": int,
          "avg_citations_per_pub": float,
          "citations_last_12_months": int,
          "data_source": "openalex" | "manuscripts" | "none",
        }
    """
    uid = user_id
    now = datetime.now(timezone.utc)
    cutoff_12m = now - timedelta(days=365)

    # ── Source 1: publications collection ─────────────────────────────────────
    pub_docs = await db.publications.find(
        {"owner_id": uid},
        {"citations": 1, "year": 1, "status": 1},
    ).to_list(2000)

    if pub_docs:
        citation_counts: list[int] = [int(p.get("citations") or 0) for p in pub_docs]
        total_citations = sum(citation_counts)
        total_publications = len(pub_docs)

        # For publications collection there's no draft/submitted distinction —
        # treat all as "published" since OpenAlex only indexes published works.
        published_count = total_publications
        submitted_count = 0
        draft_count = 0

        # citations gained in the last 12 months from snapshot deltas
        cit_12m_agg = await db.publication_citations.aggregate([
            {"$match": {"user_id": uid, "created_at": {"$gte": cutoff_12m}}},
            {"$group": {"_id": None, "total": {"$sum": "$delta"}}},
        ]).to_list(1)
        citations_last_12_months = int(
            (cit_12m_agg[0].get("total") or 0) if cit_12m_agg else 0
        )

        h = compute_h_index(citation_counts)
        i10 = compute_i10_index(citation_counts)

        return {
            "h_index": h,
            "i10_index": i10,
            "total_publications": total_publications,
            "published_count": published_count,
            "submitted_count": submitted_count,
            "draft_count": draft_count,
            "citation_counts": citation_counts,
            "total_citations": total_citations,
            "avg_citations_per_pub": round(total_citations / max(1, total_publications), 2),
            "citations_last_12_months": citations_last_12_months,
            "data_source": "openalex",
        }

    # ── Source 2: manuscripts collection ─────────────────────────────────────
    # No citation data here — only counts by status.
    manuscript_agg = await db.manuscripts.aggregate([
        {
            "$match": {
                "$or": [
                    {"lead_author_id": uid},
                    {"authors": uid},
                ]
            }
        },
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
            }
        },
    ]).to_list(20)

    if manuscript_agg:
        status_map: dict[str, int] = {}
        for row in manuscript_agg:
            key = (row.get("_id") or "unknown").lower()
            status_map[key] = int(row.get("count") or 0)

        published_count = status_map.get("published", 0)
        submitted_count = status_map.get("submitted", 0)
        draft_count = status_map.get("draft", 0)
        total_publications = published_count + submitted_count + draft_count

        # Try to pull aggregated metrics from openalex_metrics on the user doc
        u_doc = await db.users.find_one(
            {"_id": ObjectId(uid)},
            {"openalex_metrics": 1, "h_index": 1},
        )
        oam = (u_doc or {}).get("openalex_metrics") or {}
        h = int(oam.get("h_index") or (u_doc or {}).get("h_index") or 0)
        total_citations = int(oam.get("citations") or 0)
        i10 = compute_i10_index([])  # no per-pub data

        return {
            "h_index": h,
            "i10_index": i10,
            "total_publications": total_publications,
            "published_count": published_count,
            "submitted_count": submitted_count,
            "draft_count": draft_count,
            "citation_counts": [],
            "total_citations": total_citations,
            "avg_citations_per_pub": 0.0,
            "citations_last_12_months": 0,
            "data_source": "manuscripts",
        }

    # ── Source 3: openalex_metrics on user doc ────────────────────────────────
    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1},
    )
    oam = (u_doc or {}).get("openalex_metrics") or {}
    h = int(oam.get("h_index") or (u_doc or {}).get("h_index") or 0)
    total_citations = int(oam.get("citations") or 0)
    works_count = int(oam.get("works_count") or (u_doc or {}).get("publications_count") or 0)

    if h > 0 or works_count > 0:
        return {
            "h_index": h,
            "i10_index": 0,
            "total_publications": works_count,
            "published_count": works_count,
            "submitted_count": 0,
            "draft_count": 0,
            "citation_counts": [],
            "total_citations": total_citations,
            "avg_citations_per_pub": round(total_citations / max(1, works_count), 2),
            "citations_last_12_months": 0,
            "data_source": "openalex",
        }

    # ── No data at all ────────────────────────────────────────────────────────
    return {
        "h_index": 0,
        "i10_index": 0,
        "total_publications": 0,
        "published_count": 0,
        "submitted_count": 0,
        "draft_count": 0,
        "citation_counts": [],
        "total_citations": 0,
        "avg_citations_per_pub": 0.0,
        "citations_last_12_months": 0,
        "data_source": "none",
    }
