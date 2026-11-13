"""Audit #6 follow-up tests for the citation weaver: H-6, H-7.

H-6: `_in_text` never normalised an authors string, so
`weave(... authors:"Field, Andy" ...)` rendered "(F et al., 2018)"
— the string was iterated character by character — instead of
"(Field, 2018)". It now uses `_authors_list`, the same normaliser
`format_reference` already used.

H-7: author-year multi-citations failed totally. The parenthetical
regex demanded ")" right after the year, so "(Field, 2018;
Creswell, 2018)" matched neither key: `author_year` came back []
and both entries were false-positive "unused". Groups are now
scanned unit by unit, so ";" and "," separators both work.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import audit_citations, weave


def _ref(authors, year=2018, title="Judul"):
    return {"authors": authors, "year": year, "title": title}


REFS = {
    "field": _ref("Field, Andy"),
    "creswell": _ref("Creswell, John W."),
    "ghozali": _ref("Ghozali, Imam", year=2020),
}


class TestStringAuthorsInTextAudit6(unittest.TestCase):
    """H-6: weave() renders a lone authors string as one author."""

    # authors value -> expected APA in-text citation. A string is
    # ONE author (the same contract _authors_list gives
    # format_reference); only a list holds several authors.
    STRING_CASES = {
        # 1 author as a string: the reported bug.
        "Field, Andy": "(Field, 2018)",
        # 1 author as a list: was already right, must stay right.
        "list-1": "(Field, 2018)",
        # 2 authors as a list: "and", no et al.
        "list-2": "(Field and Ghozali, 2018)",
        # 3+ authors as a list: et al.
        "list-3": "(Field et al., 2018)",
        "list-4": "(Field et al., 2018)",
    }

    def _authors_for(self, case):
        if case == "list-1":
            return ["Field, Andy"]
        if case == "list-2":
            return ["Field, Andy", "Ghozali, Imam"]
        if case == "list-3":
            return ["Field, Andy", "Ghozali, Imam", "Creswell, John W."]
        if case == "list-4":
            return ["Field, Andy", "Ghozali, Imam",
                    "Creswell, John W.", "Sugiyono"]
        return case

    def test_string_authors_apa(self):
        for case, expected in self.STRING_CASES.items():
            with self.subTest(case=case):
                _, woven = weave("Hasil [cite:k] menunjukkan.",
                                 {"k": _ref(self._authors_for(case))},
                                 style="apa")
                self.assertEqual(woven, f"Hasil {expected} menunjukkan.")

    def test_string_authors_other_styles(self):
        # The same normalisation feeds every author-year style.
        expected = {
            "mla": "(Field)",
            "chicago": "(Field 2018)",
            "harvard": "(Field, 2018)",
        }
        for style, citation in expected.items():
            with self.subTest(style=style):
                _, woven = weave("Hasil [cite:k].",
                                 {"k": _ref("Field, Andy")}, style=style)
                self.assertEqual(woven, f"Hasil {citation}.")

    def test_string_authors_numbered_styles_unchanged(self):
        # IEEE / Vancouver never show the name; the fix must not
        # change their output for string authors either.
        for style in ("ieee", "vancouver"):
            with self.subTest(style=style):
                _, woven = weave("Hasil [cite:k].",
                                 {"k": _ref("Field, Andy")}, style=style)
                self.assertEqual(woven, "Hasil [1].")

    def test_string_authors_bibliography_agrees(self):
        # In-text and bibliography must name the same author now.
        full, woven = weave("Hasil [cite:k].",
                            {"k": _ref("Field, Andy")}, style="apa")
        self.assertIn("(Field, 2018)", woven)
        self.assertIn("Field, A. (2018).", full)


class TestMultiCitationAuthorYearAudit6(unittest.TestCase):
    """H-7: audit_citations() detects multi-citations in one group."""

    # text -> (expected author_year keys, expected unused keys).
    # REFS holds field + creswell (both 2018) and ghozali (2020).
    MULTI_CASES = {
        # The reported bug: semicolon separator, both detected.
        "(Field, 2018; Creswell, 2018)": (["field", "creswell"], ["ghozali"]),
        # Comma separator: same result.
        "(Field, 2018, Creswell, 2018)": (["field", "creswell"], ["ghozali"]),
        # Reversed order keeps bibliography order (dict order).
        "(Creswell, 2018; Field, 2018)": (["field", "creswell"], ["ghozali"]),
        # Three units in one group.
        "(Field, 2018; Creswell, 2018; Ghozali, 2020)":
            (["field", "creswell", "ghozali"], []),
        # et al. unit inside a multi-citation group.
        "(Field et al., 2018; Creswell, 2018)":
            (["field", "creswell"], ["ghozali"]),
        # Two separate groups in one sentence.
        "(Field, 2018) dan (Creswell, 2018)":
            (["field", "creswell"], ["ghozali"]),
        # Only one of the two units matches: the other stays unused.
        "(Field, 2018; Ghozali, 2019)":
            (["field"], ["creswell", "ghozali"]),
        # A unit with the wrong year matches nothing.
        "(Field, 2019; Creswell, 2019)":
            ([], ["creswell", "field", "ghozali"]),
    }

    def test_multi_citation_groups(self):
        for text, (expected_keys, expected_unused) in self.MULTI_CASES.items():
            with self.subTest(text=text):
                result = audit_citations(text, REFS)
                self.assertEqual(result["author_year"], expected_keys)
                self.assertEqual(result["unused"], expected_unused)
                for key in expected_keys:
                    self.assertIn(key, result["cited"])
                    self.assertEqual(result["counts"][key], 1)

    def test_single_citation_unchanged(self):
        # Single parenthetical / narrative / et al. forms keep the
        # behaviour test_audit5_citation.py already pins down.
        cases = {
            "(Field, 2018)": ["field"],
            "Menurut Field (2018), hasilnya signifikan.": ["field"],
            "(Field et al., 2018) sepakat.": ["field"],
            "(Field, 2018) dikutip.": ["field"],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                result = audit_citations(text, REFS)
                self.assertEqual(result["author_year"], expected)
                self.assertNotIn("creswell", result["cited"])

    def test_negatives_still_correct(self):
        # No citation, wrong year, and a bare name+year outside
        # parens must still match nothing.
        cases = {
            "Tidak ada sitasi di sini.": [],
            "(Field, 2019) bukan rujukan ini.": [],
            "Dalam Field, 2018, dijelaskan.": [],
            "(lihat Field, 2018) bukan sitasi langsung.": [],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                result = audit_citations(text, REFS)
                self.assertEqual(result["author_year"], expected)
                self.assertEqual(result["unused"],
                                 ["creswell", "field", "ghozali"])

    def test_multi_citation_counts_once_per_key(self):
        # Author-year credits a key once however often it appears
        # (pre-existing audit_citations semantics: _author_year_keys
        # returns each key once, unlike [cite:] markers, which count
        # every occurrence).
        text = "(Field, 2018; Creswell, 2018) dan (Field, 2018)."
        result = audit_citations(text, REFS)
        self.assertEqual(result["author_year"], ["field", "creswell"])
        self.assertEqual(result["counts"], {"field": 1, "creswell": 1})
        self.assertEqual(result["unused"], ["ghozali"])

    def test_weave_single_citation_unchanged(self):
        # H-7 touched only the audit matcher; weave() for a single
        # [cite:key] must render exactly as before.
        full, woven = weave("Hasil [cite:field] menunjukkan.", REFS,
                            style="apa")
        self.assertEqual(woven, "Hasil (Field, 2018) menunjukkan.")
        self.assertIn("Field, A. (2018). Judul.", full)


if __name__ == "__main__":
    unittest.main()
