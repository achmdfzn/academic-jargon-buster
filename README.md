# hermes-academic-jargon-buster

Translate academic jargon to plain English — a Hermes skill, plus a small runnable reference implementation.

- **Skill:** `skills/research/academic-jargon-buster/SKILL.md` (v1.0.0, MIT)
- **Demo:** `jargon_buster.py` — pure Python, no dependencies, works standalone

## What it does

Accept a paper excerpt as plain text, identify known jargon via a discipline-specific dictionary, and give a side-by-side plain-English explanation with provenance for each term.

Supported in the skill spec: PDF, TeX, and plain text input; annotated Markdown, term-list CSV, and Notion/Obsidian blocks as output. The demo in this repo implements the plain-text → annotated Markdown / CSV path, which is the part that runs without extra tooling.

## Install

No install needed for the demo — Python 3.9+ only.

To use the skill itself in Hermes, copy the skill folder into your Hermes skills directory, e.g.:

```bash
cp -r skills/research/academic-jargon-buster ~/.hermes/skills/research/
```

## Usage

```bash
# Annotate a text file (default: Markdown)
python3 jargon_buster.py demos/test_paper.txt

# Same, as CSV term list
python3 jargon_buster.py demos/test_paper.txt --format csv

# One-liner, physics only
python3 jargon_buster.py --text "The renormalization group is a mathematical framework." --field physics
```

Example output:

```
The renormalization group (a collection of techniques for studying
how a system changes when you look at it at different scales) is a
mathematical framework.
```

## Repository layout

```
.
├── README.md
├── LICENSE                         # MIT
├── jargon_buster.py                # standalone reference implementation
├── skills/
│   └── research/
│       └── academic-jargon-buster/
│           └── SKILL.md            # Hermes skill spec (source of truth)
├── demos/
│   ├── example_usage.py            # example CLI usage
│   └── test_paper.txt              # sample text for testing
├── docs/
│   ├── verification-hierarchy.md   # 4-level verification hierarchy
│   └── professional-standards.md   # professional operating standards
└── tests/
    └── test_jargon_detection.py    # tests (stdlib unittest, no deps)
```

## Verification

This skill follows a 4-level verification hierarchy (see `docs/verification-hierarchy.md`):

1. `llms.txt` index — Hermes docs
2. CLI reference — `hermes --help`
3. Source tree — https://github.com/NousResearch/hermes-agent
4. This skill body — what's documented in `SKILL.md`

Never claim a capability that hasn't been verified at one of those levels. See `docs/professional-standards.md` for the operating standards.

## Limitations

- The demo dictionary is small (8 terms) — it is a sample, not a full glossary. Specialised sub-field jargon may not be covered.
- Mathematical notation is preserved as-is, not translated.
- Low-quality OCR input may produce false term detection.
- Cross-discipline terms need manual verification.

To extend the dictionary, add entries to `DICTIONARY` in `jargon_buster.py` (term → explanation, field, source).

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT — see `LICENSE`.
