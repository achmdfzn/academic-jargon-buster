# Update Schedule — Academic Jargon Buster

Owner: Mamang, Divisi 3 Produk/Pengembangan (Kantor IT).
Notifier: Nona, Divisi 5 Notifikasi/Pengingat.
Repo: https://github.com/achmdfzn/academic-jargon-buster

## Cadence

**Daily — every day, ~10:00 WIB.**

- First daily run: **Thursday, 12 November 2026, ~10:00 WIB** (update #1 was run early on Wednesday, 11 November 2026, on Achmad's request).
- Before this change the schedule was monthly (1st of the month); Achmad changed it to daily on 11 November 2026 so the work happens every day.

Ad-hoc updates happen any time Achmad asks for one — the daily
schedule does not block that.

## What each daily update does

This schedule covers **all three** skills in this repo: Academic Jargon Buster, Citation Weaver (merged in 2026-11-11), and Skripsi Prompts (added 2026-11-11).

1. **Run the tests** — `python3 -m unittest discover -s tests -v`. All tests must pass before any release (jargon + citation-weaver tests together).
2. **Check the skills still match the repo** — `skills/research/academic-jargon-buster/SKILL.md` against the jargon code in `academic_tools.py`, `skills/research/citation-weaver/SKILL.md` against the citation code there, and `skills/research/skripsi-prompts/SKILL.md` against the `PROMPTS` templates, plus README and docs. Fix drift, don't let the spec and the code diverge.
3. **Review the dictionary** — add new jargon terms that came up in real academic use or in GitHub issues, with a plain-English explanation, field, and source for each. No invented terms, no invented sources.
4. **Version bump, only if something changed**
   - Dictionary additions / bug fixes → patch (1.0.0 → 1.0.1)
   - New output format or new input type → minor (1.0.0 → 1.1.0)
   - No changes → no release, just a note that the check passed.
   - Bump the version in the skill frontmatter and in the matching constant in `academic_tools.py` (`JARGON_VERSION`, `CITATION_VERSION`, `PROMPTS_VERSION`) together, then run the suite and `tests/test_structure.py`.
5. **Push to GitHub** (`main` branch) and verify the files are live on the repo page.
6. **Announce in Kantor IT — only when something changed** — Nona posts a short note in the group (🚀 Produk topic when its thread ID is known, otherwise General): what changed, the new version, and the repo link. If nothing changed that day, stay silent in the group (no daily spam) and just log that the check passed.

## Out of scope for the scheduled update

- No publishing, selling, or promoting without Achmad's explicit approval.
- No full ghostwriting features — the skill's limits in `SKILL.md` still apply.
- No breaking change to the CLI (`jargon_buster.py` arguments) without Achmad's approval.
