# Monetization: tiers, entitlements, AI credits and cost control

Owner-approved model. The single sources of truth are in code:

| Concern | Source |
|---|---|
| Plans, prices, credits, quotas, storage, packs, AI operation prices, capabilities | `backend/plans_catalogue.py` |
| "May this user do X" | `backend/services/entitlements.py` |
| Route-level enforcement (paid areas, workspace locks) and the per-request credit lifecycle | `backend/services/monetization_middleware.py` |
| Credits: reservations, ledger, renewal/upgrade/downgrade rules, packs | `backend/services/credits_service.py` |
| Provider prices, model routing, cost guards | `backend/services/ai/pricing.py`, `backend/services/ai/cost_guard.py` |
| Stripe lifecycle | `backend/routers/billing.py`, [`STRIPE_SETUP.md`](STRIPE_SETUP.md) |

Internal plan codes are unchanged (existing users, subscriptions and history carry
them): `free` → FREE, `researcher` → PRO ("Pro"), `pro_researcher` → PRO_ADVANCED
("Pro Advanced"). The legacy, non-self-serve `institution` / `enterprise` codes get
PRO_ADVANCED capabilities.

## Tiers

| | Free | Pro | Pro Advanced |
|---|---|---|---|
| Price | €0 | €9.99/mo (Early Access; future €14.99) | €29.99/mo |
| AI credits / month | 0 | 200 | 750 |
| Projects | 0 | unlimited | unlimited |
| Workspaces | 0 | 10 | unlimited |
| Storage | profile only (0 B general) | 10 GB | 50 GB |

FREE is identity only: profile, public research page, ORCID + publication import,
being discoverable. Paid users can invite a Free user; the invitation notification
says "<name> would like to collaborate with you — Upgrade to Pro to respond".
Responding (`PATCH /api/collaboration-requests/{id}`) requires Pro.

## Enforcement

- **AI**: `consume_credits()` rejects FREE and lapsed plans (402
  `upgrade_required`) before anything is charged. Every credit-billed endpoint goes
  through it, so this covers all AI features regardless of route gating.
- **Paid areas**: `MonetizationMiddleware.RULES` (prefix → capability). Reads of a
  user's own data areas (projects, workspaces, messages, teaching) stay allowed so a
  downgrade makes data read-only, not hidden. A test fails if a rule matches no real
  route.
- **Quotas**: `assert_quota()` / `assert_storage_quota()` use the effective plan.
- **Lapsed subscription**: `unpaid` / `canceled` / `expired` / `incomplete*` ⇒
  effective plan Free. `past_due` keeps access (grace while Stripe retries).

## Credits

Two balances: subscription credits (`users.credits_balance`) and purchased credits
(`users.credits_pack_balance`). Subscription credits are spent first.

Reservation lifecycle (`credit_reservations`): RESERVED → COMPLETED on success, or
RELEASED (exact refund to the original buckets, at most once) when the request ends
with status ≥ 400 or an exception. The middleware finalizes every reservation of a
request, so endpoints that forget to refund still never charge for failures.
An `Idempotency-Key` header (sent by the frontend on every write) prevents a retried
request from being charged twice: a replay of a RESERVED/COMPLETED key gets 409.

Ledger (`credit_transactions.ledger_type`): SUBSCRIPTION_ALLOCATION,
AI_RESERVATION (the debit), AI_CONSUMPTION (balance-neutral confirmation),
AI_REFUND, CREDIT_PACK_PURCHASE, ADMIN_ADJUSTMENT. The legacy `kind` field is kept
for existing dashboards.

### Renewal and plan-change rules

- **Renewal** (verified `invoice.paid`, `subscription_cycle`): subscription credits
  are set to the allowance (e.g. 17 → 200); purchased credits untouched
  (e.g. 120 → 120). Once per cycle key.
- **Free → paid**: allocation for the new cycle.
- **Upgrade mid-cycle (Pro → Pro Advanced)**: top-up = new allowance − credits
  already granted this cycle (e.g. 17 left of 200 → 17 + 550 = 567). The cycle's
  total grant can never exceed the higher plan's allowance, so down/up switching
  can't farm credits.
- **Downgrade (paid → lower paid)**: subscription credits capped at the new
  allowance; nothing refunded or deleted; workspaces above the limit become
  read-only (oldest stay writable; delete/leave always allowed).
- **Cancellation**: at period end the account becomes Free; subscription credits
  expire; purchased credits are kept but only usable on a paid plan.

## AI cost control

- Per-request telemetry in `ai_requests`: user, plan, operation, action, model,
  input/output/cache tokens, credits charged, provider cost, status, latency,
  reservation id, `billed` flag (false = provider call without a credit
  reservation — watch this in admin metrics).
- Provider prices: `services/ai/pricing.py`, override with
  `AI_PROVIDER_PRICING_JSON`. Defaults must be verified against current
  Anthropic pricing.
- Routing: operations tagged `simple` use `AI_MODEL_SIMPLE` (default Haiku 4.5).
- Guards (`AI_COST_GUARDS_JSON`): max input/output tokens, max estimated cost per
  request, per-user daily and monthly provider-cost ceilings. Rejections return
  413/429 and the reservation is released.
- Prompt caching: long system prompts are sent as cacheable blocks
  (`AI_PROMPT_CACHING`, `AI_PROMPT_CACHE_MIN_CHARS`); cache reads are recorded.
- Admin: `GET /api/admin/ai/monetization-metrics` (cost by plan, operation,
  feature and model; cost per credit; top users by cost; cache hit ratio).
- Simulation: `python backend/scripts/monetization_cost_simulation.py`.

## Every AI path and its billing classification

Enforced at the single gateway chokepoint (`services/ai/cost_guard.py::preflight`):
inside a user HTTP request, an AI call without a credit reservation is **blocked**
unless its feature is listed in `INTERNAL_NON_BILLABLE_FEATURES`. Every provider
call is recorded in `ai_requests` with `billing_class`.

| Path (entry point) | Feature | Class | Charged as |
|---|---|---|---|
| Manuscript Copilot chat `POST /api/assistant/sessions/{id}/messages` | general.assistant | USER_BILLABLE | AI_ASSISTANT_SIMPLE |
| AI rewriting `/api/ai/rewrite` | manuscript.rewriting | USER_BILLABLE | QUICK_ACADEMIC_REWRITE |
| Abstract generator `/api/ai/abstract` | manuscript.abstract_generator | USER_BILLABLE | ABSTRACT_ANALYSIS |
| Collaborator recommendations / methodology assist `/api/ai/*` | collaboration.researcher_matching, general.assistant | USER_BILLABLE | ai_collaborator_matching / MANUSCRIPT_SECTION_REVIEW |
| Journal / conference / grant / reviewer matching (`services/ai/matching.py`) | collaboration.matching | USER_BILLABLE | JOURNAL_FIT / CONFERENCE_FIT / GRANT_FIT / ai_reviewer_matching |
| Manuscript review `/api/manuscript-review` | manuscript.review | USER_BILLABLE | FULL_MANUSCRIPT_REVIEW |
| Manuscript intelligence (quick/standard/deep) | manuscript engine | USER_BILLABLE | MANUSCRIPT_SECTION_REVIEW / FULL_MANUSCRIPT_REVIEW / ADVANCED_MANUSCRIPT_INTELLIGENCE (deep = Pro Advanced) |
| Literature review `/api/literature-review` | literature_review.synthesis | USER_BILLABLE | LITERATURE_SYNTHESIS |
| Literature intelligence analyze / generate | literature_review.* | USER_BILLABLE (**newly billed** — was unbilled) | MULTI_PAPER_SYNTHESIS |
| Literature intelligence compare / gaps | literature_review.* | USER_BILLABLE (**newly billed**) | LITERATURE_SYNTHESIS |
| Research gap finder / gap intelligence | research_gap.finder | USER_BILLABLE | LITERATURE_SYNTHESIS |
| Statistical review / statistical intelligence | statistical.advisor | USER_BILLABLE | MANUSCRIPT_SECTION_REVIEW |
| Research design advisor | research_design.advisor | USER_BILLABLE | MANUSCRIPT_SECTION_REVIEW |
| Collaboration Intelligence | collaboration.* | USER_BILLABLE | LITERATURE_SYNTHESIS |
| Teaching lesson / assessment generation, teaching assistant | teaching.* | USER_BILLABLE | TEACHING_CONTENT_GENERATION / AI_ASSISTANT_SIMPLE |
| Academic Copilot (chat, dashboard, suggestions, roadmap) | copilot.advisor | USER_BILLABLE | copilot_* actions |
| Multi-agent Copilot `/api/copilot/execute*`, `/workflows/{id}` | agents (`agents/*.py`) | USER_BILLABLE (**newly billed**) | DEEP_RESEARCH per run |
| AI OS `/api/ai-os/conversations/{id}/messages` | ara.agent.* | USER_BILLABLE | AI_ASSISTANT_SIMPLE (charged before the call) |
| ARA mission steps (worker, incl. scheduled missions) | ara_* | USER_BILLABLE (**newly billed**, via `billed_background_operation`) | MANUSCRIPT_SECTION_REVIEW per AI step |
| Meetings AI `/api/meetings/{id}/ai/*` | meetings.ai.* | USER_BILLABLE | AI_ASSISTANT_SIMPLE |
| Research Need interpretation | research_need.interpret | USER_BILLABLE | RESEARCH_QUESTIONS |
| Team blueprint, marketplace rerank, publishing intelligence, knowledge graph, career, prediction, collab-intel v2, autonomous agents, institution intel, self-improvement, academic OS | various | USER_BILLABLE | their catalogue/legacy actions |
| LKG natural-language search summary `GET /api/lkg/search` | lkg.search | **blocked enrichment** — search still works without the AI summary | — |
| LKG insights `GET /api/lkg/insights/...` | lkg.insights | **blocked enrichment** — deterministic graph facts returned | — |
| Grant Hub gap analysis AI recommendations | grant_hub.gap_detection | **blocked enrichment** — deterministic gap analysis still returned | — (P1: make it an explicit billed action if wanted) |
| Admin OS copilot `/api/admin/x/...` | admin_copilot | INTERNAL_NON_BILLABLE (admins only) | — |
| Evidence validator (inside a billed request, Haiku ≤300 tokens) | validation | INTERNAL_NON_BILLABLE, cost attributed to the request's reservation | — |
| Worker `ai.execution` handler | — | dead code (wrong engine signature; never enqueued) | — |
| Any other background call without a reservation | — | BACKGROUND_UNATTRIBUTED — visible in admin metrics | — |

## Billing states

| Stripe status | Synaptiq access | Credits |
|---|---|---|
| active / trialing | paid plan | renewal resets subscription credits |
| past_due | **grace**: paid access kept while Stripe retries | no new credits |
| unpaid | paid access suspended (effective Free); plan, data and credits kept | no new credits; paying the invoice restores |
| canceled / incomplete_expired / deleted | Free; data kept; workspaces above limit read-only | subscription credits expire; purchased kept but unusable on Free |
| cancel_at_period_end | paid access until period end | — |

## Refunds and disputes

Full credit-pack refund: removes `min(pack credits, purchased balance)` once
(atomic status flip); any already-spent shortfall is recorded in the ledger and
`billing_alerts`. Partial refunds and disputes are recorded for manual review —
no automatic balance change. Subscription refunds don't change credits.

## Storage

Usage = latest repository file versions + message attachments + knowledge-base
documents (sizes recorded server-side at upload). Quota checked on file upload,
message attachment upload and knowledge-document upload.

## Workspaces

The limit is enforced inside `services/workspace_provisioning.provision_workspace`,
so every creation path (workspaces, team builder, grant applications, Grant Hub,
conference teams) is covered.

## Manuscript context

The Manuscript Copilot adds the current text of the sections a request names
("improve the Discussion") plus an abstract excerpt
(`services/ai/manuscript_context.py`), within a character budget. Full manuscript
review still sends the whole document by design (bounded by input-token guards).

## Admin and test tooling

- `GET /api/admin/ai/monetization-metrics`: cost today / this month, by plan,
  operation, feature, model; average cost per paid user; credits consumed; packs
  sold (real packs only); revenue by kind; estimated AI gross margin.
- `POST /api/admin/users/{uid}/billing-simulate` (super admin, refused when
  `STRIPE_MODE=live`): `set_plan`, `renew`, `end_subscription`, `grant_purchased`.
- `GET /api/billing/me`: plan, status, cancel_at_period_end, period end, credit
  balances, limits — no Stripe internals.

## Data migration

Lazy and non-destructive: no user document is rewritten by deploy. Existing Free
users' old monthly credits stay on the document but are unusable (FREE has no AI)
and reset to 0 at their next timer reset. Purchased credits are untouched. Existing
projects/workspaces of Free users stay readable; writes need Pro.
`backend/scripts/migrate_monetization_v2.py` reports the affected counts
(`--dry-run`, the default) and can normalize Free users' subscription credits to 0
with a reversible backup field (`--apply` / `--revert`).
