# OpenAI / Anthropic Setup

Synaptiq's AI features route through an internal engine (`backend/services/ai/`) behind
an Enterprise AI Gateway (`backend/gateway/`) that enforces policy, budget, and audit
logging before any call reaches a cloud provider. See
[ARCHITECTURE.md](ARCHITECTURE.md) → "AI request routing" for the full chain
(Rule Engine → Local AI → Cloud AI).

## 1. Get API keys

- **Anthropic** (primary provider): console.anthropic.com → API Keys → create a key.
- **OpenAI** (fallback provider): platform.openai.com → API Keys → create a key.

Both are optional independently, but at least one should be set for AI features to work
at all — with neither set, AI endpoints fail gracefully with a user-facing error (no
crash), per `deploy/INCIDENT_RESPONSE.md`'s "AI Provider Outage" scenario.

## 2. Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Primary provider credential | — |
| `OPENAI_API_KEY` | Fallback provider credential | — |
| `AI_MATCHING_PROVIDER` | Which provider the matching/recommendation features prefer | `anthropic` |
| `AI_MATCHING_MODEL` | Model name for matching features | provider default |
| `AI_OPENAI_MODEL` | Explicit OpenAI model override (e.g. `gpt-4o`) | provider default |
| `AI_ANTHROPIC_TIMEOUT` / `AI_OPENAI_TIMEOUT` | Per-request timeout (seconds) | provider client default |
| `AI_ANTHROPIC_RETRIES` / `AI_OPENAI_RETRIES` | Retry count on transient failure | provider client default |
| `SMART_ROUTER_PREFERRED_PROVIDER` | Overrides the smart execution router's provider choice for complexity-routed requests | unset (auto) |

## 3. Fallback behavior

If the primary provider (Anthropic) errors or times out, the gateway automatically
retries against the fallback provider (OpenAI) before surfacing an error to the user.
This is automatic — no configuration is needed beyond having both keys set. To force a
single provider (e.g., during an Anthropic outage), set `AI_MATCHING_PROVIDER=openai` and
restart, per `deploy/INCIDENT_RESPONSE.md`.

## 4. Budget controls

| Variable | Purpose |
|---|---|
| `AI_HOURLY_BUDGET_USD` | Hourly spend cap enforced by the gateway |
| `AI_DAILY_BUDGET_USD` | Daily spend cap |
| `AI_MONTHLY_BUDGET_USD` | Monthly spend cap |

Cost tracking is recorded per-call in the `obs_cost` collection
(`backend/obs/cost.py`) — see [MONITORING.md](MONITORING.md) for how to review spend.

## 5. Caching

| Variable | Purpose | Default |
|---|---|---|
| `AI_CACHE_ENABLED` | Cache identical AI responses to avoid duplicate spend | on by default in most deployments — verify current default in `services/ai/` |
| `AI_CACHE_TTL_SECONDS` | Cache lifetime | — |

## 6. Local/self-hosted models (optional, off by default)

**Correction (found during documentation audit):** this codebase has two separate,
independently-configured local-model subsystems — they do not share environment
variables, and an earlier version of this document incorrectly mixed their variable
names together.

- **Local AI layer inside the main AI Gateway chain** (`backend/services/ai/engine/`,
  `backend/services/ai/layers/local_ai.py`) — this is what actually participates in the
  Rule → Local → Cloud fallback chain described in
  [ARCHITECTURE.md](ARCHITECTURE.md). Enable with `AI_LOCAL_ENABLED=1`, and configure
  `AI_LOCAL_URL` (default `http://localhost:11434`, i.e. Ollama), `AI_LOCAL_MODEL`
  (default `llama3.2`), and `AI_LOCAL_TIMEOUT` (default `120` seconds).
- **Standalone Local AI Engine** (`backend/services/local_ai/`) — a separate, more
  fully-featured local-model engine (multi-provider registry, response caching, health
  monitoring) exposed only through its own admin router at `/api/admin/local-ai/*`
  (`routers/admin_local_ai.py`), not wired into the main AI Gateway chain. It is
  configured independently via `LOCAL_AI_OLLAMA_URL` / `LOCAL_AI_VLLM_URL` /
  `LOCAL_AI_LM_STUDIO_URL` / `LOCAL_AI_OPENAI_COMPAT_URL` (+ `LOCAL_AI_OPENAI_COMPAT_KEY`)
  and the rest of the `LOCAL_AI_*` tuning knobs — there is no single "enable" flag for
  this one; it's available whenever its config is set and is invoked directly via its
  own admin endpoints.

Full variable list for both: [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md). Both
are advanced/optional — most production deployments should just use Anthropic + OpenAI.

## 7. Verification

```bash
curl https://api.synaptiq.academy/api/health
# Does not currently report AI provider connectivity directly — see below.

# Exercise a real AI endpoint (requires an authenticated session) and confirm a response
# comes back, or check obs_cost for a fresh entry after a real request.
```

## Missing Production Requirements

- `/api/health` does not report AI provider reachability — an expired/revoked API key
  will only surface when a user actually triggers an AI feature, not proactively.
  Consider a lightweight periodic connectivity check.
- No documented default for `AI_CACHE_ENABLED` was confirmed against current code at
  time of writing — verify the actual default in `backend/services/ai/` before assuming
  caching behavior in production.
