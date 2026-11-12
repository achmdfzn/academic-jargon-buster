"""Tests for BibTeX export (Citation Weaver v1.2.0)."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import academic_tools as tools


class TestBibTeXExport(unittest.TestCase):
    def test_book_maps_to_book_with_publisher(self):
        out = tools.export_bibtex({
            "goodfellow2016": {
                "authors": ["Goodfellow, Ian", "Bengio, Yoshua", "Courville, Aaron"],
                "title": "Deep Learning",
                "type": "book",
                "venue": "MIT Press",
                "year": 2016,
            }
        })
        self.assertIn("@book{goodfellow2016,", out)
        self.assertIn("author = {Goodfellow, Ian and Bengio, Yoshua and Courville, Aaron},", out)
        self.assertIn("title = {Deep Learning},", out)
        self.assertIn("publisher = {MIT Press},", out)
        self.assertIn("year = {2016},", out)

    def test_article_maps_to_article_with_journal(self):
        out = tools.export_bibtex({
            "likert1932": {
                "authors": ["Likert, Rensis"],
                "title": "A technique for the measurement of attitudes",
                "type": "article",
                "venue": "Archives of Psychology, 22(140)",
                "year": 1932,
            }
        })
        self.assertIn("@article{likert1932,", out)
        self.assertIn("journal = {Archives of Psychology, 22(140)},", out)

    def test_conference_with_arxiv_gets_eprint(self):
        out = tools.export_bibtex({
            "vaswani2017": {
                "arxiv": "1706.03762",
                "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
                "title": "Attention Is All You Need",
                "type": "conference",
                "venue": "Advances in Neural Information Processing Systems 30",
                "year": 2017,
            }
        })
        self.assertIn("@inproceedings{vaswani2017,", out)
        self.assertIn("booktitle = {Advances in Neural Information Processing Systems 30},", out)
        self.assertIn("eprint = {1706.03762},", out)
        self.assertIn("archivePrefix = {arXiv},", out)

    def test_chapter_splits_pages_from_venue(self):
        out = tools.export_bibtex({
            "brooke1996": {
                "authors": ["Brooke, John"],
                "title": "SUS: A 'quick and dirty' usability scale",
                "type": "chapter",
                "venue": "Usability Evaluation in Industry (Taylor & Francis), pp. 189-194",
                "year": 1996,
            }
        })
        self.assertIn("@incollection{brooke1996,", out)
        self.assertIn(r"booktitle = {Usability Evaluation in Industry (Taylor \& Francis)},", out)
        self.assertIn("pages = {189--194},", out)

    def test_unknown_type_becomes_misc(self):
        out = tools.export_bibtex({
            "weird2020": {
                "authors": ["Doe, Jane"],
                "title": "Something odd",
                "type": "webpage",
                "venue": "example.com",
                "year": 2020,
            }
        })
        self.assertIn("@misc{weird2020,", out)
        self.assertIn("note = {example.com},", out)

    def test_latex_special_characters_are_escaped(self):
        out = tools.export_bibtex({
            "x2020": {
                "authors": ["A & B, C"],
                "title": "100% sure: costs $5 & under_score #1",
                "type": "article",
                "venue": "Journal of X",
                "year": 2020,
            }
        })
        self.assertIn(r"author = {A \& B, C},", out)
        self.assertIn(r"title = {100\% sure: costs \$5 \& under\_score \#1},", out)

    def test_newlines_in_values_are_flattened(self):
        # A CR/LF inside a value must not inject a line break into
        # the BibTeX record (which would break the entry).
        out = tools.export_bibtex({
            "aneh\n2020": {
                "authors": ["A\nB"],
                "title": "Judul\nbaris kedua",
                "type": "article",
                "venue": "Jurnal\r\nX",
                "doi": "10.1/x\r\ny",
            }
        })
        self.assertIn("@article{aneh 2020,", out)
        self.assertIn('author = {A B},', out)
        self.assertIn('title = {Judul baris kedua},', out)
        self.assertIn('journal = {Jurnal  X},', out)
        self.assertIn('doi = {10.1/x  y},', out)
        for line in out.splitlines():
            self.assertFalse(line.startswith("baris kedua"))
            self.assertFalse(line.startswith("y"))

    def test_entries_sorted_by_key_and_nothing_invented(self):
        out = tools.export_bibtex({
            "zebra2020": {"authors": ["Z, A"], "title": "Zed", "type": "book", "year": 2020},
            "apple2019": {"authors": ["A, B"], "title": "Aye", "type": "book", "year": 2019},
        })
        self.assertLess(out.index("@book{apple2019,"), out.index("@book{zebra2020,"))
        # No title field when the ref has no title: never invent one.
        self.assertNotIn("title = {}", out)
        out2 = tools.export_bibtex({
            "notitle2020": {"authors": ["N, O"], "type": "article", "year": 2020}
        })
        self.assertNotIn("title = {", out2)

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
                rc = tools.cite_main(["--refs", refs_path, "--export-bibtex"])
            self.assertEqual(rc, 0)
            self.assertIn("@book{goodfellow2016,", buf.getvalue())
            out_path = os.path.join(d, "refs.bib")
            rc = tools.cite_main(["--refs", refs_path, "--export-bibtex", "--out", out_path])
            self.assertEqual(rc, 0)
            with open(out_path, encoding="utf-8") as f:
                self.assertIn("@book{goodfellow2016,", f.read())

    def test_sample_bibliography_exports_all_seven(self):
        sample = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demos", "citation-weaver", "references.json",
        )
        refs = tools.load_references(sample)
        out = tools.export_bibtex(refs)
        for key in ("brooke1996", "brown2020", "devlin2019", "ferraiolo1992",
                    "goodfellow2016", "likert1932", "vaswani2017"):
            self.assertIn("@", out)
            self.assertIn("{" + key + ",", out)
        self.assertEqual(out.count("@"), 7)


if __name__ == "__main__":
    unittest.main()


class TestRefTypeAliases(unittest.TestCase):
    """v1.25.2: raw Crossref types map to canonical entry types."""

    def test_crossref_aliases_map_to_canonical_types(self):
        out = tools.export_bibtex({
            "a": {"title": "T", "type": "journal-article"},
            "b": {"title": "T", "type": "book-chapter"},
            "c": {"title": "T", "type": "proceedings-article"},
            "d": {"title": "T", "type": "report"},
        })
        self.assertIn("@article{a,", out)
        self.assertIn("@incollection{b,", out)
        self.assertIn("@inproceedings{c,", out)
        self.assertIn("@misc{d,", out)

    def test_doi_url_eprint_are_latex_escaped(self):
        out = tools.export_bibtex({
            "a": {"title": "T", "type": "article",
                  "doi": "10.1/a_b%c", "url": "https://x.example/a_b",
                  "arxiv": "2301.00001_v2"},
        })
        self.assertIn("doi = {10.1/a\\_b\\%c}", out)
        self.assertIn("url = {https://x.example/a\\_b}", out)
        self.assertIn("eprint = {2301.00001\\_v2}", out)
