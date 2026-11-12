"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the AI detector so existing commands,
demos, and imports keep working unchanged.
"""

from academic_tools import (
    DETECTOR_VERSION as __version__,
    detect_ai,
    detect_main,
    format_detect,
)

__all__ = [
    "detect_ai",
    "detect_main",
    "format_detect",
]

if __name__ == "__main__":
    raise SystemExit(detect_main())
