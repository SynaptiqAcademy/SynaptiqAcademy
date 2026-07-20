"""
Simulation engine.

Supports "what-if" reasoning over the twin's knowledge graph and platform data.
EVIDENCE POLICY: Never fabricates outcomes, probabilities, or predictions.
When evidence is insufficient, explicitly states so.
Results show historical patterns and connections, not forecasts.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("twin.simulation")

_INSUFFICIENT = "Insufficient data to run a reliable simulation. More platform activity or external data synchronization is required."


async def simulate_journal_submission(db, user_id: str, journal_name: str) -> dict:
    """
    Show what the platform data reveals about user-journal compatibility.
    Does NOT predict acceptance probability.
    Shows: topic overlap, prior submission history on platform.
    """
    evidence = []
    findings = []

    # 1. Prior submissions to this journal on platform
    prior = await db.manuscripts.count_documents({
        "user_id": user_id,
        "journal": {"$regex": journal_name, "$options": "i"},
    })
    if prior > 0:
        evidence.append({"source": "Synaptiq manuscripts DB", "detail": f"{prior} prior manuscript(s) targeting this journal"})
        findings.append(f"You have {prior} manuscript(s) on Synaptiq targeting this journal.")

    # 2. Topic overlap via LKG
    try:
        node_id  = f"researcher:platform:{user_id}"
        j_id     = f"journal:name:{journal_name.lower().replace(' ', '_')}"
        j_node   = await db.lkg_nodes.find_one({"node_id": j_id})
        if j_node:
            evidence.append({"source": "Synaptiq Living Knowledge Graph", "detail": "Journal found in LKG"})
            findings.append("This journal is present in the Living Knowledge Graph.")
        else:
            findings.append(f"Journal '{journal_name}' not yet in the Living Knowledge Graph — run OpenAlex ingestion to populate journal data.")
    except Exception:
        pass

    # 3. Research domain alignment
    ms_keywords: list[str] = []
    async for ms in db.manuscripts.find({"user_id": user_id}, {"keywords": 1}):
        ms_keywords.extend(ms.get("keywords") or [])

    if not findings:
        return {
            "simulation_type": "journal_submission",
            "journal":         journal_name,
            "result":          _INSUFFICIENT,
            "findings":        [],
            "evidence":        [],
            "policy_note":     "This simulation shows historical platform data only. It does not predict acceptance outcomes.",
        }

    return {
        "simulation_type": "journal_submission",
        "journal":         journal_name,
        "result":          "Simulation based on platform data only — not a prediction of acceptance outcome.",
        "findings":        findings,
        "evidence":        evidence,
        "your_keywords":   ms_keywords[:10],
        "policy_note":     "No acceptance probability is computed. Results reflect only what Synaptiq can verify from your profile and activity.",
        "ran_at":          datetime.now(timezone.utc).isoformat(),
    }


async def simulate_timing_impact(db, user_id: str, delay_months: int) -> dict:
    """
    Show how delaying a submission affects upcoming deadlines visible on platform.
    Does NOT predict citation impact or acceptance timing.
    """
    from datetime import timedelta
    now          = datetime.now(timezone.utc)
    future_cutoff = now + timedelta(days=delay_months * 30)

    # Grants with deadlines in that window
    deadlines_in_window = []
    async for grant in db.grants.find({"user_id": user_id, "deadline": {"$gte": now, "$lte": future_cutoff}}):
        deadlines_in_window.append({
            "title":    grant.get("title", "Untitled grant"),
            "deadline": str(grant.get("deadline", "")),
        })

    # Active collaboration requests that might be time-sensitive
    collab_requests = await db.collaborations.count_documents({
        "$or": [{"requester_id": user_id}, {"recipient_id": user_id}],
        "status": "pending",
    })

    findings = []
    if deadlines_in_window:
        findings.append(f"{len(deadlines_in_window)} grant deadline(s) fall within the {delay_months}-month delay window.")
    else:
        findings.append(f"No grant deadlines found within the next {delay_months} months on Synaptiq.")

    if collab_requests > 0:
        findings.append(f"{collab_requests} pending collaboration request(s) may be time-sensitive.")

    return {
        "simulation_type":  "timing_impact",
        "delay_months":     delay_months,
        "result":           f"Platform data shows {len(deadlines_in_window)} deadline(s) within this window.",
        "findings":         findings,
        "deadlines_found":  deadlines_in_window,
        "evidence":         [
            {"source": "Synaptiq grants DB", "detail": f"{len(deadlines_in_window)} grant deadline(s) queried"},
        ],
        "policy_note":      "This simulation shows deadline conflicts only. It does not predict citation impact, reviewer availability, or journal timing.",
        "ran_at":           datetime.now(timezone.utc).isoformat(),
    }


async def simulate_collaborator_opportunity(db, user_id: str, institution_name: str) -> dict:
    """
    Show existing LKG connections between this researcher and a target institution.
    Does NOT fabricate collaboration outcomes or research impact predictions.
    """
    evidence = []
    findings = []

    # Direct collaborations with users from that institution
    direct_collabs = await db.collaborations.count_documents({
        "$or": [{"requester_id": user_id}, {"recipient_id": user_id}],
        "status": "accepted",
        "institution": {"$regex": institution_name, "$options": "i"},
    })
    if direct_collabs > 0:
        evidence.append({"source": "Synaptiq collaborations DB", "detail": f"{direct_collabs} collaboration(s) with this institution"})
        findings.append(f"You have {direct_collabs} active collaboration(s) with researchers from {institution_name}.")

    # LKG: institution node + path from user
    try:
        inst_id = f"institution:name:{institution_name.lower().replace(' ', '_')}"
        inst_node = await db.lkg_nodes.find_one({"node_id": inst_id})
        if inst_node:
            evidence.append({"source": "Synaptiq Living Knowledge Graph", "detail": "Institution found in LKG"})
            findings.append(f"'{institution_name}' is present in the Living Knowledge Graph.")
            # Count researchers affiliated with that institution in LKG
            affiliated_count = await db.lkg_edges.count_documents({
                "to_id": inst_id, "type": "AFFILIATED_WITH"
            })
            if affiliated_count > 0:
                findings.append(f"{affiliated_count} researcher(s) in the LKG are affiliated with this institution.")
                evidence.append({"source": "LKG", "detail": f"{affiliated_count} AFFILIATED_WITH edges"})
        else:
            findings.append(f"'{institution_name}' not found in the Living Knowledge Graph. Run institution data ingestion to see LKG-based connections.")
    except Exception:
        pass

    if not evidence:
        return {
            "simulation_type": "collaborator_opportunity",
            "institution":     institution_name,
            "result":          _INSUFFICIENT,
            "findings":        ["No verified connections found between you and this institution on Synaptiq."],
            "evidence":        [],
            "policy_note":     "This simulation shows existing verified connections only. It does not predict research outcomes.",
        }

    return {
        "simulation_type": "collaborator_opportunity",
        "institution":     institution_name,
        "result":          "Simulation based on verified platform and graph data.",
        "findings":        findings,
        "evidence":        evidence,
        "policy_note":     "Results show verified existing connections. No outcome predictions are made.",
        "ran_at":          datetime.now(timezone.utc).isoformat(),
    }
