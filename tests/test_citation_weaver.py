"""Tests for citation-weaver (stdlib unittest, no dependencies).

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from citation_weaver import (
    DISCIPLINES,
    STYLES,
    format_reference,
    load_references,
    style_for_discipline,
    weave,
)

REFS = load_references(str(Path(__file__).resolve().parent.parent / "demos" / "citation-weaver" / "references.json"))


class TestCitationWeaver(unittest.TestCase):
    def test_sample_bibliography_is_real(self):
        self.assertIn("vaswani2017", REFS)
        self.assertEqual(REFS["vaswani2017"]["arxiv"], "1706.03762")
        self.assertEqual(REFS["vaswani2017"]["year"], 2017)

    def test_apa_in_text_and_bibliography(self):
        out, _ = weave("Attention changed NLP [cite:vaswani2017].", REFS, style="apa", lang="en")
        self.assertIn("(Vaswani et al., 2017)", out)
        self.assertIn("## References", out)
        self.assertIn("Vaswani, A., Shazeer, N.", out)
        self.assertIn("https://arxiv.org/abs/1706.03762", out)

    def test_ieee_numbering_in_order_of_appearance(self):
        text = "First BERT [cite:devlin2019], then Transformers [cite:vaswani2017]."
        out, _ = weave(text, REFS, style="ieee", lang="en")
        self.assertIn("[1]", out)
        self.assertIn("[2]", out)
        self.assertIn("[1] J. Devlin", out)  # Devlin first -> [1]
        self.assertIn("[2] A. Vaswani", out)

    def test_missing_citation_is_never_invented_id(self):
        out, _ = weave("Klaim [cite:tidak-ada2024].", REFS, style="apa", lang="id")
        self.assertIn("[PERLU RUJUKAN: tidak-ada2024]", out)
        self.assertIn("Daftar Pustaka", out)

    def test_missing_citation_is_never_invented_en(self):
        out, _ = weave("A claim [cite:does-not-exist2024].", REFS, style="apa", lang="en")
        self.assertIn("[REFERENCE NEEDED: does-not-exist2024]", out)
        self.assertIn("## References", out)

    def test_tex_cite_marker(self):
        out, _ = weave(r"Attention \cite{vaswani2017} changed NLP.", REFS, style="apa", lang="en")
        self.assertIn("(Vaswani et al., 2017)", out)
        self.assertNotIn("\\cite", out)

    def test_all_six_styles_format(self):
        for style in STYLES:
            entry = format_reference(REFS["vaswani2017"], style)
            self.assertIn("Attention Is All You Need", entry)
            self.assertIn("2017", entry)

    def test_vancouver_bibliography_numbered(self):
        out, _ = weave("X [cite:vaswani2017].", REFS, style="vancouver", lang="id")
        self.assertIn("[1] Vaswani A, Shazeer N", out)

    def test_jurusan_mapping_covers_all_disciplines(self):
        self.assertGreaterEqual(len(DISCIPLINES), 20)
        for d in DISCIPLINES:
            self.assertIn(d["style"], STYLES)
            self.assertIn(d["id"], [x["id"] for x in DISCIPLINES])

    def test_jurusan_recommendations(self):
        self.assertEqual(style_for_discipline("Kedokteran"), "vancouver")
        self.assertEqual(style_for_discipline("Medicine"), "vancouver")
        self.assertEqual(style_for_discipline("Psikologi"), "apa")
        self.assertEqual(style_for_discipline("Teknik Informatika"), "ieee")
        self.assertEqual(style_for_discipline("Sastra Inggris"), "mla")
        self.assertEqual(style_for_discipline("Hukum"), "chicago")
        self.assertEqual(style_for_discipline("Ekonomi"), "harvard")
        self.assertIsNone(style_for_discipline("Jurusan Tidak Ada"))

    def test_unknown_style_raises(self):
        with self.assertRaises(ValueError):
            weave("X [cite:vaswani2017].", REFS, style="tidak-ada", lang="id")


if __name__ == "__main__":
    unittest.main()
