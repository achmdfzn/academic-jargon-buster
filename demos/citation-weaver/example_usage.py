"""Example usage of citation-weaver (standalone demo).

Run from the repo root:
    python3 demos/example_usage.py

Uses the sample bibliography in demos/citation-weaver/references.json — four real,
verifiable references (Vaswani et al. 2017, Devlin et al. 2019,
Brown et al. 2020, Goodfellow et al. 2016). Never invent references:
a [cite:key] with no bibliography entry is marked PERLU RUJUKAN /
REFERENCE NEEDED instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from citation_weaver import load_references, weave

REFS = load_references(str(Path(__file__).resolve().parent / "references.json"))

TEXT_ID = "Model Transformer memperkenalkan attention [cite:vaswani2017]."
TEXT_EN = "The Transformer introduced attention [cite:vaswani2017]."

if __name__ == "__main__":
    print("=== Bahasa Indonesia — APA ===")
    out, _ = weave(TEXT_ID, REFS, style="apa", lang="id")
    print(out)
    print("=== English — IEEE ===")
    out, _ = weave(TEXT_EN, REFS, style="ieee", lang="en")
    print(out)
    print("=== Bahasa Indonesia — Kedokteran (Vancouver, rekomendasi jurusan) ===")
    out, _ = weave(TEXT_ID, REFS, style="vancouver", lang="id")
    print(out)
