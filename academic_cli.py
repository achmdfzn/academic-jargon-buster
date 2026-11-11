"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the interactive menu CLI so the familiar
command keeps working: python3 academic_cli.py
"""

from academic_tools import (
    CLI,
    CLI_VERSION as __version__,
    analyze_main,
    analyze_text_quality,
    check_style,
    format_analyze,
    format_banner,
    format_suggestions,
    humanize_main,
    main,
    suggest_style_fixes,
)

__all__ = [
    "CLI",
    "analyze_main",
    "analyze_text_quality",
    "check_style",
    "format_analyze",
    "format_banner",
    "format_suggestions",
    "humanize_main",
    "main",
    "suggest_style_fixes",
]

if __name__ == "__main__":
    raise SystemExit(main())
