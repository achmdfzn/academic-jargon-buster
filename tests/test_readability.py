"""Tests for the readability scorer (Flesch Reading Ease + FKGL),
the `readability` subcommand, and its analyze / web UI integration.

The syllable counter follows EYD edisi V: vowels a/e/i/o/u,
diphthongs ai/au/ei/oi ("ei" IS a diphthong, so "survei" is 2),
plus a curated whole-word exception list for pairs that straddle
a syllable/morpheme boundary ("ma-in", "ke-in-dah-an"). English
(lang="en") counts vowel-letter runs with a silent-final-e rule. The formulas are Flesch
(1948), J. Appl. Psychol. 32(3), 221-233:
  RE   = 206.835 - 1.015 * (words/sentence) - 84.6 * (syllables/word)
  FKGL = 0.39 * (words/sentence) + 11.8 * (syllables/word) - 15.59
Band boundaries are built from known components (monosyllabic words
in one sentence) rather than natural texts, so they cannot drift:
with every word one syllable, RE = 122.235 - 1.015 * words, so the
90/80/70/60/50/30 crossings fall between word counts 31/32, 41/42,
51/52, 61/62, 71/72, 90/91.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools

_MONO = ("di", "dan", "yang", "ke", "pun", "tak")


def _mono_sentence(n_words):
    """One sentence of n monosyllabic words (1 syllable each)."""
    return " ".join(_MONO[i % len(_MONO)] for i in range(n_words)) + "."


class TestCountSyllables(unittest.TestCase):
    def test_spec_examples(self):
        # Every example from the spec, including the documented limits.
        cases = {
            "penelitian": 5, "mahasiswa": 4, "kuesioner": 5,
            "baik": 1, "atau": 2, "boikot": 2, "dia": 2, "biaya": 3,
            "buah": 2, "keindahan": 4, "sistem": 2, "informasi": 4,
            "di": 1, "yang": 1,
        }
        for word, want in cases.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_ei_is_a_diphthong(self):
        # EYD edisi V has FOUR diphthongs, ai/au/ei/oi: "survei" is
        # 2 (sur-vei), not 3. "keindahan" stays 4 (ke-in-dah-an):
        # its "ei" straddles a morpheme boundary, so it is covered
        # by the whole-word exception list, not by the diphthong.
        self.assertEqual(tools._count_syllables("survei"), 2)
        self.assertEqual(tools._count_syllables("keindahan"), 4)

    def test_no_vowel_words_count_one(self):
        for word in ("123", "2024", "TV", "b2b"):
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), 1)

    def test_mixed_letters_and_digits(self):
        # Trailing non-letters are stripped, then the letters count:
        # "COVID-19" -> "covid" (2), "buku2" -> "buku" (2).
        self.assertEqual(tools._count_syllables("COVID-19"), 2)
        self.assertEqual(tools._count_syllables("buku2"), 2)

    def test_case_and_punctuation_stripped(self):
        self.assertEqual(tools._count_syllables("Penelitian,"), 5)
        self.assertEqual(tools._count_syllables("MAHASISWA"), 4)
        self.assertEqual(tools._count_syllables("(sistem)"), 2)


class TestReadabilityMath(unittest.TestCase):
    def test_hand_computed_two_sentences(self):
        # 2 sentences x 10 words, every word 2 syllables:
        #   words/sentence = 10, syllables/word = 2
        #   RE   = 206.835 - 1.015*10 - 84.6*2 = 27.485 -> 27.5
        #   FKGL = 0.39*10 + 11.8*2 - 15.59 = 11.91 -> 11.9
        text = (" ".join(["sistem data buku tulis baca"] * 2) + ". "
                + " ".join(["sistem data buku tulis baca"] * 2) + ".")
        r = tools.readability_score(text)
        self.assertEqual(r["flesch_reading_ease"], 27.5)
        self.assertEqual(r["flesch_kincaid_grade"], 11.9)
        self.assertEqual(r["band"], "Sangat sulit")
        self.assertEqual(r["words"], 20)
        self.assertEqual(r["sentences"], 2)
        self.assertEqual(r["avg_words_per_sentence"], 10.0)
        self.assertEqual(r["avg_syllables_per_word"], 2.0)
        self.assertEqual(r["total_syllables"], 40)

    def test_easy_text_clamps_to_100_and_grade_to_0(self):
        # 3 monosyllabic words, 1 sentence: RE = 122.235 - 3.045
        # = 119.19 -> clamped to 100; FKGL = 1.17 + 11.8 - 15.59
        # = -2.62 -> clamped to 0.
        r = tools.readability_score("Di dan yang.")
        self.assertEqual(r["flesch_reading_ease"], 100.0)
        self.assertEqual(r["flesch_kincaid_grade"], 0.0)
        self.assertEqual(r["band"], "Sangat mudah")

    def test_hard_text_clamps_re_to_0(self):
        # 200 monosyllabic words, 1 sentence: RE = 122.235 - 203
        # = -80.765 -> clamped to 0; FKGL = 78 + 11.8 - 15.59
        # = 74.21 -> 74.2.
        r = tools.readability_score(_mono_sentence(200))
        self.assertEqual(r["flesch_reading_ease"], 0.0)
        self.assertEqual(r["flesch_kincaid_grade"], 74.2)
        self.assertEqual(r["band"], "Sangat sulit")

    def test_result_keys(self):
        r = tools.readability_score("Penelitian ini memakai metode survei.")
        self.assertEqual(
            set(r),
            {"flesch_reading_ease", "flesch_kincaid_grade", "band",
             "words", "sentences", "avg_words_per_sentence",
             "avg_syllables_per_word", "total_syllables", "note"})

    def test_empty_text_is_value_error(self):
        for bad in ("", "   ", "\n\t "):
            with self.subTest(text=repr(bad)):
                with self.assertRaises(ValueError) as cm:
                    tools.readability_score(bad)
                self.assertEqual(str(cm.exception), "teks kosong")

    def test_single_sentence_scores(self):
        r = tools.readability_score("Di sini.")
        self.assertEqual(r["sentences"], 1)
        self.assertEqual(r["words"], 2)
        # di=1, sini=2 -> 3 syllables; RE = 206.835 - 2.03 - 126.9
        # = 77.905 -> 77.9.
        self.assertEqual(r["flesch_reading_ease"], 77.9)
        self.assertEqual(r["band"], "Cukup mudah")

    def test_note_is_honest_in_both_languages(self):
        id_note = tools.readability_score("Di sini.")["note"]
        en_note = tools.readability_score("Di sini.", lang="en")["note"]
        self.assertIn("hanya indikasi, bukan vonis", id_note)
        self.assertIn("indication, not a verdict", en_note)
        self.assertIn("Flesch", id_note)
        self.assertIn("Flesch", en_note)


class TestReadabilityBands(unittest.TestCase):
    # With every word one syllable, RE = 122.235 - 1.015 * words:
    #   31 -> 90.8 (Sangat mudah)   32 -> 89.8 (Mudah)
    #   41 -> 80.6 (Mudah)          42 -> 79.6 (Cukup mudah)
    #   51 -> 70.5 (Cukup mudah)    52 -> 69.5 (Standar)
    #   61 -> 60.3 (Standar)        62 -> 59.3 (Cukup sulit)
    #   71 -> 50.2 (Cukup sulit)    72 -> 49.2 (Sulit)
    #   90 -> 30.9 (Sulit)          91 -> 29.9 (Sangat sulit)
    BOUNDARIES = (
        (31, 90.8, "Sangat mudah"), (32, 89.8, "Mudah"),
        (41, 80.6, "Mudah"), (42, 79.6, "Cukup mudah"),
        (51, 70.5, "Cukup mudah"), (52, 69.5, "Standar"),
        (61, 60.3, "Standar"), (62, 59.3, "Cukup sulit"),
        (71, 50.2, "Cukup sulit"), (72, 49.2, "Sulit"),
        (90, 30.9, "Sulit"), (91, 29.9, "Sangat sulit"),
    )

    def test_band_boundaries(self):
        for n_words, re_want, band_want in self.BOUNDARIES:
            with self.subTest(n_words=n_words):
                r = tools.readability_score(_mono_sentence(n_words))
                self.assertEqual(r["flesch_reading_ease"], re_want)
                self.assertEqual(r["band"], band_want)

    def test_english_band_labels(self):
        self.assertEqual(
            tools.readability_score(_mono_sentence(31), lang="en")["band"],
            "Very easy")
        self.assertEqual(
            tools.readability_score(_mono_sentence(91), lang="en")["band"],
            "Very difficult")
        self.assertEqual(
            tools.readability_score(_mono_sentence(62), lang="en")["band"],
            "Fairly difficult")


class TestAnalyzeCarriesReadability(unittest.TestCase):
    TEXT = ("Penelitian ini menggunakan metode survei. "
            "Data dikumpulkan melalui kuesioner.")

    def test_analyze_carries_readability_without_changing_score(self):
        result = tools.analyze_text_quality(self.TEXT, verify_dois=False)
        self.assertIn("readability", result)
        self.assertEqual(result["readability"],
                         tools.readability_score(self.TEXT))
        # The score is unchanged: four 25-point parts, no refs means
        # citations and DOI are neutral 25 each.
        parts = tools._score_parts(result)
        self.assertEqual(parts[:3], [25.0, 25.0, 25.0])
        self.assertEqual(parts[3], result["style"]["style_score"])
        self.assertEqual(result["quality_score"],
                         tools._round_half_up(sum(parts)))

    def test_format_analyze_shows_readability(self):
        result = tools.analyze_text_quality(self.TEXT, verify_dois=False)
        out = tools.format_analyze(result)
        self.assertIn("Keterbacaan", out)
        self.assertIn("Flesch Reading Ease", out)
        self.assertIn(result["readability"]["band"], out)
        self.assertIn("FKGL", out)
        self.assertIn("hanya indikasi, bukan vonis", out)

    def test_format_analyze_english(self):
        result = tools.analyze_text_quality(self.TEXT, lang="en",
                                            verify_dois=False)
        out = tools.format_analyze(result, lang="en")
        self.assertIn("Readability", out)
        self.assertIn("indication, not a verdict", out)

    def test_analyze_json_carries_readability(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.analyze_main(["--text", self.TEXT, "--json"])
        self.assertEqual(code, 0)
        res = json.loads(buf.getvalue())
        self.assertIn("readability", res)
        self.assertEqual(res["readability"]["words"], 9)
        self.assertEqual(res["score_parts"], [25.0, 25.0, 25.0,
                                              res["style"]["style_score"]])


class TestReadabilityCLI(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.readability_main(argv)
        return code, buf.getvalue()

    def test_text_flag(self):
        code, out = self._run(["--text",
                               "Penelitian ini memakai metode survei."])
        self.assertEqual(code, 0)
        self.assertIn("Keterbacaan", out)
        self.assertIn("Flesch Reading Ease", out)
        self.assertIn("Flesch-Kincaid Grade Level", out)

    def test_file(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False,
                encoding="utf-8") as f:
            f.write("Penelitian ini memakai metode survei. "
                    "Data dikumpulkan melalui kuesioner.")
            path = f.name
        try:
            code, out = self._run([path])
            self.assertEqual(code, 0)
            self.assertIn("Keterbacaan", out)
        finally:
            os.unlink(path)

    def test_json(self):
        code, out = self._run(["--text", "Di sini.", "--json"])
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertEqual(res["flesch_reading_ease"], 77.9)
        self.assertEqual(res["band"], "Cukup mudah")
        self.assertEqual(res["words"], 2)

    def test_json_english(self):
        code, out = self._run(["--text", _mono_sentence(31),
                               "--lang", "en", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["band"], "Very easy")

    def test_missing_file_is_clean_error(self):
        with self.assertRaises(ValueError) as cm:
            tools.readability_main(["/tidak/ada/file.txt"])
        self.assertIn("File tidak ditemukan", str(cm.exception))

    def test_empty_text_is_clean_error(self):
        with self.assertRaises(ValueError) as cm:
            tools.readability_main(["--text", "   "])
        self.assertEqual(str(cm.exception), "teks kosong")

    def test_no_input_is_an_error(self):
        with self.assertRaises(SystemExit) as cm:
            tools.readability_main([])
        self.assertEqual(cm.exception.code, 2)

    def test_main_dispatches_readability(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.main(["readability", "--text", "Di sini."])
        self.assertEqual(code, 0)
        self.assertIn("Keterbacaan", buf.getvalue())

    def test_main_version_lists_readability(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.main(["--version"])
        self.assertEqual(code, 0)
        self.assertIn(f"readability {tools.READABILITY_VERSION}", buf.getvalue())
        self.assertIn(f"academic_tools.py {tools.__version__}", buf.getvalue())
        self.assertIn(f"cli {tools.CLI_VERSION}", buf.getvalue())


class TestReadabilityShim(unittest.TestCase):
    def test_shim_reexports_the_core(self):
        import readability
        self.assertIs(readability.readability_score,
                      tools.readability_score)
        self.assertIs(readability.readability_main,
                      tools.readability_main)
        self.assertIs(readability.format_readability,
                      tools.format_readability)
        self.assertEqual(readability.__version__,
                         tools.READABILITY_VERSION)
        for name in ("readability_score", "readability_main",
                     "format_readability"):
            self.assertIn(name, readability.__all__)


if __name__ == "__main__":
    unittest.main()
