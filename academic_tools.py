#!/usr/bin/env python3
"""academic_tools — every feature of this repo in one file.

Pure Python, no dependencies. Copy this single file anywhere and it
works: a jargon translator, a citation weaver, thesis prompts, and an
interactive menu CLI (Claude-CLI style) on top of all three.

    python3 academic_tools.py                  # interactive menu (default)
    python3 academic_tools.py jargon ...       # straight to Jargon Buster
    python3 academic_tools.py cite ...         # straight to Citation Weaver
    python3 academic_tools.py prompts ...      # straight to Thesis Prompts

Jargon Buster: find known jargon in plain text and explain each term
in plain language, with provenance. 32 terms, fields from physics to
usability to software engineering, plus Indonesian aliases.

    python3 academic_tools.py jargon demos/jargon-buster/test_paper.txt
    python3 academic_tools.py jargon --text "The renormalization group ..." --field physics
    python3 academic_tools.py jargon --list-terms [--field general]
    python3 academic_tools.py jargon --update-dictionary --from new_terms.json

Citation Weaver: give it text with [cite:key] (or TeX \\cite{key})
markers plus a bibliography file, and it returns the text with
in-text citations plus a bibliography, in Indonesian or English.
6 styles (APA, MLA, Chicago, IEEE, Harvard, Vancouver), 21 majors
with a recommended style each.

    python3 academic_tools.py cite demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --lang id
    python3 academic_tools.py cite demos/citation-weaver/example_en.txt --refs demos/citation-weaver/references.json --lang en --style ieee
    python3 academic_tools.py cite --text "... [cite:vaswani2017]." --refs demos/citation-weaver/references.json --jurusan Kedokteran

Reference lookup: fetch real metadata by DOI or title from Crossref
and OpenAlex, instead of typing bibliography JSON by hand.

    python3 academic_tools.py cite --lookup 10.1038/nature14539
    python3 academic_tools.py cite --lookup "Deep learning" --add-to my-refs.json
    python3 academic_tools.py cite --lookup 10.1038/nature14539 --key lecun2015 --add-to my-refs.json

One rule, everywhere in this file: NEVER invent a reference. A
[cite:key] with no bibliography entry is marked [PERLU RUJUKAN: key] /
[REFERENCE NEEDED: key], never filled in with a made-up paper.

Thesis Prompts: 18 ready-made prompt templates for writing a thesis,
from research roadmap to defense prep and publication. Pick one, fill
its placeholders with your own title, theory, method, and data, then
paste the result into the recommended AI tool.

    python3 academic_tools.py prompts --list
    python3 academic_tools.py prompts latar-belakang
    python3 academic_tools.py prompts roadmap --set judul="..." --set teori="..." --set metode="..." --set bulan=6 --set tanggal="11 November 2026"

Quality check: one pass over a manuscript — jargon, citation audit,
DOI verification, and a rule-based style check for stiff Indonesian
academic prose (light verbs, stacked connectors, passive pile-ups,
calqued relatives, flat sentence rhythm). One score 0-100, plus
recommendations. A style report, not a rewrite and not a detector
dodge: flagged patterns are suggestions for the author's own edit.

    python3 academic_tools.py analyze demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json
    python3 academic_tools.py analyze --text "... [cite:devlin2019]." --refs demos/citation-weaver/references.json --json

Library: analysis history and a personal bibliography in one local
SQLite file (stdlib sqlite3, no account, no cloud). `analyze --save`
records a run; `library` lists past runs, shows one in detail, and
searches, imports, and exports references.

    python3 academic_tools.py analyze naskah.txt --refs my-refs.json --save
    python3 academic_tools.py library --history
    python3 academic_tools.py library --refs --search "deep learning"

Local web UI: the same four tools in a browser page, served from
this file alone (stdlib http.server, no external resources).

    python3 academic_tools.py serve [--port 8000]   # then open http://127.0.0.1:8000/

The old entry points (jargon_buster.py, citation_weaver.py,
academic_cli.py) still exist as thin wrappers around this file, so
existing commands, demos, and imports keep working.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import difflib
import hashlib
import http.server
import io
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from urllib.parse import parse_qs, quote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

__version__ = "1.19.0"
JARGON_VERSION = "1.0.5"
CITATION_VERSION = "1.4.0"
PROMPTS_VERSION = "1.1.0"
QUALITY_VERSION = "1.2.2"
CLI_VERSION = "1.12.0"

# ======================================================================
# Jargon Buster
# ======================================================================
# term -> (plain-English explanation, field, source)
DICTIONARY = {
    "renormalization group": (
        "a collection of techniques for studying how a system changes "
        "when you look at it at different scales",
        "physics",
        "arXiv glossary / Wikipedia",
    ),
    "gradient descent": (
        "a step-by-step method for finding the lowest point of a curve "
        "by repeatedly moving downhill",
        "machine-learning",
        "Wikipedia / field textbooks",
    ),
    "causal inference": (
        "figuring out whether one thing actually causes another, "
        "rather than just happening at the same time",
        "economics",
        "Wikipedia / field textbooks",
    ),
    "polymorphism": (
        "one interface that can work with different kinds of objects, "
        "like one remote control working with different devices",
        "computer-science",
        "Wikipedia / field textbooks",
    ),
    "mitosis": (
        "the process by which one cell divides into two identical cells, "
        "step by step",
        "biology",
        "Wikipedia / field textbooks",
    ),
    "stochastic gradient descent": (
        "gradient descent that uses a small random sample of the data "
        "at each step instead of the whole dataset, to go faster",
        "machine-learning",
        "Wikipedia / field textbooks",
    ),
    "overfitting": (
        "when a model memorises its training examples so closely that "
        "it performs badly on new, unseen examples",
        "machine-learning",
        "Wikipedia / field textbooks",
    ),
    "heteroscedasticity": (
        "when the spread of errors in data is not constant, but changes "
        "across the range of values",
        "economics",
        "Wikipedia / field textbooks",
    ),
    "peer review": (
        "when other experts in the same field read and check a paper "
        "before it is published, to catch mistakes and judge its quality",
        "general",
        "Wikipedia",
    ),
    "hypothesis": (
        "a testable guess or proposed explanation that a study sets out "
        "to check with evidence",
        "general",
        "Wikipedia / field textbooks",
    ),
    "methodology": (
        "the overall plan of how a study is done — what data is collected, "
        "how it is collected, and why that way",
        "general",
        "Wikipedia / field textbooks",
    ),
    "qualitative research": (
        "research that describes qualities, meanings, and experiences, "
        "usually with words rather than numbers",
        "general",
        "Wikipedia / field textbooks",
    ),
    "quantitative research": (
        "research that measures things with numbers and statistics, "
        "to find patterns and test relationships",
        "general",
        "Wikipedia / field textbooks",
    ),
    # Added 2026-11-11 from a real student abstract (management
    # information system, SUS evaluation). Indonesian aliases included
    # where the source text uses the Indonesian form.
    "system usability scale": (
        "a 10-question survey that measures how easy a system is to use; "
        "answers are scored and combined into one number from 0 to 100",
        "usability",
        "Brooke 1996, 'SUS: A quick and dirty usability scale'",
    ),
    "usability": (
        "how easy and pleasant a system is to use — whether people can "
        "do what they need quickly and without confusion",
        "usability",
        "ISO 9241-11",
    ),
    "object relational mapping": (
        "a technique that lets code treat database tables as ordinary "
        "objects instead of writing raw SQL",
        "software-engineering",
        "Software engineering textbooks",
    ),
    "likert scale": (
        "a survey answer scale with ordered steps, usually 1 to 5, "
        "from 'strongly disagree' to 'strongly agree'",
        "research-methods",
        "Likert 1932, 'A technique for the measurement of attitudes'",
    ),
    "skala likert": (
        "a survey answer scale with ordered steps, usually 1 to 5, "
        "from 'strongly disagree' to 'strongly agree'",
        "research-methods",
        "Likert 1932, 'A technique for the measurement of attitudes'",
    ),
    "authentication": (
        "checking that a user really is who they claim to be, "
        "usually with a username and password",
        "software-engineering",
        "Software engineering textbooks",
    ),
    "autentikasi": (
        "checking that a user really is who they claim to be, "
        "usually with a username and password",
        "software-engineering",
        "Software engineering textbooks",
    ),
    "role-based access control": (
        "deciding what each user may do in a system based on their role, "
        "such as admin or member",
        "software-engineering",
        "Ferraiolo & Kuhn 1992, 'Role-based access control'",
    ),
    "hak akses berbasis peran": (
        "deciding what each user may do in a system based on their role, "
        "such as admin or member",
        "software-engineering",
        "Ferraiolo & Kuhn 1992, 'Role-based access control'",
    ),
    # Added 2026-11-11: 10 research-methods terms students meet in almost
    # every thesis. Sources verified the same day (Crossref/OpenAlex/web):
    # Creswell & Creswell 2018, Denzin 1978, Patton 2015, Braun & Clarke
    # 2006, Boote & Beile 2005. Indonesian aliases included where the
    # source text uses the Indonesian form.
    "validity": (
        "whether a test or study actually measures what it claims to measure, "
        "rather than something else",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed.)",
    ),
    "validitas": (
        "whether a test or study actually measures what it claims to measure, "
        "rather than something else",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed.)",
    ),
    "reliability": (
        "whether a test or study gives the same result when repeated "
        "under the same conditions",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed.)",
    ),
    "reliabilitas": (
        "whether a test or study gives the same result when repeated "
        "under the same conditions",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed.)",
    ),
    "triangulation": (
        "checking one finding with more than one method, data source, "
        "or viewpoint, so the result is more trustworthy",
        "research-methods",
        "Denzin 1978, 'The Research Act' (2nd ed.)",
    ),
    "triangulasi": (
        "checking one finding with more than one method, data source, "
        "or viewpoint, so the result is more trustworthy",
        "research-methods",
        "Denzin 1978, 'The Research Act' (2nd ed.)",
    ),
    "purposive sampling": (
        "choosing participants on purpose because they have the knowledge "
        "or experience the study needs, instead of picking at random",
        "research-methods",
        "Patton 2015, 'Qualitative Research & Evaluation Methods' (4th ed.)",
    ),
    "thematic analysis": (
        "a method for finding and describing patterns, called themes, "
        "across interview or written data",
        "research-methods",
        "Braun & Clarke 2006, 'Using thematic analysis in psychology'",
    ),
    "operational definition": (
        "a clear statement of exactly how a variable is measured "
        "or observed in a study",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed.)",
    ),
    "literature review": (
        "a survey of the research already done on a topic, showing "
        "what is known and where the gaps are",
        "research-methods",
        "Boote & Beile 2005, 'Scholars before researchers'",
    ),
    # Added 2026-11-12: 10 statistics terms students meet in almost
    # every quantitative thesis. Sources verified the same day (web):
    # Field 2018, Ghozali 2018. Indonesian aliases included where the
    # source text uses the Indonesian form. "variance" was left out
    # on purpose: the matcher is substring-based, so it would also
    # match inside "covariance" and explain the wrong concept. The
    # same trade-off is accepted for "validity" (inside "invalidity")
    # and "normality" (inside "abnormality"): word-boundary matching
    # would fix those but would also stop plurals such as
    # "correlations" from matching, so the substring matcher stays.
    "statistical significance": (
        "when a result is unlikely to have happened by chance alone, "
        "so the study treats it as a real effect",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "signifikansi statistik": (
        "when a result is unlikely to have happened by chance alone, "
        "so the study treats it as a real effect",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "p-value": (
        "a number from 0 to 1 that measures how surprising the data "
        "would be if there were no real effect; below 0.05, the result "
        "is usually called significant",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "nilai-p": (
        "a number from 0 to 1 that measures how surprising the data "
        "would be if there were no real effect; below 0.05, the result "
        "is usually called significant",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "correlation": (
        "a measure of how two things move together — when one goes up, "
        "the other tends to go up or down — without proving that one "
        "causes the other",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "korelasi": (
        "a measure of how two things move together — when one goes up, "
        "the other tends to go up or down — without proving that one "
        "causes the other",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "regression": (
        "a method for predicting one value from others, by fitting a "
        "line or curve that best describes how they relate",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "regresi": (
        "a method for predicting one value from others, by fitting a "
        "line or curve that best describes how they relate",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "standard deviation": (
        "a number that says how spread out values are around their "
        "average — a small one means the values cluster close to "
        "the average",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "standar deviasi": (
        "a number that says how spread out values are around their "
        "average — a small one means the values cluster close to "
        "the average",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "null hypothesis": (
        "the starting assumption that there is no effect or no "
        "difference, which a study tries to disprove with evidence",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "hipotesis nol": (
        "the starting assumption that there is no effect or no "
        "difference, which a study tries to disprove with evidence",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "confidence interval": (
        "a range of values that probably contains the true value — "
        "a 95% interval means the method would capture the true value "
        "in 95 out of 100 repeats",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "interval kepercayaan": (
        "a range of values that probably contains the true value — "
        "a 95% interval means the method would capture the true value "
        "in 95 out of 100 repeats",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "normality": (
        "whether data follows the bell-shaped normal distribution, "
        "which many statistical tests assume before they can be trusted",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "normalitas": (
        "whether data follows the bell-shaped normal distribution, "
        "which many statistical tests assume before they can be trusted",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "multicollinearity": (
        "when two or more predictors in a regression are so strongly "
        "related to each other that their separate effects cannot be "
        "told apart",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "multikolinearitas": (
        "when two or more predictors in a regression are so strongly "
        "related to each other that their separate effects cannot be "
        "told apart",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "autocorrelation": (
        "when the errors in a regression are related to each other "
        "over time or order, instead of being independent",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "autokorelasi": (
        "when the errors in a regression are related to each other "
        "over time or order, instead of being independent",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
}


def _user_dictionary_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary.json")


def load_dictionary():
    """Built-in dictionary plus user-added terms from dictionary.json."""
    merged = dict(DICTIONARY)
    path = _user_dictionary_path()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            extra = json.load(f)
        for term, value in extra.items():
            merged[term.lower()] = (
                value["explanation"],
                value.get("field", "general"),
                value.get("source", "user-added"),
            )
    return merged


def list_terms(field: str | None = None):
    """All dictionary terms, optionally filtered by field."""
    items = sorted(load_dictionary().items())
    if field:
        items = [(t, v) for t, v in items if v[1] == field]
    return [{"term": t, "translation": v[0], "field": v[1], "source": v[2]} for t, v in items]


def update_dictionary(from_file: str, field: str | None = None):
    """Add terms from a JSON file into dictionary.json. Returns added terms.

    File format: {"term": {"explanation": "...", "field": "...",
    "source": "..."}}. Entries without an explanation are skipped.
    """
    with open(from_file, encoding="utf-8") as f:
        incoming = json.load(f)
    path = _user_dictionary_path()
    existing = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    added = []
    for term, value in incoming.items():
        term = term.lower()
        if not isinstance(value, dict) or not value.get("explanation"):
            continue
        if field and value.get("field", "general") != field:
            continue
        existing[term] = {
            "explanation": value["explanation"],
            "field": value.get("field", "general"),
            "source": value.get("source", "user-added"),
        }
        added.append(term)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return sorted(added)


def _iter_matches(text: str, field: str | None = None):
    """One dictionary match per occurrence, longest term first.

    Terms are tried longest-first, so 'stochastic gradient descent'
    claims its span before 'gradient descent' can. Case-insensitive;
    spans that overlap an already-claimed span are skipped.
    """
    dictionary = load_dictionary()
    seen_spans = []
    for term in sorted(dictionary, key=len, reverse=True):
        explanation, term_field, source = dictionary[term]
        if field and term_field != field:
            continue
        for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            span = (m.start(), m.end())
            if any(s < span[1] and span[0] < e for s, e in seen_spans):
                continue
            seen_spans.append(span)
            yield {
                "original": m.group(0),
                "term": term,
                "translation": explanation,
                "field": term_field,
                "source": source,
                "confidence": 1.0,  # exact dictionary match
                "start": span[0],
                "end": span[1],
            }


def find_terms(text: str, field: str | None = None):
    """Return list of dicts for each dictionary term found in text.

    Longest terms first, so 'stochastic gradient descent' wins over
    'gradient descent' when both match. Case-insensitive. Results are
    ordered by position in the text.
    """
    matches = sorted(_iter_matches(text, field=field), key=lambda d: d["start"])
    return [
        {k: v for k, v in item.items() if k not in ("start", "end")}
        for item in matches
    ]


def to_annotated_markdown(text: str, field: str | None = None) -> str:
    """Original text with jargon followed by its plain explanation."""
    matches = sorted(_iter_matches(text, field=field), key=lambda d: d["start"])
    if not matches:
        return text + "\n\n_No known jargon terms found in the dictionary._\n"
    # Splice by span, so each occurrence is annotated exactly once and
    # an inserted explanation can never be matched again.
    parts = []
    cursor = 0
    for item in matches:
        parts.append(text[cursor:item["end"]])
        parts.append(f" ({item['translation']})")
        cursor = item["end"]
    parts.append(text[cursor:])
    lines = ["# Annotated output\n", "".join(parts), "\n## Terms found\n"]
    for item in matches:
        lines.append(
            f"- **{item['original']}** ({item['field']}) — "
            f"{item['translation']} — _source: {item['source']}_"
        )
    return "\n".join(lines) + "\n"


def to_csv(text: str, field: str | None = None) -> str:
    """Term list as CSV: term, definition, field, confidence, source."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["term", "definition", "field", "confidence", "source"])
    for item in find_terms(text, field=field):
        w.writerow(
            [item["term"], item["translation"], item["field"],
             item["confidence"], item["source"]]
        )
    return buf.getvalue()


def jargon_main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Translate academic jargon to plain English.")
    p.add_argument("input", nargs="?", help="plain-text file to translate")
    p.add_argument("--text", help="translate this text instead of a file")
    p.add_argument("--field", help="only use terms from this field, e.g. physics")
    p.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    p.add_argument("--list-terms", action="store_true", help="list dictionary terms and exit")
    p.add_argument("--update-dictionary", action="store_true",
                   help="add terms from --from <json file> to dictionary.json")
    p.add_argument("--from", dest="from_file", help="JSON file of terms for --update-dictionary")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.list_terms:
        for item in list_terms(field=args.field):
            print(f"{item['term']} ({item['field']}) — {item['translation']} — {item['source']}")
        return 0

    if args.update_dictionary:
        if not args.from_file:
            for item in list_terms(field=args.field):
                print(f"{item['term']} ({item['field']}) — {item['translation']} — {item['source']}")
            print("\nTo add terms: --update-dictionary --from new_terms.json", file=sys.stderr)
            return 0
        added = update_dictionary(args.from_file, field=args.field)
        if added:
            print(f"Added {len(added)} term(s): {', '.join(added)}")
        else:
            print("No terms added (check the file format and --field filter).")
        return 0

    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
        return 2

    if args.format == "csv":
        sys.stdout.write(to_csv(text, field=args.field))
    else:
        sys.stdout.write(to_annotated_markdown(text, field=args.field))
    return 0


# ======================================================================
# Citation Weaver
# ======================================================================
STYLES = ["apa", "mla", "chicago", "ieee", "harvard", "vancouver"]

# Jurusan (majors) -> recommended citation style.
# A recommendation, not a rule: --style always overrides it.
# id: Indonesian name, en: English name, style: recommended style.
DISCIPLINES = [
    {"id": "Kedokteran", "en": "Medicine", "style": "vancouver"},
    {"id": "Keperawatan", "en": "Nursing", "style": "apa"},
    {"id": "Farmasi", "en": "Pharmacy", "style": "vancouver"},
    {"id": "Kesehatan Masyarakat", "en": "Public Health", "style": "apa"},
    {"id": "Psikologi", "en": "Psychology", "style": "apa"},
    {"id": "Hukum", "en": "Law", "style": "chicago"},
    {"id": "Ekonomi", "en": "Economics", "style": "harvard"},
    {"id": "Manajemen", "en": "Management", "style": "apa"},
    {"id": "Akuntansi", "en": "Accounting", "style": "apa"},
    {"id": "Teknik Informatika", "en": "Informatics", "style": "ieee"},
    {"id": "Ilmu Komputer", "en": "Computer Science", "style": "ieee"},
    {"id": "Teknik Elektro", "en": "Electrical Engineering", "style": "ieee"},
    {"id": "Teknik Sipil", "en": "Civil Engineering", "style": "ieee"},
    {"id": "Teknik Mesin", "en": "Mechanical Engineering", "style": "ieee"},
    {"id": "Pendidikan", "en": "Education", "style": "apa"},
    {"id": "Sastra Inggris", "en": "English Literature", "style": "mla"},
    {"id": "Bahasa Indonesia", "en": "Indonesian Language", "style": "mla"},
    {"id": "Sejarah", "en": "History", "style": "chicago"},
    {"id": "Sosiologi", "en": "Sociology", "style": "apa"},
    {"id": "Biologi", "en": "Biology", "style": "apa"},
    {"id": "Fisika", "en": "Physics", "style": "ieee"},
]

MESSAGES = {
    "id": {
        "references_heading": "Daftar Pustaka",
        "missing": "PERLU RUJUKAN",
        "missing_note": "Rujukan berikut tidak ditemukan di bibliografi — jangan dikarang, tambahkan datanya dulu:",
        "no_citations": "Tidak ada sitasi [cite:key] yang ditemukan di teks.",
    },
    "en": {
        "references_heading": "References",
        "missing": "REFERENCE NEEDED",
        "missing_note": "These references were not found in the bibliography — do not invent them, add their data first:",
        "no_citations": "No [cite:key] citations found in the text.",
    },
}


def style_for_discipline(name: str):
    """Recommended style for a jurusan, by Indonesian or English name."""
    needle = name.strip().lower()
    for d in DISCIPLINES:
        if needle in (d["id"].lower(), d["en"].lower()):
            return d["style"]
    return None


def load_references(path: str):
    """Load a bibliography JSON file: {"key": {author fields...}}.

    Authors are stored as ["Family, Given", ...].
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {r["key"]: r for r in data}
    return data


# ======================================================================
# Reference lookup (OpenAlex / Crossref)
# ======================================================================
# Fetch real reference metadata by DOI or title, so a bibliography can
# be built without typing JSON by hand. Crossref is free and needs no
# key. OpenAlex has required a key for production use since February
# 2026: the key is free, every key gets about $1 of free usage per day,
# a single lookup by DOI or ID is free, and a search costs roughly
# $0.001. The key is read from OPENALEX_API_KEY. Crossref is tried
# first for DOIs; OpenAlex backs it up and powers title search. A
# polite mailto in the User-Agent puts requests in the APIs' polite
# pools. No data is ever invented: a failed lookup is an error, never
# a guess.
LOOKUP_USER_AGENT = (
    f"academic-jargon-buster/{__version__} (mailto:achmddfzn@proton.me)"
)
CROSSREF_URL = "https://api.crossref.org/works/{doi}"
OPENALEX_DOI_URL = "https://api.openalex.org/works/https://doi.org/{doi}"
OPENALEX_SEARCH_URL = "https://api.openalex.org/works?search={q}&per-page=1"


class LookupError(Exception):
    """A reference lookup failed (not found, rate-limited, offline)."""


def _lookup_get(url: str, timeout: int = 15):
    """GET JSON from a lookup API. Raises LookupError on any failure."""
    req = urllib.request.Request(url, headers={"User-Agent": LOOKUP_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise LookupError("not found (HTTP 404)")
        if e.code in (401, 403):
            raise LookupError(
                "API access denied (HTTP %d). OpenAlex has required a free API "
                "key since February 2026: create one at "
                "https://openalex.org/settings/api and set OPENALEX_API_KEY."
                % e.code
            )
        if e.code == 429:
            raise LookupError(
                "rate limited by the API (HTTP 429). OpenAlex allows about $1 "
                "of free usage per key per day; try again later, or set "
                "OPENALEX_API_KEY (free at https://openalex.org/settings/api) "
                "to use your own daily allowance."
            )
        raise LookupError(f"lookup failed (HTTP {e.code})")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LookupError(f"lookup failed: {e}")


def _crossref_type(kind: str) -> str:
    return {
        "journal-article": "article",
        "proceedings-article": "conference",
        "book-chapter": "chapter",
        "book": "book",
        "monograph": "book",
    }.get(kind, "article")


def _crossref_to_ref(msg: dict) -> dict:
    """Crossref work message -> repo reference dict."""
    title = (msg.get("title") or [""])[0]
    authors = []
    for a in msg.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        authors.append(f"{family}, {given}" if given else family)
    venue = (msg.get("container-title") or [""])[0]
    year = None
    for key in ("published", "issued", "created"):
        parts = (msg.get(key) or {}).get("date-parts")
        if parts and parts[0]:
            year = parts[0][0]
            break
    ref = {
        "authors": authors,
        "title": title,
        "type": _crossref_type(msg.get("type", "")),
        "venue": venue,
        "year": year,
    }
    if msg.get("DOI"):
        ref["doi"] = msg["DOI"]
    return ref


def _openalex_type(kind: str) -> str:
    return {
        "article": "article",
        "proceedings-article": "conference",
        "book-chapter": "chapter",
        "book": "book",
    }.get(kind, "article")


def _openalex_to_ref(work: dict) -> dict:
    """OpenAlex work -> repo reference dict."""
    title = work.get("title") or work.get("display_name") or ""
    authors = []
    for a in work.get("authorships", []):
        name = (a.get("author") or {}).get("display_name", "")
        if not name:
            continue
        parts = name.split()
        if len(parts) > 1:
            authors.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
        else:
            authors.append(name)
    source = (work.get("primary_location") or {}).get("source") or {}
    ref = {
        "authors": authors,
        "title": title,
        "type": _openalex_type(work.get("type", "")),
        "venue": source.get("display_name", ""),
        "year": work.get("publication_year"),
    }
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    if doi:
        ref["doi"] = doi
    return ref


def _openalex_url(url: str) -> str:
    """Append the OpenAlex API key when OPENALEX_API_KEY is set."""
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if not key:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}api_key={key}"


def fetch_reference_by_doi(doi: str) -> dict:
    """Fetch one reference by DOI: Crossref first, OpenAlex as backup."""
    doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    if not doi:
        raise LookupError("empty DOI")
    try:
        msg = _lookup_get(CROSSREF_URL.format(doi=quote(doi, safe="/")))
        return _crossref_to_ref(msg["message"])
    except LookupError:
        pass  # fall through to OpenAlex
    work = _lookup_get(_openalex_url(OPENALEX_DOI_URL.format(doi=quote(doi, safe="/"))))
    return _openalex_to_ref(work)


def search_reference_by_title(title: str) -> dict:
    """Fetch the best OpenAlex match for a title."""
    title = title.strip()
    if not title:
        raise LookupError("empty title")
    data = _lookup_get(_openalex_url(OPENALEX_SEARCH_URL.format(q=quote(title))))
    results = data.get("results") or []
    if not results:
        raise LookupError(f"no match found for title: {title}")
    return _openalex_to_ref(results[0])


def lookup_reference(query: str) -> dict:
    """Fetch one reference by DOI or title.

    A query that looks like a DOI (starts with 10. or is a doi.org URL)
    goes to fetch_reference_by_doi; anything else is a title search.
    """
    q = query.strip()
    if q.startswith("10.") or "doi.org/" in q:
        return fetch_reference_by_doi(q)
    return search_reference_by_title(q)


def _doi_source_status(url: str) -> str:
    """One DOI lookup -> 'ok', 'not-found', or 'error' (never invented)."""
    try:
        _lookup_get(url)
        return "ok"
    except LookupError as e:
        return "not-found" if "404" in str(e) else "error"


def _doi_verdict(entry: dict) -> str:
    """Combine both sources into ok / missing / unverified / no-doi.

    A DOI only needs to exist in one source to be real: arXiv and
    datasets register with DataCite, not Crossref. 'missing' therefore
    needs both sources to say 404; one source alone is 'unverified'.
    """
    if not entry["doi"]:
        return "no-doi"
    checked = [s for s in (entry["crossref"], entry["openalex"])
               if s in ("ok", "not-found")]
    if "ok" in checked:
        return "ok"
    if len(checked) == 2:
        return "missing"
    return "unverified"


def verify_reference_dois(references: dict) -> dict:
    """Check every reference DOI against Crossref and OpenAlex.

    Returns {key: {doi, crossref, openalex, verdict}}. OpenAlex has
    required a key since February 2026; without OPENALEX_API_KEY its
    column is 'skipped' and a DOI missing from Crossref alone stays
    'unverified' instead of being called fake.
    """
    openalex_available = bool(os.environ.get("OPENALEX_API_KEY", "").strip())
    result = {}
    for key, ref in references.items():
        doi = str(ref.get("doi") or "").strip()
        entry = {"doi": doi, "crossref": "no-doi", "openalex": "no-doi"}
        if doi:
            entry["crossref"] = _doi_source_status(
                CROSSREF_URL.format(doi=quote(doi, safe="/")))
            if openalex_available:
                entry["openalex"] = _doi_source_status(
                    _openalex_url(
                        OPENALEX_DOI_URL.format(doi=quote(doi, safe="/"))))
            else:
                entry["openalex"] = "skipped"
        entry["verdict"] = _doi_verdict(entry)
        result[key] = entry
    return result


_VERIFY_STRINGS = {
    "id": {
        "heading": "Verifikasi DOI (Crossref + OpenAlex)",
        "cols": ("kunci", "doi", "crossref", "openalex", "hasil"),
        "ok": "ok",
        "missing": "TIDAK DITEMUKAN",
        "unverified": "belum terverifikasi",
        "no_doi": "tanpa DOI",
        "skipped": "tanpa key",
        "src": {"ok": "ok", "not-found": "tidak ada",
                "no-doi": "tanpa DOI", "skipped": "tanpa key",
                "error": "error"},
        "summary": (
            "Terverifikasi {ok} dari {total} DOI; tidak ditemukan {missing}, "
            "belum terverifikasi {unverified}, tanpa DOI {no_doi}."
        ),
        "note": (
            "DOI yang baru dicek satu sumber dilaporkan 'belum terverifikasi', "
            "bukan palsu. Set OPENALEX_API_KEY agar dua sumber diperiksa."
        ),
        "empty": "Tidak ada referensi di bibliografi.",
    },
    "en": {
        "heading": "DOI verification (Crossref + OpenAlex)",
        "cols": ("key", "doi", "crossref", "openalex", "result"),
        "ok": "ok",
        "missing": "NOT FOUND",
        "unverified": "unverified",
        "no_doi": "no DOI",
        "skipped": "no key",
        "src": {"ok": "ok", "not-found": "not found",
                "no-doi": "no DOI", "skipped": "no key",
                "error": "error"},
        "summary": (
            "Verified {ok} of {total} DOIs; not found {missing}, "
            "unverified {unverified}, no DOI {no_doi}."
        ),
        "note": (
            "A DOI checked in only one source is 'unverified', not fake. "
            "Set OPENALEX_API_KEY so both sources are checked."
        ),
        "empty": "No references in the bibliography.",
    },
}


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def format_verification(result: dict, lang: str = "id") -> str:
    """Human-readable table for verify_reference_dois()."""
    t = _VERIFY_STRINGS.get(lang, _VERIFY_STRINGS["id"])
    if not result:
        return t["empty"]
    key_w = max([len(t["cols"][0])] + [len(k) for k in result])
    doi_w = max([len(t["cols"][1])] + [min(len(r["doi"]), 40)
                                       for r in result.values()])
    header = (f"{t['cols'][0]:<{key_w}}  {t['cols'][1]:<{doi_w}}  "
              f"{t['cols'][2]:<10}  {t['cols'][3]:<10}  {t['cols'][4]}")
    lines = [t["heading"], "", header, "-" * len(header)]
    counts = {"ok": 0, "missing": 0, "unverified": 0, "no-doi": 0}
    for key, ref in result.items():
        counts[ref["verdict"]] += 1
        label = t[ref["verdict"].replace("-", "_")]
        crossref = t["src"].get(ref["crossref"], ref["crossref"])
        openalex = t["src"].get(ref["openalex"], ref["openalex"])
        lines.append(
            f"{key:<{key_w}}  {_clip(ref['doi'], doi_w):<{doi_w}}  "
            f"{crossref:<10}  {openalex:<10}  {label}"
        )
    lines += ["", t["summary"].format(
        total=len(result), ok=counts["ok"], missing=counts["missing"],
        unverified=counts["unverified"], no_doi=counts["no-doi"]), t["note"]]
    return "\n".join(lines) + "\n"


def reference_key(ref: dict, existing: dict | None = None) -> str:
    """Suggested bibliography key: first author family name + year.

    Appends a, b, ... when the key is already taken.
    """
    authors = ref.get("authors") or []
    family = _family(authors[0]).lower() if authors else "unknown"
    family = re.sub(r"[^a-z0-9]+", "", family) or "unknown"
    base = f"{family}{ref.get('year') or ''}"
    if not existing or base not in existing:
        return base
    suffix = ord("a")
    while f"{base}{chr(suffix)}" in existing:
        suffix += 1
    return f"{base}{chr(suffix)}"


def save_reference(ref: dict, path: str, key: str | None = None) -> str:
    """Append one reference to a bibliography JSON file. Returns its key."""
    refs = {}
    if os.path.isfile(path):
        refs = load_references(path)
    key = key or reference_key(ref, refs)
    refs[key] = ref
    with open(path, "w", encoding="utf-8") as f:
        json.dump(refs, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return key


def _family(author: str) -> str:
    return author.split(",", 1)[0].strip()


def _initials(author: str) -> str:
    parts = author.split(",", 1)
    if len(parts) < 2:
        return ""
    return "".join(f"{w[0]}." for w in parts[1].strip().split() if w)


def _given(author: str) -> str:
    parts = author.split(",", 1)
    return parts[1].strip() if len(parts) > 1 else ""


def _authors_apa(authors):
    formatted = [f"{_family(a)}, {_initials(a)}" for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _authors_mla(authors):
    if len(authors) == 1:
        return f"{_family(authors[0])}, {_given(authors[0])}"
    if len(authors) == 2:
        return f"{_family(authors[0])}, {_given(authors[0])}, and {_given(authors[1])} {_family(authors[1])}"
    return f"{_family(authors[0])}, {_given(authors[0])}, et al."


def _authors_chicago(authors):
    formatted = [f"{_family(authors[0])}, {_given(authors[0])}"] + [
        f"{_given(a)} {_family(a)}" for a in authors[1:]
    ]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, and {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"


def _authors_ieee(authors):
    return ", ".join(f"{_initials(a)} {_family(a)}" for a in authors)


def _authors_vancouver(authors):
    formatted = [f"{_family(a)} {_initials(a).replace('.', '')}" for a in authors]
    if len(formatted) > 6:
        return ", ".join(formatted[:6]) + ", et al"  # no period: format_reference adds one
    return ", ".join(formatted)


def _venue(ref):
    parts = []
    if ref.get("venue"):
        parts.append(ref["venue"])
    if ref.get("volume"):
        vol = f"vol. {ref['volume']}"
        if ref.get("issue"):
            vol += f", no. {ref['issue']}"
        parts.append(vol)
    if ref.get("pages"):
        parts.append(f"pp. {ref['pages']}")
    return ", ".join(parts)


def _doi_url(ref):
    if ref.get("doi"):
        return f"https://doi.org/{ref['doi']}"
    if ref.get("arxiv"):
        return f"https://arxiv.org/abs/{ref['arxiv']}"
    return ref.get("url", "")


def format_reference(ref, style: str) -> str:
    """Format one bibliography entry in the given style (simplified)."""
    authors = ref.get("authors", [])
    year = ref.get("year", "n.d.")
    title = ref.get("title", "")
    venue = _venue(ref)
    link = _doi_url(ref)
    if style == "apa":
        out = f"{_authors_apa(authors)} ({year}). {title}."
        if venue:
            out += f" {venue}."
        if link:
            out += f" {link}"
        return out
    if style == "mla":
        out = f"{_authors_mla(authors)}. “{title}.”"
        if venue:
            out += f" {venue},"
        out += f" {year}."
        if link:
            out += f" {link}."
        return out
    if style == "chicago":
        out = f"{_authors_chicago(authors)}. {year}. “{title}.”"
        if venue:
            out += f" {venue}."
        if link:
            out += f" {link}."
        return out
    if style == "ieee":
        out = f"{_authors_ieee(authors)}, “{title},”"
        if venue:
            out += f" {venue},"
        out += f" {year}."
        if link:
            out += f" {link}."
        return out
    if style == "harvard":
        first = _family(authors[0]) if authors else ""
        etal = " et al." if len(authors) > 3 else ""
        if len(authors) in (2, 3):
            first = ", ".join(_family(a) for a in authors[:-1]) + f" and {_family(authors[-1])}"
        out = f"{first}{etal} ({year}) '{title}',"
        if venue:
            out += f" {venue}."
        if link:
            out += f" Available at: {link}"
        return out
    if style == "vancouver":
        out = f"{_authors_vancouver(authors)}. {title}."
        if venue:
            out += f" {venue};"
        out += f" {year}."
        if link:
            out += f" Available from: {link}"
        return out
    raise ValueError(f"unknown style: {style}")


def _in_text(ref, style: str, number: int) -> str:
    authors = ref.get("authors", [])
    year = ref.get("year", "n.d.")
    first = _family(authors[0]) if authors else "Anon."
    etal = " et al." if len(authors) > 2 else ""
    if len(authors) == 2:
        first = f"{_family(authors[0])} and {_family(authors[1])}"
    if style == "apa":
        return f"({first}{etal}, {year})"
    if style == "mla":
        return f"({first}{etal})"
    if style == "chicago":
        return f"({first}{etal} {year})"
    if style in ("ieee", "vancouver"):
        return f"[{number}]"
    if style == "harvard":
        return f"({first}{etal}, {year})"
    raise ValueError(f"unknown style: {style}")


def weave(text: str, references: dict, style: str = "apa", lang: str = "id"):
    """Replace [cite:key] / \\cite{key} markers with in-text citations.

    Returns (woven_text, bibliography_text). Unknown keys are marked
    [PERLU RUJUKAN: key] / [REFERENCE NEEDED: key], never invented.
    """
    if style not in STYLES:
        raise ValueError(f"unknown style: {style}; choose one of {', '.join(STYLES)}")
    msg = MESSAGES["en" if lang == "en" else "id"]
    order = []
    missing = []

    def replace(match):
        key = (match.group(1) or match.group(2)).strip()
        if key not in references:
            if key not in missing:
                missing.append(key)
            return f"[{msg['missing']}: {key}]"
        if key not in order:
            order.append(key)
        return _in_text(references[key], style, order.index(key) + 1)

    pattern = re.compile(r"(?:\[cite:([^\]]+)\]|\\cite\{([^}]+)\})")
    woven = pattern.sub(replace, text)
    lines = [woven, "", f"## {msg['references_heading']}", ""]
    if not order and not missing:
        lines.append(msg["no_citations"])
    for i, key in enumerate(order, 1):
        prefix = f"[{i}] " if style in ("ieee", "vancouver") else ""
        lines.append(f"{prefix}{format_reference(references[key], style)}")
    if missing:
        lines += ["", msg["missing_note"]]
        for key in missing:
            lines.append(f"- {key}")
    return "\n".join(lines) + "\n", woven


# ======================================================================
# BibTeX export
# ======================================================================
# Turn a bibliography JSON file into a .bib file ready for LaTeX /
# Overleaf. Entry types follow the stored "type": article -> @article,
# book -> @book, conference -> @inproceedings, chapter -> @incollection,
# anything else -> @misc. Only fields actually present are exported —
# nothing is invented, and a missing title simply means no title field.
# LaTeX special characters in author/title/venue are escaped.
_BIBTEX_TYPES = {
    "article": "article",
    "book": "book",
    "conference": "inproceedings",
    "chapter": "incollection",
}

_BIBTEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _bibtex_escape(text) -> str:
    return "".join(_BIBTEX_ESCAPES.get(ch, ch) for ch in str(text))


def _bibtex_pages(pages) -> str:
    """Normalise a pages value to BibTeX form, e.g. '189-194' -> '189--194'."""
    p = str(pages).replace("pp. ", "").strip()
    return p.replace("--", "-").replace("-", "--")


def _bibtex_entry(key: str, ref: dict) -> str:
    entry_type = _BIBTEX_TYPES.get(ref.get("type", ""), "misc")
    fields = []
    authors = ref.get("authors") or []
    if authors:
        fields.append(("author", " and ".join(_bibtex_escape(a) for a in authors)))
    if ref.get("title"):
        fields.append(("title", _bibtex_escape(ref["title"])))
    venue = ref.get("venue", "")
    pages = ref.get("pages", "")
    if entry_type == "incollection" and ", pp. " in venue:
        venue, _, pp = venue.partition(", pp. ")
        pages = pages or pp
    if entry_type == "article":
        if venue:
            fields.append(("journal", _bibtex_escape(venue)))
    elif entry_type == "book":
        if venue:
            fields.append(("publisher", _bibtex_escape(venue)))
    elif entry_type in ("inproceedings", "incollection"):
        if venue:
            fields.append(("booktitle", _bibtex_escape(venue)))
    elif venue:
        fields.append(("note", _bibtex_escape(venue)))
    if ref.get("volume"):
        fields.append(("volume", str(ref["volume"])))
    if ref.get("issue"):
        fields.append(("number", str(ref["issue"])))
    if pages:
        fields.append(("pages", _bibtex_pages(pages)))
    if ref.get("year"):
        fields.append(("year", str(ref["year"])))
    if ref.get("doi"):
        fields.append(("doi", ref["doi"]))
    if ref.get("arxiv"):
        fields.append(("eprint", ref["arxiv"]))
        fields.append(("archivePrefix", "arXiv"))
    if ref.get("url"):
        fields.append(("url", ref["url"]))
    lines = [f"@{entry_type}{{{key},"]
    for name, value in fields:
        lines.append(f"  {name} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def export_bibtex(references: dict) -> str:
    """Export a bibliography dict {key: ref} to BibTeX text, sorted by key."""
    return "\n\n".join(_bibtex_entry(k, references[k]) for k in sorted(references)) + "\n"


# ======================================================================
# Citation audit
# ======================================================================
# Check a manuscript's citations against its bibliography before it is
# submitted: which [cite:key] / \cite{key} markers have no bibliography
# entry (missing — the reader can never check them), and which
# bibliography entries are never cited (unused). Optionally verify that
# each cited reference's DOI / arXiv / URL actually resolves, with a
# plain HEAD request. A failed check is reported, never faked: a link
# that cannot be reached is "unreachable", not "alive".
_CITE_PATTERN = re.compile(r"(?:\[cite:([^\]]+)\]|\\cite\{([^}]+)\})")


def audit_citations(text: str, references: dict) -> dict:
    """Audit citations in `text` against `references`.

    Returns {"cited": [...], "counts": {...}, "missing": [...],
    "unused": [...]}. `cited` keeps first-appearance order; `missing`
    and `unused` are sorted.
    """
    cited = []
    counts = {}
    for match in _CITE_PATTERN.finditer(text):
        key = (match.group(1) or match.group(2)).strip()
        counts[key] = counts.get(key, 0) + 1
        if key not in cited:
            cited.append(key)
    missing = sorted(k for k in cited if k not in references)
    unused = sorted(k for k in references if k not in counts)
    return {"cited": cited, "counts": counts, "missing": missing, "unused": unused}


def _reference_link(ref: dict) -> str:
    """The checkable link for a reference: DOI, arXiv, or plain URL."""
    if ref.get("doi"):
        return f"https://doi.org/{ref['doi']}"
    if ref.get("arxiv"):
        return f"https://arxiv.org/abs/{ref['arxiv']}"
    return ref.get("url", "")


def _url_alive(url: str, timeout: int = 10) -> tuple[bool, str]:
    """HEAD the URL. Returns (alive, status): status is the HTTP code
    or the error text when the request failed."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": LOOKUP_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, str(resp.status)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # offline, DNS failure, timeout, ...
        return False, str(e)


def check_reference_links(references: dict, keys=None) -> dict:
    """Check each reference's link. Returns {key: (url, alive, status)}.
    Keys without any link are skipped."""
    out = {}
    for key in (keys if keys is not None else sorted(references)):
        ref = references.get(key)
        if not ref:
            continue
        url = _reference_link(ref)
        if not url:
            continue
        alive, status = _url_alive(url)
        out[key] = (url, alive, status)
    return out


_AUDIT_STRINGS = {
    "id": {
        "heading": "Hasil audit sitasi",
        "cited": "Dikutip di naskah",
        "missing": "HILANG dari bibliografi (tidak bisa dicek pembaca)",
        "unused": "Ada di bibliografi tapi tidak pernah dikutip",
        "dead": "Link mati / tidak bisa dijangkau",
        "ok": "Semua sitasi ada di bibliografi.",
        "none_missing": "Tidak ada sitasi yang hilang.",
        "none_unused": "Tidak ada entri yang tidak terpakai.",
        "none_dead": "Semua link yang dicek masih hidup.",
    },
    "en": {
        "heading": "Citation audit result",
        "cited": "Cited in the text",
        "missing": "MISSING from the bibliography (the reader can never check them)",
        "unused": "In the bibliography but never cited",
        "dead": "Dead / unreachable links",
        "ok": "Every citation is in the bibliography.",
        "none_missing": "No missing citations.",
        "none_unused": "No unused entries.",
        "none_dead": "Every checked link is alive.",
    },
}


def format_audit(result: dict, lang: str = "id", links: dict | None = None) -> str:
    """Render an audit result as a readable report."""
    s = _AUDIT_STRINGS["en" if lang == "en" else "id"]
    lines = [f"# {s['heading']}", ""]
    lines.append(f"{s['cited']}: {len(result['cited'])}")
    for key in result["cited"]:
        lines.append(f"- {key} (x{result['counts'][key]})")
    lines.append("")
    if result["missing"]:
        lines.append(f"## {s['missing']}")
        for key in result["missing"]:
            lines.append(f"- {key}")
    else:
        lines.append(s["none_missing"])
    lines.append("")
    if result["unused"]:
        lines.append(f"## {s['unused']}")
        for key in result["unused"]:
            lines.append(f"- {key}")
    else:
        lines.append(s["none_unused"])
    if links is not None:
        lines.append("")
        dead = {k: v for k, v in links.items() if not v[1]}
        if dead:
            lines.append(f"## {s['dead']}")
            for key, (url, _alive, status) in sorted(dead.items()):
                lines.append(f"- {key}: {url} ({status})")
        else:
            lines.append(s["none_dead"])
    if not result["missing"] and not result["unused"]:
        lines.append("")
        lines.append(s["ok"])
    return "\n".join(lines) + "\n"


# ======================================================================
# NEW ENGINE: Academic Text Quality Analyzer
# ======================================================================
# Integrated engine that combines jargon detection, citation analysis,
# DOI verification, and bibliography completeness checking into a
# single comprehensive report for academic texts.
# ======================================================================


# ======================================================================
# Style check (cek gaya) — fourth component of analyze
# ======================================================================
# Rule-based signals for stiff Indonesian academic prose, written from
# Indonesian grammar (EYD/KBBI), not from any other project's tables:
# light verbs paired with nominalized nouns, stacked connectors,
# passive pile-ups, calqued relatives, and flat sentence rhythm.
# This is a style report, not a rewrite and not a detector dodge:
# flagged patterns are suggestions for the author's own edit.
# Thresholds were calibrated on this repo's own sample texts
# (demos/citation-weaver/contoh_id.txt, demos/jargon-buster/test_paper.txt):
# clean academic prose passes all five signals.

# Light verbs that turn a verb into a noun phrase: "melakukan
# pengukuran" says in three words what "mengukur" says in one.
_LIGHT_VERBS = (
    "melakukan", "memberikan", "mengalami", "melaksanakan",
    "mengadakan", "menjalani",
)
# Nominalized endings: a noun built from a verb.
_NOMINAL_ENDINGS = ("an", "isasi", "asi", "itas", "isme", "usi")
# Deverbal nouns that do not end in a nominal ending.
_NOMINAL_WORDS = ("analisis", "pengaruh", "kontribusi")
_LIGHT_VERB_RE = re.compile(
    r"\b(" + "|".join(_LIGHT_VERBS) + r")\b"
    r"(?:\s+(?:terhadap|atas|antara|sebesar|kepada|dalam|dari|untuk|dengan|yang))?"
    r"\s+([A-Za-z]+(?:an|isasi|asi|itas|isme|usi)\b|analisis|pengaruh|kontribusi)",
    re.IGNORECASE,
)

# Discourse connectors that, stacked, make the text read like a list
# of transitions instead of an argument.
_CONNECTORS = (
    "selain itu", "namun demikian", "di sisi lain", "oleh karena itu",
    "dengan demikian", "lebih lanjut", "sementara itu", "akan tetapi",
    "di samping itu", "sebagai tambahan", "pada akhirnya",
    "secara keseluruhan", "dalam hal ini", "berdasarkan hal tersebut",
)

# Common passive verbs in academic Indonesian. Passive itself is
# legitimate; the signal is a pile-up of them.
_PASSIVE_VERBS = (
    "dilakukan", "dilaksanakan", "diperoleh", "ditunjukkan", "digunakan",
    "dibuat", "diberikan", "ditemukan", "dijelaskan", "dinyatakan",
    "ditetapkan", "diperlihatkan", "dilaporkan", "dianalisis", "diukur",
    "dihitung", "dibandingkan", "disimpulkan", "diharapkan", "diketahui",
)

# "yang mana" and joined "dimana" as relative pronouns are calques
# from English "which"/"where". (Separate "di mana" for a real place
# is correct and is not flagged.)
_YANG_MANA_RE = re.compile(r"\byang mana\b|\bdimana\b", re.IGNORECASE)


def _split_sentences(text: str) -> list[str]:
    """Sentences as strings; splits on . ! ? followed by space/end."""
    parts = re.split(r"[.!?]+(?:\s+|$)", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _sentence_word_counts(text: str) -> list[int]:
    """Word counts per sentence; splits on . ! ? followed by space/end."""
    return [len(s.split()) for s in _split_sentences(text)]


def _stdev(values: list[int]) -> float:
    """Population standard deviation, no statistics import needed."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return round(var ** 0.5, 1)


def check_style(text: str) -> dict:
    """Check Indonesian academic prose for stiff-style signals.

    Returns a dict with keys:
    - signals: per-signal {count, flagged, examples} (rhythm also
      carries sentence count and stdev)
    - style_score: 0-25, five points per clean signal
    - flagged: names of the flagged signals

    Density signals need at least two occurrences to flag, so one
    stray connector in a short note does not fail the check. Rhythm
    is only judged on five or more sentences: flagged when 60% or
    more of them sit within two words of the mean sentence length.
    """
    words = text.split()
    n_words = len(words)
    per_100 = (lambda c: round(c / max(1, n_words) * 100, 1))

    matches = _LIGHT_VERB_RE.findall(text)
    nominal = {
        "count": len(matches),
        "density_per_100": per_100(len(matches)),
        "flagged": len(matches) >= 2 and per_100(len(matches)) > 1.0,
        "examples": [" ".join(m).strip() for m in matches[:3]],
    }

    conn_hits = []
    for conn in _CONNECTORS:
        conn_hits += [conn] * len(
            re.findall(r"\b" + re.escape(conn) + r"\b", text, re.IGNORECASE))
    connectors = {
        "count": len(conn_hits),
        "density_per_100": per_100(len(conn_hits)),
        "flagged": len(conn_hits) >= 2 and per_100(len(conn_hits)) > 2.0,
        "examples": conn_hits[:3],
    }

    passive_hits = []
    for verb in _PASSIVE_VERBS:
        passive_hits += [verb] * len(
            re.findall(r"\b" + verb + r"\b", text, re.IGNORECASE))
    passive = {
        "count": len(passive_hits),
        "density_per_100": per_100(len(passive_hits)),
        "flagged": len(passive_hits) >= 3 and per_100(len(passive_hits)) > 5.0,
        "examples": passive_hits[:3],
    }

    ym = _YANG_MANA_RE.findall(text)
    yang_mana = {
        "count": len(ym),
        "flagged": len(ym) >= 1,
        "examples": [m.lower() for m in ym[:3]],
    }

    counts = _sentence_word_counts(text)
    if len(counts) >= 5:
        mean = sum(counts) / len(counts)
        near = sum(1 for x in counts if abs(x - mean) <= 2)
        share = round(near / len(counts), 2)
    else:
        share = None
    rhythm = {
        "sentences": len(counts),
        "stdev": _stdev(counts) if len(counts) >= 2 else None,
        "same_length_share": share,
        "flagged": share is not None and share >= 0.6,
    }

    signals = {
        "nominalization": nominal,
        "connectors": connectors,
        "passive": passive,
        "yang_mana": yang_mana,
        "rhythm": rhythm,
    }
    flagged = [name for name, s in signals.items() if s["flagged"]]
    return {
        "signals": signals,
        "style_score": 5 * (5 - len(flagged)),
        "flagged": flagged,
    }


# ======================================================================
# Style rewrite suggestions (saran rewrite gaya)
# ======================================================================
# For each stiff-style pattern found by check_style(), propose a
# concrete replacement — shown before/after, never applied silently.
# The verb table is written from Indonesian grammar: a nominalized
# noun maps to the verb that says the same thing in one word.
# Patterns that need a human decision (passive voice, rhythm, a
# "dimana" that may or may not be a place) get guidance instead of
# a mechanical replacement.

# Nominalized noun -> the verb form.
_NOUN_TO_VERB = {
    "pengukuran": "mengukur", "analisis": "menganalisis",
    "pengujian": "menguji", "penelitian": "meneliti",
    "perbandingan": "membandingkan", "perhitungan": "menghitung",
    "pengamatan": "mengamati", "evaluasi": "mengevaluasi",
    "observasi": "mengobservasi", "simulasi": "mensimulasikan",
    "pemodelan": "memodelkan", "pengaruh": "memengaruhi",
    "kontribusi": "menyumbang", "gambaran": "menggambarkan",
    "informasi": "memberi tahu", "peningkatan": "naik",
    "penurunan": "turun", "perubahan": "berubah",
    "perjalanan": "bepergian", "perawatan": "dirawat",
    "pengembangan": "mengembangkan", "penerapan": "menerapkan",
    "penggunaan": "menggunakan", "pemeriksaan": "memeriksa",
    "penyusunan": "menyusun", "pelaksanaan": "melaksanakan",
    "pembangunan": "membangun", "pembahasan": "membahas",
    "peninjauan": "meninjau", "pendekatan": "mendekati",
    "pengumpulan": "mengumpulkan", "pengolahan": "mengolah",
    "penentuan": "menentukan", "perhatian": "memperhatikan",
    "dukungan": "mendukung",
}

# Trailing prepositions that belong to the light-verb frame and can
# be dropped with it ("pengukuran terhadap suhu" -> "mengukur suhu").
# "untuk", "dengan", "dari", "dalam" are NOT safe: they change the
# meaning ("pengujian untuk validasi" is not "menguji validasi").
_SAFE_TRAILING_PREPS = ("terhadap", "atas", "antara", "sebesar", "kepada")


def _sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """(start, end, sentence) for each sentence in the text."""
    spans = []
    start = 0
    for m in re.finditer(r"[.!?]+(?:\s+|$)", text):
        end = m.end()
        sent = text[start:end].strip()
        if sent:
            spans.append((start, end, sent))
        start = end
    tail = text[start:].strip()
    if tail:
        spans.append((start, len(text), tail))
    return spans


def _context_sentence(spans, pos: int) -> str:
    for s, e, sent in spans:
        if s <= pos < e:
            return sent
    return spans[-1][2] if spans else ""


def _apply_suggestion(text: str, s: dict) -> str:
    """Return `text` with one suggestion's span replaced.

    Collapses double spaces and capitalizes the first letter of
    every sentence, so a removed sentence-initial connector or a
    split after "yang mana" still reads correctly.
    """
    new = text[:s["start"]] + (s["replacement"] or "") + text[s["end"]:]
    new = re.sub(r" {2,}", " ", new).strip()

    def _cap(m):
        return m.group(1) + m.group(2).upper()

    return re.sub(r"(^|[.!?]\s+)([a-z])", _cap, new)


def _fixed_sentence(text: str, sug: dict) -> str | None:
    """The suggestion's sentence with the replacement applied."""
    if sug["replacement"] is None:
        return None
    for s, e, sent in _sentence_spans(text):
        if s <= sug["start"] < e:
            rel = sug["start"] - s
            return _apply_suggestion(sent, {
                "start": rel,
                "end": rel + len(sug["original"]),
                "replacement": sug["replacement"],
            })
    return sug["context"]


_SUGGEST_NOTES = {
    "id": {
        "nominalization": "Pakai kata kerja langsung.",
        "connectors": "Hapus konektornya — biarkan kalimat menyambung sendiri.",
        "passive": "Pakai bentuk aktif bila pelakunya jelas.",
        "yang_mana": "Tulis ulang tanpa kalke; pisah jadi dua kalimat bila perlu.",
        "rhythm": "Variasikan panjang kalimat: pecah yang panjang, gabung yang pendek.",
    },
    "en": {
        "nominalization": "Use the verb directly.",
        "connectors": "Drop the connector — let the sentences connect the argument.",
        "passive": "Use the active form when the actor is clear.",
        "yang_mana": "Rewrite without the calque; split into two sentences if needed.",
        "rhythm": "Vary sentence length: split long ones, join short ones.",
    },
}


def suggest_style_fixes(text: str, lang: str = "id",
                        limit: int | None = 10) -> dict:
    """Propose rewrite suggestions for stiff-style patterns in `text`.

    Returns {"suggestions": [...first `limit`...], "count": total}.
    Each suggestion carries pattern, original, replacement (None when
    the fix needs a human decision), context (the sentence), fixed
    (the sentence with the replacement applied, or None), note, and
    the span offsets. Nothing is changed: the caller shows these and
    the author edits by hand. Pass limit=None to get every
    suggestion (used by --apply, which must not miss the tail).
    """
    notes = _SUGGEST_NOTES.get(lang, _SUGGEST_NOTES["id"])
    spans = _sentence_spans(text)
    suggestions = []

    # 1. Light verbs: mechanical when the noun has a verb form.
    for m in _LIGHT_VERB_RE.finditer(text):
        verb, noun = m.group(1), m.group(2)
        start, end = m.start(), m.end()
        tail = re.match(
            r"\s+(terhadap|atas|antara|sebesar|kepada)\b", text[end:])
        if tail:
            end += tail.end()
        repl = _NOUN_TO_VERB.get(noun.lower())
        suggestions.append({
            "pattern": "nominalization",
            "original": text[start:end],
            "replacement": repl,
            "context": _context_sentence(spans, start),
            "fixed": None,
            "note": notes["nominalization"],
            "start": start,
            "end": end,
        })

    # 2. Connectors: delete the connector (and a following comma).
    for conn in _CONNECTORS:
        for m in re.finditer(r"\b" + re.escape(conn) + r"\b",
                             text, re.IGNORECASE):
            start, end = m.start(), m.end()
            if end < len(text) and text[end] == ",":
                end += 1
            suggestions.append({
                "pattern": "connectors",
                "original": text[start:end],
                "replacement": "",
                "context": _context_sentence(spans, start),
                "fixed": None,
                "note": notes["connectors"],
                "start": start,
                "end": end,
            })

    # 3. Passive: one guidance suggestion per sentence that has one.
    for s, e, sent in spans:
        m = re.search(r"\b(" + "|".join(_PASSIVE_VERBS) + r")\b",
                      sent, re.IGNORECASE)
        if m:
            suggestions.append({
                "pattern": "passive",
                "original": m.group(0),
                "replacement": None,
                "context": sent,
                "fixed": None,
                "note": notes["passive"],
                "start": s + m.start(),
                "end": s + m.end(),
            })

    # 4. "yang mana" splits the sentence; "dimana" needs a decision.
    for m in _YANG_MANA_RE.finditer(text):
        word = m.group(0).lower()
        if word == "yang mana":
            start, end = m.start(), m.end()
            sentence_start = (start == 0 or (start >= 2
                              and text[start - 2] in ".!?"
                              and text[start - 1] == " "))
            if sentence_start:
                # "Yang mana" opening a sentence cannot be split off
                # mechanically; leave it as guidance.
                suggestions.append({
                    "pattern": "yang_mana",
                    "original": m.group(0),
                    "replacement": None,
                    "context": _context_sentence(spans, start),
                    "fixed": None,
                    "note": notes["yang_mana"],
                    "start": start,
                    "end": end,
                })
                continue
            if start > 0 and text[start - 1] == ",":
                start -= 1
            elif (start > 1 and text[start - 1] == " "
                    and text[start - 2] == ","):
                # ", yang mana" — swallow comma and space together.
                start -= 2
            elif start > 0 and text[start - 1] == " ":
                # Swallow the space before it, or the "." lands after
                # a gap ("metode . Hasilnya").
                start -= 1
            suggestions.append({
                "pattern": "yang_mana",
                "original": text[start:end],
                "replacement": ".",
                "context": _context_sentence(spans, start),
                "fixed": None,
                "note": notes["yang_mana"],
                "start": start,
                "end": end,
            })
        else:
            suggestions.append({
                "pattern": "yang_mana",
                "original": m.group(0),
                "replacement": None,
                "context": _context_sentence(spans, m.start()),
                "fixed": None,
                "note": notes["yang_mana"],
                "start": m.start(),
                "end": m.end(),
            })

    # 5. Rhythm: only when flagged; the longest sentence is the example.
    style = check_style(text)
    if style["signals"]["rhythm"]["flagged"]:
        longest = max(spans, key=lambda t: len(t[2].split()))
        suggestions.append({
            "pattern": "rhythm",
            "original": longest[2],
            "replacement": None,
            "context": longest[2],
            "fixed": None,
            "note": notes["rhythm"],
            "start": longest[0],
            "end": longest[1],
        })

    suggestions.sort(key=lambda s: s["start"])
    for sug in suggestions:
        sug["fixed"] = _fixed_sentence(text, sug)
    total = len(suggestions)
    shown = suggestions if limit is None else suggestions[:limit]
    return {"suggestions": shown, "count": total}


_SUGGEST_STRINGS = {
    "id": {
        "heading": "Saran rewrite gaya",
        "more": "Menampilkan {shown} dari {total} saran.",
        "labels": {
            "nominalization": "Verba ringan",
            "connectors": "Konektor",
            "passive": "Verba pasif",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "Ritme kalimat",
        },
        "before": "Sebelum",
        "after": "Sesudah",
        "none": "Tidak ada saran rewrite — gaya naskah sudah luwes.",
    },
    "en": {
        "heading": "Style rewrite suggestions",
        "more": "Showing {shown} of {total} suggestions.",
        "labels": {
            "nominalization": "Light verbs",
            "connectors": "Connectors",
            "passive": "Passive verbs",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "Sentence rhythm",
        },
        "before": "Before",
        "after": "After",
        "none": "No rewrite suggestions — the style is already fluent.",
    },
}


def format_suggestions(result: dict, lang: str = "id") -> str:
    """Render a suggest_style_fixes() result as readable before/after text."""
    s = _SUGGEST_STRINGS.get(lang, _SUGGEST_STRINGS["id"])
    suggestions = result["suggestions"]
    if not suggestions:
        return s["none"] + "\n"
    lines = [f"{s['heading']} ({result['count']}):"]
    for i, sug in enumerate(suggestions, 1):
        label = s["labels"][sug["pattern"]]
        # The span may swallow a leading space (see suggest_style_fixes);
        # display trims it.
        original = sug["original"].strip()
        if sug["replacement"] is not None:
            repl = "(hapus)" if sug["replacement"] == "" \
                else f"\"{sug['replacement']}\""
            lines.append(
                f"{i}. {label} — \"{original}\" -> {repl}")
            lines.append(f"   {s['before']}: {sug['context']}")
            lines.append(f"   {s['after']}: {sug['fixed']}")
        else:
            lines.append(f"{i}. {label} — \"{original}\"")
            lines.append(f"   {s['before']}: {sug['context']}")
            lines.append(f"   {sug['note']}")
    if result["count"] > len(suggestions):
        lines.append(s["more"].format(shown=len(suggestions),
                                      total=result["count"]))
    return "\n".join(lines) + "\n"


def _apply_one(text: str, sug: dict) -> str:
    """Return `text` with one mechanical suggestion's span replaced.

    Only the neighbourhood of the edit is touched: a double space
    created at the splice is collapsed, and a sentence-initial letter
    is capitalized only when the edit itself starts a sentence or
    ends one (a "yang mana" split). Text the suggestion does not
    cover is left exactly as it was.
    """
    start, end = sug["start"], sug["end"]
    repl = sug["replacement"] or ""
    left, right = text[:start], text[end:]
    # Drop one space only where the splice would otherwise double it:
    # the replacement ends in a space followed by one, or an empty
    # replacement between two spaces (or at the start of the text).
    # Anything else — including pre-existing double spaces — is left
    # alone.
    if right.startswith(" "):
        if repl.endswith(" "):
            right = right[1:]
        elif not repl and (not left or left.endswith(" ")):
            right = right[1:]
    new = left + repl + right
    before = text[:start].rstrip()
    at_sent_start = not before or before[-1] in ".!?"
    ends_sentence = bool(repl) and repl[-1] in ".!?"
    target = None
    if ends_sentence:
        target = start + len(repl)
    elif at_sent_start:
        target = start
    if target is not None:
        m = re.search(r"[A-Za-z]", new[target:])
        if m:
            i = target + m.start()
            new = new[:i] + new[i].upper() + new[i + 1:]
    return new


def apply_suggestions(text: str, result: dict) -> dict:
    """Apply the mechanical suggestions of a suggest_style_fixes()
    result to `text` and return the fixed text plus a report.

    Returns {"text": fixed text, "applied": [...], "skipped": [...]}.
    Guidance-only suggestions (replacement None) are skipped — they
    need a human decision — and so is any suggestion whose span
    overlaps one already applied. Edits run from the end of the text
    backwards, so earlier offsets stay valid.
    """
    applied, skipped = [], []
    used = []  # (start, end) spans already applied, original coords
    new = text
    for sug in sorted(result["suggestions"],
                      key=lambda s: s["start"], reverse=True):
        if sug["replacement"] is None:
            skipped.append(sug)
            continue
        if any(sug["start"] < e and s < sug["end"] for s, e in used):
            skipped.append(sug)
            continue
        new = _apply_one(new, sug)
        used.append((sug["start"], sug["end"]))
        applied.append(sug)
    applied.reverse()
    skipped.reverse()
    return {"text": new, "applied": applied, "skipped": skipped}


def analyze_text_quality(
    text: str,
    references: dict | None = None,
    *,
    lang: str = "id",
    verify_dois: bool = True,
    suggest: bool = False,
) -> dict:
    """Analyze an academic text for quality: jargon, citations, DOI status,
    style, and bibliography completeness.

    Returns a dict with keys:
    - jargon: list of detected jargon terms with explanations
    - citations: citation audit result (cited, missing, unused)
    - doi_verification: per-reference DOI check results
    - style: style check result (signals, style_score, flagged)
    - quality_score: composite score 0-100
    - recommendations: list of improvement suggestions
    - suggestions: rewrite suggestions from suggest_style_fixes()
      (empty unless suggest=True)

    If `references` is provided, citation audit and DOI verification are
    performed against it. Otherwise, citation and DOI checks are skipped.
    The style check always runs; its lexical signals are calibrated
    for Indonesian academic prose.
    """
    result = {
        "jargon": [],
        "citations": None,
        "doi_verification": {},
        "style": check_style(text),
        "quality_score": 0,
        "recommendations": [],
        "suggestions": {"suggestions": [], "count": 0},
    }
    if suggest:
        result["suggestions"] = suggest_style_fixes(text, lang=lang)

    # --- Jargon detection ---
    jargon_matches = find_terms(text)
    jargon_explanations = [
        {
            "term": m["term"],
            "original": m["original"],
            "translation": m["translation"],
            "field": m["field"],
            "source": m["source"],
        }
        for m in jargon_matches
    ]
    result["jargon"] = jargon_explanations

    # --- Citation audit ---
    if references is not None:
        citation_result = audit_citations(text, references)
        result["citations"] = {
            "cited": citation_result["cited"],
            "counts": citation_result["counts"],
            "missing": citation_result["missing"],
            "unused": citation_result["unused"],
        }

        # --- DOI verification ---
        if verify_dois:
            doi_result = verify_reference_dois(references)
            result["doi_verification"] = doi_result

    # --- Quality score calculation ---
    # Four parts of 25 (max 100): jargon, citations, DOI, style.
    score_parts = []

    # Jargon: every term found is explained by construction, so a run
    # with terms scores 25; a text with no recognised jargon is neutral.
    score_parts.append(25)

    # Citations completeness
    if references is not None:
        cit = result["citations"]
        total_cited = len(cit["cited"]) if cit else 0
        total_missing = len(cit["missing"]) if cit else 0
        if total_missing == 0:
            score_parts.append(25)  # all citations have bibliography entries
        else:
            score_parts.append(25 * (1 - min(total_missing / max(1, total_missing + total_cited), 1.0)))
    else:
        score_parts.append(25)  # no refs to audit = neutral

    # DOI verification quality: only entries that actually carry a DOI
    # count — a reference without one is not a failed verification.
    doi_result = result.get("doi_verification", {})
    if doi_result:
        checkable = [v for v in doi_result.values() if v.get("doi")]
        if checkable:
            ok_count = sum(1 for v in checkable if v.get("verdict") == "ok")
            score_parts.append(25 * (ok_count / len(checkable)))
        else:
            score_parts.append(25)  # no DOIs to verify = neutral
    else:
        score_parts.append(25)  # no references = neutral

    # Style: 0-25 from check_style, five points per clean signal.
    score_parts.append(result["style"]["style_score"])

    total_score = sum(score_parts)
    result["quality_score"] = round(min(total_score, 100))

    # --- Recommendations ---
    en = lang == "en"
    recs = []
    if result["citations"]:
        cit = result["citations"]
        if cit["missing"]:
            if en:
                recs.append(
                    f"{len(cit['missing'])} citations in the text have no bibliography entry: "
                    + ", ".join(cit["missing"])
                )
            else:
                recs.append(
                    f"{len(cit['missing'])} sitasi di naskah tidak ada di bibliografi: "
                    + ", ".join(cit["missing"])
                )
        if cit["unused"]:
            if en:
                recs.append(
                    f"{len(cit['unused'])} bibliography entries are never cited: "
                    + ", ".join(cit["unused"][:5])
                )
            else:
                recs.append(
                    f"{len(cit['unused'])} entri di bibliografi tidak pernah dikutip: "
                    + ", ".join(cit["unused"][:5])
                )
    if result["doi_verification"]:
        dv = result["doi_verification"]
        bad = [k for k, v in dv.items()
               if v["verdict"] in ("unverified", "missing")]
        if bad:
            if en:
                recs.append(
                    f"{len(bad)} DOIs unverified: " + ", ".join(bad)
                )
            else:
                recs.append(
                    f"{len(bad)} DOI belum terverifikasi: " + ", ".join(bad)
                )
    style = result["style"]
    for name in style["flagged"]:
        sig = style["signals"][name]
        if name == "nominalization":
            ex = ", ".join(f"'{e}'" for e in sig["examples"])
            if en:
                recs.append(
                    f"Style: {sig['count']} light-verb constructions "
                    f"({ex}) — use the verb directly."
                )
            else:
                recs.append(
                    f"Gaya: {sig['count']} konstruksi verba ringan "
                    f"({ex}) — pakai kata kerja langsung."
                )
        elif name == "connectors":
            if en:
                recs.append(
                    f"Style: {sig['count']} connectors "
                    f"({sig['density_per_100']}/100 words) — let the "
                    "sentences connect the argument instead."
                )
            else:
                recs.append(
                    f"Gaya: {sig['count']} konektor "
                    f"({sig['density_per_100']}/100 kata) — kurangi "
                    "penghubung, biarkan alur kalimat yang menyambung."
                )
        elif name == "passive":
            if en:
                recs.append(
                    f"Style: {sig['count']} passive verbs piled up — "
                    "use the active form when the actor is clear."
                )
            else:
                recs.append(
                    f"Gaya: {sig['count']} verba pasif menumpuk — "
                    "pakai bentuk aktif bila pelakunya jelas."
                )
        elif name == "yang_mana":
            if en:
                recs.append(
                    "Style: 'yang mana' / 'dimana' used as a relative "
                    "pronoun — rewrite without the calque."
                )
            else:
                recs.append(
                    "Gaya: 'yang mana' / 'dimana' sebagai kata ganti "
                    "relatif — tulis ulang tanpa kalke."
                )
        elif name == "rhythm":
            if en:
                recs.append(
                    "Style: sentence lengths are too uniform — vary "
                    "short and long sentences."
                )
            else:
                recs.append(
                    "Gaya: panjang kalimat terlalu seragam — variasikan "
                    "kalimat pendek dan panjang."
                )
    if not jargon_matches:
        if en:
            recs.append(
                "No recognised academic jargon found — consider adding "
                "terms to the dictionary"
            )
        else:
            recs.append(
                "Tidak ditemukan jargon akademik yang dikenali — pertimbangkan "
                "menambahkan istilah ke dictionary.json"
            )
    if not references:
        if en:
            recs.append(
                "Add a bibliography JSON file for citation audit and DOI verification."
            )
        else:
            recs.append(
                "Tambahkan bibliografi JSON untuk audit sitasi dan verifikasi DOI."
            )
    result["recommendations"] = recs

    return result


_ANALYZE_STRINGS = {
    "id": {
        "heading": "Analisis Kualitas Naskah",
        "score": "Skor kualitas",
        "jargon": "Istilah jargon ditemukan",
        "jargon_none": "Tidak ada istilah jargon yang dikenali.",
        "citations": "Sitasi",
        "cited": "dikutip",
        "missing": "hilang dari bibliografi",
        "unused": "tak terpakai",
        "doi": "Verifikasi DOI",
        "doi_none": "Tidak ada DOI untuk diverifikasi.",
        "style": "Gaya",
        "style_clean": "tidak ada pola kaku yang terdeteksi",
        "duplicates": "Duplikasi",
        "duplicates_none": "Tidak ada kalimat yang berulang dengan pustaka.",
        "duplicates_found": "kalimat berulang",
        "duplicates_similar": "mirip",
        "duplicates_in_text": "naskah ini",
        "duplicates_in_library": "pustaka",
        "signals": {
            "nominalization": "verba ringan",
            "connectors": "konektor",
            "passive": "verba pasif",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "ritme kalimat",
        },
        "rhythm_same": "{pct}% kalimat hampir sama panjang",
        "recs": "Rekomendasi",
        "recs_none": "Tidak ada rekomendasi — naskah sudah rapi.",
        "no_refs": "Tanpa bibliografi: audit sitasi dan verifikasi DOI dilewati.",
    },
    "en": {
        "heading": "Text Quality Analysis",
        "score": "Quality score",
        "jargon": "Jargon terms found",
        "jargon_none": "No recognised jargon terms.",
        "citations": "Citations",
        "cited": "cited",
        "missing": "missing from bibliography",
        "unused": "unused",
        "doi": "DOI verification",
        "doi_none": "No DOIs to verify.",
        "style": "Style",
        "style_clean": "no stiff patterns detected",
        "duplicates": "Duplication",
        "duplicates_none": "No sentences repeat the library.",
        "duplicates_found": "repeated sentences",
        "duplicates_similar": "similar to",
        "duplicates_in_text": "this text",
        "duplicates_in_library": "library",
        "signals": {
            "nominalization": "light verbs",
            "connectors": "connectors",
            "passive": "passive verbs",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "sentence rhythm",
        },
        "rhythm_same": "{pct}% of sentences nearly the same length",
        "recs": "Recommendations",
        "recs_none": "No recommendations — the text is in good shape.",
        "no_refs": "No bibliography: citation audit and DOI verification skipped.",
    },
}


_SCORE_PART_LABELS = {
    "id": ("Jargon", "Sitasi", "DOI", "Gaya"),
    "en": ("Jargon", "Citations", "DOI", "Style"),
}


def _score_parts(result: dict) -> list:
    """The four 25-point components behind quality_score.

    Mirrors the scoring in analyze_text_quality(): jargon is always
    25 (every term found is explained by construction), citations
    lose points for missing entries, DOI for failed verifications.
    """
    parts = [25.0]
    cit = result["citations"]
    if cit is None:
        parts.append(25.0)
    else:
        cited, missing = len(cit["cited"]), len(cit["missing"])
        parts.append(25.0 if missing == 0 else
                     25 * (1 - missing / max(1, missing + cited)))
    dv = result.get("doi_verification", {})
    checkable = [v for v in dv.values() if v.get("doi")]
    if checkable:
        ok = sum(1 for v in checkable if v.get("verdict") == "ok")
        parts.append(25 * ok / len(checkable))
    else:
        parts.append(25.0)
    parts.append(float(result["style"]["style_score"]))
    return parts


def format_analyze(result: dict, lang: str = "id") -> str:
    """Render an analyze_text_quality() result as readable text."""
    s = _ANALYZE_STRINGS.get(lang, _ANALYZE_STRINGS["id"])
    lines = [s["heading"], "",
             _bold(f"{s['score']}: {result['quality_score']}/100"),
             _green(_bar(result["quality_score"], 100))]
    labels = _SCORE_PART_LABELS.get(lang, _SCORE_PART_LABELS["id"])
    for label, value in zip(labels, _score_parts(result)):
        lines.append(f"{label:<10} {_green(_bar(value, 25))} "
                     f"{round(value):>2}/25")
    lines.append("")
    jargon = result["jargon"]
    if jargon:
        lines.append(f"{s['jargon']}: {len(jargon)}")
        for item in jargon:
            lines.append(f"  - {item['term']}: {item['translation']}")
    else:
        lines.append(s["jargon_none"])
    cit = result["citations"]
    if cit is None:
        lines.append(s["no_refs"])
    else:
        lines.append(
            f"{s['citations']}: {len(cit['cited'])} {s['cited']}, "
            f"{len(cit['missing'])} {s['missing']}, "
            f"{len(cit['unused'])} {s['unused']}"
        )
        if cit["missing"]:
            lines.append("  " + ", ".join(cit["missing"]))
    dv = result["doi_verification"]
    if dv:
        ok = sum(1 for v in dv.values() if v.get("verdict") == "ok")
        with_doi = sum(1 for v in dv.values() if v.get("doi"))
        lines.append(f"{s['doi']}: {ok}/{with_doi} ok")
        bad = [k for k, v in dv.items()
               if v.get("doi") and v.get("verdict") != "ok"]
        if bad:
            lines.append("  " + ", ".join(bad))
    else:
        lines.append(s["doi_none"])
    style = result["style"]
    if style["flagged"]:
        lines.append(f"{s['style']}: {style['style_score']}/25")
        for name in style["flagged"]:
            sig = style["signals"][name]
            label = s["signals"][name]
            if name == "rhythm":
                pct = int(sig["same_length_share"] * 100)
                lines.append(f"  - {label}: "
                             + s["rhythm_same"].format(pct=pct))
            else:
                ex = ", ".join(f"'{e}'" for e in sig["examples"])
                lines.append(f"  - {label}: {sig['count']}"
                             + (f" ({ex})" if ex else ""))
    else:
        lines.append(f"{s['style']}: {style['style_score']}/25 — "
                     f"{s['style_clean']}")
    dups = result.get("duplicates")
    if dups is not None:
        if dups["duplicates"]:
            lines.append(f"{s['duplicates']}: {dups['count']} "
                         f"{s['duplicates_found']}")
            for d in dups["duplicates"]:
                sent = d["sentence"]
                if len(sent) > 90:
                    sent = sent[:90].rstrip() + "…"
                match = d["match"]
                if len(match) > 90:
                    match = match[:90].rstrip() + "…"
                if d["source_id"] is None:
                    source = s["duplicates_in_text"]
                else:
                    source = (f"{s['duplicates_in_library']} "
                              f"#{d['source_id']}")
                lines.append(f"  - \"{sent}\" — {d['similarity']:.0%} "
                             f"{s['duplicates_similar']} \"{match}\" "
                             f"({source})")
        else:
            lines.append(s["duplicates_none"])
    sugs = result.get("suggestions") or {"suggestions": [], "count": 0}
    if sugs["suggestions"]:
        lines.append(format_suggestions(sugs, lang=lang).rstrip("\n"))
    recs = result["recommendations"]
    lines.append(f"{s['recs']}:")
    if recs:
        for r in recs:
            lines.append(f"  - {r}")
    else:
        lines.append(f"  {s['recs_none']}")
    return "\n".join(lines) + "\n"


def analyze_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Check an academic text: jargon, citations, DOI "
                    "verification, and style in one pass.")
    p.add_argument("input", nargs="?", help="plain-text file to analyze")
    p.add_argument("--text", help="analyze this text instead of a file")
    p.add_argument("--refs", help="bibliography JSON file (optional; without "
                   "it, citation audit and DOI checks are skipped)")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--no-verify", action="store_true",
                   help="skip DOI verification even when --refs is given")
    p.add_argument("--suggest", action="store_true",
                   help="also show style rewrite suggestions (before/after)")
    p.add_argument("--save", action="store_true",
                   help="record this run in the library "
                        "(~/.academic-tools/library.db)")
    p.add_argument("--duplicates", action="store_true",
                   help="also check sentences against saved runs in the "
                        "library (same database as --save)")
    p.add_argument("--title", help="label for the saved run "
                   "(default: first line of the text)")
    p.add_argument("--db", help="library database path (with --save or "
                   "--duplicates)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
        return 2

    references = None
    if args.refs:
        references = load_references(args.refs)
    result = analyze_text_quality(text, references, lang=args.lang,
                                  verify_dois=not args.no_verify,
                                  suggest=args.suggest)
    if args.duplicates:
        try:
            result["duplicates"] = find_duplicates(text, db=args.db)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
    if args.save:
        try:
            result["library_id"] = save_analysis(
                text, result, references, title=args.title, db=args.db)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_analyze(result, lang=args.lang))
        if args.save:
            sys.stdout.write(
                f"Tersimpan di pustaka (id {result['library_id']})\n")
    bad_doi = any(v.get("verdict") == "missing"
                  for v in result["doi_verification"].values())
    missing = result["citations"]["missing"] if result["citations"] else []
    return 1 if missing or bad_doi else 0


# ======================================================================
# Duplicate sentences: the text against its own saved drafts
# ======================================================================

def _normalize_sentence(sentence: str) -> str:
    """Lowercase, no punctuation, single spaces — for comparison only."""
    cleaned = re.sub(r"[^\w\s]", " ", sentence.lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _word_overlap(a: set, b: set) -> float:
    """Shared words over the shorter sentence's word count (0-1)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _sentence_similarity(a: str, b: str) -> float:
    """0-1 similarity of two normalized sentences (difflib ratio)."""
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _past_texts(db=None) -> list:
    """Saved runs as {id, title, created_at, text, text_hash}, newest first."""
    conn = open_library(db)
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, text, text_hash FROM analyses "
            "ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    return [{"id": r["id"], "title": r["title"],
             "created_at": r["created_at"], "text": r["text"],
             "text_hash": r["text_hash"]} for r in rows]


def find_duplicates(text: str, db=None, *, threshold: float = 0.8,
                    min_words: int = 6, past_runs=None) -> dict:
    """Find sentences in `text` that repeat the user's own saved drafts.

    Each sentence of at least `min_words` words is compared against
    every sentence of every saved analysis in the library, plus against
    the other sentences of the text itself. A match is a normalized
    difflib ratio of at least `threshold`; only the best match per
    sentence is reported. The text itself is never matched against its
    own saved copy (same text hash), so re-analyzing a saved run does
    not flag every sentence. A word-overlap pre-filter (half the words
    of the shorter sentence shared) keeps the comparison fast.

    Returns {"duplicates": [...], "count": n, "checked": m} where m is
    the number of saved runs compared. Each duplicate carries sentence,
    match, similarity, source_id, source_title, source_date; a repeat
    inside the text itself has source_id None and source_title
    "naskah ini".
    """
    if not 0 < threshold <= 1:
        raise ValueError("threshold harus di antara 0 dan 1")
    sentences = [s for s in _split_sentences(text)
                 if len(s.split()) >= min_words]
    if past_runs is None:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        past_runs = [r for r in _past_texts(db)
                     if r["text_hash"] != text_hash]
    normalized = [_normalize_sentence(s) for s in sentences]
    word_sets = [set(n.split()) for n in normalized]

    corpus = []
    for run in past_runs:
        for sent in _split_sentences(run["text"]):
            if len(sent.split()) < min_words:
                continue
            norm = _normalize_sentence(sent)
            corpus.append((norm, sent, set(norm.split()), run))
    duplicates = []
    for i, (sent, norm, words) in enumerate(zip(sentences, normalized,
                                                word_sets)):
        best = None
        for cand_norm, cand_sent, cand_words, run in corpus:
            if _word_overlap(words, cand_words) < 0.5:
                continue
            sim = _sentence_similarity(norm, cand_norm)
            if sim >= threshold and (best is None or sim > best[0]):
                best = (sim, cand_sent, run)
        for j in range(i + 1, len(sentences)):
            if _word_overlap(words, word_sets[j]) < 0.5:
                continue
            sim = _sentence_similarity(norm, normalized[j])
            if sim >= threshold and (best is None or sim > best[0]):
                best = (sim, sentences[j], None)
        if best is not None:
            sim, match, run = best
            duplicates.append({
                "sentence": sent, "match": match,
                "similarity": round(sim, 2),
                "source_id": run["id"] if run else None,
                "source_title": run["title"] if run else "naskah ini",
                "source_date": (run["created_at"][:10] if run else None),
            })
    return {"duplicates": duplicates, "count": len(duplicates),
            "checked": len(past_runs)}


_DUPLICATES_STRINGS = {
    "id": {
        "heading": "Duplikasi internal",
        "none": "Tidak ada kalimat yang berulang dengan pustaka.",
        "checked": "Dibandingkan dengan {n} analisis tersimpan.",
        "similar": "mirip",
        "source": "sumber",
    },
    "en": {
        "heading": "Internal duplication",
        "none": "No sentences repeat the library.",
        "checked": "Compared with {n} saved analyses.",
        "similar": "similar to",
        "source": "source",
    },
}


def format_duplicates(result: dict, lang: str = "id") -> str:
    """Render a find_duplicates() result as readable text."""
    s = _DUPLICATES_STRINGS.get(lang, _DUPLICATES_STRINGS["id"])
    lines = [s["heading"], s["checked"].format(n=result["checked"])]
    if not result["duplicates"]:
        lines.append(s["none"])
        return "\n".join(lines)
    for d in result["duplicates"]:
        if d["source_id"] is None:
            source = s["source"] + ": " + d["source_title"]
        else:
            source = (f"{s['source']}: pustaka #{d['source_id']} — "
                      f"{d['source_title']}"
                      + (f" ({d['source_date']})" if d["source_date"]
                         else ""))
        lines.append(f"  - {d['sentence']}")
        lines.append(f"    {d['similarity']:.0%} {s['similar']}: {d['match']}")
        lines.append(f"    {source}")
    return "\n".join(lines)


def duplicates_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Check a text for sentences that repeat the user's "
                    "own saved drafts in the library.")
    p.add_argument("input", nargs="?", help="plain-text file to check")
    p.add_argument("--text", help="check this text instead of a file")
    p.add_argument("--db", help="library database path "
                   "(default: ~/.academic-tools/library.db)")
    p.add_argument("--threshold", type=float, default=0.8,
                   help="minimum similarity 0-1 to report (default: 0.8)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
        return 2
    try:
        result = find_duplicates(text, db=args.db,
                                 threshold=args.threshold)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_duplicates(result) + "\n")
    return 1 if result["count"] else 0


def humanize_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Suggest style rewrites for Indonesian academic prose "
                    "(before/after per pattern). Nothing is changed unless "
                    "--apply is given: then the mechanical suggestions are "
                    "written out and the guidance-only ones are left for "
                    "the author. Exits 1 when it has suggestions, 0 when "
                    "the style is already fluent.")
    p.add_argument("input", nargs="?", help="plain-text file to check")
    p.add_argument("--text", help="check this text instead of a file")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--apply", action="store_true",
                   help="apply the mechanical suggestions")
    p.add_argument("--out", help="write the fixed text here (default: "
                   "<file>.humanized.txt, or stdout for --text)")
    p.add_argument("--in-place", action="store_true",
                   help="overwrite the input file (keeps a .bak copy)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
        return 2
    if args.in_place and not args.input:
        p.error("--in-place needs a file input")
        return 2
    if args.out and args.in_place:
        p.error("--out and --in-place cannot be combined")
        return 2
    result = suggest_style_fixes(text, lang=args.lang,
                                 limit=None if args.apply else 10)
    fixed = apply_suggestions(text, result) if args.apply else None
    if args.json:
        if fixed is not None:
            result["fixed_text"] = fixed["text"]
            result["applied"] = len(fixed["applied"])
            result["skipped"] = len(fixed["skipped"])
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_suggestions(result, lang=args.lang))
    if fixed is not None:
        en = args.lang == "en"
        n_applied, n_skipped = len(fixed["applied"]), len(fixed["skipped"])
        report = (
            f"Applied: {n_applied} mechanical suggestions; "
            f"skipped: {n_skipped} (need a human decision)."
            if en else
            f"Diterapkan: {n_applied} saran mekanis; "
            f"dilewati: {n_skipped} (butuh keputusan manual).")
        if args.in_place:
            bak = args.input + ".bak"
            with open(args.input, encoding="utf-8") as f:
                original = f.read()
            with open(bak, "w", encoding="utf-8") as f:
                f.write(original)
            with open(args.input, "w", encoding="utf-8") as f:
                f.write(fixed["text"])
            done = (f"File updated: {args.input} (backup: {bak})"
                    if en else
                    f"File diperbarui: {args.input} (salinan: {bak})")
            sys.stdout.write(f"{report}\n{done}\n")
        elif args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(fixed["text"])
            sys.stdout.write(f"{report}\n"
                             + (f"Saved to: {args.out}"
                                if en else f"Tersimpan di: {args.out}") + "\n")
        elif args.input:
            stem, ext = os.path.splitext(args.input)
            out_path = f"{stem}.humanized{ext or '.txt'}"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(fixed["text"])
            sys.stdout.write(f"{report}\n"
                             + (f"Saved to: {out_path}"
                                if en else f"Tersimpan di: {out_path}") + "\n")
        elif not args.json:
            sys.stderr.write(f"{report}\n")
            sys.stdout.write(fixed["text"])
    return 1 if result["count"] else 0


# ======================================================================
# Library — analysis history + personal bibliography (stdlib sqlite3)
# ======================================================================
# One local file, no account, no cloud. `analyze --save` records a
# run (scores, missing citations, DOI counts, style, suggestions, the
# text itself and its hash); the cited references are upserted into
# the personal bibliography. `library` reads it back: history, one
# run in detail, reference search, import/export of refs.json files.

DEFAULT_LIBRARY_DB = os.path.join(
    os.path.expanduser("~"), ".academic-tools", "library.db")

_LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    quality_score INTEGER NOT NULL,
    jargon_count INTEGER NOT NULL,
    citations_missing INTEGER NOT NULL,
    doi_ok INTEGER NOT NULL,
    doi_total INTEGER NOT NULL,
    style_score INTEGER NOT NULL,
    suggestions_count INTEGER NOT NULL,
    text_hash TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_references (
    analysis_id INTEGER NOT NULL REFERENCES analyses(id),
    ref_key TEXT NOT NULL,
    PRIMARY KEY (analysis_id, ref_key)
);
CREATE TABLE IF NOT EXISTS library_references (
    key TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,
    year INTEGER,
    doi TEXT,
    url TEXT,
    added_at TEXT NOT NULL,
    source TEXT,
    data TEXT NOT NULL
);
"""


def library_path(db: str | None = None) -> str:
    """Resolve the library database path.

    Explicit --db wins, then the ACADEMIC_LIBRARY_DB environment
    variable (used by the tests), then ~/.academic-tools/library.db.
    """
    if db:
        return db
    env = os.environ.get("ACADEMIC_LIBRARY_DB")
    if env:
        return env
    return DEFAULT_LIBRARY_DB


def open_library(db: str | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the library database.

    A corrupt or unreadable file raises ValueError with a plain
    message instead of leaking a sqlite3 traceback to the user.
    """
    path = library_path(db)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.executescript(_LIBRARY_SCHEMA)
    except sqlite3.Error:
        if conn is not None:
            conn.close()
        raise ValueError(
            f"pustaka rusak: {path} — hapus atau ganti file databasenya")
    return conn


def _ref_columns(ref: dict) -> dict:
    authors = ref.get("authors") or ref.get("author") or ""
    if isinstance(authors, list):
        authors = ", ".join(str(a) for a in authors)
    year = ref.get("year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None
    return {
        "title": ref.get("title") or "",
        "authors": str(authors),
        "year": year,
        "doi": ref.get("doi") or "",
        "url": ref.get("url") or "",
    }


def _upsert_reference(conn: sqlite3.Connection, key: str, ref: dict,
                      source: str) -> str:
    """Insert a reference, or update it when the key already exists.

    Returns "added" or "updated".
    """
    cols = _ref_columns(ref)
    # Local time, with offset: the history shows the user's date,
    # not the UTC date (which is a day behind in the evening, WIB).
    now = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")
    cur = conn.execute(
        "SELECT key FROM library_references WHERE key = ?", (key,))
    exists = cur.fetchone() is not None
    conn.execute(
        """INSERT INTO library_references
           (key, title, authors, year, doi, url, added_at, source, data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET
             title=excluded.title, authors=excluded.authors,
             year=excluded.year, doi=excluded.doi, url=excluded.url,
             source=excluded.source, data=excluded.data""",
        (key, cols["title"], cols["authors"], cols["year"], cols["doi"],
         cols["url"], now, source, json.dumps(ref, ensure_ascii=False)))
    return "updated" if exists else "added"


def save_analysis(text: str, result: dict,
                  references: dict | None = None,
                  title: str | None = None,
                  db: str | None = None) -> int:
    """Record an analyze_text_quality() run in the library.

    The cited references are upserted into the personal bibliography
    (source "analyze") and linked to the run. Returns the run id.
    """
    if title is None:
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        title = first_line[:60] or "tanpa judul"
    cit = result.get("citations") or {}
    dv = result.get("doi_verification") or {}
    with_doi = [v for v in dv.values() if v.get("doi")]
    conn = open_library(db)
    try:
        cur = conn.execute(
            """INSERT INTO analyses
               (created_at, title, quality_score, jargon_count,
                citations_missing, doi_ok, doi_total, style_score,
                suggestions_count, text_hash, text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.datetime.now().astimezone().isoformat(
                timespec="seconds"),
             title, result["quality_score"], len(result.get("jargon") or []),
             len(cit.get("missing") or []),
             sum(1 for v in with_doi if v.get("verdict") == "ok"),
             len(with_doi), result["style"]["style_score"],
             result.get("suggestions", {}).get("count", 0),
             hashlib.sha256(text.encode("utf-8")).hexdigest(), text))
        analysis_id = cur.lastrowid
        if references:
            for key in cit.get("cited") or []:
                if key in references:
                    _upsert_reference(conn, key, references[key], "analyze")
                    conn.execute(
                        "INSERT OR IGNORE INTO analysis_references "
                        "(analysis_id, ref_key) VALUES (?, ?)",
                        (analysis_id, key))
        conn.commit()
        return analysis_id
    finally:
        conn.close()


def list_analyses(db: str | None = None, limit: int = 20) -> list[dict]:
    """Past runs, newest first (id, date, title, scores)."""
    conn = open_library(db)
    try:
        rows = conn.execute(
            """SELECT id, created_at, title, quality_score, jargon_count,
                      citations_missing, doi_ok, doi_total, style_score,
                      suggestions_count
               FROM analyses ORDER BY id DESC LIMIT ?""",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_analysis(analysis_id: int,
                 db: str | None = None) -> dict | None:
    """One run in full: the row, its cited reference keys, the text."""
    conn = open_library(db)
    try:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?",
            (analysis_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        refs = conn.execute(
            "SELECT ref_key FROM analysis_references "
            "WHERE analysis_id = ? ORDER BY ref_key",
            (analysis_id,)).fetchall()
        result["references"] = [r["ref_key"] for r in refs]
        return result
    finally:
        conn.close()


def list_references(db: str | None = None, limit: int = 20) -> list[dict]:
    """Personal bibliography, most recently added first."""
    conn = open_library(db)
    try:
        rows = conn.execute(
            """SELECT key, title, authors, year, doi, url, added_at, source
               FROM library_references ORDER BY added_at DESC, key LIMIT ?""",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_references(query: str, db: str | None = None,
                      limit: int = 20) -> list[dict]:
    """Search the bibliography by key, title, authors, or DOI."""
    like = f"%{query}%"
    conn = open_library(db)
    try:
        rows = conn.execute(
            """SELECT key, title, authors, year, doi, url, added_at, source
               FROM library_references
               WHERE key LIKE ? OR title LIKE ? OR authors LIKE ?
                     OR doi LIKE ?
               ORDER BY added_at DESC, key LIMIT ?""",
            (like, like, like, like, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def import_references(refs: dict, db: str | None = None,
                      source: str = "import") -> dict:
    """Upsert a bibliography dict ({key: ref}) into the library.

    Returns {"added": n, "updated": m}.
    """
    conn = open_library(db)
    counts = {"added": 0, "updated": 0}
    try:
        for key, ref in refs.items():
            counts[_upsert_reference(conn, key, ref, source)] += 1
        conn.commit()
        return counts
    finally:
        conn.close()


def export_references(db: str | None = None) -> dict:
    """The whole personal bibliography as a {key: ref} dict."""
    conn = open_library(db)
    try:
        rows = conn.execute(
            "SELECT key, data FROM library_references ORDER BY key"
        ).fetchall()
        return {r["key"]: json.loads(r["data"]) for r in rows}
    finally:
        conn.close()


def format_history(rows: list[dict]) -> str:
    """Render list_analyses() rows as a readable table."""
    if not rows:
        return "Belum ada riwayat analisis — jalankan analyze --save dulu.\n"
    lines = ["Riwayat analisis:"]
    for r in rows:
        lines.append(
            f"  #{r['id']} {r['created_at'][:10]} {r['title']} — "
            f"skor {r['quality_score']}/100, gaya {r['style_score']}/25, "
            f"jargon {r['jargon_count']}, sitasi hilang "
            f"{r['citations_missing']}, DOI {r['doi_ok']}/{r['doi_total']}")
    return "\n".join(lines) + "\n"


def format_analysis_detail(analysis: dict) -> str:
    """Render one get_analysis() result in full."""
    lines = [
        f"Analisis #{analysis['id']} — {analysis['title']}",
        f"Tanggal: {analysis['created_at']}",
        f"Skor kualitas: {analysis['quality_score']}/100",
        f"Gaya: {analysis['style_score']}/25",
        f"Jargon: {analysis['jargon_count']} istilah",
        f"Sitasi hilang: {analysis['citations_missing']}",
        f"DOI terverifikasi: {analysis['doi_ok']}/{analysis['doi_total']}",
        f"Saran rewrite: {analysis['suggestions_count']}",
    ]
    if analysis["references"]:
        lines.append("Referensi dikutip: " + ", ".join(analysis["references"]))
    lines.append("")
    lines.append(analysis["text"])
    return "\n".join(lines) + "\n"


def format_references(rows: list[dict]) -> str:
    """Render list/search_reference rows as a readable list."""
    if not rows:
        return "Tidak ada referensi di pustaka.\n"
    lines = ["Referensi di pustaka:"]
    for r in rows:
        year = f" ({r['year']})" if r.get("year") else ""
        lines.append(f"  - {r['key']}{year}: {r.get('title') or '-'}"
                     + (f" — {r['authors']}" if r.get("authors") else "")
                     + (f" — doi:{r['doi']}" if r.get("doi") else ""))
    return "\n".join(lines) + "\n"


def library_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Analysis history and personal bibliography in one "
                    "local SQLite file (~/.academic-tools/library.db). "
                    "Pick one action per call.")
    p.add_argument("--db", help="library database path "
                   "(default: ~/.academic-tools/library.db)")
    p.add_argument("--history", action="store_true",
                   help="list past analyze runs, newest first")
    p.add_argument("--show", type=int, metavar="ID",
                   help="show one past run in full")
    p.add_argument("--refs", action="store_true",
                   help="list the personal bibliography")
    p.add_argument("--search", metavar="QUERY",
                   help="search the bibliography by key, title, authors, or DOI")
    p.add_argument("--import", dest="import_path", metavar="REFS.JSON",
                   help="import a bibliography JSON file into the library")
    p.add_argument("--export", dest="export_path", metavar="OUT.JSON",
                   help="export the personal bibliography to a JSON file")
    p.add_argument("--limit", type=int, default=20,
                   help="rows to show (default: 20)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)
    try:
        return _library_run(args, p)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1


def _library_run(args, parser) -> int:
    if args.history:
        rows = list_analyses(db=args.db, limit=args.limit)
        if args.json:
            sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_history(rows))
        return 0
    if args.show is not None:
        analysis = get_analysis(args.show, db=args.db)
        if analysis is None:
            print(f"tidak ada analisis #{args.show} di pustaka",
                  file=sys.stderr)
            return 1
        if args.json:
            sys.stdout.write(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_analysis_detail(analysis))
        return 0
    if args.search is not None:
        rows = search_references(args.search, db=args.db, limit=args.limit)
        if args.json:
            sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_references(rows))
        return 0
    if args.refs:
        rows = list_references(db=args.db, limit=args.limit)
        if args.json:
            sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_references(rows))
        return 0
    if args.import_path:
        refs = load_references(args.import_path)
        counts = import_references(refs, db=args.db)
        print(f"Ditambahkan: {counts['added']}, diperbarui: {counts['updated']}")
        return 0
    if args.export_path:
        refs = export_references(db=args.db)
        with open(args.export_path, "w", encoding="utf-8") as f:
            json.dump(refs, f, ensure_ascii=False, indent=2)
        print(f"Diekspor: {len(refs)} referensi -> {args.export_path}")
        return 0
    parser.print_help()
    return 0


def cite_main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Weave citations into narrative text.")
    p.add_argument("input", nargs="?", help="plain-text file with [cite:key] markers")
    p.add_argument("--text", help="weave this text instead of a file")
    p.add_argument("--refs", help="bibliography JSON file (required unless --list-*)")
    p.add_argument("--style", choices=STYLES, help="citation style")
    p.add_argument("--jurusan", help="major (Indonesian or English name); sets the recommended style")
    p.add_argument("--lang", choices=["id", "en"], default="id", help="output language (default: id)")
    p.add_argument("--list-styles", action="store_true", help="list citation styles and exit")
    p.add_argument("--list-jurusan", action="store_true", help="list majors and their recommended style, then exit")
    p.add_argument("--lookup", metavar="DOI-OR-TITLE",
                   help="fetch one reference by DOI or title (OpenAlex/Crossref) and print it as JSON")
    p.add_argument("--key", help="bibliography key to use with --add-to (default: auto)")
    p.add_argument("--add-to", metavar="REFS.JSON",
                   help="with --lookup: append the fetched reference to this bibliography file")
    p.add_argument("--export-bibtex", action="store_true",
                   help="export the bibliography to BibTeX (.bib) instead of weaving")
    p.add_argument("--out", metavar="FILE",
                   help="with --export-bibtex: write the .bib file here (default: stdout)")
    p.add_argument("--audit", action="store_true",
                   help="audit citations: report markers with no bibliography entry, "
                   "and entries never cited, instead of weaving")
    p.add_argument("--check-links", action="store_true",
                   help="with --audit: also verify each cited reference's DOI/arXiv/URL resolves")
    p.add_argument("--verify", action="store_true",
                   help="verify every reference DOI against Crossref and OpenAlex")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.list_styles:
        print("Citation styles: " + ", ".join(STYLES))
        return 0
    if args.list_jurusan:
        for d in DISCIPLINES:
            print(f"{d['id']} / {d['en']} — {d['style']}")
        return 0

    if args.lookup:
        try:
            ref = lookup_reference(args.lookup)
        except LookupError as e:
            p.error(str(e))
            return 2
        if args.add_to:
            key = save_reference(ref, args.add_to, key=args.key)
            print(f"Saved as [{key}] in {args.add_to}")
        else:
            print(json.dumps(ref, ensure_ascii=False, indent=2))
        return 0

    if args.export_bibtex:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --export-bibtex")
            return 2
        references = load_references(args.refs)
        bib = export_bibtex(references)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(bib)
            print(f"Wrote {len(references)} entries to {args.out}")
        else:
            sys.stdout.write(bib)
        return 0

    if args.audit:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --audit")
            return 2
        if args.text:
            text = args.text
        elif args.input:
            with open(args.input, encoding="utf-8") as f:
                text = f.read()
        else:
            p.error("give a file or --text")
            return 2
        references = load_references(args.refs)
        result = audit_citations(text, references)
        links = None
        if args.check_links:
            links = check_reference_links(references, keys=result["cited"])
        sys.stdout.write(format_audit(result, lang=args.lang, links=links))
        dead = any(not v[1] for v in (links or {}).values())
        return 1 if result["missing"] or dead else 0

    if args.verify:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --verify")
            return 2
        references = load_references(args.refs)
        result = verify_reference_dois(references)
        sys.stdout.write(format_verification(result, lang=args.lang))
        return 1 if any(r["verdict"] == "missing" for r in result.values()) else 0

    style = args.style
    if not style and args.jurusan:
        style = style_for_discipline(args.jurusan)
        if not style:
            p.error(f"unknown jurusan: {args.jurusan} (see --list-jurusan)")
            return 2
    if not style:
        style = "apa"
    if not args.refs:
        p.error("--refs <bibliography.json> is required")
        return 2

    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
        return 2

    references = load_references(args.refs)
    output, _ = weave(text, references, style=style, lang=args.lang)
    sys.stdout.write(output)
    return 0


# ======================================================================
# Thesis Prompts (Prompt Skripsi)
# ======================================================================
# Ready-made prompt templates for writing a thesis (skripsi), one per
# task: research roadmap, each chapter, defense prep, publication.
# Each template has {placeholders} the student fills with their own
# title, theory, method, data, etc., then pastes into the recommended
# AI tool (ChatGPT, Grok, Claude, Gemini, Perplexity, Manus).
# Templates are original wording written for this repo: they follow the
# usual structure of thesis-writing prompts, they do not copy any
# third-party prompt collection. The skill in
# skills/research/skripsi-prompts/SKILL.md carries the same templates.
# Rules: these prompts help the student write their own thesis. They
# never write a whole thesis for the student, and no reference or data
# is ever invented — a missing reference stays missing.
PROMPTS = [
    {
        "id": "roadmap",
        "name": "Roadmap Penelitian",
        "name_en": "Research Roadmap",
        "category": "Persiapan",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "teori", "label": "Teori yang digunakan", "label_en": "Theory used"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "bulan", "label": "Jangka waktu (bulan)", "label_en": "Duration (months)"},
            {"key": "tanggal", "label": "Tanggal mulai", "label_en": "Start date"},
        ],
        "template": (
            "Saya sedang mengerjakan skripsi berjudul {judul}, memakai teori {teori} "
            "dan metode {metode}. Bantu saya menyusun rencana kerja penelitian dari awal "
            "sampai selesai: mulai dari merumuskan masalah, membaca literatur, menyiapkan "
            "instrumen, mengumpulkan data, menganalisis, hingga menulis laporan dan "
            "menyiapkan publikasi. Waktu yang saya punya {bulan} bulan, mulai {tanggal}. "
            "Tuliskan sebagai daftar langkah berurutan dengan perkiraan durasi tiap langkahnya."
        ),
        "template_en": (
            "I am working on a thesis titled {judul}, using {teori} theory and the "
            "{metode} method. Help me build a work plan for the research from start to "
            "finish: from formulating the problem, reading the literature, preparing "
            "instruments, collecting data, analyzing, to writing the report and preparing "
            "publication. I have {bulan} months, starting {tanggal}. Write it as an "
            "ordered list of steps with an estimated duration for each step."
        ),
    },
    {
        "id": "abstrak",
        "name": "Abstrak Skripsi",
        "name_en": "Thesis Abstract",
        "category": "Abstrak",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "masalah", "label": "Masalah yang diteliti", "label_en": "Problem studied"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "hasil", "label": "Hasil utama penelitian", "label_en": "Main findings"},
            {"key": "kunci", "label": "Kata kunci (3-5 kata)", "label_en": "Keywords (3-5 words)"},
        ],
        "template": (
            "Saya sedang menulis abstrak skripsi berjudul {judul}. Masalah yang saya "
            "teliti: {masalah}. Metode yang saya pakai: {metode}. Hasil utama penelitian "
            "saya: {hasil}. Tolong susun abstrak dalam satu paragraf (sekitar 150-250 kata) "
            "dengan struktur: latar belakang singkat, tujuan, metode, hasil utama, dan "
            "kesimpulan. Akhiri dengan kata kunci: {kunci}. Gunakan bahasa akademik yang "
            "ringkas dan jelas, tanpa menambahkan data atau klaim yang tidak saya sebutkan."
        ),
        "template_en": (
            "I am writing the abstract for my thesis titled {judul}. The problem I "
            "studied: {masalah}. The method I used: {metode}. My main findings: {hasil}. "
            "Please draft the abstract as a single paragraph (about 150-250 words) with "
            "this structure: brief background, objective, method, main findings, and "
            "conclusion. End with keywords: {kunci}. Use concise, clear academic language, "
            "and do not add any data or claims I did not mention."
        ),
    },
    {
        "id": "kata-pengantar",
        "name": "Kata Pengantar",
        "name_en": "Preface",
        "category": "Persiapan",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "pembimbing", "label": "Nama dosen pembimbing", "label_en": "Supervisor's name"},
            {"key": "ucapan", "label": "Pihak yang ingin diucapkan terima kasih", "label_en": "People to thank"},
        ],
        "template": (
            "Saya sedang menulis kata pengantar skripsi berjudul {judul}, dibimbing oleh "
            "{pembimbing}. Pihak-pihak yang ingin saya ucapkan terima kasih: {ucapan}. "
            "Tolong susun kata pengantar yang sopan dan formal: buka dengan puji syukur, "
            "sebutkan judul skripsi dan tujuannya, ucapkan terima kasih kepada pihak-pihak "
            "di atas dengan kalimat yang tulus dan spesifik, lalu tutup dengan harapan "
            "semoga skripsi ini bermanfaat. Jangan tambahkan nama atau pihak yang tidak "
            "saya sebutkan."
        ),
        "template_en": (
            "I am writing the preface for my thesis titled {judul}, supervised by "
            "{pembimbing}. The people I want to thank: {ucapan}. Please draft a polite, "
            "formal preface: open with gratitude, state the thesis title and its purpose, "
            "thank the people above with sincere and specific sentences, then close with "
            "a hope that this thesis will be useful. Do not add any names or parties I "
            "did not mention."
        ),
    },
    {
        "id": "latar-belakang",
        "name": "Latar Belakang (Bab 1)",
        "name_en": "Background (Chapter 1)",
        "category": "Bab 1",
        "tool": "Grok",
        "fields": [
            {"key": "topik", "label": "Topik penelitian", "label_en": "Research topic"},
            {"key": "catatan", "label": "Catatan / poin dari pembimbing", "label_en": "Notes from supervisor"},
            {"key": "paragraf", "label": "Jumlah paragraf", "label_en": "Number of paragraphs"},
        ],
        "template": (
            "Saya sedang menulis bagian latar belakang untuk skripsi bertopik {topik}. "
            "Berikut poin-poin dari saya dan dosen pembimbing: {catatan}. Tolong rangkai "
            "poin-poin itu menjadi latar belakang yang runtut dengan struktur piramida "
            "terbalik, dari isu umum ke konteks lokal, lalu ke masalah spesifik penelitian "
            "saya. Sertakan data atau referensi pendukung bila ada, gunakan bahasa akademik "
            "standar skripsi, dan buat dalam {paragraf} paragraf yang mengalir dan siap "
            "dipakai di dokumen skripsi."
        ),
        "template_en": (
            "I am writing the background section for a thesis on {topik}. Here are the "
            "points from me and my supervisor: {catatan}. Please weave these points into "
            "a coherent background with an inverted-pyramid structure, from the general "
            "issue to the local context, then to the specific problem of my research. "
            "Include supporting data or references where available, use standard academic "
            "thesis language, and make it {paragraf} paragraphs that flow and are ready "
            "to use in the thesis document."
        ),
    },
    {
        "id": "rumusan-masalah",
        "name": "Rumusan Masalah & Tujuan (Bab 1)",
        "name_en": "Problem Statement & Objectives (Chapter 1)",
        "category": "Bab 1",
        "tool": "ChatGPT",
        "fields": [
            {"key": "topik", "label": "Topik penelitian", "label_en": "Research topic"},
            {"key": "masalah", "label": "Masalah yang dihadapi", "label_en": "Problem faced"},
            {"key": "tujuan", "label": "Tujuan penelitian", "label_en": "Research objective"},
        ],
        "template": (
            "Saya sedang menulis Bab 1 skripsi bertopik {topik}. Masalah yang saya "
            "hadapi: {masalah}. Tujuan penelitian saya: {tujuan}. Tolong bantu saya "
            "merumuskan masalah penelitian dalam bentuk pertanyaan penelitian yang jelas "
            "dan terukur, lalu turunkan tujuan penelitian yang sesuai dengan pertanyaan "
            "itu. Beri 2-3 rumusan masalah beserta tujuan masing-masing, dan jelaskan "
            "singkat kenapa rumusan itu layak diteliti."
        ),
        "template_en": (
            "I am writing Chapter 1 of my thesis on {topik}. The problem I am facing: "
            "{masalah}. My research objective: {tujuan}. Please help me turn this into "
            "clear, measurable research questions, then derive matching research objectives "
            "for each question. Give 2-3 problem statements with their objectives, and "
            "briefly explain why each is worth researching."
        ),
    },
    {
        "id": "banding-teori",
        "name": "Membandingkan 3 Teori (Bab 2)",
        "name_en": "Comparing 3 Theories (Chapter 2)",
        "category": "Bab 2",
        "tool": "Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
        ],
        "template": (
            "Saya sedang menulis skripsi tentang {judul}. Tolong carikan tiga teori yang "
            "relevan dengan topik ini, lalu bandingkan ketiganya dalam tabel: nama teori, "
            "tokoh atau penelitinya, konsep utama, kelebihan dan keterbatasan, serta "
            "relevansinya dengan penelitian saya. Di akhir, beri rekomendasi teori mana "
            "yang paling cocok dijadikan landasan teori penelitian saya."
        ),
        "template_en": (
            "I am writing a thesis about {judul}. Please find three theories relevant to "
            "this topic, then compare them in a table: theory name, its figure or "
            "researcher, main concepts, strengths and limitations, and relevance to my "
            "research. At the end, recommend which theory fits best as the theoretical "
            "foundation of my research."
        ),
    },
    {
        "id": "review-terdahulu",
        "name": "Review Penelitian Terdahulu (Bab 2)",
        "name_en": "Review of Prior Research (Chapter 2)",
        "category": "Bab 2",
        "tool": "Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "daftar", "label": "Daftar penelitian terdahulu", "label_en": "List of prior studies"},
            {"key": "gaya", "label": "Gaya sitasi (mis. APA 7th)", "label_en": "Citation style (e.g. APA 7th)"},
        ],
        "template": (
            "Saya sedang meneliti {judul}. Berikut daftar penelitian terdahulu yang saya "
            "jadikan rujukan: {daftar}. Tolong buat ulasan kritis terhadap penelitian-"
            "penelitian itu, dengan fokus pada metode, sampel, hasil, dan keterbatasannya. "
            "Jelaskan celah penelitian (research gap) yang belum banyak diteliti dan "
            "bagaimana penelitian saya bisa mengisinya. Tulis dalam bahasa akademik, "
            "sekitar 3-4 paragraf, dengan sitasi gaya {gaya}."
        ),
        "template_en": (
            "I am researching {judul}. Here is the list of prior studies I am using as "
            "references: {daftar}. Please write a critical review of these studies, "
            "focusing on method, sample, findings, and limitations. Explain the research "
            "gap that has not been widely studied and how my research can fill it. Write "
            "in academic language, about 3-4 paragraphs, with citations in {gaya} style."
        ),
    },
    {
        "id": "metodologi",
        "name": "Metodologi Penelitian (Bab 3)",
        "name_en": "Research Methodology (Chapter 3)",
        "category": "Bab 3",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "jenis", "label": "Jenis penelitian", "label_en": "Research type"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "populasi", "label": "Populasi dan sampel", "label_en": "Population and sample"},
            {"key": "pengumpulan", "label": "Teknik pengumpulan data", "label_en": "Data collection technique"},
            {"key": "analisis", "label": "Teknik analisis data", "label_en": "Data analysis technique"},
        ],
        "template": (
            "Saya sedang menulis Bab 3 Metodologi Penelitian untuk skripsi berjudul {judul}. "
            "Jenis penelitian saya: {jenis}. Metode yang digunakan: {metode}. Populasi dan "
            "sampel: {populasi}. Teknik pengumpulan data: {pengumpulan}. Teknik analisis "
            "data: {analisis}. Susunlah Bab 3 yang lengkap dan logis, mencakup desain "
            "penelitian, definisi operasional variabel, populasi dan sampel, instrumen "
            "penelitian, teknik pengumpulan data, dan teknik analisis data. Pastikan isinya "
            "selaras dengan judul serta Bab 1 dan 2, dan jelaskan alasan metode ini paling "
            "tepat untuk penelitian saya, dengan bahasa akademik yang rapi."
        ),
        "template_en": (
            "I am writing Chapter 3, Research Methodology, for a thesis titled {judul}. "
            "My research type: {jenis}. Method used: {metode}. Population and sample: "
            "{populasi}. Data collection technique: {pengumpulan}. Data analysis technique: "
            "{analisis}. Draft a complete and logical Chapter 3, covering research design, "
            "operational definitions of variables, population and sample, research "
            "instruments, data collection techniques, and data analysis techniques. Make "
            "sure the content aligns with the title and Chapters 1 and 2, and explain why "
            "this method is the best fit for my research, in neat academic language."
        ),
    },
    {
        "id": "hubungan-variabel",
        "name": "Hubungan Antar Variabel (Bab 3)",
        "name_en": "Relationships Between Variables (Chapter 3)",
        "category": "Bab 3",
        "tool": "ChatGPT / Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "variabel_x", "label": "Variabel X", "label_en": "Variable X"},
            {"key": "variabel_y", "label": "Variabel Y", "label_en": "Variable Y"},
            {"key": "variabel_z", "label": "Variabel Z (bila ada)", "label_en": "Variable Z (if any)"},
        ],
        "template": (
            "Saya sedang menulis Bab 3 skripsi berjudul {judul}. Variabel penelitian saya: "
            "variabel X = {variabel_x}, variabel Y = {variabel_y}, variabel Z = "
            "{variabel_z} (bila ada). Tolong buat paragraf yang menjelaskan hubungan antar "
            "variabel ini berdasarkan teori yang relevan. Uraikan secara runtut, mulai dari "
            "hubungan X ke Y, lalu Z bila ada. Jelaskan mengapa hubungan ini penting untuk "
            "diteliti, dan dukung dengan minimal 3 referensi dari penelitian terdahulu "
            "(format APA 7th)."
        ),
        "template_en": (
            "I am writing Chapter 3 of a thesis titled {judul}. My research variables: "
            "variable X = {variabel_x}, variable Y = {variabel_y}, variable Z = "
            "{variabel_z} (if any). Please write a paragraph explaining the relationships "
            "between these variables based on relevant theory. Lay it out in order, "
            "starting with the X-to-Y relationship, then Z if any. Explain why this "
            "relationship is important to study, and support it with at least 3 references "
            "from prior research (APA 7th format)."
        ),
    },
    {
        "id": "hipotesis",
        "name": "Perkiraan Hipotesis (Bab 3)",
        "name_en": "Hypothesis Drafting (Chapter 3)",
        "category": "Bab 3",
        "tool": "Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "variabel", "label": "Variabel yang diteliti", "label_en": "Variables studied"},
        ],
        "template": (
            "Saya sedang menyusun hipotesis untuk skripsi berjudul {judul}. Variabel yang "
            "saya teliti: {variabel}. Tolong carikan minimal 5 penelitian terdahulu yang "
            "meneliti hubungan serupa. Ringkas temuan utama masing-masing penelitian, lalu "
            "susun hipotesis yang logis dan bisa diuji. Format hasilnya: ringkasan penelitian "
            "terdahulu (penulis, tahun, temuan, relevansi), sintesis hubungan antar penelitian "
            "(pola, konsistensi, atau perdebatan yang ada), dan hipotesis saya (H0, H1, dst) "
            "dalam format yang jelas dan siap dimasukkan ke Bab 3."
        ),
        "template_en": (
            "I am drafting hypotheses for a thesis titled {judul}. The variables I am "
            "studying: {variabel}. Please find at least 5 prior studies that examined "
            "similar relationships. Summarize each study's main findings, then formulate "
            "logical, testable hypotheses. Format the result as: summary of prior research "
            "(author, year, findings, relevance), synthesis of the relationships between "
            "studies (patterns, consistencies, or debates), and my hypotheses (H0, H1, "
            "etc.) in a clear format ready for Chapter 3."
        ),
    },
    {
        "id": "mixed-methods",
        "name": "Analisis Mixed-Methods (Bab 4)",
        "name_en": "Mixed-Methods Analysis (Chapter 4)",
        "category": "Bab 4",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "kuantitatif", "label": "Metode kuantitatif", "label_en": "Quantitative method"},
            {"key": "kualitatif", "label": "Metode kualitatif", "label_en": "Qualitative method"},
        ],
        "template": (
            "Saya sedang menganalisis data penelitian mixed method untuk skripsi berjudul "
            "{judul}. Metode kuantitatif saya: {kuantitatif}. Metode kualitatif saya: "
            "{kualitatif}. Saya akan melampirkan file data mentah saya. Tolong analisis "
            "dengan langkah: (1) Analisis kuantitatif: bersihkan data dan jelaskan penanganan "
            "missing value, lakukan uji statistik yang sesuai, sajikan hasil dalam tabel "
            "beserta interpretasi (p-value, signifikansi, effect size), dan buat visualisasi "
            "sederhana bila relevan. (2) Analisis kualitatif: lakukan coding tematik, sajikan "
            "tema utama beserta kutipan perwakilan responden, dan interpretasikan maknanya. "
            "(3) Integrasi: gabungkan kedua hasil, tunjukkan apakah keduanya saling "
            "mendukung, melengkapi, atau bertentangan, dan buat kesimpulan sementara yang "
            "menjawab rumusan masalah. Gunakan bahasa akademik yang jelas dan sistematis, "
            "dengan format akhir yang siap dimasukkan ke Bab 4."
        ),
        "template_en": (
            "I am analyzing mixed-method research data for a thesis titled {judul}. My "
            "quantitative method: {kuantitatif}. My qualitative method: {kualitatif}. I "
            "will attach my raw data files. Please analyze with these steps: (1) "
            "Quantitative analysis: clean the data and explain how missing values are "
            "handled, run the appropriate statistical tests, present the results in tables "
            "with interpretation (p-value, significance, effect size), and make simple "
            "visualizations where relevant. (2) Qualitative analysis: do thematic coding, "
            "present the main themes with representative respondent quotes, and interpret "
            "their meaning. (3) Integration: combine both results, show whether they "
            "support, complement, or contradict each other, and draw a preliminary "
            "conclusion that answers the problem statement. Use clear, systematic academic "
            "language, with a final format ready for Chapter 4."
        ),
    },
    {
        "id": "saran",
        "name": "Saran Penelitian (Bab 5)",
        "name_en": "Research Suggestions (Chapter 5)",
        "category": "Bab 5",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "hasil", "label": "Ringkasan hasil penelitian", "label_en": "Summary of findings"},
        ],
        "template": (
            "Saya sedang menyusun Bab 5 skripsi berjudul {judul}. Berdasarkan hasil "
            "penelitian saya berikut: {hasil}, tolong buatkan saran penelitian yang "
            "konstruktif untuk tiga pihak: (1) praktisi atau industri, (2) akademisi, dan "
            "(3) peneliti berikutnya. Tulis dengan bahasa akademik, masing-masing satu "
            "paragraf, dan pastikan setiap saran bisa diterapkan dan relevan dengan temuan "
            "penelitian saya."
        ),
        "template_en": (
            "I am drafting Chapter 5 of a thesis titled {judul}. Based on my findings "
            "below: {hasil}, please write constructive research suggestions for three "
            "audiences: (1) practitioners or industry, (2) academics, and (3) future "
            "researchers. Write in academic language, one paragraph each, and make sure "
            "every suggestion is actionable and relevant to my findings."
        ),
    },
    {
        "id": "keterbatasan",
        "name": "Keterbatasan + Peluang Penelitian (Bab 5)",
        "name_en": "Limitations + Future Research (Chapter 5)",
        "category": "Bab 5",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "data", "label": "Ringkasan data", "label_en": "Data summary"},
        ],
        "template": (
            "Saya sedang menulis Bab 5 skripsi berjudul {judul}. Metode penelitian saya: "
            "{metode}, dengan data: {data}. Tolong buatkan bagian keterbatasan penelitian "
            "yang ditulis secara elegan dan profesional, tanpa melemahkan hasil penelitian, "
            "lalu lanjutkan dengan peluang penelitian lanjutan. Berikan 3-5 ide penelitian "
            "berikutnya yang relevan, misalnya metode baru, populasi berbeda, atau variabel "
            "tambahan, dan jelaskan mengapa setiap ide penting untuk dikaji."
        ),
        "template_en": (
            "I am writing Chapter 5 of a thesis titled {judul}. My research method: "
            "{metode}, with data: {data}. Please write a limitations section that is "
            "elegant and professional, without weakening the findings, then continue with "
            "opportunities for future research. Give 3-5 ideas for follow-up studies, such "
            "as a new method, a different population, or additional variables, and explain "
            "why each idea matters to study."
        ),
    },
    {
        "id": "review-draf",
        "name": "Review Draf Skripsi (Persiapan Sidang)",
        "name_en": "Thesis Draft Review (Defense Prep)",
        "category": "Sidang",
        "tool": "Claude / Manus",
        "fields": [],
        "template": (
            "Saya akan melampirkan file skripsi saya (PDF/DOC). Tolong baca dan analisis "
            "seluruh isinya, dan berperan sebagai dosen pembimbing sekaligus dosen penguji "
            "yang objektif dan kritis. Beri masukan tentang bagian yang masih lemah, "
            "berpotensi jadi revisi, atau bisa memicu pertanyaan saat seminar dan sidang. "
            "Jelaskan secara spesifik letak masalahnya (bab atau subbab), alasan bagian itu "
            "dinilai kurang kuat, dan aspek apa yang sebaiknya diperdalam, tanpa langsung "
            "menuliskan revisinya. Sebutkan juga kekuatan skripsi saya, dari argumentasi, "
            "teori, metodologi, analisis, sampai kebaruan penelitian. Terakhir, evaluasi "
            "aspek teknis penulisan: sistematika, alur antarparagraf, konsistensi istilah, "
            "kualitas sitasi dan daftar pustaka, format tabel atau gambar, serta potensi "
            "kesalahan akademik lainnya. Sajikan evaluasi dalam kategori yang jelas, "
            "diurutkan berdasarkan prioritas (tinggi, sedang, rendah), agar saya tahu "
            "bagian mana yang harus diperbaiki dulu."
        ),
        "template_en": (
            "I will attach my thesis file (PDF/DOC). Please read and analyze all of it, "
            "and act as an objective, critical supervisor and examiner. Give feedback on "
            "the parts that are still weak, could trigger revisions, or could prompt "
            "questions during the seminar and defense. Explain specifically where the "
            "problem is (chapter or subchapter), why that part is considered weak, and what "
            "should be deepened, without writing the revision itself. Also mention my "
            "thesis's strengths, from argumentation, theory, methodology, analysis, to "
            "research novelty. Finally, evaluate the technical writing: structure, flow "
            "between paragraphs, term consistency, citation and bibliography quality, table "
            "or figure formatting, and other potential academic errors. Present the "
            "evaluation in clear categories, ordered by priority (high, medium, low), so "
            "I know which part to fix first."
        ),
    },
    {
        "id": "ppt",
        "name": "Skripsi Menjadi PowerPoint",
        "name_en": "Thesis to PowerPoint",
        "category": "Sidang",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "jumlah_slide", "label": "Jumlah slide", "label_en": "Number of slides"},
        ],
        "template": (
            "Saya ingin mengubah skripsi saya berjudul {judul} menjadi slide presentasi "
            "PowerPoint. Saya akan melampirkan file skripsinya. Tolong rangkum setiap bab "
            "menjadi slide dengan judul yang singkat dan menarik. Isi tiap slide berupa "
            "poin-poin penting (maksimal 5 poin per slide), ditambah 1-2 kalimat penjelas "
            "untuk setiap slide agar saya tahu apa yang harus diucapkan. Ikuti struktur "
            "presentasi skripsi: latar belakang, rumusan masalah, tujuan, tinjauan pustaka, "
            "metode, hasil, pembahasan, kesimpulan, dan saran. Bila perlu, rekomendasikan "
            "grafik, tabel, atau diagram untuk memperjelas. Hasil akhirnya adalah presentasi "
            "sebanyak {jumlah_slide} slide yang siap dipakai tanpa banyak edit."
        ),
        "template_en": (
            "I want to turn my thesis titled {judul} into a PowerPoint presentation. I "
            "will attach the thesis file. Please summarize each chapter into slides with "
            "short, engaging titles. Each slide's content should be key points (at most 5 "
            "points per slide), plus 1-2 explanatory sentences per slide so I know what to "
            "say. Follow the thesis presentation structure: background, problem statement, "
            "objectives, literature review, method, results, discussion, conclusions, and "
            "suggestions. Where needed, recommend charts, tables, or diagrams for clarity. "
            "The final result is a presentation of {jumlah_slide} slides ready to use with "
            "little editing."
        ),
    },
    {
        "id": "cue-card",
        "name": "Cue Card Presentasi",
        "name_en": "Presentation Cue Cards",
        "category": "Sidang",
        "tool": "ChatGPT",
        "fields": [],
        "template": (
            "Tolong buatkan cue card singkat dan padat untuk membantu saya saat presentasi "
            "skripsi. Bagi per slide sesuai urutan PPT skripsi saya. Tulis poin-poin atau "
            "kalimat kunci yang harus saya ucapkan, dengan bahasa lisan yang natural tapi "
            "tetap profesional. Jangan terlalu panjang, cukup 2-3 kalimat per slide supaya "
            "mudah dihafalkan. Tambahkan tips intonasi atau gestur (misalnya: senyum di awal, "
            "lihat audiens saat menyebut hasil utama). Pastikan cue card ini membuat saya "
            "percaya diri, tidak terdengar kaku, dan membantu menjawab kemungkinan pertanyaan "
            "dari penguji."
        ),
        "template_en": (
            "Please make short, compact cue cards to help me during my thesis "
            "presentation. Split them per slide following my thesis PPT order. Write the "
            "key points or sentences I must say, in natural spoken language that stays "
            "professional. Keep it short, just 2-3 sentences per slide so it is easy to "
            "memorize. Add tips on intonation or gestures (for example: smile at the start, "
            "look at the audience when stating the main result). Make sure these cue cards "
            "make me confident, not stiff, and help me answer possible questions from the "
            "examiners."
        ),
    },
    {
        "id": "blog",
        "name": "Skripsi Menjadi Artikel Blog",
        "name_en": "Thesis to Blog Article",
        "category": "Publikasi",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "platform", "label": "Platform / blog / media", "label_en": "Platform / blog / media"},
            {"key": "kata", "label": "Panjang artikel (kata)", "label_en": "Article length (words)"},
        ],
        "template": (
            "Saya ingin mengubah skripsi saya berjudul {judul} menjadi artikel pendek yang "
            "siap dipublikasikan di {platform}. Saya akan melampirkan file skripsinya. "
            "Tolong ambil intisarinya lalu tulis ulang dengan bahasa yang santai, mudah "
            "dipahami pembaca awam, dan tetap menarik. Panjang artikel sekitar {kata} kata. "
            "Susun dengan struktur yang runtut: mulai dari pembuka yang menarik perhatian "
            "(fakta menarik, pertanyaan, atau fenomena terkini), lalu paparkan masalah yang "
            "saya teliti dan relevansinya, jelaskan metode dan temuan utama secara singkat "
            "tanpa terlalu banyak jargon, dan tutup dengan manfaat praktis penelitian ini "
            "bagi pembaca. Bila perlu, tambahkan statistik, contoh kasus, atau call-to-action, "
            "dan pastikan artikel mencantumkan kredit ke penelitian saya agar bisa dipakai "
            "sebagai portofolio."
        ),
        "template_en": (
            "I want to turn my thesis titled {judul} into a short article ready to publish "
            "on {platform}. I will attach the thesis file. Please take its essence and "
            "rewrite it in relaxed language that is easy for lay readers to understand, and "
            "still engaging. The article should be about {kata} words long. Structure it in "
            "order: start with an attention-grabbing opening (an interesting fact, a "
            "question, or a current phenomenon), then present the problem I studied and its "
            "relevance, briefly explain the method and main findings without too much "
            "jargon, and close with the practical benefit of this research for readers. "
            "Where needed, add statistics, case examples, or a call-to-action, and make "
            "sure the article credits my research so it can serve as a portfolio."
        ),
    },
    {
        "id": "jurnal",
        "name": "Skripsi Menjadi Artikel Jurnal",
        "name_en": "Thesis to Journal Article",
        "category": "Publikasi",
        "tool": "ChatGPT",
        "fields": [
            {"key": "bagian", "label": "Bagian skripsi (mis. Pendahuluan/Bab 1)", "label_en": "Thesis section (e.g. Introduction/Chapter 1)"},
            {"key": "jumlah", "label": "Jumlah paragraf/kata", "label_en": "Number of paragraphs/words"},
        ],
        "template": (
            "Saya ingin memublikasikan jurnal berdasarkan skripsi saya. Ini bagian yang "
            "perlu dirangkum menjadi paragraf yang lebih singkat untuk jurnal saya: {bagian}. "
            "Buatkan maksimal sebanyak {jumlah} paragraf atau kata. Pertahankan sitasinya "
            "dan jangan membuang inti tiap paragraf. Gunakan bahasa yang humanis dan tidak "
            "terkesan robotik. Hindari kata yang berulang dan struktur kalimat yang generik, "
            "variasikan panjang kalimat, dan hindari em-dash dan titik koma. Berikut paragraf "
            "yang perlu dipersingkat: [tempel paragraf kamu di sini, satu bagian saja]."
        ),
        "template_en": (
            "I want to publish a journal article based on my thesis. This is the section "
            "that needs to be condensed into shorter paragraphs for my journal: {bagian}. "
            "Make at most {jumlah} paragraphs or words. Keep the citations and do not drop "
            "the core of each paragraph. Use human, non-robotic language. Avoid repeated "
            "words and generic sentence structures, vary sentence length, and avoid "
            "em-dashes and semicolons. Here is the paragraph to shorten: [paste your "
            "paragraph here, one section only]."
        ),
    },
]


def list_prompts(category: str | None = None):
    """All thesis prompts, optionally filtered by category."""
    if category is None:
        return list(PROMPTS)
    return [p for p in PROMPTS if p["category"].lower() == category.lower()]


def get_prompt(prompt_id: str):
    """One prompt by id, or None when unknown."""
    for p in PROMPTS:
        if p["id"] == prompt_id:
            return p
    return None


def fill_prompt(prompt_id: str, values: dict, lang: str = "id") -> str:
    """Fill a prompt template with the student's own values.

    `lang` picks the template language ("id" or "en"); English falls
    back to the Indonesian template when a prompt has no English one.
    Raises KeyError for an unknown prompt id, ValueError naming any
    placeholder left empty. Never invents values: a missing field is
    an error, not a guess.
    """
    prompt = get_prompt(prompt_id)
    if prompt is None:
        raise KeyError(f"unknown prompt: {prompt_id}")
    missing = [f["key"] for f in prompt["fields"]
               if f["key"] not in values or values[f["key"]] == ""]
    if missing:
        raise ValueError(f"missing values for: {', '.join(missing)}")
    template = prompt["template"]
    if lang == "en" and prompt.get("template_en"):
        template = prompt["template_en"]
    return template.format(**values)


def prompts_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Thesis prompts: ready-made prompts for each thesis chapter.")
    p.add_argument("prompt_id", nargs="?", help="prompt id (see --list)")
    p.add_argument("--list", action="store_true", help="list all prompts and exit")
    p.add_argument("--category", help="only list prompts from this category, e.g. 'Bab 3'")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="template language (default: id)")
    p.add_argument("--set", dest="set_values", action="append", default=[],
                   help="fill a placeholder: --set judul='...' (repeatable)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.list or not args.prompt_id:
        for pr in list_prompts(category=args.category):
            name = pr["name_en"] if args.lang == "en" else pr["name"]
            print(f"{pr['id']} — {name} ({pr['category']}, {pr['tool']})")
        return 0

    prompt = get_prompt(args.prompt_id)
    if prompt is None:
        p.error(f"unknown prompt: {args.prompt_id} (see --list)")
        return 2

    if not args.set_values:
        template = prompt["template"]
        if args.lang == "en" and prompt.get("template_en"):
            template = prompt["template_en"]
        print(template)
        return 0

    values = {}
    for item in args.set_values:
        if "=" not in item:
            p.error(f"--set needs key=value, got: {item}")
            return 2
        key, value = item.split("=", 1)
        values[key.strip()] = value
    try:
        sys.stdout.write(fill_prompt(args.prompt_id, values, lang=args.lang) + "\n")
    except ValueError as e:
        p.error(str(e))
        return 2
    return 0


# ======================================================================
# Interactive menu CLI
# ======================================================================
DEFAULT_REFS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "demos", "citation-weaver", "references.json",
)

STRINGS = {
    "id": {
        "banner": "Academic Tools",
        "motto": "Satu file. Semua alat. Tanpa referensi palsu.",
        "tagline": "Jargon Buster  ·  Citation Weaver  ·  Prompt Skripsi",
        "banner_hint": "id  ·  ketik angka, Enter untuk memilih",
        "menu_title": "Daftar isi:",
        "jargon": "Jargon Buster — terjemahkan istilah akademik",
        "cite": "Citation Weaver — sisipkan sitasi ke naskah",
        "prompts": "Prompt Skripsi — template prompt untuk tiap bab",
        "analyze": "Analisis Kualitas — cek jargon, sitasi, dan DOI sekaligus",
        "humanize": "Humanize — saran rewrite gaya (sebelum/sesudah)",
        "library": "Pustaka — riwayat & bibliografi",
        "save_analysis": "Simpan hasil ini ke pustaka? (y = ya, kosong = tidak)",
        "saved_analysis": "Tersimpan di pustaka",
        "history": "Lihat riwayat analisis",
        "detail": "Lihat satu analisis",
        "search_refs": "Cari referensi",
        "import_refs": "Impor bibliografi dari JSON",
        "export_refs": "Ekspor bibliografi ke JSON",
        "duplicates": "Cek duplikasi",
        "analysis_id": "Nomor analisis (#)",
        "analysis_missing": "Tidak ada analisis",
        "search_query": "Kata kunci (judul/penulis/DOI)",
        "imported": "Diimpor",
        "added_count": "ditambahkan",
        "updated_count": "diperbarui",
        "exported": "Diekspor",
        "list_prompts": "Lihat daftar prompt",
        "fill_prompt": "Isi prompt",
        "pick_prompt": "Pilih prompt:",
        "lang": "Ganti bahasa (id/en)",
        "exit": "Keluar",
        "back": "Kembali",
        "choice": "Pilihanmu",
        "invalid": "Pilihan tidak dikenal, coba lagi.",
        "goodbye": "Sampai jumpa!",
        "type_text": "Ketik teks (baris kosong = selesai):",
        "read_file": "Baca dari file",
        "file_path": "Path file",
        "file_missing": "File tidak ditemukan:",
        "field": "Bidang (kosong = semua bidang)",
        "format": "Format output: 1 = Markdown, 2 = CSV",
        "list_terms": "Lihat kamus",
        "add_terms": "Tambah istilah dari file JSON",
        "json_path": "Path file JSON",
        "added": "Istilah ditambahkan:",
        "refs": "File bibliografi JSON (kosong = contoh bawaan)",
        "refs_missing": "File bibliografi tidak ditemukan:",
        "pick_style": "Pilih gaya sitasi:",
        "pick_major": "Pilih jurusan (rekomendasi gaya otomatis):",
        "by_major": "Pilih dari jurusan",
        "out_lang": "Bahasa output: 1 = Indonesia, 2 = English",
        "list_styles": "Lihat gaya sitasi",
        "list_majors": "Lihat jurusan",
        "lookup": "Cari referensi online (DOI/judul)",
        "lookup_query": "DOI atau judul",
        "lookup_key": "Kunci bibliografi (kosong = otomatis)",
        "lookup_save": "Simpan ke file (kosong = jangan simpan)",
        "lookup_saved": "Tersimpan sebagai",
        "lookup_failed": "Pencarian gagal:",
        "bibtex": "Export bibliografi ke BibTeX (.bib)",
        "bibtex_out": "Simpan ke file .bib (kosong = tampilkan saja)",
        "bibtex_saved": "BibTeX tersimpan:",
        "audit": "Audit sitasi (cek rujukan hilang/tak terpakai)",
        "audit_check_links": "Cek juga DOI/link masih hidup? (y = ya, kosong = tidak)",
        "verify": "Verifikasi DOI referensi (Crossref/OpenAlex)",
        "save_fixed": "Simpan hasil perbaikan ke file (kosong = tidak)",
        "saved_fixed": "Tersimpan",
        "applied": "diterapkan",
        "skipped": "dilewati",
        "press_enter": "Tekan Enter untuk kembali...",
        "result": "Hasil:",
    },
    "en": {
        "banner": "Academic Tools",
        "motto": "One file. Every tool. No invented references.",
        "tagline": "Jargon Buster  ·  Citation Weaver  ·  Thesis Prompts",
        "banner_hint": "en  ·  type a number, Enter to choose",
        "menu_title": "Contents:",
        "jargon": "Jargon Buster — translate academic jargon",
        "cite": "Citation Weaver — weave citations into text",
        "prompts": "Thesis Prompts — ready-made prompts for each chapter",
        "analyze": "Quality Check — jargon, citations, and DOIs in one pass",
        "humanize": "Humanize — style rewrite suggestions (before/after)",
        "library": "Library — history & bibliography",
        "save_analysis": "Save this run to the library? (y = yes, empty = no)",
        "saved_analysis": "Saved to the library",
        "history": "List past analyses",
        "detail": "Show one analysis",
        "search_refs": "Search references",
        "import_refs": "Import a bibliography JSON",
        "export_refs": "Export the bibliography to JSON",
        "duplicates": "Check duplication",
        "analysis_id": "Analysis number (#)",
        "analysis_missing": "No such analysis",
        "search_query": "Keyword (title/author/DOI)",
        "imported": "Imported",
        "added_count": "added",
        "updated_count": "updated",
        "exported": "Exported",
        "list_prompts": "List prompts",
        "fill_prompt": "Fill a prompt",
        "pick_prompt": "Pick a prompt:",
        "lang": "Switch language (id/en)",
        "exit": "Exit",
        "back": "Back",
        "choice": "Your choice",
        "invalid": "Unknown choice, try again.",
        "goodbye": "Goodbye!",
        "type_text": "Type text (empty line = done):",
        "read_file": "Read from file",
        "file_path": "File path",
        "file_missing": "File not found:",
        "field": "Field (empty = all fields)",
        "format": "Output format: 1 = Markdown, 2 = CSV",
        "list_terms": "List dictionary terms",
        "add_terms": "Add terms from a JSON file",
        "json_path": "JSON file path",
        "added": "Terms added:",
        "refs": "Bibliography JSON file (empty = bundled sample)",
        "refs_missing": "Bibliography file not found:",
        "pick_style": "Pick a citation style:",
        "pick_major": "Pick a major (recommended style is automatic):",
        "by_major": "Pick from major",
        "out_lang": "Output language: 1 = Indonesian, 2 = English",
        "list_styles": "List citation styles",
        "list_majors": "List majors",
        "lookup": "Look up a reference online (DOI/title)",
        "lookup_query": "DOI or title",
        "lookup_key": "Bibliography key (empty = automatic)",
        "lookup_save": "Save to file (empty = don't save)",
        "lookup_saved": "Saved as",
        "lookup_failed": "Lookup failed:",
        "bibtex": "Export bibliography to BibTeX (.bib)",
        "bibtex_out": "Save to .bib file (empty = print only)",
        "bibtex_saved": "BibTeX saved:",
        "audit": "Audit citations (check missing/unused references)",
        "audit_check_links": "Also check DOI/links are still alive? (y = yes, empty = no)",
        "verify": "Verify reference DOIs (Crossref/OpenAlex)",
        "save_fixed": "Save the fixed text to a file (empty = skip)",
        "saved_fixed": "Saved",
        "applied": "applied",
        "skipped": "skipped",
        "press_enter": "Press Enter to go back...",
        "result": "Result:",
    },
}


BANNER_MIN_WIDTH = 60


def _unicode_ok() -> bool:
    """True when stdout can encode the box-drawing and block glyphs.

    UTF-8 and cp437/cp850 can; cp1252 cannot. A StringIO (tests,
    pipes) has no encoding, which means plain str: treat it as capable.
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "╭╮╰╯─│·█░".encode(enc)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _colors_enabled() -> bool:
    """Color only on a real terminal, unless forced off or on.

    NO_COLOR disables, ACADEMIC_COLOR=1 forces (used to preview the
    colored UI when stdout is piped), TERM=dumb disables.
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("ACADEMIC_COLOR") == "1":
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def _paint(text: str, code: str) -> str:
    if not _colors_enabled():
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def _bold(text: str) -> str:
    return _paint(text, "1")


def _green(text: str) -> str:
    return _paint(text, "32")


def _bar(value: float, maximum: float, width: int = 20) -> str:
    """A text bar: filled blocks for value/maximum, empty for the rest."""
    filled = max(0, min(width, round(value / maximum * width)))
    if _unicode_ok():
        return "█" * filled + "░" * (width - filled)
    return "#" * filled + "-" * (width - filled)


def _menu_line(number: str, name: str, desc: str = "",
               desc_col: int = 64) -> str:
    """One menu row with dot leaders: '  1  Jargon Buster ... desc'."""
    left = f"  {number}  {name} "
    if not desc:
        return left.rstrip()
    dots = max(2, desc_col - len(left) - len(desc))
    return left + "." * dots + " " + desc


def _section_header(name: str, width: int = 58) -> str:
    """A rule with the section name embedded: '── Jargon Buster ──...'."""
    if _unicode_ok():
        head = f"── {name} "
        return _bold(head + "─" * max(2, width - len(head)))
    head = f"-- {name.replace(' — ', ' - ')} "
    return head + "-" * max(2, width - len(head))


def format_banner(lang: str) -> str:
    """Cover-page banner for the interactive menu; width follows the text.

    A rounded box when stdout can encode it, plain ASCII otherwise
    (old Windows consoles). Colors only on a real terminal.
    """
    t = STRINGS[lang]
    title = t["banner"]
    version = f"v{__version__}"
    motto = t["motto"]
    tagline = t["tagline"]
    hint = t["banner_hint"]
    width = max(BANNER_MIN_WIDTH, len(title) + len(version) + 2,
                len(motto) + 2, len(tagline) + 2, len(hint) + 2)
    heading = title + " " * (width - len(title) - len(version)) + version
    if _unicode_ok():
        top = "╭" + "─" * (width + 2) + "╮"
        bot = "╰" + "─" * (width + 2) + "╯"
        rule = _green("─" * width)
        edge = "│"
    else:
        top = "+" + "=" * (width + 2) + "+"
        bot = top
        rule = "-" * width
        edge = "|"
    return "\n".join([
        f"  {top}",
        f"  {edge} {_bold(heading)} {edge}",
        f"  {edge} {rule} {edge}",
        f"  {edge} {motto.ljust(width)} {edge}",
        f"  {edge} {tagline.ljust(width)} {edge}",
        f"  {edge} {hint.ljust(width)} {edge}",
        f"  {bot}",
    ])


class CLI:
    """Interactive menu session. `lang` is the UI language (id/en)."""

    def __init__(self, lang: str = "id"):
        self.lang = lang if lang in STRINGS else "id"

    @property
    def t(self):
        return STRINGS[self.lang]

    def ask(self, prompt: str, default: str = "") -> str:
        """One line of input; returns default on empty line, '' on EOF."""
        try:
            answer = input(f"{prompt} " if not default else f"{prompt} [{default}] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return ""
        return answer.strip() or default

    def ask_choice(self, prompt: str, count: int) -> int | None:
        """Ask for a number 0..count.

        Returns None on empty line/EOF (means: back/exit), -1 on an
        invalid number (caller should re-prompt, not quit).
        """
        raw = self.ask(f"{prompt} (0-{count})")
        if not raw:
            return None
        try:
            n = int(raw)
        except ValueError:
            print(self.t["invalid"])
            return -1
        if 0 <= n <= count:
            return n
        print(self.t["invalid"])
        return -1

    def pause(self):
        try:
            input(f"\n{self.t['press_enter']}")
        except (EOFError, KeyboardInterrupt):
            print()

    def read_text(self) -> str | None:
        """Choice: type multi-line text, or read from a file."""
        print(f"  1. {self.t['type_text'].split(' (')[0]}")
        print(f"  2. {self.t['read_file']}")
        print(f"  0. {self.t['back']}")
        choice = self.ask_choice(self.t["choice"], 2)
        if choice == 1:
            print(self.t["type_text"])
            lines = []
            try:
                while True:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line)
            except (EOFError, KeyboardInterrupt):
                print()
            return "\n".join(lines)
        if choice == 2:
            path = self.ask(self.t["file_path"])
            if not path:
                return None
            if not os.path.isfile(path):
                print(f"{self.t['file_missing']} {path}")
                return None
            with open(path, encoding="utf-8") as f:
                return f.read()
        return None

    # -- main menu ------------------------------------------------------

    def run(self) -> int:
        while True:
            print()
            print(format_banner(self.lang))
            print(self.t["menu_title"])
            for number, key in (("1", "jargon"), ("2", "cite"),
                                ("3", "prompts"), ("4", "analyze"),
                                ("5", "humanize"), ("6", "library")):
                name, _, desc = self.t[key].partition(" — ")
                print(_menu_line(number, name, desc))
            print(_menu_line("7", self.t["lang"]))
            print(_menu_line("0", self.t["exit"]))
            choice = self.ask_choice(self.t["choice"], 7)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_menu()
            elif choice == 2:
                self.cite_menu()
            elif choice == 3:
                self.prompts_menu()
            elif choice == 4:
                self.analyze_menu()
            elif choice == 5:
                self.humanize_menu()
            elif choice == 6:
                self.library_menu()
            elif choice == 7:
                self.lang = "en" if self.lang == "id" else "id"
            elif choice == 0 or choice is None:
                print(self.t["goodbye"])
                return 0

    # -- Jargon Buster --------------------------------------------------

    def jargon_menu(self):
        while True:
            print(f"\n{_section_header(self.t['jargon'])}")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_terms']}")
            print(f"3. {self.t['add_terms']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 3)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_annotate()
            elif choice == 2:
                field = self.ask(self.t["field"])
                for item in list_terms(field or None):
                    print(f"- {item['term']} ({item['field']}): {item['translation']}")
                self.pause()
            elif choice == 3:
                path = self.ask(self.t["json_path"])
                if path and os.path.isfile(path):
                    added = update_dictionary(path)
                    print(f"{self.t['added']} {', '.join(added) if added else '-'}")
                elif path:
                    print(f"{self.t['file_missing']} {path}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def jargon_annotate(self):
        text = self.read_text()
        if not text:
            return
        field = self.ask(self.t["field"])
        print(f"1. Markdown\n2. CSV")
        fmt = self.ask_choice(self.t["format"], 2)
        if fmt == 2:
            out = to_csv(text, field or None)
        else:
            out = to_annotated_markdown(text, field or None)
        print(f"\n{self.t['result']}\n{out}")
        self.pause()

    # -- Citation Weaver ------------------------------------------------

    def cite_menu(self):
        while True:
            print(f"\n{_section_header(self.t['cite'])}")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_styles']}")
            print(f"3. {self.t['list_majors']}")
            print(f"4. {self.t['lookup']}")
            print(f"5. {self.t['bibtex']}")
            print(f"6. {self.t['audit']}")
            print(f"7. {self.t['verify']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 7)
            if choice == -1:
                continue
            if choice == 1:
                self.cite_weave()
            elif choice == 2:
                for i, s in enumerate(STYLES, 1):
                    print(f"  {i}. {s}")
                self.pause()
            elif choice == 3:
                for i, d in enumerate(DISCIPLINES, 1):
                    print(f"  {i}. {d['id']} / {d['en']} -> {d['style']}")
                self.pause()
            elif choice == 4:
                self.cite_lookup()
            elif choice == 5:
                self.cite_export_bibtex()
            elif choice == 6:
                self.cite_audit()
            elif choice == 7:
                self.cite_verify()
            elif choice == 0 or choice is None:
                return

    def cite_audit(self):
        text = self.read_text()
        if not text:
            return
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        refs = load_references(refs_path)
        result = audit_citations(text, refs)
        check = self.ask(self.t["audit_check_links"])
        links = None
        if check.strip().lower() in ("y", "ya", "yes", "1"):
            links = check_reference_links(refs, keys=result["cited"])
        print(f"\n{format_audit(result, lang=self.lang, links=links)}")
        self.pause()

    def cite_verify(self):
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        result = verify_reference_dois(load_references(refs_path))
        print(f"\n{format_verification(result, lang=self.lang)}")
        self.pause()

    def analyze_menu(self):
        text = self.read_text()
        if not text:
            return
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        refs = load_references(refs_path)
        result = analyze_text_quality(text, refs, lang=self.lang)
        print(f"\n{format_analyze(result, lang=self.lang)}")
        save = self.ask(self.t["save_analysis"])
        if save.strip().lower() in ("y", "ya", "yes"):
            analysis_id = save_analysis(text, result, refs)
            print(f"{self.t['saved_analysis']}: #{analysis_id}")
        self.pause()

    def library_menu(self):
        while True:
            print(f"\n{_section_header(self.t['library'])}")
            print(f"1. {self.t['history']}")
            print(f"2. {self.t['detail']}")
            print(f"3. {self.t['search_refs']}")
            print(f"4. {self.t['import_refs']}")
            print(f"5. {self.t['export_refs']}")
            print(f"6. {self.t['duplicates']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 6)
            if choice == -1:
                continue
            if choice == 1:
                print(f"\n{format_history(list_analyses())}")
                self.pause()
            elif choice == 2:
                raw = self.ask(self.t["analysis_id"])
                if raw.strip().isdigit():
                    analysis = get_analysis(int(raw))
                    if analysis is None:
                        print(f"{self.t['analysis_missing']} {raw}")
                    else:
                        print(f"\n{format_analysis_detail(analysis)}")
                self.pause()
            elif choice == 3:
                query = self.ask(self.t["search_query"])
                if query:
                    print(f"\n{format_references(search_references(query))}")
                self.pause()
            elif choice == 4:
                path = self.ask(self.t["json_path"])
                if path and os.path.isfile(path):
                    counts = import_references(load_references(path))
                    print(f"{self.t['imported']}: "
                          f"{counts['added']} {self.t['added_count']}, "
                          f"{counts['updated']} {self.t['updated_count']}")
                elif path:
                    print(f"{self.t['file_missing']} {path}")
                self.pause()
            elif choice == 5:
                path = self.ask(self.t["json_path"])
                if path:
                    refs = export_references()
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(refs, f, ensure_ascii=False, indent=2)
                    print(f"{self.t['exported']}: {len(refs)} -> {path}")
                self.pause()
            elif choice == 6:
                text = self.read_text()
                if text:
                    try:
                        result = find_duplicates(text)
                    except ValueError as e:
                        print(str(e))
                    else:
                        print(f"\n{format_duplicates(result, lang=self.lang)}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def humanize_menu(self):
        text = self.read_text()
        if not text:
            return
        result = suggest_style_fixes(text, lang=self.lang)
        print(f"\n{format_suggestions(result, lang=self.lang)}")
        mechanical = [s for s in result["suggestions"]
                      if s["replacement"] is not None]
        if mechanical:
            path = self.ask(self.t["save_fixed"])
            if path:
                full = suggest_style_fixes(text, lang=self.lang,
                                           limit=None)
                fixed = apply_suggestions(text, full)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(fixed["text"])
                print(f"{self.t['saved_fixed']}: {path} "
                      f"({len(fixed['applied'])} {self.t['applied']}, "
                      f"{len(fixed['skipped'])} {self.t['skipped']})")
        self.pause()

    def cite_export_bibtex(self):
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        out = self.ask(self.t["bibtex_out"])
        refs = load_references(refs_path)
        bib = export_bibtex(refs)
        if out:
            with open(out, "w", encoding="utf-8") as f:
                f.write(bib)
            print(f"{self.t['bibtex_saved']} {len(refs)} entries -> {out}")
        else:
            print(f"\n{bib}")
        self.pause()

    def cite_lookup(self):
        query = self.ask(self.t["lookup_query"])
        if not query:
            return
        try:
            ref = lookup_reference(query)
        except LookupError as e:
            print(f"{self.t['lookup_failed']} {e}")
            self.pause()
            return
        print(f"\n{json.dumps(ref, ensure_ascii=False, indent=2)}")
        path = self.ask(self.t["lookup_save"])
        if not path:
            self.pause()
            return
        key = self.ask(self.t["lookup_key"])
        saved = save_reference(ref, path, key=key or None)
        print(f"{self.t['lookup_saved']} [{saved}] ({path})")
        self.pause()

    def pick_style(self) -> str | None:
        print(f"\n{self.t['pick_style']}")
        for i, s in enumerate(STYLES, 1):
            print(f"  {i}. {s}")
        print(f"  {len(STYLES) + 1}. {self.t['by_major']}")
        choice = self.ask_choice(self.t["choice"], len(STYLES) + 1)
        if choice is None or choice == 0:
            return None
        if choice == len(STYLES) + 1:
            return self.pick_style_by_major()
        return STYLES[choice - 1]

    def pick_style_by_major(self) -> str | None:
        print(f"\n{self.t['pick_major']}")
        for i, d in enumerate(DISCIPLINES, 1):
            print(f"  {i}. {d['id']} / {d['en']} -> {d['style']}")
        choice = self.ask_choice(self.t["choice"], len(DISCIPLINES))
        if choice is None or choice == 0:
            return None
        return DISCIPLINES[choice - 1]["style"]

    def cite_weave(self):
        text = self.read_text()
        if not text:
            return
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        style = self.pick_style()
        if not style:
            return
        print("1. Indonesia\n2. English")
        lang_choice = self.ask_choice(self.t["out_lang"], 2)
        lang = "en" if lang_choice == 2 else "id"
        refs = load_references(refs_path)
        out = weave(text, refs, style=style, lang=lang)
        # weave() returns (full output with bibliography, woven text only)
        if isinstance(out, tuple):
            out = out[0]
        print(f"\n{self.t['result']}\n{out}")
        self.pause()

    # -- Thesis Prompts -------------------------------------------------

    def prompts_menu(self):
        while True:
            print(f"\n{_section_header(self.t['prompts'])}")
            print(f"1. {self.t['fill_prompt']}")
            print(f"2. {self.t['list_prompts']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 2)
            if choice == -1:
                continue
            if choice == 1:
                self.prompts_fill()
            elif choice == 2:
                for pr in list_prompts():
                    name = pr["name_en"] if self.lang == "en" else pr["name"]
                    print(f"  {pr['id']} — {name} ({pr['category']}, {pr['tool']})")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def prompts_fill(self):
        prompts = list_prompts()
        print(f"\n{self.t['pick_prompt']}")
        for i, pr in enumerate(prompts, 1):
            name = pr["name_en"] if self.lang == "en" else pr["name"]
            print(f"  {i}. {pr['id']} — {name} ({pr['tool']})")
        choice = self.ask_choice(self.t["choice"], len(prompts))
        if choice is None or choice == 0:
            return
        pr = prompts[choice - 1]
        values = {}
        for f in pr["fields"]:
            label = f["label"] if self.lang == "id" else f["label_en"]
            values[f["key"]] = self.ask(f"{label}:")
        try:
            out = fill_prompt(pr["id"], values, lang=self.lang)
        except ValueError as e:
            print(e)
            return
        print(f"\n{self.t['result']}\n{out}")
        print(f"\n({pr['tool']})")
        self.pause()


# ======================================================================
# Local web UI (serve) — the same four tools in a browser page
# ======================================================================
# Design direction (our own brief, written for this page):
# - A tool page, not a landing page: no hero, the work (paste text,
#   press Analyze) is at the top; every section earns its place.
# - Paper background, ink text, one restrained green accent. No
#   gradients, no decoration without a purpose.
# - System font stack, one type scale, real Indonesian copy, honest
#   labels (a score is a score, not a verdict).
# - Zero external resources: no CDN, no webfonts, no analytics —
#   the page works offline and sends nothing anywhere.
# - Keyboard-accessible tabs and buttons, visible focus outlines.
# The HTML is a raw string so the JavaScript stays verbatim.
WEB_UI_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Academic Tools — Analisis Kualitas</title>
<style>
  :root {
    --paper: #fafaf7;
    --card: #ffffff;
    --ink: #1d1d1a;
    --muted: #6b6b64;
    --line: #e2e2da;
    --accent: #206040;
    --accent-ink: #ffffff;
    --warn: #8a5a00;
    --bad: #9b2c2c;
    --radius: 6px;
    --space: 16px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 16px;
    line-height: 1.55;
  }
  header {
    border-bottom: 1px solid var(--line);
    background: var(--card);
  }
  .wrap { max-width: 860px; margin: 0 auto; padding: 0 var(--space); }
  header .wrap { padding-top: 20px; padding-bottom: 16px; }
  h1 { font-size: 22px; margin: 0; letter-spacing: -0.01em; }
  h1 .ver {
    font-size: 12px; font-weight: 600; color: var(--muted);
    border: 1px solid var(--line); border-radius: 999px;
    padding: 2px 8px; margin-left: 8px; vertical-align: middle;
  }
  header p { margin: 6px 0 0; color: var(--muted); font-size: 14px; }
  nav.tabs { display: flex; gap: 4px; margin-top: 16px; flex-wrap: wrap; }
  nav.tabs button {
    appearance: none; border: 1px solid transparent; background: none;
    font: inherit; font-size: 14px; font-weight: 600; color: var(--muted);
    padding: 8px 12px; border-radius: var(--radius) var(--radius) 0 0; cursor: pointer;
  }
  nav.tabs button[aria-selected="true"] {
    color: var(--ink); background: var(--paper);
    border-color: var(--line); border-bottom-color: var(--paper);
  }
  nav.tabs button:focus-visible, button:focus-visible, select:focus-visible,
  textarea:focus-visible, input:focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  main .wrap { padding-top: 24px; padding-bottom: 48px; }
  .panel { display: none; }
  .panel.active { display: block; }
  label { display: block; font-size: 14px; font-weight: 600; margin: 0 0 6px; }
  label .hint { font-weight: 400; color: var(--muted); }
  textarea, select, input[type="text"] {
    width: 100%; font: inherit; color: var(--ink);
    border: 1px solid var(--line); border-radius: var(--radius);
    background: var(--card); padding: 10px 12px;
  }
  textarea { min-height: 180px; resize: vertical; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
  .row > div { flex: 1 1 180px; }
  .actions { margin-top: 16px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  button.primary {
    appearance: none; border: 1px solid var(--accent); background: var(--accent);
    color: var(--accent-ink); font: inherit; font-weight: 600;
    padding: 10px 18px; border-radius: var(--radius); cursor: pointer;
  }
  button.primary:disabled { opacity: 0.55; cursor: wait; }
  button.ghost {
    appearance: none; border: 1px solid var(--line); background: var(--card);
    color: var(--ink); font: inherit; padding: 8px 14px;
    border-radius: var(--radius); cursor: pointer;
  }
  details { margin-top: 12px; font-size: 14px; }
  details summary { cursor: pointer; font-weight: 600; }
  details textarea { min-height: 110px; margin-top: 8px; }
  .status { font-size: 14px; color: var(--muted); }
  .error {
    margin-top: 16px; padding: 12px 14px; border: 1px solid var(--bad);
    border-radius: var(--radius); color: var(--bad); background: #fdf6f6;
    display: none; font-size: 14px;
  }
  .error.show { display: block; }
  .result { margin-top: 24px; }
  .card {
    background: var(--card); border: 1px solid var(--line);
    border-radius: var(--radius); padding: 16px; margin-top: 12px;
  }
  .card h2 { font-size: 15px; margin: 0 0 8px; }
  .card h2 .meta { font-weight: 400; color: var(--muted); font-size: 13px; }
  .card ul { margin: 0; padding-left: 20px; }
  .card li { margin: 4px 0; }
  .card li .src { color: var(--muted); font-size: 13px; }
  .score { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
  .score .num { font-size: 40px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
  .score .of { color: var(--muted); }
  .score .bar { flex: 1 1 160px; height: 10px; background: var(--line); border-radius: 999px; overflow: hidden; min-width: 120px; }
  .score .bar span { display: block; height: 100%; background: var(--accent); }
  .flag { color: var(--warn); font-weight: 600; }
  pre {
    white-space: pre-wrap; word-wrap: break-word; font: inherit;
    margin: 0; background: var(--card);
  }
  .bib { font-size: 14px; color: var(--ink); }
  footer { border-top: 1px solid var(--line); padding: 20px 0 32px; font-size: 13px; color: var(--muted); }
  @media (max-width: 560px) {
    .score .num { font-size: 32px; }
    nav.tabs button { padding: 8px 8px; }
  }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>Academic Tools <span class="ver">v__ACADEMIC_TOOLS_VERSION__</span></h1>
    <p>Satu file Python untuk tulisan mahasiswa: terjemahkan jargon, sisipkan sitasi, cek kualitas naskah, isi template prompt skripsi, dan lihat riwayat di pustaka.</p>
    <nav class="tabs" role="tablist" aria-label="Alat">
      <button role="tab" data-tab="analyze" aria-selected="true">Analisis Kualitas</button>
      <button role="tab" data-tab="jargon" aria-selected="false">Jargon Buster</button>
      <button role="tab" data-tab="cite" aria-selected="false">Citation Weaver</button>
      <button role="tab" data-tab="prompts" aria-selected="false">Prompt Skripsi</button>
      <button role="tab" data-tab="library" aria-selected="false">Pustaka</button>
    </nav>
  </div>
</header>
<main>
  <div class="wrap">

    <section class="panel active" id="panel-analyze" role="tabpanel" aria-label="Analisis Kualitas">
      <label for="analyze-text">Tempel naskah <span class="hint">— satu atau beberapa paragraf, bahasa Indonesia</span></label>
      <textarea id="analyze-text" placeholder="Tempel naskah di sini, misalnya satu paragraf Bab 1 atau abstrak."></textarea>
      <div class="row">
        <div>
          <label for="analyze-refs">Bibliografi</label>
          <select id="analyze-refs">
            <option value="sample">Contoh bawaan (7 referensi)</option>
            <option value="none">Tanpa bibliografi</option>
          </select>
        </div>
        <div>
          <label for="analyze-lang">Bahasa hasil</label>
          <select id="analyze-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
        <div>
          <label>&nbsp;</label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-verify"> Verifikasi DOI <span class="hint">(butuh internet)</span></label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-suggest"> Saran rewrite gaya</label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-duplicates"> Cek duplikasi dengan pustaka <span class="hint">(kalimat yang berulang)</span></label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-save"> Simpan ke pustaka <span class="hint">(riwayat di komputer ini)</span></label>
        </div>
      </div>
      <details>
        <summary>Atau tempel bibliografi JSON sendiri</summary>
        <textarea id="analyze-refs-json" placeholder='{"devlin2019": {"title": "BERT: ...", "year": 2019}}'></textarea>
      </details>
      <div class="actions">
        <button class="primary" id="analyze-btn">Analisis naskah</button>
        <span class="status" id="analyze-status"></span>
      </div>
      <div class="error" id="analyze-error"></div>
      <div class="result" id="analyze-result"></div>
    </section>

    <section class="panel" id="panel-jargon" role="tabpanel" aria-label="Jargon Buster">
      <label for="jargon-text">Tempel teks <span class="hint">— istilah akademik yang dikenali akan dijelaskan</span></label>
      <textarea id="jargon-text" placeholder="Tempel teks di sini."></textarea>
      <div class="actions">
        <button class="primary" id="jargon-btn">Cari istilah</button>
        <span class="status" id="jargon-status"></span>
      </div>
      <div class="error" id="jargon-error"></div>
      <div class="result" id="jargon-result"></div>
    </section>

    <section class="panel" id="panel-cite" role="tabpanel" aria-label="Citation Weaver">
      <label for="cite-text">Tempel naskah dengan penanda sitasi <span class="hint">— contoh: [cite:devlin2019]</span></label>
      <textarea id="cite-text" placeholder="Tulis naskah dengan [cite:kunci] di tempat sitasi."></textarea>
      <div class="row">
        <div>
          <label for="cite-refs">Bibliografi</label>
          <select id="cite-refs">
            <option value="sample">Contoh bawaan (7 referensi)</option>
            <option value="none">Tanpa bibliografi</option>
          </select>
        </div>
        <div>
          <label for="cite-style">Gaya sitasi</label>
          <select id="cite-style">
            <option value="apa">APA</option>
            <option value="mla">MLA</option>
            <option value="chicago">Chicago</option>
            <option value="ieee">IEEE</option>
            <option value="harvard">Harvard</option>
            <option value="vancouver">Vancouver</option>
          </select>
        </div>
        <div>
          <label for="cite-lang">Bahasa hasil</label>
          <select id="cite-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
      <details>
        <summary>Atau tempel bibliografi JSON sendiri</summary>
        <textarea id="cite-refs-json" placeholder='{"devlin2019": {"title": "BERT: ...", "year": 2019}}'></textarea>
      </details>
      <div class="actions">
        <button class="primary" id="cite-btn">Sisipkan sitasi</button>
        <span class="status" id="cite-status"></span>
      </div>
      <div class="error" id="cite-error"></div>
      <div class="result" id="cite-result"></div>
    </section>

    <section class="panel" id="panel-prompts" role="tabpanel" aria-label="Prompt Skripsi">
      <label for="prompt-select">Pilih prompt</label>
      <select id="prompt-select"></select>
      <div class="row" id="prompt-fields" style="margin-top:16px"></div>
      <div class="row">
        <div>
          <label for="prompt-lang">Bahasa prompt</label>
          <select id="prompt-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
      <div class="actions">
        <button class="primary" id="prompt-btn">Isi prompt</button>
        <button class="ghost" id="prompt-copy" disabled>Salin hasil</button>
        <span class="status" id="prompt-status"></span>
      </div>
      <div class="error" id="prompt-error"></div>
      <div class="result" id="prompt-result"></div>
    </section>

    <section class="panel" id="panel-library" role="tabpanel" aria-label="Pustaka">
      <p>Riwayat analisis yang disimpan dari tab Analisis Kualitas, dan bibliografi pribadi yang tumbuh dari referensi yang dikutip.</p>
      <div class="actions">
        <button class="primary" id="library-refresh">Muat ulang</button>
        <span class="status" id="library-status"></span>
      </div>
      <div class="error" id="library-error"></div>
      <div class="result" id="library-history"></div>
      <div class="result" id="library-detail"></div>
      <label for="library-search">Cari referensi <span class="hint">— judul, penulis, kunci, atau DOI</span></label>
      <input type="text" id="library-search" placeholder="misalnya: deep learning">
      <div class="actions">
        <button class="primary" id="library-search-btn">Cari</button>
      </div>
      <div class="result" id="library-refs"></div>
    </section>

  </div>
</main>
<footer>
  <div class="wrap">
    Berjalan lokal di komputer Anda — halaman ini tidak mengirim data ke mana pun. Skor gaya hanya laporan: baca, lalu sunting sendiri. Referensi yang tidak ada di bibliografi tidak pernah dikarang.
  </div>
</footer>
<script>
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
    });
  }
  function showError(id, msg) {
    var el = $(id);
    el.textContent = msg;
    el.classList.add("show");
  }
  function clearError(id) { $(id).classList.remove("show"); $(id).textContent = ""; }
  async function post(path, body) {
    var r = await fetch(path, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    var data = await r.json();
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }
  async function get(path) {
    var r = await fetch(path);
    var data = await r.json();
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }
  function refsPayload(modeEl, jsonEl) {
    var custom = jsonEl.value.trim();
    if (custom) return {refs_json: custom};
    return {refs: modeEl.value};
  }

  document.querySelectorAll("nav.tabs button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("nav.tabs button").forEach(function (b) {
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      document.querySelectorAll(".panel").forEach(function (p) {
        p.classList.toggle("active", p.id === "panel-" + btn.dataset.tab);
      });
      if (btn.dataset.tab === "library") loadLibrary();
    });
  });

  function renderHistory(rows) {
    var h = "";
    if (!rows.length) {
      h += '<div class="card"><p>Belum ada riwayat analisis — centang "Simpan ke pustaka" di tab Analisis Kualitas.</p></div>';
    } else {
      h += '<div class="card"><h2>Riwayat analisis</h2><ul>';
      rows.forEach(function (a) {
        h += '<li><a href="#" data-analysis="' + a.id + '">#' + a.id + " " + esc(a.title) + "</a> — "
          + esc(a.created_at.slice(0, 10)) + ", skor " + a.quality_score + "/100, gaya "
          + a.style_score + "/25</li>";
      });
      h += "</ul></div>";
    }
    $("library-history").innerHTML = h;
  }
  function renderDetail(a) {
    var h = '<div class="card"><h2>Analisis #' + a.id + " — " + esc(a.title) + "</h2>"
      + "<p>" + esc(a.created_at.slice(0, 10)) + " · Skor " + a.quality_score + "/100 · Gaya "
      + a.style_score + "/25 · Jargon " + a.jargon_count + " · Sitasi hilang "
      + a.citations_missing + " · DOI " + a.doi_ok + "/" + a.doi_total + "</p>";
    if (a.references && a.references.length) {
      h += "<p>Referensi dikutip: " + esc(a.references.join(", ")) + "</p>";
    }
    h += "<pre>" + esc(a.text) + "</pre></div>";
    $("library-detail").innerHTML = h;
  }
  function renderRefs(rows, query) {
    var h = "";
    if (!rows.length) {
      h += '<div class="card"><p>' + (query
        ? "Tidak ada referensi yang cocok dengan “" + esc(query) + "”."
        : "Tidak ada referensi di pustaka.") + "</p></div>";
    } else {
      h += '<div class="card"><h2>Referensi <span class="meta">' + rows.length + "</span></h2><ul>";
      rows.forEach(function (r) {
        h += "<li><strong>" + esc(r.key) + "</strong>" + (r.year ? " (" + r.year + ")" : "")
          + ": " + esc(r.title || "-")
          + (r.authors ? ' <span class="src">' + esc(r.authors) + "</span>" : "")
          + (r.doi ? ' <span class="src">doi:' + esc(r.doi) + "</span>" : "") + "</li>";
      });
      h += "</ul></div>";
    }
    $("library-refs").innerHTML = h;
  }
  async function loadLibrary() {
    clearError("library-error");
    $("library-status").textContent = "Memuat…";
    try {
      var hist = await get("/api/library/history?limit=20");
      renderHistory(hist.analyses);
      var refs = await get("/api/library/refs?limit=20");
      renderRefs(refs.references, "");
    } catch (e) {
      showError("library-error", e.message);
    } finally {
      $("library-status").textContent = "";
    }
  }
  $("library-refresh").addEventListener("click", loadLibrary);
  $("library-search-btn").addEventListener("click", async function () {
    var q = $("library-search").value.trim();
    clearError("library-error");
    try {
      var res = await get("/api/library/refs?limit=20"
        + (q ? "&search=" + encodeURIComponent(q) : ""));
      renderRefs(res.references, q);
    } catch (e) {
      showError("library-error", e.message);
    }
  });
  $("library-search").addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      $("library-search-btn").click();
    }
  });
  $("library-history").addEventListener("click", async function (ev) {
    var link = ev.target.closest("a[data-analysis]");
    if (!link) return;
    ev.preventDefault();
    clearError("library-error");
    try {
      var res = await get("/api/library/analysis?id="
        + encodeURIComponent(link.dataset.analysis));
      renderDetail(res.analysis);
    } catch (e) {
      showError("library-error", e.message);
    }
  });

  function renderAnalyze(res, lang) {
    var h = "";
    h += '<div class="card"><h2>Skor kualitas</h2><div class="score">'
      + '<span class="num">' + res.quality_score + '</span><span class="of">/ 100</span>'
      + '<div class="bar"><span style="width:' + res.quality_score + '%"></span></div></div></div>';
    if (res.library_id) {
      h += '<div class="card"><p>Tersimpan di pustaka (id ' + res.library_id + ").</p></div>";
    }
    if (res.jargon && res.jargon.length) {
      h += '<div class="card"><h2>Istilah jargon <span class="meta">' + res.jargon.length + ' ditemukan</span></h2><ul>';
      res.jargon.forEach(function (j) {
        h += "<li><strong>" + esc(j.term) + "</strong> — " + esc(j.translation)
          + ' <span class="src">(' + esc(j.field) + "; " + esc(j.source) + ")</span></li>";
      });
      h += "</ul></div>";
    } else {
      h += '<div class="card"><h2>Istilah jargon</h2><p>Tidak ada istilah jargon yang dikenali.</p></div>';
    }
    if (res.citations) {
      var c = res.citations;
      h += '<div class="card"><h2>Sitasi</h2><p>' + c.cited.length + " dikutip, "
        + c.missing.length + " hilang dari bibliografi, "
        + c.unused.length + " tak terpakai.</p>";
      if (c.missing.length) h += "<p><strong>Hilang:</strong> " + esc(c.missing.join(", ")) + "</p>";
      h += "</div>";
    } else {
      h += '<div class="card"><h2>Sitasi</h2><p>Tanpa bibliografi: audit sitasi dilewati.</p></div>';
    }
    var dv = res.doi_verification || {};
    var keys = Object.keys(dv);
    if (keys.length) {
      var ok = keys.filter(function (k) { return dv[k].verdict === "ok"; }).length;
      var withDoi = keys.filter(function (k) { return dv[k].doi; }).length;
      h += '<div class="card"><h2>Verifikasi DOI</h2><p>' + ok + " dari " + withDoi + " DOI terverifikasi.</p></div>";
    }
    var st = res.style;
    if (st) {
      if (st.flagged.length) {
        h += '<div class="card"><h2>Gaya <span class="meta">' + st.style_score + "/25</span></h2><ul>";
        st.flagged.forEach(function (name) {
          var s = st.signals[name];
          var label = {nominalization: "Verba ringan", connectors: "Konektor",
            passive: "Verba pasif", yang_mana: "'yang mana'/'dimana'",
            rhythm: "Ritme kalimat"}[name] || name;
          if (name === "rhythm") {
            h += "<li>" + label + ": " + Math.round(s.same_length_share * 100)
              + "% kalimat hampir sama panjang</li>";
          } else {
            h += "<li>" + label + ": " + s.count
              + (s.examples && s.examples.length ? " (" + esc(s.examples.join(", ")) + ")" : "") + "</li>";
          }
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Gaya <span class="meta">' + st.style_score + '/25</span></h2><p>Tidak ada pola kaku yang terdeteksi.</p></div>';
      }
    }
    if (res.duplicates) {
      var d = res.duplicates;
      if (d.duplicates.length) {
        h += '<div class="card"><h2>Duplikasi <span class="meta">' + d.duplicates.length + ' kalimat berulang</span></h2><ul>';
        d.duplicates.forEach(function (x) {
          h += "<li>" + esc(x.sentence) + '<br><span class="meta">'
            + Math.round(x.similarity * 100) + "% mirip &ldquo;" + esc(x.match)
            + "&rdquo; — " + (x.source_id ? "pustaka #" + x.source_id + " — " + esc(x.source_title) : "naskah ini") + "</span></li>";
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Duplikasi</h2><p>Tidak ada kalimat yang berulang dengan pustaka.</p></div>';
      }
    }
    if (res.recommendations && res.recommendations.length) {
      h += '<div class="card"><h2>Rekomendasi</h2><ul>';
      res.recommendations.forEach(function (r) { h += "<li>" + esc(r) + "</li>"; });
      h += "</ul></div>";
    }
    var sg = res.suggestions;
    if (sg && sg.suggestions && sg.suggestions.length) {
      var labels = {nominalization: "Verba ringan", connectors: "Konektor",
        passive: "Verba pasif", yang_mana: "'yang mana'/'dimana'",
        rhythm: "Ritme kalimat"};
      h += '<div class="card"><h2>Saran rewrite gaya <span class="meta">' + sg.count + "</span></h2>";
      sg.suggestions.forEach(function (s, i) {
        h += "<p><strong>" + (i + 1) + ". " + (labels[s.pattern] || s.pattern) + "</strong> — “" + esc(s.original.trim()) + "”";
        if (s.replacement !== null) {
          h += " → “" + (s.replacement === "" ? "(hapus)" : esc(s.replacement)) + "”";
        }
        h += "<br><span class=\"hint\">Sebelum:</span> " + esc(s.context);
        if (s.fixed) {
          h += "<br><span class=\"hint\">Sesudah:</span> " + esc(s.fixed);
        } else {
          h += "<br>" + esc(s.note);
        }
        h += "</p>";
      });
      if (sg.count > sg.suggestions.length) {
        h += "<p>Menampilkan " + sg.suggestions.length + " dari " + sg.count + " saran.</p>";
      }
      h += '<div class="actions"><button id="copy-fixed-btn" onclick="copyFixedText()">Salin teks yang diperbaiki</button> <span class="status" id="copy-fixed-status"></span></div>';
      h += "</div>";
    }
    return h;
  }

  async function copyFixedText() {
    var btn = $("copy-fixed-btn");
    var status = $("copy-fixed-status");
    if (!btn) return;
    btn.disabled = true;
    status.textContent = "Menyalin…";
    try {
      var res = await post("/api/humanize", {
        text: $("analyze-text").value,
        lang: $("analyze-lang").value,
        apply: true
      });
      var fixed = res.fixed_text || "";
      var n = (res.suggestions || []).filter(function (s) { return s.replacement !== null; }).length;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(fixed);
      } else {
        var ta = document.createElement("textarea");
        ta.value = fixed;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      status.textContent = "Disalin — " + n + " saran diterapkan.";
    } catch (e) {
      status.textContent = "Gagal: " + e.message;
    } finally { btn.disabled = false; }
  }

  $("analyze-btn").addEventListener("click", async function () {
    var btn = $("analyze-btn");
    clearError("analyze-error");
    $("analyze-result").innerHTML = "";
    var text = $("analyze-text").value.trim();
    if (!text) { showError("analyze-error", "Tempel naskah dulu."); return; }
    btn.disabled = true;
    $("analyze-status").textContent = "Menganalisis…";
    try {
      var body = refsPayload($("analyze-refs"), $("analyze-refs-json"));
      body.text = text;
      body.lang = $("analyze-lang").value;
      body.verify = $("analyze-verify").checked;
      body.suggest = $("analyze-suggest").checked;
      body.duplicates = $("analyze-duplicates").checked;
      body.save = $("analyze-save").checked;
      var res = await post("/api/analyze", body);
      $("analyze-result").innerHTML = renderAnalyze(res, body.lang);
      $("analyze-status").textContent = "";
    } catch (e) {
      showError("analyze-error", "Gagal: " + e.message);
      $("analyze-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  $("jargon-btn").addEventListener("click", async function () {
    var btn = $("jargon-btn");
    clearError("jargon-error");
    $("jargon-result").innerHTML = "";
    var text = $("jargon-text").value.trim();
    if (!text) { showError("jargon-error", "Tempel teks dulu."); return; }
    btn.disabled = true;
    $("jargon-status").textContent = "Mencari istilah…";
    try {
      var res = await post("/api/jargon", {text: text});
      var h = "";
      if (res.matches.length) {
        h += '<div class="card"><h2>Istilah ditemukan <span class="meta">' + res.matches.length + "</span></h2><ul>";
        res.matches.forEach(function (m) {
          h += "<li><strong>" + esc(m.term) + "</strong> — " + esc(m.translation)
            + ' <span class="src">(' + esc(m.field) + "; " + esc(m.source) + ")</span></li>";
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Istilah ditemukan</h2><p>Tidak ada istilah kamus yang cocok dengan teks ini.</p></div>';
      }
      $("jargon-result").innerHTML = h;
      $("jargon-status").textContent = "";
    } catch (e) {
      showError("jargon-error", "Gagal: " + e.message);
      $("jargon-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  $("cite-btn").addEventListener("click", async function () {
    var btn = $("cite-btn");
    clearError("cite-error");
    $("cite-result").innerHTML = "";
    var text = $("cite-text").value.trim();
    if (!text) { showError("cite-error", "Tempel naskah dulu."); return; }
    btn.disabled = true;
    $("cite-status").textContent = "Menyisipkan sitasi…";
    try {
      var body = refsPayload($("cite-refs"), $("cite-refs-json"));
      body.text = text;
      body.style = $("cite-style").value;
      body.lang = $("cite-lang").value;
      var res = await post("/api/cite", body);
      $("cite-result").innerHTML = '<div class="card"><h2>Hasil</h2><pre class="bib">'
        + esc(res.output) + "</pre></div>";
      $("cite-status").textContent = "";
    } catch (e) {
      showError("cite-error", "Gagal: " + e.message);
      $("cite-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  var promptsCache = null;
  async function loadPrompts() {
    var r = await fetch("/api/prompts");
    var data = await r.json();
    promptsCache = data.prompts;
    var sel = $("prompt-select");
    var groups = {};
    data.prompts.forEach(function (p) {
      (groups[p.category] = groups[p.category] || []).push(p);
    });
    Object.keys(groups).forEach(function (cat) {
      var og = document.createElement("optgroup");
      og.label = cat;
      groups[cat].forEach(function (p) {
        var o = document.createElement("option");
        o.value = p.id;
        o.textContent = p.name;
        og.appendChild(o);
      });
      sel.appendChild(og);
    });
    renderPromptFields();
  }
  function currentPrompt() {
    var id = $("prompt-select").value;
    return promptsCache.find(function (p) { return p.id === id; });
  }
  function renderPromptFields() {
    var p = currentPrompt();
    var box = $("prompt-fields");
    box.innerHTML = "";
    if (!p) return;
    p.fields.forEach(function (f) {
      var div = document.createElement("div");
      var lab = document.createElement("label");
      lab.textContent = f.label;
      lab.setAttribute("for", "pf-" + f.key);
      var inp = document.createElement("input");
      inp.type = "text";
      inp.id = "pf-" + f.key;
      inp.dataset.key = f.key;
      div.appendChild(lab);
      div.appendChild(inp);
      box.appendChild(div);
    });
  }
  $("prompt-select").addEventListener("change", renderPromptFields);
  $("prompt-btn").addEventListener("click", async function () {
    var btn = $("prompt-btn");
    clearError("prompt-error");
    $("prompt-result").innerHTML = "";
    var p = currentPrompt();
    if (!p) { showError("prompt-error", "Pilih prompt dulu."); return; }
    var values = {};
    document.querySelectorAll("#prompt-fields input").forEach(function (inp) {
      values[inp.dataset.key] = inp.value;
    });
    btn.disabled = true;
    $("prompt-status").textContent = "Mengisi prompt…";
    try {
      var res = await post("/api/prompts/fill", {
        id: p.id, values: values, lang: $("prompt-lang").value
      });
      $("prompt-result").innerHTML = '<div class="card"><h2>Hasil</h2><pre>'
        + esc(res.text) + "</pre></div>";
      $("prompt-copy").disabled = false;
      $("prompt-status").textContent = "";
    } catch (e) {
      showError("prompt-error", "Gagal: " + e.message);
      $("prompt-status").textContent = "";
    } finally { btn.disabled = false; }
  });
  $("prompt-copy").addEventListener("click", async function () {
    var pre = document.querySelector("#prompt-result pre");
    if (!pre) return;
    try {
      await navigator.clipboard.writeText(pre.textContent);
      $("prompt-status").textContent = "Disalin.";
    } catch (e) {
      $("prompt-status").textContent = "Tidak bisa menyalin otomatis — blok lalu salin manual.";
    }
  });

  loadPrompts().catch(function (e) {
    showError("prompt-error", "Gagal memuat daftar prompt: " + e.message);
  });
})();
</script>
</body>
</html>
"""


_MAX_BODY = 1_000_000  # 1 MB cap on API request bodies
_DRAIN_CAP = 2_000_000  # most the server will read to discard an oversize body


class RequestTooLargeError(ValueError):
    """Request body over the 1 MB cap (maps to HTTP 413)."""


def _error_message(e: Exception) -> str:
    """Plain message for an exception raised with one argument.

    str(KeyError("x")) is "'x'" (repr), so take args[0] instead.
    """
    return str(e.args[0]) if e.args else str(e)


def _load_ui_references(payload: dict) -> dict | None:
    """Resolve the UI's refs choice: 'sample' (default), 'none', or
    a pasted bibliography JSON string under 'refs_json'."""
    if payload.get("refs_json"):
        try:
            refs = json.loads(payload["refs_json"])
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"bibliografi JSON tidak valid: {e}")
        if not isinstance(refs, dict):
            raise ValueError("bibliografi JSON harus berupa objek {kunci: referensi}")
        return refs
    if payload.get("refs", "sample") == "none":
        return None
    try:
        return load_references(DEFAULT_REFS)
    except FileNotFoundError:
        raise ValueError("contoh bibliografi tidak ditemukan di folder ini")


def _read_json_body(handler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    if length > _MAX_BODY:
        if length <= _DRAIN_CAP:
            # Read and discard the body so the client can still read
            # the 413 and the connection stays usable on keep-alive.
            remaining = length
            while remaining > 0:
                chunk = handler.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        else:
            # Absurd size: do not waste time draining it. Closing the
            # connection keeps the unread bytes from being parsed as
            # a new request line (which used to log a 414 traceback).
            handler.close_connection = True
        raise RequestTooLargeError("badan permintaan terlalu besar (maks 1 MB)")
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("badan permintaan harus JSON yang valid")
    if not isinstance(body, dict):
        raise ValueError("badan permintaan harus berupa objek JSON")
    return body


class _UIHandler(http.server.BaseHTTPRequestHandler):
    """Serves the embedded page plus a small JSON API for the five tabs."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep the console quiet
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_page(self) -> None:
        data = WEB_UI_HTML.replace(
            "__ACADEMIC_TOOLS_VERSION__", __version__).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)
        try:
            if path in ("/", "/index.html"):
                self._send_page()
            elif path == "/api/prompts":
                self._send_json(200, {"prompts": [
                    {"id": p["id"], "name": p["name"], "name_en": p["name_en"],
                     "category": p["category"], "tool": p["tool"],
                     "fields": p["fields"]}
                    for p in PROMPTS
                ]})
            elif path == "/api/library/history":
                self._send_json(200, self._library_history(query))
            elif path == "/api/library/analysis":
                self._send_json(200, self._library_analysis(query))
            elif path == "/api/library/refs":
                self._send_json(200, self._library_refs(query))
            else:
                self._send_json(404, {"error": "tidak ditemukan"})
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except KeyError as e:
            self._send_json(404, {"error": _error_message(e)})
        except Exception:
            self._send_json(500, {"error": "kesalahan server, coba lagi"})

    @staticmethod
    def _query_int(query: dict, name: str, default: int) -> int:
        raw = (query.get(name) or [None])[0]
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            raise ValueError(f"{name} harus angka")
        return max(1, min(100, value))

    def _library_history(self, query: dict) -> dict:
        return {"analyses": list_analyses(
            limit=self._query_int(query, "limit", 20))}

    def _library_analysis(self, query: dict) -> dict:
        raw = (query.get("id") or [None])[0]
        if raw is None or not raw.isdigit():
            raise ValueError("id analisis harus angka")
        analysis = get_analysis(int(raw))
        if analysis is None:
            raise KeyError(f"tidak ada analisis #{raw}")
        return {"analysis": analysis}

    def _library_refs(self, query: dict) -> dict:
        limit = self._query_int(query, "limit", 20)
        search = (query.get("search") or [""])[0].strip()
        if search:
            rows = search_references(search, limit=limit)
        else:
            rows = list_references(limit=limit)
        return {"references": rows}

    def do_POST(self):
        try:
            body = _read_json_body(self)
            if self.path == "/api/analyze":
                self._send_json(200, self._analyze(body))
            elif self.path == "/api/humanize":
                self._send_json(200, self._humanize(body))
            elif self.path == "/api/jargon":
                self._send_json(200, self._jargon(body))
            elif self.path == "/api/cite":
                self._send_json(200, self._cite(body))
            elif self.path == "/api/prompts/fill":
                self._send_json(200, self._fill_prompt(body))
            else:
                self._send_json(404, {"error": "tidak ditemukan"})
        except RequestTooLargeError as e:
            self._send_json(413, {"error": str(e)})
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except (LookupError, KeyError) as e:
            self._send_json(400, {"error": _error_message(e)})
        except Exception:
            self._send_json(500, {"error": "kesalahan server, coba lagi"})

    def _analyze(self, body: dict) -> dict:
        text = str(body.get("text") or "").strip()
        if not text:
            raise ValueError("teks kosong")
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        refs = _load_ui_references(body)
        result = analyze_text_quality(
            text, refs, lang=lang, verify_dois=bool(body.get("verify")),
            suggest=bool(body.get("suggest")))
        if body.get("duplicates"):
            result["duplicates"] = find_duplicates(text)
        if body.get("save"):
            result["library_id"] = save_analysis(text, result, refs)
        return result

    def _humanize(self, body: dict) -> dict:
        text = str(body.get("text") or "").strip()
        if not text:
            raise ValueError("teks kosong")
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        result = suggest_style_fixes(text, lang=lang, limit=None)
        if body.get("apply"):
            result["fixed_text"] = apply_suggestions(text, result)["text"]
        return result

    def _jargon(self, body: dict) -> dict:
        text = str(body.get("text") or "").strip()
        if not text:
            raise ValueError("teks kosong")
        field = body.get("field") or None
        matches = find_terms(text, field)
        return {"matches": matches, "count": len(matches)}

    def _cite(self, body: dict) -> dict:
        text = str(body.get("text") or "").strip()
        if not text:
            raise ValueError("teks kosong")
        refs = _load_ui_references(body)
        if refs is None:
            raise ValueError("sitasi butuh bibliografi (pilih contoh bawaan atau tempel JSON)")
        style = body.get("style") or "apa"
        if style not in STYLES:
            raise ValueError(f"gaya tidak dikenal: {style}")
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        output, woven = weave(text, refs, style=style, lang=lang)
        return {"output": output, "woven": woven}

    def _fill_prompt(self, body: dict) -> dict:
        prompt_id = str(body.get("id") or "")
        prompt = get_prompt(prompt_id)
        if prompt is None:
            raise ValueError(f"prompt tidak dikenal: {prompt_id}")
        values = body.get("values") or {}
        if not isinstance(values, dict):
            raise ValueError("values harus berupa objek {kunci: nilai}")
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        return {"text": fill_prompt(prompt_id, values, lang=lang)}


def make_server(host: str = "127.0.0.1", port: int = 8000):
    """Build the local web UI server (port 0 picks a free port)."""
    return http.server.ThreadingHTTPServer((host, port), _UIHandler)


def serve_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Serve a local web UI for all four tools (localhost only).")
    p.add_argument("--port", type=int, default=8000,
                   help="port to listen on (default: 8000)")
    p.add_argument("--host", default="127.0.0.1",
                   help="interface to bind (default: 127.0.0.1, localhost only)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)
    server = make_server(args.host, args.port)
    host, port = server.server_address[:2]
    print(f"Academic Tools v{__version__} — buka http://{host}:{port}/")
    print("Berhenti dengan Ctrl-C. Hanya localhost; tidak ada data yang keluar dari komputer ini.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
    return 0


def main(argv=None) -> int:
    """Entry point. No args -> interactive menu; jargon/cite/prompts -> passthrough."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("jargon", "cite", "prompts", "analyze",
                           "humanize", "library", "serve", "duplicates"):
        tool, rest = argv[0], argv[1:]
        if tool == "jargon":
            return jargon_main(rest)
        if tool == "cite":
            return cite_main(rest)
        if tool == "analyze":
            return analyze_main(rest)
        if tool == "humanize":
            return humanize_main(rest)
        if tool == "library":
            return library_main(rest)
        if tool == "duplicates":
            return duplicates_main(rest)
        if tool == "serve":
            return serve_main(rest)
        return prompts_main(rest)
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] in ("-v", "--version"):
        print(f"academic_cli {CLI_VERSION} "
              f"(jargon_buster {JARGON_VERSION}, citation_weaver {CITATION_VERSION}, "
              f"skripsi_prompts {PROMPTS_VERSION})")
        return 0
    try:
        return CLI().run()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
