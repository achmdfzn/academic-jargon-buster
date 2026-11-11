# Changelog

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
