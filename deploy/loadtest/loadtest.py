"""Synaptiq staging load test — logged-in researchers browsing the product.

Each virtual user signs in once, then loops through a weighted mix of the
requests the app makes for real pages: session check, Today feed, member
search (discovery), project list and project detail, notifications, and
(optionally, --writes) creating then deleting a project. No AI endpoint is
called: AI work is measured separately against a stub provider (see
docs/PRODUCTION_READINESS_AUDIT.md, section 5) so no paid model is ever used.

Never point this at production.

Usage:
  python deploy/loadtest/loadtest.py --base https://staging-api.example \\
      --users users.csv --vus 50 --duration 300 --ramp 60 [--writes] \\
      [--pid <uvicorn/gunicorn pid, local only>] [--mongo-uri mongodb://...]

users.csv: email,password per line (test accounts on staging only). Virtual
users are spread across the accounts; sign-ins are spaced to respect the
5/minute auth rate limit unless --login-gap 0 is passed (staging with
RATE_LIMIT_AUTH raised).

Output: per-endpoint count, error rate, p50/p95/p99 latency, overall
requests/s, and, when --pid / --mongo-uri are given, backend CPU and RSS
samples and MongoDB operation counters for the run.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import random
import statistics
import subprocess
import time
from collections import defaultdict

import httpx

ENDPOINTS = [
    # (name, weight, method, path, params)
    ("auth_me",        10, "GET", "/api/auth/me", None),
    ("today_feed",     20, "GET", "/api/discover/feed", None),
    ("member_search",  25, "GET", "/api/network/people", {"page": 1, "limit": 12}),
    ("member_search_q", 10, "GET", "/api/network/people", {"page": 1, "limit": 12, "q": "learning"}),
    ("projects_list",  15, "GET", "/api/projects", None),
    ("project_detail", 10, "GET", "/api/projects/{project_id}", None),
    ("notifications",  10, "GET", "/api/notifications", None),
]

lat: dict[str, list[float]] = defaultdict(list)
errs: dict[str, int] = defaultdict(int)
codes: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))


def record(name: str, t0: float, status: int | None):
    lat[name].append((time.perf_counter() - t0) * 1000)
    if status is None or status >= 400:
        errs[name] += 1
    codes[name][status or 0] += 1


async def timed(client, name, method, url, **kw):
    t0 = time.perf_counter()
    try:
        r = await client.request(method, url, **kw)
        record(name, t0, r.status_code)
        return r
    except Exception:
        record(name, t0, None)
        return None


async def vu(i, args, account, stop_at, start_delay):
    await asyncio.sleep(start_delay)
    async with httpx.AsyncClient(base_url=args.base, timeout=30, follow_redirects=False) as c:
        r = await timed(c, "login", "POST", "/api/auth/login",
                        json={"email": account[0], "password": account[1]})
        if r is None or r.status_code != 200:
            return
        csrf = (r.json() or {}).get("csrf_token") or c.cookies.get("csrf_token")
        hdr = {"X-CSRF-Token": csrf} if csrf else {}
        project_ids: list[str] = []
        pr = await timed(c, "projects_list", "GET", "/api/projects")
        if pr is not None and pr.status_code == 200:
            body = pr.json()
            items = body if isinstance(body, list) else body.get("projects") or body.get("items") or []
            project_ids = [p.get("id") or p.get("_id") for p in items if isinstance(p, dict)]
        weights = [e[1] for e in ENDPOINTS]
        while time.time() < stop_at:
            name, _, method, path, params = random.choices(ENDPOINTS, weights)[0]
            if "{project_id}" in path:
                if not project_ids:
                    continue
                path = path.format(project_id=random.choice(project_ids))
            await timed(c, name, method, path, params=params)
            if args.writes and random.random() < 0.03:
                cr = await timed(c, "project_create", "POST", "/api/projects", headers=hdr,
                                 json={"title": f"loadtest {i} {time.time():.0f}", "description": "load test"})
                if cr is not None and cr.status_code in (200, 201):
                    pid = (cr.json() or {}).get("id") or (cr.json() or {}).get("_id")
                    if pid:
                        await timed(c, "project_delete", "DELETE", f"/api/projects/{pid}", headers=hdr)
            await asyncio.sleep(random.uniform(args.think_min, args.think_max))


def sample_proc(pid: int):
    """CPU% and RSS (MB) of a local process tree, via ps (no extra deps)."""
    try:
        out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,%cpu=,rss="], capture_output=True, text=True).stdout
    except Exception:
        return None
    rows = [l.split() for l in out.splitlines() if l.strip()]
    tree, frontier = {str(pid)}, {str(pid)}
    while frontier:
        frontier = {r[0] for r in rows if r[1] in frontier} - tree
        tree |= frontier
    sel = [r for r in rows if r[0] in tree]
    return sum(float(r[2]) for r in sel), sum(int(r[3]) for r in sel) / 1024


async def sampler(args, stop_at, samples):
    while time.time() < stop_at:
        s = sample_proc(args.pid)
        if s:
            samples.append(s)
        await asyncio.sleep(2)


def mongo_ops(uri):
    try:
        from pymongo import MongoClient
        st = MongoClient(uri, serverSelectionTimeoutMS=3000).admin.command("serverStatus")
        return dict(st["opcounters"]), st["connections"]["current"]
    except Exception as exc:
        return {"error": str(exc)[:80]}, None


def pct(v, p):
    if not v:
        return 0.0
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--users", required=True)
    ap.add_argument("--vus", type=int, default=20)
    ap.add_argument("--duration", type=int, default=120)
    ap.add_argument("--ramp", type=int, default=30)
    ap.add_argument("--think-min", type=float, default=0.5)
    ap.add_argument("--think-max", type=float, default=2.0)
    ap.add_argument("--login-gap", type=float, default=12.5, help="seconds between sign-ins per account")
    ap.add_argument("--writes", action="store_true")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--mongo-uri")
    args = ap.parse_args()
    if "synaptiq.academy" in args.base or "synaptiqacademy-production" in args.base:
        raise SystemExit("Refusing to load-test production.")

    accounts = [(r[0].strip(), r[1].strip()) for r in csv.reader(open(args.users)) if len(r) >= 2]
    m0 = mongo_ops(args.mongo_uri) if args.mongo_uri else None
    t_start = time.time()
    per_account = defaultdict(int)
    tasks = []
    for i in range(args.vus):
        acc = accounts[i % len(accounts)]
        n = per_account[acc[0]]
        per_account[acc[0]] += 1
        delay = max(i * args.ramp / max(args.vus, 1), n * args.login_gap)
        tasks.append((acc, delay))
    last_start = max(d for _, d in tasks)
    stop_at = t_start + last_start + args.duration
    samples: list = []
    coros = [vu(i, args, acc, stop_at, d) for i, (acc, d) in enumerate(tasks)]
    if args.pid:
        coros.append(sampler(args, stop_at, samples))
    await asyncio.gather(*coros)
    elapsed = time.time() - t_start
    m1 = mongo_ops(args.mongo_uri) if args.mongo_uri else None

    total = sum(len(v) for v in lat.values())
    total_err = sum(errs.values())
    print(f"\nVUs={args.vus} steady={args.duration}s elapsed={elapsed:.0f}s requests={total} "
          f"rps={total / elapsed:.1f} errors={total_err} ({100 * total_err / max(total, 1):.2f}%)")
    print(f"{'endpoint':18} {'n':>6} {'err%':>6} {'p50':>7} {'p95':>7} {'p99':>7}  status codes")
    for name in sorted(lat):
        v = lat[name]
        print(f"{name:18} {len(v):6d} {100 * errs[name] / len(v):6.2f} {pct(v, 50):7.0f} {pct(v, 95):7.0f} "
              f"{pct(v, 99):7.0f}  {dict(codes[name])}")
    allv = [x for v in lat.values() for x in v]
    print(f"{'ALL':18} {len(allv):6d} {100 * total_err / max(total, 1):6.2f} {pct(allv, 50):7.0f} "
          f"{pct(allv, 95):7.0f} {pct(allv, 99):7.0f}")
    if samples:
        cpu = [s[0] for s in samples]
        rss = [s[1] for s in samples]
        print(f"backend CPU% avg={statistics.mean(cpu):.0f} max={max(cpu):.0f} (100 = one core); "
              f"RSS MB avg={statistics.mean(rss):.0f} max={max(rss):.0f}")
    if m0 and m1 and "error" not in m0[0]:
        d = {k: m1[0][k] - m0[0].get(k, 0) for k in m1[0]}
        print(f"MongoDB ops during run: {d}; connections now={m1[1]}")


if __name__ == "__main__":
    asyncio.run(main())
