"""Tests for the local web UI (`serve`): the embedded page and the JSON API.

The server runs on an ephemeral localhost port in a thread; no
external network is used (DOI verification stays off in these tests).
"""

import http.client
import io
import json
import os
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

TEXT = (
    "Metode penelitian ini memakai purposive sampling dan thematic analysis. "
    "Hasilnya sejalan dengan temuan sebelumnya [cite:devlin2019]."
)


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


_BOUNDARY = "----testboundary42"


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
    body = _multipart(parts)
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Content-Type",
                   f"multipart/form-data; boundary={_BOUNDARY}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


class TestServe(unittest.TestCase):
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

    def test_home_serves_page_with_no_external_resources(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Academic Tools", body)
        self.assertIn(f"v{tools.__version__}", body)
        # The Pustaka tab renders the statistics card.
        self.assertIn('id="library-stats"', body)
        self.assertIn("renderStats", body)
        self.assertIn("/api/library/stats", body)
        # The page is self-contained: no CDN, webfonts, or analytics.
        self.assertNotIn("https://", body)
        self.assertNotIn("<link", body)
        self.assertNotIn("fonts.googleapis", body)
        self.assertNotIn("cdn", body)

    def test_prompts_list(self):
        status, body = _request(self.base, "GET", "/api/prompts")
        self.assertEqual(status, 200)
        prompts = json.loads(body)["prompts"]
        self.assertEqual(len(prompts), 18)
        self.assertTrue(all("id" in p and "fields" in p for p in prompts))

    def test_analyze(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": TEXT, "refs": "sample", "verify": False})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["quality_score"], 100)
        self.assertEqual(res["style"]["style_score"], 25)
        self.assertEqual(res["citations"]["missing"], [])

    def test_home_is_a_dashboard_shell(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        # Sidebar navigation with the five real tools.
        self.assertIn('class="shell"', body)
        self.assertIn('class="sidebar"', body)
        for tab in ("analyze", "jargon", "cite", "prompts", "library"):
            self.assertIn(f'data-tab="{tab}"', body)
        # The score gauge and the stat tiles are rendered by the page.
        self.assertIn("scoreGauge", body)
        self.assertIn("gauge-arc", body)
        self.assertIn("stats-grid", body)

    def test_analyze_returns_score_parts(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": TEXT, "refs": "sample", "verify": False})
        self.assertEqual(status, 200)
        res = json.loads(body)
        # TEXT scores 100: every component is a full 25.
        self.assertEqual(res["score_parts"], [25.0, 25.0, 25.0, 25.0])
        self.assertEqual(sum(res["score_parts"]), res["quality_score"])

    def test_analyze_score_parts_drop_for_missing_citation(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": "Penelitian ini memakai [cite:tidakada].",
            "refs": "sample", "verify": False})
        self.assertEqual(status, 200)
        res = json.loads(body)
        # Cited 1 marker, missing 1: the citations component is 0 —
        # every cited marker is missing, so no credit at all.
        self.assertEqual(res["score_parts"][1], 0.0)
        self.assertEqual(round(sum(res["score_parts"])),
                         res["quality_score"])

    def test_analyze_score_parts_half_for_one_missing_citation(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": ("Penelitian ini memakai [cite:devlin2019] dan "
                     "[cite:tidakada]."),
            "refs": "sample", "verify": False})
        self.assertEqual(status, 200)
        res = json.loads(body)
        # Cited 2 markers, 1 missing: half the citations component.
        self.assertEqual(res["score_parts"][1], 12.5)

    def test_analyze_without_refs(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": "Penelitian memakai purposive sampling.",
            "refs": "none", "verify": False})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertIsNone(res["citations"])
        self.assertEqual(res["quality_score"], 100)

    def test_analyze_save_to_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze", {
                    "text": TEXT, "refs": "sample", "verify": False,
                    "save": True})
            self.assertEqual(status, 200)
            res = json.loads(body)
            self.assertEqual(res["library_id"], 1)
            self.assertEqual(len(tools.list_analyses(db=db)), 1)

    def test_analyze_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze", {
                    "text": TEXT, "refs": "sample", "verify": False,
                    "save": True})
                self.assertEqual(status, 200)
                dup_text = ("Metode penelitian ini memakai purposive "
                            "sampling dan thematic analysis. Bab ini "
                            "membahas hasil.")
                status, body = _request(self.base, "POST", "/api/analyze", {
                    "text": dup_text, "refs": "none", "verify": False,
                    "duplicates": True})
            self.assertEqual(status, 200)
            res = json.loads(body)
            self.assertEqual(res["duplicates"]["count"], 1)
            self.assertEqual(
                res["duplicates"]["duplicates"][0]["similarity"], 1.0)
            self.assertEqual(
                res["duplicates"]["duplicates"][0]["source_id"], 1)

    def test_analyze_without_save_has_no_library_id(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": TEXT, "refs": "sample", "verify": False})
        self.assertEqual(status, 200)
        self.assertNotIn("library_id", json.loads(body))

    def test_library_stats_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze", {
                    "text": TEXT, "refs": "sample", "verify": False,
                    "save": True})
                self.assertEqual(status, 200)
                status, body = _request(self.base, "GET",
                                        "/api/library/stats")
                self.assertEqual(status, 200)
                stats = json.loads(body)["stats"]
                self.assertEqual(stats["runs"], 1)
                self.assertEqual(stats["average_score"], 100)
                self.assertEqual(stats["best"]["quality_score"], 100)
                self.assertEqual(len(stats["trend"]), 1)
                self.assertEqual(
                    [(c["key"], c["count"]) for c in stats["most_cited"]],
                    [("devlin2019", 1)])

    def test_library_stats_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "GET",
                                        "/api/library/stats")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["stats"]["runs"], 0)

    def test_parse_multipart_fields_and_files(self):
        body = _multipart([
            ("refs", None, b"sample"),
            ("files", "skripsi/bab1.txt", "Bab satu.".encode()),
            ("files", "bab2.md", "Bab dua.".encode()),
        ])
        parts = tools._parse_multipart(body, _BOUNDARY.encode())
        self.assertEqual(
            [(p["name"], p["filename"]) for p in parts],
            [("refs", None), ("files", "skripsi/bab1.txt"),
             ("files", "bab2.md")])
        self.assertEqual(parts[0]["data"], b"sample")
        self.assertEqual(parts[1]["data"], b"Bab satu.")

    def test_parse_multipart_malformed_raises(self):
        body = (b"--" + _BOUNDARY.encode() + b"\r\n"
                b'Content-Disposition: form-data; name="x"\r\n'
                b"--" + _BOUNDARY.encode() + b"--\r\n")
        with self.assertRaises(ValueError):
            tools._parse_multipart(body, _BOUNDARY.encode())

    def test_parse_multipart_boundary_mid_line_in_file(self):
        # A file whose content contains the boundary mid-line must
        # not split the parse: the delimiter only counts on a line
        # of its own.
        data = (b"baris pertama\n--" + _BOUNDARY.encode()
                + b" di tengah baris\nbaris ketiga")
        body = _multipart([("files", "bab1.txt", data)])
        parts = tools._parse_multipart(body, _BOUNDARY.encode())
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["data"], data)

    def test_parse_multipart_lf_only_body(self):
        # LF-only bodies (no CR at all) must parse the same way as
        # CRLF bodies — headers and data included.
        body = (b"--" + _BOUNDARY.encode() + b"\n"
                b'Content-Disposition: form-data; name="files"; '
                b'filename="bab1.txt"\n'
                b"Content-Type: text/plain\n"
                b"\n"
                b"isi LF saja\nbaris dua\n"
                b"--" + _BOUNDARY.encode() + b"--\n")
        parts = tools._parse_multipart(body, _BOUNDARY.encode())
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["filename"], "bab1.txt")
        self.assertEqual(parts[0]["data"], b"isi LF saja\nbaris dua")

    def test_read_body_rejects_invalid_content_length(self):
        # A garbage Content-Length is a generic 400, never a leaked
        # int() traceback; a missing one means an empty body.
        class _FakeHandler:
            def __init__(self, length, data=b""):
                self.headers = {} if length is None else {
                    "Content-Length": length}
                self.rfile = io.BytesIO(data)

        for bad in ("abc", "-5", "12x", "1.5", ""):
            with self.subTest(length=bad):
                with self.assertRaises(ValueError) as cm:
                    tools._read_body(_FakeHandler(bad),
                                     1_000_000, 2_000_000, "1 MB")
                self.assertEqual(str(cm.exception),
                                 "ukuran body tidak valid")
        self.assertEqual(
            tools._read_body(_FakeHandler(None), 1_000_000, 2_000_000,
                             "1 MB"), b"")
        self.assertEqual(
            tools._read_body(_FakeHandler("5", b"hello"),
                             1_000_000, 2_000_000, "1 MB"), b"hello")

    def test_post_with_query_string(self):
        # A query string on the POST path must not turn a known
        # endpoint into a 404.
        status, body = _request(self.base, "POST", "/api/analyze?debug=1",
                                {"text": TEXT, "refs": "sample",
                                 "verify": False})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["quality_score"], 100)

    def test_folder_upload_two_files_with_duplicates_and_save(self):
        bab1 = ("Penelitian ini melakukan pengukuran terhadap kepuasan "
                "pengguna [cite:devlin2019].")
        bab2 = ("Metode penelitian ini memakai purposive sampling dan "
                "thematic analysis. Hasilnya sejalan dengan temuan "
                "sebelumnya [cite:brooke1996]. Penelitian ini melakukan "
                "pengukuran terhadap kepuasan pengguna.")
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request_multipart(self.base,
                    "/api/analyze-folder", [
                        ("refs", None, b"sample"),
                        ("duplicates", None, b"1"),
                        ("save", None, b"1"),
                        ("files", "bab1.txt", bab1.encode()),
                        ("files", "bab2.md", bab2.encode()),
                    ])
                self.assertEqual(status, 200)
                res = json.loads(body)
                folder = res["folder"]
                self.assertEqual(folder["count"], 2)
                self.assertEqual(folder["folder"], "unggahan")
                self.assertEqual(res["skipped"], [])
                # bab2 repeats bab1's sentence; bab1 was saved first.
                self.assertEqual(folder["files"][1]["duplicates"], 1)
                self.assertIsNotNone(folder["files"][0]["library_id"])
                self.assertIsNotNone(folder["files"][1]["library_id"])
                self.assertEqual(folder["average"], round(
                    (folder["files"][0]["quality_score"]
                     + folder["files"][1]["quality_score"]) / 2, 1))

    def test_folder_upload_skips_subfolders_and_other_extensions(self):
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "bab1.txt",
                 b"Penelitian ini memakai skala likert."),
                ("files", "skripsi/bab2.txt",
                 b"Penelitian ini memakai skala likert."),
                ("files", "catatan.pdf", b"%PDF-1.4"),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 1)
        self.assertEqual(res["folder"]["folder"], "skripsi")
        self.assertEqual(
            [(s["file"], s["reason"]) for s in res["skipped"]],
            [("catatan.pdf", "bukan .txt atau .md"),
             ("skripsi/bab2.txt", "bukan file tingkat atas")])

    def test_folder_upload_bad_utf8_file_is_recorded_not_fatal(self):
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "bab1.txt", b"\xff\xfe rusak"),
                ("files", "bab2.txt",
                 b"Penelitian ini memakai skala likert."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 2)
        self.assertIsNotNone(res["folder"]["files"][0]["error"])
        self.assertEqual(res["folder"]["files"][1]["quality_score"], 100)

    def test_folder_upload_oversize_file_is_skipped(self):
        # A single file over 1 MB is skipped with a clear reason —
        # it must not fail the run or drag the average.
        big = b"a" * 1_000_001
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "besar.txt", big),
                ("files", "bab1.txt",
                 b"Penelitian ini memakai skala likert."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 1)
        self.assertEqual(res["folder"]["files"][0]["file"], "bab1.txt")
        self.assertEqual(res["folder"]["average"], 100.0)
        self.assertEqual(
            [(s["file"], s["reason"]) for s in res["skipped"]],
            [("besar.txt", "file lebih dari 1 MB")])

    def test_folder_upload_empty_file_is_error_not_average(self):
        # B3 via the web upload: an empty file is an error entry and
        # stays out of the average.
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "kosong.txt", b""),
                ("files", "bab1.txt",
                 b"Penelitian ini memakai skala likert."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 2)
        by_file = {e["file"]: e for e in res["folder"]["files"]}
        self.assertEqual(by_file["kosong.txt"]["error"], "teks kosong")
        self.assertIsNone(by_file["kosong.txt"]["quality_score"])
        self.assertEqual(res["folder"]["average"], 100.0)

    def test_home_page_score_gauge_guards_missing_score(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('typeof res.quality_score !== "number"', body)
        self.assertIn(
            "Math.max(0, Math.min(25, Number(v) || 0))", body)

    def test_make_server_rejects_non_loopback(self):
        for host in ("0.0.0.0", "192.168.1.1", "example.com"):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    tools.make_server(host, 0)
        server = tools.make_server("localhost", 0)
        server.server_close()

    def test_make_server_bounds_concurrent_handlers(self):
        server = tools.make_server("127.0.0.1", 0)
        try:
            got = [server._slots.acquire(blocking=False)
                   for _ in range(9)]
            self.assertEqual(got, [True] * 8 + [False])
        finally:
            for _ in range(8):
                server._slots.release()
            server.server_close()

    def test_folder_upload_no_files_is_400(self):
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [("refs", None, b"sample")])
        self.assertEqual(status, 400)
        self.assertIn("tidak ada file", json.loads(body)["error"])

    def test_folder_upload_wrong_content_type_is_400(self):
        status, body = _request(self.base, "POST", "/api/analyze-folder",
                                {"text": "x"})
        self.assertEqual(status, 400)
        self.assertIn("multipart", json.loads(body)["error"])

    def test_folder_upload_oversize_is_413(self):
        host, port = self.server.server_address[:2]
        err = io.StringIO()
        conn = http.client.HTTPConnection(host, port, timeout=30)
        big = b"x" * (tools._MAX_UPLOAD_BODY + 1)
        body = _multipart([("files", "besar.txt", big)])
        with redirect_stderr(err):
            conn.request("POST", "/api/analyze-folder", body=body,
                         headers={"Content-Type":
                                  "multipart/form-data; boundary="
                                  + _BOUNDARY,
                                  "Connection": "keep-alive"})
            resp = conn.getresponse()
            resp_body = resp.read().decode("utf-8")
            time.sleep(0.5)
        conn.close()
        self.assertEqual(resp.status, 413)
        self.assertIn("terlalu besar", json.loads(resp_body)["error"])
        self.assertNotIn("Traceback", err.getvalue())
        status, _ = _request(self.base, "GET", "/api/prompts")
        self.assertEqual(status, 200)

    def test_home_page_has_folder_upload(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('id="folder-dir"', body)
        self.assertIn("webkitdirectory", body)
        self.assertIn("/api/analyze-folder", body)
        self.assertIn("renderFolderResult", body)

    def test_home_page_has_save_checkbox(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('id="analyze-save"', body)
        self.assertIn("Simpan ke pustaka", body)

    def test_home_page_has_library_tab(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('data-tab="library"', body)
        self.assertIn('id="panel-library"', body)
        self.assertIn('id="library-search"', body)
        self.assertIn("/api/library/history", body)

    def test_library_history_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(
                    self.base, "GET", "/api/library/history")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"analyses": []})

    def test_library_history_analysis_and_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze", {
                    "text": TEXT, "refs": "sample", "verify": False,
                    "save": True})
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["library_id"], 1)
                status, body = _request(
                    self.base, "GET", "/api/library/history")
                self.assertEqual(status, 200)
                rows = json.loads(body)["analyses"]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["quality_score"], 100)
                status, body = _request(
                    self.base, "GET", "/api/library/analysis?id=1")
                self.assertEqual(status, 200)
                analysis = json.loads(body)["analysis"]
                self.assertEqual(analysis["text"], TEXT)
                self.assertEqual(analysis["references"], ["devlin2019"])
                status, body = _request(
                    self.base, "GET", "/api/library/refs")
                self.assertEqual(status, 200)
                refs = json.loads(body)["references"]
                self.assertEqual([r["key"] for r in refs], ["devlin2019"])
                status, body = _request(
                    self.base, "GET", "/api/library/refs?search=BERT")
                self.assertEqual(status, 200)
                self.assertEqual(len(json.loads(body)["references"]), 1)
                status, body = _request(
                    self.base, "GET", "/api/library/refs?search=tidakada")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), {"references": []})

    def test_library_analysis_missing_id_has_no_stray_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(
                    self.base, "GET", "/api/library/analysis?id=99")
            self.assertEqual(status, 404)
            self.assertEqual(json.loads(body),
                             {"error": "tidak ada analisis #99"})

    def test_oversize_body_is_413_without_logged_traceback(self):
        # Keep-alive on purpose: before the fix the unread body was
        # parsed as a new request line and logged a 414 traceback.
        host, port = self.server.server_address[:2]
        err = io.StringIO()
        conn = http.client.HTTPConnection(host, port, timeout=10)
        payload = json.dumps({"text": "x" * (tools._MAX_BODY + 1)})
        with redirect_stderr(err):
            conn.request("POST", "/api/analyze", body=payload,
                         headers={"Content-Type": "application/json",
                                  "Connection": "keep-alive"})
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            # The handler logs after the response, so give it a moment.
            time.sleep(0.5)
        conn.close()
        self.assertEqual(resp.status, 413)
        self.assertIn("terlalu besar", json.loads(body)["error"])
        self.assertNotIn("Traceback", err.getvalue())
        # The server must still answer a normal request afterwards.
        status, _ = _request(self.base, "GET", "/api/prompts")
        self.assertEqual(status, 200)

    def test_corrupt_db_via_api_is_clean_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "corrupt.db")
            with open(db, "wb") as f:
                f.write(b"bukan sqlite")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(
                    self.base, "GET", "/api/library/history")
                self.assertEqual(status, 400)
                self.assertIn("pustaka rusak", json.loads(body)["error"])
                status, body = _request(
                    self.base, "POST", "/api/analyze",
                    {"text": TEXT, "refs": "none", "save": True})
                self.assertEqual(status, 400)
                self.assertIn("pustaka rusak", json.loads(body)["error"])

    def test_missing_sample_refs_is_clean_400(self):
        with patch.object(tools, "DEFAULT_REFS", "/tidak/ada/refs.json"):
            status, body = _request(self.base, "POST", "/api/analyze", {
                "text": TEXT, "refs": "sample", "verify": False})
            self.assertEqual(status, 400)
            self.assertEqual(
                json.loads(body),
                {"error": "contoh bibliografi tidak ditemukan di folder ini"})

    def test_library_analysis_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(
                    self.base, "GET", "/api/library/analysis?id=99")
                self.assertEqual(status, 404)
                self.assertIn("tidak ada analisis #99", body)
                status, body = _request(
                    self.base, "GET", "/api/library/analysis")
                self.assertEqual(status, 400)
                status, body = _request(
                    self.base, "GET", "/api/library/analysis?id=abc")
                self.assertEqual(status, 400)
                status, body = _request(
                    self.base, "GET", "/api/library/history?limit=abc")
                self.assertEqual(status, 400)
                status, body = _request(self.base, "GET", "/api/nope")
                self.assertEqual(status, 404)

    def test_humanize_with_apply(self):
        status, body = _request(self.base, "POST", "/api/humanize", {
            "text": "Penelitian ini melakukan pengukuran terhadap "
                    "suhu ruangan. Selain itu, penelitian ini melakukan "
                    "analisis terhadap data yang diperoleh.",
            "lang": "id", "apply": True})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["count"], 4)
        self.assertIn("Penelitian ini mengukur suhu ruangan.",
                      res["fixed_text"])
        self.assertIn("Penelitian ini menganalisis data yang diperoleh.",
                      res["fixed_text"])

    def test_humanize_returns_typo_suggestions(self):
        status, body = _request(self.base, "POST", "/api/humanize", {
            "text": "Penelitian dilakukan disini dengan teliti.",
            "lang": "id"})
        self.assertEqual(status, 200)
        res = json.loads(body)
        typos = [s for s in res["suggestions"]
                 if s["pattern"] == "typo"]
        self.assertEqual(len(typos), 1)
        self.assertEqual(typos[0]["replacement"], "di sini")

    def test_humanize_without_apply_has_no_fixed_text(self):
        status, body = _request(self.base, "POST", "/api/humanize", {
            "text": "Penelitian ini melakukan pengukuran terhadap "
                    "suhu ruangan.",
            "lang": "id"})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertNotIn("fixed_text", res)

    def test_humanize_empty_text_is_400(self):
        status, body = _request(self.base, "POST", "/api/humanize",
                                {"text": "  "})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_analyze_empty_text_is_400(self):
        status, body = _request(self.base, "POST", "/api/analyze",
                                {"text": "  "})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_analyze_bad_refs_json_is_400(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": TEXT, "refs_json": "{bukan json"})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_jargon(self):
        status, body = _request(self.base, "POST", "/api/jargon", {
            "text": "Penelitian memakai purposive sampling."})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(
            [m["term"] for m in res["matches"]], ["purposive sampling"])

    def test_cite(self):
        status, body = _request(self.base, "POST", "/api/cite", {
            "text": "Seperti ditunjukkan sebelumnya [cite:devlin2019].",
            "refs": "sample", "style": "apa", "lang": "id"})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertIn("Devlin", res["output"])
        self.assertIn("Daftar Pustaka", res["output"])

    def test_cite_without_refs_is_400(self):
        status, body = _request(self.base, "POST", "/api/cite", {
            "text": "Lihat [cite:devlin2019].", "refs": "none"})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_fill_prompt(self):
        _, body = _request(self.base, "GET", "/api/prompts")
        prompt = json.loads(body)["prompts"][0]
        values = {f["key"]: f"nilai-{f['key']}" for f in prompt["fields"]}
        status, body = _request(self.base, "POST", "/api/prompts/fill", {
            "id": prompt["id"], "values": values, "lang": "id"})
        self.assertEqual(status, 200)
        text = json.loads(body)["text"]
        for value in values.values():
            self.assertIn(value, text)

    def test_fill_unknown_prompt_is_400(self):
        status, body = _request(self.base, "POST", "/api/prompts/fill", {
            "id": "tidak-ada", "values": {}})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_unknown_path_is_404(self):
        status, body = _request(self.base, "GET", "/tidak-ada")
        self.assertEqual(status, 404)
        self.assertIn("error", json.loads(body))

    def test_serve_version_flag(self):
        with self.assertRaises(SystemExit):
            tools.serve_main(["--version"])


if __name__ == "__main__":
    unittest.main()
