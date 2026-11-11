# Verification Hierarchy

The skill in this repo follows a 4-level verification hierarchy. Never claim a capability you haven't verified at one of these levels. When in doubt, fetch the source and check; if it's not there, mark it UNKNOWN.

## The 4 levels

### 1. `llms.txt` index

https://hermes-agent.nousresearch.com/docs/llms.txt

The entire Hermes docs set in one file. Query this first.

### 2. CLI reference

```bash
hermes --help
hermes academic-jargon-buster --help
```

Command-level truth — what the tool actually accepts and does.

### 3. Source tree

https://github.com/NousResearch/hermes-agent

Upstream changes, issues, and PRs. Check here when the docs and CLI disagree, or when a feature is new.

### 4. This skill body

`skills/research/academic-jargon-buster/SKILL.md`

What's documented in the skill itself. Treat it as per-session context, not product gospel — it describes intended behaviour, and it must agree with levels 1–3.

## Workflow checklist

- [ ] Input file parsed successfully, text extraction verified
- [ ] Jargon terms identified match the discipline dictionary
- [ ] Translations preserve scientific accuracy (cited sources)
- [ ] Output format matches the user selection
- [ ] No hallucinated terms outside dictionary scope
