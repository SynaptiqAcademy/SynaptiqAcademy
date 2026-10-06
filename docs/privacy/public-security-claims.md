# Public security claims: evidence registry

Every security statement on `/security` (and security wording elsewhere on public pages) must appear here as **Publish: YES**. Last verified **6 October 2026** against code at `ac8ade0` and production configuration (environment-variable names only, public HTTP responses, Railway deployment metadata). This is a code and configuration review, **not a penetration test**.

## Published (verified)

| Claim (public wording, paraphrased) | Evidence | Publish |
|---|---|---|
| Connections are served over HTTPS; plain HTTP is redirected | `curl -I http://www.synaptiq.academy` → 308 to https; API → 301; HSTS on site and API | YES |
| Passwords are stored with one-way hashing, never as readable text | `auth_utils.hash_password` (bcrypt with per-password salt) | YES (no parameters) |
| Sign-in sessions use short-lived cookies that page scripts can't read; forms are protected against cross-site requests | `auth_utils.set_auth_cookies`: HttpOnly; Secure in production (`COOKIE_SECURE=1`); CSRF middleware | YES (no lifetimes, names or algorithms) |
| Repeated failed sign-ins lock the account temporarily | `routers/auth.py` lockout thresholds | YES |
| Sign in with email and password, or ORCID; Google is not offered | `/api/google/config` → `configured:false`; ORCID configured; buttons only for configured providers | YES |
| Creating an account by any route requires 18+ and Terms acceptance | `routers/orcid.py`, `routers/google_auth.py` signed acceptance; `routers/auth.py` | YES |
| Deleting an account needs the password or a recent sign-in, and ends every session immediately | `routers/users.delete_my_account`; `get_current_user` rejects deleted accounts | YES |
| Access is checked on the server for every request | Route dependencies (`get_current_user`, `require_*`) | YES |
| Administrative functions require an administrator account | `zt/middleware.admin_gate` for all `/api/admin`; `tests/test_admin_surface_gate.py` | YES (no route names) |
| Institution features need approved membership, not a plan, a profile affiliation or an ORCID affiliation | `services/permissions.require_institution_member` / `get_my_institution_context` (approved membership only) | YES |
| Projects, workspaces and manuscripts are available to their members; files to members of the space they belong to | `routers/projects.py` membership checks; `routers/files._check_access` | YES |
| Public projects are visible to signed-in members; they appear on a public profile only if that section is on | `routers/projects.py` (`visibility: public`); `services/public_profiles` | YES |
| A private profile has no public page; projects, grants, collaborations and email are off the public page unless turned on | `routers/public_profiles` (`_owner_chose_private`, `DEFAULT_VISIBILITY`); migration `public_visibility_v2` | YES |
| Turning off discovery removes a member from discovery and the directory | `services/discovery_preferences`; directory/discover filters | YES |
| Blocking someone hides each from the other in discovery and stops their requests | `routers/collaboration_requests` reciprocal blocking; `discovery_engine._discovery_exclusions` | YES |
| Messages are stored on Synaptiq's servers and are not end-to-end encrypted | Privacy Policy; messaging stores plaintext | YES (as a limitation) |
| Deleting a file also deletes the stored file | `routers/files.delete_file` → `storage_service.delete_object` | YES. Note: production has no object storage configured (no `S3_*`/`AWS_*`), so uploads are currently unavailable |
| AI features send the material for the request to Anthropic, and to OpenAI as fallback and for knowledge-base search embeddings, in the US | `services/smart_router/config.py` fallbacks; `services/knowledge/embeddings/service.py` | YES |
| AI usage records keep feature, duration and credits, not the request text; conversations are kept in the account until deleted | `ai_requests` inserts (metadata fields); Privacy Policy | YES |
| Notification emails don't carry manuscript or project titles, notes or messages | `services/email/templates/*`; test | YES |
| Analytics is off until allowed; autocapture and session recording are off; it can be withdrawn | `public/analytics-init.js`; production consent regression (`ac8ade0`) | YES |
| Typefaces are served by Synaptiq; no font requests to third parties | `@fontsource`; CSP; network QA | YES |
| Security and administrative events are logged and kept for set periods | `security_events` (1 year), `audit_log` (90 days), `retention_policy.py` | YES (link Privacy for periods) |
| An internal incident-response process exists, including assessing breach notification | `docs/privacy/incident-response.md` | YES (no runbook detail, no timelines) |
| Synaptiq doesn't claim SOC 2, ISO 27001 or HIPAA compliance; GDPR isn't presented as a certification | Absence of any certification | YES |
| Not designed for identifiable patient or participant data | Terms "Research content and ethics"; Data Protection; data-inventory decision | YES |
| Suspected vulnerabilities can be reported through the contact form (Security topic) | `routers/contact.py`: "security" topic; every submission stored | YES, qualified. OWNER ACTION: confirm the notification inbox (`ADMIN_EMAIL`, default admin@) is monitored; there is no admin screen for stored inquiries |

## Not published

| Claim | Why not |
|---|---|
| Encryption at rest (AES-256, databases, backups, files) | Atlas configuration not verified; object storage not configured |
| TLS 1.3 only | Not verified as enforced |
| Backups: frequency, point-in-time recovery, retention, encryption, location | Atlas backup policy unverified (OWNER ACTION) |
| Data location for the database / EU hosting / EU residency | Atlas region unverified; app servers in US (`sfo`) |
| All providers under DPAs; SCCs/DPF for all transfers | DPA status unconfirmed (OWNER ACTION) |
| Rate limiting on all endpoints / resilience | Behaviour with Redis unavailable not audited |
| All input/search safely handled | `routers/workspaces.py:918` raw regex (owner in-progress file) |
| Every member API route audited for authorization | Only `/api/admin` probed systematically |
| 24/7 monitoring, real-time threat detection, SOC | None exists |
| Response or notification times (48 h, 72 h to users) | Not operationally established; GDPR duties depend on risk |
| security@ mailbox, security.txt contact | No verified security mailbox |
| Penetration testing, bug bounty | None |
| Staff can't access data | False: administrators can, under logging |
| SSO/SAML, SCIM, dedicated tenancy, customer-managed keys, security SLA | Not implemented |
| Institutional DPA ready | Not ready (see institutional-readiness.md) |
