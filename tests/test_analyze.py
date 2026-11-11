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
        text = tools.format_analyze(out, lang="id")
        self.assertIn("Skor kualitas: 100/100", text)
        self.assertIn("purposive sampling", text)
        self.assertIn("Sitasi:", text)
        self.assertIn("Rekomendasi:", text)
        en = tools.format_analyze(out, lang="en")
        self.assertIn("Quality score: 100/100", en)


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
