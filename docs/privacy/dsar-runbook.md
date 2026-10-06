# Data subject request (DSAR) runbook

Requests arrive at the privacy mailbox named in the Privacy Policy (OWNER VERIFICATION REQUIRED: confirm the mailbox exists and is monitored), or in-product.

## Every request

1. **Log it** in the request register (a private spreadsheet outside this repository):
   - date received
   - requester
   - right(s) invoked
   - identity check
   - due date (one month from receipt)
   - extension (up to two further months, notified within the first month)
   - outcome and date closed
2. **Verify identity** proportionately. Reply from the account's email address, or ask the person to sign in and use the self-service tool. Never send data to an address not on the account.
3. **Reply within one month.** Requests are free unless manifestly unfounded or excessive.

## By right

| Right | Self-service | Manual steps | Gaps |
|---|---|---|---|
| Access / portability (Art. 15, 20) | Settings → Privacy → Export my data | For data outside the export (security events, audit records, contact-form messages, PostHog events), query by account id and email and send a summary | Export caps each section at 2,000 records; for bigger accounts, run `build_export` with a higher limit from a maintenance shell |
| Rectification (Art. 16) | Passport and settings edit almost every profile field | Correct email address or institution verification on request (admin user tools) | None known |
| Erasure (Art. 17) | Settings → Privacy → Delete my account | If the person can't sign in: verify identity, then use the admin anonymise tool. Use purge only on counsel's advice (it deletes billing records) | Contact-form messages aren't covered by account deletion: delete them by email address on request |
| Restriction (Art. 18) | Profile can be made private | Set `status: suspended` to freeze processing while a dispute is checked; record why | No dedicated "restricted" flag; suspension also blocks sign-in, so tell the person |
| Objection (Art. 21) | Make profile private (removes the member from discovery and suggestions); withdraw analytics consent (footer "Cookie settings") | Stop any other legitimate-interest processing named in the objection | No per-feature objection switches beyond these |
| Withdraw consent | Footer "Cookie settings" or Settings → Privacy | — | — |

## Records to keep

Keep the request log entry and the reply for the limitation period counsel advises (**LEGAL REVIEW REQUIRED**). Don't keep copies of exported data.
