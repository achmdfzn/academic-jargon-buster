"""Compatibility shim — the implementation lives in academic_tools.py.

academic_tools.py holds every feature of this repo in one file.
This module re-exports the thesis-prompt functions so existing commands,
demos, and imports keep working unchanged.
"""

from academic_tools import (
    PROMPTS,
    PROMPTS_VERSION as __version__,
    fill_prompt,
    get_prompt,
    list_prompts,
    prompts_main,
    prompts_main as main,
)

__all__ = [
    "PROMPTS",
    "fill_prompt",
    "get_prompt",
    "list_prompts",
    "main",
    "prompts_main",
]

if __name__ == "__main__":
    raise SystemExit(main())
