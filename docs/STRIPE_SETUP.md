# Stripe Setup

Stripe is already integrated in code (`backend/services/stripe_service.py`,
`backend/routers/billing.py`) — this document covers the external account setup required
to activate it. **As of this writing, Stripe is not yet configured in this environment**:
`STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` are unset, and every plan's
`stripe_price_id_monthly`/`stripe_price_id_annual` in `backend/plans_catalogue.py` is an
empty string. The integration code has been verified end-to-end with synthetic signed
webhook events against the real database (proving the plan-upgrade/downgrade sync logic
works) — what remains is purely external configuration, detailed below.

## 1. Create products and prices

For each paid plan in `backend/plans_catalogue.py` (`researcher`, `pro_researcher`,
`institution` — `enterprise` is contact-sales/custom-invoiced, not self-serve checkout):

1. Stripe Dashboard → Product Catalog → **Add Product**.
2. Add a **recurring monthly price** and a **recurring annual price** for each product,
   matching the amounts in `plans_catalogue.PLANS` (e.g. Researcher: €9.99/mo, €7.99/mo
   billed annually — verify current values in that file, they are the source of truth).
3. Copy each price's ID (`price_...`).

Also create **one-time prices** for each credit pack in `CREDIT_PACKS`
(`pack_100`, `pack_250`, `pack_1000`, `pack_5000`).

## 2. Wire price IDs into the catalogue

Unlike most config in this app, **Stripe Price IDs are not environment variables** — they
are fields on each plan/pack dict in `backend/plans_catalogue.py`:

```python
{
    "code": "researcher",
    ...
    "stripe_price_id_monthly": "price_...",   # ← fill in
    "stripe_price_id_annual":  "price_...",   # ← fill in
},
```

and similarly `"stripe_price_id"` on each `CREDIT_PACKS` entry. Until these are filled
in, `POST /api/billing/checkout-session` and `POST /api/billing/credit-pack-checkout`
correctly return `503` with a message telling the caller exactly what's missing — this is
intentional fail-closed behavior, not a bug.

**Resolved (2026-07-19 configuration consistency pass):** `backend/.env.example` used to
list `STRIPE_PRICE_RESEARCHER_MONTHLY`/`_ANNUAL` and `STRIPE_PRICE_INSTITUTION_MONTHLY`/`_ANNUAL`
as environment variables, and `services/prod_validator.py` warned if they were unset —
but nothing in the codebase ever read those env vars into `plans_catalogue.py`, so setting
them had zero effect on checkout and could give a false sense of completion. Both have
been removed: `.env.example` now points directly at this section instead, and the
validator has a single `STRIPE_PLAN_PRICE_IDS` check that inspects
`plans_catalogue.PLANS` itself — every self-serve paid plan's
`stripe_price_id_monthly`/`stripe_price_id_annual` (`free` and `enterprise` intentionally
excluded, per the code comment above), catching exactly the plans the old check missed
(it never covered `pro_researcher` at all). `plans_catalogue.py` remains the only source
of truth for whether checkout will actually work for a given plan/pack — the validator
now actually reflects that instead of checking a parallel, disconnected env var surface.

## 3. API keys

```
STRIPE_SECRET_KEY=sk_live_...       # or sk_test_... while testing
```

Dashboard → Developers → API Keys.

## 4. Webhook endpoint

1. Dashboard → Developers → Webhooks → **Add endpoint**:
   `https://api.synaptiq.academy/api/billing/webhook`
2. Subscribe to at least:
   `checkout.session.completed`, `customer.subscription.created`,
   `customer.subscription.updated`, `customer.subscription.deleted`,
   `customer.subscription.trial_will_end`, `invoice.payment_succeeded`,
   `invoice.payment_failed`, `invoice.payment_action_required`, `charge.refunded`,
   `charge.dispute.created`.
3. Copy the signing secret:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
   Without this set, the webhook endpoint acknowledges receipt but discards every event
   unprocessed (`{"received": true, "processed": false}`) — deliberate fail-safe, not a bug.

## 5. Subscription metadata — required for plan sync to work

`create_checkout_session()` sets `subscription_data.metadata` (not just top-level
Checkout Session metadata) with `user_id`/`plan_code`/`billing_period`, because Stripe
does **not** copy Checkout Session metadata onto the created Subscription object
automatically. The webhook handler reads this metadata first, falling back to matching
the subscription's Stripe price ID against `plans_catalogue.PLANS` if metadata is absent
(e.g., for subscriptions created directly in the Stripe Dashboard rather than through
Checkout). Both paths were tested and confirmed working — see §8.

## 6. Idempotency and failure handling (already implemented — verify, don't reconfigure)

- Every webhook event is inserted into `billing_events` keyed by a **unique index on
  `stripe_event_id`** — Stripe's retried/duplicate deliveries (it retries for up to 72h)
  are detected via the resulting duplicate-key error and ignored, never double-processed.
- Checkout session creation attaches a deterministic SHA-256 idempotency key
  (`user_id + price_id + billing_period`), so a retried checkout request from the client
  can't create two sessions.
- `invoice.payment_failed` marks the user's subscription `past_due` and notifies them
  in-app; a subsequent successful payment (`customer.subscription.updated` with
  `status=active`) clears `past_due` back to `active` automatically.
- `customer.subscription.deleted` (or `.updated` with a terminal status) reverts the
  user to the `free` plan and resets their credit allowance accordingly.
- Signature verification is mandatory — a request with a missing/invalid
  `stripe-signature` header is rejected with `400` before any business logic runs.

## 7. Enabling automatic tax (optional)

```
STRIPE_TAX_ENABLED=1
```
Requires Stripe Tax to be configured/activated in your Stripe account first (Dashboard →
Tax) — this env var only toggles whether checkout sessions *request* automatic tax and
tax ID collection, it doesn't configure Stripe Tax itself.

## 8. What has already been verified (evidence)

Using a synthetically-signed webhook event (Stripe webhook signatures are pure local
HMAC — no live Stripe account is required to test this), against the real dev database:

| Scenario | Before | After | Result |
|---|---|---|---|
| `customer.subscription.created`, status `active`, metadata `plan_code=researcher` | `plan_code=free`, 50 credits | `plan_code=researcher`, 300 credits, `subscription_status=active` | Upgrade path confirmed correct |
| Duplicate delivery of the same event ID | — | `{"processed": false, "reason": "duplicate"}` | Idempotency guard confirmed working |
| Invalid signature | — | HTTP 400 | Signature enforcement confirmed working |
| `customer.subscription.updated`, status `canceled` | `plan_code=researcher` | `plan_code=free`, `subscription_status=expired` | Downgrade path confirmed correct |

**What remains** (cannot be verified without real credentials): a true browser-driven
Stripe Checkout redirect and real card payment, real Stripe-hosted billing portal
session, and real webhook delivery from Stripe's servers (vs. a synthetic local
signature) — these require STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and real price IDs
to be configured per §1–4 above, then a test-mode purchase using Stripe's test card
`4242 4242 4242 4242`.

## 9. Verification checklist for go-live

- [ ] Price IDs filled in for every paid plan (monthly + annual) and every credit pack
- [ ] `STRIPE_SECRET_KEY` set to a **live** key (not `sk_test_...`) for production
- [ ] `STRIPE_WEBHOOK_SECRET` set, matching the **live** webhook endpoint (test-mode and
      live-mode webhooks have different secrets in Stripe)
- [ ] Run one real test-mode purchase end-to-end (test keys) before flipping to live keys
- [ ] Confirm `python` package `stripe` is installed in the production environment (it is
      declared in `requirements.txt`; verify it's actually present in the deployed
      image/venv — this was found missing in at least one environment during
      verification and had to be installed manually)

## Missing Production Requirements

- Stripe Price IDs are currently all empty strings in `plans_catalogue.py` — this is the
  single blocking item preventing any live checkout, and is external configuration, not
  a code defect.
- No automated test in CI exercises the Stripe webhook path — consider adding a
  signed-synthetic-event test (as used for the manual verification above) to
  `backend/tests/` so regressions are caught automatically.
