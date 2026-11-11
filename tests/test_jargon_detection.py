"""Tests for academic-jargon-buster (stdlib unittest, no dependencies).

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""

import csv
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jargon_buster import (
    _user_dictionary_path,
    find_terms,
    list_terms,
    to_annotated_markdown,
    to_csv,
    update_dictionary,
)


class TestJargonDetection(unittest.TestCase):
    def test_translates_renormalization_group(self):
        text = "The renormalization group is a mathematical framework."
        terms = find_terms(text, field="physics")
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]["original"].lower(), "renormalization group")
        self.assertIn("different scales", terms[0]["translation"])

    def test_translates_gradient_descent(self):
        terms = find_terms("We train with gradient descent.", field="machine-learning")
        self.assertEqual(len(terms), 1)
        self.assertIn("lowest point", terms[0]["translation"])

    def test_longest_term_wins(self):
        # 'stochastic gradient descent' must win over 'gradient descent'
        terms = find_terms("Use stochastic gradient descent for training.")
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]["term"], "stochastic gradient descent")

    def test_field_filter(self):
        text = "The renormalization group is a framework."
        self.assertEqual(find_terms(text, field="physics"), find_terms(text))
        self.assertEqual(find_terms(text, field="biology"), [])

    def test_no_jargon_returns_empty(self):
        self.assertEqual(find_terms("The cat sat on the mat."), [])

    def test_annotated_markdown_contains_translation(self):
        out = to_annotated_markdown(
            "The renormalization group is a mathematical framework."
        )
        self.assertIn("renormalization group", out)
        self.assertIn("different scales", out)

    def test_repeated_term_annotated_once_per_occurrence(self):
        text = "Gradient descent is used. Later, gradient descent appears again."
        out = to_annotated_markdown(text)
        # Regression: the second pass used to match inside the annotation
        # it had just inserted, producing a doubled explanation while the
        # second occurrence stayed bare.
        self.assertNotIn("downhill) (a step-by-step", out)
        self.assertEqual(out.lower().count("gradient descent ("), 2)
        self.assertIn("Later, gradient descent (", out)

    def test_csv_output(self):
        out = to_csv("We train with gradient descent.")
        rows = list(csv.DictReader(io.StringIO(out)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["term"], "gradient descent")
        self.assertEqual(rows[0]["field"], "machine-learning")

    def test_new_terms_peer_review_and_hypothesis(self):
        terms = find_terms("The paper passed peer review. Our hypothesis was confirmed.")
        found = {t["term"] for t in terms}
        self.assertIn("peer review", found)
        self.assertIn("hypothesis", found)

    def test_new_terms_methodology_and_research_types(self):
        text = "The methodology section describes qualitative research and quantitative research."
        found = {t["term"] for t in find_terms(text)}
        self.assertIn("methodology", found)
        self.assertIn("qualitative research", found)
        self.assertIn("quantitative research", found)

    def test_new_terms_sus_and_usability(self):
        text = ("We evaluated usability with the System Usability Scale (SUS). "
                "The usability score was 73.96.")
        found = {t["term"] for t in find_terms(text)}
        self.assertIn("system usability scale", found)
        self.assertIn("usability", found)
        # SUS source is the real Brooke 1996 paper, not invented
        sus = [t for t in find_terms(text) if t["term"] == "system usability scale"][0]
        self.assertIn("Brooke 1996", sus["source"])

    def test_new_terms_software_and_indonesian_aliases(self):
        text = ("Data diakses melalui Object Relational Mapping Prisma. "
                "Autentikasi dan hak akses berbasis peran ditangani NextAuth. "
                "Kuesioner memakai skala Likert 1-5.")
        found = {t["term"] for t in find_terms(text)}
        self.assertIn("object relational mapping", found)
        self.assertIn("autentikasi", found)
        self.assertIn("hak akses berbasis peran", found)
        self.assertIn("skala likert", found)

    def test_generic_word_framework_is_not_a_term(self):
        # "framework" alone is ordinary academic English ("mathematical
        # framework", "theoretical framework") — annotating every use
        # would be noise, so it is deliberately NOT in the dictionary.
        found = {t["term"] for t in find_terms(
            "The renormalization group is a mathematical framework.")}
        self.assertNotIn("framework", found)
        self.assertIn("renormalization group", found)

    def test_list_terms_includes_new_terms(self):
        terms = {t["term"] for t in list_terms()}
        self.assertGreaterEqual(len(terms), 13)
        self.assertIn("peer review", terms)

    def test_list_terms_field_filter(self):
        terms = {t["term"] for t in list_terms(field="general")}
        self.assertIn("peer review", terms)
        self.assertNotIn("gradient descent", terms)

    def test_update_dictionary_from_json(self):
        path = _user_dictionary_path()
        backup = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(
                    {"placebo effect": {
                        "explanation": "when a patient improves because they believe a treatment works, not because of the treatment itself",
                        "field": "biology",
                        "source": "Wikipedia",
                    }},
                    f,
                )
                tmp = f.name
            added = update_dictionary(tmp)
            self.assertEqual(added, ["placebo effect"])
            found = {t["term"] for t in find_terms("The placebo effect was strong.")}
            self.assertIn("placebo effect", found)
        finally:
            if backup is None:
                if os.path.exists(path):
                    os.remove(path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(backup)
            os.remove(tmp)


if __name__ == "__main__":
    unittest.main()
