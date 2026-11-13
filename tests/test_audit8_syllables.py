"""Audit #8 T-3: syllable pins — gaul/raut, -ment rule, iou=3, kau/mau.

Every word here was verified against a dictionary before it
was pinned (KBBI via kbbi.web.id / kbbi.co.id for Indonesian,
Oxford / Cambridge / WebDictionary for English, 2026-11-14).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestAudit8Syllables(unittest.TestCase):
    """H-1/H-2/H-4 + the kau/mau correction (audit #8)."""

    # H-1: "gaul" ga·ul (KBBI: ber·ga·ul, per·ga·ul·an) and
    # "raut" ra·ut (KBBI: me·ra·ut, ra·ut·an) + derivatives
    # via affix stripping (not listed anywhere).
    GAUL_RAUT_ID = {
        "gaul": 2, "raut": 2,
        "bergaul": 3, "menggaul": 3, "menggaulkan": 4,
        "pergaulan": 4, "meraut": 3, "rautan": 3,
        "merautkan": 4, "diraut": 3,
    }

    # H-2: the 24 -ment words (audit #8) — the guarded
    # silent-e rule in _en_medial_silent_e counts them right.
    MENT_EN = {
        "management": 3, "engagement": 3, "arrangement": 3,
        "improvement": 3, "statement": 2, "movement": 2,
        "requirement": 3, "achievement": 3, "excitement": 3,
        "amazement": 3, "replacement": 3, "placement": 2,
        "basement": 2, "pavement": 2, "judgement": 2,
        "retirement": 3, "involvement": 3, "refinement": 3,
        "announcement": 3, "advertisement": 4,
        "acknowledgement": 4, "encouragement": 4,
        "discouragement": 4, "postponement": 3,
        "abridgement": 3,
    }

    # H-2 guards: words the rule must NOT touch — the "l"
    # guard ("element", "supplement", "implement",
    # "puzzlement", "battlement", "settlement",
    # "embezzlement"), no "e" before "-ment" ("development",
    # "government", "sentiment", "document", "torment"), the
    # "crement" family (a real schwa after the "cr" onset),
    # plurals (count like the singular), and more of the
    # family the rule reaches ("advancement", "enhancement",
    # "commencement", "pronouncement", "amusement",
    # "casement") and must not ("judgment", "acknowledgment",
    # "sacrament", "testament", "ornament", "monument",
    # "regiment", "experiment", "complement", "enjoyment",
    # "payment", "shipment", "treatment").
    MENT_GUARDS_EN = {
        "element": 3, "development": 4, "government": 3,
        "sentiment": 3, "document": 3, "supplement": 3,
        "implement": 3, "torment": 2, "cement": 2,
        "puzzlement": 3, "increment": 3, "decrement": 3,
        "excrement": 3, "recrement": 3,
        "managements": 3, "statements": 2, "basements": 2,
        "advancement": 3, "enhancement": 3,
        "commencement": 3, "pronouncement": 3,
        "amusement": 3, "casement": 2,
        "judgment": 2, "acknowledgment": 4,
        "sacrament": 3, "testament": 3, "ornament": 3,
        "monument": 3, "regiment": 3, "experiment": 4,
        "complement": 3, "battlement": 3, "settlement": 3,
        "embezzlement": 4, "enjoyment": 3, "payment": 2,
        "shipment": 2, "treatment": 2,
    }

    # H-4 + the kau/mau correction: "iou" is 3 (Oxford,
    # Cambridge, WebDictionary); "kau" is 1 (a KBBI-based
    # "Suku Kata" document lists "kau" under "Satu suku
    # kata", Wiktionary gives [kaw] — audit #5's ka·u = 2
    # was wrong); "mau" is hiatus ma·u = 2 (KBBI me·ma·u·kan,
    # ke·ma·u·an, ma·u·pun), so "maunya" is 3 — the enclitic
    # carve-out only applies to true diphthongs; "bau"
    # stays 2 (ber·bau, mem·ba·u·i).
    KAU_MAU = {
        "iou": 3, "kau": 1, "kaupun": 3, "kaubaca": 3,
        "kaunya": 2, "mau": 2, "maunya": 3, "maukah": 3,
        "maupun": 3, "mauku": 3, "memaukan": 4, "kemauan": 4,
        "bau": 2,
    }

    # The 9 audit #7 roots, confirmed per word against KBBI
    # in the audit #8 fix round (2026-11-14): pais pa·is
    # (pepes), laun la·un (lambat), saur sa·ur (berbelit),
    # kaul ka·ul (janji; nazar), saut sa·ut (lihat "akar"),
    # pauk pa·uk (la·uk-pa·uk), taul ta·ul (me·na·ul),
    # tais ta·is (arkais: kotor), raib ra·ib (hilang; gaib).
    AUDIT7_ROOTS_ID = {
        "pais": 2, "laun": 2, "saur": 2, "kaul": 2,
        "saut": 2, "pauk": 2, "taul": 2, "tais": 2,
        "raib": 2,
    }

    def test_gaul_raut(self):
        for word, want in self.GAUL_RAUT_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_ment_words(self):
        for word, want in self.MENT_EN.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_ment_guards(self):
        for word, want in self.MENT_GUARDS_EN.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_kau_mau_iou(self):
        for word, want in self.KAU_MAU.items():
            with self.subTest(word=word):
                lang = "en" if word == "iou" else "id"
                self.assertEqual(
                    tools._count_syllables(word, lang), want)

    def test_audit7_roots_confirmed(self):
        for word, want in self.AUDIT7_ROOTS_ID.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


if __name__ == "__main__":
    unittest.main()
