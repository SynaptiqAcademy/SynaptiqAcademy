"""P1 Phase 8F — Interdisciplinary Research Team Builder.

Research Need -> Team Blueprint -> real Synaptiq candidates per role ->
user-selected team -> individual Phase 8E collaboration requests.

Reuses, never duplicates:
- services/research_need (ResearchNeed, interpretation, relevance/evidence)
- routers/collaboration_requests.send_request() for every invitation —
  this package never writes to the collaboration_requests collection
  directly.
"""
