"""Tests for the local web UI (`serve`): the embedded page and the JSON API.

The server runs on an ephemeral localhost port in a thread; no
external network is used (DOI verification stays off in these tests).
"""

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

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
