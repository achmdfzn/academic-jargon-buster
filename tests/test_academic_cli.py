"""Tests for academic_cli.py — the interactive menu wrapping both tools.

The menu is driven by input(), so tests feed scripted answers with
unittest.mock.patch and capture stdout. No real terminal needed.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
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
        code, out = run_cli(["3", "0"])
        self.assertEqual(code, 0)
        self.assertIn("Choose a tool", out)
        self.assertIn("Goodbye", out)

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
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = academic_cli.main(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("academic_cli", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
