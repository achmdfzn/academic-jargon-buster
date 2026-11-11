# Verification Hierarchy

Every skill in this repo follows the same 4-level hierarchy. Never claim a
capability you haven't verified at one of these levels. When in doubt, fetch the
source and check; if it's not there, mark it UNKNOWN.

## The 4 levels

### 1. `llms.txt` index

https://hermes-agent.nousresearch.com/docs/llms.txt

The entire Hermes docs set in one file. Query this first.

### 2. CLI reference

```bash
hermes --help
hermes academic-jargon-buster --help
hermes citation-weaver --help
hermes skripsi-prompts --help
```

Command-level truth — what the tool actually accepts and does.

### 3. Source tree

https://github.com/NousResearch/hermes-agent

Upstream changes, issues, and PRs. Check here when the docs and CLI disagree,
or when a feature is new.

### 4. Skill bodies

- `skills/research/academic-jargon-buster/SKILL.md`
- `skills/research/citation-weaver/SKILL.md`
- `skills/research/skripsi-prompts/SKILL.md`

What's documented in the skill itself. Treat it as per-session context, not
product gospel — it describes intended behaviour, and it must agree with
levels 1–3.

## Workflow checklist

- [ ] Input parsed successfully; text extraction verified
- [ ] Jargon matches the field-filtered dictionary, or the citation keys resolve
- [ ] Unknown `[cite:key]` values are marked `[PERLU RUJUKAN: key]` /
      `[REFERENCE NEEDED: key]`, never invented
- [ ] Output format and language match the user's selection
- [ ] Official style guide checked before submission
