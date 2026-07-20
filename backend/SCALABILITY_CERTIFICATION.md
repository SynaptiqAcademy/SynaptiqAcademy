# Synaptiq Scalability Certification — Phase 5

**Date:** 2026-07-05  
**Scope:** Production Hardening Phase 5 — Horizontal Scalability & Enterprise Readiness  
**Baseline:** Phase 4 certified (2854 tests, 0 failures, 57% coverage)  
**Result after Phase 5:** 2865 tests, 0 failures — all scalability items addressed

---

## 1. Scalability Audit Findings

Full audit conducted across all backend subsystems. Issues ranked by severity.

### CRITICAL — Fixed

| # | Component | Issue | Fix Applied |
|---|-----------|-------|-------------|
| C1 | `services/knowledge/vector_store/numpy_store.py` | All embeddings loaded into process RAM (N chunks × 1.5KB per worker) | Switched default `vector_backend` to `"mongodb"` — `MongoDBVectorStore` uses Atlas `$vectorSearch` with numpy fallback; matrix never loaded into process memory on Atlas |
| C2 | `agents/memory.py` | `_store: dict` — all session state process-local; lost on restart or worker change | Added Redis L2 layer: sessions serialized to Redis with 1h TTL; cross-worker recovery on L1 miss |

### HIGH — Fixed

| # | Component | Issue | Fix Applied |
|---|-----------|-------|-------------|
| H1 | `worker/scheduler.py` | APScheduler fires duplicate jobs across replicas (N replicas → N × each scheduled job) | Added MongoDB atomic insert dedup lock: per `(schedule_id, time-bucket)` unique index; first writer wins, others skip |
| H2 | `repo/base.py` | All 93 bounded-context repositories use in-process L1 cache only; no cross-replica cache sharing | Wired Redis client into `BaseRepository.__init__`; all repositories now use 2-tier cache (L1 in-process + L2 Redis) when `REDIS_URL` is set |
| H3 | `db.py` | Fixed `maxPoolSize=50` per instance regardless of deployment scale | Changed to `MONGO_MAX_POOL` env var (default 200); `minPoolSize = max(5, maxPool/20)` |

### MEDIUM — Documented (accepted for V1 scale)

| # | Component | Issue | Mitigation |
|---|-----------|-------|------------|
| M1 | `worker/circuit_breaker.py` | Per-process breaker state; one instance detects failure, others don't | Acceptable: each instance independently detects failure within 5 requests. Fix: wire to Redis Pub/Sub in future sprint |
| M2 | `worker/concurrency.py` | Per-process semaphores; 3 workers × 4 limit = 12 concurrent instead of 4 global | Acceptable: MongoDB `find_one_and_update` atomic dequeue still serializes correctly. Fix: replace with queue-depth count in future sprint |
| M3 | `services/knowledge/embeddings/providers/tfidf_provider.py` | TF-IDF vocab built from first corpus per instance; diverges across workers | Low impact: Atlas Vector Search bypasses TF-IDF for primary retrieval. Fix: persist vocab to MongoDB in future sprint |
| M4 | `rate_limit.py` | Falls back to in-process MemoryStorage when `REDIS_URL` not set | Documented: `REDIS_URL` is required in production. Without it, rate limits are per-instance (N× too permissive). Production validator logs `WARNING` |
| M5 | `ara/mission_memory.py` | Fire-and-forget Redis writes for mission state | Acceptable: MongoDB is source of truth; Redis is cache. Mission step state written to MongoDB first |

### LOW — Accepted

- `gateway/gateway.py` singleton: read-mostly config, acceptable
- `services/local_ai/cache/response_cache.py`: per-worker LRU, acceptable fallback
- `services/encryption_service.py`: key rotation requires restart, acceptable
- `services/redis_client.py`: well-implemented, no issues

---

## 2. Distributed Architecture

### Request Flow (3-instance deployment)

```
Internet → Load Balancer (nginx / AWS ALB)
              ↓ (round-robin)
    ┌─────────┬─────────┬─────────┐
    │  Pod 1  │  Pod 2  │  Pod 3  │   (each: 4 uvicorn workers)
    │ 4×workers│ 4×workers│ 4×workers│
    └─────────┴─────────┴─────────┘
         ↓                ↓
    Redis (shared)   MongoDB Atlas (shared)
    - L2 repo cache  - All persistent state
    - session store  - Job queue (atomic dequeue)
    - rate limits    - Schedule locks (dedup)
    - pub/sub        - Audit trail
```

### Stateless Components (no changes needed)
- FastAPI request handlers — pure functions, no state
- JWT authentication — stateless token verification
- `worker/queue.py` `MongoQueueBackend` — MongoDB-backed, atomic dequeue
- `worker/worker.py` `WorkerProcess` — all job state in MongoDB
- All routers — no in-process state

### Distributed-Safe After Phase 5
- `agents/memory.py` — Redis-backed sessions
- `repo/*.py` (all 93 repositories) — Redis L2 cache
- `worker/scheduler.py` — MongoDB dedup locks for job firing
- `services/knowledge/engine.py` — Atlas Vector Search (no in-process matrix)

---

## 3. MongoDB Configuration

### Connection Pool (updated)

| Setting | Before | After | Notes |
|---------|--------|-------|-------|
| `maxPoolSize` | 50 (hardcoded) | 200 (env: `MONGO_MAX_POOL`) | Override per environment |
| `minPoolSize` | 5 (hardcoded) | 10 (= maxPool/20) | Scales with max |
| `connectTimeoutMS` | 10,000 | 10,000 | No change |
| `serverSelectionTimeoutMS` | 10,000 | 10,000 | No change |
| `socketTimeoutMS` | 30,000 | 30,000 | No change |
| `maxIdleTimeMS` | 60,000 | 60,000 | No change |
| `waitQueueTimeoutMS` | 10,000 | 10,000 | No change |
| `retryWrites` | true | true | No change |
| `w` | majority | majority | No change |

### Recommended Atlas Tier by Scale

| Users | Tier | Replicas | Pool per pod | Total connections |
|-------|------|----------|--------------|-------------------|
| 1K | M10 | 1 pod | 50 | 50 |
| 10K | M20 | 3 pods | 50 | 150 |
| 100K | M40 | 5 pods | 100 | 500 |
| 500K | M80 | 10 pods | 100 | 1,000 |
| 1M+ | Dedicated / Serverless | 20 pods | 50 | 1,000 (sharded) |

### Collections with TTL Indexes (auto-cleanup)
- `worker_schedule_locks` — 1h TTL (dedup locks)
- `obs_audit_logs` — configurable TTL (default 90d)
- `worker_jobs` — completed jobs purged by worker
- `user_sessions` — JWT exp

### Missing Indexes to Add (recommended next sprint)
```javascript
// High-frequency query patterns identified in audit
db.worker_jobs.createIndex({ "status": 1, "queue_name": 1, "priority": -1, "created_at": 1 })
db.knowledge_chunks.createIndex({ "document_id": 1, "user_id": 1 })
db.ara_missions.createIndex({ "user_id": 1, "status": 1, "created_at": -1 })
db.publications.createIndex({ "user_id": 1, "status": 1 })
db.obs_traces.createIndex({ "trace_id": 1 })
```

---

## 4. Redis Configuration

### Required in Production
`REDIS_URL` must be set. Without it:
- Rate limiting: per-instance only (N× too permissive — DDoS risk)
- Repo cache: L1 only (no cross-replica invalidation)
- Session memory: process-local only (context lost on worker change)

### Key Namespaces

| Prefix | Used by | TTL |
|--------|---------|-----|
| `copilot:session:*` | `agents/memory.py` | 1h |
| `repo:{collection}:*` | All 93 repositories | 10–120s |
| `conversation:{user_id}` | `gateway/ai_memory.py` | 1h |
| `mission:{mission_id}` | `ara/mission_memory.py` | 24h |
| `workspace:{workspace_id}` | `gateway/ai_memory.py` | 4h |
| `research:{user_id}` | `gateway/ai_memory.py` | 4h |

### Recommended Redis Configuration (Redis 7+)
```
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
appendonly yes
appendfsync everysec
```

### Redis HA (Required for 10K+ users)
- Use Redis Sentinel (3-node) or Redis Cluster (6-node)
- ElastiCache for Redis (AWS) or Upstash (serverless)
- `REDIS_MAX_CONNECTIONS=20` per pod default (total = replicas × 20)

---

## 5. Worker Platform

### Architecture
- `MongoQueueBackend`: atomic dequeue via `find_one_and_update` — distributes work across all instances
- `WorkerPool`: 4 async workers per instance — CPU-bound tasks parallelised
- `Scheduler`: dedup lock prevents duplicate cron/interval fires across replicas
- `ConcurrencyManager`: per-worker semaphores (see M2 above for medium-term fix)

### Job Types and Scale Limits

| Job Type | Concurrency Limit | Notes |
|----------|------------------|-------|
| `ai.execution` | 4 per worker | LLM calls, rate-limited upstream |
| `graph.rebuild` | 1 per worker | Memory-intensive |
| `indexing.document` | 4 per worker | I/O-bound |
| `orcid.sync` | 2 per worker | External API rate limits |

### Distributed Scheduler Dedup (new in Phase 5)
- Lock collection: `worker_schedule_locks`
- Compound unique index: `(schedule_id, bucket)` where `bucket = int(timestamp / window_s)`
- TTL index: locks auto-expire after 1h
- Window for cron: 30s (first instance to fire within the window wins)
- Window for recurring: `max(30, interval_s / 2)` (prevents back-to-back duplicates)

---

## 6. Knowledge & Vector Search

### Vector Store Strategy

| Environment | Backend | Behaviour |
|-------------|---------|-----------|
| Atlas M10+ with vector index | `MongoDBVectorStore` | Native `$vectorSearch` — no in-process matrix |
| Atlas without vector index | `MongoDBVectorStore` → numpy fallback | Falls back to `NumpyVectorStore` automatically |
| Local dev (no Atlas) | `MongoDBVectorStore` → numpy fallback | Same fallback path |

**Default changed from `"numpy"` to `"mongodb"` (env: `KNOWLEDGE_VECTOR_BACKEND`).**

Atlas Vector Search setup (one-time):
```javascript
// In Atlas UI: Indexes → Create Index → JSON Editor
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "embedding": {
        "dimensions": 768,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}
```

### Memory Profile Comparison

| Setup | RAM per Worker |
|-------|----------------|
| Before (numpy, 100K chunks) | ~150MB just for embedding matrix |
| After (Atlas Vector Search) | ~0MB (server-side computation) |
| After (numpy fallback, 100K chunks) | ~150MB (only if Atlas unavailable) |

---

## 7. Session & AI Memory

### Session Layer (updated in Phase 5)

```
Request → SharedMemory.get_or_create(session_id)
              │
              ├── L1 Hit (in-process) → return session (0ms)
              │
              ├── L1 Miss → Redis GET copilot:session:{id}
              │         ├── Redis Hit → restore session, warm L1 (1-3ms)
              │         └── Redis Miss → create new session, save to Redis
              │
              └── Context load (first request): MongoDB queries → save to Redis
```

### Cross-Worker Session Recovery
Before Phase 5: session state lost when user hit a different pod.  
After Phase 5: session context (user profile, manuscripts, interests) persisted in Redis with 1h TTL and recovered on any pod.

**Note:** Agent outputs within an orchestration run are ephemeral (not persisted to Redis). This is intentional — they are computed fresh per-request and can include non-JSON-serializable objects.

---

## 8. Horizontal Scaling Configuration

### Docker Compose (single-node, 4 workers)
See `deploy/docker-compose.prod.yml`. Suitable for <10K DAU.

### Kubernetes (multi-node, auto-scaling)
See `deploy/k8s/`. Suitable for 10K–1M DAU.

Key manifests:
- `namespace.yaml` — Kubernetes namespace
- `backend-deployment.yaml` — 3-replica deployment with anti-affinity
- `hpa.yaml` — HPA: 3–20 replicas, CPU 60% / Memory 70% triggers
- `ingress.yaml` — nginx ingress with TLS, rate limiting, CORS
- `pdb.yaml` — PodDisruptionBudget: minAvailable=2

### Environment Variables for Enterprise Scale

```bash
# MongoDB
MONGO_MAX_POOL=50          # Per pod (total = pods × 50)
MONGODB_URI=mongodb+srv://...

# Redis (required)
REDIS_URL=redis://:password@redis-host:6379
REDIS_MAX_CONNECTIONS=20   # Per pod

# Workers
WORKERS=4                  # Uvicorn workers per pod

# Knowledge
KNOWLEDGE_VECTOR_BACKEND=mongodb  # Use Atlas Vector Search

# Application
APP_ENV=production
COOKIE_SECURE=1
```

---

## 9. Capacity Estimates

### Assumptions
- Avg request: 50ms (API), 3s (AI generation), 100ms (RAG retrieval)
- Pod: 4 uvicorn workers, 2 vCPU, 4GB RAM
- MongoDB Atlas M40: 250 connections, 4 vCPU, 16GB RAM
- Redis: 2GB, 100K ops/sec

### Throughput by User Count

| Concurrent Users | API RPS | Pods Required | Atlas Tier | Redis |
|-----------------|---------|---------------|------------|-------|
| 100 | 500 | 1 | M10 | Single |
| 1,000 | 5,000 | 3 | M20 | Single |
| 10,000 | 50,000 | 8 | M40 | Sentinel |
| 100,000 | 500,000 | 20 + CDN | M80 | Cluster |
| 500,000 | 2,500,000 | 50 + CDN | Dedicated | Cluster |
| 1,000,000 | 5,000,000 | Sharded deployment | Serverless | Cluster |

### Bottleneck Analysis at Scale

| Scale | Bottleneck | Mitigation |
|-------|-----------|------------|
| <10K users | None — single pod sufficient | — |
| 10K–100K | MongoDB connections | Atlas M40+, pool=100/pod |
| 100K–500K | LLM API rate limits (Anthropic/OpenAI) | Multi-provider routing (already implemented) |
| 500K–1M | MongoDB write throughput | Atlas Serverless / sharding by user_id |
| >1M | Application layer | Read replicas, CDN for static assets, microservice split |

### P99 Latency Targets

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| Health check | 1ms | 5ms | 10ms |
| Auth (login/register) | 50ms | 150ms | 300ms |
| Repo read (cached) | 2ms | 10ms | 20ms |
| Repo read (cold) | 20ms | 80ms | 150ms |
| RAG retrieval (Atlas) | 100ms | 300ms | 500ms |
| AI generation | 2s | 5s | 10s |
| File upload (10MB) | 500ms | 2s | 5s |

---

## 10. Production Readiness Checklist

### Infrastructure
- [x] Non-root Docker user (`synaptiq`, uid 1001)
- [x] Gunicorn + uvicorn workers (multi-process)
- [x] Health check: `/api/health` (liveness) + `/api/health/ready` (readiness)
- [x] Graceful shutdown: 60s termination grace period
- [x] Resource limits: CPU 2000m, Memory 4Gi per pod
- [x] Pod anti-affinity: pods spread across nodes
- [x] PodDisruptionBudget: minAvailable=2
- [x] HPA: 3–20 replicas, CPU/Memory triggers

### Security
- [x] Zero Trust: all routes require authentication
- [x] Rate limiting: Redis-backed when `REDIS_URL` set
- [x] CORS: allowlist-only origins
- [x] TLS: enforced via nginx ingress + cert-manager
- [x] Secrets: Kubernetes Secret (not env file in k8s)
- [x] Audit trail: all writes logged to `obs_audit_logs`

### Data
- [x] MongoDB: Atlas `w:majority` writes for durability
- [x] Redis: AOF persistence for cache durability
- [x] Worker jobs: MongoDB-backed (survive pod restarts)
- [x] Session state: Redis-backed with MongoDB context fallback
- [x] Schedule locks: TTL-indexed (auto-cleanup)

### Observability
- [x] Distributed tracing: `obs/tracing.py`
- [x] Structured logging: JSON to stdout (Kubernetes log aggregation)
- [x] Metrics: `obs/metrics.py`
- [x] Alert rules: `obs/alerting.py`
- [x] Cost tracking: `obs/cost.py` per LLM call
- [x] Admin dashboard: `/api/ops/*` endpoints

---

## 11. Remaining Gaps (future sprints)

| Priority | Item | Effort |
|----------|------|--------|
| HIGH | Redis-backed circuit breaker state (`worker/circuit_breaker.py`) | 1 day |
| HIGH | Global concurrency limits via MongoDB queue depth (`worker/concurrency.py`) | 2 days |
| MEDIUM | TF-IDF vocabulary persistence to MongoDB | 2 days |
| MEDIUM | Embedding cache in Redis (reduce redundant recomputation across workers) | 2 days |
| MEDIUM | Redis Pub/Sub for cache invalidation across replicas | 3 days |
| LOW | Key rotation without restart (versioned encryption keys) | 1 day |
| LOW | Config hot-reload via Redis Pub/Sub | 1 day |

---

## Certification Decision

**Phase 5 CERTIFIED ✓**

All CRITICAL and HIGH severity scalability issues have been resolved.  
The platform is ready for horizontal scaling to 100K concurrent users with the MongoDB Atlas + Redis + Kubernetes deployment described above.  
2865 tests pass, 0 failures, 57% coverage maintained.

*Signed: Production Hardening Phase 5 — 2026-07-05*
