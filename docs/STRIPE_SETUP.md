# Stripe Setup

Stripe is integrated in code (`backend/services/stripe_service.py`,
`backend/routers/billing.py`). This document covers the external setup needed to
turn it on. **No Stripe product, price, key or webhook secret has been created by
the codebase** — every step below is a manual action in the Stripe Dashboard and
the hosting environment.

The commercial model is described in [`MONETIZATION.md`](MONETIZATION.md).

## 1. Products and prices to create (manual)

Create these in the Stripe Dashboard (Product Catalog → Add product). Use EUR.
Do **not** create annual prices — annual billing is not offered.

| Product | Price | Type | Env var that receives the price id |
|---|---|---|---|
| Synaptiq Pro | €9.99 / month | Recurring, monthly | `STRIPE_PRICE_PRO_MONTHLY` |
| Synaptiq Pro Advanced | €29.99 / month | Recurring, monthly | `STRIPE_PRICE_PRO_ADVANCED_MONTHLY` |
| 100 AI Credits | €4.99 | One-time | `STRIPE_PRICE_CREDITS_100` |
| 300 AI Credits | €11.99 | One-time | `STRIPE_PRICE_CREDITS_300` |
| 750 AI Credits | €24.99 | One-time | `STRIPE_PRICE_CREDITS_750` |

Pro is sold at the Early Access price (€9.99). The future price (€14.99) is shown
on the pricing page only; moving existing subscribers to a new price is a
separate, deliberate Stripe action (create a new price, migrate subscriptions,
give the notice required by the Terms).

If you change a pack's price in Stripe, also set `CREDIT_PACK_PRICES_JSON`
(e.g. `{"pack_100": 5.49}`) so the price shown in the app matches. The number of
credits granted always comes from `backend/plans_catalogue.py::CREDIT_PACKS`.

## 2. Environment variables (Railway backend) — names only

```
STRIPE_SECRET_KEY=sk_test_... / sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_ADVANCED_MONTHLY=price_...
STRIPE_PRICE_CREDITS_100=price_...
STRIPE_PRICE_CREDITS_300=price_...
STRIPE_PRICE_CREDITS_750=price_...
STRIPE_TAX_ENABLED=1            # optional; requires Stripe Tax activated first
```

Price ids are read from the environment by `plans_catalogue.py` at startup — never
hardcode them. Until they are set, checkout endpoints return `503
billing_not_configured`, the pricing page says paid plans aren't open yet, and
credit packs show "Coming soon". `services/prod_validator.py` warns at boot when
any of them is missing (`STRIPE_PLAN_PRICE_IDS`, `STRIPE_PACK_PRICE_IDS`).

## 3. Webhook endpoint

Dashboard → Developers → Webhooks → Add endpoint:
`https://api.synaptiq.academy/api/billing/webhook`

Subscribe to:
`checkout.session.completed`, `checkout.session.async_payment_succeeded`,
`customer.subscription.created`, `customer.subscription.updated`,
`customer.subscription.deleted`, `customer.subscription.trial_will_end`,
`invoice.paid` (or `invoice.payment_succeeded`), `invoice.payment_failed`,
`invoice.payment_action_required`, `charge.refunded`, `charge.dispute.created`.

Copy the signing secret into `STRIPE_WEBHOOK_SECRET`. Test-mode and live-mode
endpoints have different secrets.

## 4. Customer portal (recommended)

Dashboard → Settings → Billing → Customer portal:
- allow switching between **Pro** and **Pro Advanced** (both monthly prices);
- set cancellations to **at period end**;
- prorate upgrades immediately; downgrades may apply at period end.

Plan changes made in the portal arrive as `customer.subscription.updated` and are
handled exactly like in-app changes (the plan is resolved from the price id, not
from metadata).

## 5. How billing state is applied (implemented — verify, don't reconfigure)

- **Source of truth is the verified webhook.** The success redirect never grants
  anything; `/payment/success` polls server state until the webhook has applied it.
- **Event idempotency:** unique index on `billing_events.stripe_event_id`. If
  processing fails, the marker is deleted and the endpoint returns 500 so Stripe
  retries (a failed delivery is never mistaken for a duplicate).
- **Handler idempotency** (events can arrive in any order or be re-sent):
  subscription credits are allocated once per billing-cycle key
  `<subscription_id>:<period_start>`; pack credits once per Checkout Session
  (unique index on `credit_purchases.stripe_checkout_session_id`).
- **Renewal** (`invoice.paid`, `billing_reason=subscription_cycle`): subscription
  credits reset to the plan allowance; purchased credits unchanged.
- **Plan change** on an existing subscription modifies that subscription's price
  (`POST /api/billing/checkout-session` detects the live subscription) — a second
  subscription is never created.
- **Payment failure:** `past_due` is a grace state (access continues while Stripe
  retries). `unpaid` / `canceled` / `incomplete_expired` / `deleted` move the user to
  Free without deleting data.
- **Pack refund** (`charge.refunded`): the unspent part of that pack is removed.
- Signature verification is mandatory (400 on a missing/invalid signature).

Automated coverage: `backend/tests/test_monetization.py::TestWebhookDb` drives
synthetically-signed events through the real webhook handler against MongoDB
(subscription start, duplicate events, renewal reset, cycle replay, upgrade
top-up, cancellation, pack fulfilment, unpaid sessions, forged signatures).

## 6. Go-live checklist

- [ ] Products/prices from §1 created in **test mode**; env vars from §2 set on Railway
- [ ] Webhook endpoint (§3) created; `STRIPE_WEBHOOK_SECRET` set
- [ ] Test purchase with card `4242 4242 4242 4242`: Free → Pro; credits = 200
- [ ] Buy a credit pack in test mode; purchased credits +100
- [ ] Upgrade Pro → Pro Advanced in test mode; credits top up to the 750 cycle total
- [ ] Cancel in test mode; at period end the account is Free and data is intact
- [ ] Decide VAT handling (Stripe Tax or manual) before live mode
- [ ] Repeat §1–3 in **live mode** (live prices, live keys, live webhook secret)
- [ ] Confirm the `stripe` package is present in the deployed image (`requirements.txt` pins it)
