---
name: academic-jargon-buster
description: "Translate academic jargon to everyday language."
version: 1.0.4
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Academic, Jargon, NLP, Translation]
    related_skills: [programming-literature-review, grounded-citations]
---

## Verification Hierarchy

**Always verify before claiming academic-jargon-buster capability.**

1. **llms.txt index** — <https://hermes-agent.nousresearch.com/docs/llms.txt> — the entire docs set in one file. Query first.
2. **CLI reference** — `hermes --help`, `hermes academic-jargon-buster --help` — command-level truth.
3. **Source tree** — <https://github.com/NousResearch/hermes-agent> — upstream changes, issues, PRs.
4. **This skill body** — what's documented here; treat as per-session context, not product gospel.

Never claim an academic-jargon-buster feature you haven't verified. When in doubt, fetch `llms.txt` and search. If it's not there, check the source. If it's not in source either, mark as UNKNOWN.

## Professional Operating Standards

- **Verify before assertion** — never claim an academic-jargon-buster feature you haven't executed.
- **Output over process narration** — report what changed and what's verified, not the steps taken.
- **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
- **Coordinate first, spawn second** — prefer in-session tools (`delegate_task`, `cronjob`) before long-lived processes.
- **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
- **Version everything** — bump `version` in frontmatter when behavior changes; keep metadata accurate.

# Academic Jargon Buster

Translate academic jargon and technical terminology to plain English (or user's preferred language) while preserving scientific accuracy. Accept paper PDFs, TeX files, or raw text, identify jargon via discipline-specific dictionaries, and provide side-by-side translation with provenance citations.

## Input Methods

- **PDF upload** — extract text, detect technical terms via field-aware dictionary
- **TeX source** — parse LaTeX, preserve math environment markers, translate surrounding text
- **Plain text** — paste paper excerpt, get inline annotation

## Output Formats

- **Annotated Markdown** — original text with jargon highlighted and translation in parentheses
- **Term List CSV** — jargon term, definition, source discipline, confidence score
- **Side-by-side View** — original paragraph with translation beneath, suitable for lecture notes
- **Notion/Obsidian Block** — embeddable block with syntax for knowledge-base linking

## Discipline Dictionaries (sample coverage)

| Field | Example Terms | Translation Approach |
|-------|-------------|---------------------|
| Physics | *renormalization group* | Keep core concept, explain mechanism |
| Machine Learning | *gradient descent* | Simplify optimization description |
| Economics | *causal inference* | Map to everyday decision logic |
| Computer Science | *polymorphism* | Analogize to real-world patterns |
| Biology | *mitosis* | Step-by-step narrative |
| Research Methods | *validity*, *triangulation* | Define the method, give the source |

## Verification Workflow

- [ ] Input file parsed successfully, text extraction verified
- [ ] Jargon terms identified match discipline dictionary
- [ ] Translations preserve scientific accuracy (cited sources)
- [ ] Output format matches user selection
- [ ] No hallucinated terms outside dictionary scope

## Known Limitations

- Specialized sub-field jargon may not be in default dictionary
- Mathematical notation not translated (preserved as-is)
- Low-quality OCR input may produce false term detection
- Cross-discipline terms require manual verification

## Update Dictionary

Refresh jargon database when new papers or field developments emerge:

```bash
jargon-buster --update-dictionary --field <discipline>
```

## Citations

All translated terms carry provenance from source dictionaries (arXiv glossaries, Wikipedia, field-specific textbooks). Cite source when sharing annotated output.