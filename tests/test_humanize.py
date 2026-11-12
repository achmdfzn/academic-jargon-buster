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
    apply_suggestions,
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
        self.assertEqual(sug["replacement"], "meningkatkan")
        self.assertEqual(sug["fixed"], "Suhu meningkatkan 12%.")

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

    def test_noun_to_verb_table(self):
        # The noun->verb table uses real transitive verbs, not the
        # intransitive/adverbial readings the old table had.
        cases = [
            ("Suhu mengalami peningkatan sebesar 12%.",
             "meningkatkan", "Suhu meningkatkan 12%."),
            ("Suhu mengalami penurunan sebesar 5%.",
             "menurunkan", "Suhu menurunkan 5%."),
            ("Penelitian ini melakukan perubahan terhadap desain.",
             "mengubah", "Penelitian ini mengubah desain."),
            ("Tim melakukan perawatan terhadap alat.",
             "merawat", "Tim merawat alat."),
        ]
        for text, verb, fixed in cases:
            with self.subTest(text=text):
                result = suggest_style_fixes(text)
                self.assertEqual(result["count"], 1)
                sug = result["suggestions"][0]
                self.assertEqual(sug["replacement"], verb)
                self.assertEqual(sug["fixed"], fixed)

    def test_perjalanan_is_guidance_only(self):
        # "perjalanan" has no direct-verb mapping: "bepergian" is a
        # different construction, so the suggestion stays guidance.
        result = suggest_style_fixes(
            "Penelitian ini melakukan perjalanan ke lokasi.")
        self.assertEqual(result["count"], 1)
        sug = result["suggestions"][0]
        self.assertIsNone(sug["replacement"])
        self.assertIsNone(sug["fixed"])

    def test_preview_fixed_matches_apply(self):
        # The "fixed" preview must be exactly what --apply produces:
        # both go through the same _apply_one path. This covers the
        # tricky cases (sentence-initial connector removal, the
        # "yang mana" split) where the old preview path capitalized
        # and spaced differently from the apply path.
        texts = [
            "Selain itu, penelitian memakai purposive sampling.",
            "Sistem menggunakan pendingin alami, yang mana hal ini "
            "mengurangi konsumsi.",
            "Penelitian ini melakukan perubahan terhadap desain.",
            "Suhu mengalami peningkatan sebesar 12%.",
        ]
        for text in texts:
            with self.subTest(text=text):
                result = suggest_style_fixes(text)
                applied = apply_suggestions(text, result)["text"]
                for sug in result["suggestions"]:
                    if sug["fixed"] is not None:
                        self.assertEqual(applied, sug["fixed"])

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
        # 5=humanize, 1=type text, text, ""=end, ""=skip save, ""=pause,
        # 0=exit
        code, out = run_cli([
            "5", "1",
            "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
            "", "", "",
            "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Saran rewrite gaya", out)
        self.assertIn("Penelitian ini mengukur suhu ruangan.", out)

    def test_menu_humanize_save_fixed(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False,
                encoding="utf-8") as f:
            out_path = f.name
        try:
            # 5=humanize, 1=type text, text, ""=end, path=save,
            # ""=pause, 0=exit
            code, out = run_cli([
                "5", "1",
                "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
                "", out_path, "",
                "0",
            ])
            self.assertEqual(code, 0)
            with open(out_path, encoding="utf-8") as f:
                saved = f.read()
            self.assertEqual(saved,
                             "Penelitian ini mengukur suhu ruangan.")
            self.assertIn("Tersimpan", out)
        finally:
            os.unlink(out_path)


class TestApplySuggestions(unittest.TestCase):
    def test_apply_light_verb(self):
        text = "Penelitian ini melakukan pengukuran terhadap suhu ruangan."
        fixed = apply_suggestions(text, suggest_style_fixes(text))
        self.assertEqual(fixed["text"],
                         "Penelitian ini mengukur suhu ruangan.")
        self.assertEqual(len(fixed["applied"]), 1)
        self.assertEqual(fixed["skipped"], [])

    def test_apply_sebesar(self):
        text = "Suhu mengalami peningkatan sebesar 12%."
        fixed = apply_suggestions(text, suggest_style_fixes(text))
        self.assertEqual(fixed["text"], "Suhu meningkatkan 12%.")

    def test_apply_connector_and_yang_mana(self):
        text = ("Selain itu, penelitian memakai purposive sampling. "
                "Sistem menggunakan pendingin alami, yang mana hal ini "
                "mengurangi konsumsi.")
        fixed = apply_suggestions(text, suggest_style_fixes(text))
        self.assertEqual(
            fixed["text"],
            "Penelitian memakai purposive sampling. "
            "Sistem menggunakan pendingin alami. "
            "Hal ini mengurangi konsumsi.")

    def test_apply_skips_guidance_only(self):
        text = "Simulasi dilakukan dengan perangkat lunak."
        fixed = apply_suggestions(text, suggest_style_fixes(text))
        self.assertEqual(fixed["text"], text)
        self.assertEqual(fixed["applied"], [])
        self.assertEqual(len(fixed["skipped"]), 1)

    def test_apply_stiff_text(self):
        result = suggest_style_fixes(STIFF, limit=None)
        fixed = apply_suggestions(STIFF, result)
        self.assertEqual(len(fixed["applied"]), 9)
        self.assertEqual(
            sorted({s["pattern"] for s in fixed["skipped"]}),
            ["passive", "rhythm"])
        self.assertIn("Penelitian ini mengukur suhu ruangan.",
                      fixed["text"])
        self.assertIn("Pengujian dilakukan dengan metode. Hasilnya "
                      "ditunjukkan pada tabel.", fixed["text"])
        self.assertNotIn("Selain itu", fixed["text"])
        self.assertNotIn("yang mana", fixed["text"])

    def test_apply_is_idempotent(self):
        result = suggest_style_fixes(STIFF, limit=None)
        once = apply_suggestions(STIFF, result)["text"]
        twice = apply_suggestions(
            once, suggest_style_fixes(once, limit=None))["text"]
        self.assertEqual(once, twice)

    def test_apply_skips_overlapping_spans(self):
        # A connector span and a light-verb span that overlap:
        # only the first (by position) is applied.
        text = ("Selain itu, penelitian ini melakukan pengukuran "
                "terhadap suhu.")
        result = suggest_style_fixes(text)
        self.assertEqual(result["count"], 2)
        overlapping = {
            "pattern": "connectors",
            "original": "Selain itu, penelitian ini melakukan pengukuran",
            "replacement": "",
            "context": result["suggestions"][0]["context"],
            "fixed": None,
            "note": "",
            "start": 0,
            "end": len("Selain itu, penelitian ini melakukan pengukuran"),
        }
        result["suggestions"].append(overlapping)
        fixed = apply_suggestions(text, result)
        # The overlapping suggestion is skipped; the real ones apply.
        self.assertIn("Penelitian ini mengukur suhu.",
                      fixed["text"])

    def test_humanize_apply_writes_humanized_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "naskah.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Penelitian ini melakukan pengukuran terhadap "
                        "suhu ruangan.")
            code = humanize_main([path, "--apply"])
            self.assertEqual(code, 1)
            out_path = os.path.join(d, "naskah.humanized.txt")
            with open(out_path, encoding="utf-8") as f:
                self.assertEqual(f.read(),
                                 "Penelitian ini mengukur suhu ruangan.")

    def test_humanize_apply_in_place_keeps_backup(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "naskah.txt")
            original = ("Penelitian ini melakukan pengukuran terhadap "
                        "suhu ruangan.")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)
            code = humanize_main([path, "--apply", "--in-place"])
            self.assertEqual(code, 1)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(),
                                 "Penelitian ini mengukur suhu ruangan.")
            with open(path + ".bak", encoding="utf-8") as f:
                self.assertEqual(f.read(), original)

    def test_humanize_apply_out(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "naskah.txt")
            dst = os.path.join(d, "hasil.txt")
            with open(src, "w", encoding="utf-8") as f:
                f.write("Selain itu, penelitian memakai purposive sampling.")
            code = humanize_main([src, "--apply", "--out", dst])
            self.assertEqual(code, 1)
            with open(dst, encoding="utf-8") as f:
                self.assertEqual(
                    f.read(), "Penelitian memakai purposive sampling.")

    def test_humanize_apply_text_prints_fixed(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = humanize_main([
                "--text",
                "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
                "--apply",
            ])
        self.assertEqual(code, 1)
        self.assertIn("Penelitian ini mengukur suhu ruangan.",
                      buf.getvalue())

    def test_humanize_apply_json_carries_fixed_text(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = humanize_main([
                "--text",
                "Penelitian ini melakukan pengukuran terhadap suhu ruangan.",
                "--apply", "--json",
            ])
        self.assertEqual(code, 1)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["fixed_text"],
                         "Penelitian ini mengukur suhu ruangan.")
        self.assertEqual(parsed["applied"], 1)
        self.assertEqual(parsed["skipped"], 0)

    def test_humanize_apply_in_place_needs_file(self):
        with self.assertRaises(SystemExit):
            humanize_main(["--text", "x", "--apply", "--in-place"])

    def test_humanize_out_and_in_place_conflict(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False,
                encoding="utf-8") as f:
            f.write("Penelitian ini melakukan pengukuran terhadap suhu.")
            path = f.name
        try:
            with self.assertRaises(SystemExit):
                humanize_main([path, "--apply", "--out", "x.txt",
                               "--in-place"])
        finally:
            os.unlink(path)


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
