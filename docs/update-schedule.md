# Update Schedule — Academic Jargon Buster

Owner: Mamang, Divisi 3 Produk/Pengembangan (Kantor IT).
Notifier: Nona, Divisi 5 Notifikasi/Pengingat.
Repo: https://github.com/achmdfzn/academic-jargon-buster

## Cadence

**Monthly — every 1st of the month, ~10:00 WIB.**

- Next update: **Tuesday, 1 December 2026, ~10:00 WIB**
- After that: 1 January 2027, 1 February 2027, and so on, on the 1st of each month.

Ad-hoc updates happen any time Achmad asks for one — the monthly
schedule does not block that.

## What each monthly update does

1. **Run the tests** — `python3 -m unittest discover -s tests -v`. All tests must pass before any release.
2. **Check the skill still matches the repo** — `skills/research/academic-jargon-buster/SKILL.md` (v1.0.0) against `jargon_buster.py`, README, and docs. Fix drift, don't let the spec and the code diverge.
3. **Review the dictionary** — add new jargon terms that came up in real academic use or in GitHub issues, with a plain-English explanation, field, and source for each. No invented terms, no invented sources.
4. **Version bump, only if something changed**
   - Dictionary additions / bug fixes → patch (1.0.0 → 1.0.1)
   - New output format or new input type → minor (1.0.0 → 1.1.0)
   - No changes → no release, just a note that the check passed.
   - Bump the version in the skill frontmatter and in `jargon_buster.py` together.
5. **Push to GitHub** (`main` branch) and verify the files are live on the repo page.
6. **Announce in Kantor IT** — Nona posts a short note in the group (🚀 Produk topic when its thread ID is known, otherwise General): what changed, the new version, and the repo link. If nothing changed, one line saying the check passed is enough.

## Out of scope for the scheduled update

- No publishing, selling, or promoting without Achmad's explicit approval.
- No full ghostwriting features — the skill's limits in `SKILL.md` still apply.
- No breaking change to the CLI (`jargon_buster.py` arguments) without Achmad's approval.
