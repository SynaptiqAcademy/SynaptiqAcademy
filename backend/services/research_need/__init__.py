"""P1 Phase 8C — Research Need Intelligence.

Research question / problem -> structured Research Need -> required expertise
-> real Synaptiq people -> explainable match -> collaboration.

This package deliberately does NOT contain a people database, a matching
engine, or a collaboration-request mechanism — it reuses the canonical ones
(services/network/discovery_engine.py for retrieval,
services/collab_intelligence/matching_engine.py's person-to-person matching
stays untouched and unused here; see relevance.py's module docstring for why
a separate, smaller relevance layer exists instead).
"""
