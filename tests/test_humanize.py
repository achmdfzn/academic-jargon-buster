"""Tests for style rewrite suggestions (Opsi B): suggest_style_fixes(),
format_suggestions(), the `humanize` subcommand, and analyze --suggest.

The suggestions are advisory before/after pairs — nothing is applied
silently. Mechanical replacements cover light verbs, connectors, and
"yang mana"; passive voice, "dimana", rhythm, and unknown light verbs
get guidance instead of a made-up rewrite.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import academic_tools as tools
from academic_tools import (
    analyze_text_quality,
    format_suggestions,
    humanize_main,
    suggest_style_fixes,
)

from test_academic_cli import run_cli  # reuse the menu harness


STIFF = (
    "Penelitian ini melakukan pengukuran terhadap suhu ruangan. "
    "Selain itu, penelitian ini melakukan analisis terhadap data yang diperoleh. "
    "Oleh karena itu, hasil yang diperoleh menunjukkan peningkatan. "
    "Dengan demikian, pengujian dilakukan dengan metode yang mana hasilnya "
    "ditunjukkan pada tabel. "
    "Selain itu, simulasi dilakukan dengan perangkat lunak. "
    "Sementara itu, data diperoleh dari pengujian. "
    "Oleh karena itu, grafik ditampilkan pada gambar."
)


class TestSuggestStyleFixes(unittest.TestCase):
    def test_light_verb_replacement(self):
        result = suggest_style_fixes(
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.")
        self.assertEqual(result["count"], 1)
        sug = result["suggestions"][0]
        self.assertEqual(sug["pattern"], "nominalization")
        self.assertEqual(sug["original"], "melakukan pengukuran terhadap")
        self.assertEqual(sug["replacement"], "mengukur")
        self.assertEqual(sug["fixed"],
                         "Penelitian ini mengukur suhu ruangan.")

    def test_light_verb_sebesar_dropped(self):
        result = suggest_style_fixes("Suhu mengalami peningkatan sebesar 12%.")
        self.assertEqual(result["count"], 1)
        sug = result["suggestions"][0]
        self.assertEqual(sug["replacement"], "naik")
        self.assertEqual(sug["fixed"], "Suhu naik 12%.")

    def test_light_verb_untuk_not_dropped(self):
        # "pengujian untuk validasi" must NOT become "menguji validasi".
        result = suggest_style_fixes(
            "Penelitian ini melakukan pengujian untuk validasi model.")
        sug = result["suggestions"][0]
        self.assertEqual(sug["replacement"], "menguji")
        self.assertEqual(sug["fixed"],
                         "Penelitian ini menguji untuk validasi model.")

    def test_unknown_light_verb_is_guidance_only(self):
        result = suggest_style_fixes(
            "Penelitian ini melakukan kunjungan ke lokasi.")
        self.assertEqual(result["count"], 1)
        sug = result["suggestions"][0]
        self.assertIsNone(sug["replacement"])
        self.assertIsNone(sug["fixed"])
        self.assertIn("kata kerja langsung", sug["note"])

    def test_connector_removal_capitalizes(self):
        result = suggest_style_fixes(
            "Selain itu, penelitian memakai purposive sampling.")
        self.assertEqual(result["count"], 1)
        sug = result["suggestions"][0]
        self.assertEqual(sug["pattern"], "connectors")
        self.assertEqual(sug["replacement"], "")
        self.assertEqual(sug["fixed"],
                         "Penelitian memakai purposive sampling.")

    def test_yang_mana_splits_sentence(self):
        result = suggest_style_fixes(
            "Sistem menggunakan pendingin alami, yang mana hal ini "
            "mengurangi konsumsi.")
        sug = result["suggestions"][0]
        self.assertEqual(sug["pattern"], "yang_mana")
        self.assertEqual(sug["replacement"], ".")
        self.assertEqual(sug["fixed"],
                         "Sistem menggunakan pendingin alami. "
                         "Hal ini mengurangi konsumsi.")

    def test_yang_mana_without_comma(self):
        result = suggest_style_fixes(
            "Pengujian dilakukan dengan metode yang mana hasilnya "
            "ditunjukkan pada tabel.")
        sug = [s for s in result["suggestions"]
               if s["pattern"] == "yang_mana"][0]
        self.assertEqual(sug["fixed"],
                         "Pengujian dilakukan dengan metode. "
                         "Hasilnya ditunjukkan pada tabel.")

    def test_dimana_is_guidance_only(self):
        result = suggest_style_fixes(
            "Pengujian dilakukan pada suhu 85°C, dimana nilai CHF "
            "mulai teramati.")
        sug = [s for s in result["suggestions"]
               if s["pattern"] == "yang_mana"][0]
        self.assertEqual(sug["original"], "dimana")
        self.assertIsNone(sug["replacement"])

    def test_passive_is_guidance_only(self):
        result = suggest_style_fixes(
            "Simulasi dilakukan dengan perangkat lunak.")
        sug = [s for s in result["suggestions"]
               if s["pattern"] == "passive"][0]
        self.assertEqual(sug["original"], "dilakukan")
        self.assertIsNone(sug["replacement"])
        self.assertIn("aktif", sug["note"])

    def test_rhythm_suggestion_only_when_flagged(self):
        result = suggest_style_fixes(STIFF)
        patterns = [s["pattern"] for s in result["suggestions"]]
        self.assertIn("rhythm", patterns)
        clean = suggest_style_fixes(
            "Penelitian memakai purposive sampling.")
        self.assertEqual(clean["count"], 0)

    def test_clean_text_has_no_suggestions(self):
        # Active verbs only: "dianalisis" would be a passive hit.
        result = suggest_style_fixes(
            "Penelitian memakai purposive sampling. Peneliti menghitung "
            "korelasi dengan regresi linear.")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["suggestions"], [])

    def test_suggestions_capped_at_ten(self):
        result = suggest_style_fixes(STIFF)
        self.assertGreater(result["count"], 10)
        self.assertEqual(len(result["suggestions"]), 10)

    def test_suggestions_sorted_by_position(self):
        result = suggest_style_fixes(STIFF)
        starts = [s["start"] for s in result["suggestions"]]
        self.assertEqual(starts, sorted(starts))


class TestFormatSuggestions(unittest.TestCase):
    def test_before_after_rendering(self):
        result = suggest_style_fixes(
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.")
        out = format_suggestions(result)
        self.assertIn("Saran rewrite gaya (1):", out)
        self.assertIn("Verba ringan", out)
        self.assertIn('"melakukan pengukuran terhadap" -> "mengukur"', out)
        self.assertIn(
            "Sebelum: Penelitian ini melakukan pengukuran terhadap "
            "suhu ruangan.", out)
        self.assertIn("Sesudah: Penelitian ini mengukur suhu ruangan.", out)

    def test_connector_renders_as_hapus(self):
        result = suggest_style_fixes(
            "Selain itu, penelitian memakai purposive sampling.")
        out = format_suggestions(result)
        self.assertIn('"Selain itu," -> (hapus)', out)
        self.assertIn("Sesudah: Penelitian memakai purposive sampling.", out)

    def test_guidance_renders_note_not_after(self):
        result = suggest_style_fixes(
            "Simulasi dilakukan dengan perangkat lunak.")
        out = format_suggestions(result)
        self.assertIn("Verba pasif", out)
        self.assertIn("Pakai bentuk aktif bila pelakunya jelas.", out)
        self.assertNotIn("Sesudah:", out)

    def test_empty_renders_none_message(self):
        result = suggest_style_fixes("Penelitian memakai purposive sampling.")
        self.assertIn("Tidak ada saran rewrite", format_suggestions(result))

    def test_truncation_note(self):
        result = suggest_style_fixes(STIFF)
        out = format_suggestions(result)
        self.assertIn(f"Menampilkan 10 dari {result['count']} saran.", out)


class TestHumanizeMain(unittest.TestCase):
    def test_humanize_text_exit_1_with_suggestions(self):
        code = humanize_main([
            "--text",
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
        ])
        self.assertEqual(code, 1)

    def test_humanize_clean_text_exit_0(self):
        code = humanize_main([
            "--text", "Penelitian memakai purposive sampling.",
        ])
        self.assertEqual(code, 0)

    def test_humanize_json(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = humanize_main([
                "--text",
                "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
                "--json",
            ])
        self.assertEqual(code, 1)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["count"], 1)
        self.assertEqual(parsed["suggestions"][0]["replacement"], "mengukur")

    def test_humanize_file(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False,
                encoding="utf-8") as f:
            f.write("Selain itu, penelitian memakai purposive sampling.")
            path = f.name
        try:
            code = humanize_main([path])
        finally:
            os.unlink(path)
        self.assertEqual(code, 1)

    def test_humanize_no_input_exits_2(self):
        with self.assertRaises(SystemExit):
            humanize_main([])

    def test_menu_humanize(self):
        # 5=humanize, 1=type text, text, ""=end, ""=pause, 0=exit
        code, out = run_cli([
            "5", "1",
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
            "", "",
            "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Saran rewrite gaya", out)
        self.assertIn("Penelitian ini mengukur suhu ruangan.", out)


class TestAnalyzeSuggest(unittest.TestCase):
    def test_analyze_without_suggest_has_empty_suggestions(self):
        result = analyze_text_quality(
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.")
        self.assertEqual(result["suggestions"]["count"], 0)

    def test_analyze_with_suggest_includes_suggestions(self):
        result = analyze_text_quality(
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
            suggest=True)
        self.assertEqual(result["suggestions"]["count"], 1)
        self.assertEqual(
            result["suggestions"]["suggestions"][0]["replacement"],
            "mengukur")

    def test_format_analyze_renders_suggestions(self):
        result = analyze_text_quality(
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
            suggest=True)
        out = tools.format_analyze(result)
        self.assertIn("Saran rewrite gaya (1):", out)
        self.assertIn("Penelitian ini mengukur suhu ruangan.", out)


if __name__ == "__main__":
    unittest.main()
