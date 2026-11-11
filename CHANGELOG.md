# Changelog

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
