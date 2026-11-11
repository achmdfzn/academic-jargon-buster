"""Structure guards: keep the repo, its docs, and its skills in sync.

These tests are cheap and deliberately boring. They exist because the
repo is documentation-heavy: counts and paths written by hand in README
and CHANGELOG drift away from the code, and the three SKILL.md files
repeat version numbers that live in academic_tools.py.

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""

import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import academic_tools


def read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def count_test_methods() -> int:
    """Number of test methods in tests/test_*.py, counted at runtime."""
    count = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        count += len(re.findall(r"^\s*def test_", text, flags=re.M))
    return count


class TestCoreStaysOneFile(unittest.TestCase):
    def test_core_imports_only_the_standard_library(self):
        tree = ast.parse(read_text("academic_tools.py"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                imported.add(node.module.split(".")[0])
        stdlib = getattr(sys, "stdlib_module_names", None)
        if stdlib is None:  # Python 3.9 has no stdlib_module_names
            stdlib = {"__future__", "argparse", "csv", "io", "json", "os",
                      "re", "sys", "urllib"}
        self.assertEqual(imported - set(stdlib), set())

    def test_shims_reexport_the_core(self):
        import academic_cli
        import citation_weaver
        import jargon_buster
        import skripsi_prompts

        self.assertIs(academic_cli.main, academic_tools.main)
        self.assertIs(jargon_buster.main, academic_tools.jargon_main)
        self.assertIs(citation_weaver.main, academic_tools.cite_main)
        self.assertIs(skripsi_prompts.main, academic_tools.prompts_main)
        self.assertEqual(jargon_buster.__version__, academic_tools.JARGON_VERSION)
        self.assertEqual(
            citation_weaver.__version__, academic_tools.CITATION_VERSION
        )
        self.assertEqual(skripsi_prompts.__version__, academic_tools.PROMPTS_VERSION)
        # Every public helper must be reachable through its shim, not
        # only through academic_tools (audit 2026-11-12: the lookup /
        # verify / analyze family was missing from the shims).
        for name in ("lookup_reference", "fetch_reference_by_doi",
                     "search_reference_by_title", "save_reference",
                     "reference_key", "verify_reference_dois",
                     "format_verification", "cite_main"):
            self.assertTrue(hasattr(citation_weaver, name), name)
            self.assertIn(name, citation_weaver.__all__)
        for name in ("analyze_text_quality", "format_analyze",
                     "format_banner", "analyze_main", "check_style"):
            self.assertTrue(hasattr(academic_cli, name), name)
            self.assertIn(name, academic_cli.__all__)
        self.assertIn("jargon_main", jargon_buster.__all__)
        self.assertIn("prompts_main", skripsi_prompts.__all__)


class TestDocsMatchTheRepo(unittest.TestCase):
    def test_readme_test_count_is_current(self):
        readme = read_text("README.md")
        self.assertIn(f"{count_test_methods()} tests", readme)

    def test_readme_version_is_current(self):
        self.assertIn(academic_tools.__version__, read_text("README.md"))

    def test_readme_counts_match_the_code(self):
        readme = read_text("README.md")
        self.assertIn(f"{len(academic_tools.DICTIONARY)} terms", readme)
        self.assertIn(f"{len(academic_tools.PROMPTS)} ready-made", readme)

    def test_documented_paths_exist(self):
        for rel in (
            "demos/jargon-buster/example_usage.py",
            "demos/jargon-buster/test_paper.txt",
            "demos/citation-weaver/example_usage.py",
            "demos/citation-weaver/references.json",
            "demos/citation-weaver/references.bib",
            "docs/standards/professional-standards.md",
            "docs/standards/verification-hierarchy.md",
            "docs/citation-weaver/jurusan.md",
            "docs/update-schedule.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_readme_paths_exist(self):
        for rel in re.findall(r"demos/[A-Za-z0-9._/-]+", read_text("README.md")):
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_demo_folders_mirror_the_tools(self):
        demo_dirs = {p.name for p in (ROOT / "demos").iterdir() if p.is_dir()}
        self.assertEqual(demo_dirs, {"jargon-buster", "citation-weaver"})


class TestSkillVersions(unittest.TestCase):
    def _frontmatter(self, rel_path: str) -> dict:
        text = read_text(rel_path)
        match = re.search(r"^---\n(.*?)\n---\n", text, flags=re.S)
        self.assertIsNotNone(match, rel_path)
        return dict(re.findall(r"^(\w+):\s*(.+)$", match.group(1), flags=re.M))

    def test_skill_versions_match_core_constants(self):
        expected = {
            "academic-jargon-buster": academic_tools.JARGON_VERSION,
            "citation-weaver": academic_tools.CITATION_VERSION,
            "skripsi-prompts": academic_tools.PROMPTS_VERSION,
        }
        for name, version in expected.items():
            meta = self._frontmatter(f"skills/research/{name}/SKILL.md")
            self.assertEqual(meta["version"], version, name)


if __name__ == "__main__":
    unittest.main()
