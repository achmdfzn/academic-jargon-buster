"""Tests for audit #7 (v1.27.4) fix round — v1.27.5.

Audit #7 (report: ~/workspace/your_files/audit-v1.27.4.md) found
0 blockers + 8 must-fix + 8 nice-to-have + 6 test gaps on v1.27.4.
This file pins every fix:

- H-4/H-6/H-7/H-8/N-2 (T-1): the lexical syllable pins — "raib"
  is ra·ib (2), KBBI does have the entry (the v1.27.4 CHANGELOG
  claim that it has none was wrong); 9 more KBBI-verified hiatus
  roots (pais, laun, saur, kaul, saut, pauk, taul, gaut, tais)
  plus the nasal remnants their derivatives need (aul, yaur,
  mauk, naul); English pins (chihuahua 3, arguing 3, interest 2,
  interested 3, adobe 3, phoebe 2, unscientific 5). NOT pinned as
  fixes: "gruel" 2 and "nescience" 2 — the audit's "want 1" /
  "want 3" were wrong (the majority of syllable dictionaries give
  2, the code already counts 2); "bauh", "maul", "maik" are not in
  KBBI at all and stay at the plain-rule count 1; "iou" is 3
  (Oxford /ˌaɪ əʊ ˈjuː/, Cambridge /ˌaɪ.əʊˈjuː/, WebDictionary
  3 syllables — audit #8 H-4 resolved the open item).
- N-1 (T-1): intro words (lihat juga, bandingkan, cf., lihat)
  after a separator in a multi-citation author-year group — but
  NOT at the start of a group: audit #6 pins "(lihat Field,
  2018)" as not a citation, and that negative still stands.
- H-5 (T-1): the humanize preview keeps abbreviation prefixes
  ("Dr. Budi …" no longer shows as "Budi …").
- H-1/H-2 (T-2): only real JSON true enables a flag; non-string
  text is rejected with 400.
- H-3 (T-5): generic error messages, no leaked Python/JSON
  decoder text.
- N-4 (T-3): _send_page sends the Connection header like
  _send_json (HTTP/1.0 keep-alive).
- N-5/N-6 (T-4): open_library(create=False) — only a truly
  missing file means "empty library"; a directory is corrupt
  (400); a 0-byte file self-heals on read like a save does.
- N-7 (T-4): id=+1 is accepted (id 1).
- N-8 (T-4): an unknown jargon field is 400.
- N-3: the inverted-index candidate finder returns exactly the
  positions the overlap gate would admit.
- T-6: analyze+save+surrogate answers 400 AND writes no row.

The server tests run on an ephemeral localhost port in a thread;
no external network is used (DOI verification stays off).
"""

import http.client
import json
import os
import random
import socket
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import academic_tools as tools
from academic_tools import (
    _gated_candidates,
    _json_flag,
    _json_text,
    _load_ui_references,
    _overlap_gate,
    _build_word_index,
    _count_syllables,
    _sentence_spans,
    audit_citations,
    find_terms,
    load_references,
    open_library,
    list_analyses,
    suggest_style_fixes,
)

TEXT = (
    "Metode penelitian ini memakai purposive sampling dan thematic analysis. "
    "Hasilnya sejalan dengan temuan sebelumnya [cite:devlin2019]."
)

LONG_TEXT = (
    "Metode penelitian ini menggunakan pendekatan kuantitatif. "
    "Data dikumpulkan melalui kuesioner yang disebarkan kepada responden. "
    "Hasil analisis menunjukkan hubungan yang signifikan antara variabel "
    "yang diteliti."
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


# ----------------------------------------------------------------------
# T-1: H-4/H-6/H-7/H-8/N-2 — the lexical syllable pins.
# ----------------------------------------------------------------------

class TestSyllablePinsAudit7(unittest.TestCase):
    """Audit #7 H-4/H-6/H-7/H-8/N-2. Every count below was verified
    against a dictionary before pinning (see the audit #7 research
    notes); the two audit claims that did NOT survive the check
    ("gruel" want 1, "nescience" want 3) are pinned at the correct
    2 in the guards, not at the audit's values."""

    # KBBI-verified hiatus roots (audit #7 H-4): ra·ib, pa·is,
    # la·un, sa·ur, ka·ul, sa·ut, pa·uk, ta·ul, ga·ut, ta·is.
    ID_NEW = {
        "raib": 2, "pais": 2, "laun": 2, "saur": 2, "kaul": 2,
        "saut": 2, "pauk": 2, "taul": 2, "gaut": 2, "tais": 2,
    }

    # Derivatives through the nasal-assimilation remnants
    # (me·nga·ul·kan, me·nya·ur, pe·ma·uk, me·na·ul — all KBBI)
    # and plain affix stripping.
    ID_DERIVATIVES = {
        "mengaulkan": 4, "menyaur": 3, "menyauri": 4,
        "pemauk": 3, "memauk": 3, "menaul": 3, "meraib": 3,
        "berkaul": 3, "kaulan": 3, "bersaur": 3, "berlaun": 3,
        "dipais": 3, "berpaut": 3, "mengais": 3,
    }

    # Guards: the diphthong rule must not break on these, and the
    # three rejected candidates stay at the plain-rule count.
    ID_GUARDS = {
        "memandai": 3, "mencintai": 3, "baik": 2, "koboi": 2,
        "boikot": 2,
        # Not in KBBI at all — deliberately NOT added, so the
        # plain rule counts them as 1.
        "bauh": 1, "maul": 1, "maik": 1,
    }

    # English pins (audit #7 H-6/H-7/H-8/N-2): chihuahua 3
    # (Chi-hua-hua), arguing 3 (ar-gu-ing), interest 2 /
    # interested 3 (the common reduced pronunciations, Cambridge
    # / Oxford), adobe 3, phoebe 2, unscientific 5.
    EN_NEW = {
        "chihuahua": 3, "chihuahuas": 3, "arguing": 3,
        "argued": 2, "argues": 2, "interest": 2, "interested": 3,
        "adobe": 3, "phoebe": 2, "unscientific": 5,
    }

    EN_GUARDS = {
        # Audit #7's "want 1" / "want 3" were wrong: the majority
        # of syllable dictionaries give 2 for both, and the code
        # already counts 2.
        "gruel": 2, "nescience": 2,
        # Audit #8 H-4: "iou" is 3 (Oxford, Cambridge,
        # WebDictionary) — the audit #7 open item is resolved.
        "iou": 3,
        # Audit #8 H-2: "management" is 3 (guarded "-ment"
        # rule); "element" still 3 (the "l" guard).
        "management": 3, "extraordinary": 6, "interesting": 4,
        "element": 3, "scientific": 4,
    }

    def test_indonesian_new_roots(self):
        for word, want in self.ID_NEW.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word), want)

    def test_indonesian_derivatives(self):
        for word, want in self.ID_DERIVATIVES.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word), want)

    def test_indonesian_guards(self):
        for word, want in self.ID_GUARDS.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word), want)

    def test_english_new_pins(self):
        for word, want in self.EN_NEW.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word, "en"), want)

    def test_english_guards(self):
        for word, want in self.EN_GUARDS.items():
            with self.subTest(word=word):
                self.assertEqual(_count_syllables(word, "en"), want)


# ----------------------------------------------------------------------
# T-1: N-1 — intro words in multi-citation author-year groups.
# ----------------------------------------------------------------------

class TestIntroCitationAudit7(unittest.TestCase):
    """Audit #7 N-1. Intro words are allowed only after ';' or ','
    inside a group — never at the start of a group (audit #6 pins
    "(lihat Field, 2018)" as not a citation)."""

    REFS = {
        "field2018": {"title": "T1", "authors": ["Field, Andy"],
                      "year": 2018},
        "creswell2018": {"title": "T2", "authors": ["Creswell, John"],
                         "year": 2018},
        "ghozali2018": {"title": "T3", "authors": ["Ghozali, Imam"],
                        "year": 2018},
    }

    CASES = [
        ("(Field, 2018; lihat juga Creswell, 2018)",
         ["field2018", "creswell2018"]),
        ("(Field, 2018; bandingkan Ghozali, 2018)",
         ["field2018", "ghozali2018"]),
        ("(Field, 2018; cf. Creswell, 2018)",
         ["field2018", "creswell2018"]),
        ("(Field, 2018; cf Creswell, 2018)",
         ["field2018", "creswell2018"]),
        ("(Field, 2018; lihat Creswell, 2018)",
         ["field2018", "creswell2018"]),
        ("(Field, 2018, lihat juga Creswell, 2018)",
         ["field2018", "creswell2018"]),
        ("(Field, 2018; Creswell, 2018)",
         ["field2018", "creswell2018"]),
        # Negatives: group-start intro is NOT a citation (audit #6),
        # a bare intro word matches nothing, an unlisted intro word
        # credits nothing, a wrong year still matches nothing.
        ("(lihat Field, 2018) bukan sitasi langsung.", []),
        ("(lihat juga Field, 2018)", []),
        ("(lihat, 2018)", []),
        ("(Field, 2018; kata lain Creswell, 2018)", ["field2018"]),
        ("(Smith, 2020; lihat juga Creswell, 2018)", ["creswell2018"]),
        ("(Field, 2019; lihat juga Creswell, 2018)", ["creswell2018"]),
    ]

    def test_intro_words(self):
        for text, want in self.CASES:
            with self.subTest(text=text):
                result = audit_citations(text, self.REFS)
                self.assertEqual(sorted(result["author_year"]),
                                 sorted(want))


# ----------------------------------------------------------------------
# T-1: H-5 — the humanize preview keeps abbreviation prefixes.
# ----------------------------------------------------------------------

class TestAbbreviationPreviewAudit7(unittest.TestCase):
    """Audit #7 H-5. _sentence_spans used to split on a naive
    [.!?]+ regex, so the preview showed "Budi melakukan …" for
    "Dr. Budi melakukan …" (the --apply path was always right).
    Spans and the preview now share the abbreviation-aware split."""

    def test_spans_keep_abbreviation(self):
        spans = _sentence_spans(
            "Dr. Budi melakukan pengukuran terhadap suhu ruangan. "
            "Ia pergi.")
        self.assertEqual(spans[0][2],
                         "Dr. Budi melakukan pengukuran terhadap suhu ruangan.")
        self.assertEqual(spans[1][2], "Ia pergi.")
        self.assertEqual(spans[0][1] - spans[0][0], len(spans[0][2]))

    def test_preview_keeps_dr_and_tn(self):
        for text in (
            "Dr. Budi melakukan pengukuran terhadap suhu ruangan.",
            "Tn. Hadi melakukan pengukuran terhadap suhu ruangan.",
        ):
            with self.subTest(text=text):
                result = suggest_style_fixes(text, lang="id")
                self.assertTrue(result["suggestions"])
                first = result["suggestions"][0]
                self.assertTrue(first["context"].startswith(
                    text.split()[0] + " " + text.split()[1]),
                    first["context"])
                self.assertTrue(first["fixed"].startswith(
                    text.split()[0] + " " + text.split()[1]),
                    first["fixed"])

    def test_quote_lowercase_is_one_span(self):
        spans = _sentence_spans(
            '"Dia berkata, \'Saya takut!\' sambil menangis." Ia pergi.')
        self.assertEqual(len(spans), 2)
        self.assertEqual(
            spans[0][2],
            '"Dia berkata, \'Saya takut!\' sambil menangis."')

    def test_dr_rer_nat_tradeoff_still_accepted(self):
        # Audit #6 t5 trade-off, unchanged: an unconditional
        # abbreviation at the very end of a sentence merges it
        # with the next one. Do not "fix" this.
        spans = _sentence_spans("Gelarnya Dr. rer. nat. Ia mengajar.")
        self.assertEqual(len(spans), 1)


# ----------------------------------------------------------------------
# T-2: H-1/H-2 — JSON flag and text validation.
# ----------------------------------------------------------------------

class TestJsonValidationAudit7(unittest.TestCase):
    """Audit #7 H-1/H-2. Only a real JSON true enables a flag;
    non-string text is rejected instead of str()-coerced."""

    def test_json_flag_only_real_true(self):
        self.assertTrue(_json_flag({"save": True}, "save"))
        for bad in ("true", "false", 1, 0, None, [], {}):
            with self.subTest(value=bad):
                self.assertFalse(_json_flag({"save": bad}, "save"))
        self.assertFalse(_json_flag({}, "save"))

    def test_json_text_rejects_non_string(self):
        for bad in (["a", "b"], {"a": 1}, True, 123, 1.5):
            with self.subTest(value=bad):
                with self.assertRaisesRegex(
                        ValueError, "text harus berupa string"):
                    _json_text({"text": bad})

    def test_json_text_empty_and_missing(self):
        for body in ({}, {"text": None}, {"text": ""}, {"text": "   "}):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, "teks kosong"):
                    _json_text(body)
        self.assertEqual(_json_text({"text": " isi "}), "isi")


# ----------------------------------------------------------------------
# T-5: H-3 — generic error messages.
# ----------------------------------------------------------------------

class TestCleanErrorsAudit7(unittest.TestCase):
    """Audit #7 H-3. No raw Python/JSON decoder message may leak
    to the API: refs_json problems answer with the fixed generic
    message."""

    def test_refs_json_non_string(self):
        for bad in (123, ["a"], {"a": 1}, True):
            with self.subTest(value=bad):
                with self.assertRaisesRegex(
                        ValueError, "bibliografi JSON tidak valid"):
                    _load_ui_references({"refs_json": bad})

    def test_refs_json_malformed(self):
        with self.assertRaisesRegex(
                ValueError, "bibliografi JSON tidak valid"):
            _load_ui_references({"refs_json": "{invalid"})
        with self.assertRaisesRegex(
                ValueError, "bibliografi JSON tidak valid"):
            _load_ui_references({"refs_json": "{invalid json"})

    def test_load_references_malformed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "refs.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{invalid")
            with self.assertRaisesRegex(
                    ValueError, "bibliografi JSON tidak valid"):
                load_references(path)
            with open(path, "wb") as f:
                f.write(b"\xff\xfe bukan utf-8")
            with self.assertRaisesRegex(
                    ValueError, "bibliografi JSON tidak valid"):
                load_references(path)


# ----------------------------------------------------------------------
# N-3: the inverted-index candidate finder == the overlap gate.
# ----------------------------------------------------------------------

class TestGateIndexEquivalenceAudit7(unittest.TestCase):
    """Audit #7 N-3. _overlap_gate is dead code (unused by
    find_duplicates since v1.27.2) but its docstring claim — that
    _gated_candidates returns exactly the pairs the gate would
    admit — is now locked by this equivalence test instead of
    deleting the gate."""

    VOCAB = ["data", "metode", "hasil", "analisis", "sampel",
             "teori", "model", "uji", "skala", "responden",
             "temuan", "variabel"]

    def _random_entries(self, rng, n):
        entries = []
        for i in range(n):
            words = set(rng.sample(
                self.VOCAB, rng.randint(1, 8)))
            entries.append((" ".join(sorted(words)),
                            " ".join(sorted(words)), words, None))
        return entries

    def test_equivalence_random(self):
        rng = random.Random(20261114)
        for _trial in range(200):
            entries = self._random_entries(rng, rng.randint(0, 12))
            index = _build_word_index(entries)
            short = [pos for pos, e in enumerate(entries)
                     if len(e[2]) < 3]
            query = set(rng.sample(self.VOCAB, rng.randint(1, 8)))
            min_pos = rng.randint(0, len(entries)) if entries else 0
            got = _gated_candidates(query, entries, index, short,
                                    min_pos=min_pos)
            want = [pos for pos in range(min_pos, len(entries))
                    if _overlap_gate(query, entries[pos][2])]
            self.assertEqual(got, want)

    def test_short_query_admits_everything(self):
        # Fewer than 3 unique words on the query side: the gate
        # always passes, so the index must return every position.
        entries = self._random_entries(random.Random(7), 6)
        index = _build_word_index(entries)
        short = [pos for pos, e in enumerate(entries)
                 if len(e[2]) < 3]
        self.assertEqual(
            _gated_candidates({"data", "metode"}, entries, index, short),
            list(range(len(entries))))

    def test_short_entry_always_included(self):
        # A one-word entry passes the gate against any query.
        entries = [("data", "data", {"data"}, None),
                   ("metode hasil analisis teori model uji",
                    "metode hasil analisis teori model uji",
                    {"metode", "hasil", "analisis", "teori", "model",
                     "uji"}, None)]
        index = _build_word_index(entries)
        got = _gated_candidates(
            {"sampel", "skala", "responden", "temuan"},
            entries, index, [0])
        self.assertEqual(got, [0])


# ----------------------------------------------------------------------
# T-4: N-5/N-6 — the read path of the library database.
# ----------------------------------------------------------------------

class TestDirectoryDbAudit7(unittest.TestCase):
    """Audit #7 N-5/N-6. open_library(create=False): only a truly
    missing file means "empty library" (FileNotFoundError). A
    directory at the path is corrupt (ValueError, -> 400), a
    0-byte file self-heals on read exactly as a save does, and
    wrong-schema / garbage files stay corrupt."""

    def _probe(self, setup):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "library.db")
        setup(path)
        return path

    def test_missing_file_is_empty_library(self):
        path = self._probe(lambda p: None)
        with self.assertRaisesRegex(FileNotFoundError, "pustaka belum ada"):
            open_library(path, create=False)

    def test_directory_is_corrupt_not_missing(self):
        path = self._probe(os.mkdir)
        with self.assertRaisesRegex(ValueError, "pustaka rusak"):
            open_library(path, create=False)

    def test_zero_byte_file_self_heals_on_read(self):
        path = self._probe(lambda p: open(p, "wb").close())
        conn = open_library(path, create=False)
        try:
            self.assertEqual(list_analyses(db=path), [])
        finally:
            conn.close()
        # The schema is now on disk, like a save would leave it.
        import sqlite3
        tables = sqlite3.connect(path).execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        self.assertGreaterEqual(tables, 3)

    def test_wrong_schema_and_garbage_stay_corrupt(self):
        def wrong_schema(p):
            import sqlite3
            c = sqlite3.connect(p)
            c.execute("CREATE TABLE analyses (id INTEGER)")
            c.commit()
            c.close()
        path = self._probe(wrong_schema)
        with self.assertRaisesRegex(ValueError, "pustaka rusak"):
            open_library(path, create=False)

        def garbage(p):
            with open(p, "wb") as f:
                f.write(b"\x00\x01\x02not sqlite" * 10)
        path = self._probe(garbage)
        with self.assertRaisesRegex(ValueError, "pustaka rusak"):
            open_library(path, create=False)


# ----------------------------------------------------------------------
# Live server: T-2, T-3, T-5, T-6, N-7, N-8.
# ----------------------------------------------------------------------

class TestServeAudit7(unittest.TestCase):
    """Audit #7 live-server tests. The library is pointed at a
    fresh temp file per test (patch.dict on ACADEMIC_LIBRARY_DB),
    so nothing touches the real ~/.academic-tools/library.db."""

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

    # -- T-2: bool flags and non-string text ----------------------

    def test_save_string_false_writes_no_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze",
                                        {"text": TEXT, "save": "false"})
            self.assertEqual(status, 200)
            self.assertNotIn("library_id", json.loads(body))
            self.assertEqual(tools.list_analyses(db=db), [])

    def test_save_string_true_writes_no_row(self):
        # A string "true" is not JSON true either.
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze",
                                        {"text": TEXT, "save": "true"})
            self.assertEqual(status, 200)
            self.assertNotIn("library_id", json.loads(body))
            self.assertEqual(tools.list_analyses(db=db), [])

    def test_save_number_writes_no_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, _ = _request(self.base, "POST", "/api/analyze",
                                     {"text": TEXT, "save": 1})
            self.assertEqual(status, 200)
            self.assertEqual(tools.list_analyses(db=db), [])

    def test_save_real_true_still_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze",
                                        {"text": TEXT, "save": True})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["library_id"], 1)
            self.assertEqual(len(tools.list_analyses(db=db)), 1)

    def test_duplicates_string_false_adds_no_key(self):
        status, body = _request(self.base, "POST", "/api/analyze",
                                {"text": TEXT, "duplicates": "false"})
        self.assertEqual(status, 200)
        self.assertNotIn("duplicates", json.loads(body))

    def test_non_string_text_is_400(self):
        for path, payload in (
            ("/api/analyze", {"text": ["a", "b"]}),
            ("/api/analyze", {"text": {"a": 1}}),
            ("/api/analyze", {"text": True}),
            ("/api/analyze", {"text": 123}),
            ("/api/humanize", {"text": ["a"]}),
            ("/api/jargon", {"text": {"a": 1}}),
            ("/api/cite", {"text": 42}),
            ("/api/detect", {"text": ["a"]}),
        ):
            with self.subTest(path=path, payload=payload):
                status, body = _request(self.base, "POST", path, payload)
                self.assertEqual(status, 400)
                self.assertIn("text harus berupa string", body)

    def test_humanize_apply_string_false_adds_no_fixed_text(self):
        status, body = _request(
            self.base, "POST", "/api/humanize",
            {"text": "Dr. Budi melakukan pengukuran.",
             "apply": "false"})
        self.assertEqual(status, 200)
        self.assertNotIn("fixed_text", json.loads(body))

    # -- T-3: _send_page Connection header -------------------------

    def test_page_http10_keep_alive_header(self):
        # Raw socket: HTTP/1.0 + Connection: keep-alive on the page
        # must answer with "Connection: keep-alive" (audit #7 N-4).
        host, port = self.server.server_address[:2]
        sock = socket.create_connection((host, port), timeout=10)
        try:
            sock.sendall(b"GET / HTTP/1.0\r\n"
                         b"Connection: keep-alive\r\n\r\n")
            raw = b""
            while b"\r\n\r\n" not in raw:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                raw += chunk
        finally:
            sock.close()
        head = raw.split(b"\r\n\r\n")[0].decode("latin-1")
        self.assertIn("Connection: keep-alive", head)

    def test_page_http11_is_200(self):
        status, _ = _request(self.base, "GET", "/")
        self.assertEqual(status, 200)

    # -- T-5: generic error messages on the API -------------------

    def test_refs_json_non_string_is_400_generic(self):
        for bad in (123, ["a"], {"a": 1}):
            with self.subTest(value=bad):
                status, body = _request(
                    self.base, "POST", "/api/analyze",
                    {"text": TEXT, "refs_json": bad})
                self.assertEqual(status, 400)
                self.assertIn("bibliografi JSON tidak valid", body)
                self.assertNotIn("must be str", body)
                self.assertNotIn("JSONDecodeError", body)

    def test_refs_json_malformed_is_400_generic(self):
        status, body = _request(
            self.base, "POST", "/api/analyze",
            {"text": TEXT, "refs_json": "{invalid"})
        self.assertEqual(status, 400)
        self.assertIn("bibliografi JSON tidak valid", body)
        self.assertNotIn("Expecting property name", body)

    def test_folder_upload_bad_utf8_message_is_generic(self):
        status, body = _request_multipart(self.base,
            "/api/analyze-folder", [
                ("refs", None, b"sample"),
                ("files", "bab1.txt", b"\xff\xfe rusak"),
            ])
        self.assertEqual(status, 200)
        res = json.loads(body)
        self.assertEqual(res["folder"]["files"][0]["error"],
                         "file bukan teks UTF-8 yang valid")

    # -- T-6: analyze+save+surrogate -> 400 AND no row ------------

    def test_analyze_save_surrogate_is_400_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(
                    self.base, "POST", "/api/analyze",
                    {"text": LONG_TEXT + " \ud800", "save": True})
            self.assertEqual(status, 400)
            self.assertIn("surrogate", body)
            self.assertEqual(tools.list_analyses(db=db), [])
            self.assertFalse(os.path.exists(db))

    # -- N-7: id=+1 ------------------------------------------------

    def test_library_analysis_plus_one(self):
        # Audit #8 N-2: the "+" must be URL-encoded (%2B) here.
        # A literal "+" in a query string decodes to a SPACE
        # (parse_qs), so "?id=+1" arrives as " 1" — and the
        # strict parser rightly rejects a space. The N-7
        # decision itself is unchanged: the VALUE "+1" is id 1.
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "library.db")
            with patch.dict(os.environ, {"ACADEMIC_LIBRARY_DB": db}):
                status, body = _request(self.base, "POST", "/api/analyze",
                                        {"text": TEXT, "save": True})
                self.assertEqual(status, 200)
                status, body = _request(
                    self.base, "GET", "/api/library/analysis?id=%2B1")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["analysis"]["id"], 1)
                for raw, want in (("abc", 400), ("1.5", 400),
                                  ("-1", 400), ("0", 404), ("%2B99", 404)):
                    status, _ = _request(
                        self.base, "GET",
                        f"/api/library/analysis?id={raw}")
                    self.assertEqual(status, want, raw)
                # A missing id is still 400, not 404.
                status, _ = _request(
                    self.base, "GET", "/api/library/analysis")
                self.assertEqual(status, 400)

    # -- N-8: unknown jargon field ---------------------------------

    def test_jargon_unknown_field_is_400(self):
        status, body = _request(self.base, "POST", "/api/jargon",
                                {"text": "uji validitas",
                                 "field": "bogus"})
        self.assertEqual(status, 400)
        self.assertIn("bidang tidak dikenal: bogus", body)
        status, body = _request(self.base, "POST", "/api/jargon",
                                {"text": "uji validitas", "field": 123})
        self.assertEqual(status, 400)
        status, body = _request(self.base, "POST", "/api/jargon",
                                {"text": "uji validitas",
                                 "field": ["a"]})
        self.assertEqual(status, 400)

    def test_jargon_known_field_still_works(self):
        status, body = _request(self.base, "POST", "/api/jargon",
                                {"text": "uji validitas",
                                 "field": "research-methods"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["count"], 1)
        status, body = _request(self.base, "POST", "/api/jargon",
                                {"text": "uji validitas"})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(json.loads(body)["count"], 1)


class TestServeDirectoryDbAudit7(unittest.TestCase):
    """Audit #7 N-5 (T-4) on the live server: a directory at the
    library path answers 400 on the read endpoints, not 200 with
    an empty library."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_dir = os.path.join(cls.tmp.name, "library.db")
        os.mkdir(cls.db_dir)
        cls._patch = patch.dict(
            os.environ, {"ACADEMIC_LIBRARY_DB": cls.db_dir})
        cls._patch.start()
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
        cls._patch.stop()
        cls.tmp.cleanup()

    def test_history_on_directory_db_is_400(self):
        status, body = _request(self.base, "GET", "/api/library/history")
        self.assertEqual(status, 400)
        self.assertIn("pustaka rusak", body)

    def test_stats_on_directory_db_is_400(self):
        status, body = _request(self.base, "GET", "/api/library/stats")
        self.assertEqual(status, 400)
        self.assertIn("pustaka rusak", body)


if __name__ == "__main__":
    unittest.main()
