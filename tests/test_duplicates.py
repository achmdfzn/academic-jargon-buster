"""Tests for the internal duplication check (find_duplicates).

The check compares each sentence against the sentences of the user's
own saved analyses in the library (plus the other sentences of the
text itself), using a normalized difflib ratio. Tests that need a
real database use a temporary file; the rest pass past runs directly.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    analyze_main,
    duplicates_main,
    find_duplicates,
    format_duplicates,
    save_analysis,
)

PAST_TITLE = "Bab 1"
PAST_TEXT = (
    "Penelitian ini menggunakan metode kualitatif dengan pendekatan "
    "studi kasus yang mendalam. Data dikumpulkan melalui wawancara "
    "semi terstruktur dengan dua belas informan yang dipilih secara "
    "purposive. Hasil analisis menunjukkan bahwa kepuasan pengguna "
    "dipengaruhi oleh kemudahan navigasi dan kecepatan respon sistem.")
EDITED = (
    "Hasil analisis menunjukkan bahwa kepuasan pengguna dipengaruhi "
    "oleh kemudahan navigasi dan kecepatan sistem.")
NEW_SENTENCE = ("Penelitian lanjutan dapat memperluas sampel ke wilayah lain "
                "di Indonesia.")


def _run(run_id, title, text):
    return {"id": run_id, "title": title,
            "created_at": "2026-11-12T10:00:00+07:00", "text": text}


def _save(db, text, title=PAST_TITLE):
    refs = tools.load_references(tools.DEFAULT_REFS)
    result = tools.analyze_text_quality(text, refs, lang="id",
                                        verify_dois=False)
    return save_analysis(text, result, refs, title=title, db=db)


class TestFindDuplicates(unittest.TestCase):
    def setUp(self):
        self.past = [_run(1, PAST_TITLE, PAST_TEXT)]

    def test_exact_duplicate_found(self):
        sentence = ("Data dikumpulkan melalui wawancara semi terstruktur "
                    "dengan dua belas informan yang dipilih secara purposive.")
        result = find_duplicates(sentence + " " + NEW_SENTENCE,
                                 past_runs=self.past)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["checked"], 1)
        dup = result["duplicates"][0]
        self.assertEqual(dup["similarity"], 1.0)
        self.assertEqual(dup["source_id"], 1)
        self.assertEqual(dup["source_title"], PAST_TITLE)
        self.assertEqual(dup["source_date"], "2026-11-12")

    def test_near_duplicate_found(self):
        result = find_duplicates(EDITED + " " + NEW_SENTENCE,
                                 past_runs=self.past)
        self.assertEqual(result["count"], 1)
        self.assertGreaterEqual(
            result["duplicates"][0]["similarity"], 0.8)

    def test_unrelated_sentence_not_flagged(self):
        result = find_duplicates(NEW_SENTENCE, past_runs=self.past)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["checked"], 1)

    def test_short_sentences_ignored(self):
        text = "Penelitian ini bagus sekali. Hasilnya sangat memuaskan."
        result = find_duplicates(text, past_runs=self.past)
        self.assertEqual(result["count"], 0)

    def test_repeat_inside_text(self):
        sentence = ("Data dikumpulkan melalui wawancara semi terstruktur "
                    "dengan dua belas informan yang dipilih secara purposive.")
        result = find_duplicates(sentence + " " + sentence, past_runs=[])
        self.assertEqual(result["count"], 1)
        dup = result["duplicates"][0]
        self.assertIsNone(dup["source_id"])
        self.assertEqual(dup["source_title"], "naskah ini")
        self.assertIsNone(dup["source_date"])

    def test_threshold_respected(self):
        original = ("Hasil analisis menunjukkan bahwa kepuasan pengguna "
                    "dipengaruhi oleh kemudahan navigasi dan kecepatan "
                    "respon sistem.")
        sim = tools._sentence_similarity(
            tools._normalize_sentence(EDITED),
            tools._normalize_sentence(original))
        self.assertGreater(sim, 0.8)
        self.assertLess(sim, 1.0)
        self.assertEqual(
            find_duplicates(EDITED, past_runs=self.past,
                            threshold=sim - 0.01)["count"], 1)
        self.assertEqual(
            find_duplicates(EDITED, past_runs=self.past,
                            threshold=1.0)["count"], 0)

    def test_bad_threshold_is_an_error(self):
        with self.assertRaises(ValueError):
            find_duplicates(NEW_SENTENCE, past_runs=self.past,
                            threshold=1.5)

    def test_best_match_wins(self):
        runs = [_run(1, "Bab 1", PAST_TEXT),
                _run(2, "Bab 2", PAST_TEXT.replace("respon sistem",
                                                   "sistem"))]
        sentence = ("Data dikumpulkan melalui wawancara semi terstruktur "
                    "dengan dua belas informan yang dipilih secara purposive.")
        result = find_duplicates(sentence, past_runs=runs)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["duplicates"][0]["source_id"], 1)
        self.assertEqual(result["duplicates"][0]["similarity"], 1.0)

    def test_same_text_not_matched_against_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _save(db, PAST_TEXT)
            result = find_duplicates(PAST_TEXT, db=db)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["checked"], 0)

    def test_trailing_whitespace_still_same_text(self):
        # Hashes ignore leading/trailing whitespace, so a saved run
        # is still recognised as "itself" when re-checked with
        # different trailing newlines — and vice versa.
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _save(db, PAST_TEXT + "\n\n")
            self.assertEqual(
                find_duplicates(PAST_TEXT, db=db)["count"], 0)
            self.assertEqual(
                find_duplicates(PAST_TEXT + "  \n", db=db)["count"], 0)
            # ...but a genuinely repeated sentence is still found.
            sentence = ("Data dikumpulkan melalui wawancara semi "
                        "terstruktur dengan dua belas informan yang "
                        "dipilih secara purposive.")
            result = find_duplicates(sentence + " " + NEW_SENTENCE,
                                     db=db)
            self.assertEqual(result["count"], 1)

    def test_one_word_sentence_skips_prefilter(self):
        # "pengukuranpengukuran pengukuran ..." vs "pengukuran
        # pengukuran ..." is 0.84 similar on difflib, but the stored
        # sentence has a single unique word, so the word-overlap
        # pre-filter (0.5) would have skipped the comparison entirely.
        past = [_run(1, "Bab 1",
                     "pengukuran pengukuran pengukuran pengukuran "
                     "pengukuran pengukuran.")]
        text = ("pengukuranpengukuran pengukuran pengukuran pengukuran "
                "pengukuran pengukuran.")
        result = find_duplicates(text, past_runs=past)
        self.assertEqual(result["count"], 1)
        self.assertGreaterEqual(
            result["duplicates"][0]["similarity"], 0.8)

    def test_empty_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            result = find_duplicates(NEW_SENTENCE, db=db)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["checked"], 0)

    def test_format_duplicates(self):
        result = find_duplicates(EDITED + " " + NEW_SENTENCE,
                                 past_runs=self.past)
        text = format_duplicates(result)
        self.assertIn("Duplikasi internal", text)
        self.assertIn("pustaka #1", text)
        # Sentences are stored without the trailing period.
        self.assertIn(EDITED.rstrip("."), text)
        clean = format_duplicates({"duplicates": [], "count": 0,
                                   "checked": 1})
        self.assertIn("Tidak ada kalimat yang berulang", clean)


class TestSelfMatchOver100k(unittest.TestCase):
    """B-2: a run over 100,000 characters must still recognise itself.

    The stored text is the canonical form — stripped, then cut to
    100,000 characters — and the stored hash is the hash of that
    same form. Before this fix save hashed text[:100k].strip() while
    find_duplicates hashed text.strip()[:100k], so a long run with
    whitespace at the ends (or a space at character 100,000)
    matched its own saved copy 400 times.
    """

    def _long_distinct_text(self):
        # 400 sentences, each built from words unique to it, so no
        # sentence resembles another: within-text matches are 0 and
        # any match can only come from the saved run itself.
        sents = [" ".join(f"kata{i}_{j}" for j in range(30)) + "."
                 for i in range(400)]
        return "  \n" + " ".join(sents) + "\n\n"

    def test_long_text_does_not_match_itself(self):
        text = self._long_distinct_text()
        self.assertGreater(len(text), 100_000)
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _save(db, text)
            result = find_duplicates(text, db=db)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["checked"], 0)

    def test_long_template_text_has_no_library_self_match(self):
        # The auditor's repro: 400 near-identical template
        # sentences. Within-text matches between the templates are
        # real (the sentences ARE near-duplicates of each other),
        # but none may point back at the run's own saved copy.
        words = ["survei", "wawancara", "observasi", "eksperimen",
                 "studi kasus", "analisis isi", "etnografi", "kuesioner"]
        sents = []
        for i in range(400):
            sents.append(
                f"Bagian {i} menguraikan {words[i % len(words)]} nomor "
                f"{i} dengan pendekatan {words[(i + 3) % len(words)]} "
                f"serta temuan {words[(i + 5) % len(words)]} yang relevan "
                f"bagi {words[(i + 7) % len(words)]} dan implikasi "
                f"{words[(i + 1) % len(words)]} untuk {words[(i + 2) % len(words)]} "
                f"beserta saran {words[(i + 4) % len(words)]} bagi "
                f"{words[(i + 6) % len(words)]} maupun rekomendasi "
                f"{words[i % len(words)]} untuk {words[(i + 3) % len(words)]}. "
                "Hasilnya dicatat dalam laporan akhir bab ini.")
        text = "  \n" + " ".join(sents) + "\n\n"
        self.assertGreater(len(text), 100_000)
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            result = find_duplicates(text, db=db)
            lib_matches = [d for d in result["duplicates"]
                           if d["source_id"] == rid]
            self.assertEqual(lib_matches, [])

    def test_legacy_hash_run_still_excluded(self):
        # A run saved by v1.25.2 (hash of text[:100k].strip()) must
        # still be recognised as "itself" after the canonical form
        # changed.
        import hashlib
        import sqlite3

        text = self._long_distinct_text()
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rid = _save(db, text)
            legacy = hashlib.sha256(
                text[:100_000].strip().encode("utf-8")).hexdigest()
            conn = sqlite3.connect(db)
            conn.execute("UPDATE analyses SET text_hash = ? WHERE id = ?",
                         (legacy, rid))
            conn.commit()
            conn.close()
            result = find_duplicates(text, db=db)
            self.assertEqual(result["count"], 0)


class TestDuplicatesMain(unittest.TestCase):
    def test_exit_codes_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _save(db, PAST_TEXT)
            check = EDITED + " " + NEW_SENTENCE
            out = io.StringIO()
            with redirect_stdout(out):
                code = duplicates_main(["--text", check, "--db", db])
            self.assertEqual(code, 1)
            self.assertIn("Duplikasi internal", out.getvalue())
            out = io.StringIO()
            with redirect_stdout(out):
                code = duplicates_main(["--text", NEW_SENTENCE, "--db", db,
                                        "--json"])
            self.assertEqual(code, 0)
            parsed = json.loads(out.getvalue())
            self.assertEqual(parsed["count"], 0)
            self.assertEqual(parsed["checked"], 1)

    def test_bad_threshold_exits_1(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = duplicates_main(["--text", NEW_SENTENCE,
                                    "--threshold", "1.5"])
        self.assertEqual(code, 1)
        self.assertIn("threshold harus", err.getvalue())

    def test_corrupt_db_is_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            corrupt = os.path.join(tmp, "corrupt.db")
            with open(corrupt, "wb") as f:
                f.write(b"bukan sqlite")
            err = io.StringIO()
            with redirect_stderr(err):
                code = duplicates_main(["--text", NEW_SENTENCE,
                                        "--db", corrupt])
            self.assertEqual(code, 1)
            self.assertIn("pustaka rusak", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())


class TestAnalyzeDuplicatesFlag(unittest.TestCase):
    def test_analyze_duplicates_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _save(db, PAST_TEXT)
            check = EDITED + " " + NEW_SENTENCE
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([
                    "--text", check, "--refs", tools.DEFAULT_REFS,
                    "--no-verify", "--duplicates", "--db", db])
            self.assertEqual(code, 0)
            self.assertIn("Duplikasi: 1 kalimat berulang", out.getvalue())


if __name__ == "__main__":
    unittest.main()


class TestDuplicatesReadOnlyAndValidation(unittest.TestCase):
    """v1.25.2: read paths never create the library file."""

    def test_find_duplicates_on_missing_db_creates_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "sub", "library.db")
            result = find_duplicates(PAST_TEXT, db=db)
            self.assertEqual(result, {"duplicates": [], "count": 0,
                                      "checked": 0, "truncated": False,
                                      "comparisons_spent": 0})
            self.assertFalse(os.path.exists(db))
            self.assertFalse(os.path.exists(os.path.dirname(db)))

    def test_min_words_must_be_positive(self):
        for bad in (0, -1):
            with self.subTest(min_words=bad):
                with self.assertRaises(ValueError):
                    find_duplicates(PAST_TEXT, min_words=bad,
                                    past_runs=[])

    def test_created_at_coerced_to_string(self):
        run = {"id": 1, "title": "Bab 1", "created_at": 20260101,
               "text": PAST_TEXT}
        result = find_duplicates(EDITED, past_runs=[run])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["duplicates"][0]["source_date"],
                         "20260101")

    def test_past_texts_capped_at_100_newest(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "library.db")
            for i in range(105):
                _save(db,
                      f"Kalimat unik nomor {i} untuk pengujian pustaka.",
                      title=f"Run {i}")
            runs = tools._past_texts(db)
            self.assertEqual(len(runs), 100)
            self.assertEqual(runs[0]["id"], 105)
