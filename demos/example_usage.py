"""Example usage of academic-jargon-buster (standalone demo).

Run from the repo root:
    python3 demos/example_usage.py

Note: this demo uses the standalone jargon_buster.py in the repo root.
It does NOT import any `hermes_tools` package — no such import is
needed, and the earlier draft that used it would have failed with
ModuleNotFoundError. The Hermes skill itself lives in
skills/research/academic-jargon-buster/SKILL.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jargon_buster import find_terms, to_annotated_markdown, to_csv

TEXT = (
    "The renormalization group is a mathematical framework. "
    "In machine learning, gradient descent is used to train models, "
    "but overfitting remains a common problem."
)

if __name__ == "__main__":
    print("=== Terms found ===")
    for item in find_terms(TEXT):
        print(f"- {item['original']} ({item['field']}): {item['translation']}")

    print("\n=== Annotated Markdown ===")
    print(to_annotated_markdown(TEXT))

    print("=== CSV ===")
    print(to_csv(TEXT))
