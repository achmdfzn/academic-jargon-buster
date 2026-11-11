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
import urllib.error
import urllib.request
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

__version__ = "1.10.0"
JARGON_VERSION = "1.0.4"
CITATION_VERSION = "1.4.0"
PROMPTS_VERSION = "1.1.0"
CLI_VERSION = "1.5.0"

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


def analyze_text_quality(
    text: str,
    references: dict | None = None,
    *,
    lang: str = "id",
    verify_dois: bool = True,
) -> dict:
    """Analyze an academic text for quality: jargon, citations, DOI status,
    and bibliography completeness.

    Returns a dict with keys:
    - jargon: list of detected jargon terms with explanations
    - citations: citation audit result (cited, missing, unused)
    - doi_verification: per-reference DOI check results
    - quality_score: composite score 0-100
    - recommendations: list of improvement suggestions

    If `references` is provided, citation audit and DOI verification are
    performed against it. Otherwise, citation and DOI checks are skipped.
    """
    result = {
        "jargon": [],
        "citations": None,
        "doi_verification": {},
        "quality_score": 0,
        "recommendations": [],
    }

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
    # Three parts of 25 (max 75), scaled to 0-100.
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

    total_score = sum(score_parts)
    result["quality_score"] = round(min(total_score, 75) / 75 * 100)

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
        "recs": "Recommendations",
        "recs_none": "No recommendations — the text is in good shape.",
        "no_refs": "No bibliography: citation audit and DOI verification skipped.",
    },
}


def format_analyze(result: dict, lang: str = "id") -> str:
    """Render an analyze_text_quality() result as readable text."""
    s = _ANALYZE_STRINGS.get(lang, _ANALYZE_STRINGS["id"])
    lines = [s["heading"], "", f"{s['score']}: {result['quality_score']}/100"]
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
        description="Check an academic text: jargon, citations, and DOI "
                    "verification in one pass.")
    p.add_argument("input", nargs="?", help="plain-text file to analyze")
    p.add_argument("--text", help="analyze this text instead of a file")
    p.add_argument("--refs", help="bibliography JSON file (optional; without "
                   "it, citation audit and DOI checks are skipped)")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--no-verify", action="store_true",
                   help="skip DOI verification even when --refs is given")
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
                                  verify_dois=not args.no_verify)
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_analyze(result, lang=args.lang))
    bad_doi = any(v.get("verdict") == "missing"
                  for v in result["doi_verification"].values())
    missing = result["citations"]["missing"] if result["citations"] else []
    return 1 if missing or bad_doi else 0


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
        "tagline": "Jargon Buster  |  Citation Weaver  |  Prompt Skripsi",
        "banner_hint": "id  |  ketik angka, Enter untuk memilih",
        "menu_title": "Pilih alat:",
        "jargon": "Jargon Buster — terjemahkan istilah akademik",
        "cite": "Citation Weaver — sisipkan sitasi ke naskah",
        "prompts": "Prompt Skripsi — template prompt untuk tiap bab",
        "analyze": "Analisis Kualitas — cek jargon, sitasi, dan DOI sekaligus",
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
        "press_enter": "Tekan Enter untuk kembali...",
        "result": "Hasil:",
    },
    "en": {
        "banner": "Academic Tools",
        "tagline": "Jargon Buster  |  Citation Weaver  |  Thesis Prompts",
        "banner_hint": "en  |  type a number, Enter to choose",
        "menu_title": "Choose a tool:",
        "jargon": "Jargon Buster — translate academic jargon",
        "cite": "Citation Weaver — weave citations into text",
        "prompts": "Thesis Prompts — ready-made prompts for each chapter",
        "analyze": "Quality Check — jargon, citations, and DOIs in one pass",
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
        "press_enter": "Press Enter to go back...",
        "result": "Result:",
    },
}


BANNER_MIN_WIDTH = 60


def format_banner(lang: str) -> str:
    """Boxed banner for the interactive menu; width follows the text.

    ASCII only: the menu still renders when stdout is piped and the
    console encoding is not UTF-8 (cp1252, cp437).
    """
    t = STRINGS[lang]
    title = t["banner"]
    version = f"v{__version__}"
    tagline = t["tagline"]
    hint = t["banner_hint"]
    width = max(BANNER_MIN_WIDTH, len(title) + len(version) + 2,
                len(tagline) + 2, len(hint) + 2)
    heading = title + " " * (width - len(title) - len(version)) + version
    heavy = "=" * (width + 2)
    light = "-" * (width + 2)
    return "\n".join([
        f"  +{heavy}+",
        f"  | {heading} |",
        f"  +{light}+",
        f"  | {tagline.ljust(width)} |",
        f"  | {hint.ljust(width)} |",
        f"  +{heavy}+",
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
            print(f"1. {self.t['jargon']}")
            print(f"2. {self.t['cite']}")
            print(f"3. {self.t['prompts']}")
            print(f"4. {self.t['analyze']}")
            print(f"5. {self.t['lang']}")
            print(f"0. {self.t['exit']}")
            choice = self.ask_choice(self.t["choice"], 5)
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
            print(f"\n--- {self.t['prompts']} ---")
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


def main(argv=None) -> int:
    """Entry point. No args -> interactive menu; jargon/cite/prompts -> passthrough."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("jargon", "cite", "prompts", "analyze"):
        tool, rest = argv[0], argv[1:]
        if tool == "jargon":
            return jargon_main(rest)
        if tool == "cite":
            return cite_main(rest)
        if tool == "analyze":
            return analyze_main(rest)
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
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
