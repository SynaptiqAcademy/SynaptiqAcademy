# Data inventory and classification

Classification: **Public** (shown to anyone), **Members** (visible to signed-in members), **Private** (the person and those they share with), **Restricted** (operator staff only, security or billing), **Secret** (credentials; never exported, never logged).

| | Category | Main collections | Source | Visible to | Class | Retention |
|---|---|---|---|---|---|---|
| A | Account and identity: name, email, password hash, sign-in method, ORCID iD, Google id | `users` | Member, ORCID, Google | Member; email never public | Private / Secret (hash, tokens) | While the account exists; anonymised at deletion |
| B | Academic Passport: affiliation, roles, research areas, publications, biography, links | `users`, `publications`, `public_profiles` | Member, ORCID, OpenAlex/Crossref metadata | Members unless profile is private | Members | While the account exists |
| C | Research content: projects, workspaces, manuscripts, notes, team blueprints, research goals | `projects`, `workspaces`, `workspace_items`, `manuscripts`, `meeting_notes`, `team_blueprints`, `user_research_goals` | Member | Owner and invited collaborators | Private | Until deleted; see account-lifecycle.md |
| D | Collaboration and messaging: connections, requests, invitations, messages | `connection_requests`, `collaboration_requests`, `messages`, `conversations` | Members | Participants | Private | Until deleted; sent messages stay with recipients |
| E | Institutional membership and verification | `institution_memberships`, `institutions`, `verification_*` | Member, institution admins | Institution admins of that institution | Private | While membership exists |
| F | AI interactions: prompts, conversations, outputs, knowledge-base documents and embeddings | `ai_conversations`, `ai_messages`, `ai_requests`, `copilot_conversations`, `knowledge_documents`, `knowledge_chunks` | Member, AI providers | Member | Private | Until the member or the account deletes them |
| G | Files | `files` (metadata); bytes in S3-compatible storage | Member | Members of the parent space | Private | Until deleted (bytes now deleted too). **Production has no object storage configured**, so uploads fail and no bytes are stored. |
| H | Billing: plan, subscription, invoices, credit ledger | `subscriptions`, `billing_history`, `credit_*`, `billing_events` | Member, Stripe | Member; staff | Restricted | As accounting law requires (LEGAL REVIEW REQUIRED). Online payments are not open. |
| I | Security and audit logs | `security_events`, `audit_log`, `obs_logs` | System | Staff | Restricted | 1 year / 90 days / 7 days |
| J | Consent and legal acceptance: cookie choice, Terms and Privacy version accepted | `consent_records`, `users.terms_*` | Member | Staff | Restricted | 2 years (not linked to an account) / with the account |
| K | Communications: email delivery log, notifications, email preferences | `email_log`, `notifications`, `email_preferences` | System | Member (notifications); staff | Private / Restricted | 90 days |
| L | Analytics and device: PostHog events (with consent only), IP addresses in request logs, user agent | PostHog; `security_events`; `obs_logs` | Browser | Staff | Restricted | PostHog per its settings; logs as above |
| M | Contact and support: contact-form messages, support tickets | `contact_inquiries`, `support_tickets` | Anyone | Staff | Restricted | No period set (LEGAL REVIEW REQUIRED) |

## Special-category and research-participant data: decision

- **Synaptiq asks for no special-category data about members.** No profile field records health, ethnicity, religion, political opinion, sexuality, disability, trade-union membership, biometrics or date of birth. A code scan found these words only as research vocabulary (taxonomies, topic matching).
- **Members can upload anything** to manuscripts, files, notes and AI prompts, including research data about participants. The product can't detect this.
- **Decision (high-risk data):** Synaptiq is **not designed or offered for identifiable research-participant data or special-category data.** The Terms ("Research content and ethics") forbid uploading identifiable participant data or special-category data without a lawful basis and permission. Synaptiq offers no ethics approval, no participant consent tooling and no data-residency guarantee. Before offering institutional plans that would host such data, carry out a DPIA (see institutional-readiness.md) and confirm the database region.
- Public pages do not invite health, clinical or patient data uploads.

## Public visibility and discovery

- **Member controls.** Network → Network Settings stores "Profile visibility" and "Show my profile in researcher discovery" in `network_settings`. Since 6 October 2026 (legal consolidation), saving them also sets `users.profile_visibility`, which every discovery surface filters on:
  - `/discover`
  - the researcher directory
  - member search
  - the public Passport

  "Private" or discovery off becomes `private` (`services/discovery_preferences.py`). Previously the choice had no effect on those surfaces.
- **A daily sync** applies existing saved choices (`cleanup_service`).
- **The "Network" visibility option** is honoured by the network discovery engine only. The other surfaces treat it as visible to members. Product follow-up.
- **The public Passport (`/researcher/:slug`) is visible without signing in.**
  - Academic sections (publications, impact, teaching, reputation, timeline) are public by default.
  - **Projects, grants (including grant applications), collaborations and the email address are private unless the member turns them on** (`services/public_profiles/visibility.py`).
  - Before this change, all sections defaulted to public, and the page was created automatically when a member first opened their profile.
  - Pages whose settings were never changed were moved to the new defaults; members' own choices are kept.
  - Only projects marked `visibility: public` are listed.
  - A member who chose Private has no public page (404 for everyone else).
- **The researcher directory** (`/api/profiles/directory`) is unauthenticated. It shows name, photo, institution, department, country, career stage and research interests, and excludes members who chose Private or turned discovery off.
- **Deleted accounts** are set to private and marked `deleted`. Their access tokens stop working at once (`auth_utils.get_current_user`).
- **Search engines:** `robots.txt` disallows everything except marketing and legal pages. Researcher pages aren't offered to search engines.
