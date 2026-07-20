from .format_validator import (
    ValidationResult,
    validate_doi, normalize_doi,
    validate_orcid,
    validate_isbn,
    validate_issn,
    validate_email,
    validate_url,
)
from .reference_validator import (
    validate_apa_reference, validate_apa_reference_list,
    validate_ieee_reference, validate_ieee_reference_list,
    find_duplicate_references,
)
from .manuscript_validator import (
    ManuscriptIssue, ManuscriptValidationReport,
    validate_abstract, validate_keywords,
    validate_manuscript_sections, validate_reference_count,
    validate_manuscript,
)
from .content_validator import (
    validate_profile_completeness, validate_required_fields,
    detect_duplicates, validate_text_length, validate_orcid_profile,
)

__all__ = [
    "ValidationResult",
    "validate_doi", "normalize_doi", "validate_orcid", "validate_isbn",
    "validate_issn", "validate_email", "validate_url",
    "validate_apa_reference", "validate_apa_reference_list",
    "validate_ieee_reference", "validate_ieee_reference_list",
    "find_duplicate_references",
    "ManuscriptIssue", "ManuscriptValidationReport",
    "validate_abstract", "validate_keywords",
    "validate_manuscript_sections", "validate_reference_count",
    "validate_manuscript",
    "validate_profile_completeness", "validate_required_fields",
    "detect_duplicates", "validate_text_length", "validate_orcid_profile",
]
