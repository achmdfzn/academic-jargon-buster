---
name: citation-weaver
description: "Weave citations into narrative text automatically."
version: 1.3.0
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

## Reference lookup (v1.1.0)

Build a bibliography without typing JSON by hand: fetch real metadata by DOI or title from Crossref and OpenAlex.

```bash
python3 academic_tools.py cite --lookup 10.1038/nature14539
python3 academic_tools.py cite --lookup "Deep learning" --add-to my-refs.json
python3 academic_tools.py cite --lookup 10.1038/nature14539 --key lecun2015 --add-to my-refs.json
```

Rules:

- **DOI lookups try Crossref first, then OpenAlex.** Title searches use OpenAlex.
- **Both APIs are free and need no key.** A polite mailto in the User-Agent puts requests in the APIs' polite pools.
- **Never invent a reference.** A failed lookup (not found, rate-limited, offline) is an error, never a guessed paper. A `[cite:key]` with no bibliography entry stays `[PERLU RUJUKAN: key]`.
- **OpenAlex without a key shares one free daily budget per IP address.** On HTTP 429, the lookup fails with a clear message: try again later, or set `OPENALEX_API_KEY` (free at <https://openalex.org/>) to raise the limit.

## BibTeX export (v1.2.0)

Export a bibliography JSON file to a `.bib` file ready for LaTeX / Overleaf:

```bash
python3 academic_tools.py cite --refs my-refs.json --export-bibtex --out my-refs.bib
# or print to stdout: omit --out
```

Entry types follow the stored `type`: `article` → `@article`, `book` → `@book`, `conference` → `@inproceedings`, `chapter` → `@incollection`, anything else → `@misc`. arXiv IDs become `eprint` + `archivePrefix`. Chapter page ranges split out of the venue into `pages = {189--194}`. LaTeX special characters (`& % $ # _ { } ~ ^ \`) are escaped. Only fields actually present are exported — a missing title simply means no title field, never an invented one. A sample export of the bundled bibliography lives in `demos/citation-weaver/references.bib`.

## Citation audit (v1.3.0)

Before a manuscript is submitted, audit its citations against the bibliography:

```bash
python3 academic_tools.py cite --refs my-refs.json --audit naskah.txt --check-links
```

The report lists every `[cite:key]` / `\cite{key}` with no bibliography entry (the reader can never check it), every bibliography entry never cited, and — with `--check-links` — every cited DOI / arXiv / URL that no longer resolves (plain HEAD request). A link that cannot be reached is reported as unreachable, never faked as alive. Exit code is 1 when a citation is missing or a link is dead, 0 when clean — so it fits in a pre-submission checklist or a CI step.
- **Keys are automatic** (first author family name + year, e.g. `lecun2015`) and get a letter suffix on collision (`lecun2015a`). Use `--key` to pick your own.
- In the interactive menu, Citation Weaver option 4 looks a reference up and offers to save it to a bibliography file of your choice.