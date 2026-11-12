"""Audit #4 follow-up tests for the readability fixes: H-3, H-6,
N-7, N-9, N-16 — test gaps T-3 (Node render, numbers compared
with Python, not just substrings) and T-10 (syllable counter).

H-6 first verified the EYD claim against the web instead of
trusting the auditor: EYD edisi V lists FOUR diphthongs
(ai, au, ei, oi) — Badan Bahasa 2022, confirmed on the official
ejaan.kemdikdasmen.go.id page — so "survei" is 2 (sur-vei),
not 3. The "ei" was added by PUEBI (Permendikbud 50/2015) for
loanwords and kept by EYD V.
"""

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools

ROOT = Path(__file__).resolve().parent.parent

# Minimal browser stand-ins so the page's <script> can run in Node:
# load-time code only touches document.getElementById (wiring
# listeners), document.createElement, and fetch (loadPrompts, whose
# rejection is caught by the page itself). navigator.clipboard is
# only used inside a click handler, but stub it anyway.
_NODE_STUB = """
var __el = function () {
  return {
    addEventListener: function () {},
    classList: {add: function () {}, remove: function () {}},
    setAttribute: function () {}, appendChild: function () {},
    dataset: {}, style: {}, disabled: false,
    value: "", textContent: "", innerHTML: ""
  };
};
var document = {
  getElementById: function () { return __el(); },
  createElement: function () { return __el(); },
  querySelector: function () { return null; },
  querySelectorAll: function () { return {forEach: function () {}}; }
};
var navigator = {clipboard: {writeText: function () { return Promise.resolve(); }}};
var fetch = function () { return Promise.reject(new Error("no network in test")); };
"""


def _page_script():
    """The page's <script> block, extracted from WEB_UI_HTML."""
    html = tools.WEB_UI_HTML
    assert html.count("<script>") == 1, "page must have one script block"
    return html.split("<script>", 1)[1].split("</script>", 1)[0]


def _render_analyze_html(res, lang, test_case):
    """Render renderAnalyze(res, lang) in Node; return the HTML.

    The page script is an IIFE, so renderAnalyze is exported by
    appending to it before the closing `})();`. Node is required.
    """
    script = _page_script()
    test_case.assertTrue(script.rstrip().endswith("})();"))
    script = (script.rstrip()[:-len("})();")]
              + "; globalThis.__renderAnalyze = renderAnalyze; })();")
    js = (_NODE_STUB + script + "\nconsole.log(__renderAnalyze("
          + json.dumps(res) + ", " + json.dumps(lang) + "));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                    encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        # Bytes mode + explicit UTF-8 decode (see _run_node in
        # test_audit4_server.py): text=True decodes with the
        # locale encoding, which is cp1252 on Windows and turns
        # the em dash in the Readability card into mojibake, so
        # the card regex stops matching. Node writes UTF-8.
        proc = subprocess.run(["node", path], capture_output=True,
                              timeout=30)
        proc.stdout = proc.stdout.decode("utf-8")
        proc.stderr = proc.stderr.decode("utf-8")
    finally:
        os.unlink(path)
    test_case.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout


class TestCountSyllablesAudit4(unittest.TestCase):
    """T-10: every auditor word, its derivatives, and English."""

    # Auditor's words (audit #4, H-6): code vs real, now all real.
    AUDITOR_ID = {
        "maupun": 3, "bermain": 3, "main": 2, "sains": 2,
        "diperbaiki": 5, "kebaikan": 4, "capaian": 4,
        "perbaikan": 4, "keindahan": 4,
    }

    # Derivatives registered explicitly in _SYLLABLE_EXCEPTIONS.
    DERIVATIVES_ID = {
        "memainkan": 4, "permainan": 4, "pemain": 3, "mainan": 3,
        "capai": 3, "mencapai": 4, "tercapai": 4, "pencapaian": 5,
        "perbaiki": 4, "memperbaiki": 5, "terperbaiki": 5,
        "ataupun": 4, "kalaupun": 4, "bagaimanapun": 5,
        "daun": 2, "dedaunan": 4, "air": 2, "berair": 3,
    }

    # Words that must NOT change: real diphthongs, and "domain",
    # which merely contains "main" as a substring.
    UNCHANGED_ID = {
        "survei": 2, "baik": 1, "atau": 2, "boikot": 2, "kau": 1,
        "mau": 1, "pulau": 2, "danau": 2, "sungai": 2, "pantai": 2,
        "pandai": 2, "geiser": 2, "domain": 2,
    }

    ENGLISH = {
        "happy": 2, "study": 2, "make": 1, "reading": 2,
        "beautiful": 3, "the": 1, "yes": 1, "yesterday": 3,
        "one": 1, "fire": 1,
    }

    def test_auditor_words(self):
        for word, want in self.AUDITOR_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_derivatives(self):
        for word, want in self.DERIVATIVES_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_unchanged_words(self):
        for word, want in self.UNCHANGED_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_english_branch(self):
        for word, want in self.ENGLISH.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word, "en"), want)

    def test_lang_defaults_to_indonesian(self):
        # No lang means EYD rules: "survei" is 2, "make" is 2
        # (no silent-e rule in Indonesian).
        self.assertEqual(tools._count_syllables("survei"), 2)
        self.assertEqual(tools._count_syllables("make"), 2)
        self.assertEqual(tools._count_syllables("happy"), 1)

    def test_readability_uses_lang(self):
        # "The cat sat." in English: every word 1 syllable, so
        # RE = 206.835 - 1.015*3 - 84.6 = 119.19 -> clamped 100.0.
        r = tools.readability_score("The cat sat.", lang="en")
        self.assertEqual(r["flesch_reading_ease"], 100.0)
        self.assertEqual(r["total_syllables"], 3)


class TestDegenerateTextAudit4(unittest.TestCase):
    """N-9: punctuation/digits alone are not a text."""

    def test_no_real_word_is_empty_text(self):
        for bad in ("...", "!!!", "123 456", "42", "?! ... !!!"):
            with self.subTest(text=repr(bad)):
                with self.assertRaises(ValueError) as cm:
                    tools.readability_score(bad)
                self.assertEqual(str(cm.exception), "teks kosong")

    def test_number_plus_word_still_scores(self):
        # One real word is enough: "123 buku." is a text.
        r = tools.readability_score("123 buku.")
        self.assertEqual(r["words"], 2)
        self.assertEqual(r["sentences"], 1)

    def test_analyze_rejects_degenerate_text_too(self):
        # analyze_text_quality always computes readability, so the
        # same guard applies there instead of a perfect score.
        with self.assertRaises(ValueError) as cm:
            tools.analyze_text_quality("...", verify_dois=False)
        self.assertEqual(str(cm.exception), "teks kosong")


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class TestReadabilityRenderNode(unittest.TestCase):
    """T-3: render the Readability card in Node and compare every
    number with Python — this is what caught H-3 (FKGL 628.4
    clamped to 100, average 1500 clamped to 1000)."""

    def _check_card(self, text, lang="id"):
        py = tools.readability_score(text, lang=lang)
        res = tools.analyze_text_quality(text, lang=lang,
                                         verify_dois=False)
        html = _render_analyze_html(res, lang, self)
        if lang == "en":
            m = re.search(
                r"Flesch Reading Ease ([\d.]+)/100 — (\w[\w ]*)"
                r"<br>Flesch-Kincaid Grade Level ([\d.]+)"
                r"<br>Average ([\d.]+) words/sentence, ([\d.]+) syllables/word "
                r"\((\d+) words, (\d+) sentences, (\d+) syllables\)",
                html)
        else:
            m = re.search(
                r"Flesch Reading Ease ([\d.]+)/100 — ([^<]*)"
                r"<br>Flesch-Kincaid Grade Level ([\d.]+)"
                r"<br>Rata-rata ([\d.]+) kata/kalimat, ([\d.]+) suku kata/kata "
                r"\((\d+) kata, (\d+) kalimat, (\d+) suku kata\)",
                html)
        self.assertIsNotNone(m, "Readability card not found in:\n" + html)
        re_s, band_s, fkgl_s, wps_s, spw_s, w_s, s_s, syl_s = m.groups()
        # RE is formatted with exactly 1 decimal ("0.0", never "0").
        self.assertEqual(re_s, f"{py['flesch_reading_ease']:.1f}")
        self.assertEqual(band_s, py["band"])
        self.assertEqual(float(fkgl_s), py["flesch_kincaid_grade"])
        self.assertEqual(float(wps_s), py["avg_words_per_sentence"])
        self.assertEqual(float(spw_s), py["avg_syllables_per_word"])
        self.assertEqual(int(w_s), py["words"])
        self.assertEqual(int(s_s), py["sentences"])
        self.assertEqual(int(syl_s), py["total_syllables"])
        return py, html

    def test_extreme_text_is_not_clamped(self):
        # H-3 repro: one 1500-word sentence. Python says FKGL
        # 628.4 and 1500.0 words/sentence; the card must show the
        # same numbers, not 100 / 1000.
        py, _ = self._check_card("penelitian " * 1500)
        self.assertEqual(py["flesch_reading_ease"], 0.0)
        self.assertEqual(py["flesch_kincaid_grade"], 628.4)
        self.assertEqual(py["avg_words_per_sentence"], 1500.0)

    def test_normal_text_matches_python(self):
        # N-7: the card shows the counts, like format_readability.
        py, _ = self._check_card(
            "Penelitian ini menggunakan metode survei. "
            "Data dikumpulkan melalui kuesioner.")
        self.assertEqual(py["words"], 9)
        self.assertEqual(py["sentences"], 2)
        self.assertEqual(py["total_syllables"], 31)
        self.assertEqual(py["flesch_kincaid_grade"], 26.8)

    def test_english_card_matches_python(self):
        py, _ = self._check_card("The cat sat on the mat.", lang="en")
        self.assertEqual(py["flesch_reading_ease"], 100.0)
        self.assertEqual(py["band"], "Very easy")

    def test_js_parses_clean(self):
        # node --check on the extracted page script.
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                        delete=False,
                                        encoding="utf-8") as f:
            f.write(_page_script())
            path = f.name
        try:
            proc = subprocess.run(["node", "--check", path],
                                  capture_output=True, text=True,
                                  encoding="utf-8", timeout=30)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class TestShimVersionAudit4(unittest.TestCase):
    """N-16: every shim's --version prints the shim's own version
    (its __version__), not the core __version__."""

    SHIMS = (
        "jargon_buster.py",
        "citation_weaver.py",
        "skripsi_prompts.py",
        "academic_cli.py",
        "ai_detector.py",
        "readability.py",
    )

    def test_shim_version_matches_its_own_dunder(self):
        for shim in self.SHIMS:
            with self.subTest(shim=shim):
                mod = importlib.import_module(shim[:-3])
                proc = subprocess.run(
                    [sys.executable, str(ROOT / shim), "--version"],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout.strip(),
                                 f"{shim} {mod.__version__}")
                # Guard against the old behaviour (core version).
                self.assertNotIn(tools.__version__, proc.stdout)

    def test_core_version_unchanged(self):
        # The top-level --version still lists every component.
        proc = subprocess.run(
            [sys.executable, str(ROOT / "academic_tools.py"),
             "--version"],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"academic_tools.py {tools.__version__}",
                      proc.stdout)
        self.assertIn(f"readability {tools.READABILITY_VERSION}",
                      proc.stdout)

    def test_dispatch_subcommand_version_still_core(self):
        # `academic_tools.py jargon --version` (via main dispatch)
        # still prints the core version: the component version is
        # only for the shim's own entry point.
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                tools.main(["jargon", "--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertTrue(buf.getvalue().strip().endswith(
            tools.__version__))


if __name__ == "__main__":
    unittest.main()
