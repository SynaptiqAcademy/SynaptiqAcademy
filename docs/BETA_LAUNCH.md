# Beta Launch

This document defines a staged rollout plan distinct from full public launch (see
[GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md) for that gate). A beta should intentionally
run with a smaller blast radius while the team observes real usage.

## Why gate a beta separately from go-live

Several real subsystems are code-complete and verified but have never been exercised
against live external services (Stripe payments, a true production OAuth round-trip). A
beta with a small, informed user group lets you find integration issues that only appear
under real usage (real Stripe test-mode purchases, real email deliverability against
real inboxes, real concurrent WebSocket load) before opening to the public.

## Recommended beta scope

- **Private/invite-only** — use the existing invitation flow (`routers/collaboration_requests.py`
  / workspace invitations, or a simple allowlist check at registration) rather than open
  signup, so you control exactly who is exercising which code paths.
- **Feature flags** — `feature_flags` collection / admin panel supports runtime toggles;
  consider gating anything not yet in the "[Verified]" column of
  [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) behind a flag, defaulting off.
- **Payments in test mode** — configure Stripe with `sk_test_...` keys and test-mode
  price IDs for the beta (see [STRIPE_SETUP.md](STRIPE_SETUP.md)) so real money never
  moves during the beta, while still exercising the full checkout → webhook → plan-sync
  pipeline with Stripe's real test-card flow.
- **Reduced email volume** — a small, known beta cohort is exactly the population you
  want sending real email through before your Resend domain has built sending reputation
  (see [RESEND_SETUP.md](RESEND_SETUP.md)) at full public-launch volume.

## Beta entry checklist

- [ ] Every **[Verified]** item in [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) still
      holds (spot-check a few, don't just trust the checklist's last-known state)
- [ ] MongoDB Atlas, Redis, S3, Resend all configured (even if Stripe stays in test mode)
- [ ] `SENTRY_DSN` and uptime monitoring live **before** the first beta user signs up —
      you want to catch problems from monitoring, not from beta-user complaints
- [ ] A private feedback channel exists (email alias, Slack Connect channel, or in-app
      feedback widget) and is actually monitored
- [ ] Beta users have been told explicitly that Stripe is in test mode (if applicable) —
      don't let a beta user think they've been charged real money by mistake
- [ ] Rollback plan rehearsed at least once against this environment specifically (not
      just read — actually run [DEPLOYMENT.md](DEPLOYMENT.md)'s rollback steps once)

## During beta — what to watch closely

- Real Stripe test-mode webhook deliveries (confirm they match the synthetic-event
  test results already verified — see [STRIPE_SETUP.md](STRIPE_SETUP.md) §8)
- Real OAuth round-trips (Google, ORCID) from real user accounts, in production
  redirect-URI conditions
- Email deliverability — actual inbox placement, not just "the send succeeded" (check
  Resend's dashboard for bounce/complaint rates building up)
- WebSocket behavior under real multi-device, real-network-condition usage (this is
  exactly the live soak test flagged as unverified in [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md))
- Actual AI spend against `AI_DAILY_BUDGET_USD`/`AI_MONTHLY_BUDGET_USD` (see
  [OPENAI_ANTHROPIC_SETUP.md](OPENAI_ANTHROPIC_SETUP.md))

## Exiting beta → full launch

Do not proceed to [GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md) until:

- [ ] No unresolved P1/P2 incidents from the beta period (see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md))
- [ ] Stripe flipped from test keys to live keys, with the exact steps in
      [STRIPE_SETUP.md](STRIPE_SETUP.md) §9 followed in order
- [ ] Every item newly marked **[Verify]** in [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
      that beta usage was meant to exercise has actually been observed working, not just
      "no complaints received" (absence of complaints is not the same as verified working)

## Missing Production Requirements

- No formal feature-flag rollout percentage/cohort mechanism was confirmed beyond simple
  on/off flags — if you need percentage-based rollout (e.g., 10% of users), verify
  whether `feature_flags` supports that or if it needs to be added.
- No dedicated beta-feedback collection endpoint/widget was found in the codebase —
  decide on a channel (see "Beta entry checklist" above) before inviting anyone.
