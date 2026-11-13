# Academic Jargon Buster

**One Python file. Every feature. Zero invented references.**

Your thesis draft is stiff. This one file loosens it up: it translates the jargon, weaves in real citations, suggests rewrites you approve, scores the whole thing, and checks whether a text reads like AI writing. Indonesian and English. One file, no install, no dependencies — copy `academic_tools.py` anywhere and run it.

```text
$ python3 academic_tools.py humanize naskah.txt --apply
In:  Penelitian ini melakukan pengukuran terhadap suhu ruangan. Selain itu,
     penelitian ini melakukan analisis terhadap data yang diperoleh.
Out: Penelitian ini mengukur suhu ruangan. Penelitian ini menganalisis
     data yang diperoleh.
```

## Why this one

- **One file, zero dependencies.** No install step, no package manager, no API key for the core tools. Copy it anywhere and it runs — Python 3.9 or newer.
- **It never invents a reference.** A `[cite:key]` with no bibliography entry prints as `[PERLU RUJUKAN: key]` — a gap to fill, not a paper to fake. DOI checks need both Crossref and OpenAlex to say 404 before calling one fake.
- **Suggestions, not silent rewrites.** Every rewrite is shown before/after, and nothing changes unless you pass `--apply`. The original is never touched: results go to `<file>.humanized.txt`.
- **Indonesian first.** The style signals are calibrated for Indonesian academic prose — light verbs, stacked connectors, `yang mana` calques — not translated English rules.
- **The web UI stays home.** `serve` runs on localhost only, with no CDN, no webfonts, no analytics. Your draft never leaves your machine.
- **Your history stays yours.** Analyses and references live in one local SQLite file (`~/.academic-tools/library.db`) — no account, no cloud, no sync to set up.
- **The AI detector is an indication, never proof.** It scores a text 0–100 from four stdlib signals (sentence-length variation, template phrases, lexical diversity, repeated sentence starters) with no language model behind it — human text can be flagged and AI text can pass, so the result must never be used to accuse anyone.

## The file

`academic_tools.py` (v1.27.6) holds everything — the jargon dictionary and translator, the citation engine with online reference lookup, 18 thesis prompts, a one-pass quality check (jargon + citations + DOI verification + a style check, one score 0–100, or a whole folder of chapters at once), style rewrite suggestions (before/after, applied only with `--apply`, including mechanical Indonesian spelling fixes), a heuristic AI-text detector (sentence-length variation, template phrases, lexical diversity, repeated sentence starters — an indication, never proof), a readability score (Flesch Reading Ease + Flesch-Kincaid Grade Level with the standard Flesch bands — an indication, not a verdict), a local library of past analyses and references (one SQLite file, no account), an internal duplication check against your own saved drafts, an interactive menu CLI, and a local web UI. The other `.py` files are thin wrappers, so old commands keep working.

## Quick start

```bash
git clone https://github.com/achmdfzn/academic-jargon-buster.git
cd academic-jargon-buster
python3 academic_tools.py                 # interactive menu
python3 academic_tools.py serve           # web UI at http://127.0.0.1:8000/
```

```
  ╭──────────────────────────────────────────────────────────────╮
  │ Academic Tools                                       v1.27.6 │
  │ ──────────────────────────────────────────────────────────── │
  │ Satu file. Semua alat. Tanpa referensi palsu.                │
  │ Jargon Buster  ·  Citation Weaver  ·  Prompt Skripsi         │
  │ id  ·  ketik angka, Enter untuk memilih                      │
  ╰──────────────────────────────────────────────────────────────╯
Daftar isi:
  1  Jargon Buster ................. terjemahkan istilah akademik
  2  Citation Weaver .................. sisipkan sitasi ke naskah
  3  Prompt Skripsi .............. template prompt untuk tiap bab
  4  Analisis Kualitas .... cek jargon, sitasi, dan DOI sekaligus
  5  Humanize .............. saran rewrite gaya (sebelum/sesudah)
  6  Pustaka .............................. riwayat & bibliografi
  7  Deteksi AI .................... cek apakah teks mirip tulisan AI
  8  Ganti bahasa (id/en)
  0  Keluar
```

Pick a number, follow the prompts: type text or read a file, pick a field, a citation style or a major, fill a thesis prompt, and a language. For scripts, skip the menu: `python3 academic_tools.py jargon ...`, `... cite ...`, `... prompts ...`, `... analyze ...`, `... humanize ...`, `... library ...`, or `... detect ...`.

## What it does

| Tool | In short |
| --- | --- |
| **Jargon Buster** | Finds jargon in your text and explains each term in plain language, with its source. 77 terms — physics, machine learning, usability, software engineering, research methods, statistics — including Indonesian aliases. |
| **Citation Weaver** | Turns `[cite:key]` markers into in-text citations plus a bibliography. 6 styles (APA, MLA, Chicago, IEEE, Harvard, Vancouver), 21 majors with a recommended style each. Look up real references by DOI or title from Crossref/OpenAlex instead of typing bibliography JSON by hand. Export the bibliography to BibTeX (`.bib`) for LaTeX/Overleaf or RIS (`.ris`) for Mendeley/Zotero/Word. Audit a manuscript's citations — find markers with no bibliography entry, entries never cited, and (optionally) dead DOI/arXiv links. Verify reference DOIs across Crossref and OpenAlex: a DOI found in either source is real; "missing" needs a checked source to answer 404 with no source erroring (a Crossref 404 is already "missing" when OpenAlex was merely skipped for lack of a key). |
| **Prompt Skripsi** | 18 ready-made prompt templates for thesis writing — roadmap, abstract, preface, problem statement, Bab 1–5, defense prep, publication. Every template has an Indonesian and an English version (`--lang en`). Pick one, fill in your title, theory, and method, paste the result into ChatGPT, Grok, Claude, Gemini, or Perplexity. |
| **Quality Check** | One pass over a manuscript: jargon found and explained, citations audited (missing / never used), DOIs verified, and stiff Indonesian prose flagged (light verbs, stacked connectors, passive pile-ups, calqued relatives, flat sentence rhythm) — one quality score 0–100 with recommendations. A style report, not a rewrite and not a detector dodge. Density signals need 10+ words and inclusive thresholds (≥ 1.0 / 2.0 / 5.0 per 100 words). Exits 1 when a citation is missing or a DOI is not found. Add `--suggest` for rewrite suggestions in the same pass, `--save` to record the run in the library, `--duplicates` to check sentences against your own saved drafts. With `--json` the result also carries `score_parts` (the four 25-point components). Or pass a folder instead of a file: `analyze folder/` analyzes every top-level `.txt`/`.md` file and prints a recap table plus the average — dotfiles are skipped, the order is case-insensitive; `--save` records each run with the file name as its title, and `--save --duplicates` also flags sentences repeated across chapters. Scoring: jargon is always 25 (so the floor is 75 with no references, 38 with references); citations are proportional — 25 × (cited − missing) / cited, so every marker missing scores 0; a DOI that could not be checked (`unverified`) earns half credit (12.5). An empty or whitespace-only text is an error (`teks kosong`), not a perfect score, and a file with an error (unreadable, empty, a failed duplicates check or save) is left out of the folder average. |
| **Humanize** | Style rewrite suggestions, shown before/after per pattern: light verbs become direct verbs ("melakukan pengukuran terhadap" → "mengukur"), connectors are dropped, "yang mana" splits the sentence. Spelling is fixed mechanically too — a curated table of fused words EYD writes separate ("disini" → "di sini", "didalam" → "di dalam", "terimakasih" → "terima kasih", "kerjasama" → "kerja sama", "masingmasing" → "masing-masing"), including clitic suffixes ("kerjasamaku" → "kerja samaku", "disinilah" → "di sinilah"). Passive voice, "dimana", flat rhythm, and unknown light verbs get guidance instead of a made-up rewrite. Nothing is changed unless you pass `--apply`: then the mechanical suggestions are written to `<file>.humanized.txt` (or `--out`, or `--in-place` with a `.bak` backup), guidance-only ones are left for the author, and overlapping spans are skipped. Exits 1 when it has suggestions. |
| **Library** | Analysis history and a personal bibliography in one local SQLite file (`~/.academic-tools/library.db`, no account, no cloud). `analyze --save` records a run — score, style, missing citations, DOI counts, suggestions, the text (first 100,000 characters) and its hash — and every reference in the bibliography is added to it (not only the cited ones). `library --history` lists past runs, `--show <id>` prints one in full, `--stats` shows the library statistics (runs, average score, best run, score trend, most-cited references), `--refs` / `--search` browse the bibliography, `--import` / `--export` move a `refs.json` in and out. Read-only commands never create the database file when it does not exist yet — an empty library is just empty. |
| **Duplication Check** | `duplicates naskah.txt` compares every sentence of at least 6 words against every sentence of your own saved runs in the library, plus against the other sentences of the text itself. A match is a normalized similarity of 0.8 or more (`--threshold` changes it); only the best match per sentence is reported, with the source run (id, title, date) or "naskah ini" for a repeat inside the text. The text itself is never matched against its own saved copy, so re-analyzing a saved run does not flag every sentence. Duplicates never change the score and never change the exit code of `analyze` — they are a warning to read, not a failure. `duplicates` itself exits 1 when it finds any. Also in the Pustaka menu (option 6) and as a checkbox on the Analisis Kualitas tab of the web UI. |
| **AI Detector** | A heuristic check whether a text reads like AI writing — sentence-length variation, template phrases, lexical diversity, repeated sentence starters — one AI score 0–100 with verdict bands (≥ 60 likely AI, 40–59 mixed / uncertain, < 40 likely human) and the most AI-like sentences highlighted. The top band is capped: a score of 60 or more only earns "likely AI" when at least 3 of the 4 signals apply — a short text with only two applicable signals is capped to "mixed / uncertain" no matter how high it scores, and the result says so (`verdict_capped`). Pure stdlib, no language model and no API, so the score is an **indication, never proof**: human text can be flagged and AI text can pass. Under 30 words the verdict is "too short". Detection never fails a run (exit 0), except bad input. Also useful as a mirror on your own draft after Humanize: if a humanized draft still scores high, its sentence structure is still too uniform. |
| **Readability** | Flesch Reading Ease + Flesch-Kincaid Grade Level (Flesch 1948) for a text — pure formulas on word/sentence/syllable counts, no language model, no API, no minimum word count. RE is clamped to 0–100, FKGL to a minimum of 0, both to 1 decimal, with the standard Flesch bands (90+ Very easy … below 30 Very difficult). Syllables are counted by KBBI syllabification (vowels a/e/i/o/u; diphthongs ai/au/ei/oi per EYD edisi V, plus the "eu" monophthong; a curated list of hiatus roots plus affix stripping keeps derivatives right, e.g. "dimainkan" is 4). `analyze` always computes it and shows it in the report, the `--json` output, and the web UI — but it never changes the 0–100 score, the four score parts, or the exit code. The formulas were calibrated for English, so on Indonesian text the score is an **indication, not a verdict**: Indonesian academic prose usually lands lower because Indonesian words average more syllables. `readability naskah.txt` (or `--text`, `--lang`, `--json`) is the standalone subcommand; there is no menu option. |
| **Menu CLI** | One command, all seven tools, bilingual prompts. |
| **Web UI** | The tools plus the library in a dashboard page: `python3 academic_tools.py serve`, then open http://127.0.0.1:8000/. A sidebar lists the six tools; the Analisis Kualitas tab shows the score as a gauge with the four 25-point components beside it, plus a Readability card (Flesch Reading Ease + band, FKGL, average words/sentence and syllables/word, word/sentence/syllable counts, and the honesty note). The tab has "Saran rewrite gaya", "Cek duplikasi dengan pustaka", and "Simpan ke pustaka" checkboxes, the suggestions card has a "Salin teks yang diperbaiki" button that copies the applied text, and an "Analisis se-folder" section uploads a whole folder (or several files) and returns the same recap table as `analyze folder/` — top-level .txt/.md only, the rest listed as skipped. The Deteksi AI tab shows the AI score on the same gauge (band colors reversed: a high AI score is red), the four signal components, the sentences scoring 70 or more, and the honesty note. The Pustaka tab opens with a Statistik card — runs, average score, best run, a score trend with a bar per run, and the most-cited references — then lists saved runs (click one for the full detail) and searches the personal bibliography. Localhost only, zero external resources — no CDN, no webfonts, no analytics. |

**The rule:** never invent a reference. A `[cite:key]` with no bibliography entry prints as `[PERLU RUJUKAN: key]` — a gap to fill, not a paper to fake.

## See it work

Jargon, translated:

```
In:  The renormalization group and gradient descent are core ideas.
Out: The renormalization group (a collection of techniques for studying
     how a system changes when you look at it at different scales) and
     gradient descent (a step-by-step method for finding the lowest point
     of a curve by repeatedly moving downhill) are core ideas.
```

Citations, woven (Indonesian, IEEE):

```
In:  ...menggunakan metode System Usability Scale (SUS) [cite:brooke1996].
Out: ...menggunakan metode System Usability Scale (SUS) [1].

     ## Daftar Pustaka
     [1] J. Brooke, "SUS: A 'quick and dirty' usability scale,"
         Usability Evaluation in Industry (Taylor & Francis), pp. 189-194, 1996.
```

## Use each tool on its own

```bash
python3 academic_tools.py jargon demos/jargon-buster/test_paper.txt
python3 academic_tools.py jargon demos/jargon-buster/test_paper.txt --format csv
python3 academic_tools.py jargon --list-terms --field general
python3 academic_tools.py jargon --update-dictionary --from new_terms.json
python3 academic_tools.py cite demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --lang id
python3 academic_tools.py cite demos/citation-weaver/example_en.txt --refs demos/citation-weaver/references.json --lang en --style ieee
python3 academic_tools.py cite --text "... [cite:vaswani2017]." --refs demos/citation-weaver/references.json --jurusan Kedokteran
python3 academic_tools.py prompts --list
python3 academic_tools.py prompts latar-belakang
python3 academic_tools.py prompts roadmap --set judul="..." --set teori="..." --set metode="..." --set bulan=6 --set tanggal="11 November 2026"
python3 academic_tools.py cite --lookup 10.1038/nature14539
python3 academic_tools.py cite --lookup "Deep learning" --add-to my-refs.json
python3 academic_tools.py cite --refs demos/citation-weaver/references.json --verify
python3 academic_tools.py analyze demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json
python3 academic_tools.py analyze --text "... [cite:devlin2019]." --refs demos/citation-weaver/references.json --json
python3 academic_tools.py analyze demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --suggest
python3 academic_tools.py humanize demos/jargon-buster/test_paper.txt
python3 academic_tools.py humanize naskah.txt --apply
python3 academic_tools.py humanize naskah.txt --apply --in-place
python3 academic_tools.py analyze naskah.txt --refs my-refs.json --save --title "Bab 1"
python3 academic_tools.py analyze naskah.txt --refs my-refs.json --duplicates
python3 academic_tools.py analyze skripsi/ --refs my-refs.json --save --duplicates
python3 academic_tools.py duplicates naskah.txt
python3 academic_tools.py duplicates --text "..." --threshold 0.7
python3 academic_tools.py detect naskah.txt
python3 academic_tools.py detect --text "..." --lang en --json
python3 academic_tools.py library --history
python3 academic_tools.py library --refs --search "deep learning"
python3 academic_tools.py library --import my-refs.json
python3 academic_tools.py serve --port 8000
```

`--version` prints the tool version plus every component version (`academic_tools.py 1.27.6 (cli …; jargon_buster …; citation_weaver …; skripsi_prompts …; academic_quality_check …; ai_detector …; readability 1.0.5)`); a subcommand's `--version` (e.g. `analyze --version`) prints just the tool version.

Title search needs a free `OPENALEX_API_KEY` — OpenAlex has required a key since February 2026 (about $0.001 per search under a ~$1/day free allowance). DOI lookups try Crossref first, so they keep working without a key. `--verify` checks every DOI against Crossref and OpenAlex; a DOI found in either source is real, and "missing" needs a checked source to answer 404 with no source erroring — a Crossref 404 is already "missing" when OpenAlex was merely skipped for lack of a key; only a source error, or nothing checked at all, leaves a DOI "unverified". It exits 1 only when a DOI is missing from a checked source; references without a DOI are reported as `no DOI` (use `--audit --check-links` for arXiv IDs and URLs).

## Layout

```
academic_tools.py            # everything (v1.27.6)
jargon_buster.py / citation_weaver.py / skripsi_prompts.py / academic_cli.py / ai_detector.py / readability.py   # thin wrappers
pyproject.toml               # optional: pipx install . / pip install .
.github/workflows/tests.yml  # CI: 3 OS x Python 3.9, 3.12, 3.13
skills/research/             # five skills: the three tools + a quality-check skill + an AI-detector skill
demos/jargon-buster/         # jargon example + sample paper
demos/citation-weaver/       # citation examples + 7 real references
docs/                        # per-tool notes, shared standards, update schedule
tests/                       # 890 tests, stdlib unittest only
```

## Skills

The `skills/research/` folders hold the same tools as agent skills: the three tools plus `academic-quality-check`, which documents the quality check, the style check, Humanize, the library, and the web UI, and `ai-detector`, which documents the heuristic AI-text detector. They follow the standard agent-skill format, so they also work in agents that load skills from a folder.

## Limits, honestly

- 77 dictionary terms is a sample, not a glossary. New terms need a real source.
- Citation formatting here is simplified — check the official style guide before submitting.
- Math notation is kept as-is; low-quality OCR can misfire.
- Style signals are calibrated for Indonesian academic prose — on English text, only sentence rhythm is actually judged.
- The AI detector is a stdlib heuristic, not a model: no perplexity from a real language model, so its bands are wide on purpose (the mixed band means "cannot tell") and short or rigidly formatted texts can score oddly in either direction.
- The web UI runs on localhost only and needs JavaScript for the buttons to work.
- The library is one local file — no sync between machines. Copy `~/.academic-tools/library.db` to take it with you.

## Tests

```bash
python3 -m unittest discover -s tests -v   # 890 tests, no dependencies
```

## License

MIT — see `LICENSE`.
