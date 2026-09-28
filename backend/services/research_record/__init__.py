"""Academic Research Record — Phase 1 consolidation.

One canonical bibliographic record (the existing `publications` collection,
extended) for academic work, whether it predates Synaptiq (imported via
ORCID/Crossref/OpenAlex/DOI/manual entry) or was created inside Synaptiq
(a manuscript explicitly published).

Modules:
  doi_normalize — canonical DOI normalization/validation (wraps the existing
                  services/rule_engine/validation/format_validator.py; does
                  not reimplement DOI parsing)
  doi_lookup     — Crossref + OpenAlex metadata fetch/merge for DOI preview
  dedup          — DOI-based and non-DOI confidence-based deduplication
  authors        — the publication_authors relationship collection
                    (a publication is a global record; a Synaptiq user's
                    relationship to it is a separate, many-to-one concept)
  manuscript_link — the explicit manuscript -> Research Record publish action
"""
