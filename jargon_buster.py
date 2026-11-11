"""academic-jargon-buster — standalone demo implementation.

Pure Python, no dependencies. This is the runnable companion to the
Hermes skill in skills/research/academic-jargon-buster/SKILL.md.

The skill file is the spec (what the Hermes agent should do).
This module is a small, honest reference implementation of its core
idea: find known jargon terms in plain text and explain them in
plain English, with provenance for each term.

Usage:
    python3 jargon_buster.py demos/test_paper.txt
    python3 jargon_buster.py demos/test_paper.txt --format csv
    python3 jargon_buster.py --text "The renormalization group ..." --field physics
    python3 jargon_buster.py --list-terms [--field physics]
    python3 jargon_buster.py --update-dictionary --from new_terms.json [--field physics]

Extra terms can be added with --update-dictionary --from <file>, where
the file is JSON: {"term": {"explanation": "...", "field": "...",
"source": "..."}}. Added terms are saved in dictionary.json next to
this script and loaded on every run.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys

__version__ = "1.0.2"

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
    # Added 2026-11-11 from a real user abstract (a student abstract
    # a student abstract MIS, SUS evaluation). Indonesian aliases included
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


def find_terms(text: str, field: str | None = None):
    """Return list of dicts for each dictionary term found in text.

    Longest terms first, so 'stochastic gradient descent' wins over
    'gradient descent' when both match. Case-insensitive.
    """
    found = []
    seen_spans = []
    dictionary = load_dictionary()
    terms = sorted(dictionary, key=len, reverse=True)
    for term in terms:
        explanation, term_field, source = dictionary[term]
        if field and term_field != field:
            continue
        for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            span = (m.start(), m.end())
            if any(s <= span[0] < e or s < span[1] <= e for s, e in seen_spans):
                continue
            seen_spans.append(span)
            found.append(
                {
                    "original": m.group(0),
                    "term": term,
                    "translation": explanation,
                    "field": term_field,
                    "source": source,
                    "confidence": 1.0,  # exact dictionary match
                }
            )
    found.sort(key=lambda d: text.lower().find(d["term"]))
    return found


def to_annotated_markdown(text: str, field: str | None = None) -> str:
    """Original text with jargon followed by its plain explanation."""
    terms = find_terms(text, field=field)
    if not terms:
        return text + "\n\n_No known jargon terms found in the dictionary._\n"
    out = text
    # Replace longest first, from the end, so offsets stay valid.
    for item in sorted(terms, key=lambda d: len(d["term"]), reverse=True):
        pattern = re.compile(re.escape(item["term"]), re.IGNORECASE)
        out = pattern.sub(
            lambda m: f"{m.group(0)} ({item['translation']})", out, count=1
        )
    lines = ["# Annotated output\n", out, "\n## Terms found\n"]
    for item in terms:
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


def main(argv=None) -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
