"""Tests for reference lookup (OpenAlex / Crossref) in academic_tools.py.

Network calls are mocked: no test hits the real APIs. Live behavior was
verified by hand (Crossref DOI 10.1038/nature14539, OpenAlex by DOI).
"""

import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import patch

import academic_tools as tools

CROSSREF_FIXTURE = {
    "message": {
        "title": ["Deep learning"],
        "author": [
            {"family": "LeCun", "given": "Yann"},
            {"family": "Bengio", "given": "Yoshua"},
            {"family": "Hinton", "given": "Geoffrey"},
        ],
        "container-title": ["Nature"],
        "published": {"date-parts": [[2015, 5, 27]]},
        "type": "journal-article",
        "DOI": "10.1038/nature14539",
    }
}

OPENALEX_FIXTURE = {
    "id": "https://openalex.org/W2919115771",
    "doi": "https://doi.org/10.1038/nature14539",
    "title": "Deep learning",
    "display_name": "Deep learning",
    "publication_year": 2015,
    "type": "article",
    "authorships": [
        {"author": {"display_name": "Yann LeCun"}},
        {"author": {"display_name": "Yoshua Bengio"}},
        {"author": {"display_name": "Geoffrey Hinton"}},
    ],
    "primary_location": {"source": {"display_name": "Nature"}},
}

OPENALEX_SEARCH_FIXTURE = {"results": [OPENALEX_FIXTURE], "meta": {"count": 1}}


class TestLookupParsing(unittest.TestCase):
    def test_crossref_to_ref_parses_live_shape(self):
        ref = tools._crossref_to_ref(CROSSREF_FIXTURE["message"])
        self.assertEqual(ref["title"], "Deep learning")
        self.assertEqual(ref["authors"], ["LeCun, Yann", "Bengio, Yoshua", "Hinton, Geoffrey"])
        self.assertEqual(ref["venue"], "Nature")
        self.assertEqual(ref["year"], 2015)
        self.assertEqual(ref["type"], "article")
        self.assertEqual(ref["doi"], "10.1038/nature14539")

    def test_openalex_to_ref_parses_live_shape(self):
        ref = tools._openalex_to_ref(OPENALEX_FIXTURE)
        self.assertEqual(ref["title"], "Deep learning")
        self.assertEqual(ref["authors"], ["LeCun, Yann", "Bengio, Yoshua", "Hinton, Geoffrey"])
        self.assertEqual(ref["venue"], "Nature")
        self.assertEqual(ref["year"], 2015)
        self.assertEqual(ref["type"], "article")
        self.assertEqual(ref["doi"], "10.1038/nature14539")

    def test_crossref_type_mapping(self):
        self.assertEqual(tools._crossref_type("proceedings-article"), "conference")
        self.assertEqual(tools._crossref_type("book-chapter"), "chapter")
        self.assertEqual(tools._crossref_type("weird-kind"), "article")


class TestLookupRouting(unittest.TestCase):
    def test_lookup_by_doi_uses_crossref(self):
        with patch.object(tools, "_lookup_get", return_value=CROSSREF_FIXTURE) as m:
            ref = tools.lookup_reference("10.1038/nature14539")
        self.assertIn("api.crossref.org", m.call_args[0][0])
        self.assertEqual(ref["title"], "Deep learning")

    def test_lookup_by_doi_url_form(self):
        with patch.object(tools, "_lookup_get", return_value=CROSSREF_FIXTURE) as m:
            tools.lookup_reference("https://doi.org/10.1038/nature14539")
        self.assertIn("10.1038/nature14539", m.call_args[0][0])

    def test_lookup_by_doi_falls_back_to_openalex(self):
        calls = {"n": 0}

        def fake_get(url):
            calls["n"] += 1
            if calls["n"] == 1:
                raise tools.LookupError("not found (HTTP 404)")
            return OPENALEX_FIXTURE

        with patch.object(tools, "_lookup_get", side_effect=fake_get) as m:
            ref = tools.lookup_reference("10.1038/nature14539")
        self.assertIn("openalex.org", m.call_args[0][0])
        self.assertEqual(ref["title"], "Deep learning")

    def test_lookup_by_title_searches_openalex(self):
        with patch.object(tools, "_lookup_get", return_value=OPENALEX_SEARCH_FIXTURE) as m:
            ref = tools.lookup_reference("Deep learning")
        self.assertIn("api.openalex.org/works?search=", m.call_args[0][0])
        self.assertEqual(ref["title"], "Deep learning")

    def test_lookup_title_no_results_raises(self):
        with patch.object(tools, "_lookup_get", return_value={"results": []}):
            with self.assertRaises(tools.LookupError):
                tools.lookup_reference("judul yang tidak ada")

    def test_lookup_empty_query_raises(self):
        with self.assertRaises(tools.LookupError):
            tools.lookup_reference("   ")


class TestLookupGetErrors(unittest.TestCase):
    def _http_error(self, code):
        return urllib.error.HTTPError("https://example.org/", code, "x", {}, None)

    def test_lookup_get_maps_404(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(404)):
            with self.assertRaises(tools.LookupError) as cm:
                tools._lookup_get("https://example.org/")
        self.assertIn("404", str(cm.exception))

    def test_lookup_get_maps_429_with_api_key_hint(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(429)):
            with self.assertRaises(tools.LookupError) as cm:
                tools._lookup_get("https://example.org/")
        self.assertIn("OPENALEX_API_KEY", str(cm.exception))

    def test_lookup_get_maps_401_to_api_key_hint(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(401)):
            with self.assertRaises(tools.LookupError) as cm:
                tools._lookup_get("https://example.org/")
        message = str(cm.exception)
        self.assertIn("OPENALEX_API_KEY", message)
        self.assertIn("openalex.org/settings/api", message)

    def test_lookup_get_maps_403_to_api_key_hint(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(403)):
            with self.assertRaises(tools.LookupError) as cm:
                tools._lookup_get("https://example.org/")
        self.assertIn("OPENALEX_API_KEY", str(cm.exception))

    def test_lookup_get_maps_url_error(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("no network")):
            with self.assertRaises(tools.LookupError):
                tools._lookup_get("https://example.org/")


class TestReferenceKeysAndSaving(unittest.TestCase):
    def test_reference_key_auto(self):
        ref = tools._crossref_to_ref(CROSSREF_FIXTURE["message"])
        self.assertEqual(tools.reference_key(ref), "lecun2015")

    def test_reference_key_collision_appends_letter(self):
        ref = tools._crossref_to_ref(CROSSREF_FIXTURE["message"])
        self.assertEqual(tools.reference_key(ref, {"lecun2015": {}}), "lecun2015a")
        self.assertEqual(
            tools.reference_key(ref, {"lecun2015": {}, "lecun2015a": {}}), "lecun2015b")

    def test_save_reference_creates_and_appends(self):
        ref = tools._crossref_to_ref(CROSSREF_FIXTURE["message"])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.json")
            key1 = tools.save_reference(ref, path)
            self.assertEqual(key1, "lecun2015")
            self.assertEqual(list(tools.load_references(path).keys()), ["lecun2015"])
            key2 = tools.save_reference(ref, path)
            self.assertEqual(key2, "lecun2015a")
            self.assertEqual(
                sorted(tools.load_references(path).keys()), ["lecun2015", "lecun2015a"])


class TestCiteMainLookup(unittest.TestCase):
    def test_cite_main_lookup_prints_json(self):
        with patch.object(tools, "_lookup_get", return_value=CROSSREF_FIXTURE):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tools.cite_main(["--lookup", "10.1038/nature14539"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["title"], "Deep learning")

    def test_cite_main_lookup_add_to(self):
        with patch.object(tools, "_lookup_get", return_value=CROSSREF_FIXTURE):
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "refs.json")
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = tools.cite_main([
                        "--lookup", "10.1038/nature14539", "--add-to", path])
                self.assertEqual(rc, 0)
                self.assertIn("lecun2015", buf.getvalue())
                self.assertIn("lecun2015", tools.load_references(path))

    def test_cite_main_lookup_not_found_exits_2(self):
        with patch.object(tools, "_lookup_get",
                          side_effect=tools.LookupError("not found (HTTP 404)")):
            with self.assertRaises(SystemExit) as cm:
                tools.cite_main(["--lookup", "10.9999/tidak-ada"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
