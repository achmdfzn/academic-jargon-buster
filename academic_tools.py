#!/usr/bin/env python3
"""academic_tools — every feature of this repo in one file.

Pure Python, no dependencies. Copy this single file anywhere and it
works: a jargon translator, a citation weaver, and an interactive
menu CLI (Claude-CLI style) on top of both.

    python3 academic_tools.py                  # interactive menu (default)
    python3 academic_tools.py jargon ...       # straight to Jargon Buster
    python3 academic_tools.py cite ...         # straight to Citation Weaver

Jargon Buster: find known jargon in plain text and explain each term
in plain language, with provenance. 22 terms, fields from physics to
usability to software engineering, plus Indonesian aliases.

    python3 academic_tools.py jargon demos/test_paper.txt
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

One rule, everywhere in this file: NEVER invent a reference. A
[cite:key] with no bibliography entry is marked [PERLU RUJUKAN: key] /
[REFERENCE NEEDED: key], never filled in with a made-up paper.

The old entry points (jargon_buster.py, citation_weaver.py,
academic_cli.py) still exist as thin wrappers around this file, so
existing commands, demos, and imports keep working.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

__version__ = "1.1.0"
JARGON_VERSION = "1.0.2"
CITATION_VERSION = "1.0.0"
CLI_VERSION = "1.0.0"

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
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.list_styles:
        print("Citation styles: " + ", ".join(STYLES))
        return 0
    if args.list_jurusan:
        for d in DISCIPLINES:
            print(f"{d['id']} / {d['en']} — {d['style']}")
        return 0

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
# Interactive menu CLI
# ======================================================================
DEFAULT_REFS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "demos", "citation-weaver", "references.json",
)

STRINGS = {
    "id": {
        "banner": "Academic Tools — Jargon Buster + Citation Weaver",
        "menu_title": "Pilih alat:",
        "jargon": "Jargon Buster — terjemahkan istilah akademik",
        "cite": "Citation Weaver — sisipkan sitasi ke naskah",
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
        "press_enter": "Tekan Enter untuk kembali...",
        "result": "Hasil:",
    },
    "en": {
        "banner": "Academic Tools — Jargon Buster + Citation Weaver",
        "menu_title": "Choose a tool:",
        "jargon": "Jargon Buster — translate academic jargon",
        "cite": "Citation Weaver — weave citations into text",
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
        "press_enter": "Press Enter to go back...",
        "result": "Result:",
    },
}


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
            print(f"\n{'=' * 20} {self.t['banner']} {'=' * 20}")
            print(self.t["menu_title"])
            print(f"1. {self.t['jargon']}")
            print(f"2. {self.t['cite']}")
            print(f"3. {self.t['lang']}")
            print(f"0. {self.t['exit']}")
            choice = self.ask_choice(self.t["choice"], 3)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_menu()
            elif choice == 2:
                self.cite_menu()
            elif choice == 3:
                self.lang = "en" if self.lang == "id" else "id"
            elif choice == 0 or choice is None:
                print(self.t["goodbye"])
                return 0

    # -- Jargon Buster --------------------------------------------------

    def jargon_menu(self):
        while True:
            print(f"\n--- {self.t['jargon']} ---")
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
            print(f"\n--- {self.t['cite']} ---")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_styles']}")
            print(f"3. {self.t['list_majors']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 3)
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
            elif choice == 0 or choice is None:
                return

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


def main(argv=None) -> int:
    """Entry point. No args -> interactive menu; jargon/cite -> passthrough."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("jargon", "cite"):
        tool, rest = argv[0], argv[1:]
        return jargon_main(rest) if tool == "jargon" else cite_main(rest)
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] in ("-v", "--version"):
        print(f"academic_cli {CLI_VERSION} "
              f"(jargon_buster {JARGON_VERSION}, citation_weaver {CITATION_VERSION})")
        return 0
    try:
        return CLI().run()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
