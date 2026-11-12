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
                raise tools.LookupNotFoundError("not found (HTTP 404)")
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
                          side_effect=tools.LookupNotFoundError("not found (HTTP 404)")):
            with self.assertRaises(SystemExit) as cm:
                tools.cite_main(["--lookup", "10.9999/tidak-ada"])
        self.assertEqual(cm.exception.code, 2)


class TestLoadReferencesValidation(unittest.TestCase):
    def _write(self, d, data):
        path = os.path.join(d, "refs.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_list_top_level_rejected(self):
        # The old list form (no 'key' per item) used to raise a bare
        # KeyError; now it is a plain ValueError.
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, [{"title": "Tanpa kunci"}])
            with self.assertRaises(ValueError) as cm:
                tools.load_references(path)
            self.assertIn("bibliografi tidak valid", str(cm.exception))

    def test_non_dict_top_level_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, "bukan objek")
            with self.assertRaises(ValueError):
                tools.load_references(path)

    def test_non_dict_value_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, {"kunci": "bukan objek"})
            with self.assertRaises(ValueError):
                tools.load_references(path)

    def test_single_string_author_normalized(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, {"a": {"title": "Judul",
                                         "authors": "Solo, Penulis"}})
            refs = tools.load_references(path)
            self.assertEqual(refs["a"]["authors"], ["Solo, Penulis"])

    def test_non_string_authors_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, {"a": {"authors": [1, 2]}})
            with self.assertRaises(ValueError):
                tools.load_references(path)
            path = self._write(d, {"a": {"authors": 42}})
            with self.assertRaises(ValueError):
                tools.load_references(path)

    def test_non_string_title_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write(d, {"a": {"title": 123}})
            with self.assertRaises(ValueError):
                tools.load_references(path)


class TestVerifyDois(unittest.TestCase):
    """Cross-source DOI verification: Crossref + OpenAlex.

    A DOI counts as real when at least one source has it, because arXiv
    and datasets register with DataCite, not Crossref. 'missing' needs
    a checked source to answer 404 with no source erroring — a skipped
    source (no OpenAlex key) does not shield a checked 404.
    """

    def _fake_lookup(self, crossref_ok: bool, openalex_ok: bool):
        def fake(url):
            if "crossref" in url:
                if crossref_ok:
                    return CROSSREF_FIXTURE
                raise tools.LookupNotFoundError("not found (HTTP 404)")
            if openalex_ok:
                return OPENALEX_FIXTURE
            raise tools.LookupNotFoundError("not found (HTTP 404)")
        return fake

    def _refs(self, doi: str = "10.1038/nature14539") -> dict:
        return {"lecun2015": {"title": "Deep learning", "year": 2015,
                              "authors": ["LeCun, Yann"], "doi": doi}}

    def test_ok_when_only_crossref_has_it(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
            with patch.object(tools, "_lookup_get",
                              side_effect=self._fake_lookup(True, False)):
                result = tools.verify_reference_dois(self._refs())
        self.assertEqual(result["lecun2015"]["crossref"], "ok")
        self.assertEqual(result["lecun2015"]["openalex"], "not-found")
        self.assertEqual(result["lecun2015"]["verdict"], "ok")

    def test_ok_when_only_openalex_has_it(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
            with patch.object(tools, "_lookup_get",
                              side_effect=self._fake_lookup(False, True)):
                result = tools.verify_reference_dois(self._refs())
        self.assertEqual(result["lecun2015"]["verdict"], "ok")

    def test_missing_when_both_sources_404(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
            with patch.object(tools, "_lookup_get",
                              side_effect=self._fake_lookup(False, False)):
                result = tools.verify_reference_dois(self._refs())
        self.assertEqual(result["lecun2015"]["verdict"], "missing")

    def test_crossref_404_without_key_is_missing(self):
        # H-5: a checked source saying 404 is already "missing" when
        # the other source was merely skipped for lack of a key — a
        # skipped source does not shield a checked 404.
        with patch.dict(os.environ, {"OPENALEX_API_KEY": ""}):
            with patch.object(tools, "_lookup_get",
                              side_effect=self._fake_lookup(False, False)) as get:
                result = tools.verify_reference_dois(self._refs())
        self.assertEqual(result["lecun2015"]["openalex"], "skipped")
        self.assertEqual(result["lecun2015"]["crossref"], "not-found")
        self.assertEqual(result["lecun2015"]["verdict"], "missing")
        self.assertEqual(get.call_count, 1)  # Crossref only

    def test_error_in_one_source_blocks_missing(self):
        # One source erroring means the DOI could not be checked
        # properly, even if the other source says 404.
        def fake(url, **kwargs):
            if "api.crossref.org" in url:
                raise tools.LookupNotFoundError("404")
            raise tools.LookupError("offline")
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
            with patch.object(tools, "_lookup_get", side_effect=fake):
                result = tools.verify_reference_dois(self._refs())
        self.assertEqual(result["lecun2015"]["verdict"], "unverified")

    def test_reference_without_doi_is_no_doi(self):
        result = tools.verify_reference_dois(self._refs(doi=""))
        self.assertEqual(result["lecun2015"]["verdict"], "no-doi")

    def test_network_error_is_unverified_not_missing(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
            with patch.object(tools, "_lookup_get",
                              side_effect=tools.LookupError("offline")):
                result = tools.verify_reference_dois(self._refs())
        self.assertEqual(result["lecun2015"]["verdict"], "unverified")

    def test_format_verification_counts_verdicts(self):
        result = {
            "ok1": {"doi": "10.1/a", "crossref": "ok",
                    "openalex": "not-found", "verdict": "ok"},
            "bad1": {"doi": "10.1/b", "crossref": "not-found",
                     "openalex": "not-found", "verdict": "missing"},
            "nokey": {"doi": "", "crossref": "no-doi",
                      "openalex": "no-doi", "verdict": "no-doi"},
        }
        text = tools.format_verification(result, lang="en")
        self.assertIn("DOI verification", text)
        self.assertIn("NOT FOUND", text)
        self.assertIn("Verified 1 of 3 DOIs", text)
        self.assertIn("no DOI 1", text)

    def test_format_verification_empty(self):
        self.assertIn("Tidak ada referensi",
                      tools.format_verification({}, lang="id"))

    def test_cite_main_verify_exits_1_on_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.json")
            tools.save_reference(self._refs()["lecun2015"], path)
            with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
                with patch.object(tools, "_lookup_get",
                                  side_effect=self._fake_lookup(False, False)):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = tools.cite_main(["--refs", path, "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("TIDAK DITEMUKAN", buf.getvalue())
        self.assertIn("lecun2015", buf.getvalue())

    def test_cite_main_verify_exits_0_when_found(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.json")
            tools.save_reference(self._refs()["lecun2015"], path)
            with patch.dict(os.environ, {"OPENALEX_API_KEY": "test"}):
                with patch.object(tools, "_lookup_get",
                                  side_effect=self._fake_lookup(True, True)):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = tools.cite_main(["--refs", path, "--verify"])
        self.assertEqual(rc, 0)

    def test_cite_main_verify_requires_refs(self):
        with self.assertRaises(SystemExit) as cm:
            tools.cite_main(["--verify"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()


class TestDoiSourceStatusStructural(unittest.TestCase):
    """v1.25.2: _doi_source_status detects 404 by exception type,
    not by grepping the message for "404"."""

    def test_not_found_error_is_not_found(self):
        with patch.object(tools, "_lookup_get",
                          side_effect=tools.LookupNotFoundError(
                              "not found (HTTP 404)")):
            self.assertEqual(
                tools._doi_source_status("https://x.example/1"),
                "not-found")

    def test_lookup_error_mentioning_404_is_error(self):
        # A network error whose message happens to contain "404"
        # must not be mistaken for a confirmed 404.
        with patch.object(tools, "_lookup_get",
                          side_effect=tools.LookupError(
                              "proxy replied 404-ish garbage")):
            self.assertEqual(
                tools._doi_source_status("https://x.example/1"), "error")

    def test_lookup_get_raises_not_found_error_on_404(self):
        # The real _lookup_get turns an HTTPError 404 into the
        # distinct subclass (message unchanged for old callers).
        import urllib.error
        err = urllib.error.HTTPError("https://x.example/1", 404,
                                     "Not Found", {}, None)
        with patch.object(tools.urllib.request, "urlopen",
                          side_effect=err):
            with self.assertRaises(tools.LookupNotFoundError):
                tools._lookup_get("https://x.example/1")
