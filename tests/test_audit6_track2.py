"""Tests for audit #6 (v1.27.3), track t2: H-3, H-4, T-6 — the
Indonesian syllable counter's new hiatus roots and nasal
assimilation.

Design (audit #6, H-3/H-4): the source of truth is KBBI
syllabification, word by word, and every count in this file was
re-verified against kbbi.web.id on 2026-11-13 (not just taken
from the audit report). Two of the audit's H-3 claims did NOT
survive that re-check, and this file pins the KBBI reading, not
the audit's:

- "koboi" is ko·boi (2) and "boikot" is boi·kot (2) on
  kbbi.web.id — the "oi" is a real diphthong there, unlike
  "koin" (ko·in) — so neither was added to
  _SYLLABLE_EXCEPTIONS. "memboikot" is mem·boi·kot (3),
  "pemboikot" pem·boi·kot (3), "pemboikotan" (4). The three
  older pins of "boikot": 2 (test_readability.py,
  test_audit4_readability.py, test_audit5_syllables.py) were
  right all along and stay. (Caveat: the official KBBI V site
  could not be fetched to cross-check; if KBBI V ever shows
  ko·bo·i / bo·i·kot, this decision must be revisited.)
- "raib" (T-6, suspected 2) has NO entry on kbbi.web.id at
  all, so it was NOT added and is deliberately NOT pinned
  here — an unverified count must not be frozen into a test.

Verified and added (H-3): kail, bait, paut, taut, laik, lauk,
kaut, gaun, aum, syair, mozaik, protein, kasein. Verified and
added (H-4b): sair, raup, aib (a·ib, via meng·a·ib·kan).
Verified and added (T-6): kais (ka·is), deisme (de·is·me),
teisme (te·is·me). "geiser" is gei·ser (2) — the T-6 suspicion
of 3 was wrong, and the code was already right.

H-4 is fixed with a remnant lexicon (_NASAL_REMNANTS), NOT by
splitting the first vowel pair after a nasal prefix: that naive
fix would break "memandai" (mem- + pandai, a real diphthong,
3, not 4). The guard tests below pin "memandai" and the four
words the audit #6 coordinator confirmed were already right
("disesuaikan" 6, "penyesuaian" 6, "pengembangan" 4,
"ketersediaan" 6). The 81 audit #5 Indonesian words are
covered by tests/test_audit5_syllables.py and are run
alongside this file; they are not duplicated here.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestH3RootsAudit6(unittest.TestCase):
    """H-3: the 13 new hiatus roots, each re-verified against
    KBBI (kbbi.web.id, 2026-11-13)."""

    ROOTS = {
        "kail": 2, "bait": 2, "paut": 2, "taut": 2,
        "laik": 2, "lauk": 2, "kaut": 2, "gaun": 2,
        "aum": 2, "syair": 2, "mozaik": 3,
        "protein": 3, "kasein": 3,
    }

    # Derivatives follow from affix stripping, no extra entries:
    # kailan = kail + -an, pautan = paut + -an, auman = aum + -an,
    # syairnya = syair + -nya, bersyair = ber- + syair,
    # kelaikan = ke- + laik + -an (KBBI ke·la·ik·an, 4).
    DERIVATIVES = {
        "kailan": 3, "pautan": 3, "auman": 3,
        "syairnya": 3, "bersyair": 3, "kelaikan": 4,
        "pensyair": 3,
    }

    def test_roots(self):
        for word, want in self.ROOTS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_derivatives(self):
        for word, want in self.DERIVATIVES.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestH3NotAddedAudit6(unittest.TestCase):
    """H-3, against the audit: "koboi" and "boikot" are NOT
    hiatus in KBBI (ko·boi, boi·kot — 2), so they were NOT
    added. These pins stop a future round from "fixing" them
    to 3 on the audit's say-so alone."""

    def test_koboi_boikot_stay_two(self):
        cases = {
            "koboi": 2, "boikot": 2,
            "memboikot": 3, "pemboikot": 3, "pemboikotan": 4,
        }
        for word, want in cases.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestH4NasalRemnantsAudit6(unittest.TestCase):
    """H-4: nasal assimilation melts the root's initial
    consonant, leaving a vowel-initial remnant whose pair is
    still the root's hiatus ("mengait" = meng- + kait)."""

    WORDS = {
        "mengait": 3, "pengait": 3, "pengaitan": 4,
        "pengaitkan": 4, "mengaitkan": 4, "pengaitanmu": 5,
        "pengaitnya": 4, "pengaib": 3, "pengaiban": 4,
        "penyair": 3, "penyairan": 4, "bersair": 3,
        "penyairnya": 4, "peraih": 3, "meraup": 3,
        "meraupkan": 4, "menyaingi": 4, "penyaing": 3,
        "mengaum": 3, "mengaut": 3, "pengaut": 3,
        "peraup": 3, "raupan": 3, "seraup": 3,
    }

    # The (b) roots themselves, plus the (a) roots they hang on.
    ROOTS = {"sair": 2, "raup": 2, "aib": 2}

    # One more remnant path: "kepenyairan" (KBBI
    # ke·pe·nya·ir·an, 5) strips to "yair" + 3 affixes.
    EXTRA = {"kepenyairan": 5}

    def test_assimilated_words(self):
        for word, want in self.WORDS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_roots(self):
        for word, want in self.ROOTS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_extra(self):
        for word, want in self.EXTRA.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)

    def test_strip_leaves_remnant(self):
        # The mechanism, at the strip level: the remnant is what
        # _strip_id_affixes actually returns.
        cases = {
            "mengait": ("ait", 1, False),
            "penyair": ("yair", 1, False),
            "peraih": ("aih", 1, False),
            "menautkan": ("naut", 2, False),
            "menyaingi": ("yaing", 2, False),
        }
        for word, want in cases.items():
            with self.subTest(word=word):
                self.assertEqual(tools._strip_id_affixes(word), want)


class TestH4RemnantExtrasAudit6(unittest.TestCase):
    """H-4, same class, verified on the root pages: "mengail"
    (me·nga·il) and "pengail" (pe·nga·il) need remnant "ail";
    "mengais" (me·nga·is) and "mengaiskan" (me·nga·is·kan)
    need "ais"; "menaut" / "menautkan" (me·na·ut·kan) need
    "naut". "memaut" (me·ma·ut) needs no remnant — it strips
    to "maut", already an exception."""

    WORDS = {
        "mengail": 3, "pengail": 3,
        "mengais": 3, "mengaiskan": 4,
        "menaut": 3, "menautkan": 4, "memaut": 3,
    }

    def test_extras(self):
        for word, want in self.WORDS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestH4GuardsAudit6(unittest.TestCase):
    """H-4 guards: the fix must be lexical, never a blanket
    "split the first vowel pair after a nasal prefix". "memandai"
    is mem- + pandai — a real diphthong, 3, not 4. The other
    four are words the audit #6 coordinator confirmed were
    already right; pinning them stops a future round from
    "fixing" them."""

    GUARDS = {
        "memandai": 3, "mencintai": 3,
        "memperbaikinya": 6, "terperbaiki": 5,
        "disesuaikan": 6, "penyesuaian": 6,
        "pengembangan": 4, "ketersediaan": 6,
    }

    def test_guards(self):
        for word, want in self.GUARDS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


class TestT6VerifiedAudit6(unittest.TestCase):
    """T-6: the suspected words that KBBI verified. "kais" is
    ka·is (2), "deisme" de·is·me (3), "teisme" te·is·me (3).
    "geiser" is gei·ser (2) — the suspicion of 3 was wrong and
    the code was already right. "raib" has no kbbi.web.id entry
    at all: NOT added, NOT pinned (see module docstring)."""

    WORDS = {
        "kais": 2, "deisme": 3, "teisme": 3, "geiser": 2,
    }

    def test_verified(self):
        for word, want in self.WORDS.items():
            with self.subTest(word=word):
                self.assertEqual(tools._count_syllables(word), want)


if __name__ == "__main__":
    unittest.main()
