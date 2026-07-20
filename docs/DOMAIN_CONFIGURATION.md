# Domain Configuration

Production hostnames (hard-coded into `deploy/nginx.conf`, the CORS allowlist, OAuth
redirect URIs, and email templates):

- **`synaptiq.academy`** / **`www.synaptiq.academy`** — frontend (React SPA)
- **`api.synaptiq.academy`** — backend API

## 1. DNS

Create the records listed in [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md) before
requesting SSL certificates — `certbot`'s HTTP-01 challenge needs the domain to already
resolve to your server.

## 2. SSL / HTTPS

Certificates are issued via Let's Encrypt (`certbot`), covering all three hostnames on a
single certificate:

```bash
apt install certbot
certbot certonly --standalone \
  -d synaptiq.academy -d www.synaptiq.academy -d api.synaptiq.academy
```

(If nginx is already running and bound to port 80, use `certbot certonly --webroot -w
/var/www/certbot ...` instead — `nginx.conf` already serves the ACME challenge path from
that directory.)

Certificates land at `/etc/letsencrypt/live/synaptiq.academy/{fullchain,privkey}.pem` and
are mounted read-only into the `nginx` container by `docker-compose.prod.yml`.

**Renewal** is automatic via `deploy/synaptiq.cron` (checks twice daily; certbot only
actually renews within 30 days of expiry):
```cron
0 6,18 * * * certbot renew --quiet --deploy-hook "nginx -s reload"
```

## 3. nginx virtual hosts

`deploy/nginx.conf` defines:

1. An HTTP (port 80) server block for all three hostnames that (a) serves the ACME
   challenge path and (b) redirects everything else to HTTPS with a 301.
2. An HTTPS (port 443, HTTP/2) server block for `synaptiq.academy`/`www.synaptiq.academy`
   serving the built React SPA from `/var/www/html` with SPA fallback routing.
3. An HTTPS server block for `api.synaptiq.academy` reverse-proxying to the backend
   container, with distinct rate-limit zones for auth vs general API traffic and a
   dedicated WebSocket-upgrade location block for `/api/ws/`.

TLS settings: TLS 1.2/1.3 only, a modern cipher suite, OCSP stapling, HSTS
(`max-age=63072000; includeSubDomains; preload`), and standard security headers
(`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`).

## 4. Redirects

- HTTP → HTTPS: unconditional 301 for all three hostnames (except the ACME challenge path).
- `www.synaptiq.academy` is served identically to `synaptiq.academy` (same server block,
  same document root) rather than redirected — if you want a canonical `www` → apex (or
  apex → `www`) redirect, add it explicitly; it does not exist today.

## 5. Application-side domain configuration

Once DNS + SSL + nginx are live, set these and restart the backend:

| Variable | Value |
|---|---|
| `FRONTEND_BASE_URL` | `https://synaptiq.academy` |
| `BACKEND_BASE_URL` | `https://api.synaptiq.academy` |
| `CORS_ORIGINS` | `https://synaptiq.academy,https://www.synaptiq.academy` |
| `GOOGLE_REDIRECT_URI` | `https://api.synaptiq.academy/api/google/callback` (must also be registered in Google Cloud Console) |
| `ORCID_REDIRECT_URI` | `https://api.synaptiq.academy/api/orcid/callback` (must also be registered in ORCID Developer Tools) |

`FRONTEND_BASE_URL` and `BACKEND_BASE_URL` are read identically by both OAuth providers
and by the email system (`services/google_oauth.py`, `services/orcid/oauth.py`,
`services/email_service.py`) as of the 2026-07-19 configuration consistency pass — set
them once, above, and every consumer picks them up correctly. `APP_BASE_URL` still works
as a deprecated backward-compatible alias for `FRONTEND_BASE_URL` if you have it set from
an older deployment, but new deployments should use `FRONTEND_BASE_URL` directly. Full
detail: [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)'s "URLs" section.
`BASE_URL` and `PUBLIC_BASE_URL` are test-only and have no effect here regardless of what
you set them to.

And rebuild the frontend with:

| Variable | Value |
|---|---|
| `REACT_APP_BACKEND_URL` | `https://api.synaptiq.academy` |

Finally, update the Stripe webhook endpoint URL (dashboard → Developers → Webhooks) to
`https://api.synaptiq.academy/api/billing/webhook` — see [STRIPE_SETUP.md](STRIPE_SETUP.md).

## Missing Production Requirements

- No apex/`www` canonicalization redirect (see §4).
- No CAA DNS record documented — recommended to restrict which CAs may issue certs for
  this domain (see [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md)).
