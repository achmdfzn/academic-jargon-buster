"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the interactive menu CLI so the familiar
command keeps working: python3 academic_cli.py
"""

from academic_tools import CLI, CLI_VERSION as __version__, main

__all__ = ["CLI", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
