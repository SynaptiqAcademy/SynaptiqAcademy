from .text_normalizer import (
    normalize_whitespace, normalize_unicode, strip_html,
    normalize_author_name, normalize_institution_name,
    normalize_country_name, normalize_journal_title,
    clean_academic_text,
)
from .reference_normalizer import (
    normalize_reference, normalize_doi_field, normalize_title,
    normalize_page_range, normalize_year, normalize_author_list,
    extract_doi_from_text, clean_reference_list,
)
from .apa_formatter import (
    format_apa_journal, format_apa_book, format_apa_chapter,
    format_apa_conference, build_apa_reference,
)
from .ieee_formatter import (
    format_ieee_journal, format_ieee_book, format_ieee_conference,
    build_ieee_reference, build_ieee_reference_list,
)

__all__ = [
    "normalize_whitespace", "normalize_unicode", "strip_html",
    "normalize_author_name", "normalize_institution_name",
    "normalize_country_name", "normalize_journal_title",
    "clean_academic_text",
    "normalize_reference", "normalize_doi_field", "normalize_title",
    "normalize_page_range", "normalize_year", "normalize_author_list",
    "extract_doi_from_text", "clean_reference_list",
    "format_apa_journal", "format_apa_book", "format_apa_chapter",
    "format_apa_conference", "build_apa_reference",
    "format_ieee_journal", "format_ieee_book", "format_ieee_conference",
    "build_ieee_reference", "build_ieee_reference_list",
]
