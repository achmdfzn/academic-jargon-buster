# Professional Operating Standards

Operating standards for the four skills in this repo — academic-jargon-buster,
citation-weaver, skripsi-prompts, academic-quality-check — and for the repo itself. Each `SKILL.md`
restates them for its own tool; this file is the single source so the copies
cannot drift.

1. **Verify before assertion** — never claim a feature you haven't executed.
2. **Output over process narration** — report what changed and what's verified,
   not the steps taken.
3. **Fail with evidence** — on a blocker, paste the exact error and say what you
   tried, then stop or escalate.
4. **Coordinate first, spawn second** — prefer in-session tools before
   long-lived processes.
5. **Ops discipline** — one operation per batch call; atomic results; roll back
   on failure.
6. **Version everything** — bump the version when behaviour changes; keep
   metadata accurate.

## Applying them here

- **One version source.** `academic_tools.py` holds `__version__` and the
  per-tool constants (`JARGON_VERSION`, `CITATION_VERSION`, `PROMPTS_VERSION`,
  `QUALITY_VERSION`, `CLI_VERSION`); each `SKILL.md` frontmatter repeats the matching tool version.
  `tests/test_structure.py` fails the suite when the two disagree.
- **The core is one file.** `academic_tools.py` must keep working when copied
  alone: no imports outside the standard library, no sibling-file dependencies.
  The root `jargon_buster.py`, `citation_weaver.py`, `skripsi_prompts.py`, and
  `academic_cli.py` are compatibility shims and stay importable.
- **Never invent references.** An unknown `[cite:key]` is marked
  `[PERLU RUJUKAN: key]` / `[REFERENCE NEEDED: key]`, never filled in with a
  made-up paper. The bundled bibliography holds real, verifiable entries only.
- **Check the official style guide** before submitting a thesis or journal
  paper: citation formatting here is simplified by design.
