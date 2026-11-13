"""Audit #6 follow-up tests, track 6 (v1.27.4): H-10, H-11, N-1..N-6,
N-8, N-11, T-1, T-5, T-7.

Style: stdlib unittest, dict + subTest like test_audit6_track3.py.
No network: the cite --lookup 404 is tested with a mocked lookup,
the server probes run against a local server on an ephemeral port.
"""

import hashlib
import http.client
import io
import json
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from tests.test_detector import AI_1, AI_2, AI_3, HUMAN_1, HUMAN_2, HUMAN_3

ROOT = Path(__file__).resolve().parent.parent

# --- T-5: fresh AI-style prose, written from scratch for calibration --
# Varied starters (no starter repeats), template phrases present but
# not stacked, uniform sentence lengths: modern AI output that is
# NOT the stereotypical "Penelitian ini" x4 of AI_1/AI_2/AI_3.
# 107 words, 8 sentences. Measured on v1.27.4: 55.2 "Campuran".
AI_FRESH = (
    "Transformasi digital telah mengubah cara organisasi mengelola informasi dalam satu dekade terakhir. "
    "Teknologi cloud memungkinkan tim bekerja dari lokasi berbeda tanpa kehilangan akses terhadap data penting. "
    "Selain itu, otomatisasi proses bisnis mengurangi beban administratif yang selama ini memakan waktu. "
    "Perlu dicatat bahwa keberhasilan adopsi teknologi sangat bergantung pada kesiapan sumber daya manusia. "
    "Dalam hal ini, pelatihan berkelanjutan menjadi faktor penentu bagi karyawan di semua tingkatan. "
    "Hasil survei menunjukkan bahwa perusahaan yang berinvestasi pada literasi digital mencatat produktivitas lebih tinggi. "
    "Dengan demikian, strategi digital perlu dirancang sebagai program jangka panjang, bukan sekadar proyek sesaat. "
    "Sebagai kesimpulan, organisasi yang adaptif akan lebih siap menghadapi perubahan teknologi di masa depan."
)

BASE_TEXT = ("Penelitian ini menggunakan metode survei untuk "
             "mengumpulkan data primer.")
SAMPLE_REFS = {
    "field2018": {"title": "Discovering Statistics",
                  "authors": ["Field, Andy"], "year": 2018},
}


class TestCappedLimitWording(unittest.TestCase):
    """H-10: the block needs BOTH conditions (<100 words AND
    <6 sentences), so the text must say "dan"/"and", not "atau"/"or"."""

    def test_strings_say_and_not_or(self):
        cases = {
            "id": tools._DETECT_STRINGS["id"]["capped_limit"],
            "en": tools._DETECT_STRINGS["en"]["capped_limit"],
        }
        for lang, text in cases.items():
            with self.subTest(lang=lang):
                if lang == "id":
                    self.assertIn("<100 kata dan <6 kalimat", text)
                else:
                    self.assertIn("<100 words and <6 sentences", text)
                self.assertNotIn(" atau ", text)
                self.assertNotIn(" or ", text)

    def test_under_100_words_but_6_plus_sentences_can_reach_ai(self):
        # 95 words (<100) but 8 sentences (>=6): only the word
        # count is short, so the cap must NOT apply.
        sents = tools._split_sentences(AI_1)
        text = ". ".join(sents[:8]) + "."
        self.assertLess(len(text.split()), 100)
        self.assertGreaterEqual(len(tools._split_sentences(text)), 6)
        result = tools.detect_ai(text)
        self.assertFalse(result["verdict_capped"])
        self.assertEqual(result["verdict"], "Kemungkinan besar AI")
        self.assertGreaterEqual(result["ai_score"], 60)


class TestCiteMissingFiles(unittest.TestCase):
    """H-11: every cite branch reports a missing file as a plain
    ValueError (exit 1), never a FileNotFoundError traceback."""

    def _run_cite(self, argv):
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            try:
                code = tools.cite_main(argv)
            except ValueError as e:
                # main() turns this into a plain stderr message
                # and exit 1; mirror that here.
                err.write(str(e) + "\n")
                code = 1
        return code, err.getvalue(), out.getvalue()

    def test_missing_files_are_clean_exit_1(self):
        missing_in = "/tmp/t6-tidak-ada-input-xyz.txt"
        missing_refs = "/tmp/t6-tidak-ada-refs-xyz.json"
        with tempfile.TemporaryDirectory() as tmp:
            good_in = os.path.join(tmp, "naskah.txt")
            Path(good_in).write_text("Menurut [cite:field2018].",
                                     encoding="utf-8")
            good_refs = os.path.join(tmp, "refs.json")
            Path(good_refs).write_text(
                json.dumps(SAMPLE_REFS), encoding="utf-8")
            cases = {
                "weave missing input": ["cite", missing_in,
                                        "--refs", good_refs],
                "weave missing refs": ["cite", good_in,
                                       "--refs", missing_refs],
                "weave --text missing refs": [
                    "cite", "--text", "Menurut [cite:field2018].",
                    "--refs", missing_refs],
                "audit missing input": ["cite", missing_in,
                                        "--refs", good_refs, "--audit"],
                "audit missing refs": [
                    "cite", "--text", "Menurut [cite:field2018].",
                    "--refs", missing_refs, "--audit"],
                "verify missing refs": ["cite", "--refs", missing_refs,
                                        "--verify"],
                "export-bibtex missing refs": [
                    "cite", "--refs", missing_refs, "--export-bibtex"],
                "export-ris missing refs": [
                    "cite", "--refs", missing_refs, "--export-ris"],
                "export-bibtex bad out dir": [
                    "cite", "--refs", good_refs, "--export-bibtex",
                    "--out", os.path.join(tmp, "no-dir", "out.bib")],
            }
            # cite_main takes argv without the program name.
            for name, argv in cases.items():
                with self.subTest(case=name):
                    code, err, _ = self._run_cite(argv[1:])
                    self.assertEqual(code, 1, err)
                    self.assertIn("File tidak ditemukan", err)
                    self.assertNotIn("Traceback", err)

    def test_load_references_missing_file_is_value_error(self):
        with self.assertRaises(ValueError) as cm:
            tools.load_references("/tmp/t6-tidak-ada-refs-xyz.json")
        self.assertIn("File tidak ditemukan", str(cm.exception))


class TestMatcherCurlyQuotes(unittest.TestCase):
    """N-1: curly quotes, '!', ellipsis and closing brackets let a
    term match; the old guards still hold."""

    def test_separator_chars_allow_a_match(self):
        cases = {
            "curly double": "\u201ckorelasi\u201d",
            "curly single": "\u2018korelasi\u2019",
            "guillemets": "\u00abkorelasi\u00bb",
            "bang": "korelasi!validitas",
            "ellipsis": "korelasi\u2026validitas",
            "close paren": "korelasi)validitas",
            "close bracket": "korelasi]validitas",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                terms = [m["term"] for m in tools.find_terms(text)]
                self.assertIn("korelasi", terms, text)
                if name in ("bang", "ellipsis", "close paren",
                            "close bracket"):
                    self.assertIn("validitas", terms, text)

    def test_old_guards_still_hold(self):
        cases = {
            "pre-t-test": "pre-t-test",
            "contest-test": "contest-test",
            "dot anova": ".anova",
            "digit anova": "1anova",
            "comma still works": "korelasi,validitas",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                terms = [m["term"] for m in tools.find_terms(text)]
                if name == "comma still works":
                    self.assertEqual(terms, ["korelasi", "validitas"])
                else:
                    self.assertEqual(terms, [], text)


class TestLoneSurrogateErrors(unittest.TestCase):
    """N-2: a lone surrogate is a clean 400 / ValueError, never the
    raw "'utf-8' codec can't encode ..." message."""

    def test_hash_helpers_raise_clean_value_error(self):
        bad = "teks\ud800 buruk"
        for fn in (tools._stored_hash, tools._legacy_stored_hash,
                   tools._ws_collapsed_hash):
            with self.subTest(fn=fn.__name__):
                with self.assertRaises(ValueError) as cm:
                    fn(bad)
                self.assertIn("surrogate", str(cm.exception))
                self.assertNotIn("codec", str(cm.exception))

    def test_duplicates_and_save_raise_clean_value_error(self):
        bad = "Penelitian ini memakai survei\ud800 untuk data."
        with self.assertRaises(ValueError) as cm:
            tools.find_duplicates(bad, db=":memory:")
        self.assertIn("surrogate", str(cm.exception))
        self.assertNotIn("codec", str(cm.exception))
        result = {"quality_score": 100,
                  "style": {"style_score": 25}, "jargon": [],
                  "citations": {}, "doi_verification": {},
                  "suggestions": {}}
        with self.assertRaises(ValueError) as cm:
            tools.save_analysis(bad, result, {}, db=":memory:")
        self.assertIn("surrogate", str(cm.exception))
        self.assertNotIn("codec", str(cm.exception))


class TestCorruptDbPathMasked(unittest.TestCase):
    """N-3: a corrupt-library error names only the basename, never
    the absolute path."""

    def test_open_library_masks_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "corrupt.db")
            Path(bad).write_bytes(b"bukan sqlite")
            with self.assertRaises(ValueError) as cm:
                tools.open_library(bad)
            msg = str(cm.exception)
            self.assertIn("pustaka rusak", msg)
            self.assertIn("corrupt.db", msg)
            self.assertNotIn(tmp, msg)


class TestOwnRunWhitespaceVariants(unittest.TestCase):
    """N-5: a saved run re-typed with different internal spacing
    is still its own run; the B-2 hash invariant and legacy rows
    stay intact."""

    def test_whitespace_variants_are_own_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "lib.db")
            result = tools.analyze_text_quality(
                BASE_TEXT, {}, verify_dois=False)
            tools.save_analysis(BASE_TEXT, result, {}, db=db)
            variants = {
                "exact": BASE_TEXT,
                "double spaces": BASE_TEXT.replace(" ", "  "),
                "tab": BASE_TEXT.replace(" ", "\t", 1),
                "leading/trailing": "  \n" + BASE_TEXT + "\n\n",
            }
            for name, text in variants.items():
                with self.subTest(variant=name):
                    self.assertEqual(
                        tools.find_duplicates(text, db=db)["count"], 0)

    def test_other_text_still_flags_and_invariant_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "lib.db")
            result = tools.analyze_text_quality(
                BASE_TEXT, {}, verify_dois=False)
            tools.save_analysis(BASE_TEXT, result, {}, db=db)
            # The same sentences twice in one new text: the saved
            # run is excluded as its own copy, but the two sentences
            # repeat each other inside the new text.
            doubled = BASE_TEXT + " " + BASE_TEXT
            self.assertEqual(
                tools.find_duplicates(doubled, db=db)["count"], 2)
            # B-2 (audit #5): sha256(stored_text) == text_hash.
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT text, text_hash FROM analyses").fetchone()
            self.assertEqual(
                hashlib.sha256(row[0].encode("utf-8")).hexdigest(),
                row[1])
            # A legacy v1.25.2 hash row is still its own run.
            conn.execute("UPDATE analyses SET text_hash=?",
                         (tools._legacy_stored_hash(BASE_TEXT),))
            conn.commit()
            conn.close()
            self.assertEqual(
                tools.find_duplicates(BASE_TEXT, db=db)["count"], 0)

    def test_ws_collapsed_hash_is_whitespace_only(self):
        # Case and punctuation still matter: only whitespace is
        # collapsed, unlike _normalize_sentence.
        self.assertNotEqual(
            tools._ws_collapsed_hash("Penelitian ini."),
            tools._ws_collapsed_hash("penelitian ini."))
        self.assertNotEqual(
            tools._ws_collapsed_hash("Penelitian ini."),
            tools._ws_collapsed_hash("Penelitian ini"))
        self.assertEqual(
            tools._ws_collapsed_hash("Penelitian  ini."),
            tools._ws_collapsed_hash("Penelitian\tini."))


class TestLookupNotFoundExitCode(unittest.TestCase):
    """N-6: cite --lookup on a confirmed-404 DOI exits 1, not
    argparse's exit 2; other lookup failures keep exit 2."""

    def test_fake_doi_exits_1(self):
        err = io.StringIO()
        with patch.object(
                tools, "lookup_reference",
                side_effect=tools.LookupNotFoundError(
                    "not found (HTTP 404)")), redirect_stderr(err):
            code = tools.cite_main(["--lookup", "10.1234/fake123456"])
        self.assertEqual(code, 1)
        self.assertIn("not found (HTTP 404)", err.getvalue())

    def test_network_error_still_exits_2(self):
        with patch.object(
                tools, "lookup_reference",
                side_effect=tools.LookupError("offline")):
            with self.assertRaises(SystemExit) as cm:
                tools.cite_main(["--lookup", "10.1234/fake123456"])
        self.assertEqual(cm.exception.code, 2)


class TestInMemoryLibrary(unittest.TestCase):
    """T-7: db=":memory:" is a legitimate empty library, not a
    corrupt one."""

    def test_find_duplicates_on_memory_db(self):
        result = tools.find_duplicates(
            "Penelitian ini memakai survei untuk mengumpulkan "
            "data primer.", db=":memory:")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["checked"], 0)
        self.assertFalse(result["truncated"])

    def test_open_library_memory_db_creates_nothing_on_disk(self):
        conn = tools.open_library(":memory:")
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'").fetchall()
        finally:
            conn.close()
        self.assertIn(("analyses",), [tuple(r) for r in rows])
        self.assertEqual(tools.library_stats(db=":memory:")["runs"], 0)


class TestCreswellSourceFormat(unittest.TestCase):
    """N-11: one source string for Creswell & Creswell 2018."""

    def test_single_creswell_format(self):
        formats = {s for _, _, s in tools.DICTIONARY.values()
                   if "Creswell & Creswell 2018" in s}
        self.assertEqual(formats, {
            "Creswell & Creswell 2018, 'Research Design' "
            "(5th ed., ISBN 978-1-5063-8670-6)"})


class TestFreshAiProseCalibration(unittest.TestCase):
    """T-5: varied modern AI prose scores 55.2 "Campuran", NOT
    "Kemungkinan besar AI" — and that is the honest answer, not a
    threshold to tune away (see CHANGELOG v1.27.4). The two
    uniformity signals fire (burstiness, template phrases) while
    lexical diversity and starter variety genuinely read human:
    the text DOES have a varied vocabulary (TTR 0.86) and varied
    starters. Retuning the weights on this one sample would let a
    long formal human text with uniform sentences + transition
    phrases cross 60, so the weights stay 30/30/20/20."""

    def test_fresh_ai_prose_is_mixed_not_likely_ai(self):
        self.assertEqual(len(AI_FRESH.split()), 107)
        self.assertEqual(len(tools._split_sentences(AI_FRESH)), 8)
        result = tools.detect_ai(AI_FRESH)
        self.assertEqual(result["ai_score"], 55.2)
        self.assertEqual(result["verdict"], "Campuran / tidak pasti")
        self.assertFalse(result["verdict_capped"])
        signals = result["signals"]
        self.assertGreaterEqual(signals["burstiness"]["score"], 90)
        self.assertGreaterEqual(signals["template_phrases"]["score"], 90)
        self.assertEqual(signals["lexical_diversity"]["score"], 0.0)
        self.assertEqual(signals["starter_repetition"]["score"], 0.0)

    def test_calibration_separation_still_holds(self):
        for text in (HUMAN_1, HUMAN_2, HUMAN_3):
            with self.subTest(text=text[:20]):
                result = tools.detect_ai(text)
                self.assertLess(result["ai_score"], 40)
                self.assertEqual(result["verdict"],
                                 "Kemungkinan besar manusia")
        for text in (AI_1, AI_2, AI_3):
            with self.subTest(text=text[:20]):
                result = tools.detect_ai(text)
                self.assertGreaterEqual(result["ai_score"], 60)
                self.assertEqual(result["verdict"],
                                 "Kemungkinan besar AI")


class TestChangelogNits(unittest.TestCase):
    """N-10: the Tn./Ny. example in the v1.27.3 entry is the real
    two-sentence text."""

    def test_tn_ny_example_is_two_sentences(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("`Tn. Hadi dan Ny. Sari datang. Mereka rapat.` "
                      "is two sentences", changelog)
        self.assertNotIn("`Tn. Hadi dan Ny. Sari datang.` "
                         "is two sentences", changelog)
        self.assertEqual(len(tools._split_sentences(
            "Tn. Hadi dan Ny. Sari datang. Mereka rapat.")), 2)


def _multipart(parts, boundary="----t6boundary"):
    out = bytearray()
    for name, filename, data in parts:
        out += b"--" + boundary.encode() + b"\r\n"
        disp = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            disp += f'; filename="{filename}"'
        out += disp.encode() + b"\r\n\r\n" + data + b"\r\n"
    out += b"--" + boundary.encode() + b"--\r\n"
    return bytes(out), boundary


class TestServerTrack6(unittest.TestCase):
    """Server-level checks: N-2 (clean 400s), N-3 (masked path),
    N-4 (dotfiles skipped in folder upload), N-8 (HTTP/1.0
    Connection headers), T-1 (huge analysis id is 404, not 500)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "lib.db")
        cls.corrupt = os.path.join(cls.tmp.name, "corrupt.db")
        Path(cls.corrupt).write_bytes(b"bukan sqlite")
        cls._env = patch.dict(
            os.environ, {"ACADEMIC_LIBRARY_DB": cls.db})
        cls._env.start()
        cls.server = tools.make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"
        cls.port = port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._env.stop()
        cls.tmp.cleanup()

    def _request(self, method, path, payload=None):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=10)
        try:
            if payload is None:
                conn.request(method, path)
            else:
                conn.request(method, path, json.dumps(payload),
                             {"Content-Type": "application/json"})
            resp = conn.getresponse()
            return resp.status, resp.read().decode("utf-8", "replace")
        finally:
            conn.close()

    def test_surrogate_errors_are_clean_400s(self):
        cases = {
            "analyze+duplicates": (
                "POST", "/api/analyze",
                {"text": "Penelitian ini memakai survei\ud800 untuk data.",
                 "duplicates": True}),
            "analyze+save": (
                "POST", "/api/analyze",
                {"text": "Penelitian ini memakai survei\ud800 untuk data.",
                 "save": True}),
            "humanize+apply": (
                "POST", "/api/humanize",
                {"text": "Penelitian ini melakukan pengukuran\ud800 "
                         "terhadap suhu.", "apply": True}),
        }
        for name, (method, path, payload) in cases.items():
            with self.subTest(case=name):
                status, body = self._request(method, path, payload)
                self.assertEqual(status, 400, body)
                err = json.loads(body)["error"]
                self.assertIn("surrogate", err)
                self.assertNotIn("codec", err)

    def test_corrupt_db_error_masks_path(self):
        with patch.dict(os.environ,
                        {"ACADEMIC_LIBRARY_DB": self.corrupt}):
            status, body = self._request(
                "GET", "/api/library/stats")
        self.assertEqual(status, 400, body)
        err = json.loads(body)["error"]
        self.assertIn("pustaka rusak", err)
        self.assertNotIn(self.tmp.name, err)

    def test_folder_upload_skips_dotfiles(self):
        good = ("Penelitian ini memakai metode survei. "
                "Data dikumpulkan melalui kuesioner.")
        body, boundary = _multipart([
            ("file", ".hidden.txt", good.encode("utf-8")),
            ("file", "bab1.txt", good.encode("utf-8")),
        ])
        req = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=10)
        try:
            req.request("POST", "/api/analyze-folder", body, {
                "Content-Type":
                    f"multipart/form-data; boundary={boundary}"})
            resp = req.getresponse()
            status, raw = resp.status, resp.read().decode("utf-8")
        finally:
            req.close()
        self.assertEqual(status, 200, raw)
        data = json.loads(raw)
        names = [e["file"] for e in data["folder"]["files"]]
        self.assertEqual(names, ["bab1.txt"])
        skipped = {s["file"]: s["reason"] for s in data["skipped"]}
        self.assertIn(".hidden.txt", skipped)
        self.assertIn("tersembunyi", skipped[".hidden.txt"])

    def test_huge_analysis_id_is_404_not_500(self):
        self.assertIsNone(tools.get_analysis(10 ** 30))
        status, body = self._request(
            "GET", "/api/library/analysis?id=" + "9" * 26)
        self.assertEqual(status, 404, body)
        self.assertIn("tidak ada analisis", json.loads(body)["error"])
        status, body = self._request(
            "GET", "/api/library/analysis?id=0")
        self.assertEqual(status, 404, body)

    def test_http10_connection_headers(self):
        # Plain HTTP/1.0: the connection closes, and the response
        # says so (audit #6 N-8, via the H-1 fix).
        sock = socket.create_connection(
            ("127.0.0.1", self.port), timeout=5)
        try:
            sock.sendall(b"GET /api/prompts HTTP/1.0\r\n"
                         b"Host: x\r\n\r\n")
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                head += chunk
        finally:
            sock.close()
        self.assertIn(b"Connection: close", head)
        # HTTP/1.0 with keep-alive: the reuse is honoured AND
        # announced.
        sock = socket.create_connection(
            ("127.0.0.1", self.port), timeout=5)
        try:
            sock.sendall(b"GET /api/prompts HTTP/1.0\r\n"
                         b"Host: x\r\nConnection: keep-alive\r\n\r\n")
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                head += chunk
        finally:
            sock.close()
        self.assertIn(b"Connection: keep-alive", head)


if __name__ == "__main__":
    unittest.main()
