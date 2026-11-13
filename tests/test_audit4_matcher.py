"""Tests for audit #4 fixes (v1.27.1): H-7, H-8, N-10, N-11, N-12, N-13, N-14.

- H-7 (T-11): the dictionary matcher requires a match to START at a
  word boundary (start of string, whitespace, or an opening bracket
  or quote), so 't-test' no longer matches inside 'contest-test'
  and 'anova' no longer matches inside 'Rekanova'. Suffixed forms
  still match ('validitasnya' -> 'validitas'): there is deliberately
  no end-boundary rule.
- H-8 (T-12): analyze/jargon/humanize/duplicates on a missing file
  raise ValueError('File tidak ditemukan: ...') so main() prints a
  clean stderr message and exits 1 — never a traceback.
- N-10: Indonesian alias 'diskusi kelompok terfokus' for
  'focus group discussion'.
- N-11: _validate_references accepts a tuple for 'authors'.
- N-12: _ris_pages keeps only the first range of
  '189–194, 200' (audit #5, N-5, changed _bibtex_pages to keep the
  full value instead).
- N-13: 'uji reliabilitas' says Cronbach's alpha can be negative.
- N-14: humanize --apply --text ends stdout with a newline, and
  --apply on a file writes no .humanized file when 0 suggestions
  were applied.
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    _bibtex_pages,
    _ris_pages,
    _validate_references,
    analyze_main,
    duplicates_main,
    find_terms,
    humanize_main,
    jargon_main,
    load_dictionary,
)


def _terms(text):
    return [t["term"] for t in find_terms(text)]


class TestMatcherStartBoundary(unittest.TestCase):
    """H-7 / T-11: no false positives from mid-word matches."""

    def test_contest_test_does_not_match_t_test(self):
        self.assertNotIn(
            "t-test", _terms("contest-test results and pretest scores"))

    def test_rekanova_does_not_match_anova(self):
        self.assertNotIn(
            "anova", _terms("Rekanova and anovulation studies."))

    def test_anovanova_matches_once_at_position_zero(self):
        # Known limitation, documented in _iter_matches: a term
        # followed by extra letters is indistinguishable from a term
        # with a suffix, so 'anovanova' still matches once — at
        # position 0, where the start-boundary rule is satisfied.
        # What the rule does fix is the second 'anova' inside the
        # word (position 4) and 'anova' inside 'Rekanova'.
        found = find_terms("anovanova")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["term"], "anova")
        self.assertEqual(found[0]["original"], "anova")

    def test_standalone_terms_still_match(self):
        found = _terms("The anova test and the t-test were used.")
        self.assertEqual(found, ["anova", "t-test"])

    def test_match_after_opening_bracket_or_quote(self):
        found = _terms('(anova) [t-test] "phenomenology"')
        self.assertEqual(found, ["anova", "t-test", "phenomenology"])

    def test_suffixed_forms_still_match(self):
        # No end-boundary rule on purpose: plurals and Indonesian
        # suffixes keep matching.
        self.assertIn("validitas", _terms("validitasnya"))
        self.assertIn("reliabilitas", _terms("reliabilitasnya"))
        self.assertIn("korelasi", _terms("korelasinya"))
        self.assertIn("fenomenologi", _terms("fenomenologinya"))
        self.assertIn("correlation", _terms("correlations"))

    def test_invalidity_and_abnormality_no_longer_match(self):
        # The start-boundary rule also fixes the older known cases
        # from the dictionary comment: 'validity' inside
        # 'invalidity', 'normality' inside 'abnormality'.
        self.assertNotIn("validity", _terms("invalidity"))
        self.assertNotIn("normality", _terms("abnormality"))

    def test_uji_terhadap_still_does_not_match_t_test(self):
        # 'uji t' stays out of the dictionary on purpose, and the
        # start-boundary rule cannot help here anyway: 'uji terhadap'
        # starts with 'uji t' at position 0.
        self.assertNotIn(
            "t-test",
            _terms("Uji terhadap hipotesis dilakukan setelah data."))


class TestMissingFileCleanError(unittest.TestCase):
    """H-8 / T-12: missing input file -> ValueError, exit 1, no traceback."""

    MAINS = (analyze_main, jargon_main, humanize_main, duplicates_main)

    def test_each_main_raises_value_error(self):
        for main in self.MAINS:
            with self.subTest(main=main.__name__):
                with self.assertRaises(ValueError) as cm:
                    main(["/tidak/ada/file.txt"])
                self.assertIn("File tidak ditemukan", str(cm.exception))

    def test_each_subcommand_via_main_exits_1_without_traceback(self):
        for sub in ("analyze", "jargon", "humanize", "duplicates"):
            with self.subTest(sub=sub):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    code = tools.main([sub, "/tidak/ada/file.txt"])
                self.assertEqual(code, 1)
                self.assertIn("File tidak ditemukan", err.getvalue())
                self.assertNotIn("Traceback", err.getvalue())
                self.assertNotIn("Traceback", out.getvalue())

    def test_analyze_missing_refs_file_is_clean_too(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False,
                encoding="utf-8") as f:
            f.write("Penelitian ini memakai data primer.")
            path = f.name
        try:
            with self.assertRaises(ValueError) as cm:
                analyze_main([path, "--refs", "/tidak/ada/refs.json"])
            self.assertIn("File tidak ditemukan", str(cm.exception))
        finally:
            os.unlink(path)


class TestDictionaryAliasAndWording(unittest.TestCase):
    """N-10, N-13: alias and explanation wording."""

    def test_diskusi_kelompok_terfokus_alias(self):
        # N-10: Indonesian alias for 'focus group discussion'.
        found = _terms("Penelitian memakai diskusi kelompok terfokus.")
        self.assertIn("diskusi kelompok terfokus", found)
        alias = load_dictionary()["diskusi kelompok terfokus"]
        english = load_dictionary()["focus group discussion"]
        self.assertEqual(alias, english)
        # 't-test' still has no Indonesian alias ('uji t' stays out:
        # the documented trade-off — 'uji terhadap' starts with it).
        self.assertNotIn("uji t", load_dictionary())

    def test_uji_reliabilitas_alpha_can_be_negative(self):
        # N-13: Cronbach's alpha is typically 0-1 but can be negative.
        explanation = load_dictionary()["uji reliabilitas"][0]
        self.assertIn("can be negative", explanation)
        self.assertNotIn("a number from 0 to 1", explanation)


class TestValidateReferencesTuple(unittest.TestCase):
    """N-11: _validate_references accepts a tuple for 'authors'."""

    def test_tuple_authors_accepted_and_normalized(self):
        data = _validate_references(
            {"k": {"authors": ("Devlin, A.", "Smith, B."),
                   "title": "Judul"}})
        self.assertEqual(data["k"]["authors"], ["Devlin, A.", "Smith, B."])

    def test_tuple_with_non_string_still_rejected(self):
        with self.assertRaises(ValueError):
            _validate_references({"k": {"authors": ("Devlin, A.", 3)}})

    def test_list_authors_unchanged(self):
        data = _validate_references(
            {"k": {"authors": ["Devlin, A."], "title": "Judul"}})
        self.assertEqual(data["k"]["authors"], ["Devlin, A."])


class TestPagesFirstRangeOnly(unittest.TestCase):
    """N-12 (audit #4): RIS keeps only the first range of an odd
    multi-page range. BibTeX changed in audit #5 (N-5): it keeps the
    full value, because a BibTeX pages field can hold a list."""

    def test_ris_pages_drops_trailing_page(self):
        self.assertEqual(_ris_pages("189–194, 200"), ("189", "194"))
        self.assertEqual(_ris_pages("189-194, 200"), ("189", "194"))
        self.assertEqual(_ris_pages("189–194"), ("189", "194"))
        self.assertEqual(_ris_pages("189"), ("189", ""))

    def test_bibtex_pages_keeps_full_value(self):
        self.assertEqual(_bibtex_pages("189–194, 200"), "189--194, 200")
        self.assertEqual(_bibtex_pages("189-194, 200"), "189--194, 200")
        self.assertEqual(_bibtex_pages("189–194"), "189--194")


class TestHumanizeApplyOutput(unittest.TestCase):
    """N-14: --apply output handling."""

    def test_apply_text_stdout_ends_with_newline(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = humanize_main([
                "--text",
                "Penelitian ini melakukan pengukuran terhadap "
                "suhu ruangan.",
                "--apply",
            ])
        self.assertEqual(code, 1)
        self.assertTrue(buf.getvalue().endswith("\n"))
        self.assertIn("Penelitian ini mengukur suhu ruangan.",
                      buf.getvalue())

    def test_apply_file_writes_nothing_when_zero_applied(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "naskah.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Penelitian ini sudah bagus.")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = humanize_main([path, "--apply"])
            self.assertEqual(code, 0)
            self.assertFalse(
                os.path.exists(os.path.join(d, "naskah.humanized.txt")))
            self.assertNotIn("Tersimpan di", buf.getvalue())

    def test_apply_file_still_writes_when_something_applied(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "naskah.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Penelitian ini melakukan pengukuran terhadap "
                        "suhu ruangan.")
            code = humanize_main([path, "--apply"])
            self.assertEqual(code, 1)
            out_path = os.path.join(d, "naskah.humanized.txt")
            with open(out_path, encoding="utf-8") as f:
                self.assertEqual(
                    f.read(), "Penelitian ini mengukur suhu ruangan.")


if __name__ == "__main__":
    unittest.main()
