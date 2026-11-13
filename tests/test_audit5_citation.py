"""Tests for audit #5 fixes, track 4 (citation weaver + dictionary):
H-4, H-5, H-8, H-9, N-3, N-5, N-12, T-2 (T-2 itself lives in
test_academic_tools.py: the count literals are gone there).
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    _authors_apa,
    _authors_chicago,
    _authors_mla,
    _bibtex_pages,
    _ris_pages,
    audit_citations,
    export_bibtex,
    export_ris,
    find_terms,
    format_audit,
    format_reference,
    format_verification,
)

NO_AUTHOR = {"title": "Judul Saja"}
NO_AUTHOR_LIST = {"title": "Judul Saja", "authors": []}
FIELD2018 = {
    "field2018": {
        "authors": ["Field, Andy"],
        "title": "Discovering Statistics Using IBM SPSS Statistics",
        "type": "book",
        "venue": "SAGE",
        "year": 2018,
    },
}


class TestNoAuthorReference(unittest.TestCase):
    """H-4: a reference with no authors never raises IndexError and is
    rendered title-first with "n.d." in every style."""

    def test_helpers_return_empty_for_no_authors(self):
        self.assertEqual(_authors_apa([]), "")
        self.assertEqual(_authors_mla([]), "")
        self.assertEqual(_authors_chicago([]), "")

    def test_all_six_styles_without_authors(self):
        for style in tools.STYLES:
            for ref in (NO_AUTHOR, NO_AUTHOR_LIST):
                out = format_reference(ref, style)
                self.assertIn("Judul Saja", out, style)
                self.assertIn("n.d.", out, style)
                self.assertNotIn("n.d..", out, style)
                # Title first: the output starts with the title (or its
                # opening quote), never with a bare author slot.
                self.assertTrue(
                    out.startswith("Judul Saja")
                    or out.startswith("“Judul Saja")
                    or out.startswith("'Judul Saja"),
                    f"{style}: {out!r}")

    def test_no_author_with_venue_and_link(self):
        ref = {"title": "Judul Saja", "authors": [],
               "venue": "Jurnal X", "year": 2020,
               "doi": "10.1000/contoh"}
        out = format_reference(ref, "apa")
        self.assertIn("Judul Saja. (2020).", out)
        self.assertIn("Jurnal X", out)
        self.assertIn("https://doi.org/10.1000/contoh", out)


class TestStringAuthors(unittest.TestCase):
    """H-5: a lone author string is one author, not one per letter."""

    def test_string_authors_rendered_as_one_author(self):
        ref = {"authors": "Field, Andy", "title": "T", "year": 2018}
        self.assertEqual(
            format_reference(ref, "apa"), "Field, A. (2018). T.")
        self.assertEqual(
            format_reference(ref, "harvard"), "Field (2018) 'T',")

    def test_string_authors_not_rendered_letter_by_letter(self):
        ref = {"authors": "Field, Andy", "title": "T", "year": 2018}
        for style in tools.STYLES:
            out = format_reference(ref, style)
            self.assertNotIn("F, i, e, l, d", out, style)
            self.assertIn("Field", out, style)


class TestVerificationFootnote(unittest.TestCase):
    """H-8: the footnote must match the rule — 'missing' when one
    checked source answers 404 and no source errored."""

    def _result(self):
        return {"a": {"doi": "10.1/x", "crossref": "not-found",
                      "openalex": "skipped", "verdict": "missing"}}

    def test_indonesian_footnote_states_missing_rule(self):
        text = format_verification(self._result(), lang="id")
        self.assertIn("tidak ditemukan", text)
        self.assertIn("menjawab 404", text)
        self.assertIn("tidak ada sumber yang error", text)
        self.assertNotIn("baru dicek satu sumber", text)

    def test_english_footnote_states_missing_rule(self):
        text = format_verification(self._result(), lang="en")
        self.assertIn("not found", text)
        self.assertIn("answers 404", text)
        self.assertIn("no source errored", text)
        self.assertNotIn("checked in only one source is 'unverified'", text)


class TestAuthorYearAudit(unittest.TestCase):
    """H-9: APA author-year citations no longer make a bibliography
    entry look "unused" — and the audit says so."""

    def test_parenthetical_author_year_marks_cited(self):
        result = audit_citations(
            "Hasil ini sejalan dengan (Field, 2018).", FIELD2018)
        self.assertEqual(result["author_year"], ["field2018"])
        self.assertEqual(result["unused"], [])
        self.assertIn("field2018", result["cited"])

    def test_narrative_author_year_marks_cited(self):
        result = audit_citations(
            "Menurut Field (2018), hasilnya signifikan.", FIELD2018)
        self.assertEqual(result["author_year"], ["field2018"])
        self.assertEqual(result["unused"], [])

    def test_et_al_parenthetical_marks_cited(self):
        result = audit_citations(
            "Beberapa studi (Field et al., 2018) sepakat.", FIELD2018)
        self.assertEqual(result["author_year"], ["field2018"])
        self.assertEqual(result["unused"], [])

    def test_marker_control_still_works(self):
        result = audit_citations("Lihat [cite:field2018].", FIELD2018)
        self.assertEqual(result["author_year"], [])
        self.assertEqual(result["cited"], ["field2018"])
        self.assertEqual(result["unused"], [])

    def test_unmentioned_entry_stays_unused(self):
        result = audit_citations("Tidak ada sitasi di sini.", FIELD2018)
        self.assertEqual(result["author_year"], [])
        self.assertEqual(result["unused"], ["field2018"])

    def test_wrong_year_does_not_match(self):
        result = audit_citations("(Field, 2019) bukan rujukan ini.",
                                 FIELD2018)
        self.assertEqual(result["author_year"], [])
        self.assertEqual(result["unused"], ["field2018"])

    def test_report_flags_author_year_as_not_fully_audited(self):
        result = audit_citations("(Field, 2018) dikutip.", FIELD2018)
        report = format_audit(result, lang="en")
        self.assertIn("field2018", report)
        self.assertIn("not fully audited", report)


class TestIrregularEnglishForms(unittest.TestCase):
    """N-3: irregular plurals / adjective form are dictionary keys
    pointing at the same explanation and source as the base form."""

    BASE = {
        "hypotheses": "hypothesis",
        "methodologies": "methodology",
        "case studies": "case study",
        "phenomenological": "phenomenology",
    }

    def test_new_forms_match_with_base_explanation_and_source(self):
        for alias, base in self.BASE.items():
            found = find_terms(f"The {alias} were tested.")
            self.assertEqual(len(found), 1, alias)
            self.assertEqual(found[0]["term"], alias)
            base_expl, _field, base_src = tools.DICTIONARY[base]
            self.assertEqual(found[0]["translation"], base_expl, alias)
            self.assertEqual(found[0]["source"], base_src, alias)

    def test_dictionary_grew_by_four(self):
        for alias in self.BASE:
            self.assertIn(alias, tools.DICTIONARY, alias)
        self.assertEqual(len(tools.DICTIONARY), 77)

    def test_phenomenologinya_is_not_a_match(self):
        # Documented: "phenomenologinya" does not start with
        # "phenomenology" (nor with "fenomenologi"), so no term
        # matches — that is not a bug.
        self.assertEqual(find_terms("phenomenologinya"), [])


class TestMultiPageRanges(unittest.TestCase):
    """N-5: BibTeX keeps the full pages value; RIS keeps the first
    range only (one SP / one EP line)."""

    def test_bibtex_pages_keeps_full_value(self):
        self.assertEqual(_bibtex_pages("189–194, 200"), "189--194, 200")
        self.assertEqual(_bibtex_pages("189-194, 200"), "189--194, 200")
        self.assertEqual(_bibtex_pages("189–194"), "189--194")

    def test_ris_pages_keeps_first_range_only(self):
        self.assertEqual(_ris_pages("189–194, 200"), ("189", "194"))
        self.assertEqual(_ris_pages("189-194, 200"), ("189", "194"))

    def test_exports_agree(self):
        refs = {"k": {"authors": ["A, B"], "title": "T",
                      "type": "article", "venue": "J",
                      "year": 2020, "pages": "189–194, 200"}}
        self.assertIn("pages = {189--194, 200}", export_bibtex(refs))
        ris = export_ris(refs)
        self.assertIn("SP  - 189", ris)
        self.assertIn("EP  - 194", ris)
        self.assertNotIn("SP  - 200", ris)


class TestSpecificSources(unittest.TestCase):
    """N-12: no dictionary source is generic any more; the 16
    formerly generic terms now cite a specific book/paper."""

    EXPECTED = {
        "renormalization group": "Wilson & Kogut 1974",
        "gradient descent": "Boyd & Vandenberghe 2004",
        "causal inference": "Pearl 2009",
        "polymorphism": "Cardelli & Wegner 1985",
        "mitosis": "Alberts et al. 2014",
        "stochastic gradient descent": "Robbins & Monro 1951",
        "overfitting": "Hastie, Tibshirani & Friedman 2009",
        "heteroscedasticity": "White 1980",
        "peer review": "Smith 2006",
        "hypothesis": "Creswell & Creswell 2018",
        "hypotheses": "Creswell & Creswell 2018",
        "methodology": "Creswell & Creswell 2018",
        "methodologies": "Creswell & Creswell 2018",
        "qualitative research": "Creswell 2013",
        "quantitative research": "Creswell & Creswell 2018",
        "object relational mapping": "Fowler 2002",
        "authentication": "Needham & Schroeder 1978",
        "autentikasi": "Needham & Schroeder 1978",
    }

    def test_no_generic_source_remains(self):
        for term, (_expl, _field, source) in tools.DICTIONARY.items():
            self.assertNotIn("Wikipedia", source, term)
            self.assertNotIn("field textbooks", source, term)
            self.assertNotIn("Software engineering textbooks", source, term)
            self.assertNotIn("arXiv glossary", source, term)

    def test_formerly_generic_terms_have_specific_sources(self):
        for term, source in self.EXPECTED.items():
            self.assertIn(term, tools.DICTIONARY, term)
            self.assertIn(source, tools.DICTIONARY[term][2], term)


if __name__ == "__main__":
    unittest.main()
