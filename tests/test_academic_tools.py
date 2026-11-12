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
import skripsi_prompts

REFS = tools.load_references(
    str(Path(__file__).resolve().parent.parent
        / "demos" / "citation-weaver" / "references.json")
)


class TestAcademicTools(unittest.TestCase):
    def test_one_file_holds_everything(self):
        self.assertRegex(tools.__version__, r"^\d+\.\d+\.\d+$")
        self.assertEqual(len(tools.DICTIONARY), 72)
        self.assertEqual(len(tools.STYLES), 6)
        self.assertEqual(len(tools.DISCIPLINES), 21)
        self.assertEqual(len(tools.PROMPTS), 18)
        for name in ("find_terms", "weave", "fill_prompt", "lookup_reference",
                     "fetch_reference_by_doi", "search_reference_by_title",
                     "save_reference", "CLI",
                     "jargon_main", "cite_main", "prompts_main", "main"):
            self.assertTrue(hasattr(tools, name), f"missing {name}")

    def test_new_research_methods_terms_have_real_sources(self):
        # Added 2026-11-11; every source was verified the same day
        # (Crossref/OpenAlex/web). A term without a real source is a bug.
        expected = {
            "validity": "Creswell & Creswell 2018",
            "validitas": "Creswell & Creswell 2018",
            "reliability": "Creswell & Creswell 2018",
            "reliabilitas": "Creswell & Creswell 2018",
            "triangulation": "Denzin 1978",
            "triangulasi": "Denzin 1978",
            "purposive sampling": "Patton 2015",
            "thematic analysis": "Braun & Clarke 2006",
            "operational definition": "Creswell & Creswell 2018",
            "literature review": "Boote & Beile 2005",
            # Added 2026-11-13 (9 more methods terms).
            "data saturation": "Glaser & Strauss 1967",
            "saturasi data": "Glaser & Strauss 1967",
            "case study": "Yin 2018",
            "studi kasus": "Yin 2018",
            "phenomenology": "Moustakas 1994",
            "fenomenologi": "Moustakas 1994",
            "focus group discussion": "Krueger & Casey 2014",
            "uji validitas": "Creswell & Creswell 2018",
            "uji reliabilitas": "Creswell & Creswell 2018",
        }
        for term, source in expected.items():
            self.assertIn(term, tools.DICTIONARY, f"missing term: {term}")
            explanation, field, real_source = tools.DICTIONARY[term]
            self.assertTrue(explanation, f"{term}: empty explanation")
            self.assertEqual(field, "research-methods", f"{term}: wrong field")
            self.assertIn(source, real_source, f"{term}: source mismatch")

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
        self.assertEqual(skripsi_prompts.__version__, tools.PROMPTS_VERSION)

    def test_old_entry_points_still_run(self):
        self.assertEqual(jargon_buster.main(["--list-terms", "--field", "general"]), 0)
        self.assertEqual(citation_weaver.main(["--list-styles"]), 0)
        self.assertEqual(skripsi_prompts.main(["--list"]), 0)
        self.assertEqual(academic_cli.main(["--version"]), 0)


if __name__ == "__main__":
    unittest.main()
