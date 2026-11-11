"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the citation functions so existing commands,
demos, and imports keep working unchanged.
"""

from academic_tools import (
    CITATION_VERSION as __version__,
    DISCIPLINES,
    STYLES,
    cite_main as main,
    format_reference,
    load_references,
    style_for_discipline,
    weave,
)

__all__ = [
    "DISCIPLINES",
    "STYLES",
    "format_reference",
    "load_references",
    "main",
    "style_for_discipline",
    "weave",
]

if __name__ == "__main__":
    raise SystemExit(main())
