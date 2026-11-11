# Changelog

## 1.0.1 — 2026-11-11

- Dictionary grew from 8 to 13 terms: peer review, hypothesis, methodology, qualitative research, quantitative research (all with plain-English explanations, field, and source).
- New: `python3 jargon_buster.py --list-terms [--field <field>]` lists the dictionary.
- Fixed: SKILL.md documented `jargon-buster --update-dictionary`, but the demo CLI didn't have it. It now works: `python3 jargon_buster.py --update-dictionary --from new_terms.json` adds terms from a JSON file into `dictionary.json` (loaded on every run). Without `--from`, it lists the current terms for the field.
- No CLI arguments changed, no behaviour change for existing terms.

## 1.0.0 — 2026-11-11

- Initial release: Hermes skill v1.0.0 + standalone `jargon_buster.py` (8-term dictionary, annotated Markdown / CSV output, 7 tests).
