# Changelog

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
