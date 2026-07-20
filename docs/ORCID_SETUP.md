# ORCID Setup

ORCID provides both an OAuth login/linking method and publication-import sync
(`backend/services/orcid/`, `backend/routers/orcid.py`).

## 1. Register an application

1. Production: https://orcid.org/developer-tools (requires a verified ORCID account).
   Sandbox (for testing, separate account/credentials): https://sandbox.orcid.org/developer-tools
2. Register a new API application. Provide:
   - **Redirect URI:** `https://api.synaptiq.academy/api/orcid/callback` — must match
     `ORCID_REDIRECT_URI` **exactly**, including scheme and trailing slash (or absence of
     one).
3. Copy the **Client ID** and **Client Secret**.

## 2. Environment variables

| Variable | Value |
|---|---|
| `ORCID_CLIENT_ID` | From step 1 |
| `ORCID_CLIENT_SECRET` | From step 1 |
| `ORCID_REDIRECT_URI` | `https://api.synaptiq.academy/api/orcid/callback` |
| `ORCID_BASE_URL` | `https://orcid.org` (production) or `https://sandbox.orcid.org` (sandbox) |
| `ORCID_API_BASE_URL` | `https://pub.orcid.org/v3.0` (production public API) |
| `ORCID_STATE_SECRET` | Any high-entropy random string — signs the OAuth `state` parameter to prevent CSRF on the callback; not provided by ORCID, generate it yourself. **If left unset, `services/orcid/oauth.py` silently falls back to `JWT_SECRET`, and if that's also unset, to a hardcoded literal string (`"synaptiq-orcid-state"`)** — the production validator (`services/prod_validator.py`) only warns (not errors) if this is unset, so this fallback can go unnoticed. Set it explicitly in production rather than relying on the `JWT_SECRET` fallback, to keep the two secrets' blast radius separate. Google OAuth follows the identical convention via `GOOGLE_STATE_SECRET` (added in the 2026-07-19 configuration consistency pass, to bring the two providers in line — see [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)). |
| `OPENALEX_MAILTO` | Your contact email, sent to OpenAlex's "polite pool" when enriching ORCID-imported publications with OpenAlex metadata |

`GET /api/orcid/status` in the running app reports which environment
(`sandbox`/`production`) is active based on `ORCID_BASE_URL`, so you can verify
configuration without reading `.env` directly.

## 3. Supported flows

- **Login/signup** (`mode=login`/`signup`): creates or matches a user by ORCID iD; if no
  matching account exists, a new one is created with no password (ORCID is the sole auth
  method for that account unless they later add a password or link Google).
- **Link** (`mode=link`): attaches an ORCID iD to an already-authenticated account.
  Blocked if that ORCID iD is already linked to a *different* account
  (`orcid_error=already_linked_to_other_account`).
- **Sync** (`POST /api/orcid/sync`): imports publications from the ORCID record,
  optionally enriched via OpenAlex (`POST /api/orcid/enrich-openalex`). A weekly
  background sync is also scheduled via the worker platform.

## 4. Email verification interaction

If `EMAIL_VERIFICATION_REQUIRED=1`, ORCID-only accounts (no email on file) are exempt
from the email-verification gate — their ORCID identity is treated as the trust anchor,
since they have no email to verify. Accounts that do have an email and it's unverified
are still blocked, same as any other signup path.

## 5. Frontend error/success feedback

Both connect-success and connect-failure redirects land on `/settings` with a query
string (`?orcid=connected` or `?orcid_error=<code>`); `OrcidSettings.jsx` reads these on
mount and shows a toast, then strips the query param from the URL.

## 6. Token security

Access/refresh tokens returned by ORCID are encrypted at rest
(`services/encryption_service.py`, keyed by `ENCRYPTION_KEY`) before being written to
MongoDB — never stored in plaintext.

## 7. Verification

```bash
curl https://api.synaptiq.academy/api/orcid/config
# {"authorization_url":null,"configured":true}  (once ORCID_CLIENT_ID/SECRET are set)
```

Then, in a browser, click "Continue with ORCID" on the login/settings page and confirm
the redirect lands on ORCID's real consent screen (`orcid.org/oauth/authorize` or
`sandbox.orcid.org/oauth/authorize` matching your configured `ORCID_BASE_URL`).

## Missing Production Requirements

- Both this app's redirect URI **and** whichever `ORCID_BASE_URL`/`ORCID_CLIENT_ID` pair
  you're using must point to the *same* environment (production vs. sandbox) — mixing a
  sandbox client ID with a production `ORCID_BASE_URL` (or vice versa) will fail
  authentication. There is no runtime check that catches this mismatch; verify manually
  before go-live.
