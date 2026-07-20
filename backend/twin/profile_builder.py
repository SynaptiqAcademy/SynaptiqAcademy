"""
Research profile builder.

Derives: research domains, emerging interests, methodological expertise,
publication themes, career stage, interdisciplinary activity.

All derivations trace to verified platform data. Nothing is invented.
"""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from .models import (
    CareerStage, EvidenceLevel, TwinEvidence,
    ResearchDomainEntry, confidence_from_evidence,
)

logger = logging.getLogger("twin.profile")

_SOURCE = "Synaptiq platform"

# ── Career stage heuristics ────────────────────────────────────────────────────

_CAREER_KEYWORDS: list[tuple[list[str], CareerStage]] = [
    (["phd student", "doctoral", "graduate student", "phd candidate"], CareerStage.PHD),
    (["postdoc", "post-doctoral", "post doctoral"],                     CareerStage.POSTDOC),
    (["assistant professor", "assistant prof", "junior lecturer"],       CareerStage.ASSISTANT_PROF),
    (["associate professor", "associate prof", "reader"],                CareerStage.ASSOCIATE_PROF),
    (["professor", "full professor", "senior lecturer", "chair of"],     CareerStage.FULL_PROF),
    (["emeritus", "retired professor"],                                  CareerStage.EMERITUS),
    (["researcher", "scientist", "r&d"],                                 CareerStage.INDUSTRY),
]

def _infer_career_stage(user: dict) -> tuple[CareerStage, list[TwinEvidence]]:
    text_field = " ".join([
        (user.get("academic_position") or ""),
        (user.get("bio") or ""),
        (user.get("title") or ""),
    ]).lower()

    for keywords, stage in _CAREER_KEYWORDS:
        if any(kw in text_field for kw in keywords):
            return stage, [TwinEvidence(
                source="User profile — academic_position/bio field",
                detail=f"Matched keyword pattern for {stage.value}",
                count=1,
            )]
    return CareerStage.UNKNOWN, []


# ── Domain builder ─────────────────────────────────────────────────────────────

async def build_research_profile(db, user_id: str, user: dict, excluded_ms_ids: list[str], excluded_proj_ids: list[str]) -> dict:
    """
    Derive research profile from:
      1. User-declared research_interests
      2. Manuscript keywords (excluding excluded_ms_ids)
      3. Project tags (excluding excluded_proj_ids)
      4. LKG topic edges

    Returns a dict ready to store in digital_twins.profile.
    """
    domain_evidence: dict[str, list[TwinEvidence]] = defaultdict(list)
    domain_first_seen: dict[str, datetime] = {}
    domain_last_active: dict[str, datetime] = {}
    now = datetime.now(timezone.utc)

    # ── 1. User-declared interests ─────────────────────────────────────────────
    for interest in (user.get("research_interests") or []):
        interest = str(interest).strip()
        if not interest:
            continue
        key = interest.lower()
        domain_evidence[key].append(TwinEvidence(
            source="User profile — research_interests field",
            detail=f"User-declared interest: {interest}",
            count=1,
        ))
        domain_first_seen.setdefault(key, now)
        domain_last_active[key] = now

    # ── 2. Manuscript keywords ─────────────────────────────────────────────────
    ms_cursor = db.manuscripts.find(
        {"user_id": user_id, "_id": {"$nin": [eid for eid in excluded_ms_ids]}},
        {"keywords": 1, "created_at": 1, "updated_at": 1}
    )
    async for ms in ms_cursor:
        ms_date = ms.get("updated_at") or ms.get("created_at") or now
        for kw in (ms.get("keywords") or []):
            kw = str(kw).strip()
            if not kw:
                continue
            key = kw.lower()
            domain_evidence[key].append(TwinEvidence(
                source="Synaptiq manuscripts DB",
                detail=f"Keyword from manuscript",
                count=1,
                observed_at=ms_date,
            ))
            if key not in domain_first_seen or ms_date < domain_first_seen[key]:
                domain_first_seen[key] = ms_date
            if key not in domain_last_active or ms_date > domain_last_active[key]:
                domain_last_active[key] = ms_date

    # ── 3. Project tags ────────────────────────────────────────────────────────
    proj_cursor = db.projects.find(
        {"user_id": user_id, "_id": {"$nin": [eid for eid in excluded_proj_ids]}},
        {"tags": 1, "created_at": 1}
    )
    async for proj in proj_cursor:
        proj_date = proj.get("created_at") or now
        for tag in (proj.get("tags") or []):
            tag = str(tag).strip()
            if not tag:
                continue
            key = tag.lower()
            domain_evidence[key].append(TwinEvidence(
                source="Synaptiq projects DB",
                detail="Tag from research project",
                count=1,
                observed_at=proj_date,
            ))
            domain_first_seen.setdefault(key, proj_date)
            if key not in domain_last_active or proj_date > domain_last_active[key]:
                domain_last_active[key] = proj_date

    # ── 4. LKG topic edges ─────────────────────────────────────────────────────
    try:
        node_id = f"researcher:platform:{user_id}"
        topic_edges = await db.lkg_edges.find(
            {"from_id": node_id, "type": "BELONGS_TO_TOPIC"}, {"to_id": 1}
        ).to_list(20)
        topic_ids = [e["to_id"] for e in topic_edges]
        if topic_ids:
            topic_nodes = await db.lkg_nodes.find(
                {"node_id": {"$in": topic_ids}}, {"label": 1}
            ).to_list(20)
            for tn in topic_nodes:
                key = (tn.get("label") or "").lower()
                if key:
                    domain_evidence[key].append(TwinEvidence(
                        source="Synaptiq Living Knowledge Graph",
                        detail="Connected via LKG topic edge",
                        count=1,
                    ))
                    domain_first_seen.setdefault(key, now)
                    domain_last_active[key] = now
    except Exception:
        pass

    # ── Build domain entries ───────────────────────────────────────────────────
    all_domains = []
    for domain, ev_list in domain_evidence.items():
        conf, _  = confidence_from_evidence(ev_list)
        all_domains.append({
            "domain":       domain,
            "evidence":     [e.to_dict() for e in ev_list],
            "confidence":   conf.value,
            "evidence_count": sum(e.count for e in ev_list),
            "first_seen":   domain_first_seen.get(domain, now).isoformat(),
            "last_active":  domain_last_active.get(domain, now).isoformat(),
        })

    all_domains.sort(key=lambda x: x["evidence_count"], reverse=True)

    # Split into established domains (3+ evidence) vs emerging interests (1-2 evidence)
    established = [d for d in all_domains if d["evidence_count"] >= 3][:15]
    emerging    = [d for d in all_domains if d["evidence_count"] < 3][:10]

    # ── Career stage ───────────────────────────────────────────────────────────
    career_stage, career_evidence = _infer_career_stage(user)

    # ── Methodological expertise (from manuscript abstracts/keywords) ───────────
    method_keywords = [
        "systematic review", "meta-analysis", "randomised controlled trial", "rct",
        "regression", "machine learning", "deep learning", "natural language processing",
        "qualitative", "mixed methods", "survey", "cohort study", "case study",
        "ethnography", "grounded theory", "structural equation", "bayesian",
        "neural network", "clustering", "classification", "time series",
        "content analysis", "bibliometric", "scoping review",
    ]
    method_counts: Counter = Counter()
    ms_texts_cursor = db.manuscripts.find(
        {"user_id": user_id},
        {"abstract": 1, "keywords": 1}
    )
    async for ms in ms_texts_cursor:
        text = " ".join([
            str(ms.get("abstract") or ""),
            " ".join(ms.get("keywords") or []),
        ]).lower()
        for meth in method_keywords:
            if meth in text:
                method_counts[meth] += 1

    methodologies = [
        {
            "method":    meth,
            "count":     cnt,
            "confidence": "high" if cnt >= 3 else "medium" if cnt >= 2 else "low",
            "evidence":  [{"source": "Synaptiq manuscripts DB", "detail": f"Observed in {cnt} manuscript(s)"}],
        }
        for meth, cnt in method_counts.most_common(10) if cnt > 0
    ]

    # ── Interdisciplinary activity ─────────────────────────────────────────────
    distinct_domains = len(set(d["domain"].split()[0] for d in established)) if established else 0
    interdisciplinary = {
        "distinct_domain_clusters": distinct_domains,
        "assessment":  (
            "Highly interdisciplinary research activity" if distinct_domains >= 4 else
            "Moderately interdisciplinary" if distinct_domains >= 2 else
            "Focused research area" if distinct_domains == 1 else
            "Insufficient data to assess"
        ),
        "methodology": "Counted distinct leading terms across research domains with 3+ evidence points",
        "source":      "Synaptiq platform data — manuscripts, projects, interests",
    } if established else None

    return {
        "research_domains":          established,
        "emerging_interests":        emerging,
        "methodological_expertise":  methodologies,
        "publication_themes":        established[:5],  # Top domains as themes
        "career_stage":              career_stage.value,
        "career_stage_evidence":     [e.to_dict() for e in career_evidence],
        "interdisciplinary_activity": interdisciplinary,
    }
