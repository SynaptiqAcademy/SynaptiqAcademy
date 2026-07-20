from __future__ import annotations

import logging
from collections import Counter

from bson import ObjectId
from fastapi import APIRouter, Depends

from auth_utils import get_current_user, serialize_public_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.discover")

router = APIRouter(prefix="/api/discover", tags=["discover"])


async def _user_publication_topics(db, user_id: str, limit: int = 10) -> list[str]:
    """Return the top OpenAlex concept/topic display names from a user's publications."""
    docs = await db.publications.find(
        {"owner_id": user_id, "openalex_enriched_at": {"$exists": True}},
        {"concepts": 1, "topics": 1},
    ).limit(40).to_list(40)

    counter: Counter = Counter()
    for pub in docs:
        for c in (pub.get("concepts") or []):
            name = c.get("display_name") or c.get("name")
            if name:
                counter[name.lower()] += 1
        for t in (pub.get("topics") or []):
            name = t.get("display_name") or t.get("name")
            if name:
                counter[name.lower()] += 1

    return [name for name, _ in counter.most_common(limit)]


@router.get("/feed")
async def feed(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    user_areas = user.get("research_areas") or []

    # ── Pull user's OpenAlex topics from publications ─────────────────────────
    pub_topics = await _user_publication_topics(db, uid)
    # Combined interest signal: explicit areas + inferred topics (deduplicated)
    area_set = {a.lower() for a in user_areas}
    topic_set = set(pub_topics)

    # ── Open collaborations — ranked by area/topic overlap ────────────────────
    collab_query = {
        "status": "open",
        "creator_id": {"$ne": uid},
        "is_demo": {"$ne": True},
    }
    collabs = await db.collaborations.find(collab_query).sort("created_at", -1).limit(20).to_list(20)

    def collab_score(c):
        score = 0
        ra = (c.get("research_area") or "").lower()
        if ra in area_set or ra in topic_set:
            score += 3
        for s in c.get("skills_needed", []):
            if s.lower() in area_set or s.lower() in topic_set:
                score += 1
        # Recency bonus (newer gets +1 if area not matched)
        if score == 0 and c.get("created_at"):
            score += 0.1
        return score

    collabs.sort(key=collab_score, reverse=True)
    top_collabs = collabs[:10]

    # Batch-fetch creator profiles
    creator_ids = list({ObjectId(c["creator_id"]) for c in top_collabs if c.get("creator_id")})
    creators_by_id: dict = {}
    if creator_ids:
        creator_docs = await db.users.find(
            {"_id": {"$in": creator_ids}},
            {"full_name": 1, "institution": 1, "avatar_url": 1},
        ).to_list(len(creator_ids))
        creators_by_id = {str(d["_id"]): d for d in creator_docs}

    collabs_out = []
    for c in top_collabs:
        creator = creators_by_id.get(c["creator_id"])
        item = {**c, "id": str(c["_id"])}
        item.pop("_id")
        if creator:
            item["creator"] = {
                "id": str(creator["_id"]),
                "full_name": creator.get("full_name", ""),
                "institution": creator.get("institution", ""),
                "avatar_url": creator.get("avatar_url", ""),
            }
        collabs_out.append(item)

    # ── Recommended researchers — area + topic overlap, exclude self + connected ──
    connected_ids: list[str] = user.get("connections") or []
    excluded_ids = {ObjectId(uid)} | {ObjectId(cid) for cid in connected_ids if cid}

    user_kw_set = {k.lower() for k in (user.get("research_keywords") or [])}
    user_methods_set = {m.lower() for m in (user.get("methods") or [])}

    base_filter: dict = {
        "_id": {"$nin": list(excluded_ids)},
        "is_demo": {"$ne": True},
        "profile_visibility": {"$ne": "private"},
    }
    researchers_q = {**base_filter}

    # Primary pass: users who share a research area OR have publications in the same topics
    if area_set:
        researchers_q["research_areas"] = {"$in": list(user_areas)}
    researchers = await db.users.find(researchers_q).limit(20).to_list(20)

    # Topic-based expansion: find users with publications sharing the user's concepts
    if pub_topics:
        try:
            topic_pub_owners = await db.publications.distinct(
                "owner_id",
                {
                    "owner_id": {"$nin": [str(oid) for oid in excluded_ids]},
                    "openalex_enriched_at": {"$exists": True},
                    "$or": [
                        {"concepts.display_name": {"$in": pub_topics}},
                        {"topics.display_name": {"$in": pub_topics}},
                    ],
                },
            )
            seen = {str(r["_id"]) for r in researchers}
            if topic_pub_owners:
                extra = await db.users.find(
                    {
                        "_id": {
                            "$in": [
                                ObjectId(oid)
                                for oid in topic_pub_owners
                                if oid not in seen
                            ],
                            "$nin": list(excluded_ids),
                        },
                        "is_demo": {"$ne": True},
                        "profile_visibility": {"$ne": "private"},
                    }
                ).limit(10).to_list(10)
                researchers.extend(extra)
        except Exception as exc:
            log.warning("Topic expansion failed: %s", exc)

    # Rank by full signal score
    def researcher_score(r):
        r_areas   = {a.lower() for a in (r.get("research_areas") or [])}
        r_kw      = {k.lower() for k in (r.get("research_keywords") or [])}
        r_methods = {m.lower() for m in (r.get("methods") or [])}
        area_overlap   = len(area_set & r_areas)
        topic_overlap  = len(topic_set & r_areas)
        kw_overlap     = len(user_kw_set & r_kw)
        method_overlap = len(user_methods_set & r_methods)
        h = int((r.get("openalex_metrics") or {}).get("h_index") or r.get("h_index") or 0)
        pubs = int(r.get("publications_count") or 0)
        inst_bonus = 2 if (user.get("institution") and r.get("institution") == user.get("institution")) else 0
        return (area_overlap * 5 + topic_overlap * 3 + kw_overlap * 3 + method_overlap * 4
                + (2 if h > 5 else 1 if h > 0 else 0)
                + (1 if pubs > 0 else 0) + inst_bonus)

    researchers.sort(key=researcher_score, reverse=True)
    seen_final: set[str] = set()
    deduped = []
    for r in researchers:
        rid = str(r["_id"])
        if rid not in seen_final:
            seen_final.add(rid)
            deduped.append(r)
        if len(deduped) >= 8:
            break

    # Fallback if we still have fewer than 6
    if len(deduped) < 6:
        more = await db.users.find(
            {"_id": {"$nin": list(excluded_ids)}, "is_demo": {"$ne": True}, "profile_visibility": {"$ne": "private"}}
        ).limit(8).to_list(8)
        for r in more:
            if str(r["_id"]) not in seen_final and len(deduped) < 8:
                seen_final.add(str(r["_id"]))
                deduped.append(r)

    # ── Trending topics — collabs + publication concepts ──────────────────────
    collab_pipeline = [
        {"$match": {"is_demo": {"$ne": True}}},
        {"$unwind": "$research_area"},
        {"$group": {"_id": "$research_area", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    trending_collabs = await db.collaborations.aggregate(collab_pipeline).to_list(10)
    collab_topic_counts = {t["_id"]: t["count"] for t in trending_collabs if t["_id"]}

    pub_topic_pipeline = [
        {"$match": {"openalex_enriched_at": {"$exists": True}}},
        {"$unwind": "$concepts"},
        {"$group": {"_id": "$concepts.display_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    trending_pub_topics = await db.publications.aggregate(pub_topic_pipeline).to_list(10)
    for t in trending_pub_topics:
        name = t["_id"]
        if name:
            collab_topic_counts[name] = collab_topic_counts.get(name, 0) + t["count"]

    trending = sorted(
        [{"topic": k, "count": v} for k, v in collab_topic_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:8]

    # ── Grants & conferences ──────────────────────────────────────────────────
    grants = await db.grants.find({}).limit(5).to_list(5)
    conferences = await db.conferences.find({}).limit(5).to_list(5)

    def _ser(d):
        x = dict(d)
        x["id"] = str(x.pop("_id"))
        return x

    def _ser_researcher(r):
        pub = serialize_public_user(r)
        pub["match_score"] = researcher_score(r)
        return pub

    return {
        "collaborations": collabs_out,
        "researchers": [_ser_researcher(r) for r in deduped[:8]],
        "trending_topics": trending,
        "grants": [_ser(g) for g in grants],
        "conferences": [_ser(c) for c in conferences],
    }
