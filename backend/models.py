from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# USER TYPE SYSTEM
# Two new fields added to the users collection:
#   user_type      — controlled 9-value identity classification
#   primary_domain — research | teaching | both
#
# Preserved (unchanged in DB): users.role (platform), workspace member_roles,
# institution_memberships.role, users.academic_role (free-text job title).
# ──────────────────────────────────────────────────────────────────────────────

USER_TYPE_VALUES = Literal[
    "undergraduate_student",
    "masters_student",
    "phd_candidate",
    "postdoctoral_researcher",
    "researcher",
    "educator",
    "university_faculty",
    "trainer",
    "industry_professional",
]

PRIMARY_DOMAIN_VALUES = Literal["research", "teaching", "both"]

USER_TYPE_LABELS: dict[str, str] = {
    "undergraduate_student":  "Undergraduate Student",
    "masters_student":        "Master's Student",
    "phd_candidate":          "PhD Candidate",
    "postdoctoral_researcher": "Postdoctoral Researcher",
    "researcher":             "Researcher",
    "educator":               "Educator",
    "university_faculty":     "University Faculty",
    "trainer":                "Trainer",
    "industry_professional":  "Industry Professional",
}

PRIMARY_DOMAIN_LABELS: dict[str, str] = {
    "research": "Research",
    "teaching": "Teaching",
    "both":     "Research & Teaching",
}

# Legacy academic_role free-text → canonical user_type
# Used by migration script and any future sync.
ACADEMIC_ROLE_MIGRATION_MAP: dict[str, str] = {
    # PhD / doctoral
    "phd candidate":              "phd_candidate",
    "phd student":                "phd_candidate",
    "doctoral candidate":         "phd_candidate",
    "doctoral student":           "phd_candidate",
    "doctoral researcher":        "phd_candidate",
    # Postdoctoral
    "postdoc":                    "postdoctoral_researcher",
    "postdoctoral researcher":    "postdoctoral_researcher",
    "postdoctoral fellow":        "postdoctoral_researcher",
    "post-doctoral researcher":   "postdoctoral_researcher",
    "post-doc":                   "postdoctoral_researcher",
    "postdoctoral associate":     "postdoctoral_researcher",
    # Researcher
    "researcher":                 "researcher",
    "research scientist":         "researcher",
    "research director":          "researcher",
    "research director":          "researcher",
    "senior researcher":          "researcher",
    "independent researcher":     "researcher",
    "research associate":         "researcher",
    # Faculty
    "professor":                  "university_faculty",
    "full professor":             "university_faculty",
    "associate professor":        "university_faculty",
    "assistant professor":        "university_faculty",
    "lecturer":                   "university_faculty",
    "senior lecturer":            "university_faculty",
    "associate lecturer":         "university_faculty",
    # Educators
    "instructor":                 "educator",
    "teacher":                    "educator",
    "high school teacher":        "educator",
    "school teacher":             "educator",
    "secondary school teacher":   "educator",
    "teaching assistant":         "educator",
    # Students
    "master student":             "masters_student",
    "master's student":           "masters_student",
    "masters student":            "masters_student",
    "graduate student":           "masters_student",
    "undergraduate":              "undergraduate_student",
    "undergraduate student":      "undergraduate_student",
    "bachelor's student":         "undergraduate_student",
    "bachelors student":          "undergraduate_student",
    # Trainer
    "trainer":                    "trainer",
    "training specialist":        "trainer",
    "corporate trainer":          "trainer",
    # Industry professional
    "industry consultant":        "industry_professional",
    "industry researcher":        "industry_professional",
    "innovation manager":         "industry_professional",
    "r&d specialist":             "industry_professional",
    "data scientist":             "industry_professional",
    "industry professional":      "industry_professional",
    "r&d manager":                "industry_professional",
    "research engineer":          "industry_professional",
}


# ============== AUTH ==============
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


# ============== USER PROFILE ==============
class ProfileUpdate(BaseModel):
    # Identity
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    academic_role: Optional[str] = None
    career_stage: Optional[str] = None  # early_career | mid_career | senior | professor | industry
    user_type: Optional[USER_TYPE_VALUES] = None
    primary_domain: Optional[PRIMARY_DOMAIN_VALUES] = None
    biography: Optional[str] = None
    # Academic identifiers — orcid excluded (OAuth only)
    google_scholar: Optional[str] = None
    researchgate: Optional[str] = None
    scopus_id: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    # Research profile
    research_areas: Optional[List[str]] = None
    research_interests: Optional[List[str]] = None
    research_keywords: Optional[List[str]] = None
    methods: Optional[List[str]] = None
    methodological_expertise: Optional[List[str]] = None
    software_skills: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    can_contribute: Optional[List[str]] = None
    looking_for: Optional[List[str]] = None
    expertise_role_tags: Optional[List[str]] = None
    teaching_areas: Optional[List[str]] = None
    professional_expertise: Optional[List[str]] = None
    # Availability
    availability: Optional[str] = None
    available_for_collaboration: Optional[bool] = None
    available_for_supervision: Optional[bool] = None
    available_for_reviewing: Optional[bool] = None
    available_for_consulting: Optional[bool] = None
    # Media
    avatar_url: Optional[str] = None
    cover_photo: Optional[str] = None
    # Career records (manually added — ORCID records are set via OAuth only)
    awards: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    memberships: Optional[List[str]] = None
    # External counts (read-only from OpenAlex — kept here for legacy compatibility only)
    publications_count: Optional[int] = None
    conferences_count: Optional[int] = None

    @field_validator("avatar_url", "website", "cover_photo", mode="before")
    @classmethod
    def _url_must_be_https(cls, v):
        if v and not str(v).startswith(("https://", "http://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class OnboardingComplete(BaseModel):
    first_name: str
    last_name: str
    country: str
    user_type: USER_TYPE_VALUES
    primary_domain: PRIMARY_DOMAIN_VALUES
    academic_role: Optional[str] = ""      # optional job title / professional title
    institution: str
    department: str
    # Research fields — required for research/hybrid users, empty-list allowed for teaching-only
    research_areas: List[str] = []
    research_interests: List[str] = []
    research_keywords: List[str] = []
    # Teaching fields — required for teaching/hybrid users
    teaching_areas: Optional[List[str]] = None
    # Industry/professional fields
    professional_expertise: Optional[List[str]] = None
    orcid: Optional[str] = ""
    google_scholar: Optional[str] = ""
    researchgate: Optional[str] = ""
    linkedin: Optional[str] = ""
    publications_count: int = 0
    conferences_count: int = 0


# ============== COLLABORATIONS ==============
class CollaborationCreate(BaseModel):
    title: str
    description: str
    collab_type: str  # Journal Article, Conference Paper, etc.
    research_area: str
    skills_needed: List[str] = []
    team_size: int = 2
    duration: str = "3 months"
    publication_goal: Optional[str] = None
    funding_status: Optional[str] = None


class ApplicationCreate(BaseModel):
    message: str


class ApplicationDecision(BaseModel):
    decision: str  # "accepted" | "rejected"


# ============== PROJECTS ==============
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    visibility: str = "team"  # private | team | public
    # Pre-fill fields from Gap Finder / Collaboration Intelligence
    source: Optional[str] = None          # "gap_finder" | "collab_intel" | None
    research_gap: Optional[str] = ""
    objectives: Optional[List[str]] = None
    research_questions: Optional[List[str]] = None
    hypotheses: Optional[List[str]] = None
    methodology: Optional[str] = ""
    keywords: Optional[List[str]] = None
    initial_member_ids: Optional[List[str]] = None  # send collab requests on creation


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    problem_statement: Optional[str] = None
    research_gap: Optional[str] = None
    objectives: Optional[List[str]] = None
    research_questions: Optional[List[str]] = None
    hypotheses: Optional[List[str]] = None
    expected_contributions: Optional[str] = None
    methodology: Optional[str] = None
    data_sources: Optional[str] = None
    sampling: Optional[str] = None
    analysis_methods: Optional[str] = None
    ethics: Optional[str] = None


class TaskCreate(BaseModel):
    title: str
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    status: str = "todo"
    # Gantt/timeline fields (Workspace redesign Phase 7) — all optional so
    # existing Kanban-only callers are unaffected.
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    progress: Optional[int] = Field(default=0, ge=0, le=100)
    depends_on: Optional[List[str]] = Field(default=None, max_length=200)  # other task ids in the same project
    parent_task_id: Optional[str] = None
    is_milestone: Optional[bool] = False


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=300)
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    depends_on: Optional[List[str]] = Field(default=None, max_length=200)
    parent_task_id: Optional[str] = None
    is_milestone: Optional[bool] = None


class MilestoneCreate(BaseModel):
    title: str
    due_date: Optional[str] = None
    description: Optional[str] = ""


class LiteratureCreate(BaseModel):
    title: str
    authors: Optional[str] = ""
    year: Optional[int] = None
    source_type: str = "Paper"  # Paper | Book | Report
    notes: Optional[str] = ""
    url: Optional[str] = ""


# ============== MESSAGES ==============
class MessageCreate(BaseModel):
    recipient_id: str
    content: str


# ============== AI ==============
class AIAssistRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    context: Optional[str] = Field("", max_length=8000)


# ============== WORKSPACES ==============
class WorkspaceCreate(BaseModel):
    name:             str
    description:      Optional[str] = ""
    workspace_type:   Optional[str] = "Research Project"
    visibility:       Optional[str] = "private"
    institution:      Optional[str] = None
    research_area:    Optional[str] = None
    keywords:         Optional[List[str]] = None


class WorkspaceUpdate(BaseModel):
    name:           Optional[str] = None
    description:    Optional[str] = None
    workspace_type: Optional[str] = None
    visibility:     Optional[str] = None
    institution:    Optional[str] = None
    research_area:  Optional[str] = None
    keywords:       Optional[List[str]] = None
    status:         Optional[str] = None
    project_ids:    Optional[List[str]] = None
    # CRediT co-authorship — author order + contribution roles per member,
    # and the designated corresponding author. Previously tracked only in
    # frontend component state and never persisted (lost on every refresh).
    coauthor_order:          Optional[List[str]] = None
    coauthor_roles:          Optional[Dict[str, List[str]]] = None
    corresponding_author_id: Optional[str] = None


# ============== MANUSCRIPTS ==============
class ManuscriptCreate(BaseModel):
    title:             str
    abstract:          Optional[str] = ""
    keywords:          Optional[List[str]] = None
    manuscript_type:   Optional[str] = "Journal Article"
    project_id:        Optional[str] = ""
    workspace_id:      Optional[str] = ""
    target_journal_id: Optional[str] = ""
    coauthors:         Optional[List[str]] = None


class ManuscriptUpdate(BaseModel):
    title:                   Optional[str] = None
    abstract:                Optional[str] = None
    keywords:                Optional[List[str]] = None
    manuscript_type:         Optional[str] = None
    project_id:              Optional[str] = None
    workspace_id:            Optional[str] = None
    target_journal_id:       Optional[str] = None
    status:                  Optional[str] = None
    sections:                Optional[dict] = None
    corresponding_author_id: Optional[str] = None
    doi:                     Optional[str] = None
    submission_notes:        Optional[str] = None
    acknowledgements:        Optional[str] = None
    funding_statement:       Optional[str] = None
    conflict_of_interest:    Optional[str] = None


# ============== GRANT APPLICATIONS ==============
class GrantApplicationCreate(BaseModel):
    grant_id:          str
    consortium_name:   Optional[str] = ""
    institution:       Optional[str] = None
    requested_budget:  Optional[float] = 0.0
    currency:          Optional[str]   = "EUR"


class GrantApplicationUpdate(BaseModel):
    consortium_name:   Optional[str] = None
    institution:       Optional[str] = None
    requested_budget:  Optional[float] = None
    currency:          Optional[str]   = None
    notes:             Optional[str]   = None
    submission_ref:    Optional[str]   = None
    outcome_notes:     Optional[str]   = None
    proposal_sections: Optional[dict]  = None
    status:            Optional[str]   = None


class BudgetItemCreate(BaseModel):
    category:     str
    description:  str
    amount:       float
    unit:         Optional[str]  = None
    quantity:     Optional[float] = None
    justification: Optional[str] = ""
    year:         Optional[int]  = None


class DeliverableCreate(BaseModel):
    title:        str
    type:         Optional[str] = "Deliverable"
    due_date:     Optional[str] = None
    work_package: Optional[str] = ""
    description:  Optional[str] = ""
    assignee_id:  Optional[str] = None
    link:         Optional[str] = ""


# ============== REPOSITORY ==============
class RepositoryItemCreate(BaseModel):
    title: str
    type: str  # Document | Dataset | Template | Literature
    description: Optional[str] = ""
    url: Optional[str] = ""
    tags: Optional[List[str]] = []
    project_id: Optional[str] = ""
    workspace_id: Optional[str] = ""
    visibility: Optional[str] = "private"


# ============== MEETINGS ==============
class MeetingCreate(BaseModel):
    title:              str
    description:        Optional[str] = ""
    meeting_type:        Optional[str] = "Research Meeting"
    start_at:           str  # ISO 8601
    end_at:             str  # ISO 8601
    timezone:           Optional[str] = "UTC"
    participant_ids:    Optional[List[str]] = None
    workspace_id:       Optional[str] = ""
    project_id:         Optional[str] = ""
    location:           Optional[str] = ""
    video_link:         Optional[str] = ""
    agenda:             Optional[List[str]] = None
    tags:               Optional[List[str]] = None
    attachment_links:   Optional[List[str]] = None
    is_recurring:       Optional[bool] = False
    recurrence_rule:    Optional[str] = "none"  # none | daily | weekly | biweekly | monthly
    reminder_minutes:   Optional[int] = 15
    ai_summary_enabled: Optional[bool] = True


class MeetingUpdate(BaseModel):
    title:              Optional[str] = None
    description:        Optional[str] = None
    meeting_type:        Optional[str] = None
    start_at:           Optional[str] = None
    end_at:             Optional[str] = None
    timezone:           Optional[str] = None
    participant_ids:    Optional[List[str]] = None
    workspace_id:       Optional[str] = None
    project_id:         Optional[str] = None
    location:           Optional[str] = None
    video_link:         Optional[str] = None
    agenda:             Optional[List[str]] = None
    tags:               Optional[List[str]] = None
    attachment_links:   Optional[List[str]] = None
    is_recurring:       Optional[bool] = None
    recurrence_rule:    Optional[str] = None
    reminder_minutes:   Optional[int] = None
    ai_summary_enabled: Optional[bool] = None
    status:             Optional[str] = None  # scheduled | completed | cancelled
    pinned:             Optional[bool] = None


class ActionItemCreate(BaseModel):
    title:       str
    owner_id:    Optional[str] = None
    priority:    Optional[str] = "medium"  # low | medium | high
    due_date:    Optional[str] = None
    project_id:  Optional[str] = ""


class ActionItemUpdate(BaseModel):
    title:      Optional[str] = None
    owner_id:   Optional[str] = None
    priority:   Optional[str] = None
    due_date:   Optional[str] = None
    status:     Optional[str] = None  # open | in_progress | done
    project_id: Optional[str] = None


class MeetingNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


# ══════════════════════════════════════════════════════════════════════════════
# WORKSPACE ITEMS — generic content model (Workspace redesign Phase 2)
#
# A single, reusable shape for workspace-owned content that isn't a
# project-scoped `Task` (which already has its own working model/endpoints
# used by the Kanban board — intentionally NOT migrated here to avoid
# rewriting a tested, working system). Used first for wiki pages; designed
# so milestones/documents/timeline items can adopt it later without another
# migration.
# ══════════════════════════════════════════════════════════════════════════════
WORKSPACE_ITEM_TYPES = ["wiki_page", "milestone", "document", "timeline_item", "note"]
WORKSPACE_ITEM_STATUSES = ["draft", "published", "archived"]


class WorkspaceItemCreate(BaseModel):
    item_type:    str                          # one of WORKSPACE_ITEM_TYPES
    project_id:   Optional[str] = None
    parent_id:    Optional[str] = None          # nesting (e.g. wiki page hierarchy)
    title:        str = Field(..., min_length=1, max_length=300)
    description:  Optional[str] = ""
    content:      Optional[dict] = None         # structured content (e.g. Tiptap JSON)
    status:       Optional[str] = "draft"
    priority:     Optional[str] = None          # low | medium | high
    start_date:   Optional[str] = None
    due_date:     Optional[str] = None
    progress_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    assignee_ids: Optional[List[str]] = None
    dependency_ids: Optional[List[str]] = None
    labels:       Optional[List[str]] = None
    position:     Optional[int] = None          # ordering within parent/column
    icon:         Optional[str] = None           # wiki page icon (emoji or key)
    cover_image:  Optional[str] = None

    @field_validator("item_type")
    @classmethod
    def _valid_item_type(cls, v):
        if v not in WORKSPACE_ITEM_TYPES:
            raise ValueError(f"item_type must be one of {WORKSPACE_ITEM_TYPES}")
        return v


class WorkspaceItemUpdate(BaseModel):
    parent_id:    Optional[str] = None
    title:        Optional[str] = None
    description:  Optional[str] = None
    content:      Optional[dict] = None
    status:       Optional[str] = None
    priority:     Optional[str] = None
    start_date:   Optional[str] = None
    due_date:     Optional[str] = None
    # completed_at is intentionally NOT client-settable — the server sets it
    # automatically on the draft->published transition (routers/workspace_items.py).
    # A client-writable version was a mass-assignment hole (forgeable completion
    # timestamps) closed in the Phase 10 security pass; no legitimate caller
    # ever sent this field.
    progress_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    assignee_ids: Optional[List[str]] = None
    dependency_ids: Optional[List[str]] = Field(default=None, max_length=200)
    labels:       Optional[List[str]] = None
    position:     Optional[int] = None
    icon:         Optional[str] = None
    cover_image:  Optional[str] = None
    expected_version: Optional[int] = None  # optimistic concurrency check


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC COMMENTS — polymorphic comment system (Workspace redesign Phase 3)
#
# One comments collection for any commentable entity (workspace items, tasks,
# manuscripts, ...) instead of a per-entity comments table. The pre-existing
# `manuscript_comments` collection is left untouched (nothing reads/writes it
# differently) — manuscripts get a thin adapter routing new comments through
# this generic system going forward without breaking old data or endpoints.
# ══════════════════════════════════════════════════════════════════════════════
COMMENT_TARGET_TYPES = ["workspace_item", "task", "manuscript", "workspace"]


class GenericCommentCreate(BaseModel):
    target_type: str
    target_id:   str
    content:     str = Field(..., min_length=1, max_length=8000)
    parent_comment_id: Optional[str] = None
    # Capped: mentions drive notification sends (routers/comments.py
    # _notify_mentions) — an unbounded list would let a single comment spam
    # notifications to an arbitrary number of user ids.
    mentions:    Optional[List[str]] = Field(default=None, max_length=50)

    @field_validator("target_type")
    @classmethod
    def _valid_target_type(cls, v):
        if v not in COMMENT_TARGET_TYPES:
            raise ValueError(f"target_type must be one of {COMMENT_TARGET_TYPES}")
        return v


class GenericCommentUpdate(BaseModel):
    content:  Optional[str] = None
    resolved: Optional[bool] = None
