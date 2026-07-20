# SYNAPTIQ Phase 5 — Discovery Suite Architecture

## 1. Data Source Analysis

| Domain | Source | License | Cost | Auth | Coverage | Notes |
|---|---|---|---|---|---|---|
| **Journals** | **OpenAlex** | CC0 | Free | Polite UA + email recommended | ~250k journals | Primary; richest metadata (subjects, OA, APC, h-index, 2yr_mean_citedness). |
| Journals | Crossref | CC0 | Free | Polite UA + email | ~75k journals | Best ISSN coverage; fewer "soft" fields. Use to back-fill ISSN-L from DOI prefixes. |
| Journals | DOAJ | CC-BY | Free | None | ~21k OA journals | Adds vetted OA status + APC fees + plain-text policy. |
| Journals | Scimago | Scrape-only | – | – | Q-rankings | **Excluded** — ToS forbids automated ingestion. Quartile back-fills only via manual import. |
| **Conferences** | **WikiCFP** | RSS public | Free | None | ~50k CFPs | Primary; well-structured RSS w/ deadlines and topics. |
| Conferences | OpenResearch.org | Public REST | Free | None | ~15k confs | Adds canonical names + CORE rankings + historical instances. |
| Conferences | CORE Rankings | CSV (CC-BY) | Free | None | ~3k ranked | Adds A*/A/B/C rank back-fills. |
| Conferences | DBLP venues | XML | Free | None | – | Optional CS-only enrichment. |
| **Grants** | **OpenAIRE Graph** | CC-BY | Free | None | EU + global, 4M+ projects | Primary; covers Horizon Europe, ERC, national agencies federated. |
| Grants | NIH RePORTER | Public REST | Free | None | US biomedical, 2.5M+ awards | Primary for biomedical. |
| Grants | UKRI Gateway to Research | Public REST | Free | None | UK research councils | Primary for UK. |
| Grants | NSF Awards API | Public REST | Free | None | US sciences | Adds physical sciences & engineering. |
| Grants | Horizon Dashboard | Public REST | Free | None | EU specific | Optional EU enrichment. |

### Excluded by design
* Scopus / Web of Science / Dimensions (commercial licenses, not legally ingestible).
* ResearchGate (no public API, ToS forbids scraping).
* Lens.org commercial dataset (sign-up gated).

## 2. Legal & Technical Constraints

1. **Attribution**: every record stores `source` + `external_ids.<source>` and is rendered in the UI as "Data from OpenAlex/Crossref/...". CC0 sources still get attribution as a courtesy.
2. **Rate limits**: OpenAlex 10 req/s polite pool (with `mailto=`), Crossref 50 req/s polite (with `User-Agent: SYNAPTIQ/0.5 (mailto:...)`), DOAJ unrestricted, WikiCFP courteous (~1 req/s), OpenAIRE 7,200 req/day anonymous.
3. **Polite UA**: All HTTP clients send `User-Agent: SYNAPTIQ/0.5 (https://synaptiq.io; mailto:hello@synaptiq.io)` and `From:` header.
4. **No commercial redistribution** — discovery surface is **read-only browsing + filtering** by authenticated SYNAPTIQ users. We don't expose a bulk-export API.
5. **PII**: Public sources only — no person-level information beyond what is already on the source records (PI name on grants, author byline on journals).
6. **Provenance**: Every record carries `last_seen_source_at` so we can re-ingest stale data.

## 3. Database Schema (canonical, post-normalization)

### `journals`
```
{
  _id, source ("openalex|crossref|doaj|seed"),
  external_ids: { openalex, crossref, doaj, issn_l, issns:[] },
  title (canonical), publisher, country, language,
  subjects:[], research_areas:[], scope_keywords:[],
  open_access (bool), oa_status ("gold|diamond|hybrid|closed"),
  apc_usd (number | null), has_apc (bool),
  quartile ("Q1|Q2|Q3|Q4" | null),
  h_index, works_count, cited_by_count, mean_citedness_2yr,
  homepage_url, submission_url,
  review_time_weeks (null), acceptance_rate (null),
  created_at, updated_at, last_seen_source_at,
  popularity_score (computed: log10(works+1) + log10(cites+1) + h/10)
}
```

### `conferences`
```
{
  _id, source ("wikicfp|openresearch|core|seed"),
  external_ids: { wikicfp, openresearch, dblp_key },
  name (canonical), acronym, organizer, sponsors:[],
  research_areas:[], topics:[],
  rank ("A*|A|B|C" | null), rank_source ("core" | null),
  location, country, format ("in-person|virtual|hybrid" | null),
  submission_deadline (ISO), notification_date (ISO),
  camera_ready_date (ISO), start_date (ISO), end_date (ISO),
  website, cfp_url,
  created_at, updated_at, last_seen_source_at,
  deadline_state ("open|closing_soon|closed") // computed at query time
}
```

### `grants`
```
{
  _id, source ("openaire|nih|ukri|nsf|seed"),
  external_ids: { openaire, nih, ukri, nsf, doi },
  title, program, sponsor, sponsor_country,
  research_areas:[], keywords:[],
  funding_amount: { currency, amount, range_text },
  eligibility, funding_type ("grant|fellowship|studentship|consortium|prize"),
  career_stage ("early|mid|senior|any" | null),
  country, region,
  open_date (ISO), deadline (ISO),
  url, status ("open|closed|forthcoming"),
  created_at, updated_at, last_seen_source_at
}
```

### `submissions` (Publication Hub)
```
{
  _id, manuscript_id, author_id (lead/submitter),
  venue_kind ("journal|conference"), venue_id, venue_snapshot:{name,quartile?,acronym?},
  stage ("selected|ready|submitted|under_review|revision_requested|accepted|published|rejected|withdrawn"),
  submitted_at, decision_at, decision ("accept|minor|major|reject" | null),
  reviewer_feedback:[{round,reviewer_alias,body,created_at}],
  revision_notes:[{round,body,submitted_at}],
  final_outcome, doi (null),
  created_at, updated_at
}
```

## 4. Ingestion Architecture

```
                ┌───────────────────────────────────────┐
                │  APScheduler (in-process, cron-ish)   │
                │  - journals refresh: daily 02:00      │
                │  - conferences refresh: every 6h      │
                │  - grants refresh: daily 04:00        │
                └────────────┬──────────────────────────┘
                             ▼
                ┌───────────────────────────────────────┐
                │  IngestRunner.run(kind, providers,    │
                │     limit, cursor, since)             │
                │  - calls provider.fetch_batch()       │
                │  - normalizes via Normalizer          │
                │  - resolves duplicates (entity_key)   │
                │  - upserts (Mongo bulk_write)         │
                │  - records ingest_run audit row       │
                └────────────┬──────────────────────────┘
                             ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ OpenAlex │    │ Crossref │    │   DOAJ   │  (journals)
        ├──────────┤    ├──────────┤    ├──────────┤
        │ WikiCFP  │    │OpenResearch │ │   CORE   │  (conferences)
        ├──────────┤    ├──────────┤    ├──────────┤
        │ OpenAIRE │    │   NIH    │    │   UKRI   │  (grants)
        └──────────┘    └──────────┘    └──────────┘
```

### Entity resolution
* **Journals**: primary key = ISSN-L; fallback = normalized title + publisher.
* **Conferences**: primary key = `(acronym, year)`; fallback = normalized name + year.
* **Grants**: primary key = `(sponsor, external_id)`; fallback = title + funder.
* All providers contribute to the **same** record via `external_ids.<source>` — last-write-wins for soft fields, first-non-null for hard fields.

### Incremental sync
* Providers report `cursor` + `since_iso` and the runner persists per-(kind,source) state in `ingest_state` collection.
* The first run is always **bounded** by `INGEST_MAX_PER_RUN` (default 5000) to keep one cycle predictable; multi-run pagination resumes via cursor.

### Audit
* `ingest_runs` collection: `{kind, source, started_at, finished_at, fetched, upserted, errored, error_log, cursor_before, cursor_after}`.

## 5. Search Architecture

* MongoDB **text indexes** on each collection's canonical fields.
* Compound indexes for the hot filter combinations (e.g. `(open_access, quartile, subjects)`).
* `discovery_search` helper centralizes pagination + facet counts (aggregation `$facet`).
* Sorting: relevance (`textScore`) → popularity_score → updated_at.
* Pagination via offset+limit (cursor-mode reserved for future use).

### Scale roadmap
* ≤ 500k records: current Mongo text index is fine.
* > 500k or fuzzy queries needed: migrate to **Atlas Search** (same Mongo store, server-side `$search`).
* > 5M records: dedicated **Elasticsearch** with the same Normalizer output as input.

## 6. AI-Readiness

The schema is intentionally over-specified vs. what the UI uses today, so the matching layer (Phase 6) can read straight from these tables:

* Journal Matching: feed `subjects + scope_keywords + quartile + oa_status + apc_usd` into an LLM-ranked retriever vs. manuscript abstract.
* Conference Matching: filter by `research_areas + topics + submission_deadline > today + 4 weeks` then rank by abstract similarity.
* Grant Matching: filter by `research_areas ∩ user.research_areas + eligibility match + deadline > now`.
* Reviewer Matching: use `manuscript.keywords` → `journals.subjects` → joined to user.publications when those exist.

## 7. Operational Notes

* All HTTP clients live in `services/discovery/http.py` with a single shared `httpx.AsyncClient` (connection pooling) and exponential-backoff retry.
* Errors during ingest do NOT block other providers; each provider runs in its own try/except.
* The scheduler is **opt-in** (`DISCOVERY_SCHEDULER_ENABLED=1` env, default `0`) so we don't hammer external APIs in dev/CI.
* Manual sync trigger: `POST /api/discovery/sync/{kind}` (admin-only) accepts `{providers?:[], limit?:int}`.
