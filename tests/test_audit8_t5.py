"""Audit #8 T-5: HEAD, strict id/limit, citation intro, re- pins,
split tail + docstring, Pustaka menu id, interest policy.

N-1: HEAD is GET without a body. N-2: only ASCII digits (with an
optional leading "+") parse as id/limit. N-3: the multi-citation
intro is case-insensitive and never leaks through the narrative
path. N-4: "re-" + vowel stems are pinned lexically. N-5/N-6:
the split docstring and tail. N-7: the Pustaka menu speaks up
on a bad id. N-8: the interest policy, per word.
"""
import http.client
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_cli
import academic_tools as tools
from academic_tools import _count_syllables, _split_sentences

TEXT = (
    "Metode penelitian ini memakai purposive sampling dan thematic analysis. "
    "Hasilnya sejalan dengan temuan sebelumnya [cite:devlin2019]."
)

REFS = {
    "field2018": {"authors": ["Field"], "year": 2018, "title": "T"},
    "creswell2018": {"authors": ["Creswell"], "year": 2018, "title": "C"},
}


def _request(base, method, path, payload=None):
    url = base + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def _request_head(base, path):
    host, port = base.split("://", 1)[1].rsplit(":", 1)
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    conn.request("HEAD", path)
    resp = conn.getresponse()
    body = resp.read()
    headers = dict(resp.getheaders())
    status = resp.status
    conn.close()
    return status, headers, body


def run_cli(answers):
    """Run the interactive menu with scripted input; return (code, output)."""
    buf = io.StringIO()
    with patch("builtins.input", side_effect=answers), redirect_stdout(buf):
        code = academic_cli.main([])
    return code, buf.getvalue()


class TestAudit8Head(unittest.TestCase):
    """N-1: HEAD is GET without a body."""

    @classmethod
    def setUpClass(cls):
        cls.server = tools.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_head_home(self):
        get_status, get_body = _request(self.base, "GET", "/")
        self.assertEqual(get_status, 200)
        status, headers, body = _request_head(self.base, "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(int(headers["Content-Length"]), len(get_body.encode("utf-8")))
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("X-Content-Type-Options", headers)
        self.assertIn("X-Frame-Options", headers)

    def test_head_unknown_path_is_404_no_body(self):
        status, headers, body = _request_head(self.base, "/nope")
        self.assertEqual(status, 404)
        self.assertEqual(body, b"")
        self.assertIn("Content-Security-Policy", headers)

    def test_head_api(self):
        status, headers, body = _request_head(self.base, "/api/prompts")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers["Content-Type"],
                         "application/json; charset=utf-8")


class TestAudit8StrictIdLimit(unittest.TestCase):
    """N-2: int() was too loose — 1_0, full-width １, " 1"."""

    @classmethod
    def setUpClass(cls):
        cls.server = tools.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "library.db")
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": cls.db}):
            status, _ = _request(cls.base, "POST", "/api/analyze",
                                 {"text": TEXT, "save": True})
            assert status == 200

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def _get(self, path):
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": self.db}):
            return _request(self.base, "GET", path)

    def test_id_underscore_is_400(self):
        status, _ = self._get("/api/library/analysis?id=1_0")
        self.assertEqual(status, 400)

    def test_id_fullwidth_is_400(self):
        # "１" is full-width U+FF11, percent-encoded: int() reads it
        # as 1, the strict parser must not.
        status, _ = self._get("/api/library/analysis?id=%EF%BC%91")
        self.assertEqual(status, 400)

    def test_id_space_is_400(self):
        status, _ = self._get("/api/library/analysis?id=%201")
        self.assertEqual(status, 400)

    def test_id_plus_one_still_200(self):
        # Audit #7 N-7, unchanged: the VALUE "+1" is id 1
        # (URL-encoded: a literal "+" decodes to a space).
        status, body = self._get("/api/library/analysis?id=%2B1")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["analysis"]["id"], 1)

    def test_id_zero_still_404(self):
        status, _ = self._get("/api/library/analysis?id=0")
        self.assertEqual(status, 404)

    def test_id_leading_zero_still_200(self):
        status, _ = self._get("/api/library/analysis?id=01")
        self.assertEqual(status, 200)

    def test_limit_underscore_is_400(self):
        status, _ = self._get("/api/library/history?limit=1_0")
        self.assertEqual(status, 400)

    def test_limit_fullwidth_is_400(self):
        status, _ = self._get("/api/library/history?limit=%EF%BC%91")
        self.assertEqual(status, 400)

    def test_limit_space_is_400(self):
        status, _ = self._get("/api/library/history?limit=%205")
        self.assertEqual(status, 400)

    def test_limit_plus_still_works(self):
        status, body = self._get("/api/library/history?limit=%2B5")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["analyses"]), 1)

    def test_limit_zero_clamps_to_one(self):
        status, body = self._get("/api/library/history?limit=0")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["analyses"]), 1)


class TestAudit8CitationIntro(unittest.TestCase):
    """N-3: intro case-insensitive; narrative path does not leak."""

    def test_intro_uppercase_works(self):
        res = tools.audit_citations(
            "(Field, 2018; LIHAT JUGA Creswell, 2018)", REFS)
        self.assertIn("creswell2018", res["author_year"])

    def test_intro_mixed_case_works(self):
        res = tools.audit_citations(
            "(Field, 2018; Lihat Juga Creswell, 2018)", REFS)
        self.assertIn("creswell2018", res["author_year"])
        res = tools.audit_citations(
            "(Field, 2018; BANDINGKAN Creswell, 2018)", REFS)
        self.assertIn("creswell2018", res["author_year"])
        res = tools.audit_citations(
            "(Field, 2018; CF. Creswell, 2018)", REFS)
        self.assertIn("creswell2018", res["author_year"])

    def test_narrative_intro_not_credited(self):
        # Audit #8 N-3: the audit #6 negative only held inside
        # parentheses; "Menurut lihat Field (2018)" was credited.
        res = tools.audit_citations("Menurut lihat Field (2018)", REFS)
        self.assertEqual(res["author_year"], [])
        self.assertIn("field2018", res["unused"])

    def test_narrative_intro_uppercase_not_credited(self):
        res = tools.audit_citations("Menurut LIHAT JUGA Field (2018)", REFS)
        self.assertEqual(res["author_year"], [])

    def test_narrative_clean_still_credited(self):
        res = tools.audit_citations("Menurut Field (2018)", REFS)
        self.assertIn("field2018", res["author_year"])

    def test_narrative_dilihat_still_credited(self):
        # "dilihat" is a different word — the \b guard must not
        # treat it as the intro "lihat".
        res = tools.audit_citations("dilihat Field (2018)", REFS)
        self.assertIn("field2018", res["author_year"])

    def test_narrative_mixed_occurrences(self):
        # One intro-prefixed occurrence must not hide a clean one.
        res = tools.audit_citations(
            "Menurut lihat Field (2018). Field (2018) juga.", REFS)
        self.assertIn("field2018", res["author_year"])

    def test_parenthetical_negative_still_holds(self):
        res = tools.audit_citations("(lihat Field, 2018)", REFS)
        self.assertEqual(res["author_year"], [])


class TestAudit8RePins(unittest.TestCase):
    """N-4: "re-" + vowel stems, pinned lexically only."""

    WORDS = {
        "reassess": 3, "reassessment": 4,
        "reapply": 3, "reappear": 3, "reaffirm": 3,
        "rearrange": 3, "reissue": 3, "reopen": 3,
        "reiterate": 4,
    }
    GUARDS = {"read": 1, "reason": 2, "really": 2}

    def test_re_words(self):
        for word, want in self.WORDS.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word, "en"), want)

    def test_no_blanket_rule(self):
        # A blanket "re- + vowel" rule would break these.
        for word, want in self.GUARDS.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word, "en"), want)


class TestAudit8SplitTailAndDocs(unittest.TestCase):
    """N-5/N-6: the degree trade-off in the docstring; the tail."""

    def test_tail_drops_abbreviation_dot(self):
        self.assertEqual(_split_sentences("Ia pergi. Dr."),
                         ["Ia pergi", "Dr"])
        self.assertEqual(_split_sentences("Ia pergi. M.Si."),
                         ["Ia pergi", "M.Si"])
        self.assertEqual(_split_sentences("Dr."), ["Dr"])

    def test_degree_tradeoff_still_accepted(self):
        # Audit #8 N-5, docs only: every dotted degree and
        # honorific at a sentence end merges with the next one.
        for text in ("Gelarnya Dr. rer. nat. Ia mengajar.",
                     "Gelarnya M.Si. Ia mengajar.",
                     "Nama saya Budi, S.Si. Saya peneliti.",
                     "Hubungi Bpk. Ia ada."):
            with self.subTest(text=text):
                self.assertEqual(len(_split_sentences(text)), 1)

    def test_docstring_covers_all_degrees(self):
        doc = _split_sentences.__doc__
        for fragment in ("M.Si.", "S.Si.", "Bpk."):
            self.assertIn(fragment, doc)

    def test_interest_policy_in_docstring(self):
        # Audit #8 N-8: the policy, per word, with sources.
        doc = _count_syllables.__doc__
        for fragment in ('"interest" 2', '"interested" 3',
                         '"interesting"', "full 4", '"interestedly"'):
            self.assertIn(fragment, doc)


class TestAudit8LibraryMenu(unittest.TestCase):
    """N-7: the Pustaka menu speaks up on a bad id."""

    def _run_detail(self, db, answers):
        # 6 = Pustaka, 2 = detail, then the id, "" = pause,
        # 0 = back, 0 = exit.
        with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
            return run_cli(["6", "2"] + answers + ["", "0", "0"])

    def test_invalid_id_shows_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _, out = self._run_detail(db, ["abc"])
            self.assertIn("ID analisis tidak valid", out)

    def test_underscore_id_rejected_like_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _, out = self._run_detail(db, ["1_0"])
            self.assertIn("ID analisis tidak valid", out)
            self.assertNotIn("Tidak ada analisis 1_0", out)

    def test_missing_id_shows_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _, out = self._run_detail(db, ["99"])
            self.assertIn("Tidak ada analisis 99", out)

    def test_zero_id_shows_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            _, out = self._run_detail(db, ["0"])
            self.assertIn("Tidak ada analisis 0", out)

    def test_plus_one_and_spaced_still_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                tools.save_analysis(
                    TEXT,
                    tools.analyze_text_quality(TEXT, verify_dois=False),
                    {}, db=db, title="Bab 1")
            for raw in ("+1", " 1 "):
                with self.subTest(raw=raw):
                    _, out = self._run_detail(db, [raw])
                    self.assertIn("Bab 1", out)


class TestAudit8SaveAnalysisMessage(unittest.TestCase):
    """Audit #8 note (A): save_analysis must not leak the raw
    exception when a reference cannot be serialized."""

    def test_generic_message_no_leak(self):
        result = tools.analyze_text_quality(TEXT, verify_dois=False)
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with self.assertRaises(ValueError) as ctx:
                tools.save_analysis(
                    TEXT, result,
                    {"bad": {"title": "T", "note": object()}},
                    db=db)
            msg = str(ctx.exception)
            self.assertEqual(msg, "referensi 'bad' tidak bisa disimpan")
            self.assertNotIn("Object of type", msg)
            self.assertNotIn("serializable", msg)


if __name__ == "__main__":
    unittest.main()
