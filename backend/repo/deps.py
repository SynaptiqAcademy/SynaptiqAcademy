"""
FastAPI dependency injection for the Repository Layer.

Usage in a router:

    from repo.deps import get_mission_repo, CurrentUser

    @router.get("/missions")
    async def list_missions(
        repo: MissionRepository = Depends(get_mission_repo),
    ):
        return await repo.list_missions()

The SecurityContext is derived from the authenticated user automatically.
Routers never call SecurityContext.from_user() directly — they just declare
the typed repo dependency and the correct context is injected.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from .security_context import SecurityContext

# Lazy imports to avoid circular dependencies at module load time
def _get_auth():
    from auth_utils import get_current_user
    return get_current_user

def _get_db():
    from db import get_db
    return get_db


# ── SecurityContext dependency ─────────────────────────────────────────────────

async def get_security_context(
    user: dict = Depends(lambda: _get_auth()()),
) -> SecurityContext:
    """Derive SecurityContext from the authenticated user."""
    return SecurityContext.from_user(user)


async def get_optional_security_context(
    user: dict | None = Depends(lambda: _get_auth()()),
) -> SecurityContext | None:
    """Like get_security_context but allows unauthenticated requests."""
    if not user:
        return None
    return SecurityContext.from_user(user)


# ── Repository factory dependencies ───────────────────────────────────────────

async def get_mission_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .missions import MissionRepository
    ctx = SecurityContext.from_user(user)
    return MissionRepository(db, ctx)


async def get_user_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .users import UserRepository
    ctx = SecurityContext.from_user(user)
    return UserRepository(db, ctx)


async def get_workspace_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .workspaces import WorkspaceRepository
    ctx = SecurityContext.from_user(user)
    return WorkspaceRepository(db, ctx)


async def get_publication_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .publications import PublicationRepository
    ctx = SecurityContext.from_user(user)
    return PublicationRepository(db, ctx)


async def get_grant_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .grants import GrantRepository
    ctx = SecurityContext.from_user(user)
    return GrantRepository(db, ctx)


async def get_institution_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .institutions import InstitutionRepository
    ctx = SecurityContext.from_user(user)
    return InstitutionRepository(db, ctx)


async def get_notification_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .notifications import NotificationRepository
    ctx = SecurityContext.from_user(user)
    return NotificationRepository(db, ctx)


async def get_recommendation_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .recommendations import RecommendationRepository
    ctx = SecurityContext.from_user(user)
    return RecommendationRepository(db, ctx)


async def get_twin_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .twin import TwinRepository
    ctx = SecurityContext.from_user(user)
    return TwinRepository(db, ctx)


async def get_kg_node_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .knowledge_graph import KnowledgeGraphNodeRepository
    ctx = SecurityContext.from_user(user)
    return KnowledgeGraphNodeRepository(db, ctx)


async def get_kg_edge_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .knowledge_graph import KnowledgeGraphEdgeRepository
    ctx = SecurityContext.from_user(user)
    return KnowledgeGraphEdgeRepository(db, ctx)


# ── Sprint 1.2 — DBProxy dependency (primary migration mechanism) ─────────────

async def get_db_proxy(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    """
    FastAPI dependency that returns a security-context-aware DBProxy.

    Usage in routers:
        from repo.deps import get_db_proxy

        @router.get("/items")
        async def list_items(db: DBProxy = Depends(get_db_proxy)):
            return await db.items.find({}).to_list(50)
    """
    from .shim import DBProxy
    ctx = SecurityContext.from_user(user)
    return DBProxy(db, ctx)


async def get_system_db_proxy(db=Depends(lambda: _get_db()())):
    """DBProxy with system context — for public/unauthenticated endpoints."""
    from .shim import DBProxy
    return DBProxy(db, SecurityContext.system())


# ── Sprint 1.2 — New domain repository dependencies ──────────────────────────

async def get_manuscript_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .manuscripts import ManuscriptRepository
    return ManuscriptRepository(db, SecurityContext.from_user(user))


async def get_project_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .projects import ProjectRepository
    return ProjectRepository(db, SecurityContext.from_user(user))


async def get_collaboration_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .collaborations import CollaborationRepository
    return CollaborationRepository(db, SecurityContext.from_user(user))


async def get_teaching_workspace_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .teaching import TeachingWorkspaceRepository
    return TeachingWorkspaceRepository(db, SecurityContext.from_user(user))


async def get_teaching_lesson_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .teaching import TeachingLessonRepository
    return TeachingLessonRepository(db, SecurityContext.from_user(user))


async def get_file_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .files_repo import FileRepository
    return FileRepository(db, SecurityContext.from_user(user))


async def get_conversation_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .messaging import ConversationRepository
    return ConversationRepository(db, SecurityContext.from_user(user))


async def get_marketplace_listing_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .marketplace import MarketplaceListingRepository
    return MarketplaceListingRepository(db, SecurityContext.from_user(user))


async def get_expertise_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .expertise import ExpertiseRequestRepository
    return ExpertiseRequestRepository(db, SecurityContext.from_user(user))


async def get_institution_membership_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .institution_members import InstitutionMembershipRepository
    return InstitutionMembershipRepository(db, SecurityContext.from_user(user))


async def get_ai_request_repo(
    user: dict = Depends(lambda: _get_auth()()),
    db=Depends(lambda: _get_db()()),
):
    from .analytics import AIRequestRepository
    return AIRequestRepository(db, SecurityContext.from_user(user))


# ── System-context factory (for workers / internal services) ──────────────────

def system_mission_repo(db) -> "MissionRepository":  # type: ignore[name-defined]
    """Return a MissionRepository with system (admin) context — for workers only."""
    from .missions import MissionRepository
    return MissionRepository(db, SecurityContext.system())


def system_notification_repo(db) -> "NotificationRepository":  # type: ignore[name-defined]
    """Return a NotificationRepository with system context — for workers/events."""
    from .notifications import NotificationRepository
    return NotificationRepository(db, SecurityContext.system())
