"""Tests for RIS export (Citation Weaver v1.5.0)."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import academic_tools as tools


class TestRISExport(unittest.TestCase):
    def test_book_maps_to_book_with_publisher(self):
        out = tools.export_ris({
            "goodfellow2016": {
                "authors": ["Goodfellow, Ian", "Bengio, Yoshua", "Courville, Aaron"],
                "title": "Deep Learning",
                "type": "book",
                "venue": "MIT Press",
                "year": 2016,
            }
        })
        self.assertIn("TY  - BOOK", out)
        self.assertIn("ID  - goodfellow2016", out)
        self.assertIn("AU  - Goodfellow, Ian", out)
        self.assertIn("AU  - Bengio, Yoshua", out)
        self.assertIn("TI  - Deep Learning", out)
        self.assertIn("PB  - MIT Press", out)
        self.assertIn("PY  - 2016", out)
        self.assertIn("ER  -", out)

    def test_article_maps_to_jour_with_journal(self):
        out = tools.export_ris({
            "likert1932": {
                "authors": ["Likert, Rensis"],
                "title": "A technique for the measurement of attitudes",
                "type": "article",
                "venue": "Archives of Psychology, 22(140)",
                "year": 1932,
            }
        })
        self.assertIn("TY  - JOUR", out)
        self.assertIn("JO  - Archives of Psychology, 22(140)", out)

    def test_conference_with_arxiv_gets_arxiv_url(self):
        out = tools.export_ris({
            "vaswani2017": {
                "arxiv": "1706.03762",
                "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
                "title": "Attention Is All You Need",
                "type": "conference",
                "venue": "Advances in Neural Information Processing Systems 30",
                "year": 2017,
            }
        })
        self.assertIn("TY  - CONF", out)
        self.assertIn("T2  - Advances in Neural Information Processing Systems 30", out)
        self.assertIn("UR  - https://arxiv.org/abs/1706.03762", out)

    def test_chapter_splits_pages_from_venue(self):
        out = tools.export_ris({
            "brooke1996": {
                "authors": ["Brooke, John"],
                "title": "SUS: A 'quick and dirty' usability scale",
                "type": "chapter",
                "venue": "Usability Evaluation in Industry (Taylor & Francis), pp. 189-194",
                "year": 1996,
            }
        })
        self.assertIn("TY  - CHAP", out)
        self.assertIn("T2  - Usability Evaluation in Industry (Taylor & Francis)", out)
        self.assertIn("SP  - 189", out)
        self.assertIn("EP  - 194", out)

    def test_unknown_type_becomes_gen(self):
        out = tools.export_ris({
            "weird2020": {
                "authors": ["Doe, Jane"],
                "title": "Something odd",
                "type": "webpage",
                "venue": "example.com",
                "year": 2020,
            }
        })
        self.assertIn("TY  - GEN", out)
        self.assertIn("N1  - example.com", out)

    def test_doi_url_volume_and_issue(self):
        out = tools.export_ris({
            "devlin2019": {
                "authors": ["Devlin, Jacob"],
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "type": "article",
                "venue": "Journal of Testing",
                "volume": 19,
                "issue": 1,
                "pages": "1-15",
                "year": 2019,
                "doi": "10.18653/v1/N19-1423",
                "url": "https://example.org/bert",
            }
        })
        self.assertIn("VL  - 19", out)
        self.assertIn("IS  - 1", out)
        self.assertIn("SP  - 1", out)
        self.assertIn("EP  - 15", out)
        self.assertIn("DO  - 10.18653/v1/N19-1423", out)
        self.assertIn("UR  - https://example.org/bert", out)

    def test_pages_dashes_normalized(self):
        # '--', en dash and em dash all split like a plain '-'.
        self.assertEqual(tools._ris_pages("189--194"), ("189", "194"))
        self.assertEqual(tools._ris_pages("189–194"), ("189", "194"))
        self.assertEqual(tools._ris_pages("189—194"), ("189", "194"))
        self.assertEqual(tools._ris_pages("189-194"), ("189", "194"))

    def test_newlines_in_values_are_flattened(self):
        # A CR/LF inside a value must not inject a line break into
        # the RIS record (which would look like a new field).
        out = tools.export_ris({
            "aneh\n2020": {
                "authors": ["A\nB", "C\rD"],
                "title": "Judul\nbaris kedua",
                "type": "article",
                "venue": "Jurnal\r\nX",
                "doi": "10.1/x\r\ny",
                "url": "https://example.org/a\nb",
            }
        })
        self.assertIn("ID  - aneh 2020", out)
        self.assertIn("AU  - A B", out)
        self.assertIn("AU  - C D", out)
        self.assertIn("TI  - Judul baris kedua", out)
        self.assertIn("JO  - Jurnal  X", out)
        self.assertIn("DO  - 10.1/x  y", out)
        self.assertIn("UR  - https://example.org/a b", out)
        for line in out.splitlines():
            self.assertFalse(line.startswith("baris kedua"))
            self.assertFalse(line.startswith("y"))

    def test_entries_sorted_by_key_and_nothing_invented(self):
        out = tools.export_ris({
            "zebra2020": {"authors": ["Z, A"], "title": "Zed", "type": "book", "year": 2020},
            "apple2019": {"authors": ["A, B"], "title": "Aye", "type": "book", "year": 2019},
        })
        self.assertLess(out.index("ID  - apple2019"), out.index("ID  - zebra2020"))
        # No title line when the ref has no title: never invent one.
        self.assertNotIn("TI  - \n", out)
        out2 = tools.export_ris({
            "notitle2020": {"authors": ["N, O"], "type": "article", "year": 2020}
        })
        self.assertNotIn("TI  -", out2)

    def test_cli_exports_to_stdout_and_to_file(self):
        refs = {
            "goodfellow2016": {
                "authors": ["Goodfellow, Ian"],
                "title": "Deep Learning",
                "type": "book",
                "venue": "MIT Press",
                "year": 2016,
            }
        }
        with tempfile.TemporaryDirectory() as d:
            refs_path = os.path.join(d, "refs.json")
            with open(refs_path, "w", encoding="utf-8") as f:
                json.dump(refs, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tools.cite_main(["--refs", refs_path, "--export-ris"])
            self.assertEqual(rc, 0)
            self.assertIn("TY  - BOOK", buf.getvalue())
            out_path = os.path.join(d, "refs.ris")
            rc = tools.cite_main(["--refs", refs_path, "--export-ris", "--out", out_path])
            self.assertEqual(rc, 0)
            with open(out_path, encoding="utf-8") as f:
                self.assertIn("TY  - BOOK", f.read())

    def test_sample_bibliography_exports_all_seven(self):
        sample = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demos", "citation-weaver", "references.json",
        )
        refs = tools.load_references(sample)
        out = tools.export_ris(refs)
        for key in ("brooke1996", "brown2020", "devlin2019", "ferraiolo1992",
                    "goodfellow2016", "likert1932", "vaswani2017"):
            self.assertIn("ID  - " + key, out)
        self.assertEqual(out.count("TY  -"), 7)
        self.assertEqual(out.count("ER  -"), 7)


if __name__ == "__main__":
    unittest.main()


class TestRefTypeAliases(unittest.TestCase):
    """v1.25.2: raw Crossref types map to canonical record types."""

    def test_crossref_aliases_map_to_canonical_types(self):
        out = tools.export_ris({
            "a": {"title": "T", "type": "journal-article"},
            "b": {"title": "T", "type": "book-chapter"},
            "c": {"title": "T", "type": "proceedings-article"},
            "d": {"title": "T", "type": "dissertation"},
        })
        self.assertIn("TY  - JOUR", out)
        self.assertIn("TY  - CHAP", out)
        self.assertIn("TY  - CONF", out)
        self.assertIn("TY  - GEN", out)

    def test_export_bibtex_and_ris_together_is_rejected(self):
        # v1.25.2: the combination is an error (exit 2), not a
        # silent BibTeX win.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"a": {"title": "T", "type": "article"}}, f)
            with self.assertRaises(SystemExit) as cm:
                tools.cite_main(["--refs", path, "--export-bibtex",
                                 "--export-ris"])
        self.assertEqual(cm.exception.code, 2)
