"""
Internal connector — maps existing Synaptiq platform objects into the LKG.

Reads: users, manuscripts, projects, collaborations, grants, lessons
Writes: researcher, institution, manuscript, project, funding_program,
        collaboration, topic, lesson nodes + all relationship edges.

All edges are status='verified' (source = "Synaptiq platform").
This is the primary data source for the LKG — run it first.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from ..graph_store import upsert_node, upsert_edge
from ..models import LKGNode, LKGEdge, make_node_id
from .base_connector import BaseConnector, IngestionResult

logger = logging.getLogger("lkg.ingestion.internal")

_SOURCE = "Synaptiq platform"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


class InternalConnector(BaseConnector):
    name        = "internal"
    source      = _SOURCE
    description = "Maps all platform entities (users, manuscripts, projects, grants, collaborations) into the LKG"

    # ------------------------------------------------------------------ #
    # Users → researcher nodes + institution nodes + AFFILIATED_WITH edges #
    # + BELONGS_TO_TOPIC edges per research interest                       #
    # ------------------------------------------------------------------ #
    async def _ingest_users(self, db, result: IngestionResult) -> None:
        cursor = db.users.find({}, {
            "_id": 1, "name": 1, "email": 1, "institution": 1,
            "research_interests": 1, "orcid": 1, "bio": 1,
            "academic_position": 1, "country": 1,
        })
        async for user in cursor:
            uid       = str(user["_id"])
            node_id   = make_node_id("researcher", "platform", uid)
            name      = user.get("name") or user.get("email", uid)

            researcher_node = LKGNode(
                node_id  = node_id,
                type     = "researcher",
                label    = name,
                source   = _SOURCE,
                metadata = {
                    "email":     user.get("email"),
                    "orcid":     user.get("orcid"),
                    "position":  user.get("academic_position"),
                    "country":   user.get("country"),
                    "bio":       (user.get("bio") or "")[:500],
                    "platform_id": uid,
                },
                confidence = "high",
            )
            op = await upsert_node(db, researcher_node)
            if op and op.upserted_id:
                result.nodes_added += 1
            else:
                result.nodes_updated += 1

            # Institution node + edge
            institution_name = user.get("institution")
            if institution_name:
                inst_slug = _slug(institution_name)
                inst_id   = make_node_id("institution", "name", inst_slug)
                inst_node = LKGNode(
                    node_id    = inst_id,
                    type       = "institution",
                    label      = institution_name,
                    source     = _SOURCE,
                    metadata   = {"slug": inst_slug},
                    confidence = "medium",
                )
                await upsert_node(db, inst_node)

                edge = LKGEdge(
                    from_id = node_id,
                    to_id   = inst_id,
                    type    = "AFFILIATED_WITH",
                    source  = _SOURCE,
                    status  = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, edge)
                if op and op.upserted_id:
                    result.edges_added += 1

            # Research interest → topic nodes + BELONGS_TO_TOPIC edges
            for interest in (user.get("research_interests") or []):
                interest = str(interest).strip()
                if not interest:
                    continue
                topic_id = make_node_id("topic", "keyword", _slug(interest))
                topic_node = LKGNode(
                    node_id    = topic_id,
                    type       = "topic",
                    label      = interest,
                    source     = _SOURCE,
                    confidence = "high",
                )
                await upsert_node(db, topic_node)

                te = LKGEdge(
                    from_id  = node_id,
                    to_id    = topic_id,
                    type     = "BELONGS_TO_TOPIC",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, te)
                if op and op.upserted_id:
                    result.edges_added += 1

    # ------------------------------------------------------------------ #
    # Manuscripts → manuscript nodes + AUTHORED edges + topic edges        #
    # ------------------------------------------------------------------ #
    async def _ingest_manuscripts(self, db, result: IngestionResult) -> None:
        cursor = db.manuscripts.find({}, {
            "_id": 1, "title": 1, "user_id": 1, "abstract": 1,
            "keywords": 1, "status": 1, "doi": 1, "journal": 1,
            "created_at": 1, "updated_at": 1,
        })
        async for ms in cursor:
            ms_id_str = str(ms["_id"])
            node_id   = make_node_id("manuscript", "platform", ms_id_str)

            ms_node = LKGNode(
                node_id  = node_id,
                type     = "manuscript",
                label    = (ms.get("title") or "Untitled manuscript")[:200],
                source   = _SOURCE,
                metadata = {
                    "status":     ms.get("status"),
                    "doi":        ms.get("doi"),
                    "journal":    ms.get("journal"),
                    "abstract":   (ms.get("abstract") or "")[:400],
                    "platform_id": ms_id_str,
                },
                confidence = "high",
            )
            op = await upsert_node(db, ms_node)
            if op and op.upserted_id:
                result.nodes_added += 1
            else:
                result.nodes_updated += 1

            # AUTHORED edge: researcher → manuscript
            uid = str(ms.get("user_id", ""))
            if uid:
                researcher_id = make_node_id("researcher", "platform", uid)
                ae = LKGEdge(
                    from_id  = researcher_id,
                    to_id    = node_id,
                    type     = "AUTHORED",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, ae)
                if op and op.upserted_id:
                    result.edges_added += 1

            # Journal node + SUBMITTED_TO edge
            journal_name = ms.get("journal")
            if journal_name:
                j_id = make_node_id("journal", "name", _slug(journal_name))
                j_node = LKGNode(
                    node_id    = j_id,
                    type       = "journal",
                    label      = journal_name,
                    source     = _SOURCE,
                    confidence = "medium",
                )
                await upsert_node(db, j_node)
                je = LKGEdge(
                    from_id  = node_id,
                    to_id    = j_id,
                    type     = "SUBMITTED_TO",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {"status": ms.get("status")},
                )
                op = await upsert_edge(db, je)
                if op and op.upserted_id:
                    result.edges_added += 1

            # Keyword → topic + BELONGS_TO_TOPIC
            for kw in (ms.get("keywords") or []):
                kw = str(kw).strip()
                if not kw:
                    continue
                t_id = make_node_id("topic", "keyword", _slug(kw))
                t_node = LKGNode(
                    node_id    = t_id,
                    type       = "topic",
                    label      = kw,
                    source     = _SOURCE,
                    confidence = "high",
                )
                await upsert_node(db, t_node)
                te = LKGEdge(
                    from_id  = node_id,
                    to_id    = t_id,
                    type     = "BELONGS_TO_TOPIC",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, te)
                if op and op.upserted_id:
                    result.edges_added += 1

    # ------------------------------------------------------------------ #
    # Projects → project nodes + WORKS_ON edges                           #
    # ------------------------------------------------------------------ #
    async def _ingest_projects(self, db, result: IngestionResult) -> None:
        cursor = db.projects.find({}, {
            "_id": 1, "title": 1, "user_id": 1, "description": 1,
            "status": 1, "tags": 1, "created_at": 1,
        })
        async for proj in cursor:
            proj_id = str(proj["_id"])
            node_id = make_node_id("project", "platform", proj_id)

            proj_node = LKGNode(
                node_id  = node_id,
                type     = "project",
                label    = (proj.get("title") or "Untitled project")[:200],
                source   = _SOURCE,
                metadata = {
                    "status":     proj.get("status"),
                    "platform_id": proj_id,
                },
                confidence = "high",
            )
            op = await upsert_node(db, proj_node)
            if op and op.upserted_id:
                result.nodes_added += 1
            else:
                result.nodes_updated += 1

            uid = str(proj.get("user_id", ""))
            if uid:
                researcher_id = make_node_id("researcher", "platform", uid)
                we = LKGEdge(
                    from_id  = researcher_id,
                    to_id    = node_id,
                    type     = "WORKS_ON",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, we)
                if op and op.upserted_id:
                    result.edges_added += 1

            for tag in (proj.get("tags") or []):
                tag = str(tag).strip()
                if not tag:
                    continue
                t_id = make_node_id("topic", "keyword", _slug(tag))
                t_node = LKGNode(
                    node_id    = t_id,
                    type       = "topic",
                    label      = tag,
                    source     = _SOURCE,
                    confidence = "high",
                )
                await upsert_node(db, t_node)
                te = LKGEdge(
                    from_id  = node_id,
                    to_id    = t_id,
                    type     = "BELONGS_TO_TOPIC",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {},
                )
                op = await upsert_edge(db, te)
                if op and op.upserted_id:
                    result.edges_added += 1

    # ------------------------------------------------------------------ #
    # Collaborations → COLLABORATES_WITH bidirectional edges               #
    # ------------------------------------------------------------------ #
    async def _ingest_collaborations(self, db, result: IngestionResult) -> None:
        cursor = db.collaborations.find({}, {
            "_id": 1, "requester_id": 1, "recipient_id": 1, "status": 1,
            "created_at": 1, "project_id": 1,
        })
        async for collab in cursor:
            if collab.get("status") != "accepted":
                continue
            req_id = make_node_id("researcher", "platform", str(collab["requester_id"]))
            rec_id = make_node_id("researcher", "platform", str(collab["recipient_id"]))

            edge = LKGEdge(
                from_id  = req_id,
                to_id    = rec_id,
                type     = "COLLABORATES_WITH",
                source   = _SOURCE,
                status   = "verified",
                metadata = {"collaboration_id": str(collab["_id"])},
            )
            op = await upsert_edge(db, edge)
            if op and op.upserted_id:
                result.edges_added += 1

    # ------------------------------------------------------------------ #
    # Grants → funding_program nodes + APPLIED_FOR edges                  #
    # ------------------------------------------------------------------ #
    async def _ingest_grants(self, db, result: IngestionResult) -> None:
        cursor = db.grants.find({}, {
            "_id": 1, "title": 1, "user_id": 1, "funder": 1,
            "status": 1, "deadline": 1, "amount": 1,
        })
        async for grant in cursor:
            grant_id = str(grant["_id"])
            node_id  = make_node_id("funding_program", "platform", grant_id)

            grant_node = LKGNode(
                node_id  = node_id,
                type     = "funding_program",
                label    = (grant.get("title") or "Untitled grant")[:200],
                source   = _SOURCE,
                metadata = {
                    "funder":     grant.get("funder"),
                    "status":     grant.get("status"),
                    "deadline":   str(grant.get("deadline", "")),
                    "amount":     grant.get("amount"),
                    "platform_id": grant_id,
                },
                confidence = "high",
            )
            op = await upsert_node(db, grant_node)
            if op and op.upserted_id:
                result.nodes_added += 1
            else:
                result.nodes_updated += 1

            uid = str(grant.get("user_id", ""))
            if uid:
                researcher_id = make_node_id("researcher", "platform", uid)
                ae = LKGEdge(
                    from_id  = researcher_id,
                    to_id    = node_id,
                    type     = "APPLIED_FOR",
                    source   = _SOURCE,
                    status   = "verified",
                    metadata = {"status": grant.get("status")},
                )
                op = await upsert_edge(db, ae)
                if op and op.upserted_id:
                    result.edges_added += 1

    # ------------------------------------------------------------------ #
    # Lessons → lesson nodes + TEACHES edges                              #
    # ------------------------------------------------------------------ #
    async def _ingest_lessons(self, db, result: IngestionResult) -> None:
        try:
            cursor = db.lessons.find({}, {
                "_id": 1, "title": 1, "instructor_id": 1, "topic": 1, "status": 1,
            })
            async for lesson in cursor:
                lesson_id = str(lesson["_id"])
                node_id   = make_node_id("lesson", "platform", lesson_id)

                lesson_node = LKGNode(
                    node_id    = node_id,
                    type       = "lesson",
                    label      = (lesson.get("title") or "Untitled lesson")[:200],
                    source     = _SOURCE,
                    confidence = "high",
                    metadata   = {"topic": lesson.get("topic")},
                )
                op = await upsert_node(db, lesson_node)
                if op and op.upserted_id:
                    result.nodes_added += 1

                instructor_id_str = str(lesson.get("instructor_id", ""))
                if instructor_id_str:
                    researcher_id = make_node_id("researcher", "platform", instructor_id_str)
                    te = LKGEdge(
                        from_id  = researcher_id,
                        to_id    = node_id,
                        type     = "TEACHES",
                        source   = _SOURCE,
                        status   = "verified",
                        metadata = {},
                    )
                    op = await upsert_edge(db, te)
                    if op and op.upserted_id:
                        result.edges_added += 1
        except Exception as exc:
            result.errors.append(f"lessons: {exc}")

    # ------------------------------------------------------------------ #
    # Entry point                                                          #
    # ------------------------------------------------------------------ #
    async def ingest(self, db: Any, **kwargs) -> IngestionResult:
        result = IngestionResult(connector=self.name)
        logger.info("Starting internal platform ingestion")

        for step_name, step in [
            ("users",           self._ingest_users),
            ("manuscripts",     self._ingest_manuscripts),
            ("projects",        self._ingest_projects),
            ("collaborations",  self._ingest_collaborations),
            ("grants",          self._ingest_grants),
            ("lessons",         self._ingest_lessons),
        ]:
            try:
                await step(db, result)
                logger.info("  %s done — nodes: %d  edges: %d",
                            step_name, result.nodes_added, result.edges_added)
            except Exception as exc:
                error_msg = f"{step_name}: {exc}"
                result.errors.append(error_msg)
                logger.error("[internal] %s", error_msg)

        return result.finish()
