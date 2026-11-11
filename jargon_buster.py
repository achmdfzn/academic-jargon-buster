"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the jargon functions so existing commands,
demos, and imports keep working unchanged.
"""

from academic_tools import (
    DICTIONARY,
    JARGON_VERSION as __version__,
    _user_dictionary_path,
    find_terms,
    jargon_main as main,
    list_terms,
    load_dictionary,
    to_annotated_markdown,
    to_csv,
    update_dictionary,
)

__all__ = [
    "DICTIONARY",
    "_user_dictionary_path",
    "find_terms",
    "list_terms",
    "load_dictionary",
    "main",
    "to_annotated_markdown",
    "to_csv",
    "update_dictionary",
]

if __name__ == "__main__":
    raise SystemExit(main())
