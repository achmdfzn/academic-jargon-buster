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
