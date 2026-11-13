---
name: academic-jargon-buster
description: "Translate academic jargon to everyday language."
version: 1.0.8
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

Translate academic jargon and technical terminology to plain language (Indonesian or English) while preserving scientific accuracy. The tool works on plain text: it finds terms from a 77-term discipline dictionary (with Indonesian aliases), explains each one in place, and names its source. It does not read PDFs or TeX files — paste the text.

## Input Methods

- **Plain text** — paste a paper excerpt or a thesis paragraph, get inline annotation
- **File** — point the CLI at a `.txt` file
- **Dictionary file** — a `dictionary.json` next to the tool adds the user's own terms (merged over the built-in dictionary)

## Output Formats

- **Annotated Markdown** — original text with each jargon term followed by its plain-language translation
- **Term List CSV** — jargon term, translation, field, source
- **Term list** — `jargon --list-terms [--field <discipline>]` prints every term in the dictionary

## Quality check (analyze)

The jargon half of the one-pass quality check (see `academic-quality-check`): `analyze` runs the same dictionary over a manuscript and counts it as one of four 25-point components — jargon found and explained, citations audited, DOIs verified, style checked — one score 0–100.

```bash
python3 academic_tools.py analyze naskah.txt --refs my-refs.json
python3 academic_tools.py analyze --text "The renormalization group ..." --json
```

Without `--refs` the citation and DOI components are skipped (neutral). Exit code is 1 when a citation is missing or a DOI is not found. In the interactive menu, this is option 4, Analisis Kualitas.

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

- 77 dictionary terms is a sample, not a glossary. New terms need a real source.
- Specialized sub-field jargon may not be in default dictionary
- Mathematical notation not translated (preserved as-is)
- Low-quality OCR input may produce false term detection
- Cross-discipline terms require manual verification
- PDF and TeX files are not read — paste plain text instead

## Update Dictionary

Refresh jargon database when new papers or field developments emerge:

```bash
jargon-buster --update-dictionary --field <discipline>
```

## Citations

All translated terms carry provenance from one specific book or paper (author + year + title, with ISBN or DOI where one exists) — no generic sources. Cite source when sharing annotated output.