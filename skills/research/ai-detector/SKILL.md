---
name: ai-detector
description: "Heuristic AI-text detector (stdlib only, no language model): burstiness, template phrases, lexical diversity, repeated sentence starters."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Academic, AI Detection, Writing, Style]
    related_skills: [academic-quality-check, academic-jargon-buster]
---

## Verification Hierarchy

**Always verify before claiming ai-detector capability.**

1. **llms.txt index** — <https://hermes-agent.nousresearch.com/docs/llms.txt> — the entire docs set in one file. Query first.
2. **CLI reference** — `hermes --help`, `hermes ai-detector --help` — command-level truth.
3. **Source tree** — <https://github.com/NousResearch/hermes-agent> — upstream changes, issues, PRs.
4. **This skill body** — what's documented here; treat as per-session context, not product gospel.

Never claim an ai-detector feature you haven't verified. When in doubt, fetch `llms.txt` and search. If it's not there, check the source. If it's not in source either, mark as UNKNOWN.

## Professional Operating Standards

- **Verify before assertion** — never claim an ai-detector feature you haven't executed.
- **Output over process narration** — report what changed and what's verified, not the steps taken.
- **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
- **Coordinate first, spawn second** — prefer in-session tools (`delegate_task`, `cronjob`) before long-lived processes.
- **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
- **Version everything** — bump `version` in frontmatter when behavior changes; keep metadata accurate.

# AI Detector

A heuristic check whether a text reads like AI writing — the same style of signals GPTZero-style detectors lean on (sentence-length variation, template phrases, lexical diversity, repeated sentence starters), implemented in pure standard-library Python with no language model and no API. Everything lives in `academic_tools.py` (one file, standard library only) alongside the Jargon Buster, Citation Weaver, Thesis Prompts, and Quality Check tools (see `academic-quality-check`).

## How it works (`detect_ai`)

```bash
python3 academic_tools.py detect naskah.txt
python3 academic_tools.py detect --text "..." --json
python3 academic_tools.py detect naskah.txt --lang en
```

Four signals, each a 0–100 sub-score (100 = most AI-like). The final `ai_score` (0–100) is the weighted mean of the applicable signals only (weights renormalized):

| Signal | Weight | What it measures | 100 when | Not applicable when |
| --- | --- | --- | --- | --- |
| Burstiness | 30 | Coefficient of variation (stdev / mean) of sentence lengths in words — uniform sentences read like AI | CV 0 (every sentence the same length) | Under 3 sentences |
| Template phrases | 30 | Density of curated AI-typical transition phrases per 100 words ("selain itu", "perlu dicatat bahwa", "secara keseluruhan", "dengan demikian", "sebagai kesimpulan", … — 20 Indonesian phrases, 10 English ones, curated from scratch for this repo) | 5 phrases per 100 words | Never (0 phrases scores 0) |
| Lexical diversity | 20 | Type-token ratio (unique words / total words) — a repetitive vocabulary reads like AI | TTR 0.42 | Under 30 words |
| Starter repetition | 20 | Share of sentences sharing the most common opening two words | A 0.50 share | Under 4 sentences |

Verdict bands (fixed thresholds):

| `ai_score` | Verdict |
| --- | --- |
| ≥ 70 | "Kemungkinan besar AI" / "Likely AI" |
| 40–69 | "Campuran / tidak pasti" / "Mixed / uncertain" |
| < 40 | "Kemungkinan besar manusia" / "Likely human" |

- **Under 30 words the verdict is "Teks terlalu pendek" / "Text too short"** and `ai_score` is `None` — there is not enough text to judge. An empty or whitespace-only text is an error (`teks kosong`, exit 1), like `analyze`.
- **The result always carries a `note`** stating the honesty limit (below). The `sentences` list scores every sentence 0–100 (most AI-like first): 60% whether it contains a template phrase, 30% closeness of its length to the mean sentence length, 10% whether it opens with the text's most common starter.
- **`--json`** prints the raw result (`ai_score`, `verdict`, `signals`, `sentences`, `note`).
- **Detection is informative: exit 0 always** (an AI-like text still exits 0), except bad input (missing file, empty text → exit 1). In the interactive menu, this is option 7, Deteksi AI.

## Calibration

Six calibration texts, written from scratch in `tests/test_detector.py` — three human-like (varied sentence lengths, an idiosyncratic voice, no template phrases) and three AI-like (uniform sentences, dense template phrases, repetitive vocabulary). The contract the tests pin: every human-like text scores under 40, every AI-like text scores over 60. A typical human methods paragraph (two template phrases, fairly uniform sentences) scores ~27; a light-AI text (five uniform sentences, two template phrases) lands in the uncertain band (~50) — which is exactly what that band is for.

## Limits — read this before using the score (non-negotiable)

- **This is a heuristic, not a model.** There is no language model behind it — no perplexity from a real LM, no trained classifier. The score is an **indication, not proof**: human text can be flagged and AI text can pass. **Never use the result to accuse anyone** of using AI — not a student, not a colleague, not an author.
- **The bands are honest about uncertainty.** 40–69 means "cannot tell", not "probably AI". A short text, a heavily edited text, or a text in a rigid genre (methods sections, legal boilerplate) can score oddly in either direction.
- **Template phrases are density, not presence.** One "selain itu" in a human paragraph is normal; five per 100 words is the AI pattern. Do not quote a single phrase as evidence.
- **Indonesian first.** The phrase list and the calibration are Indonesian; the English list is smaller (10 phrases) and the English calibration is thinner — treat English scores as rougher.
- **Use it as a mirror, not a judge.** Its best use inside this repo is checking your own draft after Humanize: if a humanized draft still scores high, its sentence structure is still too uniform — vary the lengths and starters by hand.

## Web UI (`serve`)

```bash
python3 academic_tools.py serve            # http://127.0.0.1:8000/
```

Localhost only, standard library `http.server`, no external resources. The sidebar lists six tools; the Deteksi AI tab takes a text and a language, and shows the score as the same SVG gauge as the Analisis Kualitas tab (band colors reversed: a high AI score is red), the four signal components beside it, the sentences scoring 70 or more with their scores, and the honesty note — always visible. New endpoint `POST /api/detect` (`{text, lang}`, 1 MB body cap, honest 400 for an empty text or a bad `lang`), returning the full `detect_ai` result.

## Rules (non-negotiable)

- **Never accuse from a score.** The detector is an indication, not evidence. No verdict, no report, no message to anyone may present the score as proof that a text is AI-written.
- **Never invent a reference, a term, a data point, or a source.** (Shared rule of the whole repo — see `academic-quality-check`.)
- **The student writes their own thesis.** This skill checks; it does not write whole chapters or fabricate references.

## Usage

```bash
python3 academic_tools.py detect demos/jargon-buster/test_paper.txt
python3 academic_tools.py detect --text "..." --lang en --json
python3 academic_tools.py serve --port 8000
```

Or open the interactive menu (`python3 academic_tools.py`) and pick option 7 (Deteksi AI).
