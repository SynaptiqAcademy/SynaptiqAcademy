# Vercel Setup (Frontend — Optional Alternative)

**This is not the platform's current production deployment path.** The verified,
existing production path is Docker Compose + nginx serving the CRA build directly (see
[DEPLOYMENT.md](DEPLOYMENT.md) and `/deploy/nginx.conf`). This document exists because it
was requested as an alternative for teams who prefer a managed frontend host instead of
self-hosting the static build behind nginx. Nothing here is currently configured in the
repository — there is no `vercel.json`.

## Why you might use this

- You want the frontend on a managed CDN/edge network without operating nginx yourself.
- You keep the backend on the Docker Compose/Railway path and only move the frontend.

## Setup steps

1. **Create a Vercel project** from this repository, with the project **root directory
   set to `frontend/`** (the CRA app lives there, not at the repo root).
2. **Framework preset:** Create React App (Vercel auto-detects `react-scripts`/`craco`
   builds; if it doesn't detect correctly, set manually).
3. **Build command:** `npm run build` (this repo's `frontend/package.json` maps this to
   `craco build` — do not override to plain `react-scripts build`, since the project uses
   `craco.config.js` for path aliases/build customization).
4. **Output directory:** `build`
5. **Install command:** `npm ci` (or leave default — Vercel runs `npm install` if `ci`
   isn't specified; `npm ci` is preferred for reproducible installs from `package-lock.json`).
6. **Environment variables** (Project Settings → Environment Variables — set for
   Production, Preview, and Development as appropriate):

   | Variable | Value |
   |---|---|
   | `REACT_APP_BACKEND_URL` | Your API origin, e.g. `https://api.synaptiq.academy` |

   Remember: this is baked in at build time. Changing it requires a redeploy, not just an
   env var update — Vercel handles this automatically by rebuilding on every deploy.

7. **Custom domain:** Project Settings → Domains → add `synaptiq.academy` and
   `www.synaptiq.academy`. Vercel will show you the DNS records to create (either an `A`
   record to Vercel's anycast IP, or a `CNAME` for subdomains) — follow Vercel's
   on-screen instructions rather than the self-hosted records in
   [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md), which assume nginx on your own host.
8. **SPA routing:** Vercel auto-detects CRA's client-side routing and serves
   `index.html` for unmatched paths — no `vercel.json` rewrite rule should be needed for
   a standard CRA build, but if you encounter 404s on direct navigation to a deep route,
   add:
   ```json
   {
     "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
   }
   ```
9. **CORS:** the backend's `CORS_ORIGINS` must include your Vercel-served domain(s)
   exactly (including `https://` and any preview-deployment domains you want to allow).

## What stays on your own infrastructure

The backend (FastAPI), MongoDB Atlas, Redis, and background workers are **not** covered
by this document — Vercel is serverless-function-oriented and this backend is a
long-running stateful process (WebSockets, background job workers, a persistent worker
supervisor) that does not fit Vercel's serverless model. Keep the backend on the Docker
Compose path ([DEPLOYMENT.md](DEPLOYMENT.md)) or Railway ([RAILWAY_SETUP.md](RAILWAY_SETUP.md)).

## Missing Production Requirements

- No `vercel.json` exists in the repo — if you adopt this path, commit one so the config
  above is reproducible rather than only set in the Vercel dashboard.
