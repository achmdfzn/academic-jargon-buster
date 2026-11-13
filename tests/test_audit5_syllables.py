"""Audit #5 follow-up tests for the syllable counter rewrite: H-2,
H-3, N-2, N-6, N-10 — and test gap T-1.

Design (audit #5, H-2): the source of truth is KBBI
syllabification, word by word. EYD V has four diphthongs
(ai, au, ei, oi) — that claim is TRUE — but a diphthong only
counts as one syllable when the pair sits inside ONE syllable;
KBBI decides per word ("pandai" is a diphthong, "baik" is
ba·ik = 2). The counter now strips Indonesian prefixes and
suffixes and counts the root, with a curated list of hiatus
roots — no more whole-word exception entries per derivative.

Every count in this file was verified against KBBI
(kbbi.web.id, 2026-11-13) or, for the English words, against
standard English syllabification. "baik" = 2 is the T-1
regression (it was pinned at 1 by v1.27.2 and was wrong).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestHiatusRootsAudit5(unittest.TestCase):
    """H-2: the auditor's word list, all verified against KBBI."""

    # Auditor's list (audit #5, H-2): every one of these was
    # wrong under the v1.27.2 counter and is right now.
    AUDITOR_ID = {
        "kain": 2, "lain": 2, "gaib": 2, "kait": 2, "kaitan": 3,
        "berkaitan": 4, "saingi": 3, "saingan": 3, "persaingan": 4,
        "kaidah": 3, "gairah": 3, "cairan": 3, "keairan": 4,
        "perairan": 4, "laut": 2, "lautan": 3, "bau": 2, "bauan": 3,
        "kau": 2, "kaupun": 3, "maukah": 3, "koin": 2, "poin": 2,
        "poinnya": 3, "heroik": 3, "stoik": 2, "naik": 2, "cair": 2,
        "raih": 2, "jauh": 2, "dimainkan": 4, "mainkan": 3,
        "mempermainkan": 5, "permainkan": 4, "kebaikanmu": 5,
        "kebaikanku": 5, "keindahannya": 5, "keindahanmu": 5,
        "sainsnya": 3, "kesainsan": 4, "memperbaikinya": 6,
        "menaiki": 4, "menaikkan": 4, "penaikan": 4, "kenaikan": 4,
        "pencairan": 4,
    }

    # Words that were already right in v1.27.2 and must stay right.
    STILL_RIGHT_ID = {
        "bermain": 3, "main": 2, "sains": 2, "kebaikan": 4,
        "perbaikan": 4, "keindahan": 4, "survei": 2, "maupun": 3,
        "diperbaiki": 5, "capaian": 4, "pencapaian": 5,
        "memperbaiki": 5, "daun": 2, "air": 2, "damai": 2,
        "ramai": 2, "pandai": 2, "rantai": 2, "pantai": 2,
        "sampai": 2, "boikot": 2, "geiser": 2,
    }

    # T-1 regressions: the wrong v1.27.2 expectation plus the
    # regressions the audit asked for by name.
    T1_REGRESSIONS = {
        "baik": 2, "kain": 2, "laut": 2, "baik-baik": 4,
        "dimainkan": 4,
    }

    def test_auditor_words(self):
        for word, want in self.AUDITOR_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_still_right_words(self):
        for word, want in self.STILL_RIGHT_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_t1_regressions(self):
        for word, want in self.T1_REGRESSIONS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestOverAppliedExceptionsAudit5(unittest.TestCase):
    """H-2: three v1.27.2 exception entries were wrong by
    over-application. "capai" is ca-pai (2, a real diphthong),
    "mencapai"/"tercapai" are 3 — only their suffixed forms
    split ("capaian" 4, "pencapaian" 5)."""

    def test_capai_family(self):
        cases = {
            "capai": 2, "mencapai": 3, "tercapai": 3,
            "capaian": 4, "pencapaian": 5,
        }
        for word, want in cases.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestHyphenatedReduplicationAudit5(unittest.TestCase):
    """H-3: hyphenated words count per part, then sum."""

    def test_reduplication(self):
        cases = {
            "baik-baik": 4, "main-main": 4, "kain-kain": 4,
            "laut-laut": 4, "poin-poin": 4, "daun-daun": 4,
            "buku-buku": 4, "well-known": 2, "t-test": 2,
        }
        for word, want in cases.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestEuMonophthongAudit5(unittest.TestCase):
    """N-6: "eu" is the EYD V monophthong [ə] — one syllable in
    the Indonesian branch. "seudati" is a whole-word exception:
    its "eu" spans what looks like the "se-" prefix boundary,
    so affix stripping would break it."""

    def test_eu_words(self):
        cases = {"seudati": 3, "euis": 2, "peuyeum": 3, "eureun": 3}
        for word, want in cases.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestEnglishLeAndHiatusAudit5(unittest.TestCase):
    """N-2: final "-le" after a consonant is a syllable of its
    own; plus English hiatus words. "fire" and "hour" are 1 and
    must stay 1 — do not "fix" them."""

    LE_WORDS = {
        "table": 2, "syllable": 3, "little": 2, "bottle": 2,
        "candle": 2, "apple": 2, "people": 2, "able": 2,
        "simple": 2, "example": 3, "handle": 2, "middle": 2,
        "cycle": 2, "title": 2, "single": 2, "possible": 3,
        "article": 3,
    }

    HIATUS_EN = {
        "idea": 3, "area": 3, "real": 2, "poem": 2,
        "science": 2, "rhythm": 2,
    }

    DO_NOT_FIX = {"fire": 1, "hour": 1, "aisle": 1, "isle": 1}

    def test_le_words(self):
        for word, want in self.LE_WORDS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word, "en"), want)

    def test_hiatus_words(self):
        for word, want in self.HIATUS_EN.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word, "en"), want)

    def test_do_not_fix(self):
        for word, want in self.DO_NOT_FIX.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word, "en"), want)


class TestUnsupportedLangAudit5(unittest.TestCase):
    """N-10: an unsupported lang raises instead of silently
    falling back to Indonesian."""

    def test_unknown_lang_raises(self):
        for lang in ("fr", "de", "xx", ""):
            with self.subTest(lang=lang):
                with self.assertRaises(ValueError):
                    tools.readability_score("Penelitian ini baik.", lang=lang)

    def test_supported_langs_still_work(self):
        for lang in ("id", "en"):
            with self.subTest(lang=lang):
                result = tools.readability_score(
                    "Penelitian ini baik.", lang=lang)
                self.assertIn("flesch_reading_ease", result)


class TestCommonAcademicWordsAudit5(unittest.TestCase):
    """Affix stripping must not break ordinary academic words —
    the counter is used on every word of every analyzed text."""

    COMMON = {
        "penelitian": 5, "kuesioner": 5, "mahasiswa": 4,
        "sistem": 2, "informasi": 4, "metode": 3, "data": 2,
        "dikumpulkan": 4, "melalui": 4, "menggunakan": 4,
        "responden": 3, "menunjukkan": 4, "berdasarkan": 4,
        "tersebut": 3, "digunakan": 4, "dilakukan": 4,
        "memberikan": 4, "diharapkan": 4, "peningkatan": 4,
        "perubahan": 4, "kemudian": 4, "demikian": 4,
        "berikut": 3, "berikutnya": 4, "selanjutnya": 4,
        "pertama": 3, "kedua": 3, "ketiga": 3, "adalah": 3,
        "dengan": 2, "kepada": 3, "sebagai": 3, "menjadi": 3,
        "membuat": 3, "mengatakan": 4, "sebelum": 3, "sesudah": 3,
        "sangat": 2, "sudah": 2, "belum": 2, "dapat": 2,
        "harus": 2, "juga": 2, "karena": 3, "tetapi": 3,
        "dalam": 2, "antara": 3, "skripsi": 2, "tugas": 2,
        "akhir": 2, "keuangan": 4, "seumur": 3, "pengairan": 4,
        "menanti": 3, "menikah": 3, "menulis": 3, "menara": 3,
    }

    def test_common_words(self):
        for word, want in self.COMMON.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


if __name__ == "__main__":
    unittest.main()
