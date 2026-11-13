"""Tests for audit #4, B-2 (hash residu) and N-15 (find_duplicates lambat).

B-2: perbaikan v1.26.1 menerapkan _canonical_text dua kali di jalur
save, sehingga bila karakter ke-100.000 adalah spasi, hash yang
tersimpan bukan hash dari teks yang tersimpan. Tes di sini memakai
teks >100k yang batas potongnya jatuh di spasi, lalu memeriksa ulang
dengan varian leading whitespace yang berbeda.

N-15: 600 kalimat dari pool 20 kata membuat find_duplicates berjalan
>4 menit (difflib atas hampir semua pasangan). Tes kinerja di sini
memastikan panggilan yang sama selesai dalam hitungan detik, dan tes
ekuivalensi brute-force memastikan hasil pada teks normal tidak
berubah oleh indeks kata + anggaran kerja yang baru.
"""

import hashlib
import os
import random
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    _canonical_text,
    _is_own_run,
    _legacy_stored_hash,
    _normalize_sentence,
    _overlap_gate,
    _sentence_similarity,
    _split_sentences,
    _stored_hash,
    find_duplicates,
    get_analysis,
    save_analysis,
)

# save_analysis hanya butuh field-field ini; hasil analisis lengkap
# tidak relevan untuk jalur hash/save, jadi tidak menjalankan
# analyze_text_quality di sini.
MIN_RESULT = {"quality_score": 90, "jargon": [], "citations": {},
              "doi_verification": {}, "style": {"style_score": 20},
              "suggestions": {"count": 0}}


def _distinct_long_text(n_sents=400):
    """400 kalimat dengan kata-kata unik per kalimat, >100k karakter.

    Kalimat-kalimatnya tidak mirip satu sama lain, jadi kecocokan
    dalam-teks adalah 0 dan kecocokan apa pun hanya bisa berasal
    dari salinan tersimpan di pustaka.
    """
    sents = [" ".join(f"kata{i}_{j}" for j in range(30)) + "."
             for i in range(n_sents)]
    return "  \n" + " ".join(sents) + "\n\n"


def _text_with_space_at_cut():
    """Teks panjang yang karakter ke-100.000-nya (setelah strip) spasi.

    Satu spasi disisipkan tepat di index 99999 bila belum ada, jadi
    bentuk kanoniknya berakhir tepat di spasi itu dan rstrip akhir
    _canonical_text ikut teruji.
    """
    stripped = _distinct_long_text().strip()
    assert len(stripped) > 100_000
    if stripped[99_999] != " ":
        stripped = stripped[:99_999] + " " + stripped[99_999:]
    assert stripped[99_999] == " "
    return stripped


def _text_without_space_at_cut():
    """Teks panjang yang bentuk kanoniknya TIDAK berakhir spasi (kontrol)."""
    text = _distinct_long_text().strip()
    assert len(text) > 100_000
    assert text[99_999] != " "
    assert _canonical_text(text)[-1] != " "
    return text


def _save(db, text, title="panjang"):
    return save_analysis(text, MIN_RESULT, None, title=title, db=db)


def _row(db, rid):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT text, text_hash FROM analyses WHERE id = ?",
            (rid,)).fetchone()
    finally:
        conn.close()


class TestCanonicalTextIdempotent(unittest.TestCase):
    def test_idempotent_on_short_texts(self):
        cases = ["", "   ", "\n\n", "abc", "  abc  ",
                 "\t\nhello world\n\t", "a b c", "kata " * 10,
                 "x" * 100_000, " " + "y" * 99_999 + " "]
        for text in cases:
            once = _canonical_text(text)
            twice = _canonical_text(once)
            self.assertEqual(twice, once, repr(text[:40]))
            self.assertLessEqual(len(once), 100_000)
            if once:
                self.assertEqual(once, once.strip())

    def test_idempotent_long_text_space_at_cut(self):
        text = _text_with_space_at_cut()
        once = _canonical_text(text)
        # Potongan berakhir spasi -> rstrip memangkas tepat spasi itu.
        self.assertEqual(len(once), 99_999)
        self.assertFalse(once.endswith(" "))
        self.assertEqual(_canonical_text(once), once)

    def test_idempotent_long_text_no_space_at_cut(self):
        text = _text_without_space_at_cut()
        once = _canonical_text(text)
        self.assertEqual(len(once), 100_000)
        self.assertEqual(_canonical_text(once), once)

    def test_canonical_is_strip_then_cap_then_rstrip(self):
        text = _text_with_space_at_cut()
        self.assertEqual(_canonical_text(text),
                         text.strip()[:100_000].rstrip())


class TestStoredHashInvariant(unittest.TestCase):
    def _check_invariant(self, db, rid, original):
        stored_text, stored_hash = _row(db, rid)
        self.assertEqual(stored_text, _canonical_text(original))
        self.assertEqual(
            hashlib.sha256(stored_text.encode("utf-8")).hexdigest(),
            stored_hash)

    def test_short_text_hash_is_hash_of_stored_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, "Penelitian ini memakai data primer.")
            self._check_invariant(
                db, rid, "Penelitian ini memakai data primer.")

    def test_long_text_space_at_cut_hash_is_hash_of_stored_text(self):
        text = _text_with_space_at_cut()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            self._check_invariant(db, rid, text)
            # get_analysis melihat invarian yang sama.
            got = get_analysis(rid, db=db)
            self.assertEqual(
                hashlib.sha256(got["text"].encode("utf-8")).hexdigest(),
                got["text_hash"])

    def test_whitespace_padded_text_hash_is_hash_of_stored_text(self):
        text = "  \n" + _distinct_long_text() + "\n\n"
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            self._check_invariant(db, rid, text)


class TestSelfMatchT9(unittest.TestCase):
    """Reproduksi auditor B-2: teks >100k, spasi di karakter ke-100.000."""

    def test_exact_text_no_self_match(self):
        text = _text_with_space_at_cut()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _save(db, text)
            result = find_duplicates(text, db=db)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["checked"], 0)

    def test_leading_whitespace_variants_no_self_match(self):
        text = _text_with_space_at_cut()
        variants = ["  " + text, "\n" + text, "  \n" + text,
                    text + "\n", text + "\n\n", "\t" + text]
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            for variant in variants:
                result = find_duplicates(variant, db=db)
                lib_matches = [d for d in result["duplicates"]
                               if d["source_id"] == rid]
                self.assertEqual(lib_matches, [], repr(variant[:12]))
                self.assertEqual(result["checked"], 0)

    def test_no_space_at_cut_variants_no_self_match(self):
        text = _text_without_space_at_cut()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            for variant in [text, "  " + text, text + "\n"]:
                result = find_duplicates(variant, db=db)
                lib_matches = [d for d in result["duplicates"]
                               if d["source_id"] == rid]
                self.assertEqual(lib_matches, [])

    def test_is_own_run_leading_whitespace_variant(self):
        text = _text_with_space_at_cut()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            stored_text, stored_hash = _row(db, rid)
            run = {"id": rid, "title": "panjang",
                   "created_at": "2026-11-13T01:00:00+07:00",
                   "text": stored_text, "text_hash": stored_hash}
            query = "  " + text
            self.assertTrue(_is_own_run(run, _stored_hash(query),
                                        _legacy_stored_hash(query)))

    def test_legacy_hash_run_still_excluded(self):
        text = _text_with_space_at_cut()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            legacy = _legacy_stored_hash(text)
            conn = sqlite3.connect(db)
            conn.execute("UPDATE analyses SET text_hash = ? WHERE id = ?",
                         (legacy, rid))
            conn.commit()
            conn.close()
            result = find_duplicates("  " + text, db=db)
            self.assertEqual(result["count"], 0)

    def test_row_saved_by_buggy_v1_27_1_still_excluded(self):
        # Baris yang sudah telanjur tersimpan oleh v1.27.1: teks
        # kanonik lama yang berakhir spasi + hash dari teks itu
        # setelah strip kedua. Perbaikan harus tetap mengenalinya
        # sebagai salinan sendiri (lewat fallback _is_own_run).
        text = _text_with_space_at_cut()
        old_canonical = text.strip()[:100_000]
        self.assertTrue(old_canonical.endswith(" "))
        buggy_hash = hashlib.sha256(
            old_canonical.strip().encode("utf-8")).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            conn = tools.open_library(db)
            conn.execute(
                """INSERT INTO analyses
                   (created_at, title, quality_score, jargon_count,
                    citations_missing, doi_ok, doi_total, style_score,
                    suggestions_count, text_hash, text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("2026-11-13T01:00:00+07:00", "panjang", 90, 0, 0, 0, 0,
                 20, 0, buggy_hash, old_canonical))
            conn.commit()
            conn.close()
            result = find_duplicates("  " + text, db=db)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["checked"], 0)


class TestFindDuplicatesPerformance(unittest.TestCase):
    """N-15: 600 kalimat dari pool 20 kata harus selesai hitungan detik."""

    POOL = ["survei", "wawancara", "observasi", "eksperimen", "studi",
            "kasus", "analisis", "etnografi", "kuesioner", "sampel",
            "data", "temuan", "metode", "hasil", "laporan", "bab",
            "pendekatan", "saran", "rekomendasi", "implikasi"]

    def _pool_text(self, n_sents, seed=7):
        rng = random.Random(seed)
        sents = []
        for i in range(n_sents):
            words = [rng.choice(self.POOL) for _ in range(12)]
            sents.append(f"Bagian {i} " + " ".join(words) + ".")
        return " ".join(sents)

    def test_600_sentences_small_pool_finishes_in_seconds(self):
        text = self._pool_text(600)
        start = time.time()
        result = find_duplicates(text, past_runs=[])
        elapsed = time.time() - start
        self.assertLess(elapsed, 10,
                        f"find_duplicates 600 kalimat: {elapsed:.1f} dtk")
        self.assertIn("count", result)
        self.assertIn("checked", result)

    def test_600_sentences_against_600_sentence_corpus_finishes(self):
        text = self._pool_text(600, seed=7)
        past = [{"id": 1, "title": "Bab 1",
                 "created_at": "2026-11-12T10:00:00+07:00",
                 "text": self._pool_text(600, seed=8)}]
        start = time.time()
        result = find_duplicates(text, past_runs=past)
        elapsed = time.time() - start
        self.assertLess(elapsed, 15,
                        f"find_duplicates 600+600 kalimat: {elapsed:.1f} dtk")
        self.assertEqual(result["checked"], 1)

    def test_results_match_brute_force_on_normal_input(self):
        """Indeks kata + anggaran kerja tidak mengubah hasil teks normal.

        Referensi brute-force di sini adalah loop bersarang lama
        (semua pasangan, _overlap_gate, difflib): pada input kecil
        yang anggarannya tidak tersentuh, hasilnya harus identik.
        """
        words = ["penelitian", "metode", "kualitatif", "kuantitatif",
                 "data", "analisis", "responden", "wawancara",
                 "observasi", "survei", "hasil", "temuan", "sampel",
                 "populasi", "instrumen", "validitas", "reliabilitas",
                 "hipotesis", "variabel", "pengukuran"]

        def rand_sent(rng):
            n = rng.randint(6, 14)
            return (" ".join(rng.choice(words) for _ in range(n))
                    .capitalize() + ".")

        def brute_force(text, past_runs, threshold=0.8, min_words=6):
            sentences = [s for s in _split_sentences(text)
                         if len(s.split()) >= min_words]
            normalized = [_normalize_sentence(s) for s in sentences]
            word_sets = [set(n.split()) for n in normalized]
            corpus = []
            for run in past_runs:
                for sent in _split_sentences(run["text"]):
                    if len(sent.split()) < min_words:
                        continue
                    norm = _normalize_sentence(sent)
                    corpus.append((norm, sent, set(norm.split()), run))
            duplicates = []
            spent = 0
            for i, (sent, norm, w) in enumerate(
                    zip(sentences, normalized, word_sets)):
                best = None
                for cn, cs, cw, run in corpus:
                    if not _overlap_gate(w, cw):
                        continue
                    sim = _sentence_similarity(norm, cn)
                    spent += 1
                    if sim >= threshold and (best is None
                                             or sim > best[0]):
                        best = (sim, cs, run)
                for j in range(i + 1, len(sentences)):
                    if not _overlap_gate(w, word_sets[j]):
                        continue
                    sim = _sentence_similarity(norm, normalized[j])
                    spent += 1
                    if sim >= threshold and (best is None
                                             or sim > best[0]):
                        best = (sim, sentences[j], None)
                if best is not None:
                    sim, match, run = best
                    duplicates.append({
                        "sentence": sent, "match": match,
                        "similarity": round(sim, 2),
                        "source_id": run["id"] if run else None,
                        "source_title": (run["title"] if run
                                         else "naskah ini"),
                        "source_date": (str(run["created_at"])[:10]
                                        if run else None),
                    })
            return {"duplicates": duplicates, "count": len(duplicates),
                    "checked": len(past_runs), "truncated": False,
                    "comparisons_spent": spent}

        for seed in (1, 2, 3):
            rng = random.Random(seed)
            past = []
            for rid in range(rng.randint(0, 3)):
                past.append({"id": rid + 1, "title": f"Bab {rid + 1}",
                             "created_at": "2026-11-12T10:00:00+07:00",
                             "text": " ".join(
                                 rand_sent(rng)
                                 for _ in range(rng.randint(1, 12)))})
            check = [rand_sent(rng) for _ in range(rng.randint(1, 15))]
            if past and rng.random() < 0.8:
                src = _split_sentences(rng.choice(past)["text"])
                if src:
                    check.append(rng.choice(src))
            if seed == 1:
                # Kalimat berulang (<3 kata unik): cabang gate khusus.
                check.append("Ya ya ya ya ya ya ya.")
                check.append("Pengukuran pengukuran pengukuran pengukuran.")
            text = " ".join(check)
            for threshold in (0.8, 0.9):
                self.assertEqual(
                    find_duplicates(text, past_runs=past,
                                    threshold=threshold),
                    brute_force(text, past, threshold=threshold),
                    f"seed={seed} threshold={threshold}")


if __name__ == "__main__":
    unittest.main()
