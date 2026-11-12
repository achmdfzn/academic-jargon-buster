"""Audit #4 split-sentence fixes (B-1, H-5, N-17).

B-1: `_split_sentences` was quadratic on text without a terminator
(the old pattern scanned "[^.!?]*" from every position); it now
matches terminators only and slices between them, so long
terminator-free text splits in linear time.
H-5: every period inside an abbreviation is protected, and "i.e."
joins the abbreviation list, so "e.g." / "i.e." no longer split.
N-17: "hal." joins the list and single capital initials
("Dr. A. Budi") no longer split.
"""

import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestSplitSentencesPerformance(unittest.TestCase):
    """T-1 (B-1): long text without a terminator must split fast."""

    def test_50k_chars_without_terminator_is_fast(self):
        # The old quadratic pattern took ~19 s on this input.
        text = "kata " * 10000  # 50.000 karakter, tanpa . ! ?
        start = time.perf_counter()
        sentences = tools._split_sentences(text)
        elapsed = time.perf_counter() - start
        self.assertEqual(sentences, [text.strip()])
        self.assertLess(elapsed, 2.0, f"took {elapsed:.2f}s")

    def test_100k_chars_without_terminator_is_fast(self):
        # The old pattern took ~106 s on this input.
        text = "kata " * 20000  # 100.000 karakter, tanpa . ! ?
        start = time.perf_counter()
        sentences = tools._split_sentences(text)
        elapsed = time.perf_counter() - start
        self.assertEqual(sentences, [text.strip()])
        self.assertLess(elapsed, 2.0, f"took {elapsed:.2f}s")


class TestSplitSentencesAbbreviations(unittest.TestCase):
    """T-8 (H-5): "e.g." / "i.e." must not split; assert the content,
    not just the sentence count."""

    def test_e_g_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Lihat e.g. contoh ini. Lalu pergi."),
            ["Lihat e.g. contoh ini", "Lalu pergi"])

    def test_i_e_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Contohnya i.e. data primer. Lalu pergi."),
            ["Contohnya i.e. data primer", "Lalu pergi"])

    def test_e_g_and_i_e_in_one_text(self):
        self.assertEqual(
            tools._split_sentences(
                "Metode e.g. survei dipakai, i.e. kuesioner daring. "
                "Hasilnya bagus."),
            ["Metode e.g. survei dipakai, i.e. kuesioner daring",
             "Hasilnya bagus"])

    def test_e_g_in_trailing_fragment_without_terminator(self):
        # An abbreviation inside a trailing fragment without any
        # terminator must survive intact as one sentence.
        self.assertEqual(
            tools._split_sentences("Satu kalimat. Contohnya e.g. tabel"),
            ["Satu kalimat", "Contohnya e.g. tabel"])


class TestSplitSentencesHalAndInitials(unittest.TestCase):
    """N-17: "hal." and single capital initials must not split."""

    def test_hal_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Lihat hal. 5 e.g. tabel berikut. Selesai."),
            ["Lihat hal. 5 e.g. tabel berikut", "Selesai"])

    def test_single_capital_initial_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Dr. A. Budi datang. Ia pergi."),
            ["Dr. A. Budi datang", "Ia pergi"])

    def test_initial_without_title_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("A. Budi dan B. Candra datang. Mereka pergi."),
            ["A. Budi dan B. Candra datang", "Mereka pergi"])

    def test_word_ending_in_hal_still_splits(self):
        # "perihal." is not the "hal." abbreviation: the word
        # boundary guard must not protect it.
        self.assertEqual(
            tools._split_sentences("Itu perihal. Ia pergi."),
            ["Itu perihal", "Ia pergi"])

    def test_sentence_ending_in_lone_capital_still_splits(self):
        # An initial is only protected when a capitalised word
        # follows; a lone capital at the very end still ends the
        # sentence (documented limitation: "Nilainya A. Ia senang."
        # stays merged, because an initial and a sentence-final
        # capital cannot be told apart).
        self.assertEqual(
            tools._split_sentences("Nilainya A."),
            ["Nilainya A"])


class TestSplitSentencesContract(unittest.TestCase):
    """The pre-existing output contract still holds after the rewrite."""

    def test_empty_text_gives_empty_list(self):
        self.assertEqual(tools._split_sentences(""), [])
        self.assertEqual(tools._split_sentences("   "), [])

    def test_trailing_fragment_without_terminator_is_one_sentence(self):
        self.assertEqual(
            tools._split_sentences("Satu kalimat. Lalu fragmen tanpa titik"),
            ["Satu kalimat", "Lalu fragmen tanpa titik"])

    def test_closing_quote_belongs_to_its_sentence(self):
        self.assertEqual(
            tools._split_sentences("'Jangan!' Begitu katanya. Lalu pergi."),
            ["'Jangan!'", "Begitu katanya", "Lalu pergi"])

    def test_decimal_number_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Nilai 3.14 itu pi. Lanjut."),
            ["Nilai 3.14 itu pi", "Lanjut"])


class TestAnalyzeLongTerminatorFreeTextEndToEnd(unittest.TestCase):
    """B-1 end to end: POST /api/analyze with a ~999 KB body without
    a terminator must come back quickly (the audit measured >170 s
    with no response on the old code). Server harness copied from
    tests/test_serve.py; this file does not modify that file."""

    @classmethod
    def setUpClass(cls):
        cls.server = tools.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_analyze_999kb_without_terminator_returns_fast(self):
        body = json.dumps({"text": "z" * 999000}).encode("utf-8")
        self.assertLess(len(body), 1_000_000)
        req = urllib.request.Request(
            self.base + "/api/analyze", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status, raw = resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode("utf-8")
        elapsed = time.perf_counter() - start
        self.assertEqual(status, 200, raw[:200])
        self.assertIn("quality_score", json.loads(raw))
        self.assertLess(elapsed, 30.0, f"took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
