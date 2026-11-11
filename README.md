# Academic Jargon Buster

**One Python file. Every feature. Zero invented references.**

Student writing, minus the guesswork: this repo translates academic jargon into plain language, weaves citations into narrative text, and hands you ready-made prompts for every thesis chapter. Indonesian and English. One file, no install, no dependencies — copy `academic_tools.py` anywhere and run it.

## The file

`academic_tools.py` (v1.11.0) holds everything — the jargon dictionary and translator, the citation engine with online reference lookup, 18 thesis prompts, a one-pass quality check (jargon + citations + DOI verification + a style check, one score 0–100), and an interactive menu CLI. The other `.py` files are thin wrappers, so old commands keep working.

## Quick start

```bash
git clone https://github.com/achmdfzn/academic-jargon-buster.git
cd academic-jargon-buster
python3 academic_tools.py
```

```
  +==============================================================+
  | Academic Tools                                       v1.11.0 |
  +--------------------------------------------------------------+
  | Jargon Buster  |  Citation Weaver  |  Prompt Skripsi         |
  | id  |  ketik angka, Enter untuk memilih                      |
  +==============================================================+
Pilih alat:
1. Jargon Buster — terjemahkan istilah akademik
2. Citation Weaver — sisipkan sitasi ke naskah
3. Prompt Skripsi — template prompt untuk tiap bab
4. Analisis Kualitas — cek jargon, sitasi, dan DOI sekaligus
5. Ganti bahasa (id/en)
0. Keluar
```

Pick a number, follow the prompts: type text or read a file, pick a field, a citation style or a major, fill a thesis prompt, and a language. For scripts, skip the menu: `python3 academic_tools.py jargon ...`, `... cite ...`, `... prompts ...`, or `... analyze ...`.

## What it does

| Tool | In short |
| --- | --- |
| **Jargon Buster** | Finds jargon in your text and explains each term in plain language, with its source. 32 terms — physics, machine learning, usability, software engineering, research methods — including Indonesian aliases. |
| **Citation Weaver** | Turns `[cite:key]` markers into in-text citations plus a bibliography. 6 styles (APA, MLA, Chicago, IEEE, Harvard, Vancouver), 21 majors with a recommended style each. Look up real references by DOI or title from Crossref/OpenAlex instead of typing bibliography JSON by hand. Export the bibliography to BibTeX (`.bib`) for LaTeX/Overleaf. Audit a manuscript's citations — find markers with no bibliography entry, entries never cited, and (optionally) dead DOI/arXiv links. Verify reference DOIs across Crossref and OpenAlex: a DOI found in either source is real; "not found" requires both to answer 404. |
| **Prompt Skripsi** | 18 ready-made prompt templates for thesis writing — roadmap, abstract, preface, problem statement, Bab 1–5, defense prep, publication. Every template has an Indonesian and an English version (`--lang en`). Pick one, fill in your title, theory, and method, paste the result into ChatGPT, Grok, Claude, Gemini, or Perplexity. |
| **Quality Check** | One pass over a manuscript: jargon found and explained, citations audited (missing / never used), DOIs verified, and stiff Indonesian prose flagged (light verbs, stacked connectors, passive pile-ups, calqued relatives, flat sentence rhythm) — one quality score 0–100 with recommendations. A style report, not a rewrite and not a detector dodge. Exits 1 when a citation is missing or a DOI is not found. |
| **Menu CLI** | One command, all four tools, bilingual prompts. |

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
python3 academic_tools.py jargon demos/jargon-buster/test_paper.txt
python3 academic_tools.py jargon demos/jargon-buster/test_paper.txt --format csv
python3 academic_tools.py jargon --list-terms --field general
python3 academic_tools.py jargon --update-dictionary --from new_terms.json
python3 academic_tools.py cite demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --lang id
python3 academic_tools.py cite demos/citation-weaver/example_en.txt --refs demos/citation-weaver/references.json --lang en --style ieee
python3 academic_tools.py cite --text "... [cite:vaswani2017]." --refs demos/citation-weaver/references.json --jurusan Kedokteran
python3 academic_tools.py prompts --list
python3 academic_tools.py prompts latar-belakang
python3 academic_tools.py prompts roadmap --set judul="..." --set teori="..." --set metode="..." --set bulan=6 --set tanggal="11 November 2026"
python3 academic_tools.py cite --lookup 10.1038/nature14539
python3 academic_tools.py cite --lookup "Deep learning" --add-to my-refs.json
python3 academic_tools.py cite --refs demos/citation-weaver/references.json --verify
python3 academic_tools.py analyze demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json
python3 academic_tools.py analyze --text "... [cite:devlin2019]." --refs demos/citation-weaver/references.json --json
```

Title search needs a free `OPENALEX_API_KEY` — OpenAlex has required a key since February 2026 (about $0.001 per search under a ~$1/day free allowance). DOI lookups try Crossref first, so they keep working without a key. `--verify` checks every DOI against Crossref and OpenAlex; a DOI found in either source is real, "not found" needs both to answer 404, and without the key the OpenAlex column reads `no key` and such a DOI stays "unverified" rather than being called fake. It exits 1 only when a DOI is missing from both sources; references without a DOI are reported as `no DOI` (use `--audit --check-links` for arXiv IDs and URLs).

## Layout

```
academic_tools.py            # everything (v1.11.0)
jargon_buster.py / citation_weaver.py / skripsi_prompts.py / academic_cli.py   # thin wrappers
pyproject.toml               # optional: pipx install . / pip install .
.github/workflows/tests.yml  # CI: 3 OS x Python 3.9, 3.12, 3.13
skills/research/             # the same three tools as agent skills
demos/jargon-buster/         # jargon example + sample paper
demos/citation-weaver/       # citation examples + 7 real references
docs/                        # per-tool notes, shared standards, update schedule
tests/                       # 148 tests, stdlib unittest only
```

## Skills

The `skills/research/` folders hold the same three tools as agent skills. They follow the standard agent-skill format, so they also work in agents that load skills from a folder.

## Limits, honestly

- 32 dictionary terms is a sample, not a glossary. New terms need a real source.
- Citation formatting here is simplified — check the official style guide before submitting.
- Math notation is kept as-is; low-quality OCR can misfire.
- Style signals are calibrated for Indonesian academic prose — on English text, only sentence rhythm is actually judged.

## Tests

```bash
python3 -m unittest discover -s tests -v   # 148 tests, no dependencies
```

## License

MIT — see `LICENSE`.
