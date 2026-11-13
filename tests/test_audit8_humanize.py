"""Audit #8 T-1: _apply_one must not capitalize after a degree dot.

The bug (B-1): _apply_one decided "sentence start" from the raw
character before the edit ("." means start), so a period inside a
degree capitalized the replacement:

    "Budi, M.Si. melakukan pengukuran ..." -> "Budi, M.Si. Mengukur ..."
    (preview AND --apply — the wrong text was written to the file)

The fix derives sentence-start from _sentence_spans, which knows
"M.Si." is mid-sentence. These seven cases pin the fix: the
replacement stays lowercase after a degree, and "Di sini" is
capital only when it really starts a sentence.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from academic_tools import (
    apply_suggestions,
    humanize_main,
    suggest_style_fixes,
)

# (input, fully applied text, per-suggestion "fixed" previews)
CASES = [
    ("Budi, M.Si. melakukan pengukuran terhadap suhu ruangan.",
     "Budi, M.Si. mengukur suhu ruangan.",
     ["Budi, M.Si. mengukur suhu ruangan."]),
    ("Tn. Hadi, S.Pd. melakukan pengujian terhadap sampel.",
     "Tn. Hadi, S.Pd. menguji sampel.",
     ["Tn. Hadi, S.Pd. menguji sampel."]),
    ("Budi, M.Si. disini melakukan pengukuran.",
     "Budi, M.Si. di sini mengukur.",
     ["Budi, M.Si. di sini melakukan pengukuran.",
      "Budi, M.Si. disini mengukur."]),
    ("Lihat hlm. 5. disini ia mencatat hasilnya.",
     "Lihat hlm. 5. Di sini ia mencatat hasilnya.",
     ["Di sini ia mencatat hasilnya."]),
    ("Dr. Budi melakukan pengukuran terhadap suhu ruangan.",
     "Dr. Budi mengukur suhu ruangan.",
     ["Dr. Budi mengukur suhu ruangan."]),
    ("Ia pergi. Disini ia mencatat hasilnya.",
     "Ia pergi. Di sini ia mencatat hasilnya.",
     ["Di sini ia mencatat hasilnya."]),
    ("Budi, S.Si. melakukan analisis terhadap data.",
     "Budi, S.Si. menganalisis data.",
     ["Budi, S.Si. menganalisis data."]),
]


class TestAudit8ApplyOneDegrees(unittest.TestCase):
    """T-1: capitalization after dotted degrees and titles."""

    def test_preview_fixed(self):
        for text, _want, fixeds in CASES:
            with self.subTest(text=text):
                result = suggest_style_fixes(text)
                got = [s["fixed"] for s in result["suggestions"]
                       if s["fixed"] is not None]
                self.assertEqual(got, fixeds)

    def test_apply_matches_preview(self):
        for text, want, _fixeds in CASES:
            with self.subTest(text=text):
                result = suggest_style_fixes(text)
                applied = apply_suggestions(text, result)["text"]
                self.assertEqual(applied, want)

    def test_no_wrong_capital_after_degree(self):
        # The regression itself: the verb after "M.Si." / "S.Pd." /
        # "S.Si." / "Dr." must never be capitalized by the fix.
        for text, _want, _fixeds in CASES:
            with self.subTest(text=text):
                result = suggest_style_fixes(text)
                applied = apply_suggestions(text, result)["text"]
                for bad in ("M.Si. Mengukur", "M.Si. Menganalisis",
                            "S.Pd. Menguji", "S.Si. Menganalisis",
                            "Dr. Mengukur"):
                    self.assertNotIn(bad, applied)

    def test_apply_cli_writes_lowercase(self):
        # End to end: `humanize --apply` writes the same lowercase
        # text to <file>.humanized.txt (the bug corrupted the
        # written file, not just the preview).
        text, want, _ = CASES[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tugas.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            code = humanize_main(["--apply", path])
            self.assertEqual(code, 1)  # suggestions exist, by design
            out_path = os.path.join(tmp, "tugas.humanized.txt")
            with open(out_path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), want)


if __name__ == "__main__":
    unittest.main()
