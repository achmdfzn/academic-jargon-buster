# Professional Operating Standards

Operating standards carried by the academic-jargon-buster skill (v1.0.0). They apply to the skill and to this repo.

1. **Verify before assertion** — never claim a feature you haven't executed.
2. **Output over process narration** — report what changed and what's verified, not the steps taken.
3. **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
4. **Coordinate first, spawn second** — prefer in-session tools before long-lived processes.
5. **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
6. **Version everything** — bump `version` in the skill frontmatter when behaviour changes; keep metadata accurate.

## Notes on this repo

- The `SKILL.md` frontmatter says version 1.0.0, license MIT, tags `[Academic, Jargon, NLP, Translation]`, related skills `[programming-literature-review, grounded-citations]`.
- The actual `SKILL.md` file in this repo is 4,104 bytes — not 6,705 chars as an earlier draft claimed. That earlier figure was wrong; the file was copied verbatim, so the repo matches the real skill.
- The demo code (`jargon_buster.py`) is a standalone reference implementation. It does not pretend to be the Hermes runtime, and it does not import a `hermes_tools` package (no such import exists in this repo).
