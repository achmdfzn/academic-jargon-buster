"""Tests for the sqlite3 library: analysis history + personal bibliography.

Every test uses a temporary database file (via --db or the
ACADEMIC_LIBRARY_DB env var); nothing touches the real
~/.academic-tools/library.db.
"""

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_cli
import academic_tools as tools
from academic_tools import (
    analyze_main, export_references, format_analysis_detail,
    format_history, format_references, get_analysis, import_references,
    library_main, list_analyses, list_references, save_analysis,
    search_references,
)

TEXT = ("Penelitian ini melakukan pengukuran terhadap kepuasan pengguna "
        "[cite:devlin2019].")
SAMPLE_REFS = {
    "devlin2019": {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "authors": ["Devlin, Jacob"], "year": 2019,
        "doi": "10.18653/v1/N19-1423", "type": "inproceedings"},
    "brooke1996": {
        "title": "SUS - A quick and dirty usability scale",
        "authors": ["Brooke, John"], "year": 1996, "type": "book"},
}


def run_cli(answers):
    """Run the interactive menu with scripted input; return (code, output)."""
    buf = io.StringIO()
    with patch("builtins.input", side_effect=answers), redirect_stdout(buf):
        code = academic_cli.main([])
    return code, buf.getvalue()


class LibraryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "library.db")
        self.refs_path = os.path.join(self.tmp.name, "refs.json")
        with open(self.refs_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_REFS, f)

    def tearDown(self):
        self.tmp.cleanup()

    def _result(self):
        return tools.analyze_text_quality(
            TEXT, SAMPLE_REFS, lang="id", verify_dois=False)

    def test_save_and_list_round_trip(self):
        first = save_analysis(TEXT, self._result(), SAMPLE_REFS,
                              title="Bab 1", db=self.db)
        second = save_analysis(TEXT, self._result(), SAMPLE_REFS, db=self.db)
        self.assertEqual((first, second), (1, 2))
        rows = list_analyses(db=self.db)
        self.assertEqual([r["id"] for r in rows], [2, 1])  # newest first
        self.assertEqual(rows[1]["title"], "Bab 1")
        self.assertEqual(rows[1]["quality_score"], 100)
        self.assertEqual(rows[1]["jargon_count"], 0)
        self.assertEqual(rows[1]["citations_missing"], 0)
        self.assertEqual(rows[1]["doi_ok"], 0)  # no verify, no DOI checked
        # No title given: the first line of the text is the title.
        self.assertTrue(rows[0]["title"].startswith("Penelitian ini"))

    def test_get_analysis_has_hash_text_and_refs(self):
        save_analysis(TEXT, self._result(), SAMPLE_REFS, db=self.db)
        got = get_analysis(1, db=self.db)
        self.assertEqual(got["text"], TEXT)
        self.assertEqual(
            got["text_hash"],
            hashlib.sha256(TEXT.encode("utf-8")).hexdigest())
        self.assertEqual(got["references"], ["devlin2019"])
        self.assertIsNone(get_analysis(99, db=self.db))

    def test_search_by_title_author_doi_and_key(self):
        import_references(SAMPLE_REFS, db=self.db)
        self.assertEqual([r["key"] for r in search_references("BERT", db=self.db)],
                         ["devlin2019"])
        self.assertEqual([r["key"] for r in search_references("Brooke", db=self.db)],
                         ["brooke1996"])
        self.assertEqual(
            [r["key"] for r in search_references("10.18653", db=self.db)],
            ["devlin2019"])
        self.assertEqual(
            [r["key"] for r in search_references("devlin", db=self.db)],
            ["devlin2019"])
        self.assertEqual(search_references("tidak ada", db=self.db), [])

    def test_import_export_round_trip(self):
        counts = import_references(SAMPLE_REFS, db=self.db)
        self.assertEqual(counts, {"added": 2, "updated": 0})
        changed = dict(SAMPLE_REFS)
        changed["brooke1996"] = dict(SAMPLE_REFS["brooke1996"])
        changed["brooke1996"]["title"] = "SUS — A Quick and Dirty Usability Scale"
        counts = import_references(changed, db=self.db)
        self.assertEqual(counts, {"added": 0, "updated": 2})
        exported = export_references(db=self.db)
        self.assertEqual(exported["brooke1996"]["title"],
                         "SUS — A Quick and Dirty Usability Scale")
        self.assertEqual(len(list_references(db=self.db)), 2)

    def test_analyze_main_save(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = analyze_main(["--text", TEXT, "--refs", self.refs_path,
                                 "--no-verify", "--save", "--title", "Bab 1",
                                 "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("Tersimpan di pustaka (id 1)", buf.getvalue())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = analyze_main(["--text", TEXT, "--refs", self.refs_path,
                                 "--no-verify", "--save", "--json",
                                 "--db", self.db])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["library_id"], 2)
        self.assertEqual(len(list_analyses(db=self.db)), 2)

    def test_library_main_history_show_refs_search(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--history", "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("Belum ada riwayat", buf.getvalue())

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--import", self.refs_path,
                                 "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("Ditambahkan: 2, diperbarui: 0", buf.getvalue())

        save_analysis(TEXT, self._result(), SAMPLE_REFS, db=self.db)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--history", "--json", "--db", self.db])
        self.assertEqual(code, 0)
        rows = json.loads(buf.getvalue())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quality_score"], 100)

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--show", "1", "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("Analisis #1", buf.getvalue())
        self.assertIn(TEXT, buf.getvalue())

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--search", "BERT", "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("devlin2019", buf.getvalue())

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--refs", "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("brooke1996", buf.getvalue())

    def test_library_main_show_missing_is_error(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--show", "99", "--db", self.db])
        self.assertEqual(code, 1)

    def test_library_main_export(self):
        import_references(SAMPLE_REFS, db=self.db)
        out = os.path.join(self.tmp.name, "out.json")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = library_main(["--export", out, "--db", self.db])
        self.assertEqual(code, 0)
        self.assertIn("Diekspor: 2 referensi", buf.getvalue())
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f), SAMPLE_REFS)

    def test_format_helpers(self):
        self.assertIn("Belum ada riwayat", format_history([]))
        self.assertIn("Tidak ada referensi", format_references([]))
        save_analysis(TEXT, self._result(), SAMPLE_REFS, db=self.db)
        self.assertIn("#1", format_history(list_analyses(db=self.db)))
        self.assertIn("Analisis #1",
                      format_analysis_detail(get_analysis(1, db=self.db)))

    def test_menu_library_history_empty(self):
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": self.db}):
            code, out = run_cli(["6", "1", "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Belum ada riwayat", out)

    def test_menu_library_history_and_detail(self):
        save_analysis(TEXT, self._result(), SAMPLE_REFS, db=self.db)
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": self.db}):
            code, out = run_cli(["6", "1", "", "0", "0"])
            self.assertEqual(code, 0)
            self.assertIn("Riwayat analisis", out)
            self.assertIn("#1", out)
            code, out = run_cli(["6", "2", "1", "", "0", "0"])
            self.assertEqual(code, 0)
            self.assertIn("Analisis #1", out)
            self.assertIn(TEXT, out)
            code, out = run_cli(["6", "3", "BERT", "", "0", "0"])
            self.assertEqual(code, 0)
            self.assertIn("devlin2019", out)

    def test_menu_analyze_save_prompt(self):
        refs = tools.load_references(tools.DEFAULT_REFS)
        canned = tools.analyze_text_quality(
            TEXT, refs, lang="id", verify_dois=False)
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": self.db}), \
                patch("academic_tools.analyze_text_quality",
                      return_value=canned):
            code, out = run_cli(["4", "1", TEXT, "", "", "y", "", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Tersimpan di pustaka: #1", out)
        self.assertEqual(len(list_analyses(db=self.db)), 1)

    def test_menu_analyze_skip_save(self):
        refs = tools.load_references(tools.DEFAULT_REFS)
        canned = tools.analyze_text_quality(
            TEXT, refs, lang="id", verify_dois=False)
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": self.db}), \
                patch("academic_tools.analyze_text_quality",
                      return_value=canned):
            code, out = run_cli(["4", "1", TEXT, "", "", "", "", "0"])
        self.assertEqual(code, 0)
        self.assertEqual(list_analyses(db=self.db), [])

    def test_corrupt_db_history_is_clean_error(self):
        corrupt = os.path.join(self.tmp.name, "corrupt.db")
        with open(corrupt, "wb") as f:
            f.write(b"bukan sqlite")
        err = io.StringIO()
        with redirect_stderr(err):
            code = library_main(["--history", "--db", corrupt])
        self.assertEqual(code, 1)
        self.assertIn("pustaka rusak", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_corrupt_db_analyze_save_is_clean_error(self):
        corrupt = os.path.join(self.tmp.name, "corrupt.db")
        with open(corrupt, "wb") as f:
            f.write(b"bukan sqlite")
        err = io.StringIO()
        with redirect_stderr(err):
            code = analyze_main([
                "--text", TEXT, "--refs", self.refs_path,
                "--no-verify", "--save", "--db", corrupt])
        self.assertEqual(code, 1)
        self.assertIn("pustaka rusak", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()
