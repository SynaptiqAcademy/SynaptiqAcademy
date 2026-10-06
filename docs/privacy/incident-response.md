# Incident response runbook

For security incidents and personal data breaches. Keep the live incident register **outside this repository**: incident details must not be committed.

## Roles

| Role | Who | Notes |
|---|---|---|
| Incident lead | The operator (until a team exists) | Decides severity and notifications |
| Technical responder | The operator or engineer on call | Containment and evidence |
| Legal adviser | Counsel | Breach assessment and notification wording |

Contact details go in the private register. A security mailbox **does not exist yet**. Don't publish one until it is created and monitored.

## 1. Detect and record (hour 0)

- Sources:
  - admin Security events view (`security_events`)
  - Railway logs (`railway logs`)
  - Atlas alerts
  - member or researcher reports
- Open a register entry: time noticed, reporter, what was observed, systems involved.
- Start the **72-hour clock** for a possible personal data breach from the moment of awareness (GDPR Art. 33).

## 2. Contain

- Revoke sessions:
  - for one account: the admin user tools, or `revoke_all_user_tokens`;
  - for everyone: rotate `JWT_SECRET`, which signs everyone out.
- Rotate exposed credentials: Atlas user, API keys (Anthropic, OpenAI, Resend, Stripe), `ORCID_CLIENT_SECRET`, `ORCID_STATE_SECRET`.
- Close registration if account creation is being abused (`platform_flags`).
- Disable a compromised feature with a feature flag or a hotfix deploy.
- Preserve evidence before cleaning up:
  - export the relevant logs;
  - note deployment ids (`railway deployment list`).

## 3. Assess (by hour 48)

- What personal data, how many people, which categories (see data-inventory.md)?
- Likelihood and severity of harm. Special-category or research-participant data raises severity.
- Is it a personal data breach? Is notification required?
  - to the supervisory authority: **ANSPDCP** for a Romanian controller, within 72 hours unless unlikely to result in a risk;
  - to the people affected: without undue delay, if high risk.
- **The controller is not yet identified (P0 blocker).** Notifications must name it.

## 4. Notify

- **Authority:** use ANSPDCP's breach notification form. If the facts aren't complete, notify in phases and record why.
- **People affected:** plain language. What happened, what data, likely consequences, what we did, what they should do, and who to contact.
- **Institutions:** if Synaptiq acts as their processor, notify them without undue delay under the DPA.

## 5. Recover and review

- Fix the root cause. Add a regression test.
- Write a post-incident review in the register:
  - timeline
  - cause
  - impact
  - actions
  - owner and due dates
- Record every incident, including ones not notified (Art. 33(5)).

## Incident register template

| Field | Entry |
|---|---|
| ID | INC-YYYY-NNN |
| Date/time aware | |
| Reported by | |
| Description | |
| Systems / data categories | |
| People affected (approx.) | |
| Personal data breach? (Y/N, reasoning) | |
| Risk level (none / risk / high risk) | |
| Authority notified? When, ref. | |
| People notified? When, how | |
| Containment actions | |
| Root cause | |
| Corrective actions, owner, due | |
| Closed | |
