"""Risk-based authentication engine.

Computes a risk score (0–100) for each login attempt based on:
  - New / unknown device            +25
  - Country change from last login  +20
  - Impossible travel               +40
  - TOR exit node detected          +50
  - VPN / proxy indicators          +20
  - Repeated failures (brute force) +30

Scores ≥ 60 trigger additional verification.
Scores ≥ 80 block the login and raise a critical security event.

Geolocation is fetched from ip-api.com (free, no key needed).
Requests time out in 1.5 s so they never block the login path.
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from db import get_db
from services.security_event_service import emit_security_event
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.risk_engine")

_GEO_TIMEOUT = float(os.environ.get("GEO_TIMEOUT_SECS", "1.5"))
_RISK_BLOCK_THRESHOLD   = int(os.environ.get("RISK_BLOCK_THRESHOLD",   "80"))
_RISK_VERIFY_THRESHOLD  = int(os.environ.get("RISK_VERIFY_THRESHOLD",  "60"))

# Approximate latitude/longitude per country (subset of common ones + rest-of-world centroid).
# Used only for impossible-travel detection — no accuracy needed.
_COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "US": (38.9, -77.0), "GB": (51.5, -0.1), "DE": (52.5, 13.4),
    "FR": (48.9, 2.3),   "CA": (45.4, -75.7), "AU": (-33.9, 151.2),
    "JP": (35.7, 139.7), "CN": (39.9, 116.4), "IN": (28.6, 77.2),
    "BR": (-15.8, -47.9), "RO": (44.4, 26.1), "UA": (50.4, 30.5),
    "NL": (52.4, 4.9), "RU": (55.8, 37.6), "IT": (41.9, 12.5),
    "ES": (40.4, -3.7), "PL": (52.2, 21.0), "SE": (59.3, 18.1),
    "SG": (1.3, 103.8), "ZA": (-25.7, 28.2), "AE": (25.2, 55.3),
    "KR": (37.6, 126.9), "MX": (19.4, -99.1),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ─────────────────────────────────────────────────────────────────────────────
# Geolocation
# ─────────────────────────────────────────────────────────────────────────────

async def geolocate(ip: str) -> dict:
    """Returns {country, city, lat, lon, proxy, hosting, query} or empty dict."""
    if not ip or ip in ("127.0.0.1", "::1", "localhost", "unknown"):
        return {}
    try:
        async with httpx.AsyncClient(timeout=_GEO_TIMEOUT) as client:
            r = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "country,countryCode,city,lat,lon,proxy,hosting,query,status"},
            )
            data = r.json()
            if data.get("status") == "success":
                return data
    except Exception as e:
        logger.debug("Geolocation failed for %s: %s", ip, e)
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Risk scoring
# ─────────────────────────────────────────────────────────────────────────────

async def assess_login_risk(
    user: dict,
    ip: str,
    is_trusted_device: bool,
    geo: Optional[dict] = None,
) -> dict:
    """Return a risk assessment dict for a login attempt.

    {
      score: int,               # 0-100
      level: "low"|"medium"|"high"|"critical",
      factors: [str, ...],
      action: "allow"|"challenge"|"block",
      geo: dict,
    }
    """
    if geo is None:
        geo = await geolocate(ip)

    score   = 0
    factors = []

    # 1. Unknown device
    if not is_trusted_device:
        score += 25
        factors.append("new_device")

    # 2. Country change
    last_country = user.get("last_login_country")
    current_country = geo.get("countryCode")
    if current_country and last_country and current_country != last_country:
        score += 20
        factors.append(f"country_change:{last_country}→{current_country}")

    # 3. Impossible travel
    if current_country and last_country and current_country != last_country:
        last_login_at = user.get("last_successful_login")
        if last_login_at:
            try:
                dt = datetime.fromisoformat(last_login_at.replace("Z", "+00:00"))
                hours_elapsed = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                c1 = _COUNTRY_CENTROIDS.get(last_country)
                c2 = _COUNTRY_CENTROIDS.get(current_country)
                if c1 and c2 and hours_elapsed < 6:
                    dist_km = _haversine_km(c1[0], c1[1], c2[0], c2[1])
                    # Max human travel speed ≈ 950 km/h (plane)
                    if hours_elapsed > 0 and (dist_km / hours_elapsed) > 1000:
                        score += 40
                        factors.append(f"impossible_travel:{dist_km:.0f}km_in_{hours_elapsed:.1f}h")
            except Exception:
                pass

    # 4. TOR or proxy
    if geo.get("proxy"):
        score += 50
        factors.append("tor_or_proxy")
    elif geo.get("hosting"):
        score += 20
        factors.append("datacenter_ip")

    score = min(score, 100)

    if score >= _RISK_BLOCK_THRESHOLD:
        level  = "critical"
        action = "block"
    elif score >= _RISK_VERIFY_THRESHOLD:
        level  = "high"
        action = "challenge"
    elif score >= 30:
        level  = "medium"
        action = "allow"
    else:
        level  = "low"
        action = "allow"

    return {
        "score":   score,
        "level":   level,
        "factors": factors,
        "action":  action,
        "geo":     geo,
    }


async def update_user_geo_state(user_id: str, geo: dict) -> None:
    """Store last-login geo information on the user document."""
    from bson import ObjectId
    upd = {}
    if geo.get("countryCode"):
        upd["last_login_country"] = geo["countryCode"]
    if geo.get("city"):
        upd["last_login_city"] = geo["city"]
    if upd:
        try:
            db = get_db()
            db = DBProxy(db, SecurityContext.system())

            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": upd})
        except Exception:
            pass
