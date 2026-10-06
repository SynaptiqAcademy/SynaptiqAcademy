# Account lifecycle: export and deletion

Code: `backend/services/account_lifecycle.py`. Endpoints: `GET /api/users/me/export` and `DELETE /api/users/me`. UI: Settings → Privacy. Tests: `backend/tests/test_account_lifecycle.py`.

## Deletion matrix

| Outcome | What | How |
|---|---|---|
| **DELETE** | AI conversations and messages, AI requests and memory, knowledge-base documents **and their embeddings**, saved searches, search history, research goals, SIE plans, team blueprints, meetings and notes the member owns, notifications, email preferences, connection and collaboration requests (both directions), invitations, institution/team/conversation memberships, followers and saved researchers, reputation, verification and trust records, own publication list, sessions, verification and reset tokens, trusted devices, MFA configuration, consent records linked to the account, email delivery log entries to the member's address | `delete_many` per collection (`_PRIVATE`) |
| **DELETE** | Projects, workspaces and manuscripts **nobody else has access to**, with their tasks, items, comments, versions and files (including stored bytes) | `_containers()` |
| **TRANSFER** | Shared projects and workspaces the member owned, and shared manuscripts they led | Ownership passes to the first other member or author; `ownership_transferred_at` is recorded |
| **ANONYMISE** | The account record | All fields removed except the id, plan, Stripe ids, Terms acceptance and creation date. Name becomes "Deleted user"; email becomes `deleted-<hash>@deleted.synaptiq.invalid`; profile set private; `status: deleted` |
| **KEPT FOR OTHERS** | Messages sent to others, comments and contributions in shared spaces, files uploaded to shared spaces | Left in place; the author id now shows "Deleted user" |
| **RETAIN** | Billing history, billing events, subscriptions, credit purchases and ledger | Linked only to the anonymised id. LEGAL REVIEW REQUIRED for the period |
| **RETAIN** | Security events, audit log | Until their retention period ends; deletion records hold the account id only |
| **PRESERVE** | Accounts with `legal_hold: true` | Self-deletion refused (409); handled manually |

### Safeguards

- **Confirmation:** the member types DELETE.
- **Recent authentication:**
  - accounts with a password must enter it;
  - ORCID/Google-only accounts must have signed in within the last 10 minutes (`last_successful_login`, now recorded for OAuth sign-ins too).
- **Blocked cases:** super admins can't self-delete. The sole administrator of an institution that has other members must hand over first.
- **Immediate effect:** refresh tokens are revoked. The cached user is invalidated. `get_current_user` rejects `status: deleted`, so a still-valid 15-minute access token stops working at once.
- **Backups** aren't rewritten. Data leaves them as they expire (OWNER VERIFICATION REQUIRED on the Atlas backup policy).

### Admin tools

- `POST /api/admin/users/{uid}/anonymize` and `DELETE /api/admin/users/{uid}/purge` (super admin only) still exist. The purge is a **hard erasure that also deletes billing records**. Use it only when counsel confirms nothing must be retained.
- Neither tool records the person's email in the audit log any more.

## Export

`build_export()` returns structured JSON (`format: synaptiq-account-export`, `format_version: 2`). It contains the profile, Terms acceptance, connections, AI conversations and messages, and the following, each capped at 2,000 records:
- projects, workspaces, manuscripts and publications
- files (metadata), messages sent
- AI requests, copilot conversations, knowledge documents
- saved searches, research goals, team blueprints, meetings and notes
- connection and collaboration requests, institution memberships
- notifications, consent records
- subscriptions, billing history and credit transactions

Removed recursively: password hashes, tokens and token hashes, secrets, MFA material, API keys, internal storage paths, IP hashes, embeddings and vectors.

Every export is recorded in the audit log (`user.data_export`, account id only).

Both `GET /api/users/me/export` and the older `GET /api/user/export-data` use the same builder.
