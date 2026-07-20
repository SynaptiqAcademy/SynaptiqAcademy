# DNS Configuration

Exact records to create at your DNS provider for `synaptiq.academy`. Replace
`<SERVER_IP>` with your production host's public IPv4 (and add an `AAAA` record if you
have IPv6). If you deploy the API and frontend on different hosts, point each `A` record
at the correct host.

| Type | Host | Value | TTL | Purpose |
|---|---|---|---|---|
| A | `@` (synaptiq.academy) | `<SERVER_IP>` | 300 (lower to 60 during migrations) | Frontend |
| A | `www` | `<SERVER_IP>` | 300 | Frontend (`www` alias) |
| A | `api` | `<SERVER_IP>` (or API host's IP, if separate) | 300 | Backend API |
| CAA | `@` | `0 issue "letsencrypt.org"` | 3600 | Restrict certificate issuance to Let's Encrypt (recommended, not currently documented in the codebase — add it) |
| TXT | `@` | SPF record for your email-sending domain (see [RESEND_SETUP.md](RESEND_SETUP.md)) | 3600 | Email deliverability |
| CNAME/TXT | per Resend instructions | DKIM records provided by Resend when you add the domain | 3600 | Email deliverability (DKIM signing) |
| TXT | `_dmarc` | DMARC policy, e.g. `v=DMARC1; p=quarantine; rua=mailto:contact@synaptiq.academy` | 3600 | Email deliverability / anti-spoofing |

## Notes

- **Single-host setup:** if backend and frontend run on the same VM (as the
  `docker-compose.prod.yml` in this repo assumes), all three `A` records point to the
  same IP — nginx distinguishes them by `Host` header via `server_name`.
- **Propagation:** before any planned migration, lower TTLs to 60s at least 24 hours in
  advance so the cutover is fast (see `deploy/RUNBOOK.md` → "Service migration").
- **Email records (SPF/DKIM/DMARC)** are provided by Resend when you verify your sending
  domain there — see [RESEND_SETUP.md](RESEND_SETUP.md) for the exact steps. Without
  these, transactional emails (verification, password reset, welcome) will land in spam
  or be rejected outright by receiving mail servers.
- **Verification after DNS changes:**
  ```bash
  dig +short synaptiq.academy
  dig +short api.synaptiq.academy
  dig +short TXT synaptiq.academy       # SPF
  dig +short TXT _dmarc.synaptiq.academy
  ```

## Missing Production Requirements

- No CAA record is currently documented anywhere in the repo — add one to reduce the
  blast radius of a compromised/unrelated CA issuing a cert for this domain.
- SPF/DKIM/DMARC records are provider-issued (Resend) and were not found hard-coded
  anywhere in this codebase — they must be created directly in your DNS provider's
  console per Resend's domain-verification instructions; there is nothing to grep for
  in-repo.
