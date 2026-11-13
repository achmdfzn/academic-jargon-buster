"""Tests for audit #5 (v1.27.2) server fixes, track 5: H-10, H-11,
H-12, H-13, N-9 — tests T-4, T-5, T-6, T-7.

H-10: deeply nested JSON must be a 400, never a 500 (RecursionError
caught at both json.loads sites).
H-11: send_error must not write a body for HEAD, and must send
`Connection: close` when the connection is being closed.
H-12: the Readability card must not clamp avg_syllables_per_word
to 100.
H-13: a Transfer-Encoding header must be a 400, never silently
ignored.
N-9: save_analysis with an incomplete result dict must raise
ValueError before writing anything, never a bare KeyError.

The server runs on an ephemeral localhost port in a thread; no
external network is used. Raw-socket helpers mirror
tests/test_audit4_server.py; the Node render helper mirrors
tests/test_audit4_readability.py (T-3).
"""

import http.client
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import save_analysis

TEXT = "Penelitian ini menggunakan metode survei. Data dikumpulkan melalui kuesioner."

# Minimal valid result shape (same fields save_analysis needs;
# cf. MIN_RESULT in tests/test_audit4_hash.py).
MIN_RESULT = {"quality_score": 90, "jargon": [], "citations": {},
              "doi_verification": {}, "style": {"style_score": 20},
              "suggestions": {"count": 0}}


def _recv_all(s, timeout=3.0):
    """Read until EOF (True) or timeout (False).

    On Windows a peer that closes with unread data RSTs the
    connection, so recv raises ConnectionResetError /
    ConnectionAbortedError instead of returning b"" — treat
    that as EOF too (the server did close; the client just
    observes it as an abort).
    """
    s.settimeout(timeout)
    out = b""
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                return out, True
            out += chunk
    except socket.timeout:
        return out, False
    except (ConnectionResetError, ConnectionAbortedError):
        return out, True


def _read_response(s, timeout=5.0):
    """Read one HTTP/1.1 response (headers + Content-Length body).

    Returns (status_line, headers_dict, body). Used when the
    connection stays open (keep-alive), so reading to EOF is not
    an option.
    """
    s.settimeout(timeout)
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    status = lines[0].decode("latin-1", "replace")
    headers = {}
    for line in lines[1:]:
        if b":" in line:
            key, value = line.split(b":", 1)
            headers[key.decode("latin-1").strip().lower()] = \
                value.decode("latin-1").strip()
    length = int(headers.get("content-length", "0"))
    body = rest
    while len(body) < length:
        chunk = s.recv(65536)
        if not chunk:
            break
        body += chunk
    return status, headers, body[:length]


def _post_raw(s, path, body, extra_headers=b""):
    s.sendall(b"POST " + path.encode() + b" HTTP/1.1\r\nHost: x\r\n"
              b"Content-Type: application/json\r\n"
              b"Content-Length: %d\r\n" % len(body)
              + extra_headers + b"\r\n" + body)


class _ServerCase(unittest.TestCase):
    """One throwaway server per test class, like tests/test_serve.py."""

    @classmethod
    def setUpClass(cls):
        cls.server = tools.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.host, cls.port = host, port
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()


class TestAudit5DeepJson(_ServerCase):
    """T-4 / H-10: deeply nested JSON is a 400, never a 500."""

    def test_deep_nesting_returns_400_not_500(self):
        # '[' * 10000 + ']' * 10000 blows past the recursion
        # limit inside json.loads: before the fix that escaped
        # as a RecursionError and the handler's generic
        # `except Exception` turned it into a 500.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            body = (b"[" * 10000) + (b"]" * 10000)
            _post_raw(s, "/api/analyze", body)
            status, _, data = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 400 Bad Request")
            self.assertIn(b"badan permintaan harus JSON yang valid",
                          data)
            # Keep-alive survives the 400: the next request on
            # the same connection gets its own response.
            s.sendall(b"GET /api/prompts HTTP/1.1\r\nHost: x\r\n\r\n")
            status, _, body2 = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 200 OK")
            self.assertEqual(len(json.loads(body2)["prompts"]), 18)
        finally:
            s.close()

    def test_nesting_9000_control_is_400_object(self):
        # 500 levels still parse on every supported platform,
        # but the value is a list, not an object — the same 400
        # as before the fix, never a 500. (The depth used to be
        # 9000, but the recursion threshold inside json.loads is
        # platform-dependent: 9000 parses on Python 3.12/Linux
        # yet already overflows on Python 3.9 and on Windows,
        # where it takes the RecursionError path instead — same
        # 400 status, different message. 500 is safely below the
        # threshold everywhere while still being deep nesting.)
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            body = (b"[" * 500) + (b"]" * 500)
            _post_raw(s, "/api/analyze", body)
            status, _, data = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 400 Bad Request")
            self.assertIn(
                b"badan permintaan harus berupa objek JSON", data)
        finally:
            s.close()

    def test_deep_nested_refs_json_returns_400(self):
        # The second json.loads site (_load_ui_references): a
        # deeply nested refs_json string must be a 400 too.
        with self.assertRaises(ValueError):
            tools._load_ui_references(
                {"refs_json": "[" * 10000 + "]" * 10000})
        conn = http.client.HTTPConnection(self.host, self.port,
                                         timeout=10)
        try:
            conn.request(
                "POST", "/api/analyze",
                body=json.dumps(
                    {"text": TEXT,
                     "refs_json": "[" * 10000 + "]" * 10000}),
                headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = resp.read()
            self.assertEqual(resp.status, 400)
            self.assertIn(b"bibliografi JSON tidak valid", data)
        finally:
            conn.close()


class TestAudit5HeadError(_ServerCase):
    """T-5 / H-11: a HEAD error response carries no body bytes.

    Audit #8 N-1 added do_HEAD, so the old route is gone: HEAD
    used to hit the stdlib 501 (no do_HEAD) and the H-11 guard in
    send_error kept its body out of the socket. Now HEAD routes
    like GET — /api/prompts is a 200, /nope a JSON 404 — and the
    body is skipped by _send_json/_send_page instead. The
    send_error guard stays as defense-in-depth (no HEAD request
    can reach send_error with the command set any more: a bad
    request line or version fails before command is assigned,
    and those responses are header-less HTTP/0.9-style on
    Python <=3.12 by stdlib design)."""

    def test_head_error_has_no_body(self):
        # HEAD /nope is the JSON 404 now: same Content-Length as
        # the GET 404 body, zero body bytes on the wire.
        conn = http.client.HTTPConnection(self.host, self.port,
                                         timeout=10)
        try:
            conn.request("GET", "/nope")
            resp = conn.getresponse()
            get_body = resp.read()
            self.assertEqual(resp.status, 404)
            conn.request("HEAD", "/nope")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 404)
            self.assertEqual(resp.read(), b"")
            self.assertEqual(resp.getheader("Content-Length"),
                             str(len(get_body)))
            self.assertIsNotNone(
                resp.getheader("Content-Security-Policy"))
            self.assertEqual(
                resp.getheader("X-Content-Type-Options"), "nosniff")
            self.assertEqual(
                resp.getheader("X-Frame-Options"), "DENY")
        finally:
            conn.close()

    def test_get_after_head_on_same_connection(self):
        # Reuse is not broken by the HEAD fix: the next request
        # on the same connection gets its own response.
        conn = http.client.HTTPConnection(self.host, self.port,
                                         timeout=10)
        try:
            conn.request("HEAD", "/api/prompts")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read(), b"")
            head_length = resp.getheader("Content-Length")
            conn.request("GET", "/api/prompts")
            resp = conn.getresponse()
            data = resp.read()
            self.assertEqual(resp.status, 200)
            self.assertEqual(head_length, str(len(data)))
            self.assertEqual(len(json.loads(data)["prompts"]), 18)
        finally:
            conn.close()

    def test_non_head_error_still_sends_body(self):
        # Control: the guard only skips HEAD — a PUT 501 still
        # carries the 84-byte error page.
        conn = http.client.HTTPConnection(self.host, self.port,
                                         timeout=10)
        try:
            conn.request("PUT", "/api/detect", body=b"{}")
            resp = conn.getresponse()
            data = resp.read()
            self.assertEqual(resp.status, 501)
            self.assertEqual(len(data), 84)
            self.assertEqual(resp.getheader("Content-Length"), "84")
            self.assertEqual(resp.getheader("Connection"), "close")
            self.assertIn(b"<h1>501</h1>", data)
        finally:
            conn.close()


class TestAudit5TransferEncoding(_ServerCase):
    """T-6 / H-13: Transfer-Encoding is a 400, never ignored."""

    def test_content_length_plus_chunked_is_400(self):
        # CL + TE: trusting the Content-Length would leave the
        # chunked body unread and desync keep-alive.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: x\r\n'
                      b'Content-Type: application/json\r\n'
                      b'Content-Length: 15\r\n'
                      b'Transfer-Encoding: chunked\r\n\r\n'
                      b'{"text":"hi"}')
            data, eof = _recv_all(s)
            self.assertTrue(eof, "connection must close after the 400")
            self.assertTrue(data.startswith(b"HTTP/1.1 400"))
            self.assertIn(b"Transfer-Encoding tidak didukung", data)
        finally:
            s.close()

    def test_chunked_without_content_length_is_400(self):
        # Chunked with no Content-Length: before the fix the
        # header was ignored, the body read as empty, and the
        # request failed later as "teks kosong" — the framing
        # was silently dropped instead of rejected.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: x\r\n'
                      b'Content-Type: application/json\r\n'
                      b'Transfer-Encoding: chunked\r\n\r\n'
                      b'5\r\n{"text":"hi"}\r\n0\r\n\r\n')
            data, eof = _recv_all(s)
            self.assertTrue(eof, "connection must close after the 400")
            self.assertTrue(data.startswith(b"HTTP/1.1 400"))
            self.assertIn(b"Transfer-Encoding tidak didukung", data)
        finally:
            s.close()

    def test_transfer_encoding_on_folder_upload_is_400(self):
        # _read_body is shared: the folder-upload path rejects TE
        # the same way instead of parsing a half-read multipart.
        boundary = "----audit5te"
        body = (b"--" + boundary.encode() + b"\r\n"
                b'Content-Disposition: form-data; name="files"; '
                b'filename="a.txt"\r\nContent-Type: text/plain\r\n\r\n'
                + TEXT.encode() + b"\r\n--" + boundary.encode()
                + b"--\r\n")
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b"POST /api/analyze-folder HTTP/1.1\r\nHost: x\r\n"
                      + b"Content-Type: multipart/form-data; boundary="
                      + boundary.encode() + b"\r\n"
                      + b"Content-Length: %d\r\n" % len(body)
                      + b"Transfer-Encoding: chunked\r\n\r\n" + body)
            data, eof = _recv_all(s)
            self.assertTrue(eof, "connection must close after the 400")
            self.assertTrue(data.startswith(b"HTTP/1.1 400"))
            self.assertIn(b"Transfer-Encoding tidak didukung", data)
        finally:
            s.close()

    def test_normal_request_without_te_still_200(self):
        # Control: a plain request with no TE header is unaffected.
        conn = http.client.HTTPConnection(self.host, self.port,
                                         timeout=10)
        try:
            conn.request("POST", "/api/analyze",
                         body=json.dumps({"text": TEXT}),
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = resp.read()
            self.assertEqual(resp.status, 200)
            self.assertEqual(json.loads(data)["quality_score"], 100)
        finally:
            conn.close()


class TestAudit5SaveAnalysis(unittest.TestCase):
    """N-9: an incomplete result dict is a ValueError before
    anything is written — never a bare KeyError from the INSERT."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "library.db")

    def tearDown(self):
        self.tmp.cleanup()

    def _row_count(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM analyses").fetchone()[0]
        finally:
            conn.close()

    def test_empty_result_raises_and_writes_nothing(self):
        # The reported case: {} used to raise a bare KeyError
        # ('quality_score') from inside the INSERT — after the
        # connection was already opened.
        with self.assertRaises(ValueError) as cm:
            save_analysis("teks uji.", {}, db=self.db)
        self.assertIn("quality_score", str(cm.exception))
        self.assertFalse(os.path.exists(self.db),
                         "no DB file may be created by a rejected save")

    def test_seeded_db_row_count_unchanged(self):
        save_analysis(TEXT, dict(MIN_RESULT), db=self.db)
        self.assertEqual(self._row_count(), 1)
        for bad in ({},
                    {"jargon": []},
                    {"quality_score": 90},
                    {"quality_score": 90, "style": {}},
                    {"quality_score": 90,
                     "style": {"style_score": 20}, "jargon": "x"},
                    {"quality_score": 90,
                     "style": {"style_score": 20},
                     "suggestions": None}):
            with self.subTest(result=bad):
                with self.assertRaises(ValueError):
                    save_analysis("teks uji.", bad, db=self.db)
        self.assertEqual(self._row_count(), 1,
                         "rejected saves must not add rows")

    def test_non_dict_result_raises(self):
        for bad in (None, [], "hasil"):
            with self.subTest(result=repr(bad)):
                with self.assertRaises(ValueError):
                    save_analysis("teks uji.", bad, db=self.db)
        self.assertFalse(os.path.exists(self.db))

    def test_minimal_valid_result_still_saves(self):
        # Control: the shape used by tests/test_audit4_hash.py
        # (MIN_RESULT) is accepted unchanged.
        rid = save_analysis(TEXT, dict(MIN_RESULT), db=self.db)
        self.assertEqual(rid, 1)
        self.assertEqual(self._row_count(), 1)


# ----------------------------------------------------------------------
# T-7: Node render of the Readability card (H-12).
#
# Same harness as T-3 in tests/test_audit4_readability.py: extract
# the page <script>, export renderAnalyze, render in Node, and
# compare every number with Python. The fixture overrides only
# avg_syllables_per_word to 300.0 — no real text has 300 syllables
# per word, so Python cannot produce it; the comparison is that
# the card shows the overridden value verbatim (not clamped to
# 100) while every other number still matches Python.
# ----------------------------------------------------------------------

_NODE_STUB = """
var __el = function () {
  return {
    addEventListener: function () {},
    classList: {add: function () {}, remove: function () {}},
    setAttribute: function () {}, appendChild: function () {},
    dataset: {}, style: {}, disabled: false,
    value: "", textContent: "", innerHTML: ""
  };
};
var document = {
  getElementById: function () { return __el(); },
  createElement: function () { return __el(); },
  querySelector: function () { return null; },
  querySelectorAll: function () { return {forEach: function () {}}; }
};
var navigator = {clipboard: {writeText: function () { return Promise.resolve(); }}};
var fetch = function () { return Promise.reject(new Error("no network in test")); };
"""


def _page_script():
    """The page's <script> block, extracted from WEB_UI_HTML."""
    html = tools.WEB_UI_HTML
    assert html.count("<script>") == 1, "page must have one script block"
    return html.split("<script>", 1)[1].split("</script>", 1)[0]


def _render_analyze_html(res, lang, test_case):
    """Render renderAnalyze(res, lang) in Node; return the HTML."""
    script = _page_script()
    test_case.assertTrue(script.rstrip().endswith("})();"))
    script = (script.rstrip()[:-len("})();")]
              + "; globalThis.__renderAnalyze = renderAnalyze; })();")
    js = (_NODE_STUB + script + "\nconsole.log(__renderAnalyze("
          + json.dumps(res) + ", " + json.dumps(lang) + "));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        # Bytes mode + explicit UTF-8 decode (see _run_node in
        # test_audit4_server.py): text=True decodes with the
        # locale encoding, which is cp1252 on Windows and turns
        # the em dash in the Readability card into mojibake, so
        # the card regex stops matching. Node writes UTF-8.
        proc = subprocess.run(["node", path], capture_output=True,
                              timeout=30)
        proc.stdout = proc.stdout.decode("utf-8")
        proc.stderr = proc.stderr.decode("utf-8")
    finally:
        os.unlink(path)
    test_case.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout


@unittest.skipUnless(shutil.which("node"), "node tidak tersedia")
class TestAudit5ReadabilityCard(unittest.TestCase):
    """T-7 / H-12: avg_syllables_per_word is not clamped to 100."""

    def _check_card(self, res, lang="id"):
        py = res["readability"]
        html = _render_analyze_html(res, lang, self)
        if lang == "en":
            m = re.search(
                r"Flesch Reading Ease ([\d.]+)/100 — (\w[\w ]*)"
                r"<br>Flesch-Kincaid Grade Level ([\d.]+)"
                r"<br>Average ([\d.]+) words/sentence, ([\d.]+) syllables/word "
                r"\((\d+) words, (\d+) sentences, (\d+) syllables\)",
                html)
        else:
            m = re.search(
                r"Flesch Reading Ease ([\d.]+)/100 — ([^<]*)"
                r"<br>Flesch-Kincaid Grade Level ([\d.]+)"
                r"<br>Rata-rata ([\d.]+) kata/kalimat, ([\d.]+) suku kata/kata "
                r"\((\d+) kata, (\d+) kalimat, (\d+) suku kata\)",
                html)
        self.assertIsNotNone(m, "Readability card not found in:\n" + html)
        re_s, band_s, fkgl_s, wps_s, spw_s, w_s, s_s, syl_s = m.groups()
        self.assertEqual(re_s, f"{py['flesch_reading_ease']:.1f}")
        self.assertEqual(band_s, py["band"])
        self.assertEqual(float(fkgl_s), py["flesch_kincaid_grade"])
        self.assertEqual(float(wps_s), py["avg_words_per_sentence"])
        self.assertEqual(float(spw_s), py["avg_syllables_per_word"])
        self.assertEqual(int(w_s), py["words"])
        self.assertEqual(int(s_s), py["sentences"])
        self.assertEqual(int(syl_s), py["total_syllables"])
        return py, html

    def test_avg_syllables_per_word_300_not_clamped(self):
        # H-12 repro: the card called num(r.avg_syllables_per_word,
        # 100), so a value of 300 rendered as 100 — like the FKGL
        # 628.4 -> 100 clamp T-3 caught in audit #4. The sibling
        # avg_words_per_sentence was never clamped; neither is
        # this one now.
        res = tools.analyze_text_quality(TEXT, lang="id",
                                         verify_dois=False)
        res["readability"]["avg_syllables_per_word"] = 300.0
        py, _ = self._check_card(res)
        self.assertEqual(py["avg_syllables_per_word"], 300.0)

    def test_js_parses_clean(self):
        # node --check on the extracted page script.
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False,
                                         encoding="utf-8") as f:
            f.write(_page_script())
            path = f.name
        try:
            proc = subprocess.run(["node", "--check", path],
                                  capture_output=True, text=True,
                                  encoding="utf-8", timeout=30)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
