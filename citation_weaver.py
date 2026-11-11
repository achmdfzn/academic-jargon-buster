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
    cite_main as main,
    export_bibtex,
    format_audit,
    format_reference,
    load_references,
    style_for_discipline,
    weave,
)

__all__ = [
    "DISCIPLINES",
    "STYLES",
    "audit_citations",
    "check_reference_links",
    "export_bibtex",
    "format_audit",
    "format_reference",
    "load_references",
    "main",
    "style_for_discipline",
    "weave",
]

if __name__ == "__main__":
    raise SystemExit(main())
