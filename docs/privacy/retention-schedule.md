# Retention schedule

**Source of truth:** `backend/retention_policy.py`. This table is generated from it; if they differ, the code wins and this file is stale. The Privacy Policy's "How long we keep data" table must match. `backend/tests/test_legal_truth.py` and `backend/tests/test_account_lifecycle.py` check that.

Enforcement:
- **ttl**: the document carries `expires_at` and a MongoDB TTL index deletes it.
- **purge**: `services/cleanup_service.enforce_retention_schedule()` runs at startup and then daily.
- **account**: the data is handled when the account is deleted (`services/account_lifecycle.py`).
- **none**: no automatic deletion yet.

A row with no period can be switched on without a code change by setting its environment variable (whole days):
- `RETENTION_CONTACT_INQUIRIES_DAYS`
- `RETENTION_AUDIT_BILLING_DAYS`
- `RETENTION_BILLING_DAYS`
- `RETENTION_CONSENT_ACCOUNT_DAYS`
- `RETENTION_EMAIL_LOG_DAYS`

**LEGAL REVIEW REQUIRED** on every row marked so. No period here is a legal conclusion. Each one restates a period already published or already in the code.

| Key | Data | Collection | Period | Enforcement | Basis | Legal review |
|---|---|---|---|---|---|---|
| `refresh_tokens` | Sign-in sessions | `refresh_tokens` | — | ttl | Token expiry (14 days, or the browser session) |  |
| `email_verifications` | Email verification links | `email_verifications` | — | ttl | Link expiry (24 hours) |  |
| `password_resets` | Password reset links | `password_resets` | — | ttl | Link expiry (30 minutes) |  |
| `security_events` | Security event logs (failed sign-ins, suspicious activity) | `security_events` | 365 days | ttl | Published in the Privacy Policy (1 year) | **REQUIRED** |
| `audit_admin` | Records of administrative and account actions | `audit_log` | 90 days | ttl | Existing audit-log period (AUTH-011) | **REQUIRED** |
| `audit_data_access` | Automatic data-access trail written by the database layer | `audit_log` | 90 days | purge | Same period as the audit log (AUTH-011) | **REQUIRED** |
| `audit_billing` | Billing, credit and subscription audit records | `audit_log` | — | none | Romanian tax and accounting law | **REQUIRED** |
| `consent_anonymous` | Cookie-consent records not linked to an account | `consent_records` | 730 days | purge | Existing cleanup period (2 years) | **REQUIRED** |
| `consent_account` | Cookie-consent records linked to an account | `consent_records` | — | account | Proof of consent while the account exists | **REQUIRED** |
| `contact_inquiries` | Messages sent through the contact form | `contact_inquiries` | — | none | Kept while needed to answer and follow up | **REQUIRED** |
| `email_log` | Delivery log of emails sent (recipient, subject, status) | `email_log` | 90 days | purge | Same period as the audit log (AUTH-011) | **REQUIRED** |
| `notifications_read` | Read in-app notifications | `notifications` | 90 days | purge | Existing cleanup period |  |
| `obs_logs` | Application warning and error logs | `obs_logs` | 7 days | purge | Observability log period (7 days) |  |
| `account` | Account and profile | `users` | — | account | While the account exists; anonymised at deletion |  |
| `ai_conversations` | AI conversations and results | `ai_conversations` | — | account | Until the member or the account deletes them |  |
| `billing` | Invoices, payments and subscriptions | `billing_history` | — | none | Romanian tax and accounting law | **REQUIRED** |

## Changes in Phase 2

- Security events: one writer used 180 days and another 365, while the Privacy Policy says 1 year. Both now use 365 days.
- Audit records of account deletion no longer store the deleted person's email. A daily job strips `original_email` from older records.
- The automatic data-access trail (`_source: "shim"`) had no expiry. It now follows the 90-day audit period.
- The email delivery log (recipient and subject) had no expiry. It now uses 90 days, and entries for a deleted account are removed at deletion.
- Application logs (`obs_logs`) had no expiry in deployed code. They now use 7 days.
- Cleanup now runs daily, not only at startup.

## Backups

MongoDB Atlas backup configuration (frequency, retention, point-in-time recovery) is **not visible from the codebase**. OWNER VERIFICATION REQUIRED in the Atlas console. Deleted data stays in backups until they expire. The Privacy Policy says only that deleted data disappears as backups are overwritten on the provider's cycle; it does not state a period.
