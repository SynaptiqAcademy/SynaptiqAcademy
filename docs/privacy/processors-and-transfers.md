# Processors, roles and transfers

How each fact was established:
- **env** = production environment variable *names* (no values read);
- **code** = what the code sends;
- **live** = observed against production;
- **unverified** = needs the owner.

| Provider | Role | What it receives | Location | How known | DPA status |
|---|---|---|---|---|---|
| Railway | Processor | All API traffic and data in transit; application logs | **United States: `sfo` region** (from deployment manifest) | live (`railway status`) | OWNER VERIFICATION REQUIRED |
| MongoDB Atlas | Processor | The whole database | **Unknown**: the cluster host doesn't reveal the region. Confirm in Atlas; don't migrate in this phase | env | OWNER VERIFICATION REQUIRED |
| Railway "MongoDB" service (volume `mongodb-volume`) | Processor, if it holds data | Unknown; production `MONGODB_URI` points to Atlas | United States (`sfo`) | live | Confirm the volume's contents; delete it if unused |
| Railway "shadow-choice-backend" service | Unknown | Unknown | United States (`sfo`) | live | Confirm what it is |
| Vercel | Processor | Website requests (IP address, user agent) | Global edge network; project root `frontend` | live | OWNER VERIFICATION REQUIRED |
| Resend | Processor | Recipient email, subject and body of transactional emails. Since Phase 2 these carry **no research titles, notes or messages** | United States | env (`EMAIL_PROVIDER=resend`) | OWNER VERIFICATION REQUIRED |
| Anthropic | Processor | Prompts and context for AI features | United States | env + code | OWNER VERIFICATION REQUIRED (commercial terms; confirm DPA acceptance and retention) |
| OpenAI | Processor | Fallback when Claude is unavailable (`cloud_provider_fallbacks: anthropic → openai`); knowledge-base document chunks for embeddings (`text-embedding-3-small`, selected because no local model is reachable and `OPENAI_API_KEY` is set) | United States | env + code | OWNER VERIFICATION REQUIRED |
| PostHog | Processor | Named events and page views, IP address. **Only after consent**; autocapture and session recording off | United States (`us.i.posthog.com`) | code | OWNER VERIFICATION REQUIRED |
| Stripe | Independent controller (payments) | Nothing yet: online payments are not open; only a secret key is configured | EU and United States | env | Stripe's own terms |
| ORCID | Independent controller | OAuth sign-in and the member's ORCID record, at the member's request | International | code | n/a |
| OpenAlex, Crossref | Public data sources | Queries can include public identifiers (DOIs, ORCID iDs, author names) | International | code | n/a |

## Removed or not in use

- **Google Fonts: removed** in Phase 2. Fonts are self-hosted (`@fontsource` packages); no request leaves for Google. The CSP no longer allows `fonts.googleapis.com` or `fonts.gstatic.com`.
- **Google sign-in: not configured** (`/api/google/config` returns `configured: false`). The button is now hidden.
- **Object storage (S3-compatible): not configured** in production (no `S3_*` or `AWS_*` variables). File uploads therefore fail and no file bytes are stored.
- **Redis:** `REDIS_URL` points to a host that doesn't resolve; the app runs degraded without it.
- **Error tracking (e.g. Sentry):** none configured.

## Transfer map

All application data is processed in the United States (Railway `sfo`), whatever the Atlas region. Transfers from the EEA rely on each provider's data-processing terms: EU–US Data Privacy Framework certification where the provider is certified, otherwise Standard Contractual Clauses. **Confirm DPF certification and SCC incorporation per provider** before stating either publicly. The Privacy Policy states only that transfers rely on one or the other.
