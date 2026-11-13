"""Audit #8 T-2: CLI `jargon` validates --field like the server.

Audit #8 H-3: the server answers 400 for an unknown field
(audit #7 N-8), but `jargon --text ... --field bogus` exited 0
with "No known jargon terms found" and `--list-terms --field
bogus` printed an empty list, exit 0. Both now raise the same
clean error as the server ("bidang tidak dikenal: bogus",
exit 1 via main()). A field a user added in dictionary.json
stays valid, like on the server.
"""
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import jargon_main


class TestAudit8CliJargonField(unittest.TestCase):
    """H-3: unknown --field is a clean error, not empty output."""

    def test_text_bogus_field_raises(self):
        with self.assertRaises(ValueError) as cm:
            jargon_main(["--text", "uji validitas", "--field", "bogus"])
        self.assertIn("bidang tidak dikenal: bogus", str(cm.exception))

    def test_list_terms_bogus_field_raises(self):
        with self.assertRaises(ValueError) as cm:
            jargon_main(["--list-terms", "--field", "bogus"])
        self.assertIn("bidang tidak dikenal: bogus", str(cm.exception))

    def test_csv_bogus_field_raises(self):
        with self.assertRaises(ValueError) as cm:
            jargon_main(["--text", "uji validitas", "--field", "bogus",
                         "--format", "csv"])
        self.assertIn("bidang tidak dikenal: bogus", str(cm.exception))

    def test_bogus_field_exit_code_1(self):
        # The real entry point: main() turns the ValueError
        # into a clean stderr message + exit 1, no traceback.
        proc = subprocess.run(
            [sys.executable, "academic_tools.py", "jargon",
             "--text", "uji validitas", "--field", "bogus"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("bidang tidak dikenal: bogus", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_valid_field_still_works(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = jargon_main(["--text", "uji validitas",
                                "--field", "research-methods"])
        self.assertEqual(code, 0)
        self.assertIn("uji validitas", buf.getvalue())

    def test_list_terms_valid_field(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = jargon_main(["--list-terms", "--field", "general"])
        self.assertEqual(code, 0)
        self.assertIn("peer review", buf.getvalue())

    def test_user_added_field_stays_valid(self):
        # A field that only exists in dictionary.json (patched
        # in here) must pass validation, like on the server.
        real = tools.load_dictionary()

        def merged():
            d = dict(real)
            d["istilah-baru"] = ("penjelasan baru", "bidang-baru",
                                 "user-added")
            return d

        with patch.object(tools, "load_dictionary", merged):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = jargon_main(["--text", "teks biasa",
                                    "--field", "bidang-baru"])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
