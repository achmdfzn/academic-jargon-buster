"""Audit #6 follow-up tests for the English syllable counter: H-5, N-7.

Audit #6 (on v1.27.3) found English systematically wrong: 69 of 207
words tested. The hiatus pairs ia/io/ua/ea were unhandled, plurals
of exception words were not looked up, "-ed" after a voiceless
consonant or vowel was not silenced, and ten irregular words
(N-7) were wrong. Every count here was verified against standard
English syllabification (the audit's word list, plus the fix
round's own 525-word regression battery — see the coordinator's
notes; only the documented misses below fail).

Two real bugs surfaced while fixing this, both worth remembering:
- "" in "lnt" is True in Python. The "ue" rule used `nxt in
  "lnt"` where nxt is "" at word end, so a word-final "ue"
  ("tissue", "blue") wrongly split. Every `in` check on prev/nxt
  now guards the empty string explicitly.
- The silent final "e" must not subtract when the "e" never
  formed its own vowel group: in "rueful" the "e" sits inside
  the "ue" run already counted as one, and in "enjoyed" the
  "e" of "-ed" sits inside the "oye" run. Both rules now require
  the "e" to start its own group (preceded by a consonant).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestEnglishHiatusAudit6(unittest.TestCase):
    """H-5: the hiatus pairs ia/io/ua/ea, plus ie/eo/ue/ao."""

    # The audit's hiatus words, all wrong under v1.27.3.
    AUDIT_HIATUS = {
        "various": 3, "theory": 3, "theories": 3, "theatre": 3,
        "theater": 3, "create": 2, "created": 2, "creating": 3,
        "creator": 3, "media": 3, "video": 3, "reality": 4,
        "realities": 4, "ideal": 3, "realize": 3, "realise": 3,
        "realistic": 4, "diarrhea": 4, "diarrhoea": 4, "poet": 2,
        "poems": 2, "poem": 2, "cooperate": 4, "coordinate": 4,
        "cooperation": 5, "ruin": 2, "fluid": 2, "genuine": 3,
        "influential": 4, "reaction": 3, "reactor": 3,
        "reactive": 3, "react": 2,
    }

    # "-ually" always splits (/u/ + /@/): usually, actually,
    # gradually, casually, spiritually — no letter rule separates
    # the s/t cases from the d/n/c cases, because they are the
    # same pattern.
    UALLY = {
        "usually": 4, "actually": 4, "eventually": 5,
        "gradually": 4, "manually": 4, "individually": 6,
        "dually": 3, "sexually": 4, "casually": 4,
        "spiritually": 5, "usual": 3, "actual": 3,
        "gradual": 3, "manual": 3, "individual": 5, "dual": 2,
        "sexual": 3, "casual": 3, "spiritual": 4,
    }

    # Guards: the pairs that must NOT split, and the words that
    # pin the guard boundaries.
    HIATUS_GUARDS = {
        # -cial/-tial/-tion/-sion/-cious/-tious/-xious.
        "special": 2, "official": 3, "dictionary": 4, "version": 2,
        "precious": 2, "cautious": 2, "anxious": 2, "partial": 2,
        "essential": 3, "potential": 3, "initial": 3,
        "spatial": 2, "martial": 2,
        # Word-initial "sc" is /s/ + vowel, not /S/.
        "scientific": 4, "scientist": 3, "sciatic": 3,
        "sciatica": 4, "scion": 2, "suspicion": 3, "fascia": 2,
        "glacial": 2, "allegiance": 3, "liaison": 3,
        # "io" after "n" is /j@/.
        "opinion": 3, "companion": 3, "dominion": 3, "minion": 2,
        "bunion": 2, "onion": 2, "union": 2, "reunion": 3,
        "communion": 3, "senior": 2, "junior": 2, "pinion": 2,
        # "ua" after q/g, before v; "ue" after q; "eo" before p.
        "quality": 3, "language": 2, "guard": 1, "suave": 1,
        "sequel": 2, "frequent": 2, "people": 2, "leopard": 2,
        "jeopardy": 3,
        # "ie" only before "t" + vowel/end, or "nce"/"nt".
        "diet": 2, "quiet": 2, "variety": 4, "society": 4,
        "experience": 4, "audience": 3, "client": 2,
        "patience": 2, "ancient": 2,
        # "ue" before l/n/t; "ao" before a consonant.
        "cruel": 2, "fuel": 2, "duel": 2, "fluent": 2,
        "influence": 3, "affluent": 3, "confluent": 3,
        "effluent": 3, "duet": 2, "suet": 2, "suede": 1,
        "dues": 1, "clues": 1, "chaos": 2, "chaotic": 3,
        "mao": 1,
        # "ia" after a vowel still splits (the "a" is its own
        # syllable: par-a-noi-a, se-quoi-a).
        "paranoia": 4, "sequoia": 3, "magnolia": 4, "dahlia": 3,
        "bacteria": 4, "mania": 3, "genial": 3, "radial": 3,
        "dial": 2, "iambic": 3, "equiangular": 5, "eohippus": 4,
        # Word-initial "io" (the empty-prev trap: "" in "tsn"
        # is True, so a bare `prev in "tsn"` blocked "ion").
        "ion": 2, "ions": 2, "ionic": 3, "ionize": 3,
        "ionization": 5, "ionosphere": 4,
    }

    def test_audit_hiatus(self):
        for word, want in self.AUDIT_HIATUS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_ually(self):
        for word, want in self.UALLY.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_hiatus_guards(self):
        for word, want in self.HIATUS_GUARDS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishPluralsAudit6(unittest.TestCase):
    """H-5: plurals of exception words look the base up."""

    PLURALS = {
        "ideas": 3, "areas": 3, "realities": 4, "theories": 3,
        "museums": 3, "reunions": 3, "reuses": 2, "reunites": 3,
        "trials": 2, "argues": 2, "segues": 2,
    }

    def test_plural_of_exception(self):
        for word, want in self.PLURALS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishEdAudit6(unittest.TestCase):
    """H-5: "-ed" is silent after a consonant, its own syllable
    after t/d — and only when the "e" starts its own group."""

    # Silent after a consonant (walked 1, not 2).
    SILENT_ED = {
        "walked": 1, "talked": 1, "baked": 1, "bored": 1,
        "tired": 1, "required": 2, "acquired": 2, "inspired": 2,
        "admired": 2, "expired": 2, "retired": 2, "desired": 2,
        "measured": 2, "bathed": 1, "clothed": 1, "breathed": 1,
        "reached": 1, "watched": 1, "matched": 1, "finished": 2,
        "published": 2, "established": 3, "fixed": 1, "mixed": 1,
        "boxed": 1, "organized": 3, "recognized": 3, "changed": 1,
        "managed": 2, "damaged": 2, "encouraged": 3,
        "described": 2, "absorbed": 2, "claimed": 1, "named": 1,
        "seemed": 1, "framed": 1, "concerned": 2, "designed": 2,
        "defined": 2, "combined": 2, "examined": 3,
        "determined": 3, "staffed": 1, "called": 1, "filled": 1,
        "killed": 1, "controlled": 2, "detailed": 2, "failed": 1,
        "traveled": 2, "chewed": 1, "viewed": 1, "reviewed": 2,
        "screwed": 1, "renewed": 2, "owed": 1, "allowed": 2,
        "followed": 2, "borrowed": 2, "harrowed": 2,
        "narrowed": 2,
    }

    # Its own syllable after t/d.
    PRONOUNCED_ED = {
        "wanted": 2, "needed": 2, "decided": 3, "bed": 1,
        "red": 1, "fed": 1, "led": 1, "shed": 1, "bled": 1,
        "bred": 1, "fled": 1, "sped": 1, "wed": 1,
    }

    # The "e" sits inside a vowel run already counted as one
    # ("oye" in "enjoyed", "aye" in "played") — no subtraction.
    ED_INSIDE_RUN = {
        "enjoyed": 2, "delayed": 2, "destroyed": 2, "played": 1,
        "stayed": 1, "prayed": 1, "indeed": 2, "agreed": 2,
        "freed": 1, "seed": 1, "speed": 1, "need": 1, "deed": 1,
        "breed": 1, "greed": 1, "weed": 1, "argued": 2,
        "segued": 2,
    }

    # Pronounced "-ed" anyway: pinned in _ENGLISH_EXCEPTIONS.
    ED_EXCEPTIONS = {
        "naked": 2, "wicked": 2, "rugged": 2, "beloved": 3,
        "learned": 2, "blessed": 2, "aged": 2, "dogged": 2,
        "jagged": 2, "sacred": 2, "crooked": 2, "wretched": 2,
        "ragged": 2, "hatred": 2, "hundred": 2, "kindred": 2,
    }

    def test_silent_ed(self):
        for word, want in self.SILENT_ED.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_pronounced_ed(self):
        for word, want in self.PRONOUNCED_ED.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_ed_inside_run(self):
        for word, want in self.ED_INSIDE_RUN.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_ed_exceptions(self):
        for word, want in self.ED_EXCEPTIONS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishIrregularsAudit6(unittest.TestCase):
    """N-7: irregular words no rule reaches. Dialect variants
    (chocolate, comfortable, extraordinary, interesting) are
    NOT forced — see the known misses below."""

    IRREGULARS = {
        "business": 2, "every": 2, "evening": 2,
        "definitely": 4, "wednesday": 2, "february": 4,
        "colonel": 2, "literature": 3, "vegetable": 3,
        "chaotic": 3, "laos": 1,
    }

    def test_irregulars(self):
        for word, want in self.IRREGULARS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishSilentEAudit6(unittest.TestCase):
    """The final "e" is silent unless it is part of a vowel
    digraph, the "ue" of a real vowel, or after consonant + "r";
    a medial "e" stays silent before -ly/-ful/-less/-ness."""

    # Digraph endings: the "e" is pronounced.
    DIGRAPH_E = {
        "agree": 2, "degree": 2, "coffee": 2, "canoe": 2,
        "tiptoe": 2, "movie": 2, "cookie": 2, "brownie": 2,
        "genie": 2, "zombie": 2, "selfie": 2, "sundae": 2,
        "algae": 2, "goodbye": 2, "queue": 1,
    }

    # "ue" after a consonant is a real vowel (no subtraction).
    UE_REAL = {
        "tissue": 2, "value": 2, "continue": 3, "issue": 2,
        "rescue": 2, "guarantee": 3,
    }

    # "qu"/"gu" is a glide: the "e" is silent. ("argue" and
    # "segue" are the exceptions — the "u" is a real vowel
    # there — and live in _ENGLISH_EXCEPTIONS.)
    QUE_GUE = {
        "antique": 2, "unique": 2, "technique": 2,
        "oblique": 2, "baroque": 2, "grotesque": 2,
        "picturesque": 3, "mosque": 1, "cheque": 1,
        "plaque": 1, "vague": 1, "tongue": 1, "league": 1,
        "plague": 1, "rogue": 1, "vogue": 1, "morgue": 1,
        "dialogue": 3, "colleague": 2, "intrigue": 2,
        "fatigue": 2, "argue": 2, "segue": 2,
    }

    # Consonant + "re" is pronounced; vowel + "r" is silent.
    RE_ENDING = {
        "centre": 2, "acre": 2, "fibre": 2, "more": 1,
        "care": 1, "desire": 2, "fire": 1,
    }

    # Plain silent final "e".
    PLAIN_E = {
        "make": 1, "one": 1, "blue": 1, "true": 1, "glue": 1,
        "due": 1, "clue": 1,
    }

    # Medial "e" before -ly/-ful/-less/-ness.
    MEDIAL_E = {
        "widely": 2, "completely": 3, "absolutely": 4,
        "entirely": 3, "carefully": 3, "largely": 2,
        "closely": 2, "rely": 2, "freely": 2, "hopeful": 2,
        "careful": 2, "useful": 2, "grateful": 2,
        "shameful": 2, "tasteful": 2, "wasteful": 2,
        "graceful": 2, "peaceful": 2, "rueful": 2, "woeful": 2,
        "hopefully": 3, "carefully": 3, "usefully": 3,
        "gratefully": 3, "shamefully": 3, "tastefully": 3,
        "wastefully": 3, "gracefully": 3, "peacefully": 3,
        "ruefully": 3, "woefully": 3, "careless": 2,
        "hopeless": 2, "useless": 2, "homeless": 2,
        "nameless": 2, "blameless": 2, "tasteless": 2,
        "shameless": 2, "priceless": 2, "timeless": 2,
        "ageless": 2, "faceless": 2, "carelessly": 3,
        "hopelessly": 3, "uselessly": 3, "awareness": 3,
        "likeness": 2, "politeness": 3, "forgiveness": 3,
        "fineness": 2,
        # No "-ness" pattern, so no subtraction.
        "darkness": 2, "goodness": 2, "kindness": 2,
        "happiness": 3, "sadness": 2, "weakness": 2,
        "illness": 2, "willingness": 3, "readiness": 3,
        "eagerness": 3, "cleverness": 3, "togetherness": 4,
        "keenness": 2, "greenness": 2, "cleanness": 2,
        "meanness": 2, "sheerness": 2,
    }

    def test_digraph_e(self):
        for word, want in self.DIGRAPH_E.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_ue_real(self):
        for word, want in self.UE_REAL.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_que_gue(self):
        for word, want in self.QUE_GUE.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_re_ending(self):
        for word, want in self.RE_ENDING.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_plain_e(self):
        for word, want in self.PLAIN_E.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)

    def test_medial_e(self):
        for word, want in self.MEDIAL_E.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishEuAudit6(unittest.TestCase):
    """H-5: "eu" has no rule — one sound word-initially
    ("eulogy") but two sounds across the re- boundary and in
    "museum". Pinned, not guessed."""

    EU_WORDS = {
        "reunion": 3, "reuse": 2, "reunite": 3, "reusable": 4,
        "reunification": 6, "museum": 3, "trial": 2,
    }

    def test_eu_words(self):
        for word, want in self.EU_WORDS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishGuardsAudit6(unittest.TestCase):
    """Words that were already right (audits #4/#5) and must
    stay right after the H-5 rewrite."""

    GUARDS = {
        "happy": 2, "study": 2, "reading": 2, "beautiful": 3,
        "the": 1, "yes": 1, "yesterday": 3, "one": 1,
        "fire": 1, "hour": 1, "aisle": 1, "isle": 1,
        "science": 2, "rhythm": 2, "real": 2, "idea": 3,
        "area": 3, "table": 2, "people": 2, "example": 3,
        "article": 3, "possible": 3, "syllable": 3,
        "little": 2, "bottle": 2, "candle": 2, "apple": 2,
        "able": 2, "simple": 2, "handle": 2, "middle": 2,
        "cycle": 2, "title": 2, "single": 2, "city": 2,
        "resource": 2, "organization": 5, "questionnaire": 3,
    }

    def test_guards(self):
        for word, want in self.GUARDS.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), want)


class TestEnglishKnownMissesAudit6(unittest.TestCase):
    """Documented misses — pinned at the CURRENT count so a
    future fix round notices if the count moves. Do not "fix"
    these by changing the expectation; fix the code. Only the
    deliberate dialect variant is left: every other miss this
    class once held ("management", "iou", "unscientific",
    "adobe", "phoebe", "chihuahua", "arguing") was fixed in
    audit #7/#8 and moved to its own test file."""

    # "management" 3 vs "element" 3 share the same "ement"
    # letters, so no "-ment" rule exists (it would trade one
    # error for another).
    #
    # Audit #7 corrections: "unscientific" 5, "adobe" 3,
    # "phoebe" 2, "chihuahua" 3, "arguing" 3 are FIXED (pinned
    # in test_audit7_track4.py), so they left this dict.
    # Audit #8 corrections: "management" 3 and "iou" 3 are
    # FIXED too (the guarded "-ment" rule + the "iou" pin —
    # pinned in tests/test_audit8_syllables.py), so they left
    # as well. "gruel" and "nescience" were never misses: the
    # majority of syllable dictionaries give 2 for both, and
    # the code already counts 2 — the old "want 1"/"want 3"
    # was wrong.
    KNOWN_MISSES = {
        # Dialect variants, deliberately unforced (N-7).
        "extraordinary": 6,  # AmE 5, BrE 6
    }

    def test_known_misses_pinned(self):
        for word, got in self.KNOWN_MISSES.items():
            with self.subTest(word=word):
                self.assertEqual(
                    tools._count_syllables(word, "en"), got)


if __name__ == "__main__":
    unittest.main()
