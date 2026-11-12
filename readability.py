"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the readability scorer so existing commands,
demos, and imports keep working unchanged.
"""

from academic_tools import (
    READABILITY_VERSION as __version__,
    format_readability,
    readability_main,
    readability_score,
)

__all__ = [
    "readability_score",
    "readability_main",
    "format_readability",
]

if __name__ == "__main__":
    raise SystemExit(readability_main())
