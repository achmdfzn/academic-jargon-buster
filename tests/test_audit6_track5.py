"""Audit #6 follow-up tests for _split_sentences: H-8, H-9.

Audit #6 (on v1.27.3) found _split_sentences did not protect common
Indonesian abbreviations (H-8) and split a quoted sentence from its
lowercase continuation (H-9).

H-8: the new abbreviations fall into four classes, and the class
decides the rule — this is the point of the fix, so the classes
are tested separately, not as one flat list:

- Titles (Sdri./Yth./Ir./Hj.): unconditional, like the Dr./Prof./
  Bpk. already in _ABBREVIATIONS. A title is followed by a name
  and is never sentence-final in real text, so the "end of
  sentence" case for a title is that the sentence containing it
  still ends at its real terminator ("Ir. Budi datang. Ia pergi."
  is two sentences) — the same convention audit #5 used for
  Bpk./hlm.
- List abbreviation (dsb.): conditional, like dll./dst./dkk.
  (audit #5 H-6) — protected only before a lowercase word.
- Addresses (Jln./Jl./Gg./Rt./Rw.) and editions/volumes
  (Ed./Vol./Cet.): unconditional, like "No." (also digit-followed)
  and hlm. They are followed by a capital street name, a number,
  or a Roman numeral ("Vol. IV"), never by the end of a sentence;
  their "end" case is again that the containing sentence still
  ends correctly.
- Dates (Tgl./Th. and the dotted months Jan./Feb./.../Des.;
  "Mei" has no period, so it is not an abbreviation): the ONE
  conditional class besides the list abbreviations, because a
  date CAN genuinely end a sentence ("Rapat pada 12 Jan. Besok
  libur." is two sentences). Protected only when the next token
  is a digit ("12 Jan. 2020", "Tgl. 12") or a lowercase word
  ("Jan. lalu", "Jan. adalah ...").

- "Dr. rer. nat." is a chained degree: protected as a whole
  phrase, not as standalone "rer."/"nat.", which are not
  abbreviations on their own.

H-9 (confirmed rule, do not re-ask): terminator + closing
quote/paren + lowercase continuation does NOT split. "Dia
berkata, 'Saya takut!' sambil menangis." is one sentence. The
capital-after-quote behaviour is kept: "'Jangan!' Begitu
katanya." is still two sentences. The rule applies only when
closers are present: "Dia pergi. sambil menangis." still splits.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools


class TestNewHonorificsAudit6(unittest.TestCase):
    """H-8: Sdri./Yth./Ir./Hj. never split, like Dr./Prof./Bpk."""

    # Abbreviation mid-sentence: one sentence, no split.
    MID = {
        "Sdri. Sari datang.": ["Sdri. Sari datang"],
        "Yth. Bapak Rektor hadir.": ["Yth. Bapak Rektor hadir"],
        "Ir. Budi memimpin proyek itu.": ["Ir. Budi memimpin proyek itu"],
        "Hj. Aminah datang.": ["Hj. Aminah datang"],
        "Surat untuk Yth. Bapak Rektor telah tiba.":
            ["Surat untuk Yth. Bapak Rektor telah tiba"],
        "Ir. Budi dan Hj. Aminah hadir.": ["Ir. Budi dan Hj. Aminah hadir"],
    }

    # The sentence containing the title still ends at its real
    # terminator (a title is never sentence-final in real text).
    END = {
        "Sdri. Sari datang. Ia tersenyum.":
            ["Sdri. Sari datang", "Ia tersenyum"],
        "Yth. Bapak Rektor hadir. Rapat dimulai.":
            ["Yth. Bapak Rektor hadir", "Rapat dimulai"],
        "Ir. Budi datang. Ia bangga.": ["Ir. Budi datang", "Ia bangga"],
        "Hj. Aminah datang. Ia tersenyum.":
            ["Hj. Aminah datang", "Ia tersenyum"],
        "Surat untuk Yth. Bapak Rektor telah tiba. Besok dibalas.":
            ["Surat untuk Yth. Bapak Rektor telah tiba", "Besok dibalas"],
    }

    def test_honorific_mid_sentence_does_not_split(self):
        for text, want in self.MID.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)

    def test_honorific_sentence_still_ends(self):
        for text, want in self.END.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)


class TestDsbAudit6(unittest.TestCase):
    """H-8: dsb. joins dll./dst./dkk. — protected only before a
    lowercase word (audit #5 H-6)."""

    def test_dsb_before_lowercase_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Buku, pensil, dsb. dibeli semua. Lalu disimpan."),
            ["Buku, pensil, dsb. dibeli semua", "Lalu disimpan"])

    def test_dsb_before_capital_ends_sentence(self):
        self.assertEqual(
            tools._split_sentences(
                "Ia membeli buku, dsb. Kemudian pulang."),
            ["Ia membeli buku, dsb", "Kemudian pulang"])

    def test_dsb_at_end_of_text(self):
        self.assertEqual(
            tools._split_sentences("Ia membeli buku, dsb."),
            ["Ia membeli buku, dsb"])


class TestAddressAbbreviationsAudit6(unittest.TestCase):
    """H-8: Jln./Jl./Gg./Rt./Rw. never split — followed by a
    capital street name or a number, never by a sentence end."""

    MID = {
        "Ia tinggal di Jl. Sudirman No. 5.":
            ["Ia tinggal di Jl. Sudirman No. 5"],
        "Kantor di Jln. Thamrin No. 10.":
            ["Kantor di Jln. Thamrin No. 10"],
        "Rumahnya di Gg. Melati No. 3.":
            ["Rumahnya di Gg. Melati No. 3"],
        "Ia tinggal di Rt. 05 Rw. 10.":
            ["Ia tinggal di Rt. 05 Rw. 10"],
        "Alamatnya Jl. Merdeka.": ["Alamatnya Jl. Merdeka"],
    }

    END = {
        "Ia tinggal di Jl. Sudirman. Besok pindah.":
            ["Ia tinggal di Jl. Sudirman", "Besok pindah"],
        "Kantor di Jln. Thamrin No. 10. Ia bekerja.":
            ["Kantor di Jln. Thamrin No. 10", "Ia bekerja"],
        "Rumahnya di Gg. Melati No. 3. Ia senang.":
            ["Rumahnya di Gg. Melati No. 3", "Ia senang"],
        "Ia tinggal di Rt. 05 Rw. 10. Besok pindah.":
            ["Ia tinggal di Rt. 05 Rw. 10", "Besok pindah"],
    }

    def test_address_mid_sentence_does_not_split(self):
        for text, want in self.MID.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)

    def test_address_sentence_still_ends(self):
        for text, want in self.END.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)


class TestEditionVolumeAudit6(unittest.TestCase):
    """H-8: Ed./Vol./Cet. never split — followed by a number or a
    Roman numeral ("Vol. IV"), never by a sentence end."""

    MID = {
        "Lihat Vol. 3 No. 2 untuk detail.":
            ["Lihat Vol. 3 No. 2 untuk detail"],
        "Buku Ed. 2 terbit tahun lalu.":
            ["Buku Ed. 2 terbit tahun lalu"],
        "Cet. 1 sudah habis.": ["Cet. 1 sudah habis"],
        "Vol. IV No. 1 terbit.": ["Vol. IV No. 1 terbit"],
    }

    END = {
        "Lihat Vol. 3 No. 2 untuk detail. Bab dua dimulai.":
            ["Lihat Vol. 3 No. 2 untuk detail", "Bab dua dimulai"],
        "Buku Ed. 2 terbit tahun lalu. Ia senang.":
            ["Buku Ed. 2 terbit tahun lalu", "Ia senang"],
        "Cet. 1 sudah habis. Cet. 2 terbit.":
            ["Cet. 1 sudah habis", "Cet. 2 terbit"],
        "Vol. IV No. 1 terbit. Ia bangga.":
            ["Vol. IV No. 1 terbit", "Ia bangga"],
    }

    def test_edition_mid_sentence_does_not_split(self):
        for text, want in self.MID.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)

    def test_edition_sentence_still_ends(self):
        for text, want in self.END.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)


class TestDateAbbreviationsAudit6(unittest.TestCase):
    """H-8: Tgl./Th. and the dotted months are protected only
    before a digit or a lowercase word — a date can genuinely
    end a sentence, so a capitalised next word still splits."""

    # All twelve dotted months ("Mei" has no period): protected
    # before the year, splitting before the next sentence.
    MONTHS = ("Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.",
              "Agu.", "Sep.", "Okt.", "Nov.", "Des.")

    def test_month_before_year_does_not_split(self):
        for m in self.MONTHS:
            with self.subTest(month=m):
                self.assertEqual(
                    tools._split_sentences(f"Rapat 12 {m} 2020 diadakan."),
                    [f"Rapat 12 {m} 2020 diadakan"])

    def test_month_at_sentence_end_still_splits(self):
        for m in self.MONTHS:
            with self.subTest(month=m):
                # The month's period is the sentence terminator
                # here, so it is stripped from the returned
                # sentence — same as "dll." in the audit #5 tests.
                self.assertEqual(
                    tools._split_sentences(f"Rapat pada 12 {m} Besok libur."),
                    [f"Rapat pada 12 {m.rstrip('.')}", "Besok libur"])

    def test_month_before_lowercase_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Jan. lalu rapat dibatalkan. Kini dijadwalkan."),
            ["Jan. lalu rapat dibatalkan", "Kini dijadwalkan"])
        self.assertEqual(
            tools._split_sentences(
                "Jan. adalah bulan pertama. Feb. kedua."),
            ["Jan. adalah bulan pertama", "Feb. kedua"])

    def test_tgl_and_th_before_year_do_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Tgl. 12 Jan. 2020 adalah awal. Ia ingat."),
            ["Tgl. 12 Jan. 2020 adalah awal", "Ia ingat"])
        self.assertEqual(
            tools._split_sentences("Laporan Th. 2020 terbit. Ia bangga."),
            ["Laporan Th. 2020 terbit", "Ia bangga"])

    def test_date_at_end_of_text(self):
        self.assertEqual(
            tools._split_sentences("Rapat 12 Jan."),
            ["Rapat 12 Jan"])


class TestChainedDegreeAudit6(unittest.TestCase):
    """H-8: "Dr. rer. nat." is one title — the whole phrase is
    protected, not just "Dr."."""

    def test_chained_degree_does_not_split(self):
        self.assertEqual(
            tools._split_sentences(
                "Dr. rer. nat. Ahmad memimpin penelitian. Hasilnya bagus."),
            ["Dr. rer. nat. Ahmad memimpin penelitian", "Hasilnya bagus"])

    def test_chained_degree_sentence_still_ends(self):
        self.assertEqual(
            tools._split_sentences(
                "Penelitian dipimpin Dr. rer. nat. Ahmad. Hasilnya bagus."),
            ["Penelitian dipimpin Dr. rer. nat. Ahmad", "Hasilnya bagus"])


class TestClosingQuoteLowercaseAudit6(unittest.TestCase):
    """H-9: terminator + closing quote/paren + lowercase
    continuation is ONE sentence; capital still splits."""

    # Quote/paren + lowercase: one sentence.
    LOWERCASE_ONE = {
        "Dia berkata, 'Saya takut!' sambil menangis.":
            ["Dia berkata, 'Saya takut!' sambil menangis"],
        'Dia berkata, "Saya takut!" sambil menangis.':
            ['Dia berkata, "Saya takut!" sambil menangis'],
        "Ia bertanya, 'Kapan pulang?' sambil menatapku.":
            ["Ia bertanya, 'Kapan pulang?' sambil menatapku"],
        "(Ia pergi.) sambil menangis.":
            ["(Ia pergi.) sambil menangis"],
        "Dia berkata, 'Pergi!') sambil menangis.":
            ["Dia berkata, 'Pergi!') sambil menangis"],
        "Dia berkata, 'Saya takut!' sambil menangis. Ia pergi.":
            ["Dia berkata, 'Saya takut!' sambil menangis", "Ia pergi"],
    }

    # Quote/paren + capital: still two sentences.
    CAPITAL_TWO = {
        "'Jangan!' Begitu katanya.":
            ["'Jangan!'", "Begitu katanya"],
        "Dia berkata 'Pergi!') Lalu diam.":
            ["Dia berkata 'Pergi!')", "Lalu diam"],
        "'Jangan!' Begitu katanya. Lalu pergi.":
            ["'Jangan!'", "Begitu katanya", "Lalu pergi"],
    }

    def test_quote_paren_lowercase_is_one_sentence(self):
        for text, want in self.LOWERCASE_ONE.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)

    def test_quote_paren_capital_still_splits(self):
        for text, want in self.CAPITAL_TWO.items():
            with self.subTest(text=text):
                self.assertEqual(tools._split_sentences(text), want)

    def test_no_closers_still_splits_normally(self):
        # The lowercase rule applies ONLY after a closing quote
        # or parenthesis — without closers the old behaviour
        # (split) is unchanged.
        self.assertEqual(
            tools._split_sentences("Dia pergi. sambil menangis."),
            ["Dia pergi", "sambil menangis"])
        self.assertEqual(
            tools._split_sentences("Dia pergi. Sambil menangis."),
            ["Dia pergi", "Sambil menangis"])


class TestSplitGuardsAudit6(unittest.TestCase):
    """Behaviour verified clean in audit #6 that must stay true
    after the H-8/H-9 changes."""

    def test_dr_a_budi_initial_does_not_split(self):
        self.assertEqual(
            tools._split_sentences("Dr. A. Budi datang. Ia pergi."),
            ["Dr. A. Budi datang", "Ia pergi"])

    def test_dll_before_capital_still_splits(self):
        self.assertEqual(
            tools._split_sentences(
                "Ia membeli buku, pensil, dll. Kemudian pulang."),
            ["Ia membeli buku, pensil, dll", "Kemudian pulang"])

    def test_hlm_and_bpk_still_protected(self):
        self.assertEqual(
            tools._split_sentences(
                "Lihat hlm. 12 untuk detail. Bab dua dimulai."),
            ["Lihat hlm. 12 untuk detail", "Bab dua dimulai"])
        self.assertEqual(
            tools._split_sentences("Bpk. Ahmad datang. Ia tersenyum."),
            ["Bpk. Ahmad datang", "Ia tersenyum"])

    def test_nested_closers_still_split_correctly(self):
        self.assertEqual(
            tools._split_sentences(
                "Dia berkata 'Pergi!') Lalu diam. Semua hening."),
            ["Dia berkata 'Pergi!')", "Lalu diam", "Semua hening"])
        self.assertEqual(
            tools._split_sentences("Hebat!) Lalu pergi."),
            ["Hebat!)", "Lalu pergi"])


if __name__ == "__main__":
    unittest.main()
