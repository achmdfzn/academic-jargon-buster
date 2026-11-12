"""Tests for analyze_text_quality, the `analyze` subcommand, and its menu entry.

The engine combines jargon detection, citation audit, and DOI
verification into one quality score (0-100). Network is mocked: DOI
verification is either skipped (--no-verify) or patched.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools

SAMPLE_REFS = str(
    Path(__file__).resolve().parent.parent
    / "demos" / "citation-weaver" / "references.json"
)

TEXT = (
    "Metode penelitian ini memakai purposive sampling dan thematic analysis. "
    "Hasilnya sejalan dengan temuan sebelumnya [cite:devlin2019]."
)

STIFF_TEXT = (
    "Penelitian ini melakukan pengukuran terhadap suhu ruangan. Selain itu, "
    "penelitian ini melakukan analisis terhadap data yang diperoleh. "
    "Oleh karena itu, hasil yang diperoleh menunjukkan peningkatan. "
    "Dengan demikian, pengujian dilakukan dengan metode yang mana hasilnya "
    "ditunjukkan pada tabel. Selain itu, simulasi dilakukan dengan perangkat "
    "lunak. Sementara itu, data diperoleh dari pengujian. Oleh karena itu, "
    "grafik ditampilkan pada gambar."
)


class TestAnalyzeTextQuality(unittest.TestCase):
    def test_jargon_only_without_refs(self):
        out = tools.analyze_text_quality(
            "Penelitian ini memakai purposive sampling.")
        self.assertEqual([j["term"] for j in out["jargon"]],
                         ["purposive sampling"])
        self.assertIsNone(out["citations"])
        self.assertEqual(out["doi_verification"], {})
        self.assertEqual(out["quality_score"], 100)
        self.assertTrue(any("bibliografi" in r
                            for r in out["recommendations"]))

    def test_clean_text_scores_100(self):
        refs = tools.load_references(SAMPLE_REFS)
        out = tools.analyze_text_quality(TEXT, references=refs,
                                         verify_dois=False)
        self.assertEqual(out["citations"]["missing"], [])
        self.assertEqual(out["quality_score"], 100)

    def test_missing_citation_lowers_score(self):
        refs = tools.load_references(SAMPLE_REFS)
        out = tools.analyze_text_quality(
            "Lihat [cite:tidakada2020].", references=refs, verify_dois=False)
        self.assertIn("tidakada2020", out["citations"]["missing"])
        self.assertLess(out["quality_score"], 100)
        self.assertTrue(any("tidakada2020" in r
                            for r in out["recommendations"]))

    def test_doi_part_ignores_entries_without_doi(self):
        # Only devlin2019 carries a DOI in the sample; the other six
        # entries must not drag the DOI score down.
        fake = {
            "devlin2019": {"doi": "10.18653/v1/N19-1423", "crossref": "ok",
                           "openalex": "ok", "verdict": "ok"},
            "goodfellow2016": {"doi": "", "crossref": "no-doi",
                               "openalex": "no-doi", "verdict": "no-doi"},
        }
        refs = tools.load_references(SAMPLE_REFS)
        with patch.object(tools, "verify_reference_dois",
                          return_value=fake):
            out = tools.analyze_text_quality(TEXT, references=refs)
        self.assertEqual(out["doi_verification"], fake)
        self.assertEqual(out["quality_score"], 100)

    def test_recommendations_follow_lang(self):
        refs = tools.load_references(SAMPLE_REFS)
        out_id = tools.analyze_text_quality(
            "Lihat [cite:tidakada2020].", references=refs, verify_dois=False)
        out_en = tools.analyze_text_quality(
            "Lihat [cite:tidakada2020].", references=refs, lang="en",
            verify_dois=False)
        self.assertTrue(any("bibliografi" in r
                            for r in out_id["recommendations"]))
        self.assertTrue(any("bibliography" in r
                            for r in out_en["recommendations"]))
        self.assertFalse(any("bibliografi" in r
                             for r in out_en["recommendations"]))

    def test_format_analyze_renders_everything(self):
        refs = tools.load_references(SAMPLE_REFS)
        out = tools.analyze_text_quality(TEXT, references=refs,
                                         verify_dois=False)
        # format_analyze reads sys.stdout.encoding to pick Unicode or
        # ASCII bars; a StringIO has no encoding, so the Unicode path
        # is asserted deterministically on every platform (on a real
        # cp1252 console the ASCII path runs instead — see the test
        # below). Without this redirect the test fails on Windows CI,
        # where stdout is cp1252.
        buf = io.StringIO()
        with redirect_stdout(buf):
            text = tools.format_analyze(out, lang="id")
            en = tools.format_analyze(out, lang="en")
        self.assertIn("Skor kualitas: 100/100", text)
        self.assertIn("█" * 20, text)
        self.assertIn("Jargon     " + "█" * 20 + " 25/25", text)
        self.assertIn("purposive sampling", text)
        self.assertIn("Sitasi:", text)
        self.assertIn("Gaya: 25/25", text)
        self.assertIn("Rekomendasi:", text)
        self.assertIn("Quality score: 100/100", en)

    def test_format_analyze_ascii_bars_on_cp1252(self):
        """On a cp1252 console (Windows) the score card falls back
        to ASCII bars instead of Unicode blocks."""
        from unittest.mock import Mock
        out = tools.analyze_text_quality(TEXT, verify_dois=False)
        with patch.object(sys, "stdout", Mock(encoding="cp1252")):
            text = tools.format_analyze(out, lang="id")
        self.assertIn("#" * 20, text)
        self.assertNotIn("█", text)


class TestCheckStyle(unittest.TestCase):
    def test_clean_sample_texts_pass(self):
        base = Path(__file__).resolve().parent.parent
        for name in ("demos/citation-weaver/contoh_id.txt",
                     "demos/citation-weaver/example_en.txt",
                     "demos/jargon-buster/test_paper.txt"):
            out = tools.check_style((base / name).read_text(encoding="utf-8"))
            self.assertEqual(out["style_score"], 25, name)
            self.assertEqual(out["flagged"], [], name)

    def test_stiff_text_flags_all_five_signals(self):
        out = tools.check_style(STIFF_TEXT)
        self.assertEqual(out["style_score"], 0)
        self.assertEqual(out["flagged"], ["nominalization", "connectors",
                                          "passive", "yang_mana", "rhythm"])
        self.assertIn("melakukan pengukuran",
                      out["signals"]["nominalization"]["examples"])
        self.assertEqual(out["signals"]["yang_mana"]["count"], 1)

    def test_short_text_rhythm_is_neutral(self):
        out = tools.check_style("Penelitian memakai purposive sampling.")
        self.assertIsNone(out["signals"]["rhythm"]["same_length_share"])
        self.assertFalse(out["signals"]["rhythm"]["flagged"])

    def test_single_occurrence_does_not_flag_density_signals(self):
        out = tools.check_style(
            "Selain itu, penelitian memakai purposive sampling.")
        self.assertEqual(out["signals"]["connectors"]["count"], 1)
        self.assertFalse(out["signals"]["connectors"]["flagged"])

    def test_analyze_result_carries_style(self):
        refs = tools.load_references(SAMPLE_REFS)
        out = tools.analyze_text_quality(TEXT, references=refs,
                                         verify_dois=False)
        self.assertIn("style", out)
        self.assertEqual(out["style"]["style_score"], 25)
        self.assertEqual(out["quality_score"], 100)

    def test_stiff_text_scores_lower_with_style_recommendations(self):
        out = tools.analyze_text_quality(STIFF_TEXT, verify_dois=False)
        self.assertLess(out["quality_score"], 100)
        self.assertTrue(any("verba ringan" in r
                            for r in out["recommendations"]))
        self.assertTrue(any("yang mana" in r
                            for r in out["recommendations"]))

    def test_format_analyze_shows_style(self):
        out = tools.analyze_text_quality(STIFF_TEXT, verify_dois=False)
        # Same stdout-encoding redirect as above: without it this
        # test fails on Windows CI (cp1252 → ASCII bars).
        buf = io.StringIO()
        with redirect_stdout(buf):
            text = tools.format_analyze(out, lang="id")
        self.assertIn("Gaya: 0/25", text)
        self.assertIn("Gaya       " + "░" * 20 + "  0/25", text)
        self.assertIn("verba ringan", text)


class TestAnalyzeMain(unittest.TestCase):
    def test_text_json_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = tools.analyze_main([
                "--text", "Penelitian memakai purposive sampling.", "--json",
            ])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["quality_score"], 100)
        self.assertEqual([j["term"] for j in out["jargon"]],
                         ["purposive sampling"])

    def test_missing_citation_exits_1(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = tools.analyze_main([
                "--text", "Lihat [cite:tidakada2020].",
                "--refs", SAMPLE_REFS, "--no-verify",
            ])
        self.assertEqual(rc, 1)
        self.assertIn("tidakada2020", buf.getvalue())

    def test_file_input_and_readable_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "naskah.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(TEXT)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tools.analyze_main(
                    [path, "--refs", SAMPLE_REFS, "--no-verify"])
            self.assertEqual(rc, 0)
            self.assertIn("Skor kualitas: 100/100", buf.getvalue())
            self.assertIn("purposive sampling", buf.getvalue())

    def test_no_input_is_an_error(self):
        with self.assertRaises(SystemExit):
            tools.analyze_main([])


if __name__ == "__main__":
    unittest.main()
