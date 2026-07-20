"""
Enterprise Data Access Layer — Repository Pattern with Row-Level Security.

Import pattern:
    from repo import MissionRepository, SecurityContext, Specs

For FastAPI routers, use the Depends factories from repo.deps instead:
    from repo.deps import get_mission_repo

Transparent shim (transitional migration path):
    db = DBProxy(get_db(), SecurityContext.from_user(user))
"""
from .security_context import SecurityContext
from .specs            import QuerySpec, Specs
from .base             import (
    BaseRepository,
    NotFoundError,
    PermissionError,
    ConflictError,
    RepositoryError,
)
from .audit            import AuditTrail
from .cache            import RepositoryCache, get_cache, clear_all_caches
from .events           import RepoEvent, RepoEventBus, get_event_bus, init_event_bus
from .transaction      import Tx, transaction
from .shim             import DBProxy, CollectionProxy, make_db_proxy

# Bounded-context repositories
from .missions              import MissionRepository
from .users                 import UserRepository
from .workspaces            import WorkspaceRepository
from .publications          import PublicationRepository
from .grants                import GrantRepository
from .institutions          import InstitutionRepository
from .notifications         import NotificationRepository
from .recommendations       import RecommendationRepository
from .twin                  import TwinRepository
from .knowledge_graph       import (
    KnowledgeGraphNodeRepository,
    KnowledgeGraphEdgeRepository,
)
# Sprint 1.2 — new domain repositories
from .manuscripts           import ManuscriptRepository, ManuscriptVersionRepository
from .projects              import ProjectRepository
from .collaborations        import CollaborationRepository, CollaborationRequestRepository
from .teaching              import (
    TeachingWorkspaceRepository,
    TeachingLessonRepository,
    TeachingAssessmentRepository,
)
from .files_repo            import FileRepository
from .messaging             import ConversationRepository, MessageRepository
from .marketplace           import MarketplaceListingRepository
from .expertise             import ExpertiseRequestRepository
from .institution_members   import InstitutionMembershipRepository
from .analytics             import AIRequestRepository, ResearchImpactRepository

__all__ = [
    # Core
    "SecurityContext",
    "QuerySpec",
    "Specs",
    "BaseRepository",
    "NotFoundError",
    "PermissionError",
    "ConflictError",
    "RepositoryError",
    "AuditTrail",
    "RepositoryCache",
    "get_cache",
    "clear_all_caches",
    "RepoEvent",
    "RepoEventBus",
    "get_event_bus",
    "init_event_bus",
    "Tx",
    "transaction",
    # Shim
    "DBProxy",
    "CollectionProxy",
    "make_db_proxy",
    # Repositories — original
    "MissionRepository",
    "UserRepository",
    "WorkspaceRepository",
    "PublicationRepository",
    "GrantRepository",
    "InstitutionRepository",
    "NotificationRepository",
    "RecommendationRepository",
    "TwinRepository",
    "KnowledgeGraphNodeRepository",
    "KnowledgeGraphEdgeRepository",
    # Repositories — Sprint 1.2
    "ManuscriptRepository",
    "ManuscriptVersionRepository",
    "ProjectRepository",
    "CollaborationRepository",
    "CollaborationRequestRepository",
    "TeachingWorkspaceRepository",
    "TeachingLessonRepository",
    "TeachingAssessmentRepository",
    "FileRepository",
    "ConversationRepository",
    "MessageRepository",
    "MarketplaceListingRepository",
    "ExpertiseRequestRepository",
    "InstitutionMembershipRepository",
    "AIRequestRepository",
    "ResearchImpactRepository",
]
