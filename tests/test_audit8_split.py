"""Audit #8 T-3: lowercase abbreviations do not split sentences.

Audit #8 H-5: abbreviation protection was case-sensitive, so
"dr."/"prof."/"bpk."/"tgl."/"cth."/"spt."/"dng." split
sentences ("dr. Budi pergi. Ia senang." came back as three
fragments). The abbreviations are now matched
case-insensitively, and the informal "cth." (contoh), "spt."
(seperti), "dng." (dengan) join the list.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestAudit8LowercaseAbbreviations(unittest.TestCase):
    """H-5: lowercase abbreviations protect like capitals."""

    CASES = {
        # The audit's own cases.
        "dr. Budi pergi. Ia senang.": 2,
        "Lihat cth. berikut. Ia pergi.": 2,
        # The other listed abbreviations.
        "Ia menemui prof. Budi. Ia senang.": 2,
        "Ia menemui bpk. Hadi. Ia senang.": 2,
        "Catat tgl. 12 Jan. 2020. Ia pergi.": 2,
        "Hasilnya spt. yang diduga. Ia pergi.": 2,
        "Buku itu dng. cepat dibaca. Ia pergi.": 2,
        # Lowercase chained degree: same accepted trade-off as
        # the capital form (one sentence — a title is never
        # sentence-final in real text).
        "Gelarnya dr. rer. nat. Ia mengajar.": 1,
        # Capital forms still work.
        "Dr. Budi pergi. Ia senang.": 2,
        "Ia pergi. Dr. Budi datang.": 2,
        "Lihat hlm. 5. Ia pergi.": 2,
    }

    GUARDS = {
        # A word that merely ends in the same letters is NOT
        # protected: "perihal." still splits (the \b guard).
        "Ia membahas perihal. Ia pergi.": 2,
        # The conditional rules are untouched: "dll." only
        # protects before a lowercase word.
        "Buku itu, dll. kemudian dibaca. Ia pergi.": 2,
        "Ia membeli buku, pensil, dll. Kemudian pulang.": 2,
    }

    def test_lowercase_abbreviations(self):
        for text, want in self.CASES.items():
            with self.subTest(text=text):
                got = tools._split_sentences(text)
                self.assertEqual(len(got), want, got)

    def test_guards_unchanged(self):
        for text, want in self.GUARDS.items():
            with self.subTest(text=text):
                got = tools._split_sentences(text)
                self.assertEqual(len(got), want, got)


if __name__ == "__main__":
    unittest.main()
