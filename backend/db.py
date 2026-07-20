import os
import re
import ssl
import time
import logging
import platform
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import (
    ConfigurationError, ServerSelectionTimeoutError, OperationFailure,
    AutoReconnect, ConnectionFailure, NetworkTimeout,
)

logger = logging.getLogger("synaptiq.db")

_client: AsyncIOMotorClient | None = None
_db = None
_db_proxy = None  # system-context DBProxy; cached after first call to get_db()

# ── Circuit breaker (AUTH-BUG-003) ───────────────────────────────────────────
# Every request that touches Mongo while Atlas/the cluster is unreachable pays
# the full serverSelectionTimeoutMS (10s, x3 shard members observed in practice
# = up to ~30s) before failing. Under a real outage this means every concurrent
# request — logins, background jobs, health checks — independently blocks for
# up to 30s, which can exhaust Motor's executor thread pool and take down
# unrelated requests too (reproduced locally: the whole API stopped responding,
# including /api/health, after a handful of overlapping login attempts against
# an unreachable Atlas cluster).
#
# This is a minimal, dependency-free circuit breaker: once ANY caller sees a
# real connectivity error, we remember "Mongo is down" for a cool-down window
# so every other caller in that window can fail fast (milliseconds) with a
# clear, honest error instead of queueing behind the same timeout.
#
# RC1 AUDIT FINDING: this was previously "8" — shorter than the ~10-30s
# failure latency documented above, which it is supposed to protect against.
# Reproduced live: with an 8s cooldown, any request landing more than ~8s
# after the last one (a normal traffic pattern, not just concurrent bursts)
# re-triggers a fresh connection attempt and pays the full 8-13s timeout
# again — /api/health, /api/auth/me, and /api/auth/logout each measured at
# 8.7-13.0s despite the circuit breaker being in place. The cooldown must be
# meaningfully longer than the worst documented failure cost (~30s) to
# actually short-circuit repeated attempts during a sustained outage.
DB_DOWN_COOLDOWN_SECONDS = float(os.environ.get("DB_DOWN_COOLDOWN_SECONDS", "60"))

_db_down_until: float = 0.0
_db_down_reason: str = ""

MONGO_CONNECTIVITY_ERRORS = (ServerSelectionTimeoutError, AutoReconnect, ConnectionFailure, NetworkTimeout)


def is_db_down() -> bool:
    """True if a recent real Mongo failure is still within its cool-down window."""
    return time.monotonic() < _db_down_until


def mark_db_down(exc: Exception) -> None:
    """Record that Mongo just failed, so other callers can fail fast for a bit."""
    global _db_down_until, _db_down_reason
    already_down = is_db_down()
    _db_down_until = time.monotonic() + DB_DOWN_COOLDOWN_SECONDS
    _db_down_reason = classify_mongo_error(exc)
    if not already_down:
        logger.error("Mongo marked DOWN for %.0fs — %s", DB_DOWN_COOLDOWN_SECONDS, _db_down_reason)


def mark_db_up() -> None:
    """Clear the circuit breaker after any operation succeeds."""
    global _db_down_until
    if _db_down_until:
        logger.info("Mongo recovered — circuit breaker cleared")
    _db_down_until = 0.0


def db_down_reason() -> str:
    return _db_down_reason or "Database temporarily unavailable."


def classify_mongo_error(exc: Exception) -> str:
    """Turn a raw pymongo connectivity exception into an actionable diagnostic.

    Shared by get_db()'s constructor-time handling and any call site that
    wraps a live query (login, register, health checks, background jobs) —
    the same failure (e.g. Atlas TLS/IP-allowlist rejection) can surface at
    either point depending on whether the client had already connected once.
    """
    err = str(exc)
    if "TLSV1_ALERT_INTERNAL_ERROR" in err or "tlsv1 alert internal error" in err.lower():
        return (
            "MongoDB Atlas TLS rejected — this is almost certainly an IP allowlist issue. "
            "Go to: Atlas UI → Network Access → IP Access List → Add IP Address. "
            "Add the server's current public IP (or 0.0.0.0/0 for development)."
        )
    if "no nameservers" in err.lower() or "nameserver" in err.lower():
        return "MongoDB DNS failure: could not resolve the Atlas SRV record. Check DNS/network egress."
    if isinstance(exc, ServerSelectionTimeoutError):
        return (
            "MongoDB server selection timed out. Check: (1) Atlas Network Access IP allowlist, "
            "(2) firewall rules, (3) the cluster is not paused."
        )
    return f"MongoDB connectivity error: {type(exc).__name__}: {err[:200]}"

# ── Env var resolution ────────────────────────────────────────────────────────
# Primary:  MONGODB_URI  /  MONGODB_DB_NAME  (Atlas standard)
# Fallback: MONGO_URL    /  DB_NAME          (legacy local-dev names)
# In production the validator rejects localhost URIs.

def _mongo_uri() -> str:
    uri = (
        os.environ.get("MONGODB_URI", "").strip()
        or os.environ.get("MONGO_URL", "").strip()
    )
    if not uri:
        raise RuntimeError(
            "No MongoDB URI configured. "
            "Set MONGODB_URI=mongodb+srv://... (Atlas) in your .env file."
        )
    return uri


def _db_name() -> str:
    name = (
        os.environ.get("MONGODB_DB_NAME", "").strip()
        or os.environ.get("DB_NAME", "").strip()
    )
    if not name:
        raise RuntimeError(
            "No database name configured. Set MONGODB_DB_NAME= in your .env file."
        )
    return name


def _redact_uri(uri: str) -> str:
    """Return URI with credentials replaced by *** for safe logging."""
    return re.sub(r"(?<=://)[^:]+:[^@]+@", "***:***@", uri)


def _configure_dns_fallback() -> None:
    """
    Ensure dnspython has valid nameservers before PyMongo resolves the SRV record.

    Falls back to Google (8.8.8.8 / 8.8.4.4) + Cloudflare (1.1.1.1) public DNS
    when the system resolver is unavailable — common in Docker containers, CI runners,
    and macOS environments where /etc/resolv.conf contains only link-local IPv6 addresses
    (fe80::1%en0) that are unreachable outside the local network interface.
    """
    try:
        import dns.resolver as _dns
        # Probe system resolver — raises if nameserver list is empty or unparseable
        probe = _dns.Resolver()
        if not probe.nameservers:
            raise ValueError("nameserver list is empty")
        logger.debug("DNS probe OK — system nameservers: %s", probe.nameservers[:2])
        return
    except ImportError:
        logger.warning(
            "dnspython not installed — mongodb+srv:// URIs cannot be resolved. "
            "Run: pip install 'dnspython>=2.3.0'"
        )
        return
    except Exception as probe_exc:
        pass  # fall through to configure fallback below

    try:
        import dns.resolver as _dns
        fallback = _dns.Resolver(configure=False)
        fallback.nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
        _dns.default_resolver = fallback
        logger.warning(
            "System DNS resolver unavailable; configured fallback nameservers "
            "8.8.8.8 / 8.8.4.4 / 1.1.1.1 for MongoDB SRV resolution"
        )
    except Exception as fallback_exc:
        logger.error(
            "Failed to configure DNS fallback: %s — mongodb+srv:// may not resolve",
            str(fallback_exc)[:120],
        )


def _motor_loop_is_closed() -> bool:
    """Return True if the cached motor client is bound to a closed event loop.

    Motor 3.x lazily caches the event loop the first time `io_loop` is accessed.
    In test environments, asyncio.run() creates a temporary event loop, runs a
    coroutine (which may call get_db()), then closes that loop.  Subsequent
    callers (e.g. Starlette's TestClient startup) get the stale, closed-loop
    motor client and fail with 'Event loop is closed'.

    This guard detects the stale state so get_db() can reinitialise cleanly.
    """
    if _client is None:
        return False
    try:
        loop = _client.get_io_loop()
        return loop is not None and loop.is_closed()
    except Exception:
        return False


def get_db():
    global _client, _db, _db_proxy
    if _db is not None and _motor_loop_is_closed():
        logger.warning("Motor client's event loop is closed — reinitialising DB connection")
        try:
            _client.close()
        except Exception:
            pass
        _client = None
        _db = None
        _db_proxy = None
    if _db is None:
        uri = _mongo_uri()
        db_name = _db_name()
        is_atlas = uri.startswith("mongodb+srv://")
        uri_redacted = _redact_uri(uri)

        # Pool size: default 200 per worker for enterprise scale.
        # Override with MONGO_MAX_POOL env var (e.g. 50 for local dev, 200+ for prod).
        _max_pool = int(os.environ.get("MONGO_MAX_POOL", "200"))
        _min_pool = max(5, _max_pool // 20)

        # AUTH-BUG-007: connectTimeoutMS/serverSelectionTimeoutMS were 10s each.
        # Motor dispatches the underlying (synchronous) pymongo call to a thread
        # pool executor — asyncio-level timeouts wrapped around a Motor call
        # (e.g. asyncio.wait_for) stop the *caller* from waiting, but do NOT
        # cancel that thread; it keeps running the real driver-level timeout to
        # completion regardless. During a real Atlas outage, every attempt
        # (ours or a background job's) ties up an executor thread for up to
        # this long. Reproduced locally: repeated attempts against an
        # unreachable cluster exhausted the default executor thread pool,
        # which then queued *unrelated* requests (including /api/health)
        # behind threads that wouldn't free up for the old 10s duration each.
        # 4s is still generous for a real network blip and cuts worst-case
        # thread occupancy and user-facing wait time by more than half.
        _server_selection_timeout = int(os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "4000"))
        kwargs: dict = {
            "maxPoolSize": _max_pool,
            "minPoolSize": _min_pool,
            "connectTimeoutMS": _server_selection_timeout,
            "serverSelectionTimeoutMS": _server_selection_timeout,
            "socketTimeoutMS": 20_000,
            "maxIdleTimeMS": 60_000,
            "waitQueueTimeoutMS": 5_000,
            "retryWrites": True,
            "w": "majority",
            "appName": "SYNAPTIQ",
        }

        if is_atlas:
            kwargs["tls"] = True
            kwargs["tlsAllowInvalidCertificates"] = False
            # Ensure dnspython can resolve the SRV record before Motor tries
            _configure_dns_fallback()
            logger.info(
                "Connecting to MongoDB Atlas (SRV) — host=%s db=%s pool_max=%d pool_min=%d",
                uri_redacted, db_name, kwargs["maxPoolSize"], kwargs["minPoolSize"],
            )
        else:
            _is_prod = os.environ.get("APP_ENV", "development").lower() in ("prod", "production")
            if _is_prod:
                raise RuntimeError(
                    "PRODUCTION STARTUP REFUSED: MONGODB_URI points to a local host. "
                    "Atlas (mongodb+srv://) is required in production."
                )
            logger.info(
                "Connecting to local MongoDB — host=%s db=%s",
                uri_redacted, db_name,
            )

        try:
            _client = AsyncIOMotorClient(uri, **kwargs)
            _db = _client[db_name]
            _db_proxy = None  # reset proxy whenever motor db is (re)initialised
            logger.info("MongoDB client initialised — database: %s", db_name)
        except ConfigurationError as exc:
            err = str(exc)
            if "no nameservers" in err or "nameserver" in err.lower():
                logger.error(
                    "MongoDB DNS failure: could not resolve SRV record for %s. "
                    "Ensure DNS is reachable or use a plain mongodb:// URI. Detail: %s",
                    uri_redacted, err[:200],
                )
            elif "ssl" in err.lower() or "tls" in err.lower():
                logger.error(
                    "MongoDB TLS configuration error connecting to %s. "
                    "Python %s / OpenSSL %s may be incompatible with Atlas TLS policy. "
                    "Try upgrading pymongo>=4.9 or use Python 3.12. Detail: %s",
                    uri_redacted,
                    platform.python_version(),
                    ssl.OPENSSL_VERSION,
                    err[:200],
                )
            else:
                logger.error(
                    "MongoDB configuration error — host=%s detail=%s",
                    uri_redacted, err[:200],
                )
            raise
        except ServerSelectionTimeoutError as exc:
            err = str(exc)
            if "TLSV1_ALERT_INTERNAL_ERROR" in err or "tlsv1 alert internal error" in err.lower():
                # Atlas (and other MongoDB TLS proxies) sends TLS internal_error (alert 80)
                # for connections from IP addresses not in the Network Access IP allowlist.
                # This is NOT a Python/OpenSSL/PyMongo version problem — standard TLS
                # to other servers (google.com, mongodb.com) works fine.
                import socket as _sock
                try:
                    public_ip = _sock.gethostbyname(_sock.gethostname())
                except Exception:
                    public_ip = "unknown"
                logger.error(
                    "MongoDB Atlas TLS rejected — this is almost certainly an IP allowlist issue. "
                    "Go to: Atlas UI → Network Access → IP Access List → Add IP Address. "
                    "Add your current public IP or 0.0.0.0/0 for development. "
                    "Host=%s. Detail: %s",
                    uri_redacted, err[:300],
                )
            else:
                logger.error(
                    "MongoDB server selection timeout — host=%s. "
                    "Check: (1) Atlas Network Access IP allowlist, "
                    "(2) firewall rules, (3) cluster is not paused. Detail: %s",
                    uri_redacted, err[:300],
                )
            mark_db_down(exc)
            raise
        except OperationFailure as exc:
            logger.error(
                "MongoDB authentication failed — host=%s. "
                "Verify credentials in MONGODB_URI. Detail: %s",
                uri_redacted, str(exc)[:200],
            )
            raise
        except Exception as exc:
            logger.error(
                "MongoDB client init failed — host=%s error=%s: %s",
                uri_redacted, type(exc).__name__, str(exc)[:200],
            )
            raise

    if _db_proxy is None:
        from repo.shim import make_db_proxy
        _db_proxy = make_db_proxy(_db, system=True)
    return _db_proxy


def close_db():
    global _client, _db, _db_proxy
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection pool closed")
    _client = None
    _db = None
    _db_proxy = None
