# Academic Jargon Buster

**One Python file. Every feature. Zero invented references.**

Student writing, minus the guesswork: this repo translates academic jargon into plain language and weaves citations into narrative text. Indonesian and English. One file, no install, no dependencies — copy `academic_tools.py` anywhere and run it.

## The file

`academic_tools.py` (v1.1.1) holds everything — the jargon dictionary and translator, the citation engine, and an interactive menu CLI. The other `.py` files are thin wrappers, so old commands keep working.

## Quick start

```bash
git clone https://github.com/achmdfzn/academic-jargon-buster.git
cd academic-jargon-buster
python3 academic_tools.py
```

```
==================== Academic Tools — Jargon Buster + Citation Weaver ====================
Pilih alat:
1. Jargon Buster — terjemahkan istilah akademik
2. Citation Weaver — sisipkan sitasi ke naskah
3. Ganti bahasa (id/en)
0. Keluar
```

Pick a number, follow the prompts: type text or read a file, pick a field, a citation style or a major, and a language. For scripts, skip the menu: `python3 academic_tools.py jargon ...` or `... cite ...`.

## What it does

| Tool | In short |
| --- | --- |
| **Jargon Buster** | Finds jargon in your text and explains each term in plain language, with its source. 22 terms — physics, machine learning, usability, software engineering, research methods — including Indonesian aliases. |
| **Citation Weaver** | Turns `[cite:key]` markers into in-text citations plus a bibliography. 6 styles (APA, MLA, Chicago, IEEE, Harvard, Vancouver), 21 majors with a recommended style each. |
| **Menu CLI** | One command, both tools, bilingual prompts. |

**The rule:** never invent a reference. A `[cite:key]` with no bibliography entry prints as `[PERLU RUJUKAN: key]` — a gap to fill, not a paper to fake.

## See it work

Jargon, translated:

```
In:  The renormalization group and gradient descent are core ideas.
Out: The renormalization group (a collection of techniques for studying
     how a system changes when you look at it at different scales) and
     gradient descent (a step-by-step method for finding the lowest point
     of a curve by repeatedly moving downhill) are core ideas.
```

Citations, woven (Indonesian, IEEE):

```
In:  ...menggunakan metode System Usability Scale (SUS) [cite:brooke1996].
Out: ...menggunakan metode System Usability Scale (SUS) [1].

     ## Daftar Pustaka
     [1] J. Brooke, "SUS: A 'quick and dirty' usability scale,"
         Usability Evaluation in Industry (Taylor & Francis), pp. 189-194, 1996.
```

## Use each tool on its own

```bash
python3 academic_tools.py jargon demos/test_paper.txt
python3 academic_tools.py jargon demos/test_paper.txt --format csv
python3 academic_tools.py jargon --list-terms --field general
python3 academic_tools.py jargon --update-dictionary --from new_terms.json
python3 academic_tools.py cite demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --lang id
python3 academic_tools.py cite demos/citation-weaver/example_en.txt --refs demos/citation-weaver/references.json --lang en --style ieee
python3 academic_tools.py cite --text "... [cite:vaswani2017]." --refs demos/citation-weaver/references.json --jurusan Kedokteran
```

## Layout

```
academic_tools.py            # everything (v1.1.1)
jargon_buster.py / citation_weaver.py / academic_cli.py   # thin wrappers
skills/research/             # the same two tools as agent skills
demos/                       # examples + 7 real sample references
docs/                        # majors & styles, verification, update schedule
tests/                       # 43 tests, stdlib unittest only
```

## Skills

The `skills/research/` folders hold the same two tools as agent skills. They follow the standard agent-skill format, so they also work in agents that load skills from a folder.

## Limits, honestly

- 22 dictionary terms is a sample, not a glossary. New terms need a real source.
- Citation formatting here is simplified — check the official style guide before submitting.
- Math notation is kept as-is; low-quality OCR can misfire.

## Tests

```bash
python3 -m unittest discover -s tests -v   # 43 tests, no dependencies
```

## License

MIT — see `LICENSE`.
