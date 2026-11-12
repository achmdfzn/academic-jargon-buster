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

    def test_statistics_terms_detected_with_sources(self):
        # 10 statistics concepts (English + Indonesian), v1.16.1.
        field_terms = {
            "statistical significance": "Field 2018",
            "signifikansi statistik": "Field 2018",
            "p-value": "Field 2018",
            "nilai-p": "Field 2018",
            "correlation": "Field 2018",
            "korelasi": "Field 2018",
            "regression": "Field 2018",
            "regresi": "Field 2018",
            "standard deviation": "Field 2018",
            "standar deviasi": "Field 2018",
            "null hypothesis": "Field 2018",
            "hipotesis nol": "Field 2018",
            "confidence interval": "Field 2018",
            "interval kepercayaan": "Field 2018",
            "normality": "Ghozali 2018",
            "normalitas": "Ghozali 2018",
            "multicollinearity": "Ghozali 2018",
            "multikolinearitas": "Ghozali 2018",
            "autocorrelation": "Ghozali 2018",
            "autokorelasi": "Ghozali 2018",
        }
        stats = {t["term"] for t in list_terms(field="statistics")}
        self.assertEqual(stats, set(field_terms))
        for term, source in field_terms.items():
            found = find_terms(f"The study reports {term}.", field="statistics")
            self.assertEqual(len(found), 1, term)
            self.assertEqual(found[0]["term"], term)
            self.assertEqual(found[0]["field"], "statistics")
            self.assertIn(source, found[0]["source"])

    def test_null_hypothesis_wins_over_hypothesis(self):
        # Longest-first matching: "null hypothesis" claims the span,
        # the bare "hypothesis" entry must not double-flag it.
        terms = find_terms("We test the null hypothesis first.")
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]["term"], "null hypothesis")

    def test_statistics_paragraph_in_indonesian(self):
        text = (
            "Uji normalitas menunjukkan data berdistribusi normal. "
            "Korelasi antara variabel X dan Y memiliki signifikansi "
            "statistik dengan nilai-p 0,01. Analisis regresi juga "
            "menemukan multikolinearitas yang rendah dan tidak ada "
            "autokorelasi."
        )
        found = {t["term"] for t in find_terms(text)}
        for term in ("normalitas", "korelasi", "signifikansi statistik",
                     "nilai-p", "regresi", "multikolinearitas",
                     "autokorelasi"):
            self.assertIn(term, found, term)

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
                "The usability score was 82.5.")
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
