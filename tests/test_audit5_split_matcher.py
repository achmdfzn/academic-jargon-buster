"""Tests for audit #5 track 3 fixes (v1.27.2): H-1, H-6, H-7, N-1, N-11.

- H-1: the dictionary matcher also accepts punctuation separators
  (", ; : / ?" and the dashes) immediately before a term, so
  "korelasi,validitas" matches both terms. A period still blocks
  (".anova" does not match) and a hyphen still blocks
  ("pre-t-test" stays empty).
- H-6: list abbreviations (dll./dst./dkk.) are only protected when
  the next word starts lowercase; a capitalised next word (or the
  end of the text) ends the sentence.
- H-7: honorifics (Bpk./Sdr./Tn./Ny./Nn.) and "hlm." join the
  abbreviation list and never split a sentence.
- N-1: the terminator pattern allows a RUN of closing quotes or
  parentheses ("'Pergi!')" ends a sentence), not just one.
- N-11: dotted degrees (M.Si./S.Pd./S.Si./M.Pd.) are protected
  like abbreviations and never split a sentence mid-way.

Plus regressions from audit #4 that must stay true: e.g./i.e./
hal./Dr./"Dr. A. Budi" do not split, "contest-test" and "Rekanova"
do not match, suffixed forms ("validitasnya") still match, the
decimal 3.14 does not split, and "'Jangan!'" keeps its quote.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import find_terms


def _terms(text):
    return [t["term"] for t in find_terms(text)]


class TestMatcherPunctuationSeparators(unittest.TestCase):
    """H-1: punctuation before a term starts a match."""

    def test_comma_separated_terms_all_match(self):
        found = _terms("korelasi,validitas,reliabilitas")
        self.assertIn("korelasi", found)
        self.assertIn("validitas", found)
        self.assertIn("reliabilitas", found)

    def test_comma_after_parenthesised_year(self):
        self.assertIn(
            "anova", _terms("menurut Field (2018),anova"))

    def test_semicolon_colon_slash_dashes_match_both(self):
        for text in ("korelasi;validitas", "korelasi:validitas",
                     "korelasi/validitas", "korelasi—validitas",
                     "korelasi–validitas", "korelasi?validitas"):
            with self.subTest(text=text):
                found = _terms(text)
                self.assertIn("korelasi", found)
                self.assertIn("validitas", found)

    def test_bracket_and_quote_controls_still_match(self):
        found = _terms("(validitas) [anova]")
        self.assertIn("validitas", found)
        self.assertIn("anova", found)

    def test_period_still_blocks(self):
        # ".anova" must NOT match: "." is deliberately absent from
        # _MATCH_START_CHARS (audit #4 verification).
        self.assertNotIn("anova", _terms(".anova"))

    def test_hyphen_still_blocks(self):
        self.assertEqual(_terms("pre-t-test"), [])
        self.assertEqual(_terms("contest-test"), [])


class TestListAbbreviationsConditional(unittest.TestCase):
    """H-6: dll./dst./dkk. only protected before a lowercase word."""

    def test_dll_before_capital_ends_sentence(self):
        self.assertEqual(
            tools._split_sentences(
                "Ia membeli buku, pensil, dll. Kemudian pulang."),
            ["Ia membeli buku, pensil, dll", "Kemudian pulang"])

    def test_dst_before_lowercase_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Buku itu dst. dibaca semua. Lalu disimpan."),
            ["Buku itu dst. dibaca semua", "Lalu disimpan"])

    def test_dll_before_capital_at_end(self):
        self.assertEqual(
            tools._split_sentences("Ia pergi ke pasar, dll. Selesai."),
            ["Ia pergi ke pasar, dll", "Selesai"])

    def test_dkk_before_capital_ends_sentence(self):
        self.assertEqual(
            tools._split_sentences(
                "Ia pergi bersama Budi, dkk. Mereka pulang."),
            ["Ia pergi bersama Budi, dkk", "Mereka pulang"])

    def test_dkk_before_lowercase_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Mereka, dkk. datang besok. Lalu pergi."),
            ["Mereka, dkk. datang besok", "Lalu pergi"])

    def test_list_abbrev_at_end_of_text(self):
        self.assertEqual(
            tools._split_sentences("Ia membeli buku, dll."),
            ["Ia membeli buku, dll"])


class TestHonorificAbbreviations(unittest.TestCase):
    """H-7: Bpk./Sdr./Tn./Ny./Nn./hlm. never split a sentence."""

    def test_tn_and_ny_do_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Tn. Hadi dan Ny. Sari datang. Mereka rapat."),
            ["Tn. Hadi dan Ny. Sari datang", "Mereka rapat"])

    def test_bpk_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Bpk. Ahmad datang. Ia tersenyum."),
            ["Bpk. Ahmad datang", "Ia tersenyum"])

    def test_hlm_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Lihat hlm. 12 untuk detail. Bab dua dimulai."),
            ["Lihat hlm. 12 untuk detail", "Bab dua dimulai"])

    def test_sdr_and_nn_do_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Sdr. Budi dan Nn. Ani hadir. Rapat dimulai."),
            ["Sdr. Budi dan Nn. Ani hadir", "Rapat dimulai"])


class TestTerminatorClosingRuns(unittest.TestCase):
    """N-1: a run of closing quotes/parentheses ends a sentence."""

    def test_quote_then_paren_closes_sentence(self):
        self.assertEqual(
            tools._split_sentences(
                "Dia berkata 'Pergi!') Lalu diam. Semua hening."),
            ["Dia berkata 'Pergi!')", "Lalu diam", "Semua hening"])

    def test_double_quote_then_paren_closes_sentence(self):
        self.assertEqual(
            tools._split_sentences(
                'Dia berkata "Pergi!") Lalu diam.'),
            ['Dia berkata "Pergi!")', "Lalu diam"])

    def test_single_closing_quote_still_correct(self):
        self.assertEqual(
            tools._split_sentences(
                "'Jangan!' Begitu katanya. Lalu pergi."),
            ["'Jangan!'", "Begitu katanya", "Lalu pergi"])

    def test_double_quote_control_still_correct(self):
        self.assertEqual(
            tools._split_sentences(
                'Dia berkata "Pergi!" Lalu diam.'),
            ['Dia berkata "Pergi!"', "Lalu diam"])

    def test_paren_control_still_correct(self):
        self.assertEqual(
            tools._split_sentences("Hebat!) Lalu pergi."),
            ["Hebat!)", "Lalu pergi"])


class TestDottedDegrees(unittest.TestCase):
    """N-11: M.Si./S.Pd./S.Si./M.Pd. never split a sentence."""

    def test_m_si_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Gelar M.Si. didapat. Ia bangga."),
            ["Gelar M.Si. didapat", "Ia bangga"])

    def test_s_pd_and_s_si_do_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "S.Pd. dan S.Si. adalah gelar. Mereka bangga."),
            ["S.Pd. dan S.Si. adalah gelar", "Mereka bangga"])

    def test_m_pd_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "M.Pd. didapat tahun lalu. Ia senang."),
            ["M.Pd. didapat tahun lalu", "Ia senang"])


class TestAudit4Regressions(unittest.TestCase):
    """Regressions from audit #4 that must stay true."""

    def test_e_g_i_e_hal_dr_do_not_split(self):
        self.assertEqual(
            tools._split_sentences("Lihat e.g. contoh ini. Lalu pergi."),
            ["Lihat e.g. contoh ini", "Lalu pergi"])
        self.assertEqual(
            tools._split_sentences(
                "Contohnya i.e. data primer. Lalu pergi."),
            ["Contohnya i.e. data primer", "Lalu pergi"])
        self.assertEqual(
            tools._split_sentences("Lihat hal. 5 e.g. tabel. Selesai."),
            ["Lihat hal. 5 e.g. tabel", "Selesai"])
        self.assertEqual(
            tools._split_sentences(
                "Dr. Budi datang ke kampus. Ia membawa buku."),
            ["Dr. Budi datang ke kampus", "Ia membawa buku"])

    def test_dr_a_budi_initial_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Dr. A. Budi datang. Ia pergi."),
            ["Dr. A. Budi datang", "Ia pergi"])

    def test_mid_word_terms_still_do_not_match(self):
        self.assertNotIn("t-test", _terms("contest-test"))
        self.assertNotIn("anova", _terms("Rekanova"))

    def test_suffixed_forms_still_match(self):
        self.assertIn("validitas", _terms("validitasnya"))
        self.assertIn("reliabilitas", _terms("reliabilitasnya"))
        self.assertIn("correlation", _terms("correlations"))

    def test_decimal_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Nilai 3.14 itu pi. Lanjut."),
            ["Nilai 3.14 itu pi", "Lanjut"])

    def test_closing_quote_regression(self):
        self.assertEqual(
            tools._split_sentences(
                "'Jangan!' Begitu katanya. Lalu pergi."),
            ["'Jangan!'", "Begitu katanya", "Lalu pergi"])


if __name__ == "__main__":
    unittest.main()
