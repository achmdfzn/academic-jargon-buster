"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the interactive menu CLI so the familiar
command keeps working: python3 academic_cli.py
"""

from academic_tools import (
    CLI,
    CLI_VERSION as __version__,
    analyze_folder,
    analyze_main,
    analyze_text_quality,
    apply_suggestions,
    check_style,
    duplicates_main,
    export_references,
    find_duplicates,
    format_analyze,
    format_banner,
    format_duplicates,
    format_folder_result,
    format_library_stats,
    format_suggestions,
    get_analysis,
    humanize_main,
    import_references,
    library_main,
    library_stats,
    list_analyses,
    list_references,
    main,
    open_library,
    save_analysis,
    search_references,
    suggest_style_fixes,
)

__all__ = [
    "CLI",
    "analyze_folder",
    "analyze_main",
    "analyze_text_quality",
    "apply_suggestions",
    "check_style",
    "duplicates_main",
    "export_references",
    "find_duplicates",
    "format_analyze",
    "format_banner",
    "format_duplicates",
    "format_folder_result",
    "format_library_stats",
    "format_suggestions",
    "get_analysis",
    "humanize_main",
    "import_references",
    "library_main",
    "library_stats",
    "list_analyses",
    "list_references",
    "main",
    "open_library",
    "save_analysis",
    "search_references",
    "suggest_style_fixes",
]

if __name__ == "__main__":
    raise SystemExit(main())
