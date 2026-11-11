---
name: citation-weaver
description: "Weave citations into narrative text automatically."
version: 1.4.0
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

Build a bibliography without typing JSON by hand: fetch real metadata by DOI or title from Crossref and OpenAlex. Crossref needs no key; OpenAlex has required a free key since February 2026.

```bash
python3 academic_tools.py cite --lookup 10.1038/nature14539
python3 academic_tools.py cite --lookup "Deep learning" --add-to my-refs.json
python3 academic_tools.py cite --lookup 10.1038/nature14539 --key lecun2015 --add-to my-refs.json
```

Rules:

- **DOI lookups try Crossref first, then OpenAlex.** Title searches use OpenAlex.
- **Crossref is free and needs no key.** A polite mailto in the User-Agent puts requests in the APIs' polite pools.
- **Never invent a reference.** A failed lookup (not found, rate-limited, offline) is an error, never a guessed paper. A `[cite:key]` with no bibliography entry stays `[PERLU RUJUKAN: key]`.
- **OpenAlex requires a free API key** (since February 2026; about $1 of free usage per key per day — a single DOI/ID lookup is free, a search costs roughly $0.001). Create one at <https://openalex.org/settings/api> and set `OPENALEX_API_KEY`. On HTTP 401/403 the lookup says the key is missing; on HTTP 429 it says the daily allowance is exhausted. Either way it fails with a clear message instead of inventing a reference.

## DOI verification (v1.4.0)

Check that every DOI in a bibliography points at a real record before quoting it:

```bash
python3 academic_tools.py cite --refs my-refs.json --verify
```

- Each DOI is looked up in **Crossref and OpenAlex**; the table shows both columns and a verdict.
- **`ok` if either source has it.** arXiv and dataset DOIs register with DataCite, not Crossref, so requiring both would flag real papers.
- **`NOT FOUND` only when both sources answer 404.** A network error, a timeout, or a single checked source is `unverified`, not fake.
- **Without `OPENALEX_API_KEY` the OpenAlex column reads `no key`** and a Crossref miss stays `unverified`. Set the key to check both.
- **References without a DOI are `no DOI`.** Use `--audit --check-links` for arXiv IDs and plain URLs.
- Exit code is 1 only when a DOI is missing from both sources, 0 otherwise — safe for a CI step. Menu option 7 runs the same check.

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
- In the interactive menu, Citation Weaver option 4 looks a reference up and offers to save it to a bibliography file of your choice; option 7 verifies every DOI in a bibliography.