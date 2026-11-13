"""Tests for audit #5, B-1 (duplicates check silently truncated).

Audit #5 found that find_duplicates() on a legitimate, heavily
derivative text — 300 sentences sharing one small vocabulary —
spent its global work budget (_MAX_DUPLICATE_COMPARISONS = 2000)
and returned only the matches found so far (7 in the auditor's
repro), with no flag at all: the result keys were just checked,
count, duplicates. The budget itself is unchanged (normal-input
equivalence was verified by audit #5); the fix is honesty — the
result now always carries "truncated" and "comparisons_spent",
and every renderer that shows duplication results warns the user
when the check was cut short.
"""

import io
import json
import os
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    _MAX_DUPLICATE_COMPARISONS,
    analyze_main,
    duplicates_main,
    find_duplicates,
    format_analyze,
    format_duplicates,
)

POOL = ["penelitian", "metode", "data", "analisis", "hasil",
        "responden", "wawancara", "observasi", "sampel", "temuan"]


def _rand_sent(rng, n=12):
    return " ".join(rng.choice(POOL) for _ in range(n)).capitalize() + "."


def _derivative_text(n_sentences=300, seed=5, lib_sentences=5):
    """300 sentences from a 10-word pool vs a small library.

    Every sentence shares most of its words with many others, so
    the overlap gate admits thousands of pairs and the 2000
    comparison budget is exhausted. With lib_sentences > 0 the
    first sentences repeat the library verbatim, so a few real
    matches are reported before the budget runs out — the
    auditor's shape (hundreds in, a handful out).
    """
    rng = random.Random(seed)
    lib = [_rand_sent(rng) for _ in range(lib_sentences)]
    past = [{"id": 1, "title": "Bab 1",
             "created_at": "2026-11-12T10:00:00+07:00",
             "text": " ".join(lib)}]
    text = " ".join(lib + [_rand_sent(rng)
                           for _ in range(n_sentences - lib_sentences)])
    return text, past


def _brute_force(text, past_runs, threshold=0.8, min_words=6):
    """Reference without any work budget (audit #4's nested loops).

    Counts every difflib comparison it performs, so on inputs that
    never reach the budget its "comparisons_spent" must equal the
    real find_duplicates() count.
    """
    sentences = [s for s in tools._split_sentences(text)
                 if len(s.split()) >= min_words]
    normalized = [tools._normalize_sentence(s) for s in sentences]
    word_sets = [set(n.split()) for n in normalized]
    corpus = []
    for run in past_runs:
        for sent in tools._split_sentences(run["text"]):
            if len(sent.split()) < min_words:
                continue
            norm = tools._normalize_sentence(sent)
            corpus.append((norm, sent, set(norm.split()), run))
    duplicates = []
    spent = 0
    for i, (sent, norm, w) in enumerate(
            zip(sentences, normalized, word_sets)):
        best = None
        for cn, cs, cw, run in corpus:
            if not tools._overlap_gate(w, cw):
                continue
            sim = tools._sentence_similarity(norm, cn)
            spent += 1
            if sim >= threshold and (best is None or sim > best[0]):
                best = (sim, cs, run)
        for j in range(i + 1, len(sentences)):
            if not tools._overlap_gate(w, word_sets[j]):
                continue
            sim = tools._sentence_similarity(norm, normalized[j])
            spent += 1
            if sim >= threshold and (best is None or sim > best[0]):
                best = (sim, sentences[j], None)
        if best is not None:
            sim, match, run = best
            duplicates.append({
                "sentence": sent, "match": match,
                "similarity": round(sim, 2),
                "source_id": run["id"] if run else None,
                "source_title": run["title"] if run else "naskah ini",
                "source_date": (str(run["created_at"])[:10]
                                if run else None),
            })
    return {"duplicates": duplicates, "count": len(duplicates),
            "checked": len(past_runs), "truncated": False,
            "comparisons_spent": spent}


def _save(db, text, title="Bab 1"):
    refs = tools.load_references(tools.DEFAULT_REFS)
    result = tools.analyze_text_quality(text, refs, lang="id",
                                        verify_dois=False)
    return tools.save_analysis(text, result, refs, title=title, db=db)


class TestBudgetExhausted(unittest.TestCase):
    def test_budget_constant_unchanged(self):
        # Audit #5 verified normal-input equivalence at 2000; the
        # fix changes only the honesty of the result, not the budget.
        self.assertEqual(_MAX_DUPLICATE_COMPARISONS, 2000)

    def test_300_derivative_sentences_truncated(self):
        # The auditor's repro shape: 300 sentences, small library.
        text, past = _derivative_text(lib_sentences=0)
        result = find_duplicates(text, past_runs=past)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["comparisons_spent"], 2000)
        self.assertEqual(result["checked"], 1)

    def test_truncated_result_reports_only_what_was_found(self):
        # 300 sentences in, only the 5 verbatim library repeats out
        # — the rest were never compared once the budget ran out.
        text, past = _derivative_text()
        result = find_duplicates(text, past_runs=past)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["comparisons_spent"], 2000)
        self.assertEqual(result["count"], 5)
        self.assertLess(result["count"], 300)
        self.assertTrue(all(d["source_id"] == 1
                            for d in result["duplicates"]))

    def test_truncated_with_zero_matches_still_flags(self):
        # Budget exhausted but nothing matched: the empty list must
        # still say it is incomplete, not "no duplicates".
        text, past = _derivative_text(lib_sentences=0, seed=1)
        result = find_duplicates(text, past_runs=past)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["count"], 0)


class TestFormatDuplicatesWarning(unittest.TestCase):
    def test_warning_shown_when_truncated_with_matches(self):
        text, past = _derivative_text()
        result = find_duplicates(text, past_runs=past)
        out = format_duplicates(result)
        self.assertIn("Peringatan", out)
        self.assertIn("2000", out)
        self.assertIn("tidak lengkap", out)

    def test_warning_shown_when_truncated_without_matches(self):
        text, past = _derivative_text(lib_sentences=0, seed=1)
        result = find_duplicates(text, past_runs=past)
        out = format_duplicates(result)
        self.assertIn("Peringatan", out)
        self.assertIn("Tidak ada kalimat yang berulang", out)

    def test_warning_in_english_too(self):
        result = {"duplicates": [], "count": 0, "checked": 1,
                  "truncated": True, "comparisons_spent": 2000}
        out = format_duplicates(result, lang="en")
        self.assertIn("Warning", out)
        self.assertIn("incomplete", out)

    def test_no_warning_on_normal_result(self):
        result = {"duplicates": [], "count": 0, "checked": 1,
                  "truncated": False, "comparisons_spent": 3}
        out = format_duplicates(result)
        self.assertNotIn("Peringatan", out)
        self.assertNotIn("Warning", out)

    def test_old_dict_without_keys_still_renders(self):
        # Hand-built dicts from before the fix have no "truncated"
        # key: they render as complete, without raising.
        result = {"duplicates": [], "count": 0, "checked": 1}
        out = format_duplicates(result)
        self.assertIn("Tidak ada kalimat yang berulang", out)
        self.assertNotIn("Peringatan", out)


class TestNormalInputEquivalence(unittest.TestCase):
    def test_normal_input_not_truncated(self):
        text, past = _derivative_text(n_sentences=3, lib_sentences=2)
        result = find_duplicates(text, past_runs=past)
        self.assertFalse(result["truncated"])
        self.assertLess(result["comparisons_spent"], 2000)

    def test_normal_input_matches_budget_free_reference(self):
        # On inputs that never reach the budget, the result must be
        # identical to the old budget-free nested loops — same
        # duplicates, same count, same number of comparisons.
        words = ["penelitian", "metode", "kualitatif", "kuantitatif",
                 "data", "analisis", "responden", "wawancara",
                 "observasi", "survei", "hasil", "temuan", "sampel",
                 "populasi", "instrumen", "validitas", "reliabilitas",
                 "hipotesis", "variabel", "pengukuran"]

        def rand_sent(rng):
            n = rng.randint(6, 14)
            return (" ".join(rng.choice(words) for _ in range(n))
                    .capitalize() + ".")

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
                src = tools._split_sentences(rng.choice(past)["text"])
                if src:
                    check.append(rng.choice(src))
            text = " ".join(check)
            for threshold in (0.8, 0.9):
                with self.subTest(seed=seed, threshold=threshold):
                    self.assertEqual(
                        find_duplicates(text, past_runs=past,
                                        threshold=threshold),
                        _brute_force(text, past, threshold=threshold))


class TestCLIDuplicatesTruncated(unittest.TestCase):
    def test_cli_text_output_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rng = random.Random(5)
            lib = [_rand_sent(rng) for _ in range(5)]
            _save(db, " ".join(lib))
            check = " ".join(lib + [_rand_sent(rng)
                                    for _ in range(295)])
            out = io.StringIO()
            with redirect_stdout(out):
                code = duplicates_main(["--text", check, "--db", db])
            self.assertEqual(code, 1)
            self.assertIn("Peringatan", out.getvalue())
            self.assertIn("tidak lengkap", out.getvalue())

    def test_cli_json_carries_truncated_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rng = random.Random(5)
            lib = [_rand_sent(rng) for _ in range(5)]
            _save(db, " ".join(lib))
            check = " ".join(lib + [_rand_sent(rng)
                                    for _ in range(295)])
            out = io.StringIO()
            with redirect_stdout(out):
                code = duplicates_main(["--text", check, "--db", db,
                                        "--json"])
            self.assertEqual(code, 1)
            parsed = json.loads(out.getvalue())
            self.assertTrue(parsed["truncated"])
            self.assertEqual(parsed["comparisons_spent"], 2000)
            self.assertEqual(parsed["count"], 5)


class TestAnalyzeReportWarning(unittest.TestCase):
    def test_analyze_duplicates_flag_warns_when_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            rng = random.Random(5)
            lib = [_rand_sent(rng) for _ in range(5)]
            _save(db, " ".join(lib))
            check = " ".join(lib + [_rand_sent(rng)
                                    for _ in range(295)])
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([
                    "--text", check, "--refs", tools.DEFAULT_REFS,
                    "--no-verify", "--duplicates", "--db", db])
            self.assertEqual(code, 0)
            self.assertIn("Peringatan", out.getvalue())
            self.assertIn("tidak lengkap", out.getvalue())

    def test_format_analyze_warns_on_truncated_dict(self):
        refs = tools.load_references(tools.DEFAULT_REFS)
        result = tools.analyze_text_quality(
            "Penelitian ini menggunakan metode kualitatif.",
            refs, lang="id", verify_dois=False)
        result["duplicates"] = {"duplicates": [], "count": 0,
                                "checked": 1, "truncated": True,
                                "comparisons_spent": 2000}
        out = format_analyze(result)
        self.assertIn("Peringatan", out)
        self.assertIn("tidak lengkap", out)


class TestWebUIWarning(unittest.TestCase):
    def test_page_renders_truncation_warning(self):
        # The analyze card is rendered client-side from the JSON
        # result; the served page must branch on d.truncated in
        # both the "found" and the "none found" branches.
        html = tools.WEB_UI_HTML
        self.assertIn("d.truncated", html)
        self.assertIn("Peringatan: pemeriksaan berhenti setelah",
                      html)
        self.assertIn("truncWarn", html)
        # Defined once, used in both branches of the card.
        self.assertGreaterEqual(html.count("truncWarn"), 3)


if __name__ == "__main__":
    unittest.main()
