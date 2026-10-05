# Stripe setup — source of truth for TEST (sandbox) configuration

Synaptiq bills through Stripe **in TEST mode only** until the company/payment
setup is finalised. The same code runs in LIVE later; switching is configuration
only (§9). Commercial model: [`MONETIZATION.md`](MONETIZATION.md).

**Entitlements and credit amounts never come from Stripe.** Stripe tells Synaptiq
*that* a verified payment happened for a configured Price ID; the server-side
catalogue (`backend/plans_catalogue.py`) decides what that Price grants. Product
names, descriptions and metadata in Stripe are display text only.

## 1. Existing TEST prices (verified read-only on 2026-10-05)

| Internal product | Browser sends | Price ID (TEST) | Amount | Type | Grants (server-side) |
|---|---|---|---|---|---|
| PRO (`researcher`) | `pro` | `price_1UN7g6IjD6Qlwfj8erUQX6CW` | €9.99 | recurring, monthly | Pro, 200 credits / month |
| PRO_ADVANCED (`pro_researcher`) | `pro_advanced` | `price_1UN7lAIjD6Qlwfj815FCz1c8` | €29.99 | recurring, monthly | Pro Advanced, 750 credits / month |
| CREDIT_SMALL (`pack_100`) | `small` | `price_1UN7n5IjD6Qlwfj8AD9VIxYQ` | €4.99 | one-time | +100 purchased credits |
| CREDIT_PLUS (`pack_300`) | `plus` | `price_1UN7oOIjD6Qlwfj8MesEbcdS` | €11.99 | one-time | +300 purchased credits |
| CREDIT_MAX (`pack_750`) | `max` | `price_1UN7pOIjD6Qlwfj8b1gaDcRT` | €24.99 | one-time | +750 purchased credits |

All five are `livemode=false`, active, EUR, `tax_behavior=inclusive` (the shown
price includes VAT when tax is collected). Amounts and intervals are correct, so
**no new Price is needed**.

### 1a. Product text to correct (MANUAL — Dashboard, TEST mode)

The products' descriptions still describe the old allocations. Stripe lets you
edit a Product's name, description, metadata and marketing features **without
replacing its Prices** (a Price's amount/currency/interval are immutable; its
nickname and metadata are editable). Product catalog → product → Edit:

| Product | Current description says | Set description to |
|---|---|---|
| Synaptiq Pro | "Includes 300 AI credits per month" | "Research network, collaboration and AI tools for active researchers. Includes 200 AI credits per month. Early Access price." |
| Synaptiq Pro Advanced | "Includes 1,000 AI credits per month…" | "Everything in Pro plus advanced research intelligence, analytics and impact tools. Includes 750 AI credits per month." |
| Synaptiq AI Credits, Small | "250 additional AI credits" | "100 additional AI credits for Synaptiq. One-time purchase; requires an active Pro or Pro Advanced plan." |
| Synaptiq AI Credits, Plus | "750 additional AI credits" | "300 additional AI credits for Synaptiq. One-time purchase; requires an active Pro or Pro Advanced plan." |
| Synaptiq AI Credits, Max | "2,000 additional AI credits" | "750 additional AI credits for Synaptiq. One-time purchase; requires an active Pro or Pro Advanced plan." |

These texts appear on Stripe Checkout and invoices, so correct them before anyone
outside the team runs a test purchase.

## 2. Railway (backend) environment variables

Names only — never commit values. Server secrets belong on Railway only.

| Variable | Value (TEST) | Status on 2026-10-05 |
|---|---|---|
| `STRIPE_MODE` | `test` | not set (code defaults to `test`) |
| `STRIPE_SECRET_KEY` | `sk_test_…` or restricted `rk_test_…` | **set** (restricted test key) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` from §3 | **missing — required** |
| `STRIPE_PRICE_PRO_MONTHLY` | `price_1UN7g6IjD6Qlwfj8erUQX6CW` | **missing** |
| `STRIPE_PRICE_PRO_ADVANCED_MONTHLY` | `price_1UN7lAIjD6Qlwfj815FCz1c8` | **missing** |
| `STRIPE_PRICE_CREDITS_100` | `price_1UN7n5IjD6Qlwfj8AD9VIxYQ` | **missing** |
| `STRIPE_PRICE_CREDITS_300` | `price_1UN7oOIjD6Qlwfj8MesEbcdS` | **missing** |
| `STRIPE_PRICE_CREDITS_750` | `price_1UN7pOIjD6Qlwfj8b1gaDcRT` | **missing** |
| `FRONTEND_BASE_URL` | `https://synaptiq.academy` | set (Checkout/Portal redirects are built from it) |
| `STRIPE_TAX_ENABLED` | `0`/`1` — see §8 | not set |
| `STRIPE_PRICE_PRO_LEGACY_IDS` | comma list, only after a price change (§10) | — |

Safety: if `STRIPE_SECRET_KEY` doesn't match `STRIPE_MODE` (e.g. a `sk_live_` key
with `STRIPE_MODE=test`), Stripe is disabled (fail closed) and checkout returns 503.

Restricted-key permissions needed: Checkout Sessions (write), Customers (write),
Subscriptions (write — plan changes), Customer portal (write), Prices/Products
(read), Webhook signature verification needs no API permission.

**Vercel:** no Stripe variables. The frontend uses Stripe-hosted Checkout and
Portal URLs returned by the backend; no publishable key is needed.

## 3. Webhook endpoint (MANUAL — none exists in TEST yet)

Developers → Webhooks → Add endpoint (TEST mode):
`https://api.synaptiq.academy/api/billing/webhook` (the Railway backend host).

Enable exactly these events:

| Event | Used for |
|---|---|
| `checkout.session.completed` | credit-pack fulfilment (if paid); subscription checkout audit |
| `checkout.session.async_payment_succeeded` | credit packs paid by delayed methods |
| `customer.subscription.created` | initial activation (plan + first allocation) |
| `customer.subscription.updated` | upgrades/downgrades, cancel-at-period-end, `past_due` / `unpaid` |
| `customer.subscription.deleted` | subscription ended → Free |
| `invoice.paid` | renewal → monthly credit reset; clears `past_due`/`unpaid` |
| `invoice.payment_failed` | failed renewal → `past_due` grace + notification |
| `invoice.payment_action_required` | SCA/3DS notification |
| `charge.refunded` | credit-pack refund reversal |
| `charge.dispute.created` | logged for manual handling |

(`invoice.payment_succeeded` is also accepted but not needed when `invoice.paid`
is enabled.) Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.

Payload shapes of API version 2026-02-25 (clover) and older are both parsed
(subscription periods on items, invoice subscription under `parent`).

## 4. Customer Portal (MANUAL — no configuration exists in TEST yet)

Settings → Billing → Customer portal (TEST mode):
- Invoice history: on. Payment method update: on.
- Cancellation: on, **at end of billing period**.
- Subscription update: on, products **Synaptiq Pro** and **Synaptiq Pro Advanced**
  (monthly prices from §1); proration: "prorate and invoice immediately" for
  upgrades. Downgrades may be scheduled at period end.

The app opens it via `POST /api/billing/portal-session`; the return URL is built
server-side (`FRONTEND_BASE_URL/settings/billing`).

## 5. How billing state is applied (implemented)

- Checkout: browser sends `pro` / `pro_advanced` or `small` / `plus` / `max`
  only. Price IDs, credit amounts, prices and redirect URLs are resolved server-side;
  anything else is rejected (400). Existing Stripe customer is reused.
- An existing live subscription is **changed** (`Subscription.modify`, prorated),
  never duplicated. Two parallel first-time checkouts that both complete raise a
  `billing_alerts` `duplicate_subscription` record for manual resolution.
- Credit packs: Pro/Pro Advanced only (402 for Free); fulfilled only when the
  verified session is `paid`; granted once per Checkout Session (unique index).
  Promotion codes are disabled for packs.
- Webhook events: `PROCESSING → COMPLETED | FAILED`. Only `COMPLETED` blocks
  reprocessing; `FAILED` or stale `PROCESSING` (>10 min) is re-claimed atomically.
  Handlers are idempotent (cycle keys, session ids, status CAS).
- The success page polls the server's billing state (`/api/billing/subscription`,
  `/api/credits/purchases`) until the webhook has applied the change — the redirect
  itself grants nothing. `GET /api/billing/me` returns the authoritative summary.

## 6. TEST procedure

Prerequisites: §1a, §2, §3, §4 done; redeploy backend after setting variables.

1. Log in as a test Free user → `/pricing` → **Choose Pro** → card `4242 4242 4242 4242`,
   any future date, any CVC. Expect: back on `/payment/success`, then plan Pro, 200
   monthly credits, purchased credits unchanged.
2. `/ai-credits` → **Buy 100 credits** (Small) → pay → purchased +100. Buy Small
   again → +100 again (new session).
3. Pricing → **Choose Pro Advanced** while on Pro → plan changes in place (no
   second subscription in Dashboard → Customers), credits topped up to the cycle's
   750 total.
4. **Renewal**: Dashboard → Developers → Test clocks: create a clock, a customer on
   it, subscribe that customer to Pro via Checkout (or subscription in Dashboard
   with `metadata.user_id` set), advance the clock one month → `invoice.paid`
   (`subscription_cycle`) → subscription credits reset to 200, purchased unchanged.
   Without test clocks: admin `POST /api/admin/users/{uid}/billing-simulate
   {"action":"renew"}` exercises the same allocation code (TEST mode only).
5. **Failed payment**: card `4000 0000 0000 0341` (attaches, fails on charge) +
   advance the test clock → `invoice.payment_failed` → status `past_due` (access
   kept, no new credits). After retries are exhausted Stripe sets `unpaid` or
   cancels (per Dashboard → Billing → Subscriptions settings).
6. **Cancellation**: Portal → cancel → `cancel_at_period_end=true`, access kept;
   advance clock past period end → `customer.subscription.deleted` → Free; data and
   purchased credits kept.
7. **Duplicate webhook**: Dashboard → Webhooks → event → **Resend** → response
   `{"reason": "duplicate"}`, balances unchanged.
8. **Refund**: Dashboard → Payments → a pack payment → Refund (full) → unspent part
   of that pack removed; partial refunds are only logged (`billing_alerts`).

## 7. Migration and rollback

- Dry run: `cd backend && python scripts/migrate_monetization_v2.py` (report only).
- Apply/revert: `--apply` / `--revert` (Free users' legacy monthly credits → 0 with
  backup field `legacy_v1_credits_balance`). Nothing else is modified.
- Code rollback: revert the monetization commits and redeploy; collections added
  (`credit_reservations`, `ai_user_cost_counters`, `billing_alerts`) are additive.

## 8. VAT / Stripe Tax — decision required before LIVE

Stripe Tax shows as active on the account; prices are tax-inclusive. The app adds
`automatic_tax` to Checkout only when `STRIPE_TAX_ENABLED=1`. Before LIVE decide:
registrations (EU OSS?), inclusive vs exclusive pricing per market, B2B reverse
charge / tax-ID collection. Leave `STRIPE_TAX_ENABLED` unset in TEST unless you
are testing tax specifically. The account's default currency is RON; all Synaptiq
prices are EUR.

## 9. Switching TEST → LIVE (later)

1. In LIVE mode create the same five products/prices (amounts per §1) — TEST
   Price IDs do not exist in LIVE.
2. Create the LIVE webhook endpoint (§3) and Portal configuration (§4).
3. On Railway set `STRIPE_MODE=live`, the `sk_live_`/`rk_live_` key, the LIVE
   `whsec_`, and the five LIVE Price IDs. No code change.
4. Verify provider pricing (`AI_PROVIDER_PRICING_JSON`) and the VAT decision (§8).

## 10. Future €14.99 Pro price

No €14.99 Price exists — do not invent one. When it's introduced: create it on
the Pro product, set `STRIPE_PRICE_PRO_MONTHLY` to the new id (new subscribers)
and put the €9.99 id in `STRIPE_PRICE_PRO_LEGACY_IDS` so Early Access
subscribers keep mapping to Pro. Moving existing subscribers is a separate,
deliberate Stripe migration with the notice required by the Terms.
