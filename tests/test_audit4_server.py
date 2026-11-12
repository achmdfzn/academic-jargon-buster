"""Tests for audit #4 (v1.27.1) server fixes: H-1, H-2, H-4, N-1..N-6, N-8.

Raw-socket tests (T-2, T-4, T-6), multipart / Content-Length tests
(T-5), and Node end-to-end renders for the XSS panels (T-7).

The server runs on an ephemeral localhost port in a thread; no
external network is used.
"""

import http.client
import http.server
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools

_BOUNDARY = "----audit4boundary"


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


def _multipart(parts):
    """Build a multipart/form-data body.

    parts: list of (name, filename_or_None, data_bytes). The
    disposition line is UTF-8 encoded, so a non-ASCII filename is
    sent as UTF-8 bytes, the way a browser sends it.
    """
    out = bytearray()
    for name, filename, data in parts:
        out += b"--" + _BOUNDARY.encode() + b"\r\n"
        disp = 'Content-Disposition: form-data; name="%s"' % name
        if filename is not None:
            disp += '; filename="%s"' % filename
        out += disp.encode("utf-8") + b"\r\n"
        if filename is not None:
            out += b"Content-Type: text/plain\r\n"
        out += b"\r\n" + data + b"\r\n"
    out += b"--" + _BOUNDARY.encode() + b"--\r\n"
    return bytes(out)


def _request_multipart(base, path, parts):
    body = _multipart(parts)
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Content-Type",
                   "multipart/form-data; boundary=" + _BOUNDARY)
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


class TestAudit4Desync(_ServerCase):
    """T-2: keep-alive reuse after a 400 (H-1 request-line, H-2 CL).

    The fix closes the connection after the error, so the unread
    bytes can never be re-parsed as a new request: the client gets
    exactly one error response and then EOF — never a stray second
    body delivered as the next response.
    """

    def test_malformed_request_line_sends_one_400_then_closes(self):
        # H-1: "BAD METHOD ..." has four words, so parse_request
        # fails before the header lines are read; before the fix
        # handle() re-parsed "Host: x" as a new HTTP/0.9 request
        # and sent a second 84-byte body that poisoned the next
        # response on the same connection.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b"BAD METHOD /api/detect HTTP/1.1\r\n"
                      b"Host: x\r\nContent-Length: 0\r\n\r\n")
            data, eof = _recv_all(s)
            self.assertTrue(eof, "connection must close after the 400")
            self.assertTrue(data.startswith(b"HTTP/1.1 400"))
            self.assertEqual(data.count(b"<h1>400</h1>"), 1,
                             "exactly one error body, not two")
            # Reuse: nothing is delivered as the GET's response.
            try:
                s.sendall(b"GET /api/prompts HTTP/1.1\r\n"
                          b"Host: x\r\n\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass  # already closed is fine too
            reuse, _ = _recv_all(s)
            self.assertEqual(reuse, b"")
        finally:
            s.close()

    def test_invalid_content_length_sends_400_then_closes(self):
        # H-2: the declared length is unusable, so the body cannot
        # be drained; the unread {"text":"hi"} must not be glued
        # to the next request line.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: x\r\n'
                      b'Content-Type: application/json\r\n'
                      b'Content-Length: abc\r\n\r\n{"text":"hi"}')
            data, eof = _recv_all(s)
            self.assertTrue(eof, "connection must close after the 400")
            self.assertTrue(data.startswith(b"HTTP/1.1 400"))
            self.assertIn(b'"ukuran body tidak valid"', data)
            try:
                s.sendall(b"GET /api/prompts HTTP/1.1\r\n"
                          b"Host: x\r\n\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass
            reuse, _ = _recv_all(s)
            self.assertEqual(reuse, b"")
        finally:
            s.close()

    def test_server_still_healthy_after_bad_requests(self):
        # A fresh connection must still get proper JSON — the bad
        # requests above wedged nothing.
        status, body = _request(self.base, "GET", "/api/prompts")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["prompts"]), 18)


class TestAudit4Timeout(unittest.TestCase):
    """T-4 / H-4: a stalled client is not a server crash, and the
    timeout must not write a traceback to stderr."""

    def test_handle_error_swallows_timeout(self):
        # The server's handle_error already swallows aborts; a
        # socket timeout is the same class of non-error.
        server = tools.make_server("127.0.0.1", 0)
        try:
            for exc_type in (TimeoutError, socket.timeout):
                err = io.StringIO()
                with patch("sys.exc_info",
                           return_value=(exc_type, exc_type(), None)):
                    with redirect_stderr(err):
                        server.handle_error(None, ("127.0.0.1", 1))
                self.assertEqual(err.getvalue(), "", exc_type)
        finally:
            server.server_close()

    def test_stalled_client_gets_no_500_and_stderr_stays_silent(self):
        # End to end with a short socket timeout (the real one is
        # 30 s): stall once mid-body (timeout inside do_POST) and
        # once mid-request-line (timeout inside parse_request).
        # Neither stall may produce a 500, and stderr must stay
        # empty — the timeout is by design, not an error.
        def fast_setup(self):
            http.server.BaseHTTPRequestHandler.setup(self)
            self.connection.settimeout(0.6)

        with patch.object(tools._UIHandler, "setup", fast_setup):
            server = tools.make_server("127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever,
                                      daemon=True)
            thread.start()
            host, port = server.server_address[:2]
            try:
                err = io.StringIO()
                with redirect_stderr(err):
                    s = socket.create_connection((host, port), timeout=5)
                    s.sendall(b"POST /api/analyze HTTP/1.1\r\n"
                              b"Host: x\r\n"
                              b"Content-Type: application/json\r\n"
                              b"Content-Length: 100000\r\n\r\n"
                              b'{"text": "abc')
                    body_got, body_eof = _recv_all(s, timeout=5)
                    s.close()
                    s2 = socket.create_connection((host, port), timeout=5)
                    s2.sendall(b"POST /api/analyze HTTP/1")
                    line_got, line_eof = _recv_all(s2, timeout=5)
                    s2.close()
                    time.sleep(0.3)  # let the handler finish logging
                self.assertEqual(body_got, b"",
                                 "stalled body must not get a 500")
                self.assertTrue(body_eof)
                self.assertEqual(line_got, b"",
                                 "stalled request line must get nothing")
                self.assertTrue(line_eof)
                self.assertEqual(err.getvalue(), "")
            finally:
                server.shutdown()
                server.server_close()


class TestAudit4ContentLengthAndMultipart(_ServerCase):
    """T-5: duplicate Content-Length (N-3), filename backslash
    (N-1), filename unicode (N-2)."""

    def test_duplicate_content_length_differing_values_is_400(self):
        # N-3 (RFC 7230 §3.3.2): two different values must be a
        # 400, never "trust the first and leave the rest unread".
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: x\r\n'
                      b'Content-Type: application/json\r\n'
                      b'Content-Length: 13\r\nContent-Length: 99\r\n\r\n'
                      b'{"text":"hi"}')
            data, eof = _recv_all(s)
            self.assertTrue(eof, "connection must close after the 400")
            self.assertTrue(data.startswith(b"HTTP/1.1 400"))
            self.assertIn(b'"ukuran body tidak valid"', data)
        finally:
            s.close()

    def test_duplicate_content_length_identical_values_is_accepted(self):
        # N-3: identical duplicates are harmless — the request
        # goes through normally and keep-alive stays usable.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: x\r\n'
                      b'Content-Type: application/json\r\n'
                      b'Content-Length: 13\r\nContent-Length: 13\r\n\r\n'
                      b'{"text":"hi"}')
            status, _, body = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 200 OK")
            self.assertEqual(json.loads(body)["quality_score"], 100)
        finally:
            s.close()

    def test_multipart_param_unescapes_only_quote_and_backslash(self):
        # N-1: the docstring promises only \" and \\ are
        # unescaped — a backslash before any other character is
        # literal, so "a\nb.txt" keeps its backslash.
        param = tools._multipart_param
        self.assertEqual(
            param('form-data; filename="a\\nb.txt"', "filename"),
            "a\\nb.txt")
        self.assertEqual(
            param('form-data; filename="a\\qb.txt"', "filename"),
            "a\\qb.txt")
        self.assertEqual(
            param('form-data; filename="a\\"b.txt"', "filename"),
            'a"b.txt')
        self.assertEqual(
            param('form-data; filename="a\\\\b.txt"', "filename"),
            "a\\b.txt")
        self.assertEqual(
            param('form-data; filename="a\\tb.txt"', "filename"),
            "a\\tb.txt")
        # The quoted-semicolon case from the earlier fix still works.
        self.assertEqual(
            param('multipart/form-data; boundary="a;b"', "boundary"),
            "a;b")

    def test_parse_multipart_keeps_backslash_in_filename(self):
        # N-1 at the parser level: "a\b.txt" must not become "ab.txt".
        body = (b'--B\r\nContent-Disposition: form-data; name="files"; '
                b'filename="a\\b.txt"\r\nContent-Type: text/plain\r\n\r\n'
                b"Penelitian memakai metode survei.\r\n--B--\r\n")
        parts = tools._parse_multipart(body, b"B")
        self.assertEqual(parts[0]["filename"], "a\\b.txt")

    def test_unicode_filename_not_mojibake(self):
        # N-2: a UTF-8 filename must come back as UTF-8, not as
        # latin-1 mojibake ("ünïcode-✓.txt", not "Ã¼nÃ¯code-âœ".txt).
        status, body = _request_multipart(
            self.base, "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "ünïcode-✓.txt",
                 "Penelitian memakai metode survei dan analisis data."
                 .encode("utf-8")),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 1)
        self.assertEqual(res["folder"]["files"][0]["file"],
                         "ünïcode-✓.txt")

    def test_latin1_filename_falls_back_to_latin1(self):
        # N-2: a filename that is not valid UTF-8 (a lone latin-1
        # byte) still decodes instead of raising or mojibake-ing.
        body = (b'--B\r\nContent-Disposition: form-data; name="files"; '
                b'filename="caf\xe9.txt"\r\n'
                b'Content-Type: text/plain\r\n\r\nx\r\n--B--\r\n')
        parts = tools._parse_multipart(body, b"B")
        self.assertEqual(parts[0]["filename"], "café.txt")

    def test_backslash_filename_upload_is_skipped_not_mangled(self):
        # N-1 end to end: the folder handler treats "\" as a path
        # separator, so "a\b.txt" is a subfolder file — but the
        # name must arrive intact ("b.txt" skipped), never mangled
        # to "ab.txt".
        status, body = _request_multipart(
            self.base, "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "a\\b.txt",
                 b"Penelitian memakai metode survei."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 0)
        self.assertEqual(
            [(s["file"], s["reason"]) for s in res["skipped"]],
            [("b.txt", "bukan file tingkat atas")])


class TestAudit4Http09(_ServerCase):
    """T-6: HTTP/0.9 responses (N-4) and a malformed header line."""

    def test_http09_request_gets_bare_body_then_close(self):
        # N-4: an HTTP/0.9-style request line must get exactly one
        # 400 and the connection must close right after, never be
        # left open for a header-less exchange. What the 400 looks
        # like depends on the stdlib: Python <=3.12 sends only the
        # bare body for HTTP/0.9, 3.13 sends a full response
        # (status line + headers + body). Either is fine as long
        # as it is exactly one 400, carries the security headers
        # when headers are present, and the connection closes.
        body = (b"<!DOCTYPE HTML><html><head><title>400</title></head>"
                b"<body><h1>400</h1></body></html>")
        for raw in (b"EVIL\r\nInjected-Header: pwned\r\n\r\n",
                    b"GET\r\n"):
            s = socket.create_connection((self.host, self.port),
                                         timeout=5)
            try:
                s.sendall(raw)
                data, eof = _recv_all(s)
                self.assertTrue(eof, raw)
                self.assertIn(body, data, raw)
                self.assertEqual(data.count(body), 1, raw)
                if data.startswith(b"HTTP/"):
                    self.assertIn(b"400", data.split(b"\r\n", 1)[0],
                                  raw)
                    for hdr in (b"Content-Security-Policy:",
                                b"X-Content-Type-Options: nosniff",
                                b"X-Frame-Options: DENY"):
                        self.assertIn(hdr, data, raw)
            finally:
                s.close()

    def test_malformed_header_line_without_colon_is_ignored(self):
        # T-6 observation: a header line with no colon is silently
        # ignored by the stdlib parser — the request still gets a
        # normal 200. Pinned so a future change is deliberate.
        s = socket.create_connection((self.host, self.port), timeout=5)
        try:
            s.sendall(b"GET /api/prompts HTTP/1.1\r\n"
                      b"BadHeaderLine\r\nHost: x\r\n\r\n")
            status, _, body = _read_response(s)
            self.assertEqual(status, "HTTP/1.1 200 OK")
            self.assertEqual(len(json.loads(body)["prompts"]), 18)
        finally:
            s.close()


class TestAudit4ServerMisc(_ServerCase):
    """N-5 (per-instance semaphore), N-6 (flushed banner), N-8
    (folder upload cosmetics)."""

    def test_semaphore_is_per_instance(self):
        # N-5: two servers in one process must each have their
        # own 8 slots — before the fix they shared one class-level
        # semaphore, so the second server's cap was already eaten.
        a = tools.make_server("127.0.0.1", 0)
        b = tools.make_server("127.0.0.1", 0)
        try:
            self.assertIsNot(a._slots, b._slots)
            got_a = [a._slots.acquire(blocking=False) for _ in range(9)]
            got_b = [b._slots.acquire(blocking=False) for _ in range(9)]
            try:
                self.assertEqual(got_a, [True] * 8 + [False])
                self.assertEqual(got_b, [True] * 8 + [False])
            finally:
                for _ in range(sum(got_a)):
                    a._slots.release()
                for _ in range(sum(got_b)):
                    b._slots.release()
        finally:
            a.server_close()
            b.server_close()

    def test_serve_banner_print_uses_flush(self):
        # N-6: as a service stdout is a pipe (block-buffered), so
        # the startup banner must be printed with flush=True or
        # it never shows in the service log.
        class _FakeServer:
            server_address = ("127.0.0.1", 8000)

            def serve_forever(self):
                raise KeyboardInterrupt

        with patch.object(tools, "make_server",
                          return_value=_FakeServer()):
            with patch("builtins.print") as mock_print:
                code = tools.serve_main(["--port", "8000"])
        self.assertEqual(code, 0)
        self.assertEqual(len(mock_print.call_args_list), 3)
        for call in mock_print.call_args_list:
            self.assertTrue(call.kwargs.get("flush"), call)

    def test_folder_upload_traversal_name_falls_back(self):
        # N-8: "../../etc/passwd.txt" is skipped as a non-top-level
        # file (no traversal — nothing is ever written to disk),
        # but its first component must not name the folder "..".
        status, body = _request_multipart(
            self.base, "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "../../etc/passwd.txt",
                 b"Penelitian memakai metode survei."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["folder"], "unggahan")
        self.assertEqual(res["folder"]["count"], 0)
        self.assertEqual(
            [(s["file"], s["reason"]) for s in res["skipped"]],
            [("passwd.txt", "bukan file tingkat atas")])

    def test_folder_upload_only_empty_filenames_is_400(self):
        # N-8: an upload of only empty filenames (an unchosen file
        # input) is a 400, not a 200 with count 0.
        status, body = _request_multipart(
            self.base, "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "", b"Penelitian memakai metode survei."),
            ])
        self.assertEqual(status, 400)
        self.assertIn("tidak ada file yang diunggah", body)

    def test_folder_upload_mixed_empty_filename_is_ignored(self):
        # N-8: an empty-filename part next to a real file is just
        # ignored — the real file is still analyzed.
        status, body = _request_multipart(
            self.base, "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "", b"x"),
                ("files", "bab1.txt",
                 b"Penelitian memakai metode survei."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 1)
        self.assertEqual(res["folder"]["files"][0]["file"], "bab1.txt")
        self.assertEqual(res["skipped"], [])


if __name__ == "__main__":
    unittest.main()


# ----------------------------------------------------------------------
# T-7: Node end-to-end renders for the XSS panels.
#
# The page JS is an IIFE, so the render functions are not exported.
# The harness stubs the DOM (getElementById / querySelectorAll /
# createElement / fetch) just enough for the IIFE to load, then
# injects a driver *inside* the IIFE — right before its closing
# "})();" (which occurs exactly once) — that calls the real render
# functions and the real click handlers with hostile fixtures and
# prints the resulting HTML as JSON for the Python assertions.
# ----------------------------------------------------------------------

_NODE_STUB = r"""
var __els = {};
function __makeEl(id) {
  return {
    id: id, value: "", textContent: "", innerHTML: "",
    disabled: false, checked: false, files: [],
    dataset: {}, style: {}, type: "",
    classList: { add: function () {}, remove: function () {},
                 toggle: function () {} },
    _listeners: {},
    addEventListener: function (t, fn) { this._listeners[t] = fn; },
    removeEventListener: function () {},
    setAttribute: function () {}, getAttribute: function () { return null; },
    appendChild: function (c) { return c; },
    removeChild: function (c) { return c; },
    click: function () {}, select: function () {},
    closest: function () { return null; },
    querySelectorAll: function () { return []; },
    querySelector: function () { return null; }
  };
}
var document = {
  getElementById: function (id) {
    if (!__els[id]) __els[id] = __makeEl(id);
    return __els[id];
  },
  querySelectorAll: function () { return []; },
  querySelector: function () { return null; },
  createElement: function (tag) { return __makeEl(tag); },
  body: __makeEl("body"),
  execCommand: function () { return false; }
};
var __fetchResponses = {};
var fetch = function (url) {
  var body = Object.prototype.hasOwnProperty.call(__fetchResponses, url)
    ? __fetchResponses[url] : { prompts: [] };
  return Promise.resolve({ ok: true, status: 200,
    json: function () { return Promise.resolve(body); } });
};
var navigator = { clipboard: undefined };
"""

_NODE_DRIVER = r"""
;(async function __audit4Driver() {
  var out = {};
  var X1 = "<script>alert(1)</script>";
  var X2 = "<img src=x onerror=alert(2)>";
  var X3 = '"><svg onload=alert(3)>';
  var X4 = "javascript:alert(4)";
  var X5 = "'\"<>&";
  function grab(id) { return document.getElementById(id).innerHTML; }

  // Analisis panel (renderAnalyze): gauge, readability band/note,
  // jargon matches, missing citations, style examples, duplicates,
  // recommendations, humanize suggestions (original/context/fixed).
  out.analyze = renderAnalyze({
    quality_score: 90, score_parts: [25, 25, 25, 15],
    readability: { flesch_reading_ease: 12.7, flesch_kincaid_grade: 14.1,
      band: X1, avg_words_per_sentence: 8.8, avg_syllables_per_word: 3.1,
      note: X2 },
    library_id: 3,
    jargon: [{ term: X1, translation: X2, field: X3, source: X4 }],
    citations: { cited: ["devlin2019"], missing: [X1], unused: [] },
    doi_verification: {},
    style: { style_score: 20, flagged: ["yang_mana"],
      signals: { yang_mana: { count: 2, examples: [X1, X2] } } },
    duplicates: { duplicates: [{ sentence: X2, similarity: 0.9,
      match: X3, source_id: 1, source_title: X4 }] },
    recommendations: [X3],
    suggestions: { count: 1, suggestions: [{ pattern: "typo",
      original: X1, replacement: X2, context: X3, fixed: X4 }] }
  }, "id");

  // Deteksi AI panel (renderDetect): capped reason, top sentences, note.
  out.detect = renderDetect({
    ai_score: 80.2, verdict: X1, verdict_capped: true,
    verdict_capped_reason: X2,
    signals: { burstiness: { applicable: true, score: 90 },
      template_phrases: { applicable: true, score: 80 },
      lexical_diversity: { applicable: false, score: 0 },
      starter_repetition: { applicable: true, score: 70 } },
    sentences: [{ sentence: X3, score: 95 }],
    note: X4
  }, "id");

  // Pustaka panels.
  renderHistory([{ id: 1, title: X1, created_at: "2026-11-13 01:00:00",
    quality_score: 90, style_score: 20 }]);
  out.history = grab("library-history");
  renderDetail({ id: 2, title: X2, created_at: "2026-11-13 01:00:00",
    quality_score: 80, style_score: 20, jargon_count: 1,
    citations_missing: 1, doi_ok: 0, doi_total: 0,
    references: [X3], text: X4 });
  out.detail = grab("library-detail");
  renderRefs([{ key: X1, year: 2020, title: X2, authors: X3, doi: X4 }],
    X5);
  out.refs = grab("library-refs");
  renderRefs([], X5);
  out.refs_empty = grab("library-refs");
  renderStats({ runs: 2, average_score: 85,
    best: { quality_score: 90, title: X1 },
    trend: [{ title: X2, quality_score: 80 }],
    most_cited: [{ key: X3, title: X4, count: 3 }] });
  out.stats = grab("library-stats");

  // Folder panel.
  out.folder = renderFolderResult({ folder: { folder: X1, count: 1,
    average: 90, files: [{ file: X2, quality_score: 90, jargon_count: 1,
      citations_cited: 1, citations_missing: [], doi_ok: 0, doi_total: 0,
      style_score: 20, duplicates: null, error: null }] },
    skipped: [{ file: X3, reason: X4 }] }, "id");

  // Jargon panel, driven through the real click handler.
  document.getElementById("jargon-text").value = "purposive sampling";
  __fetchResponses["/api/jargon"] = { matches: [
    { term: X1, translation: X2, field: X3, source: X4 }] };
  await document.getElementById("jargon-btn")._listeners.click();
  out.jargon = grab("jargon-result");

  // Citation panel, driven through the real click handler.
  document.getElementById("cite-text").value = "teks [cite:devlin2019]";
  __fetchResponses["/api/cite"] = { output: X1 + "\n" + X2 };
  await document.getElementById("cite-btn")._listeners.click();
  out.cite = grab("cite-result");

  // Prompts panel, driven through the real click handler.
  promptsCache = [{ id: "p1", name: "P1", fields: [] }];
  document.getElementById("prompt-select").value = "p1";
  __fetchResponses["/api/prompts/fill"] = { text: X1 + " " + X3 };
  await document.getElementById("prompt-btn")._listeners.click();
  out.prompts = grab("prompt-result");

  console.log("__RESULTS__" + JSON.stringify(out));
})().catch(function (e) {
  console.log("__DRIVER_ERROR__" + (e && e.stack ? e.stack : e));
});
"""

# Hostile payloads and their escaped forms (the page's esc()).
_X1 = "<script>alert(1)</script>"
_X2 = "<img src=x onerror=alert(2)>"
_X3 = '"><svg onload=alert(3)>'
_X4 = "javascript:alert(4)"
_X5 = "'\"<>&"
_ESC = {
    _X1: "&lt;script&gt;alert(1)&lt;/script&gt;",
    _X2: "&lt;img src=x onerror=alert(2)&gt;",
    _X3: "&quot;&gt;&lt;svg onload=alert(3)&gt;",
    _X5: "&#39;&quot;&lt;&gt;&amp;",
    # _X4 has no escapable character; it may only ever appear as
    # plain text, never inside a live href.
}


def _node_script():
    """Page JS + DOM stub + driver, as one Node script."""
    html = tools.WEB_UI_HTML
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]
    assembled = _NODE_STUB + "\n" + js
    marker = "})();"
    idx = assembled.rfind(marker)
    assert idx != -1, "page IIFE closer not found"
    return assembled[:idx] + _NODE_DRIVER + "\n" + assembled[idx:]


def _run_node(script, check_only=False):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        cmd = ["node", "--check", path] if check_only else ["node", path]
        # Bytes mode + explicit UTF-8 decode: text=True decodes
        # with the locale encoding, which is cp1252 on Windows
        # and corrupts the non-ASCII the page renders (the em
        # dash in "0.0/100 — Sangat sulit" becomes mojibake and
        # the render assertions stop matching). Node always
        # writes UTF-8 here, so decode it as UTF-8 everywhere.
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        proc.stdout = proc.stdout.decode("utf-8")
        proc.stderr = proc.stderr.decode("utf-8")
        return proc
    finally:
        os.unlink(path)


@unittest.skipUnless(shutil.which("node"), "node tidak tersedia")
class TestAudit4NodeRenders(unittest.TestCase):
    """T-7: render the page JS in Node end to end and check that
    hostile payloads come out escaped in every panel."""

    def test_page_js_passes_node_check(self):
        proc = _run_node(_node_script(), check_only=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_node_renders_escape_hostile_payloads(self):
        proc = _run_node(_node_script())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        results = None
        for line in proc.stdout.splitlines():
            if line.startswith("__DRIVER_ERROR__"):
                self.fail("driver Node gagal: "
                          + line[len("__DRIVER_ERROR__"):])
            if line.startswith("__RESULTS__"):
                results = json.loads(line[len("__RESULTS__"):])
        self.assertIsNotNone(results, "driver tidak mencetak hasil:\n"
                              + proc.stdout + proc.stderr)

        # Which hostile values each panel must carry, escaped.
        expected = {
            "analyze": [_X1, _X2, _X3, _X4],
            "detect": [_X2, _X3, _X4],
            "history": [_X1],
            "detail": [_X2, _X3, _X4],
            "refs": [_X1, _X2, _X3, _X4],
            "refs_empty": [_X5],
            "stats": [_X1, _X2, _X3, _X4],
            "folder": [_X1, _X2, _X3, _X4],
            "jargon": [_X1, _X2, _X3, _X4],
            "cite": [_X1, _X2],
            "prompts": [_X1, _X3],
        }
        self.assertEqual(set(results), set(expected))
        for panel, payloads in expected.items():
            html = results[panel]
            with self.subTest(panel=panel):
                # No live markup from any payload, in any panel.
                self.assertNotIn("<script>", html)
                self.assertNotIn("<img", html)
                self.assertNotIn('href="javascript:', html)
                # The gauge SVG is the page's own; it is the only
                # "<svg" a panel may contain.
                if panel in ("analyze", "detect"):
                    self.assertEqual(html.count("<svg"), 1)
                    self.assertNotIn("<svg onload", html)
                else:
                    self.assertNotIn("<svg", html)
                for payload in payloads:
                    if payload == _X4:
                        # No escapable character: assert it is
                        # present as plain text only (checked above
                        # for a live href), not raw markup.
                        self.assertIn(_X4, html)
                        continue
                    self.assertNotIn(payload, html,
                                     "payload mentah lolos di " + panel)
                    self.assertIn(_ESC[payload], html,
                                  "bentuk escape hilang di " + panel)
