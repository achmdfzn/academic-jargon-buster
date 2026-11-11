# Professional Operating Standards

Operating standards carried by the citation-weaver skill (v1.0.0). They apply to the skill and to this repo.

1. **Verify before assertion** — never claim a feature you haven't executed.
2. **Output over process narration** — report what changed and what's verified, not the steps taken.
3. **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
4. **Coordinate first, spawn second** — prefer in-session tools before long-lived processes.
5. **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
6. **Version everything** — bump `version` in the skill frontmatter when behaviour changes; keep metadata accurate.

## Notes on this repo

- The `SKILL.md` frontmatter says version 1.0.0, license MIT, tags `[Academic, Citation, Writing, NLP]`, related skills `[academic-jargon-buster, programming-literature-review]`.
- The actual `SKILL.md` file in this repo is 2,098 bytes, copied verbatim from the Hermes skill at `~/.hermes-pakozan/skills/research/citation-weaver/SKILL.md`.
- The demo code (`citation_weaver.py`) is a standalone reference implementation. Its style formatting is simplified — check the official style guide before submitting a thesis or journal paper.
- **Never invent references.** A citation key with no bibliography entry is marked `[PERLU RUJUKAN: key]` / `[REFERENCE NEEDED: key]`, never filled in with a made-up paper. The sample bibliography (`demos/references.json`) contains four real, verifiable references only.
