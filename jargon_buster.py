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
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys

__version__ = "1.0.0"

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
}


def find_terms(text: str, field: str | None = None):
    """Return list of dicts for each dictionary term found in text.

    Longest terms first, so 'stochastic gradient descent' wins over
    'gradient descent' when both match. Case-insensitive.
    """
    found = []
    seen_spans = []
    terms = sorted(DICTIONARY, key=len, reverse=True)
    for term in terms:
        explanation, term_field, source = DICTIONARY[term]
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
    args = p.parse_args(argv)

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
