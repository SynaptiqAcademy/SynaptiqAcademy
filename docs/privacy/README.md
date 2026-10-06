# Privacy, data protection and security: internal records

Internal working documents for the operator of Synaptiq and its legal adviser. They describe what the code does as of **6 October 2026** (Legal & Trust Phase 2). They are not legal advice and not public documents. Contracts, credentials and signed DPAs do **not** belong in this repository.

| Document | What it covers |
|---|---|
| [data-inventory.md](data-inventory.md) | Categories A–M of personal data, where they live, who sees them, classification, special-category and research-participant decision |
| [retention-schedule.md](retention-schedule.md) | Every retention period, its basis and how it's enforced (source of truth: `backend/retention_policy.py`) |
| [account-lifecycle.md](account-lifecycle.md) | Export and deletion: the DELETE / ANONYMISE / TRANSFER / RETAIN / PRESERVE matrix |
| [dsar-runbook.md](dsar-runbook.md) | Handling access, rectification, erasure, restriction, objection and portability requests |
| [processors-and-transfers.md](processors-and-transfers.md) | Processors, roles, DPA status, regions and transfer map |
| [ai-systems.md](ai-systems.md) | AI provider and route map, data sent, fallback, logging, retention, embeddings |
| [security-review.md](security-review.md) | Security review findings and fixes (not a penetration test); safe and unsafe Security-page claims |
| [incident-response.md](incident-response.md) | Incident response runbook and incident register template |
| [institutional-readiness.md](institutional-readiness.md) | Controller/processor matrix, DPA checklist, sub-processor list readiness, DPIA screening, research ethics boundary |

## Open blockers before commercial launch

| # | Blocker | Owner |
|---|---|---|
| P0 | **Controller not identified.** No legal entity, address or registration number is recorded anywhere. The Privacy Policy, Terms and GDPR notice say so plainly. Nothing may be invented. | Owner + counsel |
| P0 | **SECRET ROTATION REQUIRED.** A MongoDB Atlas credential for the production cluster (database user `admin_db_user`) was committed in `backend/test_atlas_connection.py` (commit 1524a0b, 20 July 2026). It isn't the credential production currently uses, but it stays in git history. Delete or rotate that Atlas user and review Atlas access logs. | Owner |
| P1 | **Mailboxes unverified.** `privacy@synaptiq.academy` and `contact@synaptiq.academy` are named in the documents. OWNER VERIFICATION REQUIRED: confirm both exist and are monitored. No `security@` address is published. | Owner |
| P1 | **MongoDB Atlas region unknown.** The connection string doesn't reveal it. Confirm it in the Atlas console; don't migrate in this phase. | Owner |
| P1 | **DPAs not confirmed.** For each processor, confirm a DPA is accepted (see processors-and-transfers.md). | Owner |
| P1 | **LEGAL REVIEW REQUIRED** periods: billing records, contact-form messages, billing audit records, consent proof, the 90-day audit period, the 30-day Terms change notice. | Counsel |
| P2 | Railway project also runs a `MongoDB` service with a volume and a `shadow-choice-backend` service. Production uses Atlas. Confirm what data the Railway MongoDB volume holds, and delete it if it is unused. | Owner |
