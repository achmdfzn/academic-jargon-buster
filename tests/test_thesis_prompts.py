"""Tests for Thesis Prompts (Prompt Skripsi) in academic_tools.py."""

import io
import re
import unittest
from contextlib import redirect_stdout

import academic_tools as tools
import skripsi_prompts


class TestThesisPrompts(unittest.TestCase):
    def test_fifteen_prompts_with_unique_ids(self):
        self.assertEqual(len(tools.PROMPTS), 15)
        ids = [p["id"] for p in tools.PROMPTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_prompt_has_required_fields(self):
        for p in tools.PROMPTS:
            for key in ("id", "name", "name_en", "category", "tool", "fields", "template"):
                self.assertIn(key, p, f"{p['id']} missing {key}")
            self.assertTrue(p["name"])
            self.assertTrue(p["template"])
            self.assertIsInstance(p["fields"], list)

    def test_every_placeholder_is_declared(self):
        for p in tools.PROMPTS:
            declared = {f["key"] for f in p["fields"]}
            used = set(re.findall(r"\{(\w+)\}", p["template"]))
            self.assertEqual(used, declared, f"{p['id']}: {used} vs {declared}")

    def test_every_field_has_bilingual_labels(self):
        for p in tools.PROMPTS:
            for f in p["fields"]:
                self.assertTrue(f["label"], f"{p['id']}.{f['key']} missing id label")
                self.assertTrue(f["label_en"], f"{p['id']}.{f['key']} missing en label")

    def test_fill_prompt_fills_all_placeholders(self):
        out = tools.fill_prompt("roadmap", {
            "judul": "Sistem Informasi Manajemen",
            "teori": "TAM",
            "metode": "kualitatif",
            "bulan": "6",
            "tanggal": "11 November 2026",
        })
        self.assertIn("Sistem Informasi Manajemen", out)
        self.assertIn("TAM", out)
        self.assertNotIn("{", out)
        self.assertNotIn("}", out)

    def test_fill_prompt_with_no_fields_returns_template(self):
        out = tools.fill_prompt("review-draf", {})
        self.assertIn("dosen penguji", out)

    def test_fill_prompt_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            tools.fill_prompt("tidak-ada", {})

    def test_fill_prompt_missing_field_raises(self):
        with self.assertRaises(ValueError) as cm:
            tools.fill_prompt("roadmap", {"judul": "X"})
        self.assertIn("teori", str(cm.exception))

    def test_fill_prompt_empty_value_raises(self):
        with self.assertRaises(ValueError):
            tools.fill_prompt("saran", {"judul": "X", "hasil": ""})

    def test_get_prompt_returns_none_for_unknown(self):
        self.assertIsNone(tools.get_prompt("tidak-ada"))
        self.assertEqual(tools.get_prompt("ppt")["id"], "ppt")

    def test_list_prompts_category_filter(self):
        bab3 = tools.list_prompts(category="Bab 3")
        self.assertEqual({p["id"] for p in bab3},
                         {"metodologi", "hubungan-variabel", "hipotesis"})
        self.assertEqual(len(tools.list_prompts()), 15)
        self.assertEqual(tools.list_prompts(category="Tidak Ada"), [])

    def test_prompts_main_list(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(tools.prompts_main(["--list"]), 0)
        out = buf.getvalue()
        self.assertIn("roadmap", out)
        self.assertIn("jurnal", out)

    def test_prompts_main_show_template(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(tools.prompts_main(["latar-belakang"]), 0)
        self.assertIn("{topik}", buf.getvalue())

    def test_prompts_main_fill_with_set(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = tools.prompts_main([
                "saran",
                "--set", "judul=Sistem Informasi",
                "--set", "hasil=skor SUS 73,96",
            ])
        self.assertEqual(rc, 0)
        self.assertIn("Sistem Informasi", buf.getvalue())
        self.assertIn("73,96", buf.getvalue())

    def test_prompts_main_no_args_lists(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(tools.prompts_main([]), 0)
        self.assertIn("roadmap", buf.getvalue())

    def test_shim_reexports_match(self):
        self.assertEqual(skripsi_prompts.__version__, tools.PROMPTS_VERSION)
        self.assertIs(skripsi_prompts.PROMPTS, tools.PROMPTS)
        self.assertIs(skripsi_prompts.fill_prompt, tools.fill_prompt)
        self.assertIs(skripsi_prompts.get_prompt, tools.get_prompt)
        self.assertIs(skripsi_prompts.list_prompts, tools.list_prompts)


if __name__ == "__main__":
    unittest.main()
