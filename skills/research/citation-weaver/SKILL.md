---
name: citation-weaver
description: "Weave citations into narrative text automatically."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Academic, Citation, Writing, NLP]
    related_skills: [academic-jargon-buster, programming-literature-review]
---

## Verification Hierarchy

**Always verify before claiming citation-weaver capability.**

1. **llms.txt index** — <https://hermes-agent.nousresearch.com/docs/llms.txt> — the entire docs set in one file. Query first.
2. **CLI reference** — `hermes --help`, `hermes citation-weaver --help` — command-level truth.
3. **Source tree** — <https://github.com/NousResearch/hermes-agent> — upstream changes, issues, PRs.
4. **This skill body** — what's documented here; treat as per-session context, not product gospel.

Never claim a citation-weaver feature you haven't verified. When in doubt, fetch `llms.txt` and search. If it's not there, check the source. If it's not in source either, mark as UNKNOWN.

## Professional Operating Standards

- **Verify before assertion** — never claim a citation-weaver feature you haven't executed.
- **Output over process narration** — report what changed and what's verified, not the steps taken.
- **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
- **Coordinate first, spawn second** — prefer in-session tools (`delegate_task`, `cronjob`) before long-lived processes.
- **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
- **Version everything** — bump `version` in frontmatter when behavior changes; keep metadata accurate.

# Citation Weaver Skill

Automatically weave citations into narrative text for academic writing. Accepts paper PDFs, TeX files, or raw text, identifies relevant citations from a database, and produces annotated text with citations embedded in proper academic format. Supports multiple citation styles (APA, MLA, Chicago, IEEE) and provides side-by-side preview of original text vs. cited text.