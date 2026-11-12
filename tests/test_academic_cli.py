"""Tests for academic_cli.py — the interactive menu wrapping all three tools.

The menu is driven by input(), so tests feed scripted answers with
unittest.mock.patch and capture stdout. No real terminal needed.
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_cli


def run_cli(answers):
    """Run the interactive menu with scripted input; return (code, output)."""
    buf = io.StringIO()
    with patch("builtins.input", side_effect=answers), redirect_stdout(buf):
        code = academic_cli.main([])
    return code, buf.getvalue()


class TestAcademicCli(unittest.TestCase):
    def test_exit_from_main_menu(self):
        code, out = run_cli(["0"])
        self.assertEqual(code, 0)
        self.assertIn("Academic Tools", out)

    def test_banner_is_a_box_with_version(self):
        import academic_tools as tools
        code, out = run_cli(["0"])
        self.assertEqual(code, 0)
        self.assertIn("Academic Tools", out)
        self.assertIn(f"v{tools.__version__}", out)
        self.assertIn(
            "Jargon Buster  ·  Citation Weaver  ·  Prompt Skripsi", out
        )
        self.assertIn("Satu file. Semua alat.", out)
        self.assertTrue(
            any(line.startswith(("  ╭", "  +"))
                for line in out.splitlines())
        )

    def test_menu_uses_dot_leaders(self):
        code, out = run_cli(["0"])
        self.assertEqual(code, 0)
        self.assertIn("Daftar isi:", out)
        self.assertRegex(out, r"Jargon Buster \.+ terjemahkan")
        self.assertRegex(out, r"Analisis Kualitas \.+ cek jargon")

    def test_ascii_fallback_and_color(self):
        import academic_tools as tools
        with patch.object(tools, "_unicode_ok", return_value=False):
            banner = tools.format_banner("id")
            self.assertTrue(banner.splitlines()[0].startswith("  +==="))
            self.assertNotIn("╭", banner)
            self.assertIn("#", tools._bar(21, 25))
        with patch.dict(os.environ, {"ACADEMIC_COLOR": "1"}):
            self.assertIn("\x1b[1m", tools.format_banner("id"))
        with patch.dict(os.environ, {"NO_COLOR": "1",
                                     "ACADEMIC_COLOR": "1"}):
            self.assertNotIn("\x1b[", tools.format_banner("id"))

    def test_english_banner_names_thesis_prompts(self):
        code, out = run_cli(["8", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Thesis Prompts", out)
        self.assertIn("type a number", out)

    def test_invalid_choice_reprompts_then_exits(self):
        code, out = run_cli(["99", "abc", "0"])
        self.assertEqual(code, 0)
        self.assertIn("tidak dikenal", out)  # invalid message (id UI)

    def test_jargon_annotate_typed_text(self):
        # 1=jargon, 1=annotate, 1=type text, text lines, ""=end, ""=all fields,
        # 1=markdown, ""=pause, 0=back, 0=exit
        code, out = run_cli([
            "1", "1", "1",
            "The renormalization group is a mathematical framework.", "",
            "", "1", "",
            "0", "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("renormalization group", out)
        self.assertIn("different scales", out)

    def test_jargon_list_terms(self):
        code, out = run_cli(["1", "2", "", "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("peer review", out)

    def test_cite_weave_typed_text_apa(self):
        # 2=cite, 1=weave, 1=type text, text, ""=end, ""=default refs,
        # 1=APA style, ""=output lang (id), ""=pause, 0=back, 0=exit
        code, out = run_cli([
            "2", "1", "1",
            "Transformer mengubah NLP [cite:vaswani2017].", "",
            "", "1", "", "",
            "0", "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("(Vaswani et al., 2017)", out)
        self.assertIn("Daftar Pustaka", out)

    def test_cite_weave_by_major_recommends_vancouver(self):
        # style menu: 7 = by major; major 1 = Kedokteran -> vancouver [1]
        code, out = run_cli([
            "2", "1", "1",
            "Transformer [cite:vaswani2017].", "",
            "", "7", "1", "", "",
            "0", "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("[1]", out)

    def test_cite_list_majors(self):
        code, out = run_cli(["2", "3", "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Kedokteran", out)
        self.assertIn("vancouver", out)

    def test_switch_language_to_english(self):
        code, out = run_cli(["8", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Contents", out)
        self.assertIn("Goodbye", out)

    def test_prompts_list_from_menu(self):
        code, out = run_cli(["3", "2", "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("roadmap", out)
        self.assertIn("jurnal", out)

    def test_prompts_fill_from_menu(self):
        # 3=prompts, 1=fill, 1=roadmap, then 5 field values, ""=pause,
        # 0=back, 0=exit
        code, out = run_cli([
            "3", "1", "1",
            "Sistem Informasi", "TAM", "kualitatif", "6", "11 November 2026",
            "",
            "0", "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Sistem Informasi", out)
        self.assertIn("ChatGPT", out)

    def test_cite_lookup_from_menu(self):
        import academic_tools as tools
        fake_ref = {"authors": ["LeCun, Yann"], "title": "Deep learning",
                    "type": "article", "venue": "Nature", "year": 2015,
                    "doi": "10.1038/nature14539"}
        with patch.object(tools, "lookup_reference", return_value=fake_ref):
            code, out = run_cli(["2", "4", "10.1038/nature14539", "", "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Deep learning", out)

    def test_cite_lookup_failure_from_menu(self):
        import academic_tools as tools
        with patch.object(tools, "lookup_reference",
                          side_effect=tools.LookupError("not found (HTTP 404)")):
            code, out = run_cli(["2", "4", "10.9999/tidak-ada", "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Pencarian gagal", out)

    def test_cite_verify_from_menu(self):
        import tempfile
        import os
        import academic_tools as tools
        fake_result = {
            "lecun2015": {"doi": "10.1038/nature14539", "crossref": "ok",
                          "openalex": "ok", "verdict": "ok"},
        }
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"lecun2015": {"title": "Deep learning", "doi": '
                        '"10.1038/nature14539"}}')
            with patch.object(tools, "verify_reference_dois",
                              return_value=fake_result):
                code, out = run_cli(["2", "7", path, "", "0", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Verifikasi DOI", out)
        self.assertIn("lecun2015", out)

    def test_analyze_from_menu(self):
        import academic_tools as tools
        fake_result = {
            "devlin2019": {"doi": "10.18653/v1/N19-1423", "crossref": "ok",
                           "openalex": "ok", "verdict": "ok"},
        }
        with patch.object(tools, "verify_reference_dois",
                          return_value=fake_result):
            # 4=analyze, 1=type text, text lines, ""=end, ""=refs (sample),
            # ""=skip saving to the library, ""=pause, 0=exit
            code, out = run_cli([
                "4", "1",
                "Metode memakai purposive sampling [cite:devlin2019].", "",
                "", "", "",
                "0",
            ])
        self.assertEqual(code, 0)
        self.assertIn("Skor kualitas", out)
        self.assertIn("purposive sampling", out)

    def test_passthrough_jargon_list_terms(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = academic_cli.main(["jargon", "--list-terms"])
        self.assertEqual(code, 0)
        self.assertIn("peer review", buf.getvalue())

    def test_passthrough_cite_list_styles(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = academic_cli.main(["cite", "--list-styles"])
        self.assertEqual(code, 0)
        self.assertIn("apa", buf.getvalue())
        self.assertIn("vancouver", buf.getvalue())

    def test_version_flag(self):
        import academic_tools as tools

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = academic_cli.main(["--version"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn(f"academic_tools.py {tools.__version__}", out)
        self.assertIn(f"cli {tools.CLI_VERSION}", out)
        self.assertIn(f"jargon_buster {tools.JARGON_VERSION}", out)
        self.assertIn(f"citation_weaver {tools.CITATION_VERSION}", out)
        self.assertIn(f"skripsi_prompts {tools.PROMPTS_VERSION}", out)
        self.assertIn(
            f"academic_quality_check {tools.QUALITY_VERSION}", out)

    def test_subcommand_version_flag(self):
        # A subcommand --version prints just "prog {__version__}":
        # the component list belongs to the top-level --version only.
        import academic_tools as tools

        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                academic_cli.main(["analyze", "--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertTrue(
            buf.getvalue().strip().endswith(tools.__version__))
        self.assertNotIn("jargon_buster", buf.getvalue())

    def test_main_empty_text_is_clean_exit_1(self):
        # A ValueError from a subcommand (empty text) is a plain
        # stderr message and exit 1 — never a traceback.
        err = io.StringIO()
        with redirect_stderr(err):
            code = academic_cli.main(
                ["analyze", "--text", "   ", "--no-verify"])
        self.assertEqual(code, 1)
        self.assertIn("teks kosong", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_main_bad_refs_json_is_clean_exit_1(self):
        # JSONDecodeError is a ValueError, so a malformed
        # bibliography file is the same clean exit 1.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{bukan json")
            err = io.StringIO()
            with redirect_stderr(err):
                code = academic_cli.main([
                    "analyze", "--text",
                    "Penelitian ini memakai purposive sampling.",
                    "--refs", path, "--no-verify"])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()
