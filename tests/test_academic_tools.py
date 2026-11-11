"""Tests for academic_tools.py — every feature in one file.

The old entry points (jargon_buster.py, citation_weaver.py,
academic_cli.py) are thin wrappers around this file, so these tests
check the single file directly, and that the wrappers still work.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_cli
import academic_tools as tools
import citation_weaver
import jargon_buster

REFS = tools.load_references(
    str(Path(__file__).resolve().parent.parent
        / "demos" / "citation-weaver" / "references.json")
)


class TestAcademicTools(unittest.TestCase):
    def test_one_file_holds_everything(self):
        self.assertEqual(tools.__version__, "1.1.1")
        self.assertEqual(len(tools.DICTIONARY), 22)
        self.assertEqual(len(tools.STYLES), 6)
        self.assertEqual(len(tools.DISCIPLINES), 21)
        for name in ("find_terms", "weave", "CLI", "jargon_main", "cite_main", "main"):
            self.assertTrue(hasattr(tools, name), f"missing {name}")

    def test_jargon_and_citation_work_from_the_one_file(self):
        found = {t["term"] for t in tools.find_terms(
            "System Usability Scale and gradient descent.")}
        self.assertIn("system usability scale", found)
        self.assertIn("gradient descent", found)
        out, _ = tools.weave(
            "Transformer [cite:vaswani2017].", REFS, style="ieee", lang="en")
        self.assertIn("[1]", out)

    def test_wrappers_reexport_the_same_implementation(self):
        self.assertIs(jargon_buster.find_terms, tools.find_terms)
        self.assertIs(citation_weaver.weave, tools.weave)
        self.assertIs(academic_cli.CLI, tools.CLI)
        self.assertIs(academic_cli.main, tools.main)
        self.assertEqual(jargon_buster.__version__, tools.JARGON_VERSION)
        self.assertEqual(citation_weaver.__version__, tools.CITATION_VERSION)

    def test_old_entry_points_still_run(self):
        self.assertEqual(jargon_buster.main(["--list-terms", "--field", "general"]), 0)
        self.assertEqual(citation_weaver.main(["--list-styles"]), 0)
        self.assertEqual(academic_cli.main(["--version"]), 0)


if __name__ == "__main__":
    unittest.main()
