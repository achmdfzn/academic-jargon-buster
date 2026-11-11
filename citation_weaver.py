"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the citation functions so existing commands,
demos, and imports keep working unchanged.
"""

from academic_tools import (
    CITATION_VERSION as __version__,
    DISCIPLINES,
    STYLES,
    audit_citations,
    check_reference_links,
    cite_main,
    cite_main as main,
    export_bibtex,
    fetch_reference_by_doi,
    format_audit,
    format_reference,
    format_verification,
    load_references,
    lookup_reference,
    reference_key,
    save_reference,
    search_reference_by_title,
    style_for_discipline,
    verify_reference_dois,
    weave,
)

__all__ = [
    "DISCIPLINES",
    "STYLES",
    "audit_citations",
    "check_reference_links",
    "cite_main",
    "export_bibtex",
    "fetch_reference_by_doi",
    "format_audit",
    "format_reference",
    "format_verification",
    "load_references",
    "lookup_reference",
    "main",
    "reference_key",
    "save_reference",
    "search_reference_by_title",
    "style_for_discipline",
    "verify_reference_dois",
    "weave",
]

if __name__ == "__main__":
    raise SystemExit(main())
