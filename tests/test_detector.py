"""Tests for detect_ai, the `detect` subcommand, and its menu entry.

The calibration texts below are written from scratch for this repo
(no source, no copied detector output): three human-like texts with
varied sentence lengths, an idiosyncratic voice, and no template
phrases, and three AI-like texts with uniform sentences, dense
template phrases, and repetitive vocabulary. The contract is the
separation: every human-like text scores under 40, every AI-like
text scores over 60.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools

# --- Calibration texts (original, written from scratch) ---------------

HUMAN_1 = (
    "Saya sampai di desa itu jam enam pagi, dan kabutnya masih tebal sekali. "
    "Jalan tanahnya licin — semalam hujan. "
    "Pak RT menyambut kami dengan kopi tubruk yang manisnya kebangetan, terus ketawa waktu saya tanya soal sinyal: "
    "'Di sini, sinyal itu kayak hantu. Kadang ada, kadang tidak.' "
    "Saya catat itu. Bukan karena lucu saja, tapi karena kalimat seperti itulah yang menjelaskan "
    "kenapa warga lebih percaya radio desa daripada grup WhatsApp. "
    "Tiga hari saya tinggal di sana, dan baru di hari ketiga saya paham: "
    "teknologi yang bagus itu yang tidak memaksa orang berubah. "
    "Ia menyesuaikan diri. Atau ditinggalkan."
)

HUMAN_2 = (
    "Percobaan kedua gagal total. Bukan gagal sedikit — gagal total. "
    "Larutannya berubah jadi cokelat pekat, bau gosong, dan suhu tabung naik sampai 90 derajat "
    "padahal termostatnya saya setel 60. "
    "Saya cek ulang semua: timbangan? Beres. pH meter? Baru dikalibrasi kemarin. "
    "Ternyata, dan ini memalukan, saya salah baca label — botol yang saya pakai itu asam sulfat pekat, bukan yang encer. "
    "Teman saya, Dita, cuma bilang, 'Lain kali baca dulu, baru tuang.' Dia benar. "
    "Minggu depannya saya ulang dari nol, kali ini dengan checklist di kertas yang saya tempel di dinding, "
    "persis di depan mata. Hasilnya? Normal. Akhirnya."
)

HUMAN_3 = (
    "Jujur saja, saya benci membaca jurnal tahun 80-an. "
    "Kertasnya kuning, font-nya kecil, dan setiap halaman rasanya seperti sedang membaca surat dari zaman lain. "
    "Tapi kemarin saya menemukan satu artikel yang membuat saya duduk tegak: penulisnya, entah siapa namanya — "
    "saya lupa, catatannya hilang di tas — menulis dengan cara yang sangat aneh untuk zamannya. "
    "Ia bercerita dulu, baru berteori. "
    "Dua halaman pertama isinya cerita tentang pasar ikan di Bergen, lengkap dengan bau dan suara. "
    "Baru di halaman tiga ia bicara soal model. Apakah itu buruk? Mungkin, menurut standar sekarang. "
    "Tapi saya membacanya sampai habis tanpa menguap sekali pun. "
    "Kapan terakhir kali sebuah jurnal melakukan itu pada saya?"
)

AI_1 = (
    "Penelitian ini bertujuan untuk menganalisis pengaruh media sosial terhadap prestasi belajar siswa. "
    "Penelitian ini juga mengkaji peran motivasi belajar dalam proses pembelajaran di sekolah. "
    "Penelitian ini mengukur durasi penggunaan media sosial harian melalui kuesioner terstruktur. "
    "Penelitian ini menemukan bahwa penggunaan berlebihan menurunkan prestasi belajar siswa secara signifikan. "
    "Selain itu, motivasi belajar berperan sebagai faktor penting dalam keberhasilan akademik siswa. "
    "Perlu dicatat bahwa media sosial memiliki dampak yang signifikan terhadap perilaku belajar siswa. "
    "Dalam hal ini, guru dan orang tua perlu mengawasi penggunaan media sosial anak. "
    "Secara keseluruhan, media sosial harus digunakan secara bijak oleh siswa. "
    "Dengan demikian, prestasi belajar dapat meningkat melalui penggunaan media sosial yang terkontrol. "
    "Sebagai kesimpulan, penelitian ini memberikan rekomendasi bagi guru dan orang tua siswa."
)

AI_2 = (
    "Pembelajaran daring telah menjadi bagian penting dari pendidikan modern saat ini. "
    "Pembelajaran daring memungkinkan siswa belajar dari mana saja tanpa batasan waktu. "
    "Pembelajaran daring juga memberikan fleksibilitas bagi guru dalam menyampaikan materi pelajaran. "
    "Selain itu, pembelajaran daring membutuhkan koneksi internet yang stabil dan perangkat yang memadai. "
    "Hasil penelitian menunjukkan bahwa siswa daring membutuhkan disiplin diri yang tinggi. "
    "Perlu dicatat bahwa interaksi tatap muka tetap penting dalam proses pembelajaran daring. "
    "Dalam hal ini, guru harus merancang aktivitas yang menarik bagi siswa daring. "
    "Secara keseluruhan, pembelajaran daring menawarkan banyak manfaat bagi pendidikan modern. "
    "Dengan demikian, sekolah perlu menyediakan dukungan teknis bagi guru dan siswa daring. "
    "Sebagai kesimpulan, pembelajaran daring akan terus berkembang di masa yang akan datang."
)

AI_3 = (
    "Pelaku UMKM merupakan tulang punggung perekonomian Indonesia yang sangat penting. "
    "Pelaku UMKM menghadapi berbagai tantangan dalam era digital yang terus berkembang. "
    "Pelaku UMKM perlu beradaptasi dengan teknologi digital untuk tetap bersaing di pasar. "
    "Selain itu, pemasaran digital membantu UMKM menjangkau pelanggan yang lebih luas. "
    "Hasil penelitian menunjukkan bahwa UMKM digital mengalami peningkatan omzet yang signifikan. "
    "Perlu dicatat bahwa literasi digital menjadi kunci keberhasilan UMKM di era modern. "
    "Dalam hal ini, pemerintah perlu memberikan pelatihan digital bagi pelaku UMKM. "
    "Secara keseluruhan, transformasi digital membawa peluang besar bagi UMKM Indonesia. "
    "Dengan demikian, UMKM dapat meningkatkan daya saing melalui teknologi digital. "
    "Sebagai kesimpulan, digitalisasi menjadi langkah penting bagi masa depan UMKM."
)

HUMAN_TEXTS = (HUMAN_1, HUMAN_2, HUMAN_3)
AI_TEXTS = (AI_1, AI_2, AI_3)


class TestCalibration(unittest.TestCase):
    def test_human_like_texts_score_under_40(self):
        for text in HUMAN_TEXTS:
            result = tools.detect_ai(text)
            self.assertLess(result["ai_score"], 40, result)
            self.assertEqual(result["verdict"], "Kemungkinan besar manusia")

    def test_ai_like_texts_score_over_60(self):
        for text in AI_TEXTS:
            result = tools.detect_ai(text)
            self.assertGreater(result["ai_score"], 60, result)

    def test_ai_like_texts_reach_the_ai_verdict(self):
        # T-1: the calibration contract is a verdict, not just a
        # number — every AI-like text has all 4 signals applicable,
        # so none of them is capped and all reach the top band.
        for text in AI_TEXTS:
            result = tools.detect_ai(text)
            self.assertEqual(
                sum(1 for s in result["signals"].values()
                    if s["applicable"]), 4, result)
            self.assertFalse(result["verdict_capped"])
            self.assertEqual(result["verdict"], "Kemungkinan besar AI")

    def test_calibration_texts_are_separated(self):
        human = [tools.detect_ai(t)["ai_score"] for t in HUMAN_TEXTS]
        ai = [tools.detect_ai(t)["ai_score"] for t in AI_TEXTS]
        self.assertLess(max(human), min(ai))
        # The gap is wide on purpose: the bands (40 / 60) sit inside it.
        self.assertLess(max(human), 40)
        self.assertGreater(min(ai), 60)

    def test_result_shape(self):
        result = tools.detect_ai(AI_1)
        self.assertEqual(set(result),
                         {"ai_score", "verdict", "verdict_capped",
                          "verdict_capped_reason", "signals", "sentences",
                          "note"})
        self.assertEqual(set(result["signals"]),
                         {"burstiness", "template_phrases",
                          "lexical_diversity", "starter_repetition"})
        for sig in result["signals"].values():
            self.assertIn("score", sig)
            self.assertIn("weight", sig)
            self.assertIn("applicable", sig)
        # The honesty note is always attached.
        self.assertIn("heuristik", result["note"])
        self.assertIn("bukan bukti", result["note"])

    def test_sentence_scores_are_sorted_and_highlight_ai_text(self):
        human = tools.detect_ai(HUMAN_1)
        self.assertEqual([s["score"] for s in human["sentences"]],
                         sorted([s["score"] for s in human["sentences"]],
                                reverse=True))
        # No human sentence reaches the 70 highlight threshold.
        self.assertTrue(all(s["score"] < 70 for s in human["sentences"]))
        ai = tools.detect_ai(AI_1)
        top = [s for s in ai["sentences"] if s["score"] >= 70]
        self.assertEqual(len(top), 6)
        self.assertIn("Selain itu", top[0]["sentence"])


class TestSignals(unittest.TestCase):
    def test_burstiness_uniform_sentences_score_high(self):
        # 7 identical sentences: CV 0 -> burstiness 100.
        uniform = " ".join(
            ["Kalimat ini terdiri dari tepat dua belas kata yang sama panjangnya."] * 7)
        result = tools.detect_ai(uniform)
        self.assertEqual(result["signals"]["burstiness"]["score"], 100.0)

    def test_burstiness_varied_sentences_score_low(self):
        result = tools.detect_ai(HUMAN_1)
        self.assertEqual(result["signals"]["burstiness"]["score"], 0.0)

    def test_burstiness_not_applicable_under_three_sentences(self):
        text = ("Satu kalimat yang cukup panjang untuk dihitung kata-katanya dengan benar. "
                "Dua kalimat pendek saja ditambah banyak kata kata kata kata kata kata kata "
                "kata kata kata kata kata kata kata kata kata kata kata kata kata.")
        result = tools.detect_ai(text)
        self.assertFalse(result["signals"]["burstiness"]["applicable"])
        self.assertIsNone(result["signals"]["burstiness"]["score"])

    def test_template_density_drives_the_signal(self):
        # 30+ words, one template phrase -> small score; four -> 100.
        base = ("Penelitian tentang kebiasaan membaca mahasiswa di perpustakaan kampus "
                "menunjukkan pola yang menarik dan berbeda dari dugaan awal para peneliti. "
                "Responden dipilih secara acak dari berbagai fakultas dan angkatan yang berbeda. ")
        one = base + "Selain itu, hasil survei mendukung temuan tersebut."
        result = tools.detect_ai(one)
        self.assertEqual(result["signals"]["template_phrases"]["count"], 1)
        self.assertLess(result["signals"]["template_phrases"]["score"], 60)
        dense = base + ("Selain itu, data menunjukkan hal yang sama. "
                        "Dengan demikian, kesimpulan dapat ditarik dengan jelas. "
                        "Secara keseluruhan, temuan ini konsisten dan dapat diandalkan. "
                        "Sebagai kesimpulan, penelitian ini memberikan gambaran yang jelas.")
        result = tools.detect_ai(dense)
        self.assertEqual(result["signals"]["template_phrases"]["score"], 100.0)

    def test_lexical_diversity_repetitive_text_scores_high(self):
        repetitive = (("kata " * 110).strip() + ".")
        result = tools.detect_ai(repetitive)
        self.assertGreater(result["signals"]["lexical_diversity"]["score"], 90)

    def test_starter_repetition_needs_six_sentences(self):
        text = ("Satu kalimat pembuka yang panjang dan berisi banyak kata penting. "
                "Dua kalimat pembuka yang juga panjang dan berisi banyak kata. "
                "Tiga kalimat pembuka yang panjang dan berisi cukup banyak kata. "
                "Empat kalimat pembuka yang panjang dan berisi banyak kata juga. "
                "Lima kalimat pembuka yang panjang dan berisi banyak kata penting.")
        result = tools.detect_ai(text)
        self.assertFalse(result["signals"]["starter_repetition"]["applicable"])

    def test_starter_repetition_same_opening_scores_high(self):
        text = ("Penelitian ini memakai metode survei yang terstruktur dan sistematis. "
                "Penelitian ini memakai kuesioner tertutup dengan skala Likert lima poin. "
                "Penelitian ini memakai sampel acak sebanyak seratus dua puluh responden terpilih. "
                "Penelitian ini memakai analisis regresi untuk menguji hubungan antarvariabel penelitian. "
                "Penelitian ini memakai wawancara mendalam dengan sepuluh informan kunci terpilih. "
                "Penelitian ini memakai observasi lapangan selama tiga bulan di lokasi penelitian.")
        result = tools.detect_ai(text)
        self.assertEqual(result["signals"]["starter_repetition"]["starter"],
                         "penelitian ini")
        self.assertEqual(result["signals"]["starter_repetition"]["share"], 1.0)
        self.assertEqual(result["signals"]["starter_repetition"]["score"], 100.0)

    def test_weights_renormalize_when_a_signal_is_not_applicable(self):
        # 2 sentences, 100+ words: burstiness and starter repetition
        # are not applicable, so only template (30) + lexical (20)
        # carry the score.
        text = ("Satu kalimat yang sangat panjang sekali dengan banyak kata yang menjelaskan "
                "metode penelitian secara rinci dan sistematis tanpa henti dan tanpa jeda sama "
                "sekali dalam setiap bagian yang panjang dan berbelit dan membingungkan bagi "
                "pembaca awam yang baru pertama kali membaca naskah ilmiah seperti ini di "
                "perpustakaan kampus yang sepi dan tenang pada sore hari yang cerah. "
                "Kalimat kedua yang juga sangat panjang sekali dengan banyak kata yang menjelaskan "
                "hasil penelitian secara rinci dan sistematis tanpa henti dan tanpa jeda sama "
                "sekali dalam setiap bagian yang panjang dan berbelit dan membingungkan bagi "
                "pembaca awam yang baru pertama kali membaca naskah ilmiah seperti ini di "
                "perpustakaan kampus yang sepi dan tenang pada sore hari yang cerah.")
        result = tools.detect_ai(text)
        self.assertFalse(result["signals"]["burstiness"]["applicable"])
        self.assertFalse(result["signals"]["starter_repetition"]["applicable"])
        expected = (result["signals"]["template_phrases"]["score"] * 30
                    + result["signals"]["lexical_diversity"]["score"] * 20) / 50
        self.assertAlmostEqual(result["ai_score"], round(expected, 1))


class TestEdgeCases(unittest.TestCase):
    def test_short_text_is_too_short(self):
        result = tools.detect_ai("Ini teks pendek sekali.")
        self.assertIsNone(result["ai_score"])
        self.assertEqual(result["verdict"], "Teks terlalu pendek")
        self.assertEqual(result["signals"], {})
        self.assertEqual(result["sentences"], [])
        self.assertIn("heuristik", result["note"])

    def test_twenty_nine_words_is_too_short(self):
        text = " ".join(["kata"] * 29) + "."
        result = tools.detect_ai(text)
        self.assertIsNone(result["ai_score"])

    def test_thirty_words_is_scored(self):
        text = " ".join(["kata"] * 30) + "."
        result = tools.detect_ai(text)
        self.assertIsNotNone(result["ai_score"])

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError) as cm:
            tools.detect_ai("   ")
        self.assertEqual(str(cm.exception), "teks kosong")
        with self.assertRaises(ValueError):
            tools.detect_ai("")

    def test_verdict_bands(self):
        self.assertEqual(tools.detect_ai(HUMAN_1)["verdict"],
                         "Kemungkinan besar manusia")
        self.assertEqual(tools.detect_ai(AI_1)["verdict"],
                         "Kemungkinan besar AI")
        # Uniform sentences + dense templates read as AI, even when short:
        # the weak signals no longer dilute the two strong ones — but
        # only two signals apply to this short text, so the verdict is
        # capped at "Campuran" instead of "Kemungkinan besar AI".
        light = ("Teknologi informasi telah mengubah cara perusahaan beroperasi dalam satu dekade terakhir. "
                 "Perusahaan yang mengadopsi teknologi digital dapat meningkatkan efisiensi operasional mereka. "
                 "Selain itu, teknologi digital memungkinkan perusahaan menjangkau pasar yang lebih luas. "
                 "Dalam hal ini, transformasi digital menjadi kebutuhan bagi perusahaan modern. "
                 "Perusahaan harus berinvestasi dalam teknologi untuk tetap kompetitif di pasar global.")
        result = tools.detect_ai(light)
        self.assertGreaterEqual(result["ai_score"], 60)
        self.assertTrue(result["verdict_capped"])
        self.assertIn("2 dari 4", result["verdict_capped_reason"])
        self.assertEqual(result["verdict"], "Campuran / tidak pasti")
        # Uniform sentences but no template phrases: honestly uncertain.
        mixed = ("Perusahaan teknologi itu berdiri pada tahun dua ribu lima belas di sebuah ruko kecil. "
                 "Pendirinya, seorang insinyur muda, memulai usaha dengan modal pinjaman dari keluarga dekat. "
                 "Produk pertama mereka gagal total karena tidak ada yang mau membelinya di pasaran. "
                 "Tahun berikutnya tim itu mengubah strategi dan fokus ke pelanggan korporat besar saja. "
                 "Sekarang perusahaan tersebut mempekerjakan lebih dari dua ratus karyawan tetap di tiga kota.")
        result = tools.detect_ai(mixed)
        self.assertEqual(result["verdict"], "Campuran / tidak pasti")

    def test_english_uses_the_english_phrase_list(self):
        ai_en = ("This study aims to analyze the impact of social media on student performance. "
                 "This study also examines the role of motivation in the learning process at school. "
                 "This study measures daily social media use through a structured questionnaire. "
                 "Moreover, motivation plays an important role in academic success. "
                 "It is important to note that social media has a significant impact on student behavior. "
                 "In conclusion, this study provides recommendations for teachers and parents.")
        result = tools.detect_ai(ai_en, lang="en")
        self.assertEqual(result["signals"]["template_phrases"]["count"], 3)
        # Uniform sentences + dense templates + repeated "This study"
        # opening: confidently AI-like.
        self.assertGreaterEqual(result["ai_score"], 70)
        self.assertEqual(result["verdict"], "Likely AI")
        self.assertIn("heuristic", result["note"])
        human_en = ("I got to the village at six in the morning and the fog was still thick. "
                    "The dirt road was slippery — it had rained all night. "
                    "The village head welcomed us with coffee so sweet it made my teeth ache, then laughed when I asked about the signal. "
                    "Three days I stayed there, and only on the third day did I understand: good technology does not force people to change. "
                    "It adapts. Or it gets left behind.")
        result = tools.detect_ai(human_en, lang="en")
        self.assertLess(result["ai_score"], 40)
        self.assertEqual(result["verdict"], "Likely human")

    def test_unknown_lang_falls_back_to_id(self):
        result = tools.detect_ai(HUMAN_1, lang="xx")
        self.assertEqual(result["verdict"], "Kemungkinan besar manusia")


class TestVerdictCap(unittest.TestCase):
    """B-1: the top verdict needs a score >= 60 AND >= 3 signals.

    A short text has only burstiness + template phrases applicable;
    stiff human prose trips both, so the score is honest but the
    verdict is capped at "Campuran / tidak pasti".
    """

    METHODS_PARAGRAPH = (
        "Penelitian ini menggunakan metode survei. "
        "Data dikumpulkan melalui kuesioner yang disebarkan kepada responden. "
        "Selain itu, wawancara dilakukan dengan beberapa informan kunci. "
        "Data yang terkumpul dianalisis menggunakan statistik deskriptif. "
        "Secara keseluruhan, metode ini dipilih karena sesuai dengan "
        "tujuan penelitian.")

    def test_human_methods_paragraph_is_capped(self):
        result = tools.detect_ai(self.METHODS_PARAGRAPH)
        # The score is not hidden: 80.5 is honestly high.
        self.assertGreaterEqual(result["ai_score"], 60)
        self.assertEqual(
            sum(1 for s in result["signals"].values()
                if s["applicable"]), 2)
        self.assertTrue(result["verdict_capped"])
        self.assertIn("2 dari 4", result["verdict_capped_reason"])
        self.assertEqual(result["verdict"], "Campuran / tidak pasti")

    def test_uncapped_ai_verdict_has_no_reason(self):
        result = tools.detect_ai(AI_1)
        self.assertFalse(result["verdict_capped"])
        self.assertIsNone(result["verdict_capped_reason"])

    def test_too_short_is_not_capped(self):
        result = tools.detect_ai("Ini teks pendek sekali.")
        self.assertFalse(result["verdict_capped"])
        self.assertIsNone(result["verdict_capped_reason"])

    def test_capped_reason_shows_in_format(self):
        out = tools.format_detect(tools.detect_ai(self.METHODS_PARAGRAPH))
        self.assertIn("Campuran / tidak pasti", out)
        self.assertIn("hanya 2 dari 4 sinyal", out)

    def test_capped_reason_in_english(self):
        # The same shape in English: 5 uniform sentences, two
        # English template phrases, under 100 words — only 2 signals
        # apply, so the verdict is capped at Mixed / uncertain.
        text = ("This study uses a survey method. "
                "Data were collected through a questionnaire distributed to "
                "the respondents. "
                "Moreover, interviews were conducted with several key "
                "informants. "
                "The collected data were analyzed using descriptive "
                "statistics. "
                "In conclusion, this method was chosen because it fits the "
                "purpose of the study.")
        result = tools.detect_ai(text, lang="en")
        self.assertGreaterEqual(result["ai_score"], 60)
        self.assertTrue(result["verdict_capped"])
        self.assertIn("only 2 of 4 signals", result["verdict_capped_reason"])
        self.assertEqual(result["verdict"], "Mixed / uncertain")


class TestFormatDetect(unittest.TestCase):
    def test_human_format(self):
        out = tools.format_detect(tools.detect_ai(HUMAN_1))
        self.assertIn("Skor AI: 0.0/100", out)
        self.assertIn("Kemungkinan besar manusia", out)
        self.assertIn("Variasi panjang kalimat", out)
        self.assertIn("Frasa template", out)
        self.assertIn("Keragaman kosakata", out)
        self.assertIn("Pengulangan awalan kalimat", out)
        self.assertIn("Tidak ada kalimat yang melewati ambang 70/100.", out)
        self.assertIn("heuristik", out)

    def test_ai_format_lists_top_sentences(self):
        out = tools.format_detect(tools.detect_ai(AI_1))
        self.assertIn("Skor AI: 78.9/100", out)
        self.assertIn("Kalimat paling mirip AI:", out)
        self.assertIn("Selain itu", out)

    def test_short_format(self):
        out = tools.format_detect(tools.detect_ai("Teks pendek."))
        self.assertIn("Teks terlalu pendek", out)
        self.assertIn("heuristik", out)

    def test_english_format(self):
        out = tools.format_detect(tools.detect_ai(HUMAN_1, lang="en"),
                                  lang="en")
        self.assertIn("AI score", out)
        self.assertIn("Likely human", out)
        self.assertIn("heuristic", out)


class TestDetectMain(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.detect_main(argv)
        return code, buf.getvalue()

    def test_text_flag(self):
        code, out = self._run(["--text", AI_1])
        self.assertEqual(code, 0)
        self.assertIn("Skor AI: 78.9/100", out)
        self.assertIn("Kemungkinan besar AI", out)

    def test_json_flag(self):
        code, out = self._run(["--text", AI_1, "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["ai_score"], 78.9)
        self.assertEqual(set(data),
                         {"ai_score", "verdict", "verdict_capped",
                          "verdict_capped_reason", "signals", "sentences",
                          "note"})

    def test_file_input(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                        encoding="utf-8") as f:
            f.write(HUMAN_2)
            path = f.name
        try:
            code, out = self._run([path])
            self.assertEqual(code, 0)
            self.assertIn("Kemungkinan besar manusia", out)
        finally:
            os.unlink(path)

    def test_missing_file_is_clean_error(self):
        with self.assertRaises(ValueError) as cm:
            tools.detect_main(["/tidak/ada/file.txt"])
        self.assertIn("File tidak ditemukan", str(cm.exception))

    def test_empty_text_is_clean_error(self):
        with self.assertRaises(ValueError) as cm:
            tools.detect_main(["--text", "   "])
        self.assertEqual(str(cm.exception), "teks kosong")

    def test_no_input_is_an_error(self):
        with self.assertRaises(SystemExit) as cm:
            tools.detect_main([])
        self.assertEqual(cm.exception.code, 2)

    def test_detect_is_informative_exit_0_even_for_ai(self):
        # Detection never fails the run: an AI-like text still exits 0.
        code, _ = self._run(["--text", AI_3])
        self.assertEqual(code, 0)

    def test_main_dispatches_detect(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.main(["detect", "--text", HUMAN_3])
        self.assertEqual(code, 0)
        self.assertIn("Kemungkinan besar manusia", buf.getvalue())

    def test_main_version_lists_ai_detector(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = tools.main(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("ai_detector 1.0.1", buf.getvalue())
        self.assertIn("academic_tools.py 1.27.0", buf.getvalue())


class TestDetectMenu(unittest.TestCase):
    def _run_cli(self, inputs):
        import builtins
        cli = tools.CLI(lang="id")
        out = io.StringIO()
        queue = list(inputs)
        real_input = builtins.input
        builtins.input = lambda *a: queue.pop(0) if queue else (_ for _ in ()).throw(EOFError)
        try:
            with redirect_stdout(out):
                code = cli.run()
        finally:
            builtins.input = real_input
        return code, out.getvalue()

    def test_menu_lists_detect_as_option_7(self):
        code, text = self._run_cli(["0"])
        self.assertEqual(code, 0)
        self.assertIn("7  Deteksi AI", text)
        self.assertIn("8  Ganti bahasa", text)

    def test_detect_from_menu_reads_a_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                        encoding="utf-8") as f:
            f.write(HUMAN_3)
            path = f.name
        try:
            # 7=detect, 1=check text, 2=read file, path, ""=pause,
            # 0=back, 0=exit.
            code, text = self._run_cli(["7", "1", "2", path, "", "0", "0"])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        self.assertIn("Deteksi AI", text)
        self.assertIn("Kemungkinan besar manusia", text)


if __name__ == "__main__":
    unittest.main()
