"""Unified Project Center — every research project as the central object."""
from __future__ import annotations

import threading
import time

from .models import ResearchProject

_MAX_PROJECTS = 5_000

_LINKABLE_FIELDS: dict[str, str] = {
    "document":    "document_ids",
    "grant":       "grant_ids",
    "publication": "publication_ids",
    "journal":     "journal_targets",
    "conference":  "conference_targets",
    "team":        "team_cohorts",
    "task":        "tasks",
    "tag":         "tags",
}


class ProjectCenter:
    def __init__(self):
        self._lock     = threading.Lock()
        self._projects: dict[str, ResearchProject] = {}
        self._by_cohort: dict[str, list[str]] = {}  # cohort → project_ids

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_project(
        self,
        name:         str,
        owner_cohort: str,
        description:  str  = "",
        tags:         list | None = None,
        metadata:     dict | None = None,
    ) -> ResearchProject:
        project = ResearchProject(
            name=name,
            description=description,
            owner_cohort=owner_cohort,
            tags=tags or [],
            metadata=metadata or {},
        )
        with self._lock:
            self._projects[project.project_id] = project
            self._by_cohort.setdefault(owner_cohort, []).append(project.project_id)
            if len(self._projects) > _MAX_PROJECTS:
                oldest = next(iter(self._projects))
                old    = self._projects.pop(oldest)
                cohort_list = self._by_cohort.get(old.owner_cohort, [])
                if oldest in cohort_list:
                    cohort_list.remove(oldest)
        return project

    def get_project(self, project_id: str) -> ResearchProject | None:
        with self._lock:
            return self._projects.get(project_id)

    def update_project(self, project_id: str, updates: dict) -> ResearchProject | None:
        _allowed = {"name", "description", "status", "workspace_id", "workflow_id", "metadata"}
        with self._lock:
            project = self._projects.get(project_id)
            if not project:
                return None
            for key, val in updates.items():
                if key in _allowed and hasattr(project, key):
                    setattr(project, key, val)
            project.updated_at = time.time()
        return project

    def get_projects_by_cohort(self, owner_cohort: str, status: str | None = None) -> list[ResearchProject]:
        with self._lock:
            ids      = list(self._by_cohort.get(owner_cohort, []))
            projects = [self._projects[pid] for pid in ids if pid in self._projects]
        if status:
            projects = [p for p in projects if p.status == status]
        return projects

    def get_active_projects(self) -> list[ResearchProject]:
        with self._lock:
            return [p for p in self._projects.values() if p.status == "active"]

    def get_all_projects(self, limit: int = 100) -> list[ResearchProject]:
        with self._lock:
            return list(self._projects.values())[-limit:]

    # ── Linking ───────────────────────────────────────────────────────────────

    def link_entity(self, project_id: str, entity_type: str, entity_id: str) -> bool:
        field_name = _LINKABLE_FIELDS.get(entity_type)
        if not field_name:
            return False
        with self._lock:
            project = self._projects.get(project_id)
            if not project:
                return False
            lst = getattr(project, field_name, [])
            if entity_id not in lst:
                lst.append(entity_id)
            project.updated_at = time.time()
        return True

    def unlink_entity(self, project_id: str, entity_type: str, entity_id: str) -> bool:
        field_name = _LINKABLE_FIELDS.get(entity_type)
        if not field_name:
            return False
        with self._lock:
            project = self._projects.get(project_id)
            if not project:
                return False
            lst = getattr(project, field_name, [])
            if entity_id in lst:
                lst.remove(entity_id)
            project.updated_at = time.time()
        return True

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_project_summary(self, project_id: str) -> dict | None:
        with self._lock:
            project = self._projects.get(project_id)
        if not project:
            return None
        return {
            "project_id":         project.project_id,
            "name":               project.name,
            "status":             project.status,
            "team_size":          len(project.team_cohorts),
            "document_count":     len(project.document_ids),
            "grant_count":        len(project.grant_ids),
            "publication_count":  len(project.publication_ids),
            "journal_targets":    len(project.journal_targets),
            "conference_targets": len(project.conference_targets),
            "task_count":         len(project.tasks),
            "has_workspace":      bool(project.workspace_id),
            "has_workflow":       bool(project.workflow_id),
            "tags":               project.tags,
            "created_at":         project.created_at,
            "updated_at":         project.updated_at,
        }

    def search_projects(self, query: str, owner_cohort: str | None = None) -> list[ResearchProject]:
        q = query.lower()
        with self._lock:
            src = list(self._projects.values())
        results = []
        for p in src:
            if owner_cohort and p.owner_cohort != owner_cohort:
                continue
            if q in p.name.lower() or q in p.description.lower() or any(q in t.lower() for t in p.tags):
                results.append(p)
        return results

    def stats(self) -> dict:
        with self._lock:
            total  = len(self._projects)
            active = sum(1 for p in self._projects.values() if p.status == "active")
        return {"total": total, "active": active}
