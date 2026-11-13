"""Audit #8 T-4: /api/prompts/fill rejects non-string id/values.

Audit #8 H-6: the handler coerced with str(), so
`values: {"judul": {"a": 1}}` answered 200 with "{'a': 1}" in
the text, `null` became "None", `["a","b"]` became "['a',
'b']", `true` became "True", and `id: 123` / `["x"]` became
"prompt tidak dikenal: 123" / "['x']". All are 400 now, like
_json_text in the other five handlers. The web UI always sends
strings, so it is unaffected (the valid-fill control below).
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


class TestAudit8PromptsFill(unittest.TestCase):
    """H-6: no str() coercion on /api/prompts/fill."""

    @classmethod
    def setUpClass(cls):
        cls.server = tools.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"
        _, body = _request(cls.base, "GET", "/api/prompts")
        prompt = json.loads(body)["prompts"][0]
        cls.prompt_id = prompt["id"]
        cls.field_key = prompt["fields"][0]["key"]
        cls.good_values = {f["key"]: f"nilai-{f['key']}"
                           for f in prompt["fields"]}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_dict_value_is_400(self):
        status, body = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id,
            "values": {self.field_key: {"a": 1}}})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))
        self.assertNotIn("{'a': 1}", body)

    def test_null_value_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id,
            "values": {self.field_key: None}})
        self.assertEqual(status, 400)

    def test_list_value_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id,
            "values": {self.field_key: ["a", "b"]}})
        self.assertEqual(status, 400)

    def test_bool_value_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id,
            "values": {self.field_key: True}})
        self.assertEqual(status, 400)

    def test_int_value_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id,
            "values": {self.field_key: 123}})
        self.assertEqual(status, 400)

    def test_values_null_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id, "values": None})
        self.assertEqual(status, 400)

    def test_values_list_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id, "values": ["a", "b"]})
        self.assertEqual(status, 400)

    def test_values_bool_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id, "values": True})
        self.assertEqual(status, 400)

    def test_int_id_is_400(self):
        status, body = _request(self.base, "POST", "/api/prompts/fill", {
            "id": 123, "values": {}})
        self.assertEqual(status, 400)
        self.assertNotIn("123", body)

    def test_list_id_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": ["x"], "values": {}})
        self.assertEqual(status, 400)

    def test_bool_id_is_400(self):
        status, _ = _request(self.base, "POST", "/api/prompts/fill", {
            "id": True, "values": {}})
        self.assertEqual(status, 400)

    def test_valid_fill_still_200(self):
        status, body = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id, "values": self.good_values,
            "lang": "id"})
        self.assertEqual(status, 200)
        text = json.loads(body)["text"]
        for value in self.good_values.values():
            self.assertIn(value, text)

    def test_braces_in_value_stay_literal(self):
        # A string value that looks like a placeholder is NOT
        # re-interpreted (no format-string injection).
        values = dict(self.good_values)
        values[self.field_key] = "{teori}"
        status, body = _request(self.base, "POST", "/api/prompts/fill", {
            "id": self.prompt_id, "values": values, "lang": "id"})
        self.assertEqual(status, 200)
        self.assertIn("{teori}", json.loads(body)["text"])


if __name__ == "__main__":
    unittest.main()
