"""Tests for the local web UI (`serve`): the embedded page and the JSON API.

The server runs on an ephemeral localhost port in a thread; no
external network is used (DOI verification stays off in these tests).
"""

import http.client
import io
import json
import os
import socket
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

    def test_detect_ai_text(self):
        text = ("Penelitian ini bertujuan untuk menganalisis pengaruh media sosial "
                "terhadap prestasi belajar siswa. Penelitian ini juga mengkaji peran "
                "motivasi belajar dalam proses pembelajaran di sekolah. Penelitian ini "
                "mengukur durasi penggunaan media sosial harian melalui kuesioner "
                "terstruktur. Penelitian ini menemukan bahwa penggunaan berlebihan "
                "menurunkan prestasi belajar siswa secara signifikan. Selain itu, "
                "motivasi belajar berperan sebagai faktor penting dalam keberhasilan "
                "akademik siswa. Perlu dicatat bahwa media sosial memiliki dampak "
                "yang signifikan terhadap perilaku belajar siswa. Dalam hal ini, guru "
                "dan orang tua perlu mengawasi penggunaan media sosial anak.")
        status, body = _request(self.base, "POST", "/api/detect",
                                {"text": text})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertGreaterEqual(res["ai_score"], 70)
        self.assertEqual(res["verdict"], "Kemungkinan besar AI")
        self.assertEqual(set(res["signals"]),
                         {"burstiness", "template_phrases",
                          "lexical_diversity", "starter_repetition"})
        self.assertIn("heuristik", res["note"])
        scores = [s["score"] for s in res["sentences"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(any(s >= 70 for s in scores))

    def test_detect_human_text(self):
        text = ("Saya sampai di desa itu jam enam pagi, dan kabutnya masih tebal sekali. "
                "Pak RT menyambut kami dengan kopi tubruk yang manisnya kebangetan, "
                "terus ketawa waktu saya tanya soal sinyal. Saya catat itu, karena "
                "kalimat seperti itulah yang menjelaskan kenapa warga lebih percaya "
                "radio desa daripada grup WhatsApp. Tiga hari saya tinggal di sana, "
                "dan baru di hari ketiga saya paham: teknologi yang bagus itu yang "
                "tidak memaksa orang berubah.")
        status, body = _request(self.base, "POST", "/api/detect",
                                {"text": text})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertLess(res["ai_score"], 40)
        self.assertEqual(res["verdict"], "Kemungkinan besar manusia")

    def test_detect_short_text_is_too_short(self):
        status, body = _request(self.base, "POST", "/api/detect",
                                {"text": "Teks pendek."})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertIsNone(res["ai_score"])
        self.assertEqual(res["verdict"], "Teks terlalu pendek")
        self.assertIn("heuristik", res["note"])

    def test_detect_empty_text_is_400(self):
        status, body = _request(self.base, "POST", "/api/detect",
                                {"text": "   "})
        self.assertEqual(status, 400)
        self.assertIn("teks kosong", body)

    def test_detect_bad_lang_is_400(self):
        status, body = _request(self.base, "POST", "/api/detect",
                                {"text": "kata " * 40, "lang": "xx"})
        self.assertEqual(status, 400)

    def test_home_is_a_dashboard_shell(self):
        status, body = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)
        # Sidebar navigation with the six real tools.
        self.assertIn('class="shell"', body)
        self.assertIn('class="sidebar"', body)
        for tab in ("analyze", "jargon", "cite", "prompts", "library",
                    "detect"):
            self.assertIn(f'data-tab="{tab}"', body)
        self.assertIn('id="panel-detect"', body)
        self.assertIn("renderDetect", body)
        self.assertIn("/api/detect", body)
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
             ("bab2.txt", "bukan file tingkat atas")])

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
                # v1.25.2: save_analysis upserts every reference in
                # the bibliography, not only the cited one.
                self.assertEqual([r["key"] for r in refs],
                                 ["brooke1996", "brown2020", "devlin2019",
                                  "ferraiolo1992", "goodfellow2016",
                                  "likert1932", "vaswani2017"])
                status, body = _request(
                    self.base, "GET", "/api/library/refs?search=BERT")
                self.assertEqual(status, 200)
                # "BERT" matches devlin2019's title — and brown2020's
                # author list ("Herbert-Voss"): substring search.
                self.assertEqual(
                    [r["key"] for r in
                     json.loads(body)["references"]],
                    ["brown2020", "devlin2019"])
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


def _request_headers(base, path):
    """GET returning (status, headers, body) for header assertions."""
    req = urllib.request.Request(base + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.headers, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


class TestServeNiceToHave1252(unittest.TestCase):
    """v1.25.2: security headers, multipart params, no text echo."""

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

    def test_security_headers_on_page_and_404(self):
        status, headers, _ = _request_headers(self.base, "/")
        self.assertEqual(status, 200)
        self.assertEqual(
            headers.get("Content-Security-Policy"),
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("Server"), "academic-tools")
        status, headers, _ = _request_headers(self.base, "/nope")
        self.assertEqual(status, 404)
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("Server"), "academic-tools")

    def test_multipart_param_handles_semicolon_and_quote(self):
        body = (b"--B\r\nContent-Disposition: form-data; name=\"files\"; "
                b"filename=\"a;b.txt\"\r\n\r\nhello\r\n--B--\r\n")
        parts = tools._parse_multipart(body, b"B")
        self.assertEqual(parts[0]["filename"], "a;b.txt")
        body = (b"--B\r\nContent-Disposition: form-data; name=\"files\"; "
                b"filename=\"a\\\"b.txt\"\r\n\r\nhello\r\n--B--\r\n")
        parts = tools._parse_multipart(body, b"B")
        self.assertEqual(parts[0]["filename"], 'a"b.txt')

    def test_folder_upload_response_omits_file_text(self):
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "bab1.txt",
                 b"Penelitian ini memakai skala likert."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["count"], 1)
        self.assertNotIn("text", res["folder"]["files"][0])

    def test_folder_upload_leading_slash_name_falls_back(self):
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "/bab1.txt",
                 b"Penelitian ini memakai skala likert."),
                ("files", "bab2.txt",
                 b"Penelitian ini memakai skala likert."),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["folder"], "unggahan")
        self.assertEqual(res["folder"]["count"], 1)
        self.assertEqual(
            [(s["file"], s["reason"]) for s in res["skipped"]],
            [("bab1.txt", "bukan file tingkat atas")])

    def test_js_uses_num_helper_and_escapes_labels(self):
        html = tools.WEB_UI_HTML
        self.assertIn("function num(v, max)", html)
        self.assertIn("esc(label)", html)
        self.assertIn("esc(labels[s.pattern] || s.pattern)", html)
        self.assertIn("num(res.quality_score, 100)", html)
        self.assertIn("num(e.quality_score, 100)", html)


class TestServeHardening1261(unittest.TestCase):
    """v1.26.1: IPv6 loopback, quoted boundaries, error headers,
    quiet client aborts, socket timeout, thread cap end-to-end."""

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

    def _headers(self, conn, method, path, body=None, headers=None):
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        data = resp.read()
        return resp, data

    def test_make_server_ipv6_loopback(self):
        # H-1: ::1 binds on a machine with IPv6 — or fails with a
        # clean ValueError on one without. A socket.gaierror must
        # never escape.
        try:
            server = tools.make_server("::1", 0)
        except ValueError as e:
            self.assertIn("IPv6", str(e))
        else:
            try:
                self.assertEqual(server.address_family, socket.AF_INET6)
            finally:
                server.server_close()

    def test_ipv6_bind_failure_is_clean_value_error(self):
        # H-1: the OSError path, forced with a mock so the test does
        # not depend on the machine having no IPv6.
        with patch.object(tools, "_BoundedThreadingHTTPServer6",
                          side_effect=OSError("no ipv6")):
            with self.assertRaises(ValueError) as cm:
                tools.make_server("::1", 0)
            self.assertEqual(str(cm.exception),
                             "IPv6 tidak didukung di mesin ini")

    def test_serve_ipv6_without_ipv6_exits_1_cleanly(self):
        # H-1: the CLI path — main() turns the ValueError into a
        # plain stderr message and exit 1, never a traceback.
        err = io.StringIO()
        with patch.object(tools, "_BoundedThreadingHTTPServer6",
                          side_effect=OSError("no ipv6")):
            with redirect_stderr(err):
                code = tools.main(["serve", "--host", "::1",
                                   "--port", "0"])
        self.assertEqual(code, 1)
        self.assertIn("IPv6 tidak didukung", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_quoted_boundary_with_semicolon(self):
        # N-1: a quoted boundary containing ';' must survive intact.
        host, port = self.server.server_address[:2]
        conn = http.client.HTTPConnection(host, port, timeout=10)
        body = (b'--a;b\r\nContent-Disposition: form-data; name="files"; '
                b'filename="a.txt"\r\nContent-Type: text/plain\r\n\r\n'
                b"Penelitian memakai metode survei dan analisis data."
                b"\r\n--a;b--\r\n")
        try:
            resp, data = self._headers(
                conn, "POST", "/api/analyze-folder", body=body,
                headers={"Content-Type":
                         'multipart/form-data; boundary="a;b"'})
        finally:
            conn.close()
        self.assertEqual(resp.status, 200)
        res = json.loads(data)
        self.assertEqual(res["folder"]["count"], 1)

    def test_unsupported_methods_get_501_with_security_headers(self):
        # N-2: the stdlib 501 page carries the same three headers.
        host, port = self.server.server_address[:2]
        for method in ("PUT", "DELETE", "OPTIONS", "HEAD"):
            conn = http.client.HTTPConnection(host, port, timeout=10)
            try:
                resp, _ = self._headers(conn, method, "/api/detect",
                                        body=b"{}")
            finally:
                conn.close()
            with self.subTest(method=method):
                self.assertEqual(resp.status, 501)
                self.assertIsNotNone(
                    resp.getheader("Content-Security-Policy"))
                self.assertEqual(
                    resp.getheader("X-Content-Type-Options"), "nosniff")
                self.assertEqual(
                    resp.getheader("X-Frame-Options"), "DENY")

    def test_security_headers_on_error_responses(self):
        # 400, 413, and 500 JSON errors carry the same three headers
        # as a 200.
        host, port = self.server.server_address[:2]
        cases = []
        # 400: empty text.
        cases.append(("POST", "/api/analyze",
                      json.dumps({"text": ""}).encode(),
                      {"Content-Type": "application/json"}, 400))
        # 413: oversize body.
        cases.append(("POST", "/api/analyze",
                      json.dumps({"text": "x" * (tools._MAX_BODY + 1)})
                      .encode(),
                      {"Content-Type": "application/json"}, 413))
        for method, path, body, headers, want in cases:
            conn = http.client.HTTPConnection(host, port, timeout=10)
            try:
                resp, _ = self._headers(conn, method, path, body=body,
                                        headers=headers)
            finally:
                conn.close()
            with self.subTest(status=want):
                self.assertEqual(resp.status, want)
                self.assertIsNotNone(
                    resp.getheader("Content-Security-Policy"))
                self.assertEqual(
                    resp.getheader("X-Content-Type-Options"), "nosniff")
                self.assertEqual(
                    resp.getheader("X-Frame-Options"), "DENY")
        # 500: a handler crash is honest JSON, still with headers.
        with patch.object(tools, "detect_ai",
                          side_effect=RuntimeError("boom")):
            conn = http.client.HTTPConnection(host, port, timeout=10)
            try:
                resp, data = self._headers(
                    conn, "POST", "/api/detect",
                    body=json.dumps({"text": TEXT}).encode(),
                    headers={"Content-Type": "application/json"})
            finally:
                conn.close()
        self.assertEqual(resp.status, 500)
        self.assertNotIn("Traceback", data.decode())
        self.assertIsNotNone(resp.getheader("Content-Security-Policy"))
        self.assertEqual(resp.getheader("X-Content-Type-Options"),
                         "nosniff")
        self.assertEqual(resp.getheader("X-Frame-Options"), "DENY")

    def test_handle_error_swallows_client_abort(self):
        # N-3: process_request_thread calls the SERVER's
        # handle_error, not the handler's — a broken pipe or reset
        # writes nothing to stderr; a real error still logs.
        server = tools.make_server("127.0.0.1", 0)
        try:
            for exc_type in (BrokenPipeError, ConnectionResetError):
                err = io.StringIO()
                with patch("sys.exc_info",
                           return_value=(exc_type, exc_type(), None)):
                    with redirect_stderr(err):
                        server.handle_error(None, ("127.0.0.1", 1))
                self.assertEqual(err.getvalue(), "", exc_type)
            err = io.StringIO()
            with patch("sys.exc_info",
                       return_value=(ValueError, ValueError("x"), None)):
                with redirect_stderr(err):
                    server.handle_error(None, ("127.0.0.1", 1))
            self.assertIn("Exception occurred during processing",
                          err.getvalue())
        finally:
            server.server_close()

    def test_handler_sets_socket_timeout(self):
        # N-4: every connection gets a 30-second timeout, so a
        # stalled client cannot hold a handler slot forever.
        import socket

        handler = object.__new__(tools._UIHandler)
        handler.request = socket.socket()
        try:
            tools._UIHandler.setup(handler)
            self.assertEqual(handler.request.gettimeout(), 30)
        finally:
            handler.request.close()

    def test_js_detect_band_is_capped(self):
        # B-1 (web UI): the AI band is 60, and a capped verdict is
        # forced to the mixed band with its reason shown.
        html = tools.WEB_UI_HTML
        self.assertIn("function detectBand(score, lang, capped)", html)
        self.assertIn("score >= 60", html)
        self.assertIn("res.verdict_capped", html)
        self.assertIn("esc(res.verdict_capped_reason)", html)

    def test_thread_cap_end_to_end_with_stalled_connections(self):
        # The 8-slot cap, end to end: 8 connections that never
        # finish their body hold all 8 slots, so a 9th request gets
        # no answer within 2 seconds; closing one stalled
        # connection frees a slot and the 9th request answers.
        # (The in-process semaphore test in TestServe pins the cap
        # itself; this test pins that the cap actually gates
        # requests.)
        server = tools.make_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever,
                                  daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        stalled = []
        try:
            for _ in range(8):
                s = http.client.socket.create_connection(
                    (host, port), timeout=10)
                s.sendall(b"POST /api/analyze HTTP/1.1\r\n"
                          b"Host: x\r\n"
                          b"Content-Type: application/json\r\n"
                          b"Content-Length: 100000\r\n\r\n"
                          b'{"text": "abc')
                stalled.append(s)
            time.sleep(0.5)  # let all 8 handlers block on the body
            conn = http.client.HTTPConnection(host, port, timeout=2)
            try:
                conn.request("GET", "/api/prompts")
                with self.assertRaises((TimeoutError, OSError)):
                    conn.getresponse()
            finally:
                conn.close()
            stalled.pop().close()  # free one slot
            status, _ = _request(f"http://{host}:{port}", "GET",
                                 "/api/prompts")
            self.assertEqual(status, 200)
        finally:
            for s in stalled:
                s.close()
            server.shutdown()
            server.server_close()


class TestServeReadability1270(unittest.TestCase):
    """v1.27.0: /api/analyze carries readability, and the Analisis tab
    renders it (Flesch Reading Ease + band, FKGL, averages, note)."""

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

    def test_api_analyze_returns_readability(self):
        status, body = _request(self.base, "POST", "/api/analyze", {
            "text": TEXT, "refs": "sample", "verify": False})
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertIn("readability", res)
        r = res["readability"]
        self.assertEqual(r, tools.readability_score(TEXT))
        self.assertIn("flesch_reading_ease", r)
        self.assertIn("flesch_kincaid_grade", r)
        self.assertIn("band", r)
        self.assertIn("note", r)
        # Readability is informative only: the score is untouched.
        self.assertEqual(res["score_parts"], [25.0, 25.0, 25.0, 25.0])
        self.assertEqual(res["quality_score"], 100)

    def test_js_renders_readability_in_analyze_tab(self):
        html = tools.WEB_UI_HTML
        self.assertIn("res.readability", html)
        self.assertIn("Flesch Reading Ease", html)
        self.assertIn("Flesch-Kincaid Grade Level", html)
        self.assertIn("esc(r.band)", html)
        self.assertIn("esc(r.note)", html)
        self.assertIn("avg_words_per_sentence", html)
        self.assertIn("avg_syllables_per_word", html)
