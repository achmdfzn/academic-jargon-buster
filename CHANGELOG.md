# Changelog

## 1.21.0 — 2026-11-12

- `analyze` now takes a folder: `analyze skripsi/` analyzes every top-level `.txt`/`.md` file in name order and prints a recap table (file, score, jargon, citations, DOI, style, duplicates) plus the average; `--json` prints the full per-file results. `--refs`, `--no-verify`, `--save` (each run recorded with the file name as its title), `--duplicates`, and `--db` all work; `--suggest` and `--title` are rejected for folders. With `--save --duplicates`, files analyzed earlier in the same run are already in the library, so a sentence repeated in a later chapter is flagged. A file that cannot be read (bad encoding, permissions) is recorded with its error and the rest still run; exit 1 when any file errors, has a missing citation, or a missing DOI. The interactive menu's Analisis Kualitas offers "Baca folder" as a third choice (and asks once whether to save all runs). The web UI has no folder upload yet — that needs multipart handling and stays a follow-up. `CLI_VERSION` 1.13.0 → 1.14.0; `QUALITY_VERSION` 1.2.3 → 1.2.4 (the quality-check skill documents the folder mode).
- 12 new tests (core + CLI + menu). Full suite 279/279.

## 1.20.0 — 2026-11-12

- Humanize gains a Tata tulis (spelling) pattern: a curated table of 41 fused words that EYD writes separate (or hyphenated) — "disini" → "di sini", "didalam" → "di dalam", "terimakasih" → "terima kasih", "kerjasama" → "kerja sama", "masingmasing" → "masing-masing", "di/dari/ke + tempat" ("dirumah" → "di rumah", "kekampus" → "ke kampus"), plus "-nya" forms ("didalamnya" → "di dalamnya", "kerjasamanya" → "kerja samanya"). Only always-wrong forms are in the table, so every fix is mechanical: suggested by `humanize` and `analyze --suggest`, applied by `--apply` (idempotent), shown in the web UI with an "Ejaan" label. Word boundaries keep "kerjasama" from matching inside "kerjasamanya"; "dimana" stays guidance (its fix depends on the sentence) and fused "di"+verb forms ("ditulis", "dibaca") are correct and untouched. The style score is unchanged — typos live in Humanize, not in the style check. `CLI_VERSION` 1.12.0 → 1.13.0; `QUALITY_VERSION` 1.2.2 → 1.2.3 (the quality-check skill documents the pattern).
- 8 new tests (whole table, sentence-initial capitalization, no false positives, apply + idempotence, analyze --suggest, web UI). Full suite 267/267.

## 1.19.0 — 2026-11-12

- New internal duplication check: `duplicates naskah.txt` (or `--text "..."`) compares every sentence of at least 6 words against every sentence of the user's own saved runs in the library, plus against the other sentences of the text itself. A match is a normalized difflib similarity of 0.8 or more (`--threshold` changes it, 0–1); only the best match per sentence is reported, with the source run (id, title, date) or "naskah ini" for a repeat inside the text. The text itself is never matched against its own saved copy (same SHA-256 hash), so re-analyzing a saved run does not flag every sentence. A word-overlap pre-filter (half the words of the shorter sentence shared) keeps the comparison fast. `analyze --duplicates` runs the same check in the quality pass (the result gains a `duplicates` key and the report a Duplikasi section); duplicates never change the score and never change the exit code — they are a warning to read, not a failure. `duplicates` itself exits 1 when it finds any, 0 when clean. Also in the interactive menu (Pustaka, option 6) and as a "Cek duplikasi dengan pustaka" checkbox on the Analisis Kualitas tab of the web UI, with a Duplikasi card in the result. `CLI_VERSION` 1.11.0 → 1.12.0; `QUALITY_VERSION` 1.2.1 → 1.2.2 (the quality-check skill documents the check). The structure guard's Python 3.9 stdlib fallback set now includes `difflib`.
- 17 new tests (core + CLI + menu + web UI). Full suite 259/259.

## 1.18.0 — 2026-11-12

- The interactive menu gets a new look: a rounded cover-page banner with a motto ("Satu file. Semua alat. Tanpa referensi palsu."), the menu becomes a "Daftar isi" with dot leaders, subsection headers are rules with the name embedded, and the analyze result opens with a score card — a total bar plus one bar per 25-point component (Jargon / Sitasi / DOI / Gaya). One restrained green accent on real terminals (bold titles, green rules and bars); colors are off when stdout is piped, off with `NO_COLOR`, and forceable with `ACADEMIC_COLOR=1`. The box, bars, and rules fall back to plain ASCII (`+===+`, `#`/`-`, `--`) when the console encoding cannot do them (cp1252), so the menu still renders on old Windows consoles. `CLI_VERSION` 1.10.0 → 1.11.0.
- Oversize request bodies are now drained (up to 2 MB) before the 413, so the client reliably receives the 413 instead of a broken pipe; absurd sizes still close the connection. Found while the v1.17.1 keep-alive test turned flaky.
- 2 new tests (dot-leader menu, ASCII fallback + color) and 2 extended (score bars in the analyze report). Full suite 242/242.

## 1.17.1 — 2026-11-12

- Audit fixes (full repo audit, 2026-11-12: 234 tests, docs, dictionary, library, web UI, skills, security — no blockers, 6 should-fix + 7 nice-to-have): a corrupt library `.db` now fails with a plain `pustaka rusak: <path> — hapus atau ganti file databasenya` (exit 1) instead of a raw sqlite3 traceback, in the `library` and `analyze --save` commands, the interactive menu, and the web UI (honest 400). A missing analysis id in the API now returns `{"error": "tidak ada analisis #99"}` without stray quotes. An oversize request body (> 1 MB) now answers 413 instead of 400 and closes the connection, so the unread body is no longer parsed as a new request on HTTP/1.1 keep-alive (which used to log a spurious 414 traceback). A lone `academic_tools.py` without `demos/` next to it now answers 400 `contoh bibliografi tidak ditemukan di folder ini` for sample refs instead of a generic 500. `docs/update-schedule.md` now covers all four skills (it said three) and the `QUALITY_VERSION`/`CLI_VERSION` bump step. The two remaining thesis-derived test fixtures were replaced with clearly fictional values. The substring-matcher trade-off (`validity` inside `invalidity`, `normality` inside `abnormality`) is now documented next to the `variance` note — word-boundary matching would also stop plurals such as `correlations` from matching. `QUALITY_VERSION` 1.2.0 → 1.2.1 (the quality-check skill now lists the 413).
- 6 new tests (corrupt db in CLI + API, 404 body exact, oversize 413 with keep-alive and no logged traceback, missing sample refs). Full suite 240/240.

## 1.17.0 — 2026-11-12

- The web UI gains a Pustaka tab: saved runs listed newest first (click one for the full detail, including the text), the personal bibliography below, and a search box (title, author, key, or DOI; Enter works too). Three new GET endpoints — `/api/library/history`, `/api/library/analysis?id=<n>`, `/api/library/refs?search=<q>` — each with `?limit=` clamped to 1–100; a missing analysis id is an honest 404, a bad id or limit a 400. The tab loads its data when opened, plus a "Muat ulang" button. Still one file, zero external resources. `QUALITY_VERSION` 1.1.0 → 1.2.0.
- 4 new tests (tab in the page, empty history, save → history → detail → refs search, error cases). Full suite 234/234.

## 1.16.1 — 2026-11-12

- Dictionary grows 32 → 52 terms: 10 statistics concepts (English + Indonesian alias each) — statistical significance, p-value, correlation, regression, standard deviation, null hypothesis, confidence interval, normality, multicollinearity, autocorrelation — in a new `statistics` field, filterable with `jargon --list-terms --field statistics`. Sources verified live the same day: Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed., SAGE) for the inference terms; Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed., Badan Penerbit Undip) for the classical-assumption tests (normality, multicollinearity, autocorrelation). "variance" was left out on purpose: the matcher is substring-based, so it would also match inside "covariance". `JARGON_VERSION` 1.0.4 → 1.0.5.
- 3 new tests (all 20 keys with sources, "null hypothesis" wins over "hypothesis", an Indonesian stats paragraph). Full suite 230/230.

## 1.16.0 — 2026-11-12

- New `library` subcommand: analysis history and a personal bibliography in one local SQLite file (`~/.academic-tools/library.db`, stdlib `sqlite3`, no account, no cloud; override with `--db` or `ACADEMIC_LIBRARY_DB`). `analyze --save` records a run — title, date, score 0–100, style, jargon count, missing citations, DOI counts, suggestions, the text and its SHA-256 hash — and upserts every cited reference into the personal bibliography. `library --history` lists past runs newest first, `--show <id>` prints one in full, `--refs` lists the bibliography, `--search <query>` matches key/title/authors/DOI, `--import <refs.json>` upserts a bibliography file (reports added vs updated), `--export <out.json>` writes it back out. `--json` for machine-readable output. `CLI_VERSION` 1.9.0 → 1.10.0.
- The interactive menu gains Pustaka as option 6 (language switch moves to 7); the analyze menu asks after each run whether to save it. The web UI's Analisis Kualitas tab gains a "Simpan ke pustaka" checkbox; a saved run shows its library id and `/api/analyze` carries `library_id`.
- The `academic-quality-check` skill (v1.0.0 → v1.1.0, `QUALITY_VERSION`) documents the library; the structure guard pins the skill coverage, the shim re-exports, and the stdlib-import fallback list now includes `datetime`, `hashlib`, and `sqlite3`.
- 17 new tests (library core + CLI + menu + web UI save). Full suite 227/227.

## 1.15.0 — 2026-11-12

- New skill `academic-quality-check` (v1.0.0, `QUALITY_VERSION`): documents the features that landed in v1.10.0–v1.14.0 with no skill coverage — the one-pass quality check (`analyze`, four 25-point components), the style check (five signals with thresholds), Humanize (suggest + `--apply`), and the web UI (`serve`, six JSON endpoints). The three existing skills now point at it: jargon-buster documents the analyze jargon half, citation-weaver the citation/DOI half, skripsi-prompts the Humanize + analyze workflow after drafting. The jargon-buster skill also stops claiming PDF/TeX input it never had — plain text only. A structure guard now checks that the skills document these features, so the gap cannot reopen.
- README rewritten around a before/after demo and a "Why this one" section (one file, zero dependencies, never invents a reference, suggestions not silent rewrites, Indonesian first, localhost-only web UI). Still 0 emoji. GitHub About rewritten to match.
- 4 new tests (skill-docs guard). Full suite 210/210.

## 1.14.0 — 2026-11-12

- `humanize` gains `--apply`: the mechanical suggestions are written out (light verbs, connectors, "yang mana"), guidance-only ones are skipped for the author, and overlapping spans are never double-applied. Edits run from the end of the text backwards so offsets stay valid; only the neighbourhood of each edit is touched (a doubled space at the splice is collapsed, a sentence-initial letter is re-capitalized only when the edit itself starts or ends a sentence). Output defaults to `<file>.humanized.txt` — the original is never touched unless you pass `--out <path>` or `--in-place` (which keeps a `.bak` copy). `--text --apply` prints the fixed text; `--json` carries `fixed_text` plus applied/skipped counts. `suggest_style_fixes()` takes `limit=None` so apply sees every suggestion, not just the first 10 shown. `CLI_VERSION` 1.8.0 → 1.9.0.
- Web UI: new `/api/humanize` endpoint (suggestions, plus `fixed_text` when `apply: true`) and a "Salin teks yang diperbaiki" button on the suggestions card. The interactive menu's Humanize option now asks where to save the fixed text (empty = skip).
- 18 new tests. Full suite 206/206. `apply_suggestions()` is re-exported by the `academic_cli` shim and pinned by the structure guard.

## 1.13.0 — 2026-11-12

- New `humanize` subcommand: style rewrite suggestions (before/after per pattern), built on the v1.11.0 style check — the missing half of Opsi B. Light verbs get a concrete verb ("melakukan pengukuran terhadap" → "mengukur", from an original noun→verb table written from Indonesian grammar); connectors are dropped (with the next word re-capitalized); "yang mana" splits the sentence. Passive voice, "dimana", flat rhythm, and light verbs with no known verb form get guidance instead of a made-up rewrite. Nothing is changed — suggestions only, the author edits by hand. Exits 1 when it has suggestions, 0 when the style is already fluent. `CLI_VERSION` 1.7.0 → 1.8.0.
- `analyze` gains `--suggest` (same suggestions inside the quality pass, plus a "Saran rewrite gaya" checkbox in the web UI's Analisis Kualitas tab). `analyze_text_quality()` takes `suggest=True` and carries a `suggestions` key in the result (empty unless requested). The interactive menu gains Humanize as option 5; language switch moves to 6.
- 27 new tests. Full suite 188/188. `suggest_style_fixes()`, `format_suggestions()`, and `humanize_main()` are re-exported by the `academic_cli` shim and pinned by the structure guard.

## 1.12.0 — 2026-11-12

- New `serve` subcommand: a local web UI for all four tools, built from this file alone (`python3 academic_tools.py serve`, then open http://127.0.0.1:8000/). Stdlib `http.server` plus an embedded page and a small JSON API (`/api/analyze`, `/api/jargon`, `/api/cite`, `/api/prompts`, `/api/prompts/fill`). Localhost only, 1 MB request cap, honest 400/404/500 errors. `CLI_VERSION` 1.6.0 → 1.7.0.
- The page is designed from our own brief, guided by the anti-slop purpose test (every visual choice must serve the work) and design-system thinking (tokens + components): a tool page, not a landing page — no hero, no gradients, paper background with ink text and one restrained green accent, system font stack, real Indonesian copy. Zero external resources: no CDN, no webfonts, no analytics — it works offline and sends nothing anywhere.
- 13 new tests (live HTTP against an ephemeral localhost port, including a no-external-resources check on the page). Full suite 161/161. The stdlib-import guard's Python 3.9 fallback list now includes `http`.

## 1.11.0 — 2026-11-12

- `analyze` gains a fourth component: a rule-based style check for stiff Indonesian academic prose (`check_style()`), written from Indonesian grammar, not copied from any other project. Five signals, five points each: light-verb constructions ("melakukan pengukuran"), stacked connectors, passive pile-ups, "yang mana"/"dimana" as relative pronouns, and flat sentence rhythm (60%+ of sentences within two words of the mean length). The score is now four parts of 25 (jargon, citations, DOI, style) = 100, no scaling. Style findings appear in the readable output, in `--json`, and as bilingual recommendations. A style report, not a rewrite and not a detector dodge. `CLI_VERSION` 1.5.0 → 1.6.0.
- Thresholds calibrated on this repo's own sample texts (all three pass 25/25); a deliberately stiff paragraph flags all five signals and scores 0/25 on style. `check_style()` is re-exported by the `academic_cli` shim and pinned by the structure guard.
- 7 new tests. Full suite 148/148.

## 1.10.0 — 2026-11-12

- `analyze_text_quality()` is finally wired up: new `analyze` subcommand (`python3 academic_tools.py analyze <file|--text> [--refs refs.json] [--lang id|en] [--json] [--no-verify]`) and menu option 4 (Quality Check). It checks jargon, audits citations, verifies DOIs, and prints one quality score 0–100 with recommendations; exits 1 when a citation is missing or a DOI is not found. `CLI_VERSION` 1.4.0 → 1.5.0.
- Scoring fixes in `analyze_text_quality()`: the three 25-point parts now scale to 0–100 (a clean text scores 100, not 75); references without a DOI no longer count as failed verifications; recommendations are bilingual in full; entries without a DOI are no longer reported as unverified DOIs.
- Shims re-export the full public surface: `citation_weaver` now exposes the lookup/verify family, `academic_cli` exposes `analyze_text_quality` / `format_analyze` / `format_banner` / `analyze_main`, and the `*_main` entry points are exported under their real names. The structure guard now checks this.
- Sample bibliography: `devlin2019` (BERT) now carries its real DOI `10.18653/v1/N19-1423` (verified against Crossref), so `--verify` can be demonstrated on the bundled data; `references.bib` regenerated.
- 11 new tests (engine, subcommand, menu, shim guard). Full suite 141/141.

## 1.9.0 — 2026-11-12

- New `cite --refs refs.json --verify` and menu option 7: check every reference DOI against Crossref and OpenAlex. A DOI found in either source counts as real (arXiv and datasets register with DataCite, not Crossref); "not found" needs both sources to answer 404; a network error or a single checked source stays "unverified". Without `OPENALEX_API_KEY` the OpenAlex column reads `no key`, so a Crossref miss is never reported as fake. Exits 1 only when a DOI is missing from both sources. Output has an Indonesian and an English table with a summary line. Menu option 7 runs the same check; `CLI_VERSION` 1.3.0 → 1.4.0. Citation Weaver skill v1.4.0.
- 12 tests cover one-source success, both-404, skipped key, no DOI, network error, the table, and `cite_main` exit codes. Full suite 130/130.

## 1.8.1 — 2026-11-12

- OpenAlex lookup corrected for the February 2026 API change: a key is now required for production use (free, about $1 of usage per key per day; a single DOI/ID lookup is free, a search is about $0.001). HTTP 401/403 now fails with "create a free key at openalex.org/settings/api and set OPENALEX_API_KEY" instead of a bare HTTP code, and the 429 message no longer claims one budget per IP address. Crossref is unchanged and still needs no key, so DOI lookups work without one. Citation Weaver skill v1.3.1.
- Two tests pin the 401 and 403 messages. Full suite 118/118.

## 1.8.0 — 2026-11-12

- New menu banner: a bordered panel with the version, the three tools, and a language hint, replacing the single `====` line. ASCII only, so the menu still renders when stdout is piped or the console is not UTF-8. `CLI_VERSION` 1.2.0 → 1.3.0.
- Two tests pin the banner (Indonesian and English) and the version shown in it. Full suite 116/116.
- CI: Python 3.9 on Linux runs on `ubuntu-22.04` (`ubuntu-latest` has no 3.9 toolcache build and the source build needs OpenSSL 1.1). Other combinations stay on `ubuntu-latest`.

## 1.7.0 — 2026-11-12

- Structure release, no new tool features. `academic_tools.py` is still the whole tool in one dependency-free file, and the four root `.py` files are still the same thin shims. What moved:
  - `demos/` is now symmetric: `demos/jargon-buster/` (example + sample paper) and `demos/citation-weaver/` (examples + 7 real references).
  - `docs/` is now `docs/standards/` (one shared professional-standards and verification-hierarchy pair instead of two copies that had already drifted), `docs/citation-weaver/jurusan.md`, and `docs/update-schedule.md`.
- Fixed: `to_annotated_markdown` annotated a repeated jargon term twice at its first occurrence and left later occurrences bare, because the second replacement matched inside the explanation it had just inserted. Matches are now spliced by span, so every occurrence is annotated exactly once. Regression test included. Jargon Buster skill v1.0.4.
- Added `pyproject.toml` (dynamic version from `academic_tools.__version__`; `pipx install .` provides the `academic-tools` command), a CI matrix (Ubuntu/Windows/macOS × Python 3.9/3.12/3.13), `.editorconfig`, and `.gitattributes` (LF everywhere).
- Added `tests/test_structure.py`: fails when the README test count or version is stale, a documented demo/docs path no longer exists, `academic_tools.py` imports a third-party module, or a `SKILL.md` version disagrees with the constant it documents.
- Docs corrected: README v1.3.0 → v1.7.0 and 15 → 18 prompts, `docs/jurusan.md` pointed at a non-existent `demos/references.json`, and the citation demo claimed four references (it has seven).
- Full suite 114/114.

## 1.6.0 — 2026-11-11

- Thesis Prompts grew from 15 to 18 templates: new abstrak (abstract), rumusan-masalah (problem statement & objectives, Bab 1), and kata-pengantar (preface). Every template now has an English version with the same placeholders — `prompts <id> --lang en` or menu option 3 with language switched to English. 6 new tests (18 prompts, bilingual placeholders, English fill, new categories); full suite 104/104. Skill skripsi-prompts v1.1.0, templates verified in sync with code (18 × 2).

## 1.5.0 — 2026-11-11

- Citation Weaver can now audit a manuscript before submission: `cite --refs refs.json --audit naskah.txt [--check-links]` (or menu Citation Weaver option 6) reports every `[cite:key]` / `\cite{key}` with no bibliography entry, every bibliography entry never cited, and — with `--check-links` — every cited DOI/arXiv/URL that no longer resolves (plain HEAD request; unreachable is reported, never faked). Exit 1 when a citation is missing or a link is dead, 0 when clean. 7 new tests; full suite 98/98. Citation Weaver skill v1.3.0.

## 1.4.0 — 2026-11-11

- Citation Weaver can now export a bibliography to BibTeX: `cite --refs refs.json --export-bibtex [--out refs.bib]`, or menu Citation Weaver option 5. Entry types follow the stored type (article, book, conference → @inproceedings, chapter → @incollection, other → @misc); arXiv IDs become `eprint` + `archivePrefix`, chapter page ranges split out of the venue into `pages = {189--194}`, LaTeX special characters are escaped, and only fields actually present are exported — nothing is invented. Sample output in `demos/citation-weaver/references.bib`. 9 new tests; full suite 91/91. Citation Weaver skill v1.2.0.

## 1.3.1 — 2026-11-11

- Dictionary grew from 22 to 32 terms: 10 research-methods terms students meet in almost every thesis — validity / validitas, reliability / reliabilitas, triangulation / triangulasi, purposive sampling, thematic analysis, operational definition, literature review. Every source verified the same day: Creswell & Creswell 2018 ('Research Design', 5th ed.), Denzin 1978 ('The Research Act', 2nd ed.), Patton 2015 ('Qualitative Research & Evaluation Methods', 4th ed.), Braun & Clarke 2006 ('Using thematic analysis in psychology'), Boote & Beile 2005 ('Scholars before researchers'). A regression test pins all 10 terms and their sources. Jargon Buster skill v1.0.3.

## 1.3.0 — 2026-11-11

- New: Citation Weaver reference lookup — fetch real reference metadata by DOI or title from Crossref and OpenAlex, instead of typing bibliography JSON by hand. `python3 academic_tools.py cite --lookup <DOI-or-title>` prints the reference as JSON; `--add-to my-refs.json` appends it (key auto-generated as first-author + year, e.g. `lecun2015`, with a letter suffix on collision; `--key` overrides). DOI lookups try Crossref first, then OpenAlex; title searches use OpenAlex. Both APIs are free, no key needed. A failed lookup (not found, rate-limited, offline) is a clear error, never an invented reference. Note: OpenAlex without a key shares one free daily budget per IP address — on HTTP 429, set `OPENALEX_API_KEY` (free at openalex.org) or retry later. Citation Weaver skill v1.1.0 documents the lookup; menu option 4 in Citation Weaver looks a reference up and offers to save it. Tests 61 → 81.

## 1.2.0 — 2026-11-11

- New: Thesis Prompts (Prompt Skripsi) — 15 ready-made prompt templates for thesis writing: research roadmap, Bab 1–5 (background, theory comparison, prior research review, methodology, variables, hypothesis, mixed-methods analysis, suggestions, limitations), defense prep (draft review, PowerPoint, cue cards), and publication (blog, journal). Pick a prompt, fill its placeholders with your own title/theory/method/data, paste into ChatGPT, Grok, Claude, Gemini, or Perplexity. Available as `python3 academic_tools.py prompts ...` and as menu option 3. New skill `skills/research/skripsi-prompts/` (v1.0.0) carries the same templates. Templates are original wording written for this repo; they guide the student's own writing and never write a whole thesis or invent references.
- Menu CLI is now 1 Jargon Buster, 2 Citation Weaver, 3 Prompt Skripsi, 4 language switch (was 1–3); CLI version 1.1.0. Tests 43 → 61.

## 1.1.1 — 2026-11-11

- Removed: a student thesis abstract demo and every mention of it, including from git history (history rewritten and force-pushed) — a thesis draft does not belong in a public repo. The Indonesian citation demo now uses the generic example. README rewritten shorter.

## 1.1.0 — 2026-11-11

- One file, every feature: new `academic_tools.py` (989 lines) merges Jargon Buster + Citation Weaver + the menu CLI into a single self-contained file — copy it anywhere, Python 3.9+ only, no dependencies. `jargon_buster.py`, `citation_weaver.py`, and `academic_cli.py` are now thin wrappers around it; every old command, demo, and import keeps working. Tests: 43/43 pass (4 new one-file tests, including wrapper identity checks).

## 1.0.2 — 2026-11-11 (continued)

- Citation Weaver sample bibliography grew from 4 to 7 references: Brooke 1996 (SUS), Likert 1932, Ferraiolo & Kuhn 1992 (RBAC) — all real and verified. The Indonesian demo weaves to IEEE [1][2][3] with a full Daftar Pustaka and zero missing references.

## 1.0.2 — 2026-11-11

- Dictionary grew from 13 to 22 terms: 9 terms from a real student abstract (management information system, SUS evaluation): System Usability Scale, usability, Object Relational Mapping, Likert scale, authentication, role-based access control — plus Indonesian aliases used in the source text (skala Likert, autentikasi, hak akses berbasis peran). Sources are real: Brooke 1996 (SUS), Likert 1932, ISO 9241-11, Ferraiolo & Kuhn 1992 (RBAC). A student abstract that previously matched 0 terms now matches 6 distinct terms. Deliberately NOT added: bare "framework" — it is ordinary academic English ("mathematical framework", "theoretical framework") and would false-positive on almost any paper; covered by a regression test.

## Unreleased — merged 2026-11-11

- Citation Weaver (skill v1.0.0) merged into this repo from its own short-lived repo `achmdfzn/citation-weaver` (deleted after the merge): `skills/research/citation-weaver/SKILL.md`, `citation_weaver.py`, `demos/citation-weaver/`, `tests/test_citation_weaver.py`, `docs/jurusan.md` + `docs/citation-weaver/`. 6 citation styles, 21 jurusan, bilingual `--lang id/en`. The separate repo no longer exists; this repo is now home to both academic skills.
- New: `academic_cli.py` — one interactive CLI for both tools, Claude-CLI style: `python3 academic_cli.py` opens a menu (1 Jargon Buster, 2 Citation Weaver, 3 switch language id/en, 0 exit), with sub-menus for typing text / reading a file, picking a field, citation style or major (major picks the recommended style automatically), and output language. `python3 academic_cli.py jargon ...` / `cite ...` skip the menu for scripting. Tests: 34/34 pass (11 new CLI tests).

## 1.0.1 — 2026-11-11

- Dictionary grew from 8 to 13 terms: peer review, hypothesis, methodology, qualitative research, quantitative research (all with plain-English explanations, field, and source).
- New: `python3 jargon_buster.py --list-terms [--field <field>]` lists the dictionary.
- Fixed: SKILL.md documented `jargon-buster --update-dictionary`, but the demo CLI didn't have it. It now works: `python3 jargon_buster.py --update-dictionary --from new_terms.json` adds terms from a JSON file into `dictionary.json` (loaded on every run). Without `--from`, it lists the current terms for the field.
- No CLI arguments changed, no behaviour change for existing terms.

## 1.0.0 — 2026-11-11

- Initial release: Hermes skill v1.0.0 + standalone `jargon_buster.py` (8-term dictionary, annotated Markdown / CSV output, 7 tests).
