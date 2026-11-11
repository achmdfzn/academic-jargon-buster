"""Tests for citation audit (Citation Weaver v1.3.0)."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import academic_tools as tools

REFS = {
    "vaswani2017": {
        "arxiv": "1706.03762",
        "authors": ["Vaswani, Ashish"],
        "title": "Attention Is All You Need",
        "type": "conference",
        "venue": "NeurIPS 30",
        "year": 2017,
    },
    "goodfellow2016": {
        "authors": ["Goodfellow, Ian"],
        "title": "Deep Learning",
        "type": "book",
        "venue": "MIT Press",
        "year": 2016,
    },
    "brooke1996": {
        "authors": ["Brooke, John"],
        "title": "SUS: A 'quick and dirty' usability scale",
        "type": "chapter",
        "venue": "Usability Evaluation in Industry",
        "year": 1996,
    },
}

TEXT = (
    "Transformers [cite:vaswani2017] changed the field, and "
    "deep learning \\cite{goodfellow2016} made it practical. "
    "But nobody cites [cite:tidakada2020] or [cite:vaswani2017] twice."
)


class TestCitationAudit(unittest.TestCase):
    def test_finds_missing_and_counts_repeats(self):
        result = tools.audit_citations(TEXT, REFS)
        self.assertEqual(result["cited"], ["vaswani2017", "goodfellow2016", "tidakada2020"])
        self.assertEqual(result["counts"]["vaswani2017"], 2)
        self.assertEqual(result["counts"]["goodfellow2016"], 1)
        self.assertEqual(result["missing"], ["tidakada2020"])

    def test_finds_unused_entries(self):
        result = tools.audit_citations(TEXT, REFS)
        self.assertEqual(result["unused"], ["brooke1996"])

    def test_clean_text_has_no_missing_or_unused(self):
        result = tools.audit_citations(
            "[cite:vaswani2017] [cite:goodfellow2016] [cite:brooke1996]",
            REFS,
        )
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["unused"], [])

    def test_both_marker_syntaxes(self):
        result = tools.audit_citations(
            r"[cite:vaswani2017] and \cite{goodfellow2016}", REFS
        )
        self.assertEqual(result["cited"], ["vaswani2017", "goodfellow2016"])

    def test_report_lists_missing_and_unused(self):
        result = tools.audit_citations(TEXT, REFS)
        report = tools.format_audit(result)
        self.assertIn("tidakada2020", report)
        self.assertIn("brooke1996", report)
        self.assertIn("Dikutip di naskah: 3", report)

    def test_cli_audit_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            refs_path = os.path.join(d, "refs.json")
            with open(refs_path, "w", encoding="utf-8") as f:
                json.dump(REFS, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tools.cite_main(["--refs", refs_path, "--audit", "--text", TEXT])
            self.assertEqual(rc, 1)  # missing citation found
            self.assertIn("tidakada2020", buf.getvalue())
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tools.cite_main([
                    "--refs", refs_path, "--audit", "--text",
                    "[cite:vaswani2017] [cite:goodfellow2016] [cite:brooke1996]",
                ])
            self.assertEqual(rc, 0)
            self.assertIn("Semua sitasi ada di bibliografi.", buf.getvalue())

    def test_check_links_reports_dead_doi(self):
        refs = {
            "alive2020": {
                "authors": ["A, B"], "title": "Alive", "type": "article",
                "venue": "Journal", "year": 2020, "doi": "10.1000/alive",
            },
            "dead2020": {
                "authors": ["C, D"], "title": "Dead", "type": "article",
                "venue": "Journal", "year": 2020, "doi": "10.9999/tidak-ada",
            },
        }

        class FakeResp:
            def __init__(self, status):
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(req, timeout=10):
            url = req.full_url
            if "10.1000/alive" in url:
                return FakeResp(200)
            raise tools.urllib.error.HTTPError(url, 404, "Not Found", None, None)

        with patch.object(tools.urllib.request, "urlopen", side_effect=fake_urlopen):
            links = tools.check_reference_links(refs)
        self.assertTrue(links["alive2020"][1])
        self.assertFalse(links["dead2020"][1])
        self.assertEqual(links["dead2020"][2], "HTTP 404")
        report = tools.format_audit(
            {"cited": ["alive2020", "dead2020"],
             "counts": {"alive2020": 1, "dead2020": 1},
             "missing": [], "unused": []},
            links=links,
        )
        self.assertIn("dead2020", report)
        self.assertIn("HTTP 404", report)


if __name__ == "__main__":
    unittest.main()
