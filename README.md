# Academic Jargon Buster

Translate academic jargon to plain English — plus a small runnable reference implementation. This repo now holds **two** Hermes academic skills (both bilingual Indonesian/English where noted).

- **Skill 1 — Academic Jargon Buster:** `skills/research/academic-jargon-buster/SKILL.md` (v1.0.1, MIT)
  - Demo: `jargon_buster.py` — pure Python, no dependencies, works standalone
- **Skill 2 — Citation Weaver:** `skills/research/citation-weaver/SKILL.md` (v1.0.0, MIT)
  - Demo: `citation_weaver.py` — pure Python, no dependencies, works standalone

## What it does

### Academic Jargon Buster

Accept a paper excerpt as plain text, identify known jargon via a discipline-specific dictionary, and give a side-by-side plain-English explanation with provenance for each term.

Supported in the skill spec: PDF, TeX, and plain text input; annotated Markdown, term-list CSV, and Notion/Obsidian blocks as output. The demo in this repo implements the plain-text → annotated Markdown / CSV path, which is the part that runs without extra tooling.

### Citation Weaver

Weave citations into narrative text: give it a text with `[cite:key]` markers (or TeX `\cite{key}`) plus a bibliography file, and it returns the text with in-text citations plus a bibliography — in Indonesian or English (`--lang id` / `--lang en`).

- **Citation styles:** APA, MLA, Chicago, IEEE, Harvard, Vancouver (6 styles)
- **Majors:** 21 jurusan, each with a recommended style (see `docs/jurusan.md` or `python3 citation_weaver.py --list-jurusan`). `--style` always overrides the recommendation.
- **Never invent references:** a `[cite:key]` with no bibliography entry is marked `[PERLU RUJUKAN: key]` / `[REFERENCE NEEDED: key]`, never filled in with a made-up paper.

## Install

No install needed for the demo — Python 3.9+ only.

To use the skill itself in Hermes, copy the skill folder into your Hermes skills directory, e.g.:

```bash
cp -r skills/research/academic-jargon-buster ~/.hermes/skills/research/
cp -r skills/research/citation-weaver ~/.hermes/skills/research/
```

## Usage

```bash
# Annotate a text file (default: Markdown)
python3 jargon_buster.py demos/test_paper.txt

# Same, as CSV term list
python3 jargon_buster.py demos/test_paper.txt --format csv

# One-liner, physics only
python3 jargon_buster.py --text "The renormalization group is a mathematical framework." --field physics

# List the dictionary (optionally one field)
python3 jargon_buster.py --list-terms --field general

# Add terms from a JSON file (see jargon_buster.py docstring for the format)
python3 jargon_buster.py --update-dictionary --from new_terms.json

# Citation Weaver: Indonesian, APA style (default)
python3 citation_weaver.py demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --lang id

# Citation Weaver: English, IEEE style, or by major (Medicine -> Vancouver)
python3 citation_weaver.py demos/citation-weaver/example_en.txt --refs demos/citation-weaver/references.json --lang en --style ieee
python3 citation_weaver.py demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --jurusan Kedokteran
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
├── CHANGELOG.md                    # version history
├── jargon_buster.py                # Academic Jargon Buster demo
├── citation_weaver.py              # Citation Weaver demo
├── dictionary.json                 # user-added terms (created by --update-dictionary)
├── skills/
│   └── research/
│       ├── academic-jargon-buster/
│       │   └── SKILL.md            # Hermes skill spec (source of truth)
│       └── citation-weaver/
│           └── SKILL.md            # Hermes skill spec (source of truth)
├── demos/
│   ├── example_usage.py            # jargon example CLI usage
│   ├── test_paper.txt              # jargon sample text
│   └── citation-weaver/
│       ├── example_usage.py
│       ├── references.json         # 4 real sample references
│       ├── contoh_id.txt           # Indonesian example
│       └── example_en.txt          # English example
├── docs/
│   ├── verification-hierarchy.md   # 4-level verification hierarchy
│   ├── professional-standards.md   # professional operating standards
│   ├── jurusan.md                  # majors & recommended citation styles
│   └── citation-weaver/
│       ├── verification-hierarchy.md
│       └── professional-standards.md
└── tests/
    ├── test_jargon_detection.py    # tests (stdlib unittest, no deps)
    └── test_citation_weaver.py
```

## Verification

This skill follows a 4-level verification hierarchy (see `docs/verification-hierarchy.md`):

1. `llms.txt` index — Hermes docs
2. CLI reference — `hermes --help`
3. Source tree — https://github.com/NousResearch/hermes-agent
4. This skill body — what's documented in `SKILL.md`

Never claim a capability that hasn't been verified at one of those levels. See `docs/professional-standards.md` for the operating standards.

## Limitations

- The demo dictionary is small (13 terms) — it is a sample, not a full glossary. Specialised sub-field jargon may not be covered.
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
