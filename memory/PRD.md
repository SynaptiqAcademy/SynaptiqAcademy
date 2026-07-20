# SYNAPTIQ — Product Requirements Document

## Problem Statement
SYNAPTIQ is an academic collaboration platform that helps researchers discover collaborators, build research teams, manage projects, and publish together. It combines LinkedIn-style networking, GitHub-style collaboration, and a Research Operating System into a single platform.

Core principle: researchers join SYNAPTIQ to find the right people and transform ideas into publications — not to write documents.

## Architecture
- **Backend**: FastAPI + MongoDB (Motor). Routers: `/api/auth`, `/api/users`, `/api/collaborations`, `/api/projects`, `/api/messages`, `/api/notifications`, `/api/discover`, `/api/ai`, `/api/analytics`. JWT auth via httpOnly cookies (PyJWT, bcrypt).
- **Frontend**: React 19 + React Router 7. Tailwind + shadcn/ui (deeply customized). Cormorant Garamond serif headings, IBM Plex Sans body. Editorial academic theme (Oxford Blue accent on off-white).
- **AI**: emergentintegrations → Claude Sonnet 4.5 for collaborator recommendations and research assistant.

## User Personas
- **PI / Senior Researcher** — posts collaborations, reviews applicants, runs projects.
- **Postdoc / PhD** — discovers and applies to collaborations, builds reputation.
- **Lecturer / Methods Specialist** — searchable expertise (PLS-SEM, qualitative, statistics).
- **Cross-disciplinary collaborator** — looking for co-authors across disciplines.

## Core Requirements (Static)
1. Email/password auth with academic identity onboarding.
2. Researcher profiles with ORCID, institution, research areas, skills, reputation scores.
3. Open collaborations marketplace (CRUD + apply + accept/reject).
4. Network search (researchers).
5. Project workspace (research foundation, design, literature, tasks, milestones, team).
6. Direct messaging between researchers.
7. Personalized Discover feed + AI collaborator recommendations.
8. Notifications.
9. Analytics dashboard.
10. Editorial / academic visual identity.

## What's Been Implemented (2026-02)
### Phase I
- ✅ JWT auth (httpOnly cookies), register, login, logout, /me, brute-force-resistant
- ✅ Academic identity onboarding wizard (institution, role, areas, skills, availability)
- ✅ Researcher profiles (view + edit; reputation scores; ORCID/Scholar/website links)
- ✅ Network search (by name, area, availability)
- ✅ Collaboration marketplace (create, list, filter, detail, apply, decide applications)
- ✅ Auto-created project per collaboration
- ✅ Project workspace with tabs: Research Foundation, Design, Literature, Tasks/Milestones, Team
- ✅ Tasks (create, toggle status, assign), Milestones, Literature notes
- ✅ Direct messages with conversation list + thread view
- ✅ Notifications (application, decision, new message)
- ✅ Discover feed (open collabs, recommended researchers, grants, conferences, trending topics)
- ✅ AI collaborator recommendations (Claude Sonnet 4.5) with reasoning, plus heuristic fallback
- ✅ Analytics dashboard (research, collaboration, impact, reputation scores)
- ✅ Settings (account info, logout)
- ✅ Editorial design: Cormorant Garamond + IBM Plex Sans + Oxford Blue, sharp edges, no shadows
- ✅ Seed data: 6 demo researchers, 6 demo collaborations, 5 grants, 5 conferences

### Phase II (2026-02-13)
- ✅ Sidebar dropdown groups — Discover (Journals, Conferences, Funding, Grants, Publication Hub, Repository) and Projects (Projects, Workspaces, Manuscripts)
- ✅ Journals, Conferences, Funding, Grants (with tabs Recommended/Saved/Tracking/Discover), Workspaces, Manuscripts (9 IMRaD sections, status workflow), Publication Hub (6-stage Kanban), Repository — all with backend routers + seeded data

### Phase IV — Messaging System (2026-02-13)
- ✅ **Conversation model**: 5 types (direct, collaboration, project, workspace, manuscript). `conversations` collection with `context_key` uniqueness; `conversation_members` per-user with `last_read_at` for unread counters.
- ✅ **Real-time**: WebSocket at `/api/ws/conversations/{id}` (auth via httpOnly cookie). In-process `ConnectionManager` broadcasts message/typing/read/presence events. Frontend opens WS per active conversation; falls back to polling on disconnect.
- ✅ **Direct messaging**: 1:1 deterministic `direct:{a}:{b}` key (sorted user IDs) prevents duplicate conversations. Read receipts (✓ / ✓✓) for direct chats.
- ✅ **Context conversations**: auto-membership sync from collaboration/project/workspace/manuscript. "Open chat" buttons in each context detail page.
- ✅ **Attachments**: `/api/uploads` POST (multipart), allowed MIMEs (PDF/DOCX/XLSX/PPTX/PNG/JPG/WebP/GIF), 25 MB cap. Storage via Emergent object storage (`services/storage_service.py`). Authorized download via `/api/uploads/{id}` (membership check); image-friendly `/api/uploads/{id}/blob?token=` for `<img src>`.
- ✅ **Academic sharing**: shared_resources array on each message (journal/conference/grant/publication/project/manuscript). Share picker modal searches existing entities and inserts a chip into the composer.
- ✅ **Mentions**: `@handle` parsed at send-time against conversation members; mentioned users get `type=mention` notifications instead of plain `message`.
- ✅ **Unread counters**: per-conversation badge + `/api/conversations/unread/count` global tally.
- ✅ **Conversation search & filters**: by type pills (All/Direct/Collab/Project/Workspace/Manuscript) and free-text search.
- ✅ **Typing indicators**: client emits via WS, server fanned out to other members; 4 s auto-decay client-side.
- ✅ **Security (row-level)**: every endpoint asserts conversation membership via `_assert_member()`. Attachment download checks ownership OR membership of any conversation referencing it. WS rejects with code 4403 if not a member.
- ✅ **Notifications**: every new message creates notifications for other members; mentions yield distinct title/type. Notifications page already in place.
- ✅ Legacy `messages` collection auto-dropped on startup.

### Phase IV — Database
- `conversations`: type, context_id, context_key (unique), title, created_by, created_at, last_message_at, last_message_preview
- `conversation_members`: conversation_id, user_id, role, joined_at, last_read_at, muted
- `messages`: conversation_id, sender_id, content, attachment_ids[], shared_resources[], mentions[], deleted, edited_at, created_at
- `message_attachments`: owner_id, storage_path, original_filename, content_type, size, kind, is_deleted, created_at
- `message_reads`: conversation_id, user_id, last_read_at (per-message receipts derived from last_read_at vs created_at)

### Phase IV — Remaining improvements
1. Reply / quote previous message
2. Edit + delete (soft) with edited_at audit
3. Message-level reactions (emoji)
4. Cursor pagination for very long threads (current is limit+before timestamp)
5. Per-user mute & notification preferences per conversation
6. Push notifications (when web app is closed)
7. Voice notes (audio attachments)
8. Markdown / LaTeX rendering in message body
9. Multi-region scale: replace in-process `ConnectionManager` with Redis pub/sub when sharding across nodes

### Phase III — SaaS Foundation (2026-02-13)
- ✅ **Auth complete**: register, login, logout, /me, **forgot-password** (signed JWT reset token, 30 min TTL, debug field for dev), **reset-password** (single-use), **change-password** (verifies current)
- ✅ **Onboarding enforcement**: 5-step wizard (Personal → Academic → Research → Profiles → Experience) with required-field validation; `ProtectedRoute` redirects unfinished users to `/onboarding`; new fields: first_name, last_name, country, research_interests, research_keywords, linkedin, publications_count, conferences_count
- ✅ **Marketing site** (9 pages): Landing (with FAQ), Platform, Pricing, Contact, Terms, Privacy, GDPR, Cookies, Security — shared `MarketingLayout` with consistent header/footer, internal cross-links
- ✅ **Pricing page**: 3 plans (Free €0 / Researcher €19 monthly · €15 annual / Institution €199 monthly · €159 annual) with monthly/annual toggle, feature list, credit allowance per plan, "Most popular" Researcher card
- ✅ **FAQ section** on landing: 8 questions (what / who / vs ResearchGate / vs Mendeley / collaboration / data protection / ORCID / institutions)
- ✅ **Research Credits system**:
  - `credits_balance`, `credits_monthly_allowance`, `credits_reset_at` per user
  - 8 AI actions with costs (5-25 each); `services/credits_service.py` handles atomic consume + refund on failure + monthly rollover
  - Sidebar widget shows balance/allowance with progress bar
  - GET `/api/credits/balance`, `/api/credits/usage`
- ✅ **Plans & Subscriptions backend**:
  - `plans_catalogue.py` (single source of truth), `plans` collection upserted on startup
  - `subscriptions` collection ready (status, current_period_end, stripe_subscription_id, stripe_customer_id)
  - GET `/api/billing/plans`, `/api/billing/subscription`, POST `/api/billing/checkout-session`, POST `/api/billing/portal-session`, POST `/api/billing/webhook`
- ✅ **Stripe-ready architecture** (no mocks): `services/stripe_service.py` lazily imports SDK; gracefully returns 503 with structured detail when not configured. Env vars set: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_RESEARCHER_MONTHLY|ANNUAL`, `STRIPE_PRICE_INSTITUTION_MONTHLY|ANNUAL`. `billing_events` collection captures inbound webhooks.
- ✅ **Settings page** rebuilt: account info, subscription card (plan + credits + reset date + link to /pricing), change-password form
- ✅ **Database additions**: `plans`, `subscriptions`, `credit_usage`, `billing_events`, `password_resets`; users extended with `first_name`, `last_name`, `country`, `research_interests`, `research_keywords`, `linkedin`, `publications_count`, `conferences_count`, `plan_code`, `credits_balance`, `credits_monthly_allowance`, `credits_reset_at`

### Stripe Readiness Report
| Component | State |
|---|---|
| Stripe SDK installed | ✅ `stripe` in requirements.txt |
| Env var scaffolding | ✅ 6 keys reserved (blank) in backend/.env |
| Plan → Stripe Price ID mapping | ⚠ `stripe_price_id_monthly` / `_annual` empty — fill from Stripe dashboard |
| Checkout session endpoint | ✅ Returns 503 with clear message when not configured; production-ready signature otherwise |
| Billing portal endpoint | ✅ Stubbed; activates when SDK + customer ID present |
| Webhook receiver | ✅ Persists events to `billing_events`; signature verification turns on automatically when `STRIPE_WEBHOOK_SECRET` set |
| Subscription DB shape | ✅ Matches Stripe object (status, current_period_end, customer_id, subscription_id, cancel_at_period_end) |

### Remaining tasks before production launch
1. **Stripe live config**: create products + prices in Stripe dashboard, paste the 6 price IDs into env, set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`.
2. **Transactional email**: integrate Resend/SendGrid for password-reset emails (currently surfaces `debug_reset_token` in non-prod). Wire `POST /api/contact` for the contact form.
3. **Webhook signature verification path**: switch handler to use raw bytes + Stripe-Signature header (one-line change in billing.py).
4. **Plan enforcement** at write-time: cap workspaces/projects per plan limits (currently informational only).
5. **Cookie banner** for cookies policy.
6. **Audit logging** for sensitive admin actions.
7. **DPA template** PDF served from /security or via sales handoff.
8. **Production domain** with HTTPS + secure cookies (`secure=True` on cookie set).
9. **Email confirmation** on registration (verify email link).
10. **Live ORCID OAuth** to enable publication sync.
- ✅ Sidebar dropdown groups — Discover (Journals, Conferences, Funding, Grants, Publication Hub, Repository) and Projects (Projects, Workspaces, Manuscripts)
- ✅ Journals (`/journals`, `/journals/:id`): search by subject/quartile/OA, impact metrics, submission requirements; 12 seeded journals (Nature, Science, Cell, Lancet, JAMA, …)
- ✅ Conferences (`/conferences`, `/conferences/:id`): topics, organizer, important dates, submission URLs; 10 seeded conferences
- ✅ Funding (`/funding`, `/funding/:id`): 12 seeded opportunities with eligibility, funding_type, duration; save/unsave
- ✅ Grants (`/grants`): tabs Recommended / Saved / Tracking / Discover (personal view over funding opportunities, ranked by user research areas)
- ✅ Workspaces (`/workspaces`, `/workspaces/:id`): create, members, activity feed (post notes), documents tab; 3 seeded workspaces
- ✅ Manuscripts (`/manuscripts`, `/manuscripts/:id`): create with project + journal targeting, 9 IMRaD sections, status workflow, multi-author support; 3 seeded manuscripts
- ✅ Publication Hub (`/publication-hub`): 6-stage Kanban pipeline (Drafting → Under Review → Revising → Accepted → Published → Rejected) with summary stats
- ✅ Repository (`/repository`): documents/datasets/templates/literature, filter by type, search, add new items; 8 seeded items

### Database additions (Phase II)
- `journals` (12 docs)
- `workspaces` (3 docs)
- `workspace_activity` (3 docs)
- `manuscripts` (3 docs)
- `repository_items` (8 docs)
- `users.saved_funding_ids` array field (new)
- `grants` collection extended with `description, eligibility, funding_type, duration` fields
- `conferences` collection extended with `topics, organizer, important_dates, submission_url, description` fields

### Phase V — Research Operating System (2026-02-14)
- ✅ **Research OS router** (`/api` prefix, services-style): registered alongside `workspaces.py` and `manuscripts.py`.
- ✅ **Workspace roles & invitations**: 6 roles (Owner / Principal Investigator / Co-Investigator / Researcher / Reviewer / Observer). `WS_WRITE_ROLES = {Owner, PI, Co-I, Researcher}` gates writes. Endpoints: `POST /api/workspaces/{id}/invitations`, `GET /api/workspaces/invitations/mine`, `POST /api/workspaces/invitations/{inv_id}/respond` (accept|decline), `PATCH /api/workspaces/{id}/members/{uid}/role`, `DELETE /api/workspaces/{id}/members/{uid}`. Owner role is immutable; PI/Owner only can manage roles.
- ✅ **Workspace dashboard** `GET /api/workspaces/{id}/dashboard`: returns workspace, your_role, counts (members/active_projects/active_manuscripts/tasks_total+completed/milestones_total+completed), `research_health` (weighted 0-100 score), projects, manuscripts, upcoming_milestones (top 5), recent_activity (last 20).
- ✅ **Workspace meta**: `PATCH /api/workspaces/{id}/meta` (research_domain, status active|archived, description).
- ✅ **Manuscript versions**: `POST /api/manuscripts/{id}/versions` (snapshot title+sections+keywords+authors+target_journal), `GET .../versions` (descending list w/o payload), `GET .../versions/{v}` (full snapshot), `POST .../versions/{v}/restore` (auto-snapshots current FIRST, then writes restored marker; current_version advances by +2).
- ✅ **Manuscript comments**: `POST/GET /api/manuscripts/{id}/comments` (per-section, anchored), `POST /api/manuscripts/comments/{cid}/resolve`. Notifications dispatched to other authors on new comments.
- ✅ **Manuscript contributions**: `POST /api/manuscripts/{id}/contributions` upserts per-user per-section aggregate (chars_changed, edits, first_edit, last_edit). Fired automatically by frontend on every Save.
- ✅ **Authorship**: `PATCH /api/manuscripts/{id}/authors` reorders authors + sets corresponding_author_id (must be in order array). `PATCH /api/manuscripts/{id}/meta` for keywords/workspace_id/project_id/target_journal_id.
- ✅ **Manuscript dashboard** `GET /api/manuscripts/{id}/dashboard`: progress_pct (filled sections / total), ready_for_submission (≥80% + target journal + abstract), versions_count, comments_open/total, review_requests_pending, contributions array, pipeline_hooks (journal/conference/grant finder placeholders for Phase 2 wiring).
- ✅ **Static lookups**: `/api/research-os/workspace-roles | task-statuses | manuscript-statuses`.
- ✅ **Startup migration**: back-fills `member_roles` for existing workspaces (owner→"Owner", other members→"Researcher"). Creates indexes for workspace_invitations, manuscript_versions, manuscript_comments, manuscript_contributions (unique per user+section), review_requests.
- ✅ **`workspaces.py` create_workspace** auto-assigns the creator as Owner in member_roles (so new workspaces no longer need the migration).

### Phase V — Frontend (Workspaces & Manuscripts)
- ✅ **Workspaces.jsx**: Pending invitations inbox banner at top (Accept/Decline), workspace cards with status pill + member/project counts.
- ✅ **WorkspaceDetail.jsx** — Overview: SVG Research Health gauge, 4 KPI cards (Members / Active Projects / Active Manuscripts / Milestones+tasks summary), Linked Manuscripts list (status + version), Upcoming Milestones rail, Recent Activity rail. Header role badge + "Open chat" + "Invite member" (admins only).
- ✅ **WorkspaceDetail.jsx** — Team: members with roles; Owner/PI can change roles via select per non-owner, remove via trash icon; non-admins see role pills only.
- ✅ **Invite modal**: searches `/api/users`, role select, click-to-invite. Toast "Invitation sent". Existing members filtered out of results.
- ✅ **ManuscriptDetail.jsx** — sections sidebar with per-section progress checkmarks (filled vs empty), Status (8 stages), Target journal selector, Submission Readiness card (6 checklist items, color-coded), center editor with char/word counter, right rail with 3 tabs: Comments (per-section thread + resolve), History (version timeline + restore), Authors (reorder ↑/↓ + corresponding author star). Snapshot button at top creates a new version.
- ✅ **Auto contribution logging**: Save handler PATCHes manuscript + fires `/contributions` with `char_delta`. Contributions widget on right rail shows aggregated edits per user per section.
- ✅ **Testing**: backend `backend_research_os_test.py` — 22 pytest tests, 100% pass. Frontend critical flows verified by testing agent (iteration_6).


### P0 — completed in Phase V (2026-02-14)
- ✅ Research OS backend (workspace roles + dashboards + manuscript versions/comments/contributions/authors)
- ✅ Premium Workspaces & Manuscripts frontend (role-aware, version history, collaborative writing rail)

### Phase VI — Kanban, Review Workflow, Email Infrastructure (2026-02-14)
**P1 — Workspace Task Kanban**
- ✅ Backend: `GET /api/workspaces/{ws_id}/tasks` aggregates tasks across all linked projects with project + assignee enrichment; normalises legacy `todo` → `backlog`; 403 for non-members.
- ✅ Frontend: HTML5 native drag-and-drop kanban (`/components/researchOS/WorkspaceKanban.jsx`) with 5 columns (Backlog / Planned / In progress / Review / Completed), color-coded headers, per-column quick-add composer, project picker dropdown.

**P2 — Manuscript Review Workflow**
- ✅ Backend: 6 new endpoints — `GET /api/manuscripts/{mid}/review-requests`, `GET /api/review-requests/mine`, `POST /api/review-requests/{rid}/respond`, `POST /api/review-requests/{rid}/verdict`, `GET /api/manuscripts/{mid}/review-history`, `GET /api/research-os/review-verdicts`. State machine: `pending → accepted → completed (verdict)` | `pending → declined`. Verdict cascades to manuscript status.
- ✅ Frontend: `/reviews` reviewer dashboard (4 tabs, accept/decline, verdict form). ManuscriptDetail right rail gains "Reviews" tab with reviewer assignment + live list.

**P3 — Resend Transactional Email Infrastructure (DRY-RUN)**
- ✅ Provider abstraction in `services/email_service.py` — `ResendProvider`, retry-aware `send_email()` (3 attempts, 0.5/1/2s backoff), 4 typed helpers, automatic dry-run when env vars missing. Persists live sends to `email_log` collection.
- ✅ 4 typed templates with branded HTML shell (`services/email_templates.py`).
- ✅ Diagnostic endpoints `/api/email/config | /preview/{t} | /test` (`routers/email.py`).
- ✅ 4 trigger sites wired (password reset, workspace invitation, review request, collaboration invitation). EXACTLY-ONCE delivery (EVENT_KIND_TO_EMAIL=∅ — typed helpers canonical).
- ✅ Env vars: `RESEND_API_KEY`, `EMAIL_FROM`, `APP_BASE_URL`, `EMAIL_DRY_RUN=1` (all blank by default). `resend==2.30.1` in requirements.txt.

**Testing:** Backend 20/20 pytest PASS, frontend critical flows 100% (iteration_7).

## Prioritized Backlog
### Phase 6 — AI Intelligence Layer (2026-02-14) ✅
**Module 1 — Deadline Intelligence**
- ✅ `GET /api/deadlines/mine` aggregates: manuscript submission deadlines (journal + conference), revision_due (21d after last revision note), camera_ready (from conference data), grant deadlines (saved grants), workspace milestones. Sorted by urgency (`missed → critical → due_soon → upcoming`), with bucket counts.
- ✅ Workspace dashboard now embeds `upcoming_deadlines` array alongside `upcoming_milestones`.
- ✅ Frontend `DeadlinesWidget` on `/discover` sidebar + `/workspaces/{id}` overview right rail (urgency-coded border colours + deep-links).

**Module 2 — Reviewer Matching** (10 credits)
- ✅ `POST /api/matching/reviewer {manuscript_id, top_n}` — pulls onboarded SYNAPTIQ users (excluding authors), excludes prior-collab where possible, sends compact JSON to Claude Sonnet 4.5 with strict response schema. Returns score 0-100 + rationale + concerns + expertise_areas + collaboration_risk (low|high).
- ✅ Frontend card shows score ring, expertise chips, h-index + pub count, "Request review" → POST `/manuscripts/{id}/review-requests`.

**Module 3 — Journal Matching** (10 credits)
- ✅ `POST /api/matching/journal {manuscript_id, top_n}` — text-search prefilter on `subjects+title+publisher`, fallback to popularity. LLM ranks with quartile/OA/APC awareness. Returns enriched journal cards.
- ✅ Frontend card: Q-quartile + OA + APC badges, "Add to Pub Hub" calls `/publication-hub/submissions`.

**Module 4 — Conference Matching** (5 credits)
- ✅ `POST /api/matching/conference` — filters out closed CFPs, ranks by topical+rank fit. Returns acronym + rank + deadline + format.
- ✅ Frontend "Add to Pub Hub" creates a conference submission.

**Module 5 — Grant Matching** (10 credits)
- ✅ `POST /api/matching/grant {manuscript_id|project_id|query}` — uses user profile (research_areas + country + career_stage) + context, penalises geo/career mismatch. Returns eligibility_match (high|medium|low) per recommendation.
- ✅ Frontend "Save" calls `/grants/{id}/save`.

**Architecture**
- ✅ Provider abstraction: `services/ai/matching.py` with `_call_llm_json()` — provider+model controlled by env (`AI_MATCHING_PROVIDER`, `AI_MATCHING_MODEL`). Default anthropic/claude-sonnet-4-6.
- ✅ Audit: every call persisted to `ai_requests` collection (user_id, kind, input_summary, output_excerpt, credits_consumed, latency_ms, provider, model, created_at).
- ✅ Credit charging via `consume_credits` wrapper with refund on any exception after charge.
- ✅ Analytics: `GET /api/matching/analytics` returns by-kind counts + top journals/conferences/grants + recent activity. Admin sees global scope; users see own.
- ✅ Indexes on `ai_requests` (user+created, kind+created).

**Credit costs** (`plans_catalogue.CREDIT_COSTS`):
- ai_journal_matching: 10
- ai_conference_matching: 5
- ai_grant_matching: 10
- ai_reviewer_matching: 10

**Testing**: Backend 11/11 pytest PASS (4 live Claude Sonnet 4.5 calls verified end-to-end). Frontend 100% — AI toolbar, modal, DeadlinesWidget, credits decrement all visually confirmed.


### Phase 5 — Discovery Suite (2026-02-14) ✅
- **Provider architecture** (services/discovery/{base,http,ingest,scheduler,registry,providers/*}) — `JournalProvider | ConferenceProvider | GrantProvider` abstract bases, normalizer helpers (slug, entity_key, ISSN normalization, ISO date parsing), shared httpx pool with polite User-Agent + exponential backoff.
- **7 real providers** implemented: OpenAlex (journals, primary), DOAJ (OA back-fill), Crossref (ISSN back-fill), WikiCFP (conferences via RSS), OpenAIRE (EU grants), NIH RePORTER (US biomedical grants), UKRI Gateway to Research (UK grants).
- **Ingestion orchestrator** (`services/discovery/ingest.py`) — cursor-paginated `run_provider`/`run_kind` with `entity_key` dedup (Mongo bulk_write upsert), per-(kind,source) state persistence, wall-seconds bound, audit log (`ingest_runs` collection).
- **APScheduler in-process** (`services/discovery/scheduler.py`) — daily journals 02:00 UTC, conferences /6h, grants daily 04:00 UTC. Opt-in via `DISCOVERY_SCHEDULER_ENABLED=1` (default off).
- **Mongo indexes**: text indexes on title/publisher/subjects/keywords; unique sparse `entity_key`; compound indexes for hot filter paths.
- **Admin endpoints** (`/api/discovery/{sources,stats,sync/{kind},indexes/ensure,runs}`).
- **Public APIs**: faceted `/api/journals`, `/api/conferences`, `/api/grants` (each with `/facets` + `/{id}`).
- **Live initial sync** completed: **9,287 journals + 818 conferences + 8,009 grants = ~18k normalized records**. Real metadata (Q1-Q4 + OA + h-index + popularity_score for journals; location + conference dates for conferences; sponsor + amount + deadline for grants).
- **Publication Hub** (`/api/publication-hub/{pipeline,submissions,...}`): full lifecycle tracker (selected → ready → submitted → under_review → revision_requested → accepted → published / rejected / withdrawn), reviewer feedback append, revision notes append, history audit per submission.
- **Frontend**: `DiscoveryShell` reusable component, 3 list pages (Journals/Conferences/Grants), 3 detail pages with provenance badges + impact metrics + key dates, Publication Hub kanban with VenuePicker modal.
- **Backend tests: 27/27 pytest PASS** (`/app/backend/tests/backend_phase5_discovery_test.py`).
- **Frontend tests**: all critical flows verified by testing agent (iteration_8). Two cosmetic issues fixed post-test (modal aria, action label wrap).

### Architecture document: `/app/memory/PHASE5_DATA_SOURCES.md`
Includes: data source analysis (with licenses + rate limits), legal constraints, full schema, ingestion flow diagram, search architecture, scale roadmap (Mongo text → Atlas Search → Elasticsearch), AI-readiness mapping.

### Deferred (P6+)
- AI matching layer (Journal/Conference/Grant/Reviewer — feeds off these normalized records)
- Cover letter generator
- APC payment tracking + Stripe integration
- Multi-provider initial back-fills (Crossref/DOAJ/CORE Rankings)
- Out-of-process worker (Celery/RQ) for sync at >500k records
- Atlas Search migration for relevance + autocomplete

### Phase 7 — AI Intelligence Frontend Productization (2026-02-14) ✅
The Phase 6 backend (Matching, Deadlines, Conversational Assistant, AI Usage, Saved Searches + Digests) is now fully exposed via a premium frontend.

- ✅ **Conversational Research Assistant** drawer (`/app/frontend/src/components/ai/AssistantPanel.jsx`) — context-aware Copilot embedded on Workspace, Project, and Manuscript pages via `AssistantLauncher`. Features:
  - Right-side drawer with serif assistant bubbles, mono metadata, live credit counter, history/session switcher, optimistic UI.
  - Context-specific quick-action chips: Workspace (Summarize Literature / Identify Gaps / Suggest Methodology / Generate Research Questions), Project (same 4), Manuscript (8 incl. Improve Abstract / Explain Journal Match / Explain Conference Match / Explain Grant Match / Draft Reviewer Response).
  - 2 credits per send; out-of-credits guard rail; latency + cost shown on each reply.
  - Auto-hides Made-with-Emergent badge while open (z-[100]) and restores on close.
- ✅ **AI Usage Dashboard** (`/app/frontend/src/pages/AIUsage.jsx`, route `/ai-usage`) — premium analytics:
  - 4 KPI cards (Credits remaining, Credits used, Assistant sessions, Estimated cost).
  - 30-day credit consumption sparkline.
  - "Most used AI features" horizontal bar list (by kind: journal/conference/grant/reviewer/assistant).
  - "Matching breakdown" cards.
  - "Most popular journals / conferences / grants" lists (titles resolved server-side, not raw IDs).
  - Recent AI activity feed.
  - Admin scope auto-detected: shows global view chip + `admin-top-users` block (top credit consumers).
- ✅ **Saved Searches + Email Digests** (`/app/frontend/src/components/discovery/SavedSearchControls.jsx`) — embedded in `DiscoveryShell` via a `topBarSlot` render prop on Journals, Conferences, Grants pages:
  - Save current query + filters with daily/weekly/off digest cadence.
  - Manage drawer with edit / delete / live preview (≤10 current matches).
  - Kind-isolated lists (journal vs conference vs grant drawers).
- ✅ Backend hardening:
  - `/api/matching/analytics` & `/api/ai/usage` aggregations now $set-normalize legacy `credits_consumed` dict shape → int (4 historical records migrated to int).
  - `/api/matching/analytics` resolves journal/conference/grant titles via $lookup-style resolution; admin scope returns `top_users` + `assistant_sessions`.
  - Fixed ObjectId leak in `/api/assistant/sessions/{sid}/messages` GET (pop `_id` before spread).
- ✅ Sidebar nav: new "AI Usage" entry (`[data-testid='nav-ai-usage']`).
- **Testing**: iteration_11 — frontend 100% PASS (KPIs, sparkline, popular venues, assistant Send+reply+credit decrement, history, drawer overlay fix, saved-search create/preview/edit/delete on all 3 kinds, kind isolation, sidebar nav, admin scope).

### Phase 8 — Marketplace v2 + Reputation System (2026-02-14) ✅
Strategic phase per user direction. People-first + opportunity-first two-surface model, hybrid (deterministic + LLM) matching, real reputation across 5 sub-scores.

**Backend**
- `services/marketplace/matching.py` — `deterministic_rank` (TF-IDF-lite + Jaccard over areas/keywords/skills, role-keyword bonus, co-author/workspace history bonus, weighted overall) returns top-50 candidates with sub-scores; `llm_rerank` calls Claude Sonnet via `emergentintegrations` to re-rank top-25 → return top-N with score+explanation+shared interests+concerns. Costs `ai_marketplace_rerank=5` credits; refunds on failure.
- `services/reputation/scorer.py` — 5 sub-scores from real activity:
  - **Collaboration**: accepted collaborations + completion rate + workspaces
  - **Publication**: platform manuscripts + OpenAlex works + log-scaled citations + h-index
  - **Reviewer**: completed peer reviews + turnaround days + quality ratings
  - **Funding**: awarded grants + log-scaled USD totals
  - **Activity**: 90-day chat/task/manuscript edit counts
  - Overall = weighted avg; cached 24h in `reputation_scores`.
- `services/reputation/openalex.py` — polite httpx fetch by ORCID (preferred) or name+institution.
- Routers: `marketplace.py` (search/rerank/reverse/invite/invitations/analytics/roles), `expertise.py` (CRUD + apply + decide + close + matching), `reputation.py` (/me, /{id}, /sync-openalex, /batch).
- New collections + indexes: `expertise_requests`, `marketplace_invitations`, `reputation_scores`.
- New credit cost: `ai_marketplace_rerank: 5`.
- Pytest: `/app/backend/tests/test_marketplace_phase.py` (4/4) — extended by testing agent to 10/10.

**Frontend**
- `/pages/Marketplace.jsx` — 9 role chips (any + 8 expert kinds), debounced search, filter row (availability/country/institution), AI rerank button (5 credits gated), 3-widget sidebar (reverse matches, network impact analytics, your reputation + OpenAlex sync).
- `/pages/ExpertiseRequests.jsx` — 3 tabs (Open / Matching me / My requests), kind filter + free-text search, create-modal posting requests with link to workspace/project/manuscript.
- `/pages/ExpertiseRequestDetail.jsx` — description + sidebar (skills/areas/engagement), apply form (≥10 char), owner applicant review (accept/reject sets status='filled'), close/delete.
- `/pages/Invitations.jsx` — received/sent tabs, accept/decline.
- `/components/marketplace/MatchCard.jsx` — researcher card with reputation badge, availability chip, prior-collab counter, shared signals chips, invite/message/profile actions, AI explanation block.
- `/components/marketplace/InviteModal.jsx` — invite by kind (collab/workspace/project/manuscript/expertise_request) with role + message.
- `/components/marketplace/ReputationBadge.jsx` — score + tier + popover with 5-bar breakdown (Elite/Established/Emerging/Active/New tiers).
- Profile page now displays reputation badge + "Invite to collaborate" CTA.
- Sidebar nav: Marketplace + Expertise links.

**Testing**: iteration_12 — backend 10/10 pytest PASS, frontend 100% PASS. AI rerank verified end-to-end (92→87 credits, 22s latency, amber-styled reranked cards with explanations). Cross-account flows verified (elena↔admin). Responsive at 1366×768 and 390×844.

### Phase 9 — Institutional Layer (2026-02-14) ✅
Transforms SYNAPTIQ from individual research tool into research operating system for universities/institutes/agencies. Flexible hierarchy, self-claim+verification, multi-seat sponsorship, real aggregated analytics over the entire platform.

**Backend**
- `services/institutions/analytics.py` — 7 real aggregations: overview, publications (by year + unit), collaboration (internal vs external + edge network), funding (status + per-unit USD), reputation (top researchers + top units + average), marketplace activity (open/filled/invites/success rate), `research_health` composite score blending pubs/grants/funding/reputation.
- `routers/institutions.py` — full CRUD on institutions + units (flexible nested via `parent_id`), self-claim with email-domain auto-verify, admin approval flow, role assignment (`owner|admin|unit_admin|research_lead|researcher`), seat management with capacity enforcement (`personal|sponsored|institution_owned`), audit logs.
- 7 analytics endpoints: `/api/institutions/{id}/analytics{,/publications,/collaboration,/funding,/reputation,/marketplace,/health}`.
- New collections + indexes: `institutions`, `units`, `institution_memberships` (unique on institution+user), `institution_audit`.
- One-shot migration `scripts/migrate_users_to_institutions.py` — fuzzy-matched 10 demo users into 2 institutions (ETH Zurich, SYNAPTIQ HQ), kept legacy `user.institution` string + added `user.institution_id` + migration_confidence score.
- Pytest: `tests/test_institutions_phase.py` 4/4 + smoke 6/6 (agent-extended) = **10/10 PASS**.

**Frontend**
- `/institutions` — directory with search, type filter, country filter, "Register institution" modal (sets `email_domains` for self-claim).
- `/institutions/:id` — 7-tab profile: Overview (6 KPIs + Research Health Score with 4 component bars) · Researchers (status filter, member rows) · Units (root-level unit cards + create-unit modal) · Publications (year bars + by-unit) · Funding (USD totals + by-status + by-unit) · Reputation (top researchers + top units) · **Govern** (admin-only): seat capacity management with cap enforcement, marketplace activity snapshot, collaboration internal/external + network edges, full member governance (approve/deny/role/seat/revoke), audit log feed.
- `/units/:id` (also `/research-centers/:id`, `/labs/:id`) — unit page with breadcrumb to institution + parent chain, 4 KPIs, member roster, sub-units cards, admin "Manage members" modal that toggles inclusion across all approved institution members.
- Self-claim CTA in institution header: button → email-domain auto-approve OR pending badge.
- Sidebar nav: "Institutions" link [data-testid='nav-institutions'].

**Testing**: iteration_13 — **Backend 10/10 PASS · Frontend 100% PASS**. Verified: directory, search, type filter, create + claim flow (auto-approve via email_domains + pending without), all 7 analytics endpoints, governance CRUD with audit, seat cap enforcement, unit nesting with breadcrumb, unit member management modal, admin-only Govern tab gating, responsive at 1366×768.

**Polish applied post-testing-agent**: backfilled `owner_id`/`admin_ids`/`seats` on migrated institutions; added `min/step` constraints to seats input.

### Phase 10 — ORCID Integration (2026-02-14) ✅
ORCID as SYNAPTIQ's academic-identity backbone. Built in **sandbox dry-run mode** — fully functional architecture, gracefully degrades when credentials absent. To go live: set `ORCID_CLIENT_ID` + `ORCID_CLIENT_SECRET` in backend/.env, no code changes needed.

**Backend**
- `services/orcid/oauth.py` — sandbox-default URLs, HMAC-signed state token, authorize URL builder, token exchange + normalization, record/work fetchers. `is_configured()` gate triggers 503 with helpful detail when keys absent.
- `services/orcid/sync.py` — `sync_user()` pulls profile (name, biography, country, keywords, research URLs, employments, educations, fundings) + works (papers/preprints/books/etc), upserts into new `publications` collection keyed by DOI/put_code/title-norm, cross-links to manuscripts on DOI/title match, records sync history with import/update/link counts and errors. `enrich_publications_with_openalex()` adds citation counts, concepts, topics, co-authors via DOI lookup.
- `routers/orcid.py` — `/config` (public), `/authorize?mode=login|signup|link`, `/callback`, `/disconnect`, `/sync` (manual), `/enrich-openalex`, `/sync-history`, `/status`, `/publications` (canonical store).
- New collection: `publications` with indexes on (owner_id, year), DOI (sparse), orcid_put_code (sparse), title_norm.
- Weekly scheduler job `_orcid_weekly_sync_job` (Sundays 03:30 UTC) — auto-skips when ORCID not configured.
- **Security**: `serialize_user()` now scrubs ORCID `access_token`/`refresh_token` from every response — only `orcid_id`/`verified_at`/`last_sync_at` exposed.
- Pytest: `tests/test_orcid_phase.py` **6/6 PASS**.

**Frontend**
- `components/orcid/OrcidBadge.jsx` — green ORCID iD SVG glyph (per ORCID brand guidelines), links to https://orcid.org/{id}, renders only when verified. Embeddable everywhere.
- `components/orcid/OrcidSettings.jsx` — connect/disconnect/sync/enrich panel with status block (ORCID iD, verification, publications imported, last sync), action buttons gated on `config.configured`, sync history scroll list with trigger + counts + errors. Shows "Admin setup pending" chip in dry-run.
- `pages/Settings.jsx` — surfaces `<OrcidSettings />` at top; handles `?orcid=connected` success toast and `?orcid_error=…` failure toast.
- `pages/PublicationHub.jsx` — new `OrcidPublicationsSection` at bottom: shows imported records with venue/year/type/DOI/concepts/citations + ORCID badge + "linked" indicator when bound to a manuscript. CTA section when no records.
- `components/marketplace/MatchCard.jsx` + `pages/Profile.jsx` — render `OrcidBadge` next to user name when verified.
- Route alias: `/publications` → `/publication-hub`.

**Testing**: iteration_14 — **Backend 100% PASS · Frontend 100% PASS** including the seed-and-display flow, token-sanitization verification on `/api/auth/me`, graceful 503 from `/api/orcid/authorize`, success/error toasts via deep links.

**Production readiness**: For go-live the operator needs to (1) register a sandbox or production app at https://orcid.org/developer-tools (or https://sandbox.orcid.org), (2) set `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, optionally `ORCID_BASE_URL` (default sandbox) and `ORCID_API_BASE_URL`, (3) ensure the redirect URI matches `${REACT_APP_BACKEND_URL}/api/orcid/callback`. No code or schema changes required.

### Phase 11 — Research File Layer + Marketplace v2 Enrichment (2026-02-14) ✅
File uploads attached to research entities + ORCID-publication signal integrated into matchmaking.

**Backend**
- `routers/files.py` — full CRUD: `/api/files/upload` (multipart, 50MB cap, MIME whitelist for PDF/DOCX/XLSX/PPTX/CSV/ZIP/PNG/JPG/WEBP/GIF/SVG), versioning via `root_id` chain (each upload bumps version, `is_latest` flag), download (StreamingResponse), metadata patch (rename/description), delete (uploader or admin only), `/api/files/recent` aggregating from all entities user is member of, `/api/files/{id}/versions`, `/api/files/{id}/activity` (upload/version/download/rename/edit/delete events with actor names).
- Access control: permissions inherit from the parent entity (workspace.member_ids / project.member_ids / manuscript.author_ids); 403 when non-member, 404 when entity missing.
- Storage: existing `services/storage_service.py` (Emergent Object Storage) — no changes.
- New collections + indexes: `files` (entity_kind+entity_id+is_latest, owner_id+created_at, root_id+version, sha256), `file_activity` (file_id+created_at).
- Pytest: `tests/test_files_phase.py` 3/3 PASS (full lifecycle incl. version chain, security, MIME rejection).

**Marketplace v2 enrichment**
- `services/marketplace/matching.py:deterministic_rank` now pre-fetches ORCID-imported publications for every candidate + the requester, merges OpenAlex `concepts` + `topics` + `journal` into the keyword token bag. Result: a stronger signal for users with synced ORCID — citation-grade topics now boost match scores without changing the API surface.

**Frontend**
- `components/files/FilePanel.jsx` — premium embeddable file panel: upload (single click → hidden input), per-row expand for Versions + Activity, version upload (paperclip icon per row), rename via double-click, download, delete with confirmation. Sonner toasts on every action.
- `components/files/RecentFilesWidget.jsx` — sidebar widget listing 8 most-recent files across all entities user belongs to.
- Embedded `FilePanel` on `WorkspaceDetail`, `ProjectDetail` (root level — visible on every tab), and `ManuscriptDetail`.
- All file rows + interactive elements carry data-testids.

**Testing**: iteration_15 backend 30/30 PASS (17 phase pytest + 13 fresh smoke). Frontend 100% PASS for workspace + manuscript flows; ProjectDetail placement bug fixed in iteration_16 (now visible on all 5 tabs).

### Phase 11.5 — Inline File Previews + Expertise Attachments (2026-02-14) ✅
- ✅ `components/files/PreviewDrawer.jsx` — right-side slide-in drawer for PDF / image / CSV(TSV) / TXT(MD/JSON). PDFs render in `<iframe>`, images in zoom-friendly `<img>`, CSV/TSV parsed server-side into a styled table (first 100 rows), text via blob→text. Streaming endpoints `/api/files/{fid}/preview` and `/api/files/{fid}/preview-csv` (server-side rows cap, ACL-inherited from parent entity).
- ✅ Expertise Requests: `/api/expertise/{rid}/attachments` POST (link uploaded file ids) + DELETE + GET; surfaced on `ExpertiseRequestDetail` with chip list + per-row remove for owner.
- ✅ **P0 UX fix (this session)**: PreviewDrawer close button no longer occluded by toast notifications.
  - Escape key handler closes drawer
  - z-index raised to `z-[10000]` (above Sonner's 9999)
  - Active toasts dismissed on drawer open
  - Close button gains `aria-label` + bordered style + `title="Close (Esc)"`

### Pre-Beta Audit (2026-02-14)
Comprehensive audit completed and saved to `/app/memory/PRE_BETA_AUDIT.md`:
- **Production Readiness Score: 84.5 / 100** → improved to **90.4 / 100** after Hardening Phase → **92.5 / 100** after Production-Prep.

### MVP Hardening Phase (iter 18, 2026-02-14) ✅
Full deliverable: `/app/memory/HARDENING_REPORT.md`. Test report: `/app/test_reports/iteration_18.json`.
- CORS lockdown, env-driven cookie security, slowapi rate limiting (5/min/IP), `EXPOSE_RESET_TOKEN=0` default, GDPR cookie consent banner (4 categories), email verification lifecycle (token+resend+expiry+idempotent verify), `/verify-email` page.
- 13/14 backend hardening assertions PASS; 100% frontend PASS; 1 P1 infra finding (ingress CORS rewrite — flagged for deploy).

### MVP Production-Prep Phase (iter 19, 2026-02-14) ✅
Full deliverable: `/app/memory/PRODUCTION_CHECKLIST.md`.

### Monetization v2 (iter 20, 2026-02-15) ✅
Pricing structure + billing architecture redesigned for global academic launch. See `Pricing.jsx` rebuild + dual-balance model + 6 billing collections (delivered fully; see git history for details).

### Monetization v3 — Permission Engine + Billing Center + Admin Revenue (iter 21, 2026-02-15) ✅

### Growth Infrastructure — Referrals + Rewards + Promotions + Engagement + Analytics (iter 22, 2026-02-15) ✅

**Phase 1 (production-critical) — DONE**
- **Gating sweep**: `Depends(require_feature(...))` applied to AI Assistant (POST), AI Matching (journal/conference/grant/reviewer), Publication Hub router-level. Free user → 402 with `{code, message, required_plan, upgrade_url}` for all premium endpoints.
- **Billing Center**: shipped iter 21 (`/settings/billing`)
- **Admin Revenue Dashboard**: shipped iter 21 (`/admin/revenue`)
- **Audit log** (`services/audit.py` + `audit_log` collection): `write_audit()` called from billing cancel, credit-pack grants, all promotion issues, reward grants. Indexed on `(created_at)`, `(actor_id, action, created_at)`, `(target_user_id, created_at)`. Exposed via `GET /api/admin/audit?action=&actor_id=&target_user_id=` (super-admin).

**Phase 2 (growth) — DONE**
- **Referral system** (`services/referrals.py` + `referrals` collection):
  - Stable referral_code per user (auto-generated on first lookup)
  - Self-referrals + duplicate attributions silently ignored
  - Qualification rules: email_verified + onboarded + ≥3 session_start + ≥30 active minutes + ≥1 project + ≥1 workspace
  - `POST /api/referrals/recompute`, `GET /api/referrals/me`
  - Auto-recomputes on every session_event milestone
- **Rewards system** (`services/rewards.py` + `reward_grants` collection):
  - 6-tier ladder: 1→100c, 3→1mo, 5→500c, 10→3mo, 25→VIP badge, 50→12mo
  - Idempotent per (user, tier_count, kind) — never double-grants
  - Free-month grants extend existing subscription period OR create a comp subscription at researcher tier
  - Each grant audit-logged
  - `GET /api/rewards/me`

**Phase 3 (admin growth engine) — DONE**
- **Promotion engine** (`services/promotions.py` + `promotions` collection): SUPER_ADMIN issues credits / discounts (Stripe coupons when configured) / free_months / vip / beta / early_access / custom. Target by user_id OR email. Every issue written to `audit_log`. UI not yet built — back-end + API ready.
- `POST /api/admin/promotions`, `GET /api/admin/promotions`

**Phase 4 (advanced analytics) — DONE**
- **Engagement scoring** (`services/engagement.py`):
  - 5-tier classification: power / healthy / inactive / at_risk / dormant
  - Inputs: sessions(30d), minutes(30d), projects, workspaces, collaborations, ai_credits(30d), paid status, qualified referrals
  - Weighted score capped at 100; tier determined by `days_since_active` first, then score
  - `GET /api/admin/engagement/{uid}` + `GET /api/admin/engagement?limit=` (tier rollup)
- **Platform analytics**:
  - DAU/WAU/MAU from `session_events` aggregation
  - Avg session duration, top pages, feature usage, top users, top institutions, referral performance, retention proxy
  - `GET /api/admin/analytics`
- **Session telemetry**: `POST /api/session/event` accepts `session_start | session_end | page_view | feature_use` with duration_minutes + path + feature. Triggers referral qualification recompute as a side effect.

**Verification (preview env)**
- Gating sweep: 4/4 premium routes return 402 for Free user ✅
- Referral code + tracking endpoints functional ✅
- 4 session_event types persisted with IP + UA ✅
- SUPER_ADMIN promotion (vip / credits / free_months) all working, with VIP+free_months auto-upgrading Free user → Researcher plan + unlocking 35 features ✅
- Audit log captures every promotion with actor + target + metadata ✅
- Engagement scoring returns tier/score/metrics ✅
- Platform analytics returns DAU/WAU/MAU/retention/top pages/features ✅
- Non-admin → 403 on all `/api/admin/*` endpoints ✅

**Collections added (5 new)**: `referrals`, `reward_grants`, `promotions`, `session_events`, `audit_log` — all indexed for production-scale queries.

**Files added (7 new)**: `services/audit.py`, `services/referrals.py`, `services/rewards.py`, `services/promotions.py`, `services/engagement.py`, `routers/growth.py`, `routers/admin_growth.py`.

**Deferred (clean follow-ups)**
- Admin UI panels for Promotions (grant form + history table) and Engagement (segmented user lists with bulk actions)
- Frontend referral landing surface — `/settings/refer` with share link + qualifier checklist
- Stripe coupon redemption flow in CheckoutSession (currently coupons are created via promotion engine; redemption is via Stripe Dashboard until UI is built)
- Lifecycle emails triggered by tier transitions (Resend templates exist; just need event wiring)

**Updated credit economy** (more realistic academic usage)
- Plans: Free 50 / Researcher 300 / Pro 1,000 / Institution 20,000
- 13 AI actions repriced: Manuscript Review/Literature Review 20, Statistical Review 25, Methodology Builder / Research Design Advisor / Gap Finder 10, Journal/Conference/Grant Matching + Abstract Generator 5, Assistant/Copilot/Rewriting 2

**Permission engine** (`backend/services/permissions.py`)
- `require_plan(min_plan)`, `require_feature(key)`, `require_credits(action)`, `require_super_admin` — FastAPI dependencies for server-side gating
- `has_plan_at_least`, `has_active_subscription`, `can_access_feature`, `can_consume_credits`, `assert_quota`, `access_summary` — composable predicates
- All 402 responses carry structured detail `{code, message, required_plan, current_plan, upgrade_url, ...}` consumed by frontend modal
- `FEATURE_MIN_PLAN` catalogue maps 35 feature keys → minimum plan tier
- `PLAN_QUOTAS` centralises projects/workspaces caps
- `SUPER_ADMIN_EMAILS` env list — bypasses every gate

**SUPER_ADMIN role**
- New env vars: `SUPER_ADMIN_EMAILS` (default `synaptiq.academy@gmail.com`) + `SUPER_ADMIN_PASSWORD` (default `SuperAdmin123` — rotate in prod)
- Seeded user with `role=super_admin`, `plan=institution`, 1M credits, `email_verified=true`
- All admin routes protected via `Depends(require_super_admin)`

**Permission introspection** (`routers/permissions.py`)
- `GET /api/permissions/me` — full access map (35 features) + credits + quotas, used by frontend to render gates client-side too
- `GET /api/permissions/can/{feature}` — single-feature soft check

**Admin Revenue Dashboard** (`routers/admin_revenue.py` + `pages/AdminRevenue.jsx`)
- `GET /api/admin/revenue` — MRR/ARR (computed from active plan counts × monthly price), 30d credits consumed/purchased, 30d pack revenue, churn rate, 12-week revenue trend
- `GET /api/admin/users-overview` — paginated user table with plan/status/credits
- UI at `/admin/revenue` — 4 KPI tiles + plan distribution + weekly bar trend
- Non-super-admin → 403 → `<AdminRevenue/>` renders `admin-revenue-denied` state

**Billing Center** (`pages/BillingCenter.jsx` at `/settings/billing`)
- Hydrated from production endpoints (no mocks): current plan + status + renewal date, monthly + pack + total credit tiles, billing history table, pack purchase history, subscription history
- Buttons: Upgrade Plan, Buy Credits, Cancel Subscription (new `POST /api/billing/cancel`), Manage Billing (Stripe portal)
- Past-due banner when `subscription_status=past_due`

**Frontend Upgrade Modal** (`components/billing/UpgradeModal.jsx`)
- Axios response interceptor (`lib/api.js`) catches 402 with structured `detail.code` and dispatches `window.event('synaptiq:gate', detail)`
- Modal listens globally; shows context-aware CTAs (Buy Credits + Upgrade Plan for `credits_exhausted`; View Plans for `upgrade_required`/`subscription_inactive`/`quota_exceeded`)
- Replaces raw error toasts for every premium gate

**Webhook handlers** (`routers/billing.py`)
- Added `invoice.payment_failed` → marks subscriptions `past_due` + records billing_history event
- Added `customer.subscription.deleted` → downgrades user to `free` + records subscription_history transition

**Gating applied to** `routers/assistant.py` (POST `/assistant/sessions`, POST `/assistant/sessions/{sid}/messages`) — every other premium endpoint follows the same `Depends(require_feature(...))` pattern.

**Verification (preview env)**
- 4-plan response shows 50/300/1000/20000 credits ✅
- Free user POST /api/assistant/sessions → 402 with upgrade_required payload ✅
- SuperAdmin permission map → 35/35 features allowed ✅
- Non-admin GET /api/admin/revenue → 403 ✅
- BillingCenter page hydrates current plan + credit balances + pack purchase history ✅
- AdminRevenue page shows MRR €299, ARR €3,588, plan distribution (59 free / 1 institution), 12-week trend ✅

### Deferred to next iteration (P6-P9 of original spec)
- Referral system (qualified-referral tracking + reward grants)
- Rewards system (badge/credit/free-month grants based on referral count)
- Promotion engine (SUPER_ADMIN issuing discounts / free months / bonus credits)
- Engagement scoring (Power/Healthy/Inactive/At-Risk/Dormant classification)
- Full feature gating sweep across all premium routes (only Assistant routes wrapped in this pass; pattern is established — remaining routes are ~30-minute search-and-replace per spec)
Pricing structure + billing architecture redesigned for global academic launch. Visual design / typography / spacing / colors / components untouched.

**Pricing model**
- **4 tiers**: Free €0 (50 credits) → Researcher €9.99 *Early Access*, future €14.99 (1,500 credits) → Pro Researcher €29.99 *Best Value* (5,000 credits) → Institution €299 (50,000 credits)
- **4 credit packs** (one-time, never expire): 100→€5, 250→€10, 1,000→€29, 5,000→€99
- **Annual discount**: 20% savings preserved
- Updated `CREDIT_COSTS` per spec (Manuscript Review 10, Recommendations 5, Assistant 2/query, Copilot 1/msg, discovery+profile+collab = free)

**Backend collections (new)**
- `credit_balances` (denormalized on `users.credits_balance` + `users.credits_pack_balance`)
- `credit_transactions` — append-only ledger; every consume/refund/grant/pack_grant
- `credit_purchases` — Stripe pack purchase audit
- `billing_history` — user-visible invoices/pack purchases/subscription events
- `subscription_history` — plan state-transition log
- `credit_packs` — pack catalogue (seeded from `plans_catalogue.CREDIT_PACKS`)

**Dual-balance model**
- `monthly_balance`: refills to plan allowance each billing cycle, does NOT roll over
- `pack_balance`: from one-time purchases; never resets, never expires
- Consume order: monthly first → then pack. Mixed-bucket consumption tracked in transaction metadata.

**New endpoints**
- `GET /api/billing/credit-packs` — public pack catalogue
- `GET /api/billing/credit-usage-catalogue` — display rows for pricing page
- `GET /api/billing/feature-matrix` — 24-row plan comparison
- `POST /api/billing/credit-pack-checkout` — Stripe one-time checkout for a pack
- `GET /api/billing/history` — user-visible billing history
- `GET /api/billing/subscription-history` — state-transition log
- `GET /api/credits/transactions` — authoritative ledger view
- `GET /api/credits/purchases` — pack purchase history
- `/api/billing/webhook` — now handles `checkout.session.completed` for both subscriptions AND credit-pack purchases (idempotent, metadata-driven)

**Frontend pricing page (Pricing.jsx)**
- 4-plan grid: `md:grid-cols-2 lg:grid-cols-4` (single content-driven adjustment; all card styling preserved)
- Pro Researcher highlighted with dark accent badge "Best Value"; Researcher with amber "Early Access" badge + future-price text
- Each Free plan card shows "Not included" sub-section listing 7 excluded features
- Credit-pack section (4 cards, "Never expires · Stacks with monthly credits")
- Research Credit Usage section refactored with green-tinted "Free" actions vs accent-colored paid actions
- 24-row × 4-column feature comparison matrix with check/x cells
- 5-item FAQ with expand/collapse (lucide Plus/Minus icons)
- Enterprise CTA section (dark band with Contact Sales button)
- All sections use existing editorial vocabulary: `overline`, `font-serif`, `#0F2847` accent, `border-slate-200`, Merriweather H2s via `.marketing-page`

**Migration**
- All existing users on stale plan codes auto-reset to `free` (Stripe was never live, no real subscribers — clean cut per user instruction)
- `credits_pack_balance` field backfilled to 0 on all users
- Plan catalogue upserted in `plans` collection; stale codes deleted

**Testing**
- Full end-to-end webhook flow verified: pack purchase → balance grant → purchase + transaction + billing_history persisted
- Mixed-bucket consume verified (monthly empty → falls through to pack)
- 4 pre-existing pytest assertions are now stale due to intentional spec changes (3→4 plans, credit cost adjustments, debug_reset_token off in dev). Flagged in tech debt; not real bugs.

**Implemented (no creds required)**
- **Security headers middleware** (`backend/middleware/__init__.py`): CSP, HSTS (gated on COOKIE_SECURE=1), X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy, X-XSS-Protection. CSP whitelists Stripe + form-action.
- **Production-mode env validation** (`backend/services/prod_validator.py`): startup refuses to launch with `APP_ENV=production` if required vars (CORS_ORIGINS≠*, COOKIE_SECURE=1, EXPOSE_RESET_TOKEN=0, JWT_SECRET≥32ch, APP_BASE_URL, MONGO_URL, DB_NAME) are missing — RuntimeError with bulleted list.
- **Structured logging** (`backend/services/logging_config.py`): JSON lines on stdout in prod, plain text in dev.
- **EMAIL_VERIFICATION_REQUIRED=1 flow** — verified end-to-end: register → 200 with no auto-login → login 403 "Please verify…" → verify-email → login 200.
- **Production-readiness validator endpoint**: `GET /api/admin/production-readiness` (admin-only) — returns full audit with errors/warnings, used pre-launch to confirm `ready_for_production: true`.
- **Production deployment checklist**: 8-step runbook in `PRODUCTION_CHECKLIST.md` covering domain/TLS, env vars (Group A required + Group B integrations), Stripe activation, Resend activation, ORCID prod activation, ingress CORS limitation, smoke tests, final score.

**Test verification (preview env)**
- Security headers present on every response (verified via `curl -I`).
- Production-mode RuntimeError verified when `APP_ENV=production` + missing `COOKIE_SECURE=1`.
- Admin `/production-readiness` returns 200 for admin / 403 for non-admin.
- EMAIL_VERIFICATION_REQUIRED gating works end-to-end with idempotent verify.

**Production Readiness Score: 84.5 → 90.4 → 92.5** (+2.1 this iteration; Operability +16, Deployment readiness +16).

**Security**
- CORS lockdown — explicit `CORS_ORIGINS` allowlist with fail-safe refusal of wildcard+credentials (⚠ 1 finding: ingress overrides `Access-Control-Allow-Origin` to `*` — infra task, not code).
- Cookie `secure` + `samesite` flags now env-driven (`COOKIE_SECURE`, `COOKIE_SAMESITE`).
- `slowapi` rate limiting on login/register/forgot-password/resend-verification at 5/min/IP (env-overridable).
- `EXPOSE_RESET_TOKEN=0` by default; hard-off in `APP_ENV=production`. `debug_reset_token` and `debug_verification_token` no longer leak.
- Password policy hardened: ≥8 chars + letter + digit (was ≥6).

**GDPR (Cookie Consent)**
- `CookieConsentBanner.jsx` — Accept All / Reject Non-Essential / Manage Preferences with 4 categories (Essential locked).
- `consent_records` collection — anonymous (consent_id) OR authenticated; SHA-256 truncated IP hash for audit; immutable history.
- `POST /api/consent` + `GET /api/consent/latest` endpoints.
- Privacy + Cookie Policy links inline.

**Email Verification**
- New endpoints: `POST /api/auth/verify-email`, `POST /api/auth/resend-verification`.
- New email template + `send_email_verification` typed helper (Resend dry-run-safe).
- 24h JWT verification token + `email_verifications` collection + single-active-token invariant.
- Idempotent verification + replay protection + expiry handling.
- New page `/verify-email?token=...` with 4 states (verifying/success/already/error) + resend UI.
- Optional gate at login via `EMAIL_VERIFICATION_REQUIRED=1`.

**Testing**
- iter18: 13/14 backend hardening assertions PASS (1 infra-level finding); 100% frontend PASS.
- Test artifact: `/app/backend/tests/test_hardening_iter18.py`.
- 224 backend routes verified, 0 broken; 57 frontend routes verified, 0 broken.
- 1 orphan component flagged (`RecentFilesWidget`).
- 13 stale pytest tests identified (deprecated API shapes; not real bugs).
- Permission audit: file ACL, marketplace, workspace, manuscript, institution — **no leaks**.
- Security: CORS=`*` and cookies `secure=False` flagged as P0 launch blockers; tokens scrubbed; bcrypt + JWT verified.
- 9 third-party integrations documented (LIVE | SANDBOX | DRY-RUN | UNCONFIGURED).
- 44 Mongo collections inventoried; 18k+ live discovery records.
- Recommended Sprint A/B/C/D plans laid out.

### Future Backlog
- Stripe checkout for institutional seat billing.
- Resend live API key wiring.
- ORCID OAuth credentials wiring (dry-run currently).
- Atlas Search migration.
- Cover-letter generator.
- Public institution storefront.
