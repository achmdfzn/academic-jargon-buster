# Academic Jargon Buster

**Your thesis speaks jargon. This repo translates it — and cites it properly.**

Two Hermes academic skills in one repo, built for students writing skripsi, tugas akhir, and journal papers in Indonesian and English. No dependencies. No invented references. One command opens a menu; the menu does the rest.

## How this repo was born

A real Indonesian abstract — a web-based management information system for a student abstract, evaluated with the System Usability Scale — matched **zero** terms in the first dictionary. So the dictionary learned from it. That same abstract now matches six terms, and its three real references (Brooke 1996, Likert 1932, Ferraiolo & Kuhn 1992) live in the sample bibliography. This repo grows from real student text, not from a word list.

## What is inside

| Tool | What it does | Version |
| --- | --- | --- |
| **Academic Jargon Buster** | Finds jargon in your text and explains each term in plain language, with its source | v1.0.2 |
| **Citation Weaver** | Turns `[cite:key]` markers into in-text citations plus a bibliography: APA, MLA, Chicago, IEEE, Harvard, Vancouver | v1.0.0 |
| **Academic CLI** | One interactive command for both tools, menu-driven, bilingual | v1.0.0 |

- **Two languages:** Indonesian and English — the interface, the examples, and the dictionary aliases.
- **21 majors, 6 citation styles:** each major has a recommended style (Medicine goes to Vancouver, Psychology to APA, Informatics to IEEE, Law to Chicago, Economics to Harvard). `--style` always wins over the recommendation.
- **22 dictionary terms and counting:** physics, machine learning, economics, biology, usability, software engineering, research methods. Every term carries a plain explanation, a field, and a real source.
- **7 real sample references:** Vaswani et al. 2017, Devlin et al. 2019, Brown et al. 2020, Goodfellow et al. 2016, Brooke 1996, Likert 1932, Ferraiolo & Kuhn 1992. All verifiable. None invented.

## The one rule this repo never breaks

**Never invent a reference.** A `[cite:key]` with no bibliography entry is printed as `[PERLU RUJUKAN: key]` — a gap to fill, not a paper to fake. A term with no source does not enter the dictionary. That rule is the whole point: a tool for student work must not fabricate the evidence a student is graded on.

## Quick start

```bash
git clone https://github.com/achmdfzn/academic-jargon-buster.git
cd academic-jargon-buster
python3 academic_cli.py
```

```
==================== Academic Tools — Jargon Buster + Citation Weaver ====================
Pilih alat:
1. Jargon Buster — terjemahkan istilah akademik
2. Citation Weaver — sisipkan sitasi ke naskah
3. Ganti bahasa (id/en)
0. Keluar
```

Inside each tool there are more choices: type text or read a file, pick a field, pick a citation style or a major (the major fills in its recommended style automatically), and pick the output language. For scripting, skip the menu with a subcommand — `python3 academic_cli.py jargon ...` and `python3 academic_cli.py cite ...` pass straight through to the standalone tools.

## See it work

Real output, from the repo's own demos.

### 1. Jargon, translated

Input:

```
The renormalization group and gradient descent are core ideas.
```

Output:

```
The renormalization group (a collection of techniques for studying
how a system changes when you look at it at different scales) and
gradient descent (a step-by-step method for finding the lowest point
of a curve by repeatedly moving downhill) are core ideas.
```

### 2. Citations, woven

Input (from a real Indonesian abstract, `demos/citation-weaver/contoh_id.txt`):

```
...mengevaluasi tingkat usability sistem menggunakan metode
System Usability Scale (SUS) [cite:brooke1996]. ...pengaturan
hak akses berbasis peran [cite:ferraiolo1992]... skala Likert
1–5 [cite:likert1932].
```

Output (major: Teknik Informatika, so IEEE; language: Indonesian):

```
...mengevaluasi tingkat usability sistem menggunakan metode
System Usability Scale (SUS) [1]. ...pengaturan hak akses
berbasis peran [2]... skala Likert 1–5 [3].

## Daftar Pustaka

[1] J. Brooke, "SUS: A 'quick and dirty' usability scale,"
    Usability Evaluation in Industry (Taylor & Francis), pp. 189-194, 1996.
[2] D. Ferraiolo, R. Kuhn, "Role-based access control,"
    Proceedings of the 15th National Computer Security Conference, 1992.
[3] R. Likert, "A technique for the measurement of attitudes,"
    Archives of Psychology, 22(140), 1932.
```

## Use each tool on its own

```bash
# Jargon Buster: annotate a text file (default: Markdown)
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

## Install the skills in Hermes

No install needed for the demos — Python 3.9+ only.

To use the skills themselves in Hermes, copy the skill folders into your Hermes skills directory:

```bash
cp -r skills/research/academic-jargon-buster ~/.hermes/skills/research/
cp -r skills/research/citation-weaver ~/.hermes/skills/research/
```

## Repository layout

```
.
├── README.md
├── LICENSE                         # MIT
├── CHANGELOG.md                    # version history
├── academic_cli.py                 # interactive menu CLI (both tools)
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
│       ├── references.json         # 7 real sample references
│       ├── contoh_id.txt # real Indonesian abstract, cited
│       ├── contoh_id.txt           # Indonesian example
│       └── example_en.txt          # English example
├── docs/
│   ├── verification-hierarchy.md   # 4-level verification hierarchy
│   ├── professional-standards.md   # professional operating standards
│   ├── jurusan.md                  # majors & recommended citation styles
│   ├── update-schedule.md          # daily update schedule
│   └── citation-weaver/
│       ├── verification-hierarchy.md
│       └── professional-standards.md
└── tests/
    ├── test_jargon_detection.py    # tests (stdlib unittest, no deps)
    ├── test_citation_weaver.py
    └── test_academic_cli.py        # menu tests (scripted input)
```

## Verification

This skill follows a 4-level verification hierarchy (see `docs/verification-hierarchy.md`):

1. `llms.txt` index — Hermes docs
2. CLI reference — `hermes --help`
3. Source tree — https://github.com/NousResearch/hermes-agent
4. This skill body — what's documented in `SKILL.md`

Never claim a capability that hasn't been verified at one of those levels. See `docs/professional-standards.md` for the operating standards.

## Limitations

- The demo dictionary is small (22 terms) — it is a sample, not a full glossary. Specialised sub-field jargon may not be covered.
- Mathematical notation is preserved as-is, not translated.
- Low-quality OCR input may produce false term detection.
- Cross-discipline terms need manual verification.
- Citation formatting in the demo is simplified — check the official style guide before submitting a thesis or journal paper.

To extend the dictionary, add entries to `DICTIONARY` in `jargon_buster.py` (term → explanation, field, source).

## Tests

```bash
python3 -m unittest discover -s tests -v
```

39 tests, standard library only, no dependencies.

## Contributing

This repo is updated daily (see `docs/update-schedule.md`): tests run, the dictionary grows only from real sources, and the version bumps only when something changes. Two rules for contributions:

1. A new dictionary term needs a real source.
2. A new reference needs a verifiable publication.

Anything else — a new major, a new style, a better explanation — is welcome.

## License

MIT — see `LICENSE`.
