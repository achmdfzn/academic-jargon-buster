"""Tests for academic-jargon-buster (stdlib unittest, no dependencies).

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""

import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jargon_buster import find_terms, to_annotated_markdown, to_csv


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

    def test_csv_output(self):
        out = to_csv("We train with gradient descent.")
        rows = list(csv.DictReader(io.StringIO(out)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["term"], "gradient descent")
        self.assertEqual(rows[0]["field"], "machine-learning")


if __name__ == "__main__":
    unittest.main()
