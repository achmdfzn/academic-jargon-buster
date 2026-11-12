---
name: academic-quality-check
description: "One-pass quality check, style rewrite suggestions, a local library, and a web UI for student writing."
version: 1.2.6
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
- **`--duplicates`** also checks every sentence against the saved runs in the library and reports near-duplicates (same or nearly the same sentence in an earlier draft, or repeated inside the text itself). The JSON result then carries `duplicates`. Duplicates never change the score and never change the exit code — they are a warning to read, not a failure.
- **A folder instead of a file** — `analyze <folder>` analyzes every top-level `.txt`/`.md` file in the folder, in name order, and prints a recap table (file, score, jargon, citations, DOI, style, duplicates) plus the average. `--refs`, `--no-verify`, `--save` (each run recorded with the file name as its title), `--duplicates`, `--db`, and `--json` all work; `--suggest` and `--title` are rejected for folders. With `--save --duplicates`, files analyzed earlier in the same run are already in the library, so a sentence repeated in a later chapter is flagged. A file that cannot be read is recorded with its error and the rest still run. In the interactive menu, Analisis Kualitas offers "Baca folder" as a third choice; the web UI has no folder upload yet.
- **`--save`** records the run in the library (`--title` labels it, `--db` picks another database). The JSON result then carries `library_id`.
- **`--json`** prints the raw result (`jargon`, `citations`, `doi_verification`, `style`, `quality_score`, `recommendations`, `suggestions`, `duplicates` when `--duplicates` was passed).
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
- **Spelling (Tata tulis) is fixed mechanically** — a curated table of fused words that EYD writes separate (or hyphenated): "disini" → "di sini", "didalam" → "di dalam", "terimakasih" → "terima kasih", "kerjasama" → "kerja sama", "masingmasing" → "masing-masing", plus "-nya" forms ("didalamnya" → "di dalamnya", "kerjasamanya" → "kerja samanya"). Only always-wrong forms are in the table; "dimana" stays guidance (its fix depends on the sentence) and fused "di"+verb forms ("ditulis", "dibaca") are correct and untouched. Word boundaries keep "kerjasama" from matching inside "kerjasamanya".
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
python3 academic_tools.py library --stats
python3 academic_tools.py library --refs --search "deep learning"
python3 academic_tools.py library --import my-refs.json
python3 academic_tools.py library --export library-refs.json
```

- **`analyze --save`** records the run (title, date, score 0–100, style, jargon count, missing citations, DOI counts, suggestions, the text and its hash). Every cited reference is upserted into the personal bibliography, so the bibliography grows from real use.
- **`library --history`** lists past runs, newest first. **`--show <id>`** prints one run in full, including the text.
- **Library statistics (`library --stats`)** — runs, average score, best run, a score trend (every run oldest first, one bar per run), and the top 5 most-cited references (by how many saved runs cite them). Empty library prints an honest "run `analyze --save` first" instead of zeros. In the interactive menu, this is option 7 in Pustaka.
- **`library --refs`** lists the personal bibliography; **`--search <query>`** matches key, title, authors, or DOI.
- **`library --import <refs.json>`** upserts a bibliography file (reports added vs updated); **`--export <out.json>`** writes the whole bibliography back out as `refs.json` for use with `cite` / `analyze --refs`.
- **Duplication check (`duplicates`)** — `python3 academic_tools.py duplicates naskah.txt` (or `--text "..."`) compares each sentence of at least 6 words against every sentence of every saved run, plus against the other sentences of the text itself. A match is a normalized similarity of 0.8 or more (`--threshold` changes it, 0–1); only the best match per sentence is reported, with the source run (id, title, date) or "naskah ini" for a repeat inside the text. The text itself is never matched against its own saved copy. Exit 1 when duplicates are found, 0 when clean. In the interactive menu, this is option 6 in Pustaka; in the web UI, the Analisis Kualitas tab has a "Cek duplikasi dengan pustaka" checkbox.
- **`--json`** prints raw results for `--history`, `--show`, and `--refs` / `--search`.
- In the interactive menu, this is option 6, Pustaka (the analyze menu asks after each run whether to save it).

## Web UI (`serve`)

```bash
python3 academic_tools.py serve            # http://127.0.0.1:8000/
python3 academic_tools.py serve --port 8000
```

Localhost only, standard library `http.server`, no external resources (no CDN, no webfonts, no analytics). The Analisis Kualitas tab has "Saran rewrite gaya" and "Simpan ke pustaka" checkboxes; a saved run shows its library id, and the suggestions card has a "Salin teks yang diperbaiki" button that copies the applied text. The same tab has an "Analisis se-folder" section: pick a whole folder (or several files) and the recap table from `analyze <folder>` comes back — same rules (top-level .txt/.md only, in name order; subfolder files and other extensions are listed as skipped, not failed), same verify / duplicates / save checkboxes, bibliography and language from the tab's own selectors. The upload is `POST /api/analyze-folder` (multipart/form-data, 10 MB body cap, honest 400/413; the parser is hand-written stdlib — `cgi` is gone in Python 3.13). The Pustaka tab opens with a Statistik card — runs, average score, best run, a score trend with a bar per run, and the most-cited references — then lists saved runs — click one for the full detail, including the text — and searches the personal bibliography. JSON API: `/api/analyze`, `/api/jargon`, `/api/cite`, `/api/prompts`, `/api/prompts/fill`, `/api/humanize` (`apply: true` returns `fixed_text`), plus GET `/api/library/history`, `/api/library/analysis?id=<n>`, `/api/library/refs?search=<q>`, `/api/library/stats` (each with `?limit=` up to 100; a missing analysis id is a 404). Request bodies are capped at 1 MB; errors are honest JSON 400 / 404 / 413 / 500 (413 when the body is over the cap).

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
