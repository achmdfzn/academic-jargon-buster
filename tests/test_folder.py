"""Tests for folder-wide analysis (analyze_folder, v1.21.0)."""

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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import academic_tools as tools
from academic_tools import (
    analyze_folder,
    analyze_main,
    analyze_text_quality,
    format_folder_result,
    list_analyses,
)
from test_library import run_cli

GOOD = ("Penelitian ini menggunakan metode kualitatif dengan pendekatan "
        "studi kasus yang mendalam. Data dikumpulkan melalui wawancara "
        "semi terstruktur dengan dua belas informan yang dipilih secara "
        "purposive.")
SHARED = ("Penelitian ini menggunakan metode kualitatif dengan pendekatan "
          "studi kasus yang mendalam.")
OTHER = "Data dikumpulkan melalui wawancara semi terstruktur."


def _write(folder, name, text, mode="w"):
    path = os.path.join(folder, name)
    if mode == "w":
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(path, "wb") as f:
            f.write(text)
    return path


def _refs():
    return tools.load_references(tools.DEFAULT_REFS)


class TestAnalyzeFolder(unittest.TestCase):
    def test_three_files_sorted_with_average(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab2.md", GOOD)
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bab3.txt", OTHER)
            result = analyze_folder(tmp, _refs(), verify_dois=False)
            self.assertEqual(result["count"], 3)
            self.assertEqual([e["file"] for e in result["files"]],
                             ["bab1.txt", "bab2.md", "bab3.txt"])
            expected = [analyze_text_quality(t, _refs(),
                                verify_dois=False)["quality_score"]
                        for t in (GOOD, GOOD, OTHER)]
            self.assertEqual(
                [e["quality_score"] for e in result["files"]], expected)
            self.assertEqual(result["average"],
                             round(sum(expected) / len(expected), 1))
            text = format_folder_result(result)
            self.assertIn("Analisis folder", text)
            self.assertIn("bab1.txt", text)
            self.assertIn("Rata-rata", text)

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze_folder(tmp, _refs(), verify_dois=False)
            self.assertEqual(result["count"], 0)
            self.assertIsNone(result["average"])
            self.assertIn("Tidak ada file", format_folder_result(result))

    def test_ignores_other_files_and_subfolders(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "notes.pdf", GOOD)
            _write(tmp, "data.csv", GOOD)
            sub = os.path.join(tmp, "sub")
            os.mkdir(sub)
            _write(sub, "bab2.txt", GOOD)
            result = analyze_folder(tmp, _refs(), verify_dois=False)
            self.assertEqual([e["file"] for e in result["files"]],
                             ["bab1.txt"])

    def test_missing_citation_flags_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt",
                   "Penelitian ini memakai skala likert [cite:tidakada].")
            result = analyze_folder(tmp, _refs(), verify_dois=False)
            entry = result["files"][0]
            self.assertEqual(entry["citations_missing"], ["tidakada"])
            self.assertEqual(entry["quality_score"],
                             analyze_text_quality(
                                 "Penelitian ini memakai skala likert "
                                 "[cite:tidakada].",
                                 _refs(),
                                 verify_dois=False)["quality_score"])

    def test_unreadable_file_recorded_and_rest_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bad.txt", b"\xff\xfe bukan teks", mode="wb")
            result = analyze_folder(tmp, _refs(), verify_dois=False)
            self.assertEqual(result["count"], 2)
            bad = result["files"][1]
            self.assertEqual(bad["file"], "bad.txt")
            self.assertIsNotNone(bad["error"])
            self.assertIsNone(bad["quality_score"])
            self.assertIsNotNone(result["files"][0]["quality_score"])
            self.assertIn("Gagal: bad.txt", format_folder_result(result))

    def test_save_titles_are_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bab2.md", OTHER)
            db = os.path.join(tmp, "library.db")
            result = analyze_folder(tmp, _refs(), save=True, db=db,
                                verify_dois=False)
            self.assertEqual(
                sorted(e["library_id"] for e in result["files"]), [1, 2])
            self.assertEqual(
                sorted(a["title"] for a in list_analyses(db=db)),
                ["bab1.txt", "bab2.md"])

    def test_duplicates_across_files_when_saving(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", SHARED)
            _write(tmp, "bab2.txt", SHARED + " " + OTHER)
            db = os.path.join(tmp, "library.db")
            result = analyze_folder(tmp, _refs(), duplicates=True,
                                    save=True, db=db, verify_dois=False)
            by_file = {e["file"]: e for e in result["files"]}
            self.assertEqual(by_file["bab1.txt"]["duplicates"], 0)
            self.assertEqual(by_file["bab2.txt"]["duplicates"], 1)

    def test_empty_file_is_error_and_excluded_from_average(self):
        # B3: an empty file is recorded with an error (like an
        # unreadable file) and left out of the folder average.
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "kosong.txt", "")
            _write(tmp, "spasi.txt", "   \n  ")
            result = analyze_folder(tmp, _refs(), verify_dois=False)
            self.assertEqual(result["count"], 3)
            by_file = {e["file"]: e for e in result["files"]}
            good_score = analyze_text_quality(
                GOOD, _refs(), verify_dois=False)["quality_score"]
            for name in ("kosong.txt", "spasi.txt"):
                self.assertEqual(by_file[name]["error"], "teks kosong")
                self.assertIsNone(by_file[name]["quality_score"])
            self.assertEqual(result["average"], float(good_score))

    def test_duplicates_failure_still_saves(self):
        # A failing duplicates check is recorded, but the save still
        # runs — and the file is left out of the folder average.
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bab2.txt", OTHER)
            db = os.path.join(tmp, "library.db")
            with patch.object(tools, "find_duplicates",
                              side_effect=ValueError(
                                  "pustaka rusak: x — hapus atau ganti "
                                  "file databasenya")):
                result = analyze_folder(tmp, _refs(), duplicates=True,
                                        save=True, db=db,
                                        verify_dois=False)
            by_file = {e["file"]: e for e in result["files"]}
            for entry in by_file.values():
                self.assertIn("pustaka rusak", entry["error"])
                self.assertIsNotNone(entry["library_id"])
            # Both files errored, so there is no average at all.
            self.assertIsNone(result["average"])
            self.assertEqual(len(list_analyses(db=db)), 2)

    def test_save_failure_excluded_from_average(self):
        # A file whose save fails still has a score, but it is left
        # out of the folder average — one policy for every failure.
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bab2.txt", OTHER)
            db = os.path.join(tmp, "library.db")
            real_save = tools.save_analysis

            def _flaky(text, result, references, title=None, db=None):
                if title == "bab1.txt":
                    raise ValueError("gagal simpan")
                return real_save(text, result, references,
                                 title=title, db=db)

            with patch.object(tools, "save_analysis",
                              side_effect=_flaky):
                result = analyze_folder(tmp, _refs(), save=True, db=db,
                                        verify_dois=False)
            by_file = {e["file"]: e for e in result["files"]}
            other_score = analyze_text_quality(
                OTHER, _refs(), verify_dois=False)["quality_score"]
            self.assertEqual(by_file["bab1.txt"]["error"], "gagal simpan")
            self.assertIsNotNone(by_file["bab1.txt"]["quality_score"])
            self.assertIsNotNone(by_file["bab2.txt"]["library_id"])
            self.assertEqual(result["average"], float(other_score))


class TestAnalyzeFolderMain(unittest.TestCase):
    def test_cli_table_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bab2.txt", OTHER)
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([tmp, "--refs", tools.DEFAULT_REFS,
                                     "--no-verify"])
            self.assertEqual(code, 0)
            self.assertIn("bab1.txt", out.getvalue())
            self.assertIn("Rata-rata", out.getvalue())
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([tmp, "--refs", tools.DEFAULT_REFS,
                                     "--no-verify", "--json"])
            self.assertEqual(code, 0)
            parsed = json.loads(out.getvalue())
            self.assertEqual(parsed["count"], 2)
            self.assertEqual(parsed["files"][0]["file"], "bab1.txt")

    def test_cli_exit_1_on_missing_citation(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt",
                   "Penelitian ini memakai skala likert [cite:tidakada].")
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([tmp, "--refs", tools.DEFAULT_REFS,
                                     "--no-verify"])
            self.assertEqual(code, 1)

    def test_cli_empty_folder_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = analyze_main([tmp])
            self.assertEqual(code, 1)
            self.assertIn("Tidak ada file", err.getvalue())

    def test_cli_suggest_and_title_rejected_for_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            with self.assertRaises(SystemExit):
                analyze_main([tmp, "--suggest"])
            with self.assertRaises(SystemExit):
                analyze_main([tmp, "--title", "Bab 1"])
            with self.assertRaises(SystemExit):
                analyze_main([tmp, "--text", GOOD])

    def test_menu_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "bab1.txt", GOOD)
            _write(tmp, "bab2.txt", OTHER)
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}), \
                    patch("academic_tools.verify_reference_dois",
                          return_value={}):
                code, out = run_cli(["4", "3", tmp, "", "y", "", "0"])
            self.assertEqual(code, 0)
            self.assertIn("Analisis folder", out)
            self.assertIn("bab1.txt", out)
            self.assertEqual(len(list_analyses(db=db)), 2)


if __name__ == "__main__":
    unittest.main()
