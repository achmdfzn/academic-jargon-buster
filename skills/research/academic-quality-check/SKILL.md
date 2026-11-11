---
name: academic-quality-check
description: "One-pass quality check, style rewrite suggestions, a local library, and a web UI for student writing."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Academic, Quality, Writing, Style]
    related_skills: [academic-jargon-buster, citation-weaver, skripsi-prompts]
---

## Verification Hierarchy

**Always verify before claiming academic-quality-check capability.**

1. **llms.txt index** — <https://hermes-agent.nousresearch.com/docs/llms.txt> — the entire docs set in one file. Query first.
2. **CLI reference** — `hermes --help`, `hermes academic-quality-check --help` — command-level truth.
3. **Source tree** — <https://github.com/NousResearch/hermes-agent> — upstream changes, issues, PRs.
4. **This skill body** — what's documented here; treat as per-session context, not product gospel.

Never claim an academic-quality-check feature you haven't verified. When in doubt, fetch `llms.txt` and search. If it's not there, check the source. If it's not in source either, mark as UNKNOWN.

## Professional Operating Standards

- **Verify before assertion** — never claim an academic-quality-check feature you haven't executed.
- **Output over process narration** — report what changed and what's verified, not the steps taken.
- **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
- **Coordinate first, spawn second** — prefer in-session tools (`delegate_task`, `cronjob`) before long-lived processes.
- **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
- **Version everything** — bump `version` in frontmatter when behavior changes; keep metadata accurate.

# Academic Quality Check

One pass over a student manuscript that answers four questions at once: is the jargon explained, are the citations real, are the DOIs alive, and does the prose read like a person wrote it? Then, for the prose, it suggests concrete rewrites — before/after per pattern — and applies the mechanical ones only when asked. Everything lives in `academic_tools.py` (one file, standard library only) alongside the Jargon Buster, Citation Weaver, and Thesis Prompts tools.

## Quality check (`analyze`)

```bash
python3 academic_tools.py analyze naskah.txt --refs my-refs.json
python3 academic_tools.py analyze --text "... [cite:devlin2019]." --refs my-refs.json --json
python3 academic_tools.py analyze naskah.txt --refs my-refs.json --suggest
```

Four components, 25 points each, one score 0–100:

| Component | What it checks | 25 points when |
| --- | --- | --- |
| Jargon | Every jargon term in the text is found and explained (see `academic-jargon-buster`) | Terms found (explained by construction); no recognised jargon is neutral |
| Citations | `[cite:key]` / `\cite{key}` markers against the bibliography (see `citation-weaver`) | No marker is missing from the bibliography |
| DOI verification | Every DOI in the bibliography against Crossref and OpenAlex | Every DOI that exists is found in at least one source; entries without a DOI do not count as failures |
| Style | Five stiff-prose signals (below) | All five signals clean |

- **Without `--refs`, citation audit and DOI checks are skipped** (neutral 25 each) and the report says so.
- **`--no-verify`** skips DOI verification even when `--refs` is given.
- **`--suggest`** adds the Humanize rewrite suggestions to the same pass.
- **`--save`** records the run in the library (`--title` labels it, `--db` picks another database). The JSON result then carries `library_id`.
- **`--json`** prints the raw result (`jargon`, `citations`, `doi_verification`, `style`, `quality_score`, `recommendations`, `suggestions`).
- **Exit code is 1** when a citation is missing or a DOI is not found in either source, 0 otherwise. In the interactive menu, this is option 4, Analisis Kualitas.

## Style check (`check_style`)

Five signals, five points each, calibrated on Indonesian academic prose. On English text only sentence rhythm is judged.

| Signal | Flagged when |
| --- | --- |
| Light verbs | 2+ occurrences of `melakukan` / `memberikan` / `mengalami` / `melaksanakan` / `mengadakan` / `menjalani` + a nominalized noun, and more than 1.0 per 100 words |
| Connectors | 2+ stacked connectors (`selain itu`, `oleh karena itu`, `dengan demikian`, …), more than 2.0 per 100 words |
| Passive verbs | 3+ passive verbs (`dilakukan`, `diperoleh`, `ditunjukkan`, …), more than 5.0 per 100 words |
| `yang mana` / `dimana` | 1+ occurrence used as a relative pronoun |
| Sentence rhythm | 5+ sentences and 60% or more are within ±2 words of the mean sentence length |

The check is a report, not a rewrite and not a detector dodge. A text that passes all five scores 25/25.

## Humanize — rewrite suggestions

```bash
python3 academic_tools.py humanize naskah.txt
python3 academic_tools.py humanize naskah.txt --apply
python3 academic_tools.py humanize naskah.txt --apply --in-place
```

For each stiff pattern, Humanize proposes a concrete replacement and shows it before/after:

- **Light verbs become direct verbs** — "melakukan pengukuran terhadap" → "mengukur", "mengalami peningkatan sebesar 12%" → "naik 12%". The noun→verb table is written from Indonesian grammar; a trailing preposition that belongs to the frame (`terhadap`, `atas`, `antara`, `sebesar`, `kepada`) is dropped with it, while `untuk`, `dengan`, `dari`, `dalam` are kept because they change the meaning.
- **Connectors are dropped** — "Selain itu, penelitian…" → "Penelitian…", with the next word re-capitalized.
- **"yang mana" splits the sentence** — "…, yang mana hal ini mengurangi…" → "…. Hal ini mengurangi…".
- **Guidance instead of a made-up rewrite** for passive voice, `dimana`, flat rhythm, and light verbs with no known verb form. These need a human decision; no replacement is invented.

Rules:

- **Nothing is changed unless `--apply` is given.** Suggestions only; the author edits by hand.
- **`--apply` writes to `<file>.humanized.txt` by default** — the original is never touched. `--out <path>` picks the output file; `--in-place` overwrites the input and keeps a `.bak` copy. `--text --apply` prints the fixed text. Under the hood this is `apply_suggestions()` in `academic_tools.py`.
- **Guidance-only suggestions are skipped** on apply, and so is any suggestion whose span overlaps one already applied. Edits run from the end of the text backwards so offsets stay valid; only the neighbourhood of each edit is touched.
- **Exit code is 1** when there are suggestions, 0 when the style is already fluent. `--json` carries `fixed_text` plus `applied` / `skipped` counts when `--apply` is given. In the interactive menu, this is option 5, Humanize — it asks where to save the fixed text (empty = skip).

## Library — history & bibliography (`library`)

One local SQLite file, no account, no cloud: `~/.academic-tools/library.db` by default (override with `--db`, or the `ACADEMIC_LIBRARY_DB` environment variable).

```bash
python3 academic_tools.py analyze naskah.txt --refs my-refs.json --save --title "Bab 1"
python3 academic_tools.py library --history
python3 academic_tools.py library --show 3
python3 academic_tools.py library --refs --search "deep learning"
python3 academic_tools.py library --import my-refs.json
python3 academic_tools.py library --export library-refs.json
```

- **`analyze --save`** records the run (title, date, score 0–100, style, jargon count, missing citations, DOI counts, suggestions, the text and its hash). Every cited reference is upserted into the personal bibliography, so the bibliography grows from real use.
- **`library --history`** lists past runs, newest first. **`--show <id>`** prints one run in full, including the text.
- **`library --refs`** lists the personal bibliography; **`--search <query>`** matches key, title, authors, or DOI.
- **`library --import <refs.json>`** upserts a bibliography file (reports added vs updated); **`--export <out.json>`** writes the whole bibliography back out as `refs.json` for use with `cite` / `analyze --refs`.
- **`--json`** prints raw results for `--history`, `--show`, and `--refs` / `--search`.
- In the interactive menu, this is option 6, Pustaka (the analyze menu asks after each run whether to save it).

## Web UI (`serve`)

```bash
python3 academic_tools.py serve            # http://127.0.0.1:8000/
python3 academic_tools.py serve --port 8000
```

Localhost only, standard library `http.server`, no external resources (no CDN, no webfonts, no analytics). The Analisis Kualitas tab has "Saran rewrite gaya" and "Simpan ke pustaka" checkboxes; a saved run shows its library id, and the suggestions card has a "Salin teks yang diperbaiki" button that copies the applied text. JSON API: `/api/analyze`, `/api/jargon`, `/api/cite`, `/api/prompts`, `/api/prompts/fill`, `/api/humanize` (`apply: true` returns `fixed_text`). Request bodies are capped at 1 MB; errors are honest JSON 400 / 404 / 500.

## Rules (non-negotiable)

- **Never invent a reference, a term, a data point, or a source.** A `[cite:key]` with no bibliography entry prints as `[PERLU RUJUKAN: key]` — a gap to fill, not a paper to fake.
- **Suggestions are advisory.** A rewrite suggestion is shown before/after and applied only with `--apply`; a guidance-only suggestion is never auto-completed.
- **The student writes their own thesis.** This skill checks and suggests; it does not write whole chapters or fabricate references.
- **Indonesian first.** The style signals are calibrated for Indonesian academic prose; on English text only rhythm is judged.

## Usage

```bash
python3 academic_tools.py analyze demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --suggest
python3 academic_tools.py humanize demos/jargon-buster/test_paper.txt
python3 academic_tools.py serve --port 8000
```

Or open the interactive menu (`python3 academic_tools.py`) and pick option 4 (Analisis Kualitas), 5 (Humanize), or 6 (Pustaka).
