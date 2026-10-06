# AI system inventory and data flow

| System | Purpose | Provider route | Data sent | Stored by Synaptiq | Deleted |
|---|---|---|---|---|---|
| Research assistant / copilot | Answer research questions | Smart router: Anthropic (Claude Sonnet/Haiku/Opus by task), fallback OpenAI (GPT-4o family) | Query and selected project context | `ai_conversations`, `ai_messages`, `copilot_conversations`, `ai_requests` | When the member deletes them, or at account deletion |
| Writing tools (abstract, rewriting, literature/gap/design/statistical reviews) | Draft and review text | Same router | The text or manuscript sections chosen | Per-tool collections (`abstract_generations`, `literature_reviews`, ...) | At account deletion |
| Knowledge base | Search over the member's own documents | Embeddings: OpenAI `text-embedding-3-small` (production); answers via the router | Document chunks | `knowledge_documents`, `knowledge_chunks` (with embeddings) | Per document, or at account deletion (embeddings included) |
| Matching and suggestions | Suggest collaborators, venues, funding | Rule-based and scoring code; no external AI call for ranking | — | Recommendation collections | At account deletion |
| Public landing preview | Map a typed research question | Deterministic rules (`services/public_demo`) | — | Nothing stored | — |

## Controls

- **Fallback is explicit in config** (`services/smart_router/config.py`: `cloud_provider_fallbacks = ["anthropic", "openai"]`) and disclosed in the Privacy Policy and AI Usage Policy.
- **Cost guard:** paid AI calls in request context must pass `cost_guard.preflight` and credit reservation (earlier phase).
- **Logging:** usage records (`ai_requests`) hold metadata and token counts. The admin conversation view shows metadata only. Since Phase 2, all `/api/admin/*` endpoints require an administrator; before, AI action logs and telemetry were readable by any signed-in member.
- **Provider retention:** Anthropic and OpenAI keep API data for a limited period under their own policies, and don't train on API data by default. Confirm the terms accepted for this account (OWNER VERIFICATION REQUIRED).
- **No automated decisions** with legal or similarly significant effects.

## AI Usage Policy corrections (Phase 2)

The public `/ai-policy` page claimed the following; each is now corrected or removed:
- Anthropic "does not retain data beyond the duration of the API call": false.
- "Enterprise API terms": unverified.
- OpenAI "optional / if configured": production has it configured and uses it.
- Prompt cache "isolated to your session": unverified.
- A self-hosted / local-AI offering: not offered.
