"""Tests for the Tata tulis typo pattern in Humanize (v1.20.0).

The table holds only always-wrong fused forms, so every fix is
mechanical: suggest_style_fixes proposes it and --apply applies it.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    analyze_main,
    apply_suggestions,
    suggest_style_fixes,
)


def _typo_suggestions(text):
    result = suggest_style_fixes(text, limit=None)
    return [s for s in result["suggestions"] if s["pattern"] == "typo"]


class TestTypoTable(unittest.TestCase):
    def test_table_shape(self):
        table = tools._TYPO_TABLE
        self.assertEqual(len(table), 41)
        for fused, fixed in table.items():
            self.assertEqual(fused, fused.lower())
            self.assertTrue(fused.isalpha(), fused)
            self.assertTrue(" " in fixed or "-" in fixed, fixed)
        self.assertEqual(len(set(table.values())), len(table))

    def test_every_entry_is_fixed(self):
        for fused, fixed in tools._TYPO_TABLE.items():
            with self.subTest(fused=fused):
                text = f"Kalimat ini memakai kata {fused} di tengah."
                found = _typo_suggestions(text)
                self.assertEqual(len(found), 1, text)
                self.assertEqual(found[0]["original"], fused)
                self.assertEqual(found[0]["replacement"], fixed)
                self.assertIn(fixed, found[0]["fixed"])

    def test_sentence_initial_is_capitalized(self):
        text = "Disini penelitian dilakukan dengan teliti."
        found = _typo_suggestions(text)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["original"], "Disini")
        self.assertEqual(found[0]["replacement"], "di sini")
        self.assertEqual(found[0]["fixed"],
                         "Di sini penelitian dilakukan dengan teliti.")

    def test_no_false_positives(self):
        # Fused "di"+verb is correct Indonesian; "dimana" is guidance,
        # not a mechanical typo fix.
        text = ("Penelitian ini ditulis di rumah sakit dan dibaca di "
                "perpustakaan. Kota dimana ia tinggal cukup jauh.")
        self.assertEqual(_typo_suggestions(text), [])
        result = suggest_style_fixes(text, limit=None)
        self.assertTrue(any(s["pattern"] == "yang_mana"
                            for s in result["suggestions"]))

    def test_nya_forms_use_their_own_entry(self):
        found = _typo_suggestions(
            "Kerjasamanya dengan tim berjalan baik.")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["replacement"], "kerja samanya")
        found = _typo_suggestions("Didalamnya ada tiga ruangan.")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["replacement"], "di dalamnya")


class TestTypoApply(unittest.TestCase):
    def test_apply_fixes_typos_and_is_idempotent(self):
        text = ("Disini data dikumpulkan. Penelitian dilakukan didalam "
                "laboratorium. Terimakasih atas bantuannya.")
        result = suggest_style_fixes(text, limit=None)
        applied = apply_suggestions(text, result)
        self.assertEqual(
            applied["text"],
            "Di sini data dikumpulkan. Penelitian dilakukan di dalam "
            "laboratorium. Terima kasih atas bantuannya.")
        self.assertEqual(len(applied["applied"]), 3)
        again = apply_suggestions(
            applied["text"],
            suggest_style_fixes(applied["text"], limit=None))
        self.assertEqual(len(again["applied"]), 0)
        self.assertEqual(again["text"], applied["text"])


class TestTypoInAnalyze(unittest.TestCase):
    def test_analyze_suggest_shows_typos(self):
        text = "Penelitian dilakukan disini dengan metode kualitatif."
        out = io.StringIO()
        with redirect_stdout(out):
            code = analyze_main(["--text", text, "--no-verify",
                                 "--suggest"])
        self.assertEqual(code, 0)
        self.assertIn("Ejaan", out.getvalue())
        self.assertIn("di sini", out.getvalue())


if __name__ == "__main__":
    unittest.main()
