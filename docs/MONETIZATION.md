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

## Data migration

Lazy and non-destructive: no user document is rewritten by deploy. Existing Free
users' old monthly credits stay on the document but are unusable (FREE has no AI)
and reset to 0 at their next timer reset. Purchased credits are untouched. Existing
projects/workspaces of Free users stay readable; writes need Pro.
`backend/scripts/migrate_monetization_v2.py` reports the affected counts
(`--dry-run`, the default) and can normalize Free users' subscription credits to 0
with a reversible backup field (`--apply` / `--revert`).
