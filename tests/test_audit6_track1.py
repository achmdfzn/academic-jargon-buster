"""Tests for audit #6 (v1.27.3), track t1: B-1, H-1, H-2 — tests
T-2, T-3, T-4.

B-1 / T-4: the audit #5 B-1 fix (the duplicates check carries
"truncated" + "comparisons_spent" and every renderer warns) stopped
at the single-file path — the folder path kept only the count, so a
silently cut check looked complete in the CLI (text and --json),
in /api/analyze-folder, and in the web UI folder table. The folder
entry now carries "duplicates_truncated" and
"duplicates_comparisons_spent" alongside the count, and all three
renderers warn.

H-1 / T-2: _send_json never sent "Connection: close" even when
_read_body had set close_connection (bad framing, oversize body),
so a reusing client got EOF instead of a response. Error JSON
responses (400/413) on a closing connection must carry the header;
an ordinary 400 must keep keep-alive working (control).

H-2 / T-3: the single-file web UI warning called
num(d.comparisons_spent, 0) — num() clamps n > max to max, so
max=0 forced every value to 0 and the warning read "0
perbandingan". The render test uses a REAL extreme text
(1500x"mempertahankan", FKGL 628.4) instead of overriding
avg_syllables_per_word, and checks the spent count in the warning.

The server runs on an ephemeral localhost port in a thread; no
external network is used. Raw-socket and Node-render helpers mirror
tests/test_audit5_server.py and tests/test_audit4_readability.py.
"""

import http.client
import io
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    _MAX_DUPLICATE_COMPARISONS,
    analyze_folder,
    analyze_main,
    find_duplicates,
    format_folder_result,
)

POOL = ["penelitian", "metode", "data", "analisis", "hasil",
        "responden", "wawancara", "observasi", "sampel", "temuan"]


def _rand_sent(rng, n=12):
    return " ".join(rng.choice(POOL) for _ in range(n)).capitalize() + "."


def _derivative_text(n_sentences=300, seed=5, lib_sentences=5):
    """300 sentences from a 10-word pool vs a small library — the
    audit #5 fixture: the 2000-comparison budget is exhausted, so
    the result is truncated. Returns (text, lib_sentences)."""
    rng = random.Random(seed)
    lib = [_rand_sent(rng) for _ in range(lib_sentences)]
    text = " ".join(lib + [_rand_sent(rng)
                           for _ in range(n_sentences - lib_sentences)])
    return text, lib


def _save(db, text, title="Bab 1"):
    refs = tools.load_references(tools.DEFAULT_REFS)
    result = tools.analyze_text_quality(text, refs, lang="id",
                                        verify_dois=False)
    return tools.save_analysis(text, result, refs, title=title, db=db)


def _seeded_folder(tmp, lib_sentences=5):
    """A folder with one heavily derivative file, plus a library DB
    seeded with its library sentences. Returns (folder, db)."""
    db = os.path.join(tmp, "library.db")
    text, lib = _derivative_text(lib_sentences=lib_sentences)
    _save(db, " ".join(lib))
    folder = os.path.join(tmp, "folder")
    os.mkdir(folder)
    with open(os.path.join(folder, "bab1.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    return folder, db


# ----------------------------------------------------------------------
# T-4 / B-1: the truncated flag survives the folder path.
# ----------------------------------------------------------------------

class TestFolderTruncatedFlag(unittest.TestCase):
    def test_analyze_folder_entry_carries_truncated_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, db = _seeded_folder(tmp)
            refs = tools.load_references(tools.DEFAULT_REFS)
            result = analyze_folder(folder, refs, lang="id",
                                    verify_dois=False, duplicates=True,
                                    db=db)
            entry = result["files"][0]
            # The count itself is unchanged (the old shape).
            self.assertEqual(entry["duplicates"], 5)
            self.assertTrue(entry["duplicates_truncated"])
            self.assertEqual(entry["duplicates_comparisons_spent"],
                             _MAX_DUPLICATE_COMPARISONS)

    def test_analyze_folder_entry_not_truncated_on_small_input(self):
        # Control: a small input is a complete check — flag False,
        # spent below the budget, and no warning in the table.
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            folder = os.path.join(tmp, "folder")
            os.mkdir(folder)
            with open(os.path.join(folder, "bab1.txt"), "w",
                      encoding="utf-8") as f:
                f.write("Penelitian ini menggunakan metode survei "
                        "untuk mengumpulkan data primer. "
                        "Data dianalisis dengan statistik deskriptif "
                        "dan disajikan dalam bentuk tabel.")
            refs = tools.load_references(tools.DEFAULT_REFS)
            result = analyze_folder(folder, refs, lang="id",
                                    verify_dois=False, duplicates=True,
                                    db=db)
            entry = result["files"][0]
            self.assertFalse(entry["duplicates_truncated"])
            self.assertLess(entry["duplicates_comparisons_spent"],
                            _MAX_DUPLICATE_COMPARISONS)
            self.assertNotIn(
                "Peringatan",
                format_folder_result(result, lang="id"))

    def test_cli_folder_text_warns_when_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, db = _seeded_folder(tmp)
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([folder, "--duplicates", "--db", db,
                                     "--no-verify"])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("Peringatan", text)
            self.assertIn("bab1.txt: Peringatan: pemeriksaan duplikasi "
                          "berhenti setelah 2000 perbandingan "
                          "(batas 2000)", text)
            self.assertIn("tidak lengkap", text)

    def test_cli_folder_json_carries_truncated_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, db = _seeded_folder(tmp)
            out = io.StringIO()
            with redirect_stdout(out):
                code = analyze_main([folder, "--duplicates", "--db", db,
                                     "--no-verify", "--json"])
            self.assertEqual(code, 0)
            entry = json.loads(out.getvalue())["files"][0]
            self.assertEqual(entry["duplicates"], 5)
            self.assertTrue(entry["duplicates_truncated"])
            self.assertEqual(entry["duplicates_comparisons_spent"], 2000)

    def test_cli_folder_text_warns_in_english_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, db = _seeded_folder(tmp)
            refs = tools.load_references(tools.DEFAULT_REFS)
            result = analyze_folder(folder, refs, lang="en",
                                    verify_dois=False, duplicates=True,
                                    db=db)
            text = format_folder_result(result, lang="en")
            self.assertIn(
                "Warning: the duplication check stopped after 2000 "
                "comparisons (limit 2000)", text)


# ----------------------------------------------------------------------
# T-4 / B-1: the flag survives POST /api/analyze-folder.
# ----------------------------------------------------------------------

_BOUNDARY = "----testboundary-audit6-t1"


def _multipart(parts):
    """Build a multipart/form-data body.

    parts: list of (name, filename_or_None, data_bytes).
    """
    out = bytearray()
    for name, filename, data in parts:
        out += b"--" + _BOUNDARY.encode() + b"\r\n"
        disp = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            disp += f'; filename="{filename}"'
        out += disp.encode() + b"\r\n"
        if filename is not None:
            out += b"Content-Type: text/plain\r\n"
        out += b"\r\n" + data + b"\r\n"
    out += b"--" + _BOUNDARY.encode() + b"--\r\n"
    return bytes(out)


def _request_multipart(base, path, parts):
    import urllib.error
    import urllib.request
    body = _multipart(parts)
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Content-Type",
                   f"multipart/form-data; boundary={_BOUNDARY}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


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


class TestApiAnalyzeFolderTruncated(_ServerCase):
    def test_api_folder_upload_carries_truncated_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            text, lib = _derivative_text()
            _save(db, " ".join(lib))
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request_multipart(
                    self.base, "/api/analyze-folder", [
                        ("refs", None, b"sample"),
                        ("duplicates", None, b"1"),
                        ("files", "bab1.txt", text.encode()),
                    ])
            self.assertEqual(status, 200)
            entry = json.loads(body)["folder"]["files"][0]
            self.assertEqual(entry["duplicates"], 5)
            self.assertTrue(entry["duplicates_truncated"])
            self.assertEqual(entry["duplicates_comparisons_spent"],
                             2000)


# ----------------------------------------------------------------------
# T-2 / H-1: error JSON responses carry Connection: close when the
# connection is being closed.
# ----------------------------------------------------------------------

def _recv_all(s, timeout=3.0):
    """Read until EOF (True) or timeout (False)."""
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


def _parse_raw(out):
    """Split a raw response read to EOF into (status, headers)."""
    head, _, _ = out.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    status = lines[0].decode("latin-1", "replace")
    headers = {}
    for line in lines[1:]:
        if b":" in line:
            key, value = line.split(b":", 1)
            headers[key.decode("latin-1").strip().lower()] = \
                value.decode("latin-1").strip()
    return status, headers


class TestSendJsonConnectionClose(_ServerCase):
    """T-2: _send_json must send Connection: close when
    close_connection is set — the audit #5 test only covered the
    send_error path (501), which is why this slipped through."""

    def _assert_closes(self, request, expect_status):
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(request)
            out, eof = _recv_all(s)
        finally:
            s.close()
        status, headers = _parse_raw(out)
        self.assertEqual(status, expect_status)
        self.assertTrue(eof, "server must close the connection")
        self.assertEqual(headers.get("connection"), "close")

    def test_transfer_encoding_400_carries_connection_close(self):
        body = b'{"text": "Penelitian ini memakai metode survei."}'
        self._assert_closes(
            b"POST /api/analyze HTTP/1.1\r\nHost: x\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: %d\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n" % len(body) + body,
            "HTTP/1.1 400 Bad Request")

    def test_invalid_content_length_400_carries_connection_close(self):
        body = b'{"text": "Penelitian ini memakai metode survei."}'
        self._assert_closes(
            b"POST /api/analyze HTTP/1.1\r\nHost: x\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: abc\r\n\r\n" + body,
            "HTTP/1.1 400 Bad Request")

    def test_duplicate_content_length_400_carries_connection_close(self):
        body = b'{"text": "Penelitian ini memakai metode survei."}'
        self._assert_closes(
            b"POST /api/analyze HTTP/1.1\r\nHost: x\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 5\r\nContent-Length: 9\r\n\r\n" + body,
            "HTTP/1.1 400 Bad Request")

    def test_oversize_content_length_413_carries_connection_close(self):
        # 3.000.000 > the 2 MB drain cap: the connection is closed
        # instead of drained, and the 413 must say so.
        # The 413 reason phrase is stdlib-version-dependent:
        # "Request Entity Too Large" (<= Python 3.12) vs
        # "Content Too Large" (Python 3.13+, RFC 9110) — the server
        # renders http.client.responses[413], so the test does too
        # instead of pinning one spelling.
        self._assert_closes(
            b"POST /api/analyze HTTP/1.1\r\nHost: x\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 3000000\r\n\r\n",
            "HTTP/1.1 413 " + http.client.responses[413])

    def test_plain_bad_json_400_keeps_keep_alive(self):
        # Control: an ordinary 400 (invalid JSON, length trusted)
        # must NOT close — keep-alive survives, like the audit #5
        # deep-nesting test pins.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            body = b"not json"
            s.sendall(b"POST /api/analyze HTTP/1.1\r\nHost: x\r\n"
                      b"Content-Type: application/json\r\n"
                      b"Content-Length: %d\r\n\r\n" % len(body) + body)
            status, headers, _ = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 400 Bad Request")
            self.assertNotEqual(headers.get("connection"), "close")
            s.sendall(b"GET /api/prompts HTTP/1.1\r\nHost: x\r\n\r\n")
            status, _, body2 = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 200 OK")
            self.assertEqual(len(json.loads(body2)["prompts"]), 18)
        finally:
            s.close()

    def test_normal_200_has_no_connection_close(self):
        # Control: a normal 200 on HTTP/1.1 stays keep-alive.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b"GET /api/prompts HTTP/1.1\r\nHost: x\r\n\r\n")
            status, headers, _ = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 200 OK")
            self.assertNotEqual(headers.get("connection"), "close")
        finally:
            s.close()


# ----------------------------------------------------------------------
# Node render helpers (mirrors tests/test_audit5_server.py).
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


def _render_in_node(fn_name, payload, lang, test_case):
    """Render fn_name(payload, lang) in Node; return the HTML."""
    script = _page_script()
    test_case.assertTrue(script.rstrip().endswith("})();"))
    script = (script.rstrip()[:-len("})();")]
              + "; globalThis.__fn = " + fn_name + "; })();")
    js = (_NODE_STUB + script + "\nconsole.log(__fn("
          + json.dumps(payload) + ", " + json.dumps(lang) + "));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(js)
        path = f.name
    try:
        proc = subprocess.run(["node", path], capture_output=True,
                              timeout=30)
        proc.stdout = proc.stdout.decode("utf-8")
        proc.stderr = proc.stderr.decode("utf-8")
    finally:
        os.unlink(path)
    test_case.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout


@unittest.skipUnless(shutil.which("node"), "node tidak tersedia")
class TestFolderRenderNode(unittest.TestCase):
    """T-4 / B-1 (web UI): renderFolderResult warns per truncated
    file, with the real spent count — not 0."""

    def test_render_folder_result_warns_with_spent_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, db = _seeded_folder(tmp)
            refs = tools.load_references(tools.DEFAULT_REFS)
            result = analyze_folder(folder, refs, lang="id",
                                    verify_dois=False, duplicates=True,
                                    db=db)
            html = _render_in_node(
                "renderFolderResult",
                {"folder": result, "skipped": []}, "id", self)
            self.assertIn(
                "Peringatan (bab1.txt): pemeriksaan duplikasi "
                "berhenti setelah 2000 perbandingan (batas 2000)",
                html)
            self.assertNotIn("setelah 0 perbandingan", html)

    def test_render_folder_result_silent_when_not_truncated(self):
        # Control: a complete check renders no warning at all.
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "folder")
            os.mkdir(folder)
            with open(os.path.join(folder, "bab1.txt"), "w",
                      encoding="utf-8") as f:
                f.write("Penelitian ini menggunakan metode survei "
                        "untuk mengumpulkan data primer.")
            refs = tools.load_references(tools.DEFAULT_REFS)
            result = analyze_folder(
                folder, refs, lang="id", verify_dois=False,
                duplicates=True, db=os.path.join(tmp, "library.db"))
            html = _render_in_node(
                "renderFolderResult",
                {"folder": result, "skipped": []}, "id", self)
            self.assertNotIn("Peringatan", html)

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


@unittest.skipUnless(shutil.which("node"), "node tidak tersedia")
class TestExtremeTextRender(unittest.TestCase):
    """T-3 / H-2: render a REAL extreme text (1500x"mempertahankan",
    FKGL 628.4) and check the duplicates warning shows the spent
    count — not the audit #5 test's override of
    avg_syllables_per_word=300, and not "0 perbandingan".

    Note: the truncated duplicates result comes from the audit #5
    derivative-text fixture (a real find_duplicates() call that
    exhausts the budget), not from the extreme text itself —
    running difflib on one 1500-word sentence against a corpus is
    a comparison-cost blow-up, not a render concern; the render
    under test only reads the result dict.
    """

    def test_real_extreme_text_renders_fkgl_and_spent_count(self):
        text = "mempertahankan " * 1500
        py = tools.readability_score(text, lang="id")
        self.assertEqual(py["flesch_kincaid_grade"], 628.4)
        self.assertEqual(py["flesch_reading_ease"], 0.0)
        self.assertEqual(py["avg_words_per_sentence"], 1500.0)
        self.assertEqual(py["avg_syllables_per_word"], 5.0)
        res = tools.analyze_text_quality(text, lang="id",
                                         verify_dois=False)
        check, lib = _derivative_text()
        past = [{"id": 1, "title": "Bab 1",
                 "created_at": "2026-11-12T10:00:00+07:00",
                 "text": " ".join(lib)}]
        dup = find_duplicates(check, past_runs=past)
        self.assertTrue(dup["truncated"])
        self.assertEqual(dup["comparisons_spent"], 2000)
        res["duplicates"] = dup
        html = _render_in_node("renderAnalyze", res, "id", self)
        # The Readability card shows the real extreme numbers.
        m = re.search(
            r"Flesch Reading Ease ([\d.]+)/100 — ([^<]*)"
            r"<br>Flesch-Kincaid Grade Level ([\d.]+)"
            r"<br>Rata-rata ([\d.]+) kata/kalimat, ([\d.]+) suku "
            r"kata/kata \((\d+) kata, (\d+) kalimat, "
            r"(\d+) suku kata\)",
            html)
        self.assertIsNotNone(m, "Readability card not found in:\n"
                             + html)
        re_s, band_s, fkgl_s, wps_s, spw_s, w_s, s_s, syl_s = \
            m.groups()
        self.assertEqual(re_s, f"{py['flesch_reading_ease']:.1f}")
        self.assertEqual(band_s, py["band"])
        self.assertEqual(float(fkgl_s), 628.4)
        self.assertEqual(float(wps_s), 1500.0)
        self.assertEqual(float(spw_s), 5.0)
        self.assertEqual(int(w_s), 1500)
        self.assertEqual(int(s_s), 1)
        # The duplicates warning shows the spent count, not 0.
        self.assertIn("pemeriksaan berhenti setelah 2000 perbandingan",
                      html)
        self.assertNotIn("setelah 0 perbandingan", html)


if __name__ == "__main__":
    unittest.main()
