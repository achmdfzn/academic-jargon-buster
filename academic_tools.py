#!/usr/bin/env python3
"""academic_tools — every feature of this repo in one file.

Pure Python, no dependencies. Copy this single file anywhere and it
works: a jargon translator, a citation weaver, thesis prompts, and an
interactive menu CLI (Claude-CLI style) on top of all three.

    python3 academic_tools.py                  # interactive menu (default)
    python3 academic_tools.py jargon ...       # straight to Jargon Buster
    python3 academic_tools.py cite ...         # straight to Citation Weaver
    python3 academic_tools.py prompts ...      # straight to Thesis Prompts
    python3 academic_tools.py detect ...        # straight to AI Detector

Jargon Buster: find known jargon in plain text and explain each term
in plain language, with provenance. 72 terms, fields from physics to
usability to software engineering, plus Indonesian aliases.

    python3 academic_tools.py jargon demos/jargon-buster/test_paper.txt
    python3 academic_tools.py jargon --text "The renormalization group ..." --field physics
    python3 academic_tools.py jargon --list-terms [--field general]
    python3 academic_tools.py jargon --update-dictionary --from new_terms.json

Citation Weaver: give it text with [cite:key] (or TeX \\cite{key})
markers plus a bibliography file, and it returns the text with
in-text citations plus a bibliography, in Indonesian or English.
6 styles (APA, MLA, Chicago, IEEE, Harvard, Vancouver), 21 majors
with a recommended style each.

    python3 academic_tools.py cite demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json --lang id
    python3 academic_tools.py cite demos/citation-weaver/example_en.txt --refs demos/citation-weaver/references.json --lang en --style ieee
    python3 academic_tools.py cite --text "... [cite:vaswani2017]." --refs demos/citation-weaver/references.json --jurusan Kedokteran

Reference lookup: fetch real metadata by DOI or title from Crossref
and OpenAlex, instead of typing bibliography JSON by hand.

    python3 academic_tools.py cite --lookup 10.1038/nature14539
    python3 academic_tools.py cite --lookup "Deep learning" --add-to my-refs.json
    python3 academic_tools.py cite --lookup 10.1038/nature14539 --key lecun2015 --add-to my-refs.json

One rule, everywhere in this file: NEVER invent a reference. A
[cite:key] with no bibliography entry is marked [PERLU RUJUKAN: key] /
[REFERENCE NEEDED: key], never filled in with a made-up paper.

Thesis Prompts: 18 ready-made prompt templates for writing a thesis,
from research roadmap to defense prep and publication. Pick one, fill
its placeholders with your own title, theory, method, and data, then
paste the result into the recommended AI tool.

    python3 academic_tools.py prompts --list
    python3 academic_tools.py prompts latar-belakang
    python3 academic_tools.py prompts roadmap --set judul="..." --set teori="..." --set metode="..." --set bulan=6 --set tanggal="11 November 2026"

Quality check: one pass over a manuscript — jargon, citation audit,
DOI verification, and a rule-based style check for stiff Indonesian
academic prose (light verbs, stacked connectors, passive pile-ups,
calqued relatives, flat sentence rhythm). One score 0-100, plus
recommendations. A style report, not a rewrite and not a detector
dodge: flagged patterns are suggestions for the author's own edit.

    python3 academic_tools.py analyze demos/citation-weaver/contoh_id.txt --refs demos/citation-weaver/references.json
    python3 academic_tools.py analyze --text "... [cite:devlin2019]." --refs demos/citation-weaver/references.json --json

Library: analysis history and a personal bibliography in one local
SQLite file (stdlib sqlite3, no account, no cloud). `analyze --save`
records a run; `library` lists past runs, shows one in detail, and
searches, imports, and exports references.

    python3 academic_tools.py analyze naskah.txt --refs my-refs.json --save
    python3 academic_tools.py library --history
    python3 academic_tools.py library --refs --search "deep learning"

AI Detector: a heuristic check whether a text reads like AI writing
(sentence-length variation, template phrases, lexical diversity,
repeated sentence starters). One AI score 0-100 with verdict bands —
an indication, never proof, so it must never be used to accuse anyone.

    python3 academic_tools.py detect naskah.txt
    python3 academic_tools.py detect --text "..." --lang en --json

Readability: the Flesch Reading Ease and Flesch-Kincaid Grade Level
for a text, with the standard Flesch bands. A pure formula — no
language model, no API — reported by `analyze` and by its own
subcommand. The formulas were calibrated for English, so on
Indonesian text the score is an indication, not a verdict.

    python3 academic_tools.py readability naskah.txt
    python3 academic_tools.py readability --text "..." --lang en --json

Local web UI: the same six tools in a browser page, served from
this file alone (stdlib http.server, no external resources).

    python3 academic_tools.py serve [--port 8000]   # then open http://127.0.0.1:8000/

The old entry points (jargon_buster.py, citation_weaver.py,
academic_cli.py, ai_detector.py, readability.py) still exist as thin wrappers around this file, so
existing commands, demos, and imports keep working.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import difflib
import hashlib
import http.server
import io
import json
import os
import re
import socket
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, quote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

__version__ = "1.27.5"
JARGON_VERSION = "1.0.9"
CITATION_VERSION = "1.5.7"
PROMPTS_VERSION = "1.1.0"
QUALITY_VERSION = "1.2.15"
DETECTOR_VERSION = "1.0.3"
READABILITY_VERSION = "1.0.4"
CLI_VERSION = "1.18.4"

# ======================================================================
# Jargon Buster
# ======================================================================
# term -> (plain-English explanation, field, source)
DICTIONARY = {
    "renormalization group": (
        "a collection of techniques for studying how a system changes "
        "when you look at it at different scales",
        "physics",
        "Wilson & Kogut 1974, 'The renormalization group and the ε expansion' (DOI 10.1016/0370-1573(74)90023-4)",
    ),
    "gradient descent": (
        "a step-by-step method for finding the lowest point of a curve "
        "by repeatedly moving downhill",
        "machine-learning",
        "Boyd & Vandenberghe 2004, 'Convex Optimization' (ISBN 978-0-521-83378-3)",
    ),
    "causal inference": (
        "figuring out whether one thing actually causes another, "
        "rather than just happening at the same time",
        "economics",
        "Pearl 2009, 'Causality' (2nd ed., ISBN 978-0-521-89560-6)",
    ),
    "polymorphism": (
        "one interface that can work with different kinds of objects, "
        "like one remote control working with different devices",
        "computer-science",
        "Cardelli & Wegner 1985, 'On understanding types, data abstraction, and polymorphism' (DOI 10.1145/6041.6042)",
    ),
    "mitosis": (
        "the process by which one cell divides into two identical cells, "
        "step by step",
        "biology",
        "Alberts et al. 2014, 'Molecular Biology of the Cell' (6th ed., ISBN 978-0-8153-4432-2)",
    ),
    "stochastic gradient descent": (
        "gradient descent that uses a small random sample of the data "
        "at each step instead of the whole dataset, to go faster",
        "machine-learning",
        "Robbins & Monro 1951, 'A Stochastic Approximation Method' (DOI 10.1214/aoms/1177729586)",
    ),
    "overfitting": (
        "when a model memorises its training examples so closely that "
        "it performs badly on new, unseen examples",
        "machine-learning",
        "Hastie, Tibshirani & Friedman 2009, 'The Elements of Statistical Learning' (2nd ed., ISBN 978-0-387-84857-0)",
    ),
    "heteroscedasticity": (
        "when the spread of errors in data is not constant, but changes "
        "across the range of values",
        "economics",
        "White 1980, 'A Heteroskedasticity-Consistent Covariance Matrix Estimator and a Direct Test for Heteroskedasticity' (DOI 10.2307/1912934)",
    ),
    "peer review": (
        "when other experts in the same field read and check a paper "
        "before it is published, to catch mistakes and judge its quality",
        "general",
        "Smith 2006, 'Peer review: a flawed process at the heart of science and journals' (PMID 16574968)",
    ),
    "hypothesis": (
        "a testable guess or proposed explanation that a study sets out "
        "to check with evidence",
        "general",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    # Added 2026-11-13 (audit #5, N-3): irregular English plural /
    # adjective forms as separate keys pointing at the same explanation
    # and source as the base form — the same alias mechanism as the
    # Indonesian keys ("skala likert", "studi kasus", ...).
    "hypotheses": (
        "a testable guess or proposed explanation that a study sets out "
        "to check with evidence",
        "general",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "methodology": (
        "the overall plan of how a study is done — what data is collected, "
        "how it is collected, and why that way",
        "general",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "methodologies": (
        "the overall plan of how a study is done — what data is collected, "
        "how it is collected, and why that way",
        "general",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "qualitative research": (
        "research that describes qualities, meanings, and experiences, "
        "usually with words rather than numbers",
        "general",
        "Creswell 2013, 'Qualitative Inquiry and Research Design' (3rd ed., ISBN 978-1-4129-9530-6)",
    ),
    "quantitative research": (
        "research that measures things with numbers and statistics, "
        "to find patterns and test relationships",
        "general",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    # Added 2026-11-11 from a real student abstract (management
    # information system, SUS evaluation). Indonesian aliases included
    # where the source text uses the Indonesian form.
    "system usability scale": (
        "a 10-question survey that measures how easy a system is to use; "
        "answers are scored and combined into one number from 0 to 100",
        "usability",
        "Brooke 1996, 'SUS: A quick and dirty usability scale'",
    ),
    "usability": (
        "how easy and pleasant a system is to use — whether people can "
        "do what they need quickly and without confusion",
        "usability",
        "ISO 9241-11",
    ),
    "object relational mapping": (
        "a technique that lets code treat database tables as ordinary "
        "objects instead of writing raw SQL",
        "software-engineering",
        "Fowler 2002, 'Patterns of Enterprise Application Architecture' (ISBN 978-0-321-12742-6)",
    ),
    "likert scale": (
        "a survey answer scale with ordered steps, usually 1 to 5, "
        "from 'strongly disagree' to 'strongly agree'",
        "research-methods",
        "Likert 1932, 'A technique for the measurement of attitudes'",
    ),
    "skala likert": (
        "a survey answer scale with ordered steps, usually 1 to 5, "
        "from 'strongly disagree' to 'strongly agree'",
        "research-methods",
        "Likert 1932, 'A technique for the measurement of attitudes'",
    ),
    "authentication": (
        "checking that a user really is who they claim to be, "
        "usually with a username and password",
        "software-engineering",
        "Needham & Schroeder 1978, 'Using encryption for authentication in large networks of computers' (DOI 10.1145/359657.359659)",
    ),
    "autentikasi": (
        "checking that a user really is who they claim to be, "
        "usually with a username and password",
        "software-engineering",
        "Needham & Schroeder 1978, 'Using encryption for authentication in large networks of computers' (DOI 10.1145/359657.359659)",
    ),
    "role-based access control": (
        "deciding what each user may do in a system based on their role, "
        "such as admin or member",
        "software-engineering",
        "Ferraiolo & Kuhn 1992, 'Role-based access control'",
    ),
    "hak akses berbasis peran": (
        "deciding what each user may do in a system based on their role, "
        "such as admin or member",
        "software-engineering",
        "Ferraiolo & Kuhn 1992, 'Role-based access control'",
    ),
    # Added 2026-11-11: 10 research-methods terms students meet in almost
    # every thesis. Sources verified the same day (Crossref/OpenAlex/web):
    # Creswell & Creswell 2018, Denzin 1978, Patton 2015, Braun & Clarke
    # 2006, Boote & Beile 2005. Indonesian aliases included where the
    # source text uses the Indonesian form.
    "validity": (
        "whether a test or study actually measures what it claims to measure, "
        "rather than something else",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "validitas": (
        "whether a test or study actually measures what it claims to measure, "
        "rather than something else",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "reliability": (
        "whether a test or study gives the same result when repeated "
        "under the same conditions",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "reliabilitas": (
        "whether a test or study gives the same result when repeated "
        "under the same conditions",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "triangulation": (
        "checking one finding with more than one method, data source, "
        "or viewpoint, so the result is more trustworthy",
        "research-methods",
        "Denzin 1978, 'The Research Act' (2nd ed.)",
    ),
    "triangulasi": (
        "checking one finding with more than one method, data source, "
        "or viewpoint, so the result is more trustworthy",
        "research-methods",
        "Denzin 1978, 'The Research Act' (2nd ed.)",
    ),
    "purposive sampling": (
        "choosing participants on purpose because they have the knowledge "
        "or experience the study needs, instead of picking at random",
        "research-methods",
        "Patton 2015, 'Qualitative Research & Evaluation Methods' (4th ed.)",
    ),
    "thematic analysis": (
        "a method for finding and describing patterns, called themes, "
        "across interview or written data",
        "research-methods",
        "Braun & Clarke 2006, 'Using thematic analysis in psychology'",
    ),
    "operational definition": (
        "a clear statement of exactly how a variable is measured "
        "or observed in a study",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "literature review": (
        "a survey of the research already done on a topic, showing "
        "what is known and where the gaps are",
        "research-methods",
        "Boote & Beile 2005, 'Scholars before researchers'",
    ),
    # Added 2026-11-12: 10 statistics terms students meet in almost
    # every quantitative thesis. Sources verified the same day (web):
    # Field 2018, Ghozali 2018. Indonesian aliases included where the
    # source text uses the Indonesian form. "variance" was left out
    # on purpose: before the start-boundary rule (audit #4, H-7) the
    # substring matcher would also match inside "covariance" and
    # explain the wrong concept. The exclusion was kept as decided.
    # The start-boundary rule now also stops "validity" inside
    # "invalidity" and "normality" inside "abnormality", while no
    # end-boundary rule is applied, so plurals such as
    # "correlations" keep matching.
    "statistical significance": (
        "when a result is unlikely to have happened by chance alone, "
        "so the study treats it as a real effect",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "signifikansi statistik": (
        "when a result is unlikely to have happened by chance alone, "
        "so the study treats it as a real effect",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "p-value": (
        "a number from 0 to 1 that measures how surprising the data "
        "would be if there were no real effect; below 0.05, the result "
        "is usually called significant",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "nilai-p": (
        "a number from 0 to 1 that measures how surprising the data "
        "would be if there were no real effect; below 0.05, the result "
        "is usually called significant",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "correlation": (
        "a measure of how two things move together — when one goes up, "
        "the other tends to go up or down — without proving that one "
        "causes the other",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "korelasi": (
        "a measure of how two things move together — when one goes up, "
        "the other tends to go up or down — without proving that one "
        "causes the other",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "regression": (
        "a method for predicting one value from others, by fitting a "
        "line or curve that best describes how they relate",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "regresi": (
        "a method for predicting one value from others, by fitting a "
        "line or curve that best describes how they relate",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "standard deviation": (
        "a number that says how spread out values are around their "
        "average — a small one means the values cluster close to "
        "the average",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "standar deviasi": (
        "a number that says how spread out values are around their "
        "average — a small one means the values cluster close to "
        "the average",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "null hypothesis": (
        "the starting assumption that there is no effect or no "
        "difference, which a study tries to disprove with evidence",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "hipotesis nol": (
        "the starting assumption that there is no effect or no "
        "difference, which a study tries to disprove with evidence",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "confidence interval": (
        "a range of values that probably contains the true value — "
        "a 95% interval means the method would capture the true value "
        "in 95 out of 100 repeats",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "interval kepercayaan": (
        "a range of values that probably contains the true value — "
        "a 95% interval means the method would capture the true value "
        "in 95 out of 100 repeats",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "normality": (
        "whether data follows the bell-shaped normal distribution, "
        "which many statistical tests assume before they can be trusted",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "normalitas": (
        "whether data follows the bell-shaped normal distribution, "
        "which many statistical tests assume before they can be trusted",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "multicollinearity": (
        "when two or more predictors in a regression are so strongly "
        "related to each other that their separate effects cannot be "
        "told apart",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "multikolinearitas": (
        "when two or more predictors in a regression are so strongly "
        "related to each other that their separate effects cannot be "
        "told apart",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "autocorrelation": (
        "when the errors in a regression are related to each other "
        "over time or order, instead of being independent",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "autokorelasi": (
        "when the errors in a regression are related to each other "
        "over time or order, instead of being independent",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    # Added 2026-11-13: 20 more terms (9 research-methods, 11 statistics)
    # students meet in almost every thesis. Sources verified the same
    # day (web): Glaser & Strauss 1967, Yin 2018, Moustakas 1994,
    # Krueger & Casey 2014, Creswell & Creswell 2018, Field 2018,
    # Ghozali 2018; Cronbach 1951 was verified too (named in the uji
    # reliabilitas explanation). Indonesian aliases included where the
    # source text uses the Indonesian form. "uji t" was left out on
    # purpose: the substring matcher would also match inside "uji
    # terhadap" and explain the wrong concept; "sample" was left out
    # for the same reason ("example" contains "sample").
    "data saturation": (
        "the point in qualitative research where new interviews stop "
        "adding new ideas, so the researcher stops collecting data",
        "research-methods",
        "Glaser & Strauss 1967, 'The Discovery of Grounded Theory'",
    ),
    "saturasi data": (
        "the point in qualitative research where new interviews stop "
        "adding new ideas, so the researcher stops collecting data",
        "research-methods",
        "Glaser & Strauss 1967, 'The Discovery of Grounded Theory'",
    ),
    "case study": (
        "an in-depth study of one case — a person, group, or event — "
        "in its real-life setting, using several kinds of evidence",
        "research-methods",
        "Yin 2018, 'Case Study Research and Applications' (6th ed.)",
    ),
    # Audit #5, N-3: irregular plural alias of "case study" (same
    # explanation and source as the base form).
    "case studies": (
        "an in-depth study of one case — a person, group, or event — "
        "in its real-life setting, using several kinds of evidence",
        "research-methods",
        "Yin 2018, 'Case Study Research and Applications' (6th ed.)",
    ),
    "studi kasus": (
        "an in-depth study of one case — a person, group, or event — "
        "in its real-life setting, using several kinds of evidence",
        "research-methods",
        "Yin 2018, 'Case Study Research and Applications' (6th ed.)",
    ),
    "phenomenology": (
        "a qualitative approach that studies how people experience a "
        "phenomenon, to describe what that experience is like for them",
        "research-methods",
        "Moustakas 1994, 'Phenomenological Research Methods'",
    ),
    # Audit #5, N-3: adjective-form alias of "phenomenology" (same
    # explanation and source as the base form).
    "phenomenological": (
        "a qualitative approach that studies how people experience a "
        "phenomenon, to describe what that experience is like for them",
        "research-methods",
        "Moustakas 1994, 'Phenomenological Research Methods'",
    ),
    "fenomenologi": (
        "a qualitative approach that studies how people experience a "
        "phenomenon, to describe what that experience is like for them",
        "research-methods",
        "Moustakas 1994, 'Phenomenological Research Methods'",
    ),
    "focus group discussion": (
        "a guided group discussion with a small set of participants, "
        "used to hear their views and how they react to each "
        "other's opinions",
        "research-methods",
        "Krueger & Casey 2014, 'Focus Groups' (5th ed.)",
    ),
    "diskusi kelompok terfokus": (
        "a guided group discussion with a small set of participants, "
        "used to hear their views and how they react to each "
        "other's opinions",
        "research-methods",
        "Krueger & Casey 2014, 'Focus Groups' (5th ed.)",
    ),
    "uji validitas": (
        "the procedure for checking whether each item of a questionnaire "
        "really measures what it should, usually by correlating each "
        "item score with the total score",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "uji reliabilitas": (
        "the procedure for checking whether an instrument gives "
        "consistent results, usually with Cronbach's alpha, a number "
        "that is typically between 0 and 1 but can be negative, "
        "where higher means more consistent",
        "research-methods",
        "Creswell & Creswell 2018, 'Research Design' (5th ed., ISBN 978-1-5063-8670-6)",
    ),
    "t-test": (
        "a test for whether the averages of two groups are really "
        "different, or whether one average differs from a known value",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "anova": (
        "a test for whether the averages of three or more groups are "
        "really different from each other",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "analisis varians": (
        "a test for whether the averages of three or more groups are "
        "really different from each other",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "chi-square test": (
        "a test for whether two categorical variables are related, by "
        "comparing the counts actually observed with the counts "
        "expected if there were no relation",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "uji chi-square": (
        "a test for whether two categorical variables are related, by "
        "comparing the counts actually observed with the counts "
        "expected if there were no relation",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "coefficient of determination": (
        "a number from 0 to 1, usually written R-squared, that says "
        "how much of the variation in an outcome a regression model "
        "explains",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "koefisien determinasi": (
        "a number from 0 to 1, usually written R-squared, that says "
        "how much of the variation in an outcome a regression model "
        "explains",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "uji normalitas": (
        "the procedure for checking whether data follows the "
        "bell-shaped normal distribution, usually with the "
        "Kolmogorov-Smirnov or Shapiro-Wilk test",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "uji homogenitas": (
        "the procedure for checking whether several groups have similar "
        "variances, usually with Levene's test, before comparing "
        "their averages",
        "statistics",
        "Ghozali 2018, 'Aplikasi Analisis Multivariate Dengan Program IBM SPSS 25' (9th ed.)",
    ),
    "descriptive statistics": (
        "numbers that describe a dataset as it is — averages, spreads, "
        "and frequencies — without testing hypotheses or generalizing "
        "beyond it",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
    "statistik deskriptif": (
        "numbers that describe a dataset as it is — averages, spreads, "
        "and frequencies — without testing hypotheses or generalizing "
        "beyond it",
        "statistics",
        "Field 2018, 'Discovering Statistics Using IBM SPSS Statistics' (5th ed.)",
    ),
}


def _user_dictionary_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary.json")


def load_dictionary():
    """Built-in dictionary plus user-added terms from dictionary.json."""
    merged = dict(DICTIONARY)
    path = _user_dictionary_path()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            extra = json.load(f)
        for term, value in extra.items():
            merged[term.lower()] = (
                value["explanation"],
                value.get("field", "general"),
                value.get("source", "user-added"),
            )
    return merged


def list_terms(field: str | None = None):
    """All dictionary terms, optionally filtered by field."""
    items = sorted(load_dictionary().items())
    if field:
        items = [(t, v) for t, v in items if v[1] == field]
    return [{"term": t, "translation": v[0], "field": v[1], "source": v[2]} for t, v in items]


def update_dictionary(from_file: str, field: str | None = None):
    """Add terms from a JSON file into dictionary.json. Returns added terms.

    File format: {"term": {"explanation": "...", "field": "...",
    "source": "..."}}. Entries without an explanation are skipped.
    """
    with open(from_file, encoding="utf-8") as f:
        incoming = json.load(f)
    path = _user_dictionary_path()
    existing = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    added = []
    for term, value in incoming.items():
        term = term.lower()
        if not isinstance(value, dict) or not value.get("explanation"):
            continue
        if field and value.get("field", "general") != field:
            continue
        existing[term] = {
            "explanation": value["explanation"],
            "field": value.get("field", "general"),
            "source": value.get("source", "user-added"),
        }
        added.append(term)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return sorted(added)


# Characters allowed immediately before a dictionary match (H-7):
# whitespace is checked with str.isspace(); these are the opening
# brackets and quotes, plus punctuation that separates two terms in
# running text (", ; : / ? !" and the dashes, the ellipsis, and the
# closing brackets — a term can follow them with no space, as in
# "korelasi!validitas" or "“korelasi”"). Curly quotes (“”‘’«»)
# join the set because Word/Google Docs produce them by default.
# A period is deliberately NOT in the set, so ".anova" still does
# not match (audit #4), and a hyphen still blocks, so
# "pre-t-test" stays empty.
_MATCH_START_CHARS = "([{'\",;:/?!—–“”‘’«»…])"


def _iter_matches(text: str, field: str | None = None):
    """One dictionary match per occurrence, longest term first.

    Terms are tried longest-first, so 'stochastic gradient descent'
    claims its span before 'gradient descent' can. Case-insensitive;
    spans that overlap an already-claimed span are skipped.

    A match must START at a word boundary: the character before it
    is the start of the string, whitespace, or an opening bracket
    or quote. That stops 't-test' matching inside 'contest-test'
    and 'anova' inside 'Rekanova'. There is deliberately NO
    end-boundary rule, so suffixed forms keep matching
    ('validitasnya' -> 'validitas', 'correlations' -> 'correlation'):
    a term followed by extra letters is therefore indistinguishable
    from a term with a suffix, so 'anovanova' still matches once,
    at position 0 — a known limitation, not a bug that can be fixed
    without losing plurals and suffixed forms.
    """
    dictionary = load_dictionary()
    seen_spans = []
    for term in sorted(dictionary, key=len, reverse=True):
        explanation, term_field, source = dictionary[term]
        if field and term_field != field:
            continue
        for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            if m.start() and not (
                    text[m.start() - 1].isspace()
                    or text[m.start() - 1] in _MATCH_START_CHARS):
                continue
            span = (m.start(), m.end())
            if any(s < span[1] and span[0] < e for s, e in seen_spans):
                continue
            seen_spans.append(span)
            yield {
                "original": m.group(0),
                "term": term,
                "translation": explanation,
                "field": term_field,
                "source": source,
                "confidence": 1.0,  # exact dictionary match
                "start": span[0],
                "end": span[1],
            }


def find_terms(text: str, field: str | None = None):
    """Return list of dicts for each dictionary term found in text.

    Longest terms first, so 'stochastic gradient descent' wins over
    'gradient descent' when both match. Case-insensitive. Results are
    ordered by position in the text.
    """
    matches = sorted(_iter_matches(text, field=field), key=lambda d: d["start"])
    return [
        {k: v for k, v in item.items() if k not in ("start", "end")}
        for item in matches
    ]


def to_annotated_markdown(text: str, field: str | None = None) -> str:
    """Original text with jargon followed by its plain explanation."""
    matches = sorted(_iter_matches(text, field=field), key=lambda d: d["start"])
    if not matches:
        return text + "\n\n_No known jargon terms found in the dictionary._\n"
    # Splice by span, so each occurrence is annotated exactly once and
    # an inserted explanation can never be matched again.
    parts = []
    cursor = 0
    for item in matches:
        parts.append(text[cursor:item["end"]])
        parts.append(f" ({item['translation']})")
        cursor = item["end"]
    parts.append(text[cursor:])
    lines = ["# Annotated output\n", "".join(parts), "\n## Terms found\n"]
    for item in matches:
        lines.append(
            f"- **{item['original']}** ({item['field']}) — "
            f"{item['translation']} — _source: {item['source']}_"
        )
    return "\n".join(lines) + "\n"


def to_csv(text: str, field: str | None = None) -> str:
    """Term list as CSV: term, definition, field, confidence, source."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["term", "definition", "field", "confidence", "source"])
    for item in find_terms(text, field=field):
        w.writerow(
            [item["term"], item["translation"], item["field"],
             item["confidence"], item["source"]]
        )
    return buf.getvalue()


def jargon_main(argv=None, *, version=None) -> int:
    p = argparse.ArgumentParser(description="Translate academic jargon to plain English.")
    p.add_argument("input", nargs="?", help="plain-text file to translate")
    p.add_argument("--text", help="translate this text instead of a file")
    p.add_argument("--field", help="only use terms from this field, e.g. physics")
    p.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    p.add_argument("--list-terms", action="store_true", help="list dictionary terms and exit")
    p.add_argument("--update-dictionary", action="store_true",
                   help="add terms from --from <json file> to dictionary.json")
    p.add_argument("--from", dest="from_file", help="JSON file of terms for --update-dictionary")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {version or __version__}")
    args = p.parse_args(argv)

    if args.list_terms:
        for item in list_terms(field=args.field):
            print(f"{item['term']} ({item['field']}) — {item['translation']} — {item['source']}")
        return 0

    if args.update_dictionary:
        if not args.from_file:
            for item in list_terms(field=args.field):
                print(f"{item['term']} ({item['field']}) — {item['translation']} — {item['source']}")
            print("\nTo add terms: --update-dictionary --from new_terms.json", file=sys.stderr)
            return 0
        added = update_dictionary(args.from_file, field=args.field)
        if added:
            print(f"Added {len(added)} term(s): {', '.join(added)}")
        else:
            print("No terms added (check the file format and --field filter).")
        return 0

    if args.text:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")

    if args.format == "csv":
        sys.stdout.write(to_csv(text, field=args.field))
    else:
        sys.stdout.write(to_annotated_markdown(text, field=args.field))
    return 0


# ======================================================================
# Citation Weaver
# ======================================================================
STYLES = ["apa", "mla", "chicago", "ieee", "harvard", "vancouver"]

# Jurusan (majors) -> recommended citation style.
# A recommendation, not a rule: --style always overrides it.
# id: Indonesian name, en: English name, style: recommended style.
DISCIPLINES = [
    {"id": "Kedokteran", "en": "Medicine", "style": "vancouver"},
    {"id": "Keperawatan", "en": "Nursing", "style": "apa"},
    {"id": "Farmasi", "en": "Pharmacy", "style": "vancouver"},
    {"id": "Kesehatan Masyarakat", "en": "Public Health", "style": "apa"},
    {"id": "Psikologi", "en": "Psychology", "style": "apa"},
    {"id": "Hukum", "en": "Law", "style": "chicago"},
    {"id": "Ekonomi", "en": "Economics", "style": "harvard"},
    {"id": "Manajemen", "en": "Management", "style": "apa"},
    {"id": "Akuntansi", "en": "Accounting", "style": "apa"},
    {"id": "Teknik Informatika", "en": "Informatics", "style": "ieee"},
    {"id": "Ilmu Komputer", "en": "Computer Science", "style": "ieee"},
    {"id": "Teknik Elektro", "en": "Electrical Engineering", "style": "ieee"},
    {"id": "Teknik Sipil", "en": "Civil Engineering", "style": "ieee"},
    {"id": "Teknik Mesin", "en": "Mechanical Engineering", "style": "ieee"},
    {"id": "Pendidikan", "en": "Education", "style": "apa"},
    {"id": "Sastra Inggris", "en": "English Literature", "style": "mla"},
    {"id": "Bahasa Indonesia", "en": "Indonesian Language", "style": "mla"},
    {"id": "Sejarah", "en": "History", "style": "chicago"},
    {"id": "Sosiologi", "en": "Sociology", "style": "apa"},
    {"id": "Biologi", "en": "Biology", "style": "apa"},
    {"id": "Fisika", "en": "Physics", "style": "ieee"},
]

MESSAGES = {
    "id": {
        "references_heading": "Daftar Pustaka",
        "missing": "PERLU RUJUKAN",
        "missing_note": "Rujukan berikut tidak ditemukan di bibliografi — jangan dikarang, tambahkan datanya dulu:",
        "no_citations": "Tidak ada sitasi [cite:key] yang ditemukan di teks.",
    },
    "en": {
        "references_heading": "References",
        "missing": "REFERENCE NEEDED",
        "missing_note": "These references were not found in the bibliography — do not invent them, add their data first:",
        "no_citations": "No [cite:key] citations found in the text.",
    },
}


def style_for_discipline(name: str):
    """Recommended style for a jurusan, by Indonesian or English name."""
    needle = name.strip().lower()
    for d in DISCIPLINES:
        if needle in (d["id"].lower(), d["en"].lower()):
            return d["style"]
    return None


def _validate_references(data) -> dict:
    """Validate a parsed bibliography ({key: ref}) in place.

    Top level must be a dict; every value a dict; 'authors', when
    present, must be a list or tuple of strings (a lone string is
    normalized to [string]); 'title', when present, must be a string.
    Anything else raises ValueError with a plain message — never a
    bare KeyError/TypeError downstream. Returns the (normalized) dict.
    """
    if not isinstance(data, dict):
        raise ValueError(
            "bibliografi tidak valid: harus berupa objek "
            "{kunci: referensi}, bukan "
            + ("daftar" if isinstance(data, list) else "nilai tunggal"))
    for key, ref in data.items():
        if not isinstance(ref, dict):
            raise ValueError(
                f"bibliografi tidak valid: referensi '{key}' "
                "harus berupa objek")
        if "authors" in ref:
            authors = ref["authors"]
            if isinstance(authors, str):
                ref["authors"] = [authors]
            elif isinstance(authors, (list, tuple)):
                for a in authors:
                    if not isinstance(a, str):
                        raise ValueError(
                            f"bibliografi tidak valid: 'authors' "
                            f"referensi '{key}' harus berupa daftar "
                            "nama (string)")
                ref["authors"] = list(authors)
            else:
                raise ValueError(
                    f"bibliografi tidak valid: 'authors' referensi "
                    f"'{key}' harus berupa daftar nama")
        if "title" in ref and ref["title"] is not None \
                and not isinstance(ref["title"], str):
            raise ValueError(
                f"bibliografi tidak valid: 'title' referensi '{key}' "
                "harus berupa teks")
    return data


def load_references(path: str):
    """Load a bibliography JSON file: {"key": {author fields...}}.

    Authors are stored as ["Family, Given", ...].

    Raises ValueError with a plain message when the file is not
    valid JSON or the data is not a well-formed {key: ref} object —
    and when the file does not exist at all, so `cite` (every
    branch: weave, --audit, --verify, --export-bibtex/ris) exits 1
    with "File tidak ditemukan" instead of a FileNotFoundError
    traceback (audit #6 H-11).
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File tidak ditemukan: {path}") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Audit #7 H-3: JSONDecodeError is a ValueError, so a
        # malformed file used to surface the raw decoder message
        # ("Expecting property name ... (char 1)") to the caller.
        # Same for a file that is not valid UTF-8. Both are the
        # same plain message now.
        raise ValueError("bibliografi JSON tidak valid") from None
    return _validate_references(data)


# ======================================================================
# Reference lookup (OpenAlex / Crossref)
# ======================================================================
# Fetch real reference metadata by DOI or title, so a bibliography can
# be built without typing JSON by hand. Crossref is free and needs no
# key. OpenAlex has required a key for production use since February
# 2026: the key is free, every key gets about $1 of free usage per day,
# a single lookup by DOI or ID is free, and a search costs roughly
# $0.001. The key is read from OPENALEX_API_KEY. Crossref is tried
# first for DOIs; OpenAlex backs it up and powers title search. A
# polite mailto in the User-Agent puts requests in the APIs' polite
# pools. No data is ever invented: a failed lookup is an error, never
# a guess.
LOOKUP_USER_AGENT = (
    f"academic-jargon-buster/{__version__} (mailto:achmddfzn@proton.me)"
)
CROSSREF_URL = "https://api.crossref.org/works/{doi}"
OPENALEX_DOI_URL = "https://api.openalex.org/works/https://doi.org/{doi}"
OPENALEX_SEARCH_URL = "https://api.openalex.org/works?search={q}&per-page=1"


class LookupError(Exception):
    """A reference lookup failed (not found, rate-limited, offline)."""


class LookupNotFoundError(LookupError):
    """A lookup that answered 404: the DOI / work does not exist.

    Raised (instead of a plain LookupError) so callers can tell a
    confirmed 404 from a network error without grepping the
    message for "404" — see _doi_source_status.
    """


def _lookup_get(url: str, timeout: int = 15):
    """GET JSON from a lookup API. Raises LookupError on any failure."""
    req = urllib.request.Request(url, headers={"User-Agent": LOOKUP_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise LookupNotFoundError("not found (HTTP 404)")
        if e.code in (401, 403):
            raise LookupError(
                "API access denied (HTTP %d). OpenAlex has required a free API "
                "key since February 2026: create one at "
                "https://openalex.org/settings/api and set OPENALEX_API_KEY."
                % e.code
            )
        if e.code == 429:
            raise LookupError(
                "rate limited by the API (HTTP 429). OpenAlex allows about $1 "
                "of free usage per key per day; try again later, or set "
                "OPENALEX_API_KEY (free at https://openalex.org/settings/api) "
                "to use your own daily allowance."
            )
        raise LookupError(f"lookup failed (HTTP {e.code})")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LookupError(f"lookup failed: {e}")


def _crossref_type(kind: str) -> str:
    return {
        "journal-article": "article",
        "proceedings-article": "conference",
        "book-chapter": "chapter",
        "book": "book",
        "monograph": "book",
    }.get(kind, "article")


def _crossref_to_ref(msg: dict) -> dict:
    """Crossref work message -> repo reference dict."""
    title = (msg.get("title") or [""])[0]
    authors = []
    for a in msg.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        authors.append(f"{family}, {given}" if given else family)
    venue = (msg.get("container-title") or [""])[0]
    year = None
    for key in ("published", "issued", "created"):
        parts = (msg.get(key) or {}).get("date-parts")
        if parts and parts[0]:
            year = parts[0][0]
            break
    ref = {
        "authors": authors,
        "title": title,
        "type": _crossref_type(msg.get("type", "")),
        "venue": venue,
        "year": year,
    }
    if msg.get("DOI"):
        ref["doi"] = msg["DOI"]
    return ref


def _openalex_type(kind: str) -> str:
    return {
        "article": "article",
        "proceedings-article": "conference",
        "book-chapter": "chapter",
        "book": "book",
    }.get(kind, "article")


def _openalex_to_ref(work: dict) -> dict:
    """OpenAlex work -> repo reference dict."""
    title = work.get("title") or work.get("display_name") or ""
    authors = []
    for a in work.get("authorships", []):
        name = (a.get("author") or {}).get("display_name", "")
        if not name:
            continue
        parts = name.split()
        if len(parts) > 1:
            authors.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
        else:
            authors.append(name)
    source = (work.get("primary_location") or {}).get("source") or {}
    ref = {
        "authors": authors,
        "title": title,
        "type": _openalex_type(work.get("type", "")),
        "venue": source.get("display_name", ""),
        "year": work.get("publication_year"),
    }
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    if doi:
        ref["doi"] = doi
    return ref


def _openalex_url(url: str) -> str:
    """Append the OpenAlex API key when OPENALEX_API_KEY is set."""
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if not key:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}api_key={key}"


def fetch_reference_by_doi(doi: str) -> dict:
    """Fetch one reference by DOI: Crossref first, OpenAlex as backup."""
    doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    if not doi:
        raise LookupError("empty DOI")
    try:
        msg = _lookup_get(CROSSREF_URL.format(doi=quote(doi, safe="/")))
        return _crossref_to_ref(msg["message"])
    except LookupError:
        pass  # fall through to OpenAlex
    work = _lookup_get(_openalex_url(OPENALEX_DOI_URL.format(doi=quote(doi, safe="/"))))
    return _openalex_to_ref(work)


def search_reference_by_title(title: str) -> dict:
    """Fetch the best OpenAlex match for a title."""
    title = title.strip()
    if not title:
        raise LookupError("empty title")
    data = _lookup_get(_openalex_url(OPENALEX_SEARCH_URL.format(q=quote(title))))
    results = data.get("results") or []
    if not results:
        raise LookupError(f"no match found for title: {title}")
    return _openalex_to_ref(results[0])


def lookup_reference(query: str) -> dict:
    """Fetch one reference by DOI or title.

    A query that looks like a DOI (starts with 10. or is a doi.org URL)
    goes to fetch_reference_by_doi; anything else is a title search.
    """
    q = query.strip()
    if q.startswith("10.") or "doi.org/" in q:
        return fetch_reference_by_doi(q)
    return search_reference_by_title(q)


def _doi_source_status(url: str) -> str:
    """One DOI lookup -> 'ok', 'not-found', or 'error' (never invented)."""
    try:
        _lookup_get(url)
        return "ok"
    except LookupNotFoundError:
        return "not-found"
    except LookupError:
        return "error"


def _doi_verdict(entry: dict) -> str:
    """Combine both sources into ok / missing / unverified / no-doi.

    A DOI only needs to exist in one source to be real: arXiv and
    datasets register with DataCite, not Crossref. 'missing' needs
    a checked source to say 404 with no source erroring — so a
    Crossref 404 is already 'missing' when OpenAlex was merely
    skipped for lack of a key. 'unverified' is for when a source
    errored, or when nothing was actually checked. Scoring treats
    'unverified' as half credit (12.5 per DOI): a DOI that could
    not be checked is not the same as a confirmed fake.
    """
    if not entry["doi"]:
        return "no-doi"
    statuses = (entry["crossref"], entry["openalex"])
    checked = [s for s in statuses if s in ("ok", "not-found")]
    if "ok" in checked:
        return "ok"
    if "not-found" in checked and "error" not in statuses:
        return "missing"
    return "unverified"


def verify_reference_dois(references: dict) -> dict:
    """Check every reference DOI against Crossref and OpenAlex.

    Returns {key: {doi, crossref, openalex, verdict}}. OpenAlex has
    required a key since February 2026; without OPENALEX_API_KEY its
    column is 'skipped' — but a Crossref 404 is already 'missing'
    then (a skipped source does not shield a checked 404); only a
    source error, or nothing checked at all, leaves 'unverified'.
    """
    openalex_available = bool(os.environ.get("OPENALEX_API_KEY", "").strip())
    result = {}
    for key, ref in references.items():
        doi = str(ref.get("doi") or "").strip()
        entry = {"doi": doi, "crossref": "no-doi", "openalex": "no-doi"}
        if doi:
            entry["crossref"] = _doi_source_status(
                CROSSREF_URL.format(doi=quote(doi, safe="/")))
            if openalex_available:
                entry["openalex"] = _doi_source_status(
                    _openalex_url(
                        OPENALEX_DOI_URL.format(doi=quote(doi, safe="/"))))
            else:
                entry["openalex"] = "skipped"
        entry["verdict"] = _doi_verdict(entry)
        result[key] = entry
    return result


_VERIFY_STRINGS = {
    "id": {
        "heading": "Verifikasi DOI (Crossref + OpenAlex)",
        "cols": ("kunci", "doi", "crossref", "openalex", "hasil"),
        "ok": "ok",
        "missing": "TIDAK DITEMUKAN",
        "unverified": "belum terverifikasi",
        "no_doi": "tanpa DOI",
        "skipped": "tanpa key",
        "src": {"ok": "ok", "not-found": "tidak ada",
                "no-doi": "tanpa DOI", "skipped": "tanpa key",
                "error": "error"},
        "summary": (
            "Terverifikasi {ok} dari {total} DOI; tidak ditemukan {missing}, "
            "belum terverifikasi {unverified}, tanpa DOI {no_doi}."
        ),
        "note": (
            "DOI dilaporkan 'tidak ditemukan' bila satu sumber yang "
            "diperiksa menjawab 404 dan tidak ada sumber yang error — "
            "sumber yang dilewati karena tanpa key tidak melindunginya. "
            "'Belum terverifikasi' hanya bila ada sumber yang error, "
            "atau tidak ada sumber yang diperiksa sama sekali. "
            "Set OPENALEX_API_KEY agar dua sumber diperiksa."
        ),
        "empty": "Tidak ada referensi di bibliografi.",
    },
    "en": {
        "heading": "DOI verification (Crossref + OpenAlex)",
        "cols": ("key", "doi", "crossref", "openalex", "result"),
        "ok": "ok",
        "missing": "NOT FOUND",
        "unverified": "unverified",
        "no_doi": "no DOI",
        "skipped": "no key",
        "src": {"ok": "ok", "not-found": "not found",
                "no-doi": "no DOI", "skipped": "no key",
                "error": "error"},
        "summary": (
            "Verified {ok} of {total} DOIs; not found {missing}, "
            "unverified {unverified}, no DOI {no_doi}."
        ),
        "note": (
            "A DOI is reported 'not found' when one checked source "
            "answers 404 and no source errored — a source skipped for "
            "lack of a key does not shield it. 'Unverified' only when "
            "a source errored, or when nothing was checked at all. "
            "Set OPENALEX_API_KEY so both sources are checked."
        ),
        "empty": "No references in the bibliography.",
    },
}


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def format_verification(result: dict, lang: str = "id") -> str:
    """Human-readable table for verify_reference_dois()."""
    t = _VERIFY_STRINGS.get(lang, _VERIFY_STRINGS["id"])
    if not result:
        return t["empty"]
    key_w = max([len(t["cols"][0])] + [len(k) for k in result])
    doi_w = max([len(t["cols"][1])] + [min(len(r["doi"]), 40)
                                       for r in result.values()])
    header = (f"{t['cols'][0]:<{key_w}}  {t['cols'][1]:<{doi_w}}  "
              f"{t['cols'][2]:<10}  {t['cols'][3]:<10}  {t['cols'][4]}")
    lines = [t["heading"], "", header, "-" * len(header)]
    counts = {"ok": 0, "missing": 0, "unverified": 0, "no-doi": 0}
    for key, ref in result.items():
        counts[ref["verdict"]] += 1
        label = t[ref["verdict"].replace("-", "_")]
        crossref = t["src"].get(ref["crossref"], ref["crossref"])
        openalex = t["src"].get(ref["openalex"], ref["openalex"])
        lines.append(
            f"{key:<{key_w}}  {_clip(ref['doi'], doi_w):<{doi_w}}  "
            f"{crossref:<10}  {openalex:<10}  {label}"
        )
    lines += ["", t["summary"].format(
        total=len(result), ok=counts["ok"], missing=counts["missing"],
        unverified=counts["unverified"], no_doi=counts["no-doi"]), t["note"]]
    return "\n".join(lines) + "\n"


def reference_key(ref: dict, existing: dict | None = None) -> str:
    """Suggested bibliography key: first author family name + year.

    Appends a, b, ... when the key is already taken.
    """
    authors = ref.get("authors") or []
    family = _family(authors[0]).lower() if authors else "unknown"
    family = re.sub(r"[^a-z0-9]+", "", family) or "unknown"
    base = f"{family}{ref.get('year') or ''}"
    if not existing or base not in existing:
        return base
    suffix = ord("a")
    while f"{base}{chr(suffix)}" in existing:
        suffix += 1
    return f"{base}{chr(suffix)}"


def save_reference(ref: dict, path: str, key: str | None = None) -> str:
    """Append one reference to a bibliography JSON file. Returns its key."""
    refs = {}
    if os.path.isfile(path):
        refs = load_references(path)
    key = key or reference_key(ref, refs)
    refs[key] = ref
    with open(path, "w", encoding="utf-8") as f:
        json.dump(refs, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return key


def _family(author: str) -> str:
    return author.split(",", 1)[0].strip()


def _initials(author: str) -> str:
    parts = author.split(",", 1)
    if len(parts) < 2:
        return ""
    return "".join(f"{w[0]}." for w in parts[1].strip().split() if w)


def _given(author: str) -> str:
    parts = author.split(",", 1)
    return parts[1].strip() if len(parts) > 1 else ""


def _authors_apa(authors):
    if not authors:
        return ""
    formatted = [f"{_family(a)}, {_initials(a)}" for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _authors_mla(authors):
    if not authors:
        return ""
    if len(authors) == 1:
        return f"{_family(authors[0])}, {_given(authors[0])}"
    if len(authors) == 2:
        return f"{_family(authors[0])}, {_given(authors[0])}, and {_given(authors[1])} {_family(authors[1])}"
    return f"{_family(authors[0])}, {_given(authors[0])}, et al."


def _authors_chicago(authors):
    if not authors:
        return ""
    formatted = [f"{_family(authors[0])}, {_given(authors[0])}"] + [
        f"{_given(a)} {_family(a)}" for a in authors[1:]
    ]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, and {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"


def _authors_ieee(authors):
    return ", ".join(f"{_initials(a)} {_family(a)}" for a in authors)


def _authors_vancouver(authors):
    formatted = [f"{_family(a)} {_initials(a).replace('.', '')}" for a in authors]
    if len(formatted) > 6:
        return ", ".join(formatted[:6]) + ", et al"  # no period: format_reference adds one
    return ", ".join(formatted)


def _venue(ref):
    parts = []
    if ref.get("venue"):
        parts.append(ref["venue"])
    if ref.get("volume"):
        vol = f"vol. {ref['volume']}"
        if ref.get("issue"):
            vol += f", no. {ref['issue']}"
        parts.append(vol)
    if ref.get("pages"):
        parts.append(f"pp. {ref['pages']}")
    return ", ".join(parts)


def _doi_url(ref):
    if ref.get("doi"):
        return f"https://doi.org/{ref['doi']}"
    if ref.get("arxiv"):
        return f"https://arxiv.org/abs/{ref['arxiv']}"
    return ref.get("url", "")


def format_reference(ref, style: str) -> str:
    """Format one bibliography entry in the given style (simplified).

    `authors` is normalised with _authors_list, so a lone string
    becomes [string] instead of being rendered letter by letter
    (BibTeX/RIS already do this). A reference with no authors never
    crashes: it is rendered title-first with "n.d." for the year,
    the usual no-author form in every style.
    """
    authors = _authors_list(ref.get("authors", []), "format_reference")
    year = ref.get("year", "n.d.")
    # The default year "n.d." already ends in a period: styles that
    # append "{year}." must not render "n.d..".
    year_dot = str(year) if str(year).endswith(".") else f"{year}."
    title = ref.get("title", "")
    venue = _venue(ref)
    link = _doi_url(ref)
    if style == "apa":
        if authors:
            out = f"{_authors_apa(authors)} ({year}). {title}."
        else:
            out = f"{title}. ({year})."
        if venue:
            out += f" {venue}."
        if link:
            out += f" {link}"
        return out
    if style == "mla":
        if authors:
            out = f"{_authors_mla(authors)}. “{title}.”"
        else:
            out = f"“{title}.”"
        if venue:
            out += f" {venue},"
        out += f" {year_dot}"
        if link:
            out += f" {link}."
        return out
    if style == "chicago":
        if authors:
            out = f"{_authors_chicago(authors)}. {year_dot} “{title}.”"
        else:
            out = f"“{title}.” {year_dot}"
        if venue:
            out += f" {venue}."
        if link:
            out += f" {link}."
        return out
    if style == "ieee":
        if authors:
            out = f"{_authors_ieee(authors)}, “{title},”"
        else:
            out = f"“{title},”"
        if venue:
            out += f" {venue},"
        out += f" {year_dot}"
        if link:
            out += f" {link}."
        return out
    if style == "harvard":
        if authors:
            first = _family(authors[0])
            etal = " et al." if len(authors) > 3 else ""
            if len(authors) in (2, 3):
                first = ", ".join(_family(a) for a in authors[:-1]) + f" and {_family(authors[-1])}"
            out = f"{first}{etal} ({year}) '{title}',"
        else:
            out = f"'{title}' ({year}),"
        if venue:
            out += f" {venue}."
        if link:
            out += f" Available at: {link}"
        return out
    if style == "vancouver":
        if authors:
            out = f"{_authors_vancouver(authors)}. {title}."
        else:
            out = f"{title}."
        if venue:
            out += f" {venue};"
        out += f" {year_dot}"
        if link:
            out += f" Available from: {link}"
        return out
    raise ValueError(f"unknown style: {style}")


def _in_text(ref, style: str, number: int, key: str = "") -> str:
    # Normalised like format_reference: a lone authors string is
    # [string], not a character sequence — "Field, Andy" must give
    # "(Field, 2018)", not "(F et al., 2018)".
    authors = _authors_list(ref.get("authors"), key)
    year = ref.get("year", "n.d.")
    first = _family(authors[0]) if authors else "Anon."
    etal = " et al." if len(authors) > 2 else ""
    if len(authors) == 2:
        first = f"{_family(authors[0])} and {_family(authors[1])}"
    if style == "apa":
        return f"({first}{etal}, {year})"
    if style == "mla":
        return f"({first}{etal})"
    if style == "chicago":
        return f"({first}{etal} {year})"
    if style in ("ieee", "vancouver"):
        return f"[{number}]"
    if style == "harvard":
        return f"({first}{etal}, {year})"
    raise ValueError(f"unknown style: {style}")


def weave(text: str, references: dict, style: str = "apa", lang: str = "id"):
    """Replace [cite:key] / \\cite{key} markers with in-text citations.

    Returns (full_output, woven_text): the complete output (woven
    text plus the bibliography section) first, then the woven text
    alone. Unknown keys are marked [PERLU RUJUKAN: key] /
    [REFERENCE NEEDED: key], never invented.
    """
    if references is None:
        references = {}
    if style not in STYLES:
        raise ValueError(f"unknown style: {style}; choose one of {', '.join(STYLES)}")
    msg = MESSAGES["en" if lang == "en" else "id"]
    order = []
    missing = []

    def replace(match):
        key = (match.group(1) or match.group(2)).strip()
        if key not in references:
            if key not in missing:
                missing.append(key)
            return f"[{msg['missing']}: {key}]"
        if key not in order:
            order.append(key)
        return _in_text(references[key], style, order.index(key) + 1, key)

    pattern = re.compile(r"(?:\[cite:([^\]]+)\]|\\cite\{([^}]+)\})")
    woven = pattern.sub(replace, text)
    lines = [woven, "", f"## {msg['references_heading']}", ""]
    if not order and not missing:
        lines.append(msg["no_citations"])
    for i, key in enumerate(order, 1):
        prefix = f"[{i}] " if style in ("ieee", "vancouver") else ""
        lines.append(f"{prefix}{format_reference(references[key], style)}")
    if missing:
        lines += ["", msg["missing_note"]]
        for key in missing:
            lines.append(f"- {key}")
    return "\n".join(lines) + "\n", woven


# ======================================================================
# BibTeX export
# ======================================================================
# Turn a bibliography JSON file into a .bib file ready for LaTeX /
# Overleaf. Entry types follow the stored "type": article -> @article,
# book -> @book, conference -> @inproceedings, chapter -> @incollection,
# anything else -> @misc. Only fields actually present are exported —
# nothing is invented, and a missing title simply means no title field.
# LaTeX special characters in author/title/venue are escaped.
_BIBTEX_TYPES = {
    "article": "article",
    "book": "book",
    "conference": "inproceedings",
    "chapter": "incollection",
}

_BIBTEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _bibtex_escape(text) -> str:
    return "".join(_BIBTEX_ESCAPES.get(ch, ch) for ch in str(text))


def _flat(value) -> str:
    """One-line a string value: a CR or LF inside a title, venue,
    DOI or key would inject a line break into a BibTeX/RIS record
    (and a fake field into a parser that reads it back)."""
    return str(value).replace("\r", " ").replace("\n", " ")


def _authors_list(authors, key: str) -> list:
    """Authors as a list of strings: a lone string becomes [string].

    Anything else — a number, a list holding a non-string — is a
    ValueError, never a character-by-character export (H-2) or a
    bare TypeError downstream.
    """
    if authors is None:
        return []
    if isinstance(authors, str):
        return [authors]
    if isinstance(authors, (list, tuple)):
        for a in authors:
            if not isinstance(a, str):
                raise ValueError(
                    f"authors referensi '{key}' harus berupa daftar "
                    "nama (string)")
        return list(authors)
    raise ValueError(
        f"authors referensi '{key}' harus berupa daftar nama")


def _bibtex_key(key: str) -> str:
    """A BibTeX key cannot hold braces, commas, or whitespace."""
    return re.sub(r"[{},\s]+", "-", _flat(key)).strip("-")


def _bibtex_pages(pages) -> str:
    """Normalise a pages value to BibTeX form, e.g. '189-194' -> '189--194'.

    Dashes are normalised first ('--', en dash, em dash all become
    a single '-'), like _ris_pages, so '189–194' becomes '189--194'
    instead of passing the en dash through untouched. Unlike RIS,
    the FULL value is kept: '189–194, 200' becomes '189--194, 200'
    — a BibTeX pages field can hold a list, so dropping the trailing
    page would lose information.
    """
    p = _flat(pages).replace("pp. ", "").strip()
    p = p.replace("--", "-").replace("–", "-").replace("—", "-")
    return p.replace("-", "--")


_REF_TYPE_ALIASES = {
    "journal-article": "article",
    "book-chapter": "chapter",
    "proceedings-article": "conference",
    "book": "book",
}


def _norm_ref_type(kind) -> str:
    """Map a raw Crossref-style type to the canonical repo type.

    A bibliography written from a raw Crossref record can carry
    "journal-article" where the repo expects "article"; without
    this the export falls through to @misc / GEN. Anything
    unrecognised (report, dissertation, dataset, ...) is returned
    unchanged and still falls through to @misc / GEN.
    """
    return _REF_TYPE_ALIASES.get(str(kind or "").strip(), kind)


def _bibtex_entry(key: str, ref: dict) -> str:
    entry_type = _BIBTEX_TYPES.get(
        _norm_ref_type(ref.get("type", "")), "misc")
    fields = []
    authors = _authors_list(ref.get("authors"), key)
    if authors:
        fields.append(("author", " and ".join(_bibtex_escape(_flat(a)) for a in authors)))
    if ref.get("title"):
        fields.append(("title", _bibtex_escape(_flat(ref["title"]))))
    venue = _flat(ref.get("venue", ""))
    pages = ref.get("pages", "")
    if entry_type == "incollection" and ", pp. " in venue:
        venue, _, pp = venue.partition(", pp. ")
        pages = pages or pp
    if entry_type == "article":
        if venue:
            fields.append(("journal", _bibtex_escape(venue)))
    elif entry_type == "book":
        if venue:
            fields.append(("publisher", _bibtex_escape(venue)))
    elif entry_type in ("inproceedings", "incollection"):
        if venue:
            fields.append(("booktitle", _bibtex_escape(venue)))
    elif venue:
        fields.append(("note", _bibtex_escape(venue)))
    if ref.get("volume"):
        fields.append(("volume", _bibtex_escape(_flat(ref["volume"]))))
    if ref.get("issue"):
        fields.append(("number", _bibtex_escape(_flat(ref["issue"]))))
    if pages:
        fields.append(("pages", _bibtex_pages(pages)))
    if ref.get("year"):
        fields.append(("year", _bibtex_escape(_flat(ref["year"]))))
    if ref.get("doi"):
        fields.append(("doi", _bibtex_escape(_flat(ref["doi"]))))
    if ref.get("arxiv"):
        fields.append(("eprint", _bibtex_escape(_flat(ref["arxiv"]))))
        fields.append(("archivePrefix", "arXiv"))
    if ref.get("url"):
        fields.append(("url", _bibtex_escape(_flat(ref["url"]))))
    lines = [f"@{entry_type}{{{_bibtex_key(key)},"]
    for name, value in fields:
        lines.append(f"  {name} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def export_bibtex(references: dict) -> str:
    """Export a bibliography dict {key: ref} to BibTeX text, sorted by key."""
    return "\n\n".join(_bibtex_entry(k, references[k]) for k in sorted(references)) + "\n"


# ======================================================================
# RIS export
# ======================================================================
# Mirror of the BibTeX export, for Mendeley / Zotero / Word users: turn
# a bibliography JSON file into a .ris file. Record types follow the
# stored "type": article -> JOUR, book -> BOOK, conference -> CONF,
# chapter -> CHAP, anything else -> GEN. The bibliography key is kept
# as the ID line so the record can be traced back. Only fields actually
# present are exported — nothing is invented, and a missing title
# simply means no title line. arXiv IDs become an arXiv URL line.
_RIS_TYPES = {
    "article": "JOUR",
    "book": "BOOK",
    "conference": "CONF",
    "chapter": "CHAP",
}


def _ris_pages(pages) -> tuple:
    """Split a pages value into (start, end); '189-194' -> ('189', '194').

    Normalised like _bibtex_pages first: '--', en dash and em dash
    all become a single '-', so '189–194' and '189--194' split too.
    Only the first range is kept: '189–194, 200' becomes
    ('189', '194') — RIS has a single SP and a single EP line, so
    a trailing page after the comma has nowhere to go. BibTeX keeps
    the full value instead (see _bibtex_pages).
    """
    p = _flat(pages).replace("pp. ", "").strip()
    p = p.split(",")[0].strip()
    p = p.replace("--", "-").replace("–", "-").replace("—", "-")
    if "-" in p:
        start, _, end = p.partition("-")
        return start.strip(), end.strip()
    return p, ""


def _ris_entry(key: str, ref: dict) -> str:
    entry_type = _RIS_TYPES.get(
        _norm_ref_type(ref.get("type", "")), "GEN")
    lines = [f"TY  - {entry_type}", f"ID  - {_flat(key)}"]
    authors = _authors_list(ref.get("authors"), key)
    for a in authors:
        lines.append(f"AU  - {_flat(a)}")
    if ref.get("title"):
        lines.append(f"TI  - {_flat(ref['title'])}")
    venue = _flat(ref.get("venue", ""))
    pages = ref.get("pages", "")
    if entry_type == "CHAP" and ", pp. " in venue:
        venue, _, pp = venue.partition(", pp. ")
        pages = pages or pp
    if entry_type == "JOUR":
        if venue:
            lines.append(f"JO  - {venue}")
    elif entry_type == "BOOK":
        if venue:
            lines.append(f"PB  - {venue}")
    elif entry_type in ("CONF", "CHAP"):
        if venue:
            lines.append(f"T2  - {venue}")
    elif venue:
        lines.append(f"N1  - {venue}")
    if ref.get("volume"):
        lines.append(f"VL  - {_flat(ref['volume'])}")
    if ref.get("issue"):
        lines.append(f"IS  - {_flat(ref['issue'])}")
    if pages:
        start, end = _ris_pages(pages)
        if start:
            lines.append(f"SP  - {start}")
        if end:
            lines.append(f"EP  - {end}")
    if ref.get("year"):
        lines.append(f"PY  - {_flat(ref['year'])}")
    if ref.get("doi"):
        lines.append(f"DO  - {_flat(ref['doi'])}")
    if ref.get("url"):
        lines.append(f"UR  - {_flat(ref['url'])}")
    if ref.get("arxiv"):
        lines.append(f"UR  - https://arxiv.org/abs/{_flat(ref['arxiv'])}")
    lines.append("ER  - ")
    return "\n".join(lines)


def export_ris(references: dict) -> str:
    """Export a bibliography dict {key: ref} to RIS text, sorted by key."""
    return "\n\n".join(_ris_entry(k, references[k]) for k in sorted(references)) + "\n"


# ======================================================================
# Citation audit
# ======================================================================
# Check a manuscript's citations against its bibliography before it is
# submitted: which [cite:key] / \cite{key} markers have no bibliography
# entry (missing — the reader can never check them), and which
# bibliography entries are never cited (unused). Optionally verify that
# each cited reference's DOI / arXiv / URL actually resolves, with a
# plain HEAD request. A failed check is reported, never faked: a link
# that cannot be reached is "unreachable", not "alive".
_CITE_PATTERN = re.compile(r"(?:\[cite:([^\]]+)\]|\\cite\{([^}]+)\})")


def _author_year_keys(text: str, references: dict) -> list:
    """Bibliography keys cited in author-year form, in first-appearance
    order: parenthetical "(Field, 2018)" / "(Field et al., 2018)" and
    narrative "Field (2018)" / "Menurut Field (2018)". A parenthetical
    group may hold several citations — "(Field, 2018; Creswell,
    2018)" and "(Field, 2018, Creswell, 2018)" both credit every
    unit inside the group — and a unit may carry a short intro word
    after the separator ("(Field, 2018; lihat juga Creswell, 2018)";
    the list is fixed: lihat juga, bandingkan, cf., lihat).

    Only the first author's family name and the year are matched, so
    this is NOT a full audit: it cannot tell which of two entries by
    the same family in the same year is meant, and multi-author
    forms ("Field and Ghozali (2018)", "(Field & Ghozali, 2018)")
    are not recognised. Callers must flag the matches as author-year
    (see audit_citations), never as verified [cite:key] citations.
    """
    found = []
    for key, ref in references.items():
        if not isinstance(ref, dict):
            continue
        authors = ref.get("authors")
        if isinstance(authors, str):
            authors = [authors]
        if not isinstance(authors, (list, tuple)) or not authors:
            continue
        first = authors[0]
        family = _family(first) if isinstance(first, str) else ""
        year = ref.get("year")
        if not family or year in (None, ""):
            continue
        fam = re.escape(family)
        yr = re.escape(str(year).strip())
        # One unit inside a parenthetical group: anchored at the
        # start of the group or after ';' / ',', and ending at ';' /
        # ',' / group end. The old regex demanded ')' right after
        # the year, so a multi-citation group matched nothing at
        # all; the trailing separator (instead of ')') is also what
        # keeps "(Field, 2019)" from matching a 2018 entry and a
        # bare "Field, 2018" outside parens from being claimed.
        # An intro word may follow the separator before the next
        # family name ("(Field, 2018; lihat juga Creswell, 2018)"
        # — audit #7 N-1). The list is deliberately short and
        # "lihat juga" comes first, so "lihat" cannot claim the
        # "lihat" of "lihat juga" and leave "juga" unmatched:
        # any word here is skipped, so a long list would invite
        # false positives. The intro is allowed ONLY after ';'
        # or ',' — NOT at the start of a group: audit #6 pins
        # "(lihat Field, 2018)" as NOT a citation, and that
        # negative still stands.
        intro = r"(?:lihat juga|bandingkan|cf\.?|lihat)\s+"
        unit = re.compile(
            r"(?:^|[;,]\s*(?:" + intro + r")?)\s*" + fam
            + r"(?:\s+et al\.?)?\s*,?\s*" + yr
            + r"\s*(?:[;,]|$)")
        narrative = re.compile(
            r"\b" + fam + r"(?:\s+et al\.?)?\s*\(\s*" + yr + r"\s*\)")
        in_paren = any(
            unit.search(group)
            for group in re.findall(r"\(([^()]*)\)", text))
        if in_paren or narrative.search(text):
            found.append(key)
    return found


def audit_citations(text: str, references: dict) -> dict:
    """Audit citations in `text` against `references`.

    Returns {"cited": [...], "counts": {...}, "missing": [...],
    "unused": [...], "author_year": [...]}. `cited` keeps
    first-appearance order; `missing` and `unused` are sorted.
    `author_year` lists the bibliography keys matched only in
    author-year form ("(Field, 2018)", "Field (2018)"), including
    multi-citation groups ("(Field, 2018; Creswell, 2018)",
    "(Field, 2018, Creswell, 2018)"): those keys
    count as cited and are NOT reported as "unused", but the match
    is name + year only, so author-year style is NOT fully audited —
    a same-family, same-year entry can be credited to the wrong key,
    and multi-author forms are not recognised at all.
    """
    if references is None:
        references = {}
    cited = []
    counts = {}
    for match in _CITE_PATTERN.finditer(text):
        key = (match.group(1) or match.group(2)).strip()
        counts[key] = counts.get(key, 0) + 1
        if key not in cited:
            cited.append(key)
    author_year = _author_year_keys(text, references)
    for key in author_year:
        counts[key] = counts.get(key, 0) + 1
        if key not in cited:
            cited.append(key)
    missing = sorted(k for k in cited if k not in references)
    unused = sorted(k for k in references if k not in counts)
    return {"cited": cited, "counts": counts, "missing": missing,
            "unused": unused, "author_year": author_year}


def _reference_link(ref: dict) -> str:
    """The checkable link for a reference: DOI, arXiv, or plain URL."""
    if ref.get("doi"):
        return f"https://doi.org/{ref['doi']}"
    if ref.get("arxiv"):
        return f"https://arxiv.org/abs/{ref['arxiv']}"
    return ref.get("url", "")


def _url_alive(url: str, timeout: int = 10) -> tuple[bool, str]:
    """HEAD the URL. Returns (alive, status): status is the HTTP code
    or the error text when the request failed."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": LOOKUP_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, str(resp.status)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # offline, DNS failure, timeout, ...
        return False, str(e)


def check_reference_links(references: dict, keys=None) -> dict:
    """Check each reference's link. Returns {key: (url, alive, status)}.
    Keys without any link are skipped."""
    out = {}
    for key in (keys if keys is not None else sorted(references)):
        ref = references.get(key)
        if not ref:
            continue
        url = _reference_link(ref)
        if not url:
            continue
        alive, status = _url_alive(url)
        out[key] = (url, alive, status)
    return out


_AUDIT_STRINGS = {
    "id": {
        "heading": "Hasil audit sitasi",
        "cited": "Dikutip di naskah",
        "missing": "HILANG dari bibliografi (tidak bisa dicek pembaca)",
        "unused": "Ada di bibliografi tapi tidak pernah dikutip",
        "dead": "Link mati / tidak bisa dijangkau",
        "ok": "Semua sitasi ada di bibliografi.",
        "none_missing": "Tidak ada sitasi yang hilang.",
        "none_unused": "Tidak ada entri yang tidak terpakai.",
        "none_dead": "Semua link yang dicek masih hidup.",
        "author_year": "Sitasi author-year terdeteksi (tidak diaudit penuh — hanya nama penulis + tahun yang dicocokkan)",
    },
    "en": {
        "heading": "Citation audit result",
        "cited": "Cited in the text",
        "missing": "MISSING from the bibliography (the reader can never check them)",
        "unused": "In the bibliography but never cited",
        "dead": "Dead / unreachable links",
        "ok": "Every citation is in the bibliography.",
        "none_missing": "No missing citations.",
        "none_unused": "No unused entries.",
        "none_dead": "Every checked link is alive.",
        "author_year": "Author-year citations detected (not fully audited — matched on author name + year only)",
    },
}


def format_audit(result: dict, lang: str = "id", links: dict | None = None) -> str:
    """Render an audit result as a readable report."""
    s = _AUDIT_STRINGS["en" if lang == "en" else "id"]
    lines = [f"# {s['heading']}", ""]
    lines.append(f"{s['cited']}: {len(result['cited'])}")
    for key in result["cited"]:
        lines.append(f"- {key} (x{result['counts'][key]})")
    lines.append("")
    if result["missing"]:
        lines.append(f"## {s['missing']}")
        for key in result["missing"]:
            lines.append(f"- {key}")
    else:
        lines.append(s["none_missing"])
    lines.append("")
    if result["unused"]:
        lines.append(f"## {s['unused']}")
        for key in result["unused"]:
            lines.append(f"- {key}")
    else:
        lines.append(s["none_unused"])
    if result.get("author_year"):
        lines.append("")
        lines.append(f"## {s['author_year']}")
        for key in result["author_year"]:
            lines.append(f"- {key}")
    if links is not None:
        lines.append("")
        dead = {k: v for k, v in links.items() if not v[1]}
        if dead:
            lines.append(f"## {s['dead']}")
            for key, (url, _alive, status) in sorted(dead.items()):
                lines.append(f"- {key}: {url} ({status})")
        else:
            lines.append(s["none_dead"])
    if not result["missing"] and not result["unused"]:
        lines.append("")
        lines.append(s["ok"])
    return "\n".join(lines) + "\n"


# ======================================================================
# NEW ENGINE: Academic Text Quality Analyzer
# ======================================================================
# Integrated engine that combines jargon detection, citation analysis,
# DOI verification, and bibliography completeness checking into a
# single comprehensive report for academic texts.
# ======================================================================


# ======================================================================
# Style check (cek gaya) — fourth component of analyze
# ======================================================================
# Rule-based signals for stiff Indonesian academic prose, written from
# Indonesian grammar (EYD/KBBI), not from any other project's tables:
# light verbs paired with nominalized nouns, stacked connectors,
# passive pile-ups, calqued relatives, and flat sentence rhythm.
# This is a style report, not a rewrite and not a detector dodge:
# flagged patterns are suggestions for the author's own edit.
# Thresholds were calibrated on this repo's own sample texts
# (demos/citation-weaver/contoh_id.txt, demos/jargon-buster/test_paper.txt):
# clean academic prose passes all five signals.

# Light verbs that turn a verb into a noun phrase: "melakukan
# pengukuran" says in three words what "mengukur" says in one.
_LIGHT_VERBS = (
    "melakukan", "memberikan", "mengalami", "melaksanakan",
    "mengadakan", "menjalani",
)
# Nominalized endings: a noun built from a verb.
_NOMINAL_ENDINGS = ("an", "isasi", "asi", "itas", "isme", "usi")
# Deverbal nouns that do not end in a nominal ending.
_NOMINAL_WORDS = ("analisis", "pengaruh", "kontribusi")
_LIGHT_VERB_RE = re.compile(
    r"\b(" + "|".join(_LIGHT_VERBS) + r")\b"
    r"(?:\s+(?:terhadap|atas|antara|sebesar|kepada|dalam|dari|untuk|dengan|yang))?"
    r"\s+([A-Za-z]+(?:an|isasi|asi|itas|isme|usi)\b|analisis|pengaruh|kontribusi)",
    re.IGNORECASE,
)

# Discourse connectors that, stacked, make the text read like a list
# of transitions instead of an argument.
_CONNECTORS = (
    "selain itu", "namun demikian", "di sisi lain", "oleh karena itu",
    "dengan demikian", "lebih lanjut", "sementara itu", "akan tetapi",
    "di samping itu", "sebagai tambahan", "pada akhirnya",
    "secara keseluruhan", "dalam hal ini", "berdasarkan hal tersebut",
)

# Common passive verbs in academic Indonesian. Passive itself is
# legitimate; the signal is a pile-up of them.
_PASSIVE_VERBS = (
    "dilakukan", "dilaksanakan", "diperoleh", "ditunjukkan", "digunakan",
    "dibuat", "diberikan", "ditemukan", "dijelaskan", "dinyatakan",
    "ditetapkan", "diperlihatkan", "dilaporkan", "dianalisis", "diukur",
    "dihitung", "dibandingkan", "disimpulkan", "diharapkan", "diketahui",
)

# "yang mana" and joined "dimana" as relative pronouns are calques
# from English "which"/"where". (Separate "di mana" for a real place
# is correct and is not flagged.)
_YANG_MANA_RE = re.compile(r"\byang mana\b|\bdimana\b", re.IGNORECASE)


# Abbreviations whose period never ends a sentence. Protected with
# a private-use placeholder before splitting, restored after.
# "hal." is the Indonesian abbreviation for "halaman" (page);
# "hlm." is the standard KBBI abbreviation for the same word.
# Honorifics (Bpk./Sdr./Tn./Ny./Nn.) join the list (audit #5 H-7).
# Audit #6 H-8 adds more honorifics (Sdri./Yth./Ir./Hj.), the
# address abbreviations (Jln./Jl./Gg./Rt./Rw.) and the
# edition/volume abbreviations (Ed./Vol./Cet.): all of them are
# followed by a name, a number or a Roman numeral, never by the
# end of a sentence, so they are protected unconditionally like
# Dr./Bpk./hlm. (and like "No.", which is also digit-followed).
# The list abbreviations dll./dst./dkk. are NOT here: they are only
# protected when the next word starts lowercase (audit #5 H-6) —
# "dll. Kemudian" ends a sentence, "dll. kemudian" does not — so
# they get their own conditional protection below.
# The date abbreviations (Tgl./Th. and the months) are NOT here
# either: unlike a title or an address, a date CAN end a sentence
# ("Rapat pada 12 Jan."), so they get their own conditional
# protection below (digit or lowercase next word).
_ABBREVIATIONS = ("Dr.", "Prof.", "Drs.", "Bpk.", "Sdr.", "Tn.",
                  "Ny.", "Nn.", "Sdri.", "Yth.", "Ir.", "Hj.",
                  "Jln.", "Jl.", "Gg.", "Rt.", "Rw.",
                  "Ed.", "Vol.", "Cet.",
                  "e.g.", "i.e.", "hal.", "hlm.", "No.")
_ABBREV_PLACEHOLDER = "\ue000"
# Every period inside an abbreviation is hidden, not just the last
# one: "e.g." used to survive as "e.g<placeholder>", whose remaining
# period still split the sentence. Matched at a word boundary so a
# word that merely ends in the same letters ("perihal.") is not
# protected by mistake. Longest first so "Drs." wins over "Dr.".
_ABBREV_RE = re.compile(
    r"\b(?:" + "|".join(
        re.escape(a) for a in sorted(_ABBREVIATIONS, key=len, reverse=True)
    ) + r")")
# List abbreviations (dll./dst./dkk./dsb.): protected only when the
# next word starts with a lowercase letter (audit #5 H-6; "dsb."
# joins them in audit #6 H-8). A capitalised next word — or the end
# of the text — means the abbreviation closed the sentence ("Ia
# membeli buku, dll. Kemudian pulang." is two sentences; "Buku itu
# dst. dibaca semua." is one). Matched at a word boundary so a word
# that merely ends in the same letters is not protected by mistake;
# the lowercase check is done in _split_sentences with
# str.islower(), so it covers non-ASCII lowercase letters too.
_LIST_ABBREV_RE = re.compile(r"\b(?:dll|dst|dkk|dsb)\.")
# Date abbreviations (Tgl./Th. and the months that end in a
# period; "Mei" has none, so it is not here): protected only when
# the next token is a digit — the year or day that normally
# follows ("12 Jan. 2020", "Tgl. 12") — or a lowercase word (the
# dll. rule: "Jan. lalu", "Jan. adalah bulan pertama"). A
# capitalised next word ends the sentence, because a date can
# genuinely close one ("Rapat pada 12 Jan. Besok libur." is two
# sentences). This is the one new class that is conditional rather
# than unconditional (audit #6 H-8).
_DATE_ABBREV_RE = re.compile(
    r"\b(?:Tgl|Th|Jan|Feb|Mar|Apr|Jun|Jul|Agu|Sep|Okt|Nov|Des)\.")
# A chained academic degree ("Dr. rer. nat."): the whole phrase
# is one title, so all of its periods are protected (audit #6
# H-8). Matched as a phrase, not as standalone "rer."/"nat.",
# which are not abbreviations on their own.
_CHAINED_DEGREE_RE = re.compile(r"\bDr\.\s+rer\.\s+nat\.")
# A dotted academic degree (M.Si., S.Pd., S.Si., M.Pd.): a capital
# letter, a period, a capital letter with optional lowercase
# letters, a period (audit #5 N-11). Protected like an abbreviation
# so the degree never splits a sentence mid-way.
_DEGREE_RE = re.compile(r"\b[A-Z]\.[A-Z][a-z]*\.")
# A lone capital letter followed by a period, e.g. "A." in
# "Dr. A. Budi" — an initial, not a sentence end. Only protected
# when another capitalised word follows, so a sentence that merely
# ends in a lone capital ("Nilainya A.") still splits.
_INITIAL_RE = re.compile(r"\b[A-Z]\.(?=\s+[A-Z])")
# A sentence terminator: . ! ? (runs of them, e.g. "..."), plus a
# RUN of closing quotes or parentheses (audit #5 N-1: "'Pergi!')"
# ends a sentence, not just "'Pergi!'"), followed by whitespace or
# the end of the text. Only terminators are scanned for — the
# previous pattern also scanned "[^.!?]*" from every position,
# which was quadratic on text without a terminator. The closing
# run is captured (group 1) so _split_sentences can tell a
# terminator WITH closers from one without: audit #6 H-9 only
# applies after closers.
_TERMINATOR_RE = re.compile(r"[.!?]+(['\"”’)]*)(?=\s|$)")


def _protect_abbreviations(text: str) -> str:
    """Hide abbreviation periods so terminator scans skip them.

    Every "." inside a protected abbreviation is replaced by the
    single placeholder char, so the returned string has EXACTLY the
    same length as the input — offsets into the protected string
    are offsets into the original. Shared by _split_sentences and
    _sentence_spans (audit #7 H-5: the old _sentence_spans used a
    naive terminator regex and cut "Dr. Budi ..." into "Dr." +
    "Budi ...", so humanize previews lost the title).
    """
    protected = text
    # The chained degree first: _ABBREV_RE below would hide the
    # period of "Dr.", after which the phrase no longer matches.
    protected = _CHAINED_DEGREE_RE.sub(
        lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), protected)
    protected = _ABBREV_RE.sub(
        lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), protected)

    def _protect_list_abbrev(m):
        # A list abbreviation is protected only when the next word
        # starts lowercase (audit #5 H-6); a capitalised next word
        # or the end of the text leaves the period as a terminator.
        # `protected` here is still the pre-substitution string,
        # since the assignment happens after sub() returns.
        after = protected[m.end():].lstrip()
        if after and after[0].islower():
            return m.group(0).replace(".", _ABBREV_PLACEHOLDER)
        return m.group(0)

    protected = _LIST_ABBREV_RE.sub(_protect_list_abbrev, protected)

    def _protect_date_abbrev(m):
        # A date abbreviation is protected only when the next token
        # is a digit (the year/day that normally follows: "12 Jan.
        # 2020", "Tgl. 12") or a lowercase word ("Jan. lalu");
        # a capitalised next word means the date closed the
        # sentence (audit #6 H-8). Same closure caveat as above.
        after = protected[m.end():].lstrip()
        if after and (after[0].isdigit() or after[0].islower()):
            return m.group(0).replace(".", _ABBREV_PLACEHOLDER)
        return m.group(0)

    protected = _DATE_ABBREV_RE.sub(_protect_date_abbrev, protected)
    protected = _DEGREE_RE.sub(
        lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), protected)
    protected = _INITIAL_RE.sub(
        lambda m: m.group(0)[:-1] + _ABBREV_PLACEHOLDER, protected)
    return protected


def _split_sentences(text: str) -> list[str]:
    """Sentences as strings; splits on . ! ? followed by space/end.

    A closing quote (or parenthesis) after the terminator belongs
    to the sentence that just ended, so "'Jangan!' Begitu ..." is
    three sentences, not two — UNLESS the continuation starts
    lowercase, in which case the quoted/paren material and the
    continuation are one sentence (audit #6 H-9): "Dia berkata,
    'Saya takut!' sambil menangis." is one sentence, while
    "'Jangan!' Begitu katanya." is still two. Without a closing
    quote or parenthesis the lowercase rule does not apply ("Dia
    pergi. sambil menangis." still splits). Sentences come back
    without their terminator but with any closing quote kept
    ("'Jangan!'"), a trailing fragment without a terminator is kept
    as its own sentence, and empty text gives [].

    Abbreviations ("Dr.", "e.g.", "i.e.", "hal.", "hlm.", "Bpk.",
    "Tn.", "Sdri.", "Yth.", "Ir.", "Hj.", "Jl.", "Jln.", "Gg.",
    "Rt.", "Rw.", "Ed.", "Vol.", "Cet.", ...) and single capital
    initials ("A." in "Dr. A. Budi") never split a sentence, and
    neither do dotted degrees ("M.Si.", "S.Pd.") or the chained
    degree "Dr. rer. nat.". List abbreviations ("dll.", "dst.",
    "dkk.", "dsb.") are only protected when the next word starts
    lowercase; a capitalised next word (or the end of the text)
    ends the sentence. Date abbreviations ("Tgl.", "Th." and the
    months "Jan." ... "Des.") are only protected when the next
    token is a digit or a lowercase word, because a date can
    genuinely end a sentence ("Rapat pada 12 Jan. Besok libur."
    is two sentences; "Rapat 12 Jan. 2020 diadakan." is one).
    Linear time: only terminators are matched, then the text is
    sliced between matches.

    Limitation: a sentence that genuinely ends in a lone capital
    letter is merged with the next one when the next sentence
    starts with a capital, e.g. "Nilainya A. Ia senang." stays one
    sentence — an initial and a sentence-final capital cannot be
    told apart without a dictionary of names. The same applies to
    an unconditional abbreviation at the very end of a sentence
    ("Gelarnya Dr. rer. nat. Ia mengajar." stays one sentence):
    titles and addresses are never sentence-final in real text,
    so the protection is worth the trade-off.
    """
    protected = _protect_abbreviations(text.strip())
    # Scan for sentence ends instead of splitting: a closing quote
    # (or parenthesis) after the terminator belongs to the sentence
    # that just ended, so it must be kept, not consumed as a
    # delimiter. A trailing fragment without a terminator is kept
    # as its own sentence.
    out: list[str] = []
    pos = 0
    for m in _TERMINATOR_RE.finditer(protected):
        if m.group(1):
            # Terminator + closing quote/paren (audit #6 H-9): a
            # lowercase continuation belongs to the same sentence
            # ("'Saya takut!' sambil ..." is one sentence), so this
            # match is not a boundary and the scan continues. A
            # capitalised continuation (or a digit, or the end of
            # the text) still ends the sentence ("'Jangan!' Begitu
            # ..." is two). Without closers the rule does not
            # apply: "Dia pergi. sambil ..." still splits.
            after = protected[m.end():].lstrip()
            if after and after[0].islower():
                continue
        piece = protected[pos:m.end()].strip().rstrip(".!?")
        if piece:
            out.append(piece)
        pos = m.end()
    tail = protected[pos:].strip()
    if tail:
        out.append(tail)
    return [s.replace(_ABBREV_PLACEHOLDER, ".") for s in out]


def _sentence_word_counts(text: str) -> list[int]:
    """Word counts per sentence; splits on . ! ? followed by space/end."""
    return [len(s.split()) for s in _split_sentences(text)]


def _stdev(values: list[int]) -> float:
    """Population standard deviation, no statistics import needed."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return round(var ** 0.5, 1)


def check_style(text: str) -> dict:
    """Check Indonesian academic prose for stiff-style signals.

    Returns a dict with keys:
    - signals: per-signal {count, flagged, examples} (rhythm also
      carries sentence count and stdev)
    - style_score: 0-25, five points per clean signal
    - flagged: names of the flagged signals

    Density signals need at least two occurrences to flag, so one
    stray connector in a short note does not fail the check, and a
    text under 10 words is never flagged on density at all (a short
    note cannot have a meaningful density). The density thresholds
    are inclusive (>=): exactly 1.0 nominalizations per 100 words
    flags, as does exactly 5.0 passive verbs. Rhythm is only judged
    on five or more sentences: flagged when 60% or more of them sit
    within two words of the mean sentence length.
    """
    words = text.split()
    n_words = len(words)
    per_100 = (lambda c: round(c / max(1, n_words) * 100, 1))

    matches = _LIGHT_VERB_RE.findall(text)
    nominal = {
        "count": len(matches),
        "density_per_100": per_100(len(matches)),
        "flagged": (n_words >= 10 and len(matches) >= 2
                    and per_100(len(matches)) >= 1.0),
        "examples": [" ".join(m).strip() for m in matches[:3]],
    }

    conn_hits = []
    for conn in _CONNECTORS:
        conn_hits += [conn] * len(
            re.findall(r"\b" + re.escape(conn) + r"\b", text, re.IGNORECASE))
    connectors = {
        "count": len(conn_hits),
        "density_per_100": per_100(len(conn_hits)),
        "flagged": (n_words >= 10 and len(conn_hits) >= 2
                    and per_100(len(conn_hits)) >= 2.0),
        "examples": conn_hits[:3],
    }

    passive_hits = []
    for verb in _PASSIVE_VERBS:
        passive_hits += [verb] * len(
            re.findall(r"\b" + verb + r"\b", text, re.IGNORECASE))
    passive = {
        "count": len(passive_hits),
        "density_per_100": per_100(len(passive_hits)),
        "flagged": (n_words >= 10 and len(passive_hits) >= 3
                    and per_100(len(passive_hits)) >= 5.0),
        "examples": passive_hits[:3],
    }

    ym = _YANG_MANA_RE.findall(text)
    yang_mana = {
        "count": len(ym),
        "flagged": len(ym) >= 1,
        "examples": [m.lower() for m in ym[:3]],
    }

    counts = _sentence_word_counts(text)
    if len(counts) >= 5:
        mean = sum(counts) / len(counts)
        near = sum(1 for x in counts if abs(x - mean) <= 2)
        share = round(near / len(counts), 2)
    else:
        share = None
    rhythm = {
        "sentences": len(counts),
        "stdev": _stdev(counts) if len(counts) >= 2 else None,
        "same_length_share": share,
        "flagged": share is not None and share >= 0.6,
    }

    signals = {
        "nominalization": nominal,
        "connectors": connectors,
        "passive": passive,
        "yang_mana": yang_mana,
        "rhythm": rhythm,
    }
    flagged = [name for name, s in signals.items() if s["flagged"]]
    return {
        "signals": signals,
        "style_score": 5 * (5 - len(flagged)),
        "flagged": flagged,
    }


# ======================================================================
# Style rewrite suggestions (saran rewrite gaya)
# ======================================================================
# For each stiff-style pattern found by check_style(), propose a
# concrete replacement — shown before/after, never applied silently.
# The verb table is written from Indonesian grammar: a nominalized
# noun maps to the verb that says the same thing in one word.
# Patterns that need a human decision (passive voice, rhythm, a
# "dimana" that may or may not be a place) get guidance instead of
# a mechanical replacement.

# Nominalized noun -> the verb form.
_NOUN_TO_VERB = {
    "pengukuran": "mengukur", "analisis": "menganalisis",
    "pengujian": "menguji", "penelitian": "meneliti",
    "perbandingan": "membandingkan", "perhitungan": "menghitung",
    "pengamatan": "mengamati", "evaluasi": "mengevaluasi",
    "observasi": "mengobservasi", "simulasi": "mensimulasikan",
    "pemodelan": "memodelkan", "pengaruh": "memengaruhi",
    "kontribusi": "menyumbang", "gambaran": "menggambarkan",
    "informasi": "memberi tahu", "peningkatan": "meningkatkan",
    "penurunan": "menurunkan", "perubahan": "mengubah",
    "perawatan": "merawat",
    "pengembangan": "mengembangkan", "penerapan": "menerapkan",
    "penggunaan": "menggunakan", "pemeriksaan": "memeriksa",
    "penyusunan": "menyusun", "pelaksanaan": "melaksanakan",
    "pembangunan": "membangun", "pembahasan": "membahas",
    "peninjauan": "meninjau", "pendekatan": "mendekati",
    "pengumpulan": "mengumpulkan", "pengolahan": "mengolah",
    "penentuan": "menentukan", "perhatian": "memperhatikan",
    "dukungan": "mendukung",
}

# Trailing prepositions that belong to the light-verb frame and can
# be dropped with it ("pengukuran terhadap suhu" -> "mengukur suhu").
# "untuk", "dengan", "dari", "dalam" are NOT safe: they change the
# meaning ("pengujian untuk validasi" is not "menguji validasi").
_SAFE_TRAILING_PREPS = ("terhadap", "atas", "antara", "sebesar", "kepada")


def _sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """(start, end, sentence) for each sentence in the text.

    Abbreviation-aware (audit #7 H-5): the periods inside
    abbreviations are hidden first — via _protect_abbreviations,
    which is length-preserving, so offsets into the protected
    string are offsets into the original — and the same
    _TERMINATOR_RE + lowercase-after-closers rule (audit #6 H-9)
    as _split_sentences decides the boundaries. The old version
    used a naive `[.!?]+(?:\\s+|$)` regex, so "Dr. Budi ..." was
    cut into "Dr." + "Budi ..." and humanize previews (context
    and fixed, used by the CLI and the web UI) lost the title.

    Each span's start is the first non-space char of the sentence
    and end is just past its terminator, so a suggestion offset
    inside the sentence lines up exactly with the returned
    (stripped) sentence string — that is what _fixed_sentence
    relies on.
    """
    protected = _protect_abbreviations(text)
    spans = []
    start = 0
    for m in _TERMINATOR_RE.finditer(protected):
        if m.group(1):
            # Terminator + closing quote/paren (audit #6 H-9): a
            # lowercase continuation belongs to the same sentence,
            # so this match is not a boundary.
            after = protected[m.end():].lstrip()
            if after and after[0].islower():
                continue
        end = m.end()
        sent = text[start:end].strip()
        if sent:
            s0 = start
            while s0 < end and text[s0].isspace():
                s0 += 1
            spans.append((s0, end, sent))
        start = end
    tail = text[start:].strip()
    if tail:
        s0 = start
        while s0 < len(text) and text[s0].isspace():
            s0 += 1
        spans.append((s0, len(text), tail))
    return spans


def _context_sentence(spans, pos: int) -> str:
    for s, e, sent in spans:
        if s <= pos < e:
            return sent
    return spans[-1][2] if spans else ""


def _fixed_sentence(text: str, sug: dict) -> str | None:
    """The suggestion's sentence with the replacement applied.

    Uses _apply_one — the same path apply_suggestions() takes — so
    the preview is exactly the text --apply produces.
    """
    if sug["replacement"] is None:
        return None
    for s, e, sent in _sentence_spans(text):
        if s <= sug["start"] < e:
            rel = sug["start"] - s
            return _apply_one(sent, {
                "start": rel,
                "end": rel + len(sug["original"]),
                "replacement": sug["replacement"],
            })
    return sug["context"]


# Fused words that EYD writes separate (or hyphenated). Only
# high-confidence entries: each fused form is always wrong, so the
# fix is mechanical. NOT in the table on purpose: "dimana" (its fix
# depends on the sentence — see the yang_mana guidance) and fused
# "di"+verb forms ("ditulis", "dibaca"), which are correct.
_TYPO_TABLE = {
    "disini": "di sini", "disana": "di sana", "disitu": "di situ",
    "kesini": "ke sini", "kesana": "ke sana", "kesitu": "ke situ",
    "kemana": "ke mana", "darimana": "dari mana",
    "diantara": "di antara", "diatas": "di atas", "dibawah": "di bawah",
    "didepan": "di depan", "dibelakang": "di belakang",
    "didalam": "di dalam", "diluar": "di luar",
    "disamping": "di samping", "disekitar": "di sekitar",
    "ditengah": "di tengah",
    "terimakasih": "terima kasih", "tanggungjawab": "tanggung jawab",
    "kerjasama": "kerja sama", "masingmasing": "masing-masing",
    "olehkarena": "oleh karena",
    "dirumah": "di rumah", "disekolah": "di sekolah",
    "dikantor": "di kantor", "dipasar": "di pasar",
    "dikampus": "di kampus", "dikelas": "di kelas",
    "dikota": "di kota",
    "kerumah": "ke rumah", "kesekolah": "ke sekolah",
    "kekantor": "ke kantor", "kepasar": "ke pasar",
    "kekampus": "ke kampus", "kekelas": "ke kelas",
    "kekota": "ke kota",
    "didalamnya": "di dalamnya", "dirumahnya": "di rumahnya",
    "kerjasamanya": "kerja samanya",
    "tanggungjawabnya": "tanggung jawabnya",
}

# Word boundaries so "kerjasama" never matches inside "kerjasamanya"
# (that has its own entry) and "didalam" never matches "didalamnya".
# A clitic suffix (-ku/-mu/-nya/-lah/-kah/-pun) may follow the fused
# form and stays attached to the last word of the fix: "kerjasamaku"
# -> "kerja samaku", "disinilah" -> "di sinilah", "dirumahku" ->
# "di rumahku".
_TYPO_SUFFIXES = ("ku", "mu", "nya", "lah", "kah", "pun")
_TYPO_RE = re.compile(
    r"\b(" + "|".join(sorted(_TYPO_TABLE, key=len, reverse=True)) + r")"
    r"((?:" + "|".join(_TYPO_SUFFIXES) + r"))?\b",
    re.IGNORECASE)


_SUGGEST_NOTES = {
    "id": {
        "nominalization": "Pakai kata kerja langsung.",
        "connectors": "Hapus konektornya — biarkan kalimat menyambung sendiri.",
        "passive": "Pakai bentuk aktif bila pelakunya jelas.",
        "yang_mana": "Tulis ulang tanpa kalke; pisah jadi dua kalimat bila perlu.",
        "rhythm": "Variasikan panjang kalimat: pecah yang panjang, gabung yang pendek.",
        "typo": "Ejaan: kata yang seharusnya dipisah (atau berstrip) ditulis menyatu.",
    },
    "en": {
        "nominalization": "Use the verb directly.",
        "connectors": "Drop the connector — let the sentences connect the argument.",
        "passive": "Use the active form when the actor is clear.",
        "yang_mana": "Rewrite without the calque; split into two sentences if needed.",
        "rhythm": "Vary sentence length: split long ones, join short ones.",
        "typo": "Spelling: words that should be separate (or hyphenated) were written joined.",
    },
}


def suggest_style_fixes(text: str, lang: str = "id",
                        limit: int | None = 10) -> dict:
    """Propose rewrite suggestions for stiff-style patterns in `text`.

    Returns {"suggestions": [...first `limit`...], "count": total}.
    Each suggestion carries pattern, original, replacement (None when
    the fix needs a human decision), context (the sentence), fixed
    (the sentence with the replacement applied, or None), note, and
    the span offsets. Nothing is changed: the caller shows these and
    the author edits by hand. Pass limit=None to get every
    suggestion (used by --apply, which must not miss the tail).
    """
    notes = _SUGGEST_NOTES.get(lang, _SUGGEST_NOTES["id"])
    spans = _sentence_spans(text)
    suggestions = []

    # 1. Light verbs: mechanical when the noun has a verb form.
    for m in _LIGHT_VERB_RE.finditer(text):
        verb, noun = m.group(1), m.group(2)
        start, end = m.start(), m.end()
        tail = re.match(
            r"\s+(terhadap|atas|antara|sebesar|kepada)\b", text[end:])
        if tail:
            end += tail.end()
        repl = _NOUN_TO_VERB.get(noun.lower())
        suggestions.append({
            "pattern": "nominalization",
            "original": text[start:end],
            "replacement": repl,
            "context": _context_sentence(spans, start),
            "fixed": None,
            "note": notes["nominalization"],
            "start": start,
            "end": end,
        })

    # 2. Connectors: delete the connector (and a following comma).
    for conn in _CONNECTORS:
        for m in re.finditer(r"\b" + re.escape(conn) + r"\b",
                             text, re.IGNORECASE):
            start, end = m.start(), m.end()
            if end < len(text) and text[end] == ",":
                end += 1
            suggestions.append({
                "pattern": "connectors",
                "original": text[start:end],
                "replacement": "",
                "context": _context_sentence(spans, start),
                "fixed": None,
                "note": notes["connectors"],
                "start": start,
                "end": end,
            })

    # 3. Passive: one guidance suggestion per sentence that has one.
    for s, e, sent in spans:
        m = re.search(r"\b(" + "|".join(_PASSIVE_VERBS) + r")\b",
                      sent, re.IGNORECASE)
        if m:
            suggestions.append({
                "pattern": "passive",
                "original": m.group(0),
                "replacement": None,
                "context": sent,
                "fixed": None,
                "note": notes["passive"],
                "start": s + m.start(),
                "end": s + m.end(),
            })

    # 4. "yang mana" splits the sentence; "dimana" needs a decision.
    for m in _YANG_MANA_RE.finditer(text):
        word = m.group(0).lower()
        if word == "yang mana":
            start, end = m.start(), m.end()
            sentence_start = (start == 0 or (start >= 2
                              and text[start - 2] in ".!?"
                              and text[start - 1] == " "))
            if sentence_start:
                # "Yang mana" opening a sentence cannot be split off
                # mechanically; leave it as guidance.
                suggestions.append({
                    "pattern": "yang_mana",
                    "original": m.group(0),
                    "replacement": None,
                    "context": _context_sentence(spans, start),
                    "fixed": None,
                    "note": notes["yang_mana"],
                    "start": start,
                    "end": end,
                })
                continue
            if start > 0 and text[start - 1] == ",":
                start -= 1
            elif (start > 1 and text[start - 1] == " "
                    and text[start - 2] == ","):
                # ", yang mana" — swallow comma and space together.
                start -= 2
            elif start > 0 and text[start - 1] == " ":
                # Swallow the space before it, or the "." lands after
                # a gap ("metode . Hasilnya").
                start -= 1
            suggestions.append({
                "pattern": "yang_mana",
                "original": text[start:end],
                "replacement": ".",
                "context": _context_sentence(spans, start),
                "fixed": None,
                "note": notes["yang_mana"],
                "start": start,
                "end": end,
            })
        else:
            suggestions.append({
                "pattern": "yang_mana",
                "original": m.group(0),
                "replacement": None,
                "context": _context_sentence(spans, m.start()),
                "fixed": None,
                "note": notes["yang_mana"],
                "start": m.start(),
                "end": m.end(),
            })

    # 5. Rhythm: only when flagged; the longest sentence is the example.
    style = check_style(text)
    if style["signals"]["rhythm"]["flagged"]:
        longest = max(spans, key=lambda t: len(t[2].split()))
        suggestions.append({
            "pattern": "rhythm",
            "original": longest[2],
            "replacement": None,
            "context": longest[2],
            "fixed": None,
            "note": notes["rhythm"],
            "start": longest[0],
            "end": longest[1],
        })

    # 6. Typos: fused words that EYD writes separate (or hyphenated).
    # Mechanical — the table only holds always-wrong forms.
    for m in _TYPO_RE.finditer(text):
        # A clitic suffix stays attached to the last word of the
        # fix: "kerjasamaku" -> "kerja samaku".
        replacement = (_TYPO_TABLE[m.group(1).lower()]
                       + (m.group(2) or ""))
        suggestions.append({
            "pattern": "typo",
            "original": m.group(0),
            "replacement": replacement,
            "context": _context_sentence(spans, m.start()),
            "fixed": None,
            "note": notes["typo"],
            "start": m.start(),
            "end": m.end(),
        })

    suggestions.sort(key=lambda s: s["start"])
    for sug in suggestions:
        sug["fixed"] = _fixed_sentence(text, sug)
    total = len(suggestions)
    shown = suggestions if limit is None else suggestions[:limit]
    return {"suggestions": shown, "count": total}


_SUGGEST_STRINGS = {
    "id": {
        "heading": "Saran rewrite gaya",
        "more": "Menampilkan {shown} dari {total} saran.",
        "labels": {
            "nominalization": "Verba ringan",
            "connectors": "Konektor",
            "passive": "Verba pasif",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "Ritme kalimat",
            "typo": "Ejaan",
        },
        "before": "Sebelum",
        "after": "Sesudah",
        "none": "Tidak ada saran rewrite — gaya naskah sudah luwes.",
    },
    "en": {
        "heading": "Style rewrite suggestions",
        "more": "Showing {shown} of {total} suggestions.",
        "labels": {
            "nominalization": "Light verbs",
            "connectors": "Connectors",
            "passive": "Passive verbs",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "Sentence rhythm",
            "typo": "Spelling",
        },
        "before": "Before",
        "after": "After",
        "none": "No rewrite suggestions — the style is already fluent.",
    },
}


def format_suggestions(result: dict, lang: str = "id") -> str:
    """Render a suggest_style_fixes() result as readable before/after text."""
    s = _SUGGEST_STRINGS.get(lang, _SUGGEST_STRINGS["id"])
    suggestions = result["suggestions"]
    if not suggestions:
        return s["none"] + "\n"
    lines = [f"{s['heading']} ({result['count']}):"]
    for i, sug in enumerate(suggestions, 1):
        label = s["labels"][sug["pattern"]]
        # The span may swallow a leading space (see suggest_style_fixes);
        # display trims it.
        original = sug["original"].strip()
        if sug["replacement"] is not None:
            repl = "(hapus)" if sug["replacement"] == "" \
                else f"\"{sug['replacement']}\""
            lines.append(
                f"{i}. {label} — \"{original}\" -> {repl}")
            lines.append(f"   {s['before']}: {sug['context']}")
            lines.append(f"   {s['after']}: {sug['fixed']}")
        else:
            lines.append(f"{i}. {label} — \"{original}\"")
            lines.append(f"   {s['before']}: {sug['context']}")
            lines.append(f"   {sug['note']}")
    if result["count"] > len(suggestions):
        lines.append(s["more"].format(shown=len(suggestions),
                                      total=result["count"]))
    return "\n".join(lines) + "\n"


def _apply_one(text: str, sug: dict) -> str:
    """Return `text` with one mechanical suggestion's span replaced.

    Only the neighbourhood of the edit is touched: a double space
    created at the splice is collapsed, and a sentence-initial letter
    is capitalized only when the edit itself starts a sentence or
    ends one (a "yang mana" split). Text the suggestion does not
    cover is left exactly as it was.
    """
    start, end = sug["start"], sug["end"]
    repl = sug["replacement"] or ""
    left, right = text[:start], text[end:]
    # Drop one space only where the splice would otherwise double it:
    # the replacement ends in a space followed by one, or an empty
    # replacement between two spaces (or at the start of the text).
    # Anything else — including pre-existing double spaces — is left
    # alone.
    if right.startswith(" "):
        if repl.endswith(" "):
            right = right[1:]
        elif not repl and (not left or left.endswith(" ")):
            right = right[1:]
    new = left + repl + right
    before = text[:start].rstrip()
    at_sent_start = not before or before[-1] in ".!?"
    ends_sentence = bool(repl) and repl[-1] in ".!?"
    target = None
    if ends_sentence:
        target = start + len(repl)
    elif at_sent_start:
        target = start
    if target is not None:
        m = re.search(r"[A-Za-z]", new[target:])
        if m:
            i = target + m.start()
            new = new[:i] + new[i].upper() + new[i + 1:]
    return new


def apply_suggestions(text: str, result: dict) -> dict:
    """Apply the mechanical suggestions of a suggest_style_fixes()
    result to `text` and return the fixed text plus a report.

    Returns {"text": fixed text, "applied": [...], "skipped": [...]}.
    Guidance-only suggestions (replacement None) are skipped — they
    need a human decision — and so is any suggestion whose span
    overlaps one already applied. Edits run from the end of the text
    backwards, so earlier offsets stay valid.
    """
    applied, skipped = [], []
    used = []  # (start, end) spans already applied, original coords
    new = text
    for sug in sorted(result["suggestions"],
                      key=lambda s: s["start"], reverse=True):
        if sug["replacement"] is None:
            skipped.append(sug)
            continue
        if any(sug["start"] < e and s < sug["end"] for s, e in used):
            skipped.append(sug)
            continue
        new = _apply_one(new, sug)
        used.append((sug["start"], sug["end"]))
        applied.append(sug)
    applied.reverse()
    skipped.reverse()
    return {"text": new, "applied": applied, "skipped": skipped}


def analyze_text_quality(
    text: str,
    references: dict | None = None,
    *,
    lang: str = "id",
    verify_dois: bool = True,
    suggest: bool = False,
) -> dict:
    """Analyze an academic text for quality: jargon, citations, DOI status,
    style, and bibliography completeness.

    Returns a dict with keys:
    - jargon: list of detected jargon terms with explanations
    - citations: citation audit result (cited, missing, unused)
    - doi_verification: per-reference DOI check results
    - style: style check result (signals, style_score, flagged)
    - quality_score: composite score 0-100
    - readability: Flesch Reading Ease + Flesch-Kincaid Grade Level
      (readability_score) — always computed, purely informative:
      it never changes quality_score or the four score parts
    - recommendations: list of improvement suggestions
    - suggestions: rewrite suggestions from suggest_style_fixes()
      (empty unless suggest=True)

    If `references` is provided, citation audit and DOI verification are
    performed against it. Otherwise, citation and DOI checks are skipped.
    The style check always runs; its lexical signals are calibrated
    for Indonesian academic prose.

    Raises ValueError("teks kosong") for an empty or whitespace-only
    text: an empty manuscript has nothing to score, and must not
    come back as a perfect 100.
    """
    if not text or not text.strip():
        raise ValueError("teks kosong")
    result = {
        "jargon": [],
        "citations": None,
        "doi_verification": {},
        "style": check_style(text),
        "quality_score": 0,
        # Readability is cheap (counts only, no network) and always
        # computed; it is informative only and never feeds the score.
        "readability": readability_score(text, lang=lang),
        "recommendations": [],
        "suggestions": {"suggestions": [], "count": 0},
    }
    if suggest:
        result["suggestions"] = suggest_style_fixes(text, lang=lang)

    # --- Jargon detection ---
    jargon_matches = find_terms(text)
    jargon_explanations = [
        {
            "term": m["term"],
            "original": m["original"],
            "translation": m["translation"],
            "field": m["field"],
            "source": m["source"],
        }
        for m in jargon_matches
    ]
    result["jargon"] = jargon_explanations

    # --- Citation audit ---
    if references is not None:
        citation_result = audit_citations(text, references)
        result["citations"] = {
            "cited": citation_result["cited"],
            "counts": citation_result["counts"],
            "missing": citation_result["missing"],
            "unused": citation_result["unused"],
        }

        # --- DOI verification ---
        if verify_dois:
            doi_result = verify_reference_dois(references)
            result["doi_verification"] = doi_result

    # --- Quality score calculation ---
    # Four parts of 25 (max 100): jargon, citations, DOI, style.
    score_parts = []

    # Jargon: every term found is explained by construction, so a run
    # with terms scores 25; a text with no recognised jargon is
    # neutral (also 25). The jargon component is therefore a fixed
    # 25 by design, and the effective score floor is 75 with no
    # references and 38 with references (style 0 + citations 0
    # + DOI 0).
    score_parts.append(25)

    # Citations completeness: the share of cited markers that have a
    # bibliography entry. All citations missing scores 0, not 12.5.
    if references is not None:
        cit = result["citations"]
        total_cited = len(cit["cited"]) if cit else 0
        total_missing = len(cit["missing"]) if cit else 0
        if total_cited == 0:
            score_parts.append(25)  # nothing cited = neutral
        else:
            score_parts.append(
                25 * (total_cited - total_missing) / total_cited)
    else:
        score_parts.append(25)  # no refs to audit = neutral

    # DOI verification quality: only entries that actually carry a DOI
    # count — a reference without one is not a failed verification.
    # An 'unverified' DOI (one source could not be checked) earns
    # half credit: not checked is not the same as confirmed fake.
    doi_result = result.get("doi_verification", {})
    if doi_result:
        checkable = [v for v in doi_result.values() if v.get("doi")]
        if checkable:
            ok_count = sum(1 for v in checkable if v.get("verdict") == "ok")
            unverified = sum(
                1 for v in checkable if v.get("verdict") == "unverified")
            score_parts.append(
                25 * (ok_count + 0.5 * unverified) / len(checkable))
        else:
            score_parts.append(25)  # no DOIs to verify = neutral
    else:
        score_parts.append(25)  # no references = neutral

    # Style: 0-25 from check_style, five points per clean signal.
    score_parts.append(result["style"]["style_score"])

    total_score = sum(score_parts)
    result["quality_score"] = _round_half_up(min(total_score, 100))

    # --- Recommendations ---
    en = lang == "en"
    recs = []
    if result["citations"]:
        cit = result["citations"]
        if cit["missing"]:
            if en:
                recs.append(
                    f"{len(cit['missing'])} citations in the text have no bibliography entry: "
                    + ", ".join(cit["missing"])
                )
            else:
                recs.append(
                    f"{len(cit['missing'])} sitasi di naskah tidak ada di bibliografi: "
                    + ", ".join(cit["missing"])
                )
        if cit["unused"]:
            if en:
                recs.append(
                    f"{len(cit['unused'])} bibliography entries are never cited: "
                    + ", ".join(cit["unused"][:5])
                )
            else:
                recs.append(
                    f"{len(cit['unused'])} entri di bibliografi tidak pernah dikutip: "
                    + ", ".join(cit["unused"][:5])
                )
    if result["doi_verification"]:
        dv = result["doi_verification"]
        bad = [k for k, v in dv.items()
               if v["verdict"] in ("unverified", "missing")]
        if bad:
            if en:
                recs.append(
                    f"{len(bad)} DOIs unverified: " + ", ".join(bad)
                )
            else:
                recs.append(
                    f"{len(bad)} DOI belum terverifikasi: " + ", ".join(bad)
                )
    style = result["style"]
    for name in style["flagged"]:
        sig = style["signals"][name]
        if name == "nominalization":
            ex = ", ".join(f"'{e}'" for e in sig["examples"])
            if en:
                recs.append(
                    f"Style: {sig['count']} light-verb constructions "
                    f"({ex}) — use the verb directly."
                )
            else:
                recs.append(
                    f"Gaya: {sig['count']} konstruksi verba ringan "
                    f"({ex}) — pakai kata kerja langsung."
                )
        elif name == "connectors":
            if en:
                recs.append(
                    f"Style: {sig['count']} connectors "
                    f"({sig['density_per_100']}/100 words) — let the "
                    "sentences connect the argument instead."
                )
            else:
                recs.append(
                    f"Gaya: {sig['count']} konektor "
                    f"({sig['density_per_100']}/100 kata) — kurangi "
                    "penghubung, biarkan alur kalimat yang menyambung."
                )
        elif name == "passive":
            if en:
                recs.append(
                    f"Style: {sig['count']} passive verbs piled up — "
                    "use the active form when the actor is clear."
                )
            else:
                recs.append(
                    f"Gaya: {sig['count']} verba pasif menumpuk — "
                    "pakai bentuk aktif bila pelakunya jelas."
                )
        elif name == "yang_mana":
            if en:
                recs.append(
                    "Style: 'yang mana' / 'dimana' used as a relative "
                    "pronoun — rewrite without the calque."
                )
            else:
                recs.append(
                    "Gaya: 'yang mana' / 'dimana' sebagai kata ganti "
                    "relatif — tulis ulang tanpa kalke."
                )
        elif name == "rhythm":
            if en:
                recs.append(
                    "Style: sentence lengths are too uniform — vary "
                    "short and long sentences."
                )
            else:
                recs.append(
                    "Gaya: panjang kalimat terlalu seragam — variasikan "
                    "kalimat pendek dan panjang."
                )
    if not jargon_matches:
        if en:
            recs.append(
                "No recognised academic jargon found — consider adding "
                "terms to the dictionary"
            )
        else:
            recs.append(
                "Tidak ditemukan jargon akademik yang dikenali — pertimbangkan "
                "menambahkan istilah ke dictionary.json"
            )
    if not references:
        if en:
            recs.append(
                "Add a bibliography JSON file for citation audit and DOI verification."
            )
        else:
            recs.append(
                "Tambahkan bibliografi JSON untuk audit sitasi dan verifikasi DOI."
            )
    result["recommendations"] = recs

    return result


_ANALYZE_STRINGS = {
    "id": {
        "heading": "Analisis Kualitas Naskah",
        "score": "Skor kualitas",
        "jargon": "Istilah jargon ditemukan",
        "jargon_none": "Tidak ada istilah jargon yang dikenali.",
        "citations": "Sitasi",
        "cited": "dikutip",
        "missing": "hilang dari bibliografi",
        "unused": "tak terpakai",
        "doi": "Verifikasi DOI",
        "doi_none": "Tidak ada DOI untuk diverifikasi.",
        "style": "Gaya",
        "style_clean": "tidak ada pola kaku yang terdeteksi",
        "duplicates": "Duplikasi",
        "duplicates_none": "Tidak ada kalimat yang berulang dengan pustaka.",
        "duplicates_found": "kalimat berulang",
        "duplicates_truncated": ("Peringatan: pemeriksaan duplikasi berhenti "
                                "setelah {spent} perbandingan (batas {budget}) "
                                "— hasil mungkin tidak lengkap."),
        "duplicates_similar": "mirip",
        "duplicates_in_text": "naskah ini",
        "duplicates_in_library": "pustaka",
        "signals": {
            "nominalization": "verba ringan",
            "connectors": "konektor",
            "passive": "verba pasif",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "ritme kalimat",
        },
        "rhythm_same": "{pct}% kalimat hampir sama panjang",
        "recs": "Rekomendasi",
        "recs_none": "Tidak ada rekomendasi — naskah sudah rapi.",
        "no_refs": "Tanpa bibliografi: audit sitasi dan verifikasi DOI dilewati.",
        "readability": "Keterbacaan",
        "readability_detail": ("Rata-rata {wps} kata/kalimat, "
                               "{spw} suku kata/kata"),
    },
    "en": {
        "heading": "Text Quality Analysis",
        "score": "Quality score",
        "jargon": "Jargon terms found",
        "jargon_none": "No recognised jargon terms.",
        "citations": "Citations",
        "cited": "cited",
        "missing": "missing from bibliography",
        "unused": "unused",
        "doi": "DOI verification",
        "doi_none": "No DOIs to verify.",
        "style": "Style",
        "style_clean": "no stiff patterns detected",
        "duplicates": "Duplication",
        "duplicates_none": "No sentences repeat the library.",
        "duplicates_found": "repeated sentences",
        "duplicates_truncated": ("Warning: the duplication check stopped "
                                "after {spent} comparisons (limit {budget}) "
                                "— results may be incomplete."),
        "duplicates_similar": "similar to",
        "duplicates_in_text": "this text",
        "duplicates_in_library": "library",
        "signals": {
            "nominalization": "light verbs",
            "connectors": "connectors",
            "passive": "passive verbs",
            "yang_mana": "'yang mana'/'dimana'",
            "rhythm": "sentence rhythm",
        },
        "rhythm_same": "{pct}% of sentences nearly the same length",
        "recs": "Recommendations",
        "recs_none": "No recommendations — the text is in good shape.",
        "no_refs": "No bibliography: citation audit and DOI verification skipped.",
        "readability": "Readability",
        "readability_detail": ("Average {wps} words/sentence, "
                               "{spw} syllables/word"),
    },
}


_SCORE_PART_LABELS = {
    "id": ("Jargon", "Sitasi", "DOI", "Gaya"),
    "en": ("Jargon", "Citations", "DOI", "Style"),
}


def _round_half_up(x: float) -> int:
    """Round half up (12.5 -> 13), unlike Python's round() which
    rounds half to even (12.5 -> 12). Scores are never negative,
    so int(x + 0.5) is exact here. One helper for the total and
    every displayed component, so the parts always add up to the
    total (and match the web UI, where Math.round is also half-up)."""
    return int(x + 0.5)


def _score_parts(result: dict) -> list:
    """The four 25-point components behind quality_score.

    Mirrors the scoring in analyze_text_quality(): jargon is always
    25 (every term found is explained by construction, and a text
    with no recognised jargon is neutral) — so the effective score
    floor is 75 with no references and 38 with references (style 0
    + citations 0 + DOI 0). Citations lose points for missing
    entries: 25 * (cited - missing) / cited. DOI gives half credit
    (12.5) for an 'unverified' verdict: a DOI that could not be
    checked is not the same as a confirmed fake ('missing').
    """
    parts = [25.0]
    cit = result["citations"]
    if cit is None:
        parts.append(25.0)
    else:
        cited, missing = len(cit["cited"]), len(cit["missing"])
        parts.append(25.0 if cited == 0 else
                     25 * (cited - missing) / cited)
    dv = result.get("doi_verification", {})
    checkable = [v for v in dv.values() if v.get("doi")]
    if checkable:
        ok = sum(1 for v in checkable if v.get("verdict") == "ok")
        unverified = sum(1 for v in checkable
                         if v.get("verdict") == "unverified")
        parts.append(25 * (ok + 0.5 * unverified) / len(checkable))
    else:
        parts.append(25.0)
    parts.append(float(result["style"].get("style_score", 0)))
    return parts


def format_analyze(result: dict, lang: str = "id") -> str:
    """Render an analyze_text_quality() result as readable text."""
    s = _ANALYZE_STRINGS.get(lang, _ANALYZE_STRINGS["id"])
    lines = [s["heading"], "",
             _bold(f"{s['score']}: {result['quality_score']}/100"),
             _green(_bar(result["quality_score"], 100))]
    labels = _SCORE_PART_LABELS.get(lang, _SCORE_PART_LABELS["id"])
    for label, value in zip(labels, _score_parts(result)):
        lines.append(f"{label:<10} {_green(_bar(value, 25))} "
                     f"{_round_half_up(value):>2}/25")
    lines.append("")
    read = result.get("readability")
    if read:
        lines.append(f"{s['readability']}: Flesch Reading Ease "
                     f"{read['flesch_reading_ease']}/100 "
                     f"({read['band']}) — "
                     f"FKGL {read['flesch_kincaid_grade']}")
        lines.append("  " + s["readability_detail"].format(
            wps=read["avg_words_per_sentence"],
            spw=read["avg_syllables_per_word"]))
        lines.append("  " + read["note"])
    lines.append("")
    jargon = result["jargon"]
    if jargon:
        lines.append(f"{s['jargon']}: {len(jargon)}")
        for item in jargon:
            lines.append(f"  - {item['term']}: {item['translation']}")
    else:
        lines.append(s["jargon_none"])
    cit = result["citations"]
    if cit is None:
        lines.append(s["no_refs"])
    else:
        lines.append(
            f"{s['citations']}: {len(cit['cited'])} {s['cited']}, "
            f"{len(cit['missing'])} {s['missing']}, "
            f"{len(cit['unused'])} {s['unused']}"
        )
        if cit["missing"]:
            lines.append("  " + ", ".join(cit["missing"]))
    dv = result["doi_verification"]
    if dv:
        ok = sum(1 for v in dv.values() if v.get("verdict") == "ok")
        with_doi = sum(1 for v in dv.values() if v.get("doi"))
        lines.append(f"{s['doi']}: {ok}/{with_doi} ok")
        bad = [k for k, v in dv.items()
               if v.get("doi") and v.get("verdict") != "ok"]
        if bad:
            lines.append("  " + ", ".join(bad))
    else:
        lines.append(s["doi_none"])
    style = result["style"]
    if style["flagged"]:
        lines.append(f"{s['style']}: {style['style_score']}/25")
        for name in style["flagged"]:
            sig = style["signals"][name]
            label = s["signals"][name]
            if name == "rhythm":
                pct = int(sig["same_length_share"] * 100)
                lines.append(f"  - {label}: "
                             + s["rhythm_same"].format(pct=pct))
            else:
                ex = ", ".join(f"'{e}'" for e in sig["examples"])
                lines.append(f"  - {label}: {sig['count']}"
                             + (f" ({ex})" if ex else ""))
    else:
        lines.append(f"{s['style']}: {style['style_score']}/25 — "
                     f"{s['style_clean']}")
    dups = result.get("duplicates")
    if dups is not None:
        if dups.get("truncated"):
            lines.append(s["duplicates_truncated"].format(
                spent=dups.get("comparisons_spent", "?"),
                budget=_MAX_DUPLICATE_COMPARISONS))
        if dups["duplicates"]:
            lines.append(f"{s['duplicates']}: {dups['count']} "
                         f"{s['duplicates_found']}")
            for d in dups["duplicates"]:
                sent = d["sentence"]
                if len(sent) > 90:
                    sent = sent[:90].rstrip() + "…"
                match = d["match"]
                if len(match) > 90:
                    match = match[:90].rstrip() + "…"
                if d["source_id"] is None:
                    source = s["duplicates_in_text"]
                else:
                    source = (f"{s['duplicates_in_library']} "
                              f"#{d['source_id']}")
                lines.append(f"  - \"{sent}\" — {d['similarity']:.0%} "
                             f"{s['duplicates_similar']} \"{match}\" "
                             f"({source})")
        else:
            lines.append(s["duplicates_none"])
    sugs = result.get("suggestions") or {"suggestions": [], "count": 0}
    if sugs["suggestions"]:
        lines.append(format_suggestions(sugs, lang=lang).rstrip("\n"))
    recs = result["recommendations"]
    lines.append(f"{s['recs']}:")
    if recs:
        for r in recs:
            lines.append(f"  - {r}")
    else:
        lines.append(f"  {s['recs_none']}")
    return "\n".join(lines) + "\n"


def analyze_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Check an academic text — or every .txt/.md file in a "
                    "folder: jargon, citations, DOI verification, and style "
                    "in one pass.")
    p.add_argument("input", nargs="?", help="plain-text file (or a folder of "
                   ".txt/.md files) to analyze")
    p.add_argument("--text", help="analyze this text instead of a file")
    p.add_argument("--refs", help="bibliography JSON file (optional; without "
                   "it, citation audit and DOI checks are skipped)")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--no-verify", action="store_true",
                   help="skip DOI verification even when --refs is given")
    p.add_argument("--suggest", action="store_true",
                   help="also show style rewrite suggestions (before/after)")
    p.add_argument("--save", action="store_true",
                   help="record this run in the library "
                        "(~/.academic-tools/library.db)")
    p.add_argument("--duplicates", action="store_true",
                   help="also check sentences against saved runs in the "
                        "library (same database as --save)")
    p.add_argument("--title", help="label for the saved run "
                   "(default: first line of the text)")
    p.add_argument("--db", help="library database path (with --save or "
                   "--duplicates)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.input and os.path.isdir(args.input):
        if args.suggest:
            p.error("--suggest tidak didukung untuk folder")
        if args.title:
            p.error("--title tidak didukung untuk folder")
        if args.text is not None:
            p.error("--text tidak bisa dipakai bersama folder")
        return _analyze_folder_main(args)

    if args.text is not None:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")

    references = None
    if args.refs:
        if not os.path.isfile(args.refs):
            raise ValueError(f"File tidak ditemukan: {args.refs}")
        references = load_references(args.refs)
    result = analyze_text_quality(text, references, lang=args.lang,
                                  verify_dois=not args.no_verify,
                                  suggest=args.suggest)
    if args.duplicates:
        try:
            result["duplicates"] = find_duplicates(text, db=args.db)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
    if args.save:
        try:
            result["library_id"] = save_analysis(
                text, result, references, title=args.title, db=args.db)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
    if args.json:
        # The web /api/analyze response carries score_parts; the CLI
        # --json matches it so the components never need recomputing.
        result["score_parts"] = _score_parts(result)
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_analyze(result, lang=args.lang))
        if args.save:
            sys.stdout.write(
                f"Tersimpan di pustaka (id {result['library_id']})\n")
    bad_doi = any(v.get("verdict") == "missing"
                  for v in result["doi_verification"].values())
    missing = result["citations"]["missing"] if result["citations"] else []
    return 1 if missing or bad_doi else 0


_FOLDER_EXTENSIONS = (".txt", ".md")


def _blank_folder_entry(name: str) -> dict:
    """The blank entry analyze_folder (and the web folder upload) fill
    in for one file."""
    return {"file": name, "text": None, "result": None,
            "quality_score": None, "jargon_count": 0,
            "citations_cited": 0, "citations_missing": [],
            "doi_ok": 0, "doi_total": 0, "doi_missing": 0,
            "style_score": None, "duplicates": None,
            "duplicates_truncated": False,
            "duplicates_comparisons_spent": None,
            "library_id": None, "error": None}


def _analyze_one_file(entry: dict, text: str, references=None, *,
                      lang: str = "id", verify_dois: bool = True,
                      duplicates: bool = False, save: bool = False,
                      db=None) -> dict:
    """Fill one folder-result entry from an already-read text: the
    analyze pass, the optional duplicates check, and the optional
    library save (recorded under the file name). Returns the entry.

    A file that fails a step (empty text, a duplicates check against
    a corrupt library, a failed save) is recorded with its error
    and left out of the folder average — one policy for every kind
    of failure, including unreadable files.
    """
    entry["text"] = text
    try:
        result = analyze_text_quality(text, references, lang=lang,
                                      verify_dois=verify_dois)
    except ValueError as e:
        entry["error"] = str(e)
        return entry
    entry["result"] = result
    entry["quality_score"] = result["quality_score"]
    entry["jargon_count"] = len(result["jargon"])
    if result["citations"]:
        entry["citations_cited"] = len(result["citations"]["cited"])
        entry["citations_missing"] = result["citations"]["missing"]
    doi = result["doi_verification"]
    entry["doi_total"] = sum(1 for v in doi.values() if v.get("doi"))
    entry["doi_ok"] = sum(1 for v in doi.values()
                          if v.get("verdict") == "ok")
    entry["doi_missing"] = sum(1 for v in doi.values()
                               if v.get("verdict") == "missing")
    entry["style_score"] = result["style"]["style_score"]
    if duplicates:
        try:
            # Audit #6 B-1: the folder path used to keep only the
            # count, silently dropping the truncation flag — the
            # same silent cut audit #5 B-1 fixed for single files.
            # Keep "duplicates" as the count (CLI table, API and
            # web UI read it as a number) and carry the flag and
            # the spent budget alongside it, like find_duplicates.
            dup = find_duplicates(text, db=db)
            entry["duplicates"] = dup["count"]
            entry["duplicates_truncated"] = dup.get("truncated", False)
            entry["duplicates_comparisons_spent"] = dup.get(
                "comparisons_spent")
        except ValueError as e:
            # Record the failure, but still try the save below.
            entry["error"] = str(e)
    if save:
        try:
            entry["library_id"] = save_analysis(
                text, result, references, title=entry["file"], db=db)
        except ValueError as e:
            entry["error"] = str(e)
    return entry


def analyze_folder(folder: str, references=None, *, lang: str = "id",
                   verify_dois: bool = True, duplicates: bool = False,
                   save: bool = False, db=None) -> dict:
    """Analyze every top-level .txt/.md file in `folder`.

    Dotfiles (names starting with ".") are skipped, and the order
    is case-insensitive, so "Bab2.md" sorts next to "bab1.txt".

    Each file is one analyze_text_quality() pass. With `duplicates`,
    each file is also checked against the library — and, when `save`
    is on, files analyzed earlier in this same run are already in the
    library, so a sentence repeated in a later chapter is flagged.
    With `save`, each run is recorded in the library with the file
    name as its title.

    Returns {"folder", "files": [...], "count": n, "average": float|None}.
    Each file's "result" carries "score_parts" (the four 25-point
    components), like the single-file --json output.
    A file entry carries file, text, result (the full analyze pass),
    quality_score, jargon_count, citations_cited, citations_missing,
    doi_ok, doi_total, doi_missing, style_score, duplicates (count, or
    None when not checked), duplicates_truncated (True when the
    duplicates check hit the work budget — the count may be
    incomplete) and duplicates_comparisons_spent (comparisons
    actually performed, or None when not checked), library_id
    (or None), and error (None when the file was read and analyzed).
    A file that cannot be read (bad encoding, permissions) is recorded
    with its error and the rest still run.
    """
    names = sorted(
        (n for n in os.listdir(folder)
         if not n.startswith(".")
         and n.lower().endswith(_FOLDER_EXTENSIONS)
         and os.path.isfile(os.path.join(folder, n))),
        key=str.lower)
    entries = []
    for name in names:
        path = os.path.join(folder, name)
        entry = _blank_folder_entry(name)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            entry["error"] = str(e)
            entries.append(entry)
            continue
        entries.append(_analyze_one_file(entry, text, references,
                                         lang=lang,
                                         verify_dois=verify_dois,
                                         duplicates=duplicates, save=save,
                                         db=db))
        # The CLI folder --json carries the four components per
        # file, like the single-file --json and /api/analyze.
        if entries[-1]["result"] is not None:
            entries[-1]["result"]["score_parts"] = _score_parts(
                entries[-1]["result"])
    scores = [e["quality_score"] for e in entries
              if e["quality_score"] is not None and not e.get("error")]
    average = round(sum(scores) / len(scores), 1) if scores else None
    return {"folder": folder, "files": entries, "count": len(entries),
            "average": average}


_FOLDER_STRINGS = {
    "id": {
        "heading": "Analisis folder",
        "files": "file",
        "average": "Rata-rata",
        "none": "Tidak ada file .txt atau .md di folder ini.",
        "columns": ("File", "Skor", "Jargon", "Sitasi", "DOI", "Gaya",
                    "Duplikat"),
        "cited": "{n} dikutip",
        "missing": "{n} hilang",
        "dash": "-",
        "failed": "Gagal",
    },
    "en": {
        "heading": "Folder analysis",
        "files": "files",
        "average": "Average",
        "none": "No .txt or .md files in this folder.",
        "columns": ("File", "Score", "Jargon", "Citations", "DOI", "Style",
                    "Duplicates"),
        "cited": "{n} cited",
        "missing": "{n} missing",
        "dash": "-",
        "failed": "Failed",
    },
}


def format_folder_result(result: dict, lang: str = "id") -> str:
    """Render an analyze_folder() result as a recap table."""
    s = _FOLDER_STRINGS.get(lang, _FOLDER_STRINGS["id"])
    files = result["files"]
    if not files:
        return s["none"] + "\n"
    rows = []
    for e in files:
        if e["error"]:
            rows.append((e["file"], s["dash"], s["dash"], s["dash"],
                         s["dash"], s["dash"], s["dash"]))
            continue
        if e["citations_missing"]:
            cites = s["missing"].format(n=len(e["citations_missing"]))
        elif e["citations_cited"]:
            cites = s["cited"].format(n=e["citations_cited"])
        else:
            cites = s["dash"]
        doi = (f"{e['doi_ok']}/{e['doi_total']}" if e["doi_total"]
               else s["dash"])
        dups = (str(e["duplicates"]) if e["duplicates"] is not None
                else s["dash"])
        rows.append((e["file"], str(e["quality_score"]),
                     str(e["jargon_count"]), cites, doi,
                     str(e["style_score"]), dups))
    cols = list(zip(s["columns"], *rows))
    widths = [max(len(c) for c in col) for col in cols]
    lines = [f"{s['heading']}: {result['folder']} "
             f"({result['count']} {s['files']})"]
    header = "  ".join(h.ljust(w) for h, w in zip(s["columns"], widths))
    lines.append(header)
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(
            c.ljust(w) if i == 0 else c.rjust(w)
            for i, (c, w) in enumerate(zip(row, widths))))
    if result["average"] is not None:
        lines.append(f"{s['average']}: {result['average']}")
    for e in files:
        if e["error"]:
            lines.append(f"{s['failed']}: {e['file']} — {e['error']}")
    # Audit #6 B-1: a truncated duplicates check must warn here
    # too, with the same wording as the single-file path — a
    # short count in the table is never a complete check.
    a = _ANALYZE_STRINGS.get(lang, _ANALYZE_STRINGS["id"])
    for e in files:
        if e.get("duplicates_truncated"):
            lines.append(
                f"{e['file']}: " + a["duplicates_truncated"].format(
                    spent=e.get("duplicates_comparisons_spent", "?"),
                    budget=_MAX_DUPLICATE_COMPARISONS))
    return "\n".join(lines) + "\n"


def _analyze_folder_main(args) -> int:
    references = None
    if args.refs:
        references = load_references(args.refs)
    result = analyze_folder(
        args.input, references, lang=args.lang,
        verify_dois=not args.no_verify, duplicates=args.duplicates,
        save=args.save, db=args.db)
    if not result["files"]:
        print(f"Tidak ada file .txt atau .md di {args.input}",
              file=sys.stderr)
        return 1
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2)
                         + "\n")
    else:
        sys.stdout.write(format_folder_result(result, lang=args.lang))
        if args.save:
            saved = [e for e in result["files"] if e["library_id"]]
            sys.stdout.write(f"Tersimpan di pustaka: {len(saved)} file\n")
    failed = any(e["error"] or e["citations_missing"] or e["doi_missing"]
                 for e in result["files"])
    return 1 if failed else 0


# ======================================================================
# Duplicate sentences: the text against its own saved drafts
# ======================================================================

def _normalize_sentence(sentence: str) -> str:
    """Lowercase, no punctuation, single spaces — for comparison only."""
    cleaned = re.sub(r"[^\w\s]", " ", sentence.lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _word_overlap(a: set, b: set) -> float:
    """Shared words over the shorter sentence's word count (0-1)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _sentence_similarity(a: str, b: str) -> float:
    """0-1 similarity of two normalized sentences (difflib ratio)."""
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _past_texts(db=None) -> list:
    """Saved runs as {id, title, created_at, text, text_hash}, newest first.

    At most the 100 newest runs: the duplication check compares
    every sentence against the corpus, and an unbounded library
    would make it slower with every saved run. When the library
    file does not exist yet there is nothing to compare against.
    """
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return []
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, text, text_hash FROM analyses "
            "ORDER BY id DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    return [{"id": r["id"], "title": r["title"],
             "created_at": r["created_at"], "text": r["text"],
             "text_hash": r["text_hash"]} for r in rows]


def _overlap_gate(words_a: set, words_b: set) -> bool:
    """True when a pair deserves a difflib comparison. The
    word-overlap pre-filter (half the words of the shorter sentence
    shared) is skipped when either sentence has fewer than 3 unique
    words: a one-word sentence can never reach 0.5 overlap even
    when it is nearly identical ("pengukuranpengukuran" vs
    "pengukuran pengukuran" scores 0.96 on difflib)."""
    if len(words_a) < 3 or len(words_b) < 3:
        return True
    return _word_overlap(words_a, words_b) >= 0.5


def _build_word_index(entries: list) -> dict:
    """Inverted index over sentence word sets: word -> entry positions.

    Each entry is a (normalized, raw, word set, run) tuple; a word
    occurs at most once per entry because the third element is a
    set, so every posting list holds each position once.
    """
    index: dict = {}
    for pos, entry in enumerate(entries):
        for word in entry[2]:
            index.setdefault(word, []).append(pos)
    return index


def _gated_candidates(words: set, entries: list, index: dict,
                      short_positions: list, min_pos: int = 0) -> list:
    """Entry positions that pass the overlap gate, in entry order.

    Exactly the pairs _overlap_gate would admit, found through the
    inverted index instead of scanning every entry: a pair passes
    only when the two word sets share at least half the words of
    the shorter one, so a candidate must share at least one word
    with the query — unless either side has fewer than 3 unique
    words, in which case the gate always passes (see _overlap_gate)
    and the entry is listed in short_positions. Positions come back
    in entry order, so the best-match choice (first maximum wins)
    is identical to the old nested loops.
    """
    if len(words) < 3:
        return list(range(min_pos, len(entries)))
    counts: dict = {}
    for word in words:
        for pos in index.get(word, ()):
            if pos >= min_pos:
                counts[pos] = counts.get(pos, 0) + 1
    n = len(words)
    gated = [pos for pos, shared in counts.items()
             if 2 * shared >= min(n, len(entries[pos][2]))]
    for pos in short_positions:
        if pos >= min_pos and pos not in counts:
            gated.append(pos)
    gated.sort()
    return gated


def _is_own_run(run: dict, text_hash: str, legacy_hash: str,
                ws_hash: str | None = None) -> bool:
    """True when a saved run is the text's own copy.

    Primary: the stored text_hash column matches the canonical
    hash, or the v1.25.2 legacy hash (truncate-then-strip). Fallback:
    the stored text itself, hashed canonically, matches — for a run
    saved with no hash, or by v1.25.1 with its full text. The
    fallback also rescues runs saved by v1.27.1, whose stored hash
    was taken after a second strip (see _canonical_text): with the
    idempotent canonical form, hashing their stored text now gives
    the same value as hashing the text being checked. Last
    fallback (audit #6 N-5): the whitespace-collapsed hash — a run
    re-typed with double spaces or tabs inside is still its own
    copy, even though its byte-exact hash differs.
    """
    stored = run.get("text_hash")
    if stored in (text_hash, legacy_hash):
        return True
    if _stored_hash(run.get("text") or "") == text_hash:
        return True
    if ws_hash is not None:
        return _ws_collapsed_hash(run.get("text") or "") == ws_hash
    return False


# Work budget for find_duplicates (audit #4, N-15): the number of
# difflib comparisons one call may perform. A normal check compares
# a few hundred sentence pairs at most — the overlap gate rejects
# the rest — so the budget is rarely reached; but a legitimate,
# heavily derivative text (hundreds of sentences sharing one small
# vocabulary, audit #5 B-1) DOES exhaust it, and the call then
# stops comparing and returns the matches found so far. That
# truncation is honest: the result always carries "truncated" and
# "comparisons_spent", and every renderer (format_duplicates, the
# analyze report, the web UI) warns the user when it happened.
_MAX_DUPLICATE_COMPARISONS = 2000


def find_duplicates(text: str, db=None, *, threshold: float = 0.8,
                    min_words: int = 6, past_runs=None) -> dict:
    """Find sentences in `text` that repeat the user's own saved drafts.

    Each sentence of at least `min_words` words is compared against
    every sentence of every saved analysis in the library, plus against
    the other sentences of the text itself. A match is a normalized
    difflib ratio of at least `threshold`; only the best match per
    sentence is reported. The text itself is never matched against
    its own saved copy: runs are excluded by their stored text_hash
    (canonical hash, or the v1.25.2 legacy hash), so re-analyzing a
    saved run — however long — does not flag every sentence. A
    word-overlap pre-filter (half the words of the shorter sentence
    shared) keeps the comparison fast: candidates are found through
    an inverted word index instead of a full scan, and a work budget
    (_MAX_DUPLICATE_COMPARISONS difflib comparisons per call) caps
    pathological inputs at a few seconds.

    Returns {"duplicates": [...], "count": n, "checked": m,
    "truncated": bool, "comparisons_spent": k} where m is the number
    of saved runs compared and k is the number of difflib
    comparisons actually performed. "truncated" is True exactly
    when the work budget (_MAX_DUPLICATE_COMPARISONS) was exhausted:
    the call stopped comparing early, so "duplicates" may be
    incomplete — some sentences were never compared. It is False
    (and k is below the budget) on a normal input, where the result
    is complete. Each duplicate carries sentence, match,
    similarity, source_id, source_title, source_date; a repeat
    inside the text itself has source_id None and source_title
    "naskah ini".
    """
    if not 0 < threshold <= 1:
        raise ValueError("threshold harus di antara 0 dan 1")
    if min_words < 1:
        raise ValueError("min_words harus >= 1")
    sentences = [s for s in _split_sentences(text)
                 if len(s.split()) >= min_words]
    if past_runs is None:
        # Exclude the text's own saved copy by its stored hash —
        # the canonical hash, or the v1.25.2 legacy hash for runs
        # saved before the canonical form existed (see _is_own_run).
        # The whitespace-collapsed hash is passed along so a copy
        # re-typed with different internal spacing is still
        # recognised as its own run (audit #6 N-5).
        text_hash = _stored_hash(text)
        legacy_hash = _legacy_stored_hash(text)
        ws_hash = _ws_collapsed_hash(text)
        past_runs = [r for r in _past_texts(db)
                     if not _is_own_run(r, text_hash, legacy_hash,
                                        ws_hash)]
    normalized = [_normalize_sentence(s) for s in sentences]
    word_sets = [set(n.split()) for n in normalized]

    corpus = []
    for run in past_runs:
        for sent in _split_sentences(run["text"]):
            if len(sent.split()) < min_words:
                continue
            norm = _normalize_sentence(sent)
            corpus.append((norm, sent, set(norm.split()), run))
    corpus_index = _build_word_index(corpus)
    corpus_short = [pos for pos, entry in enumerate(corpus)
                    if len(entry[2]) < 3]
    query_entries = [(norm, sent, words, None)
                     for norm, sent, words
                     in zip(normalized, sentences, word_sets)]
    query_index = _build_word_index(query_entries)
    query_short = [pos for pos, entry in enumerate(query_entries)
                   if len(entry[2]) < 3]
    duplicates = []
    spent = 0
    for i, (sent, norm, words) in enumerate(zip(sentences, normalized,
                                                word_sets)):
        if spent >= _MAX_DUPLICATE_COMPARISONS:
            break
        best = None
        for pos in _gated_candidates(words, corpus, corpus_index,
                                     corpus_short):
            if spent >= _MAX_DUPLICATE_COMPARISONS:
                break
            cand_norm, cand_sent, _cand_words, run = corpus[pos]
            sim = _sentence_similarity(norm, cand_norm)
            spent += 1
            if sim >= threshold and (best is None or sim > best[0]):
                best = (sim, cand_sent, run)
        for pos in _gated_candidates(words, query_entries, query_index,
                                     query_short, min_pos=i + 1):
            if spent >= _MAX_DUPLICATE_COMPARISONS:
                break
            cand_norm, cand_sent = (query_entries[pos][0],
                                    query_entries[pos][1])
            sim = _sentence_similarity(norm, cand_norm)
            spent += 1
            if sim >= threshold and (best is None or sim > best[0]):
                best = (sim, cand_sent, None)
        if best is not None:
            sim, match, run = best
            duplicates.append({
                "sentence": sent, "match": match,
                "similarity": round(sim, 2),
                "source_id": run["id"] if run else None,
                "source_title": run["title"] if run else "naskah ini",
                "source_date": (str(run["created_at"])[:10]
                                if run else None),
            })
    return {"duplicates": duplicates, "count": len(duplicates),
            "checked": len(past_runs),
            "truncated": spent >= _MAX_DUPLICATE_COMPARISONS,
            "comparisons_spent": spent}


_DUPLICATES_STRINGS = {
    "id": {
        "heading": "Duplikasi internal",
        "none": "Tidak ada kalimat yang berulang dengan pustaka.",
        "checked": "Dibandingkan dengan {n} analisis tersimpan.",
        "similar": "mirip",
        "source": "sumber",
        "truncated": ("Peringatan: pemeriksaan berhenti setelah {spent} "
                      "perbandingan (batas {budget}) — hasil mungkin tidak "
                      "lengkap; sebagian kalimat belum dibandingkan."),
    },
    "en": {
        "heading": "Internal duplication",
        "none": "No sentences repeat the library.",
        "checked": "Compared with {n} saved analyses.",
        "similar": "similar to",
        "source": "source",
        "truncated": ("Warning: the check stopped after {spent} "
                      "comparisons (limit {budget}) — results may be "
                      "incomplete; some sentences were not compared."),
    },
}


def format_duplicates(result: dict, lang: str = "id") -> str:
    """Render a find_duplicates() result as readable text.

    When the result is truncated (the work budget ran out), a
    warning line is shown right after the "checked" line — before
    the list, and also when no duplicates were found at all, so a
    short or empty list is never mistaken for a complete check.
    Old hand-built dicts without "truncated" are treated as
    complete (no warning).
    """
    s = _DUPLICATES_STRINGS.get(lang, _DUPLICATES_STRINGS["id"])
    lines = [s["heading"], s["checked"].format(n=result["checked"])]
    if result.get("truncated"):
        lines.append(s["truncated"].format(
            spent=result.get("comparisons_spent", "?"),
            budget=_MAX_DUPLICATE_COMPARISONS))
    if not result["duplicates"]:
        lines.append(s["none"])
        return "\n".join(lines)
    for d in result["duplicates"]:
        if d["source_id"] is None:
            source = s["source"] + ": " + d["source_title"]
        else:
            source = (f"{s['source']}: pustaka #{d['source_id']} — "
                      f"{d['source_title']}"
                      + (f" ({d['source_date']})" if d["source_date"]
                         else ""))
        lines.append(f"  - {d['sentence']}")
        lines.append(f"    {d['similarity']:.0%} {s['similar']}: {d['match']}")
        lines.append(f"    {source}")
    return "\n".join(lines)


def duplicates_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Check a text for sentences that repeat the user's "
                    "own saved drafts in the library.")
    p.add_argument("input", nargs="?", help="plain-text file to check")
    p.add_argument("--text", help="check this text instead of a file")
    p.add_argument("--db", help="library database path "
                   "(default: ~/.academic-tools/library.db)")
    p.add_argument("--threshold", type=float, default=0.8,
                   help="minimum similarity 0-1 to report (default: 0.8)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.text:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
    try:
        result = find_duplicates(text, db=args.db,
                                 threshold=args.threshold)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_duplicates(result) + "\n")
    return 1 if result["count"] else 0


def humanize_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Suggest style rewrites for Indonesian academic prose "
                    "(before/after per pattern). Nothing is changed unless "
                    "--apply is given: then the mechanical suggestions are "
                    "written out and the guidance-only ones are left for "
                    "the author. Exits 1 when it has suggestions, 0 when "
                    "the style is already fluent.")
    p.add_argument("input", nargs="?", help="plain-text file to check")
    p.add_argument("--text", help="check this text instead of a file")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--apply", action="store_true",
                   help="apply the mechanical suggestions")
    p.add_argument("--out", help="write the fixed text here (default: "
                   "<file>.humanized.txt, or stdout for --text)")
    p.add_argument("--in-place", action="store_true",
                   help="overwrite the input file (keeps a .bak copy)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    if args.text:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
    if args.in_place and not args.input:
        p.error("--in-place needs a file input")
    if args.out and args.in_place:
        p.error("--out and --in-place cannot be combined")
    result = suggest_style_fixes(text, lang=args.lang,
                                 limit=None if args.apply else 10)
    fixed = apply_suggestions(text, result) if args.apply else None
    if args.json:
        if fixed is not None:
            result["fixed_text"] = fixed["text"]
            result["applied"] = len(fixed["applied"])
            result["skipped"] = len(fixed["skipped"])
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_suggestions(result, lang=args.lang))
    if fixed is not None:
        en = args.lang == "en"
        n_applied, n_skipped = len(fixed["applied"]), len(fixed["skipped"])
        report = (
            f"Applied: {n_applied} mechanical suggestions; "
            f"skipped: {n_skipped} (need a human decision)."
            if en else
            f"Diterapkan: {n_applied} saran mekanis; "
            f"dilewati: {n_skipped} (butuh keputusan manual).")
        if args.in_place:
            bak = args.input + ".bak"
            with open(args.input, encoding="utf-8") as f:
                original = f.read()
            with open(bak, "w", encoding="utf-8") as f:
                f.write(original)
            with open(args.input, "w", encoding="utf-8") as f:
                f.write(fixed["text"])
            done = (f"File updated: {args.input} (backup: {bak})"
                    if en else
                    f"File diperbarui: {args.input} (salinan: {bak})")
            sys.stdout.write(f"{report}\n{done}\n")
        elif args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(fixed["text"])
            sys.stdout.write(f"{report}\n"
                             + (f"Saved to: {args.out}"
                                if en else f"Tersimpan di: {args.out}") + "\n")
        elif args.input:
            if n_applied:
                stem, ext = os.path.splitext(args.input)
                out_path = f"{stem}.humanized{ext or '.txt'}"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(fixed["text"])
                sys.stdout.write(f"{report}\n"
                                 + (f"Saved to: {out_path}"
                                    if en else f"Tersimpan di: {out_path}") + "\n")
            else:
                # Nothing applied: no .humanized file is written.
                sys.stdout.write(f"{report}\n")
        elif not args.json:
            sys.stderr.write(f"{report}\n")
            out = fixed["text"]
            if not out.endswith("\n"):
                out += "\n"
            sys.stdout.write(out)
    return 1 if result["count"] else 0


# ======================================================================
# AI Detector — heuristic check whether a text reads like AI writing
# ======================================================================
# A pure-stdlib heuristic, no language model and no API: four signals
# that GPTZero-style detectors also lean on (sentence-length variation,
# template phrases, lexical diversity, repeated sentence starters).
# Each signal returns a 0-100 sub-score (100 = most AI-like); the
# final score is the weighted mean of the applicable signals only.
# The verdict bands are fixed, and the honesty note is always attached:
# this is an indication, never proof — human text can be flagged and
# AI text can pass, so the result must never be used to accuse anyone.
# Calibration texts live in tests/test_detector.py (3 human-like, 3
# AI-like, written from scratch): human-like scores stay under 40,
# AI-like scores stay over 60.

# Template phrases, curated from scratch for this repo — not copied
# from any detector's list. Density, not presence, is what counts:
# one "selain itu" in a human paragraph is normal; five per 100 words
# is the AI pattern.
_TEMPLATE_PHRASES = {
    "id": (
        "selain itu", "penting untuk dicatat", "perlu dicatat bahwa",
        "secara keseluruhan", "dalam hal ini", "pada akhirnya",
        "lebih lanjut", "sebagai kesimpulan", "dengan demikian",
        "oleh karena itu", "dapat disimpulkan bahwa",
        "hal ini menunjukkan bahwa", "perlu diperhatikan bahwa",
        "tidak dapat dipungkiri", "sebagai tambahan", "di sisi lain",
        "pada dasarnya", "dengan kata lain", "penting untuk diingat",
        "perlu digarisbawahi",
    ),
    "en": (
        "moreover", "in conclusion", "it is important to note",
        "furthermore", "overall", "in summary", "it should be noted",
        "in this regard", "as a result", "in other words",
    ),
}

_DETECTOR_NOTE = {
    "id": ("Deteksi ini heuristik murni (stdlib, tanpa model bahasa): "
           "skor adalah indikasi, bukan bukti. Teks manusia bisa "
           "ter-flag dan teks AI bisa lolos — jangan gunakan hasil ini "
           "untuk menuduh."),
    "en": ("This detector is a pure heuristic (stdlib, no language "
           "model): the score is an indication, not proof. Human text "
           "can be flagged and AI text can pass — do not use this "
           "result to accuse anyone."),
}

_DETECTOR_VERDICTS = {
    "id": {
        "ai": "Kemungkinan besar AI",
        "mixed": "Campuran / tidak pasti",
        "human": "Kemungkinan besar manusia",
        "short": "Teks terlalu pendek",
    },
    "en": {
        "ai": "Likely AI",
        "mixed": "Mixed / uncertain",
        "human": "Likely human",
        "short": "Text too short",
    },
}

_DETECTOR_SIGNAL_LABELS = {
    "id": {
        "burstiness": "Variasi panjang kalimat",
        "template_phrases": "Frasa template",
        "lexical_diversity": "Keragaman kosakata",
        "starter_repetition": "Pengulangan awalan kalimat",
    },
    "en": {
        "burstiness": "Sentence-length variation",
        "template_phrases": "Template phrases",
        "lexical_diversity": "Lexical diversity",
        "starter_repetition": "Repeated sentence starters",
    },
}

_DETECT_STRINGS = {
    "id": {
        "heading": "Deteksi AI",
        "score": "Skor AI",
        "verdict": "Kesimpulan",
        "signals": "Sinyal",
        "top": "Kalimat paling mirip AI",
        "top_none": "Tidak ada kalimat yang melewati ambang 70/100.",
        "not_applicable": "tidak berlaku",
        "burstiness_detail": "CV {cv}, rata-rata {mean} kata/kalimat",
        "template_detail": "{count} frasa, {density}/100 kata",
        "lexical_detail": "TTR {ttr}, {unique}/{total} kata unik",
        "starter_detail": "'{starter}' x {count} ({share} kalimat)",
        "capped": ("Kesimpulan dibatasi ke Campuran: hanya {n} dari 4 "
                   "sinyal yang berlaku — skor tinggi dari dua sinyal "
                   "keseragaman saja belum cukup untuk menyebut teks ini AI."),
        "capped_limit": ("Batas detektor: teks pendek (<100 kata dan "
                         "<6 kalimat) tidak pernah bisa mendapat "
                         "'Kemungkinan besar AI' — keragaman kosakata "
                         "hanya berlaku pada ≥100 kata dan pengulangan "
                         "awalan hanya pada ≥6 kalimat."),
    },
    "en": {
        "heading": "AI Detection",
        "score": "AI score",
        "verdict": "Verdict",
        "signals": "Signals",
        "top": "Most AI-like sentences",
        "top_none": "No sentence passes the 70/100 threshold.",
        "not_applicable": "not applicable",
        "burstiness_detail": "CV {cv}, mean {mean} words/sentence",
        "template_detail": "{count} phrases, {density}/100 words",
        "lexical_detail": "TTR {ttr}, {unique}/{total} unique words",
        "starter_detail": "'{starter}' x {count} ({share} of sentences)",
        "capped": ("Verdict capped at Mixed: only {n} of 4 signals "
                   "apply — a high score from two uniformity signals "
                   "alone is not enough to call this text AI."),
        "capped_limit": ("Detector limit: a short text (<100 words and "
                         "<6 sentences) can never reach 'Likely AI' — "
                         "lexical diversity only applies at ≥100 words "
                         "and starter repetition only at ≥6 sentences."),
    },
}


def _sentence_starters(sentences: list[str]) -> list[str]:
    """First two words of each sentence (first word when shorter)."""
    starters = []
    for sentence in sentences:
        words = sentence.split()
        if words:
            starters.append(" ".join(words[:2]).lower())
    return starters


def _detect_sentence_scores(sentences: list[str], counts: list[int],
                            template_hits: list[int],
                            modal_starter) -> list[dict]:
    """Per-sentence AI-likeness (0-100), most AI-like first.

    60% whether the sentence contains a template phrase (any hit
    counts — one "Selain itu," already marks the sentence), 30%
    closeness of its length to the mean sentence length, 10% whether
    it opens with the text's most common starter. A template sentence
    at the average length of a uniform text scores near 90; a short,
    odd, template-free sentence scores near 0. Ties keep their
    original order.
    """
    if not sentences:
        return []
    mean = sum(counts) / len(counts) if counts else 0
    scored = []
    for i, sentence in enumerate(sentences):
        template_part = 1.0 if template_hits[i] >= 1 else 0.0
        length_part = 0.0
        if mean:
            length_part = 1.0 - min(1.0, abs(counts[i] - mean) / mean)
        starter_part = 0.0
        if modal_starter is not None:
            words = sentence.split()
            starter = " ".join(words[:2]).lower() if words else ""
            starter_part = 1.0 if starter == modal_starter else 0.0
        score = round(100 * (0.6 * template_part + 0.3 * length_part
                             + 0.1 * starter_part), 1)
        scored.append({"sentence": sentence, "score": score})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def detect_ai(text: str, lang: str = "id") -> dict:
    """Heuristic check whether a text reads like AI writing.

    Four signals, each a 0-100 sub-score (100 = most AI-like):
    - burstiness (weight 30): coefficient of variation of sentence
      lengths in words — uniform sentences read like AI. Needs 3+
      sentences; the sub-score is 100 at CV 0 and 0 at CV 0.55.
    - template_phrases (weight 30): density of curated AI-typical
      transition phrases per 100 words — 5 per 100 words scores 100.
    - lexical_diversity (weight 20): type-token ratio — a repetitive
      vocabulary reads like AI. 100 at TTR 0.42, 0 at TTR 0.72.
      Needs 100+ words; TTR is meaningless on short texts.
    - starter_repetition (weight 20): share of sentences sharing the
      most common opening two words — 100 at a 0.50 share, 0 at 0.20.
      Needs 6+ sentences.
    The final ai_score (0-100) is the weighted mean of the applicable
    signals only (weights renormalized). Verdict bands: >= 60 "likely
    AI" — but only when at least 3 of the 4 signals apply. A score
    >= 60 from fewer than 3 applicable signals is capped at "mixed /
    uncertain" (verdict_capped True, with a reason): two uniformity
    signals alone cannot call a text AI — short methods prose trips
    burstiness + template phrases with nothing else to check.
    40-59 is "mixed / uncertain", < 40 "likely human". Under 30
    words the verdict is "too short" and ai_score is None — there is
    not enough text to judge. An empty text raises ValueError, like
    analyze_text_quality. The returned "note" is always present: this
    is a stdlib heuristic with no language model, so the score is an
    indication, not proof.
    """
    if not text or not text.strip():
        raise ValueError("teks kosong")
    lang = lang if lang in _TEMPLATE_PHRASES else "id"
    note = _DETECTOR_NOTE[lang]
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    n_words = len(words)
    sentences = _split_sentences(text)
    counts = [len(s.split()) for s in sentences]
    if n_words < 30:
        return {"ai_score": None,
                "verdict": _DETECTOR_VERDICTS[lang]["short"],
                "verdict_capped": False, "verdict_capped_reason": None,
                "signals": {}, "sentences": [], "note": note}

    signals: dict = {}

    # 1. Burstiness — uniform sentence lengths read like AI.
    if len(counts) >= 3:
        mean = sum(counts) / len(counts)
        if mean:
            var = sum((c - mean) ** 2 for c in counts) / len(counts)
            cv = var ** 0.5 / mean
        else:
            cv = 0.0
        signals["burstiness"] = {
            "score": round(max(0.0, min(100.0, 100 * (0.55 - cv) / 0.55)), 1),
            "weight": 30, "applicable": True,
            "cv": round(cv, 2), "mean_length": round(mean, 1),
            "sentences": len(counts),
        }
    else:
        signals["burstiness"] = {
            "score": None, "weight": 30, "applicable": False,
            "cv": None, "mean_length": None, "sentences": len(counts),
        }

    # 2. Template phrases — density per 100 words.
    phrases = _TEMPLATE_PHRASES[lang]
    low = text.lower()
    found = {}
    for phrase in phrases:
        n = len(re.findall(r"\b" + re.escape(phrase) + r"\b", low))
        if n:
            found[phrase] = n
    hits = sum(found.values())
    density = hits / max(1, n_words) * 100
    signals["template_phrases"] = {
        "score": round(min(100.0, density * 20), 1),
        "weight": 30, "applicable": True,
        "count": hits, "density_per_100": round(density, 1),
        "found": found,
    }

    # 3. Lexical diversity — type-token ratio. TTR is strongly
    # length-dependent (short texts almost always score high), so
    # the signal only applies at 100+ words.
    if n_words >= 100:
        unique = len(set(words))
        ttr = unique / n_words
        signals["lexical_diversity"] = {
            "score": round(max(0.0, min(100.0, 100 * (0.72 - ttr) / 0.30)), 1),
            "weight": 20, "applicable": True,
            "ttr": round(ttr, 2), "unique": unique, "total": n_words,
        }
    else:
        signals["lexical_diversity"] = {
            "score": None, "weight": 20, "applicable": False,
            "ttr": None, "unique": None, "total": n_words,
        }

    # 4. Starter repetition — share of the modal opening two words.
    starters = _sentence_starters(sentences)
    modal = None
    if len(sentences) >= 6 and starters:
        counts_by_starter: dict = {}
        for starter in starters:
            counts_by_starter[starter] = counts_by_starter.get(starter, 0) + 1
        modal = max(counts_by_starter, key=counts_by_starter.get)
        share = counts_by_starter[modal] / len(sentences)
        signals["starter_repetition"] = {
            "score": round(max(0.0, min(100.0, 100 * (share - 0.20) / 0.30)), 1),
            "weight": 20, "applicable": True,
            "share": round(share, 2), "starter": modal,
            "count": counts_by_starter[modal],
        }
    else:
        signals["starter_repetition"] = {
            "score": None, "weight": 20, "applicable": False,
            "share": None, "starter": None, "count": 0,
        }

    total = sum(s["score"] * s["weight"] for s in signals.values()
                if s["applicable"])
    weights = sum(s["weight"] for s in signals.values() if s["applicable"])
    ai_score = round(total / weights, 1) if weights else 0.0
    n_applicable = sum(1 for s in signals.values() if s["applicable"])
    verdicts = _DETECTOR_VERDICTS[lang]
    verdict_capped = False
    verdict_capped_reason = None
    if ai_score >= 60 and n_applicable >= 3:
        verdict = verdicts["ai"]
    elif ai_score >= 60:
        # Capped: a high score from only two uniformity signals
        # (burstiness + template phrases on a short text) is not
        # enough to call a text AI.
        verdict = verdicts["mixed"]
        verdict_capped = True
        verdict_capped_reason = _DETECT_STRINGS.get(
            lang, _DETECT_STRINGS["id"])["capped"].format(
                n=n_applicable)
    elif ai_score >= 40:
        verdict = verdicts["mixed"]
    else:
        verdict = verdicts["human"]

    hits_per_sentence = []
    for sentence in sentences:
        slow = sentence.lower()
        hits_per_sentence.append(sum(
            len(re.findall(r"\b" + re.escape(p) + r"\b", slow))
            for p in phrases))
    sent_scores = _detect_sentence_scores(sentences, counts,
                                           hits_per_sentence, modal)

    return {"ai_score": ai_score, "verdict": verdict,
            "verdict_capped": verdict_capped,
            "verdict_capped_reason": verdict_capped_reason,
            "signals": signals, "sentences": sent_scores, "note": note}


def format_detect(result: dict, lang: str = "id") -> str:
    """Render a detect_ai() result as readable text."""
    s = _DETECT_STRINGS.get(lang, _DETECT_STRINGS["id"])
    labels = _DETECTOR_SIGNAL_LABELS.get(lang, _DETECTOR_SIGNAL_LABELS["id"])
    lines = [s["heading"], ""]
    if result["ai_score"] is None:
        lines.append(f"{s['verdict']}: {result['verdict']}")
    else:
        lines.append(_bold(f"{s['score']}: {result['ai_score']}/100"))
        lines.append(_green(_bar(result["ai_score"], 100)))
        lines.append(f"{s['verdict']}: {result['verdict']}")
        if result.get("verdict_capped") and result.get(
                "verdict_capped_reason"):
            lines.append(result["verdict_capped_reason"])
            # N-7 (audit #5): the cap reason says only two signals
            # apply, but not WHY a short text can never reach the top
            # band. State the structural limit here (CLI output), so
            # a capped high score is not read as "almost AI".
            lines.append(s["capped_limit"])
    lines.append("")
    lines.append(f"{s['signals']}:")
    for name, label in labels.items():
        sig = result["signals"].get(name) or {}
        if not sig.get("applicable"):
            lines.append(f"  - {label}: {s['not_applicable']}")
            continue
        if name == "burstiness":
            detail = s["burstiness_detail"].format(
                cv=sig["cv"], mean=sig["mean_length"])
        elif name == "template_phrases":
            detail = s["template_detail"].format(
                count=sig["count"], density=sig["density_per_100"])
        elif name == "lexical_diversity":
            detail = s["lexical_detail"].format(
                ttr=sig["ttr"], unique=sig["unique"], total=sig["total"])
        else:
            detail = s["starter_detail"].format(
                starter=sig["starter"], count=sig["count"],
                share=f"{sig['share']:.0%}")
        lines.append(f"  - {label}: {sig['score']}/100 ({detail})")
    top = [x for x in result["sentences"] if x["score"] >= 70][:3]
    lines.append("")
    if top:
        lines.append(f"{s['top']}:")
        for item in top:
            sent = item["sentence"]
            if len(sent) > 90:
                sent = sent[:90].rstrip() + "…"
            lines.append(f"  - \"{sent}\" ({item['score']}/100)")
    else:
        lines.append(s["top_none"])
    lines.append("")
    lines.append(result["note"])
    return "\n".join(lines) + "\n"


def detect_main(argv=None, *, version=None) -> int:
    p = argparse.ArgumentParser(
        description="Check whether a text reads like AI writing — a pure "
                    "stdlib heuristic (sentence-length variation, template "
                    "phrases, lexical diversity, repeated sentence "
                    "starters). Informative only: it always exits 0, "
                    "unless the input itself is bad (missing file, empty "
                    "text).")
    p.add_argument("input", nargs="?", help="plain-text file to check")
    p.add_argument("--text", help="check this text instead of a file")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {version or __version__}")
    args = p.parse_args(argv)

    if args.text is not None:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
    result = detect_ai(text, lang=args.lang)
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_detect(result, lang=args.lang))
    return 0


# ======================================================================
# Readability — Flesch Reading Ease + Flesch-Kincaid Grade Level
# ======================================================================
# Two formulas from Flesch (1948), J. Appl. Psychol. 32(3), 221-233:
#   RE   = 206.835 - 1.015 * (words/sentence) - 84.6 * (syllables/word)
#   FKGL = 0.39 * (words/sentence) + 11.8 * (syllables/word) - 15.59
# Pure arithmetic on counts — no language model, no API, no minimum
# word count (unlike the AI detector, this is a formula, not an
# inference). The syllable counter is tuned for Indonesian (EYD
# diphthongs ai/au/oi only); English is best-effort. The formulas
# were calibrated for English, so on Indonesian text the score is an
# indication, not a verdict: Indonesian words average more syllables,
# so Indonesian academic prose usually lands lower than an English
# text of the same difficulty — that is expected, not a bug.

_READABILITY_BANDS = (
    # (lowest RE in the band, Indonesian label, English label)
    (90, "Sangat mudah", "Very easy"),
    (80, "Mudah", "Easy"),
    (70, "Cukup mudah", "Fairly easy"),
    (60, "Standar", "Standard"),
    (50, "Cukup sulit", "Fairly difficult"),
    (30, "Sulit", "Difficult"),
    (0, "Sangat sulit", "Very difficult"),
)

_READABILITY_NOTE = {
    "id": ("Rumus Flesch dikalibrasi untuk Bahasa Inggris; untuk Bahasa "
           "Indonesia skor ini hanya indikasi, bukan vonis. Teks akademik "
           "Indonesia umumnya mendarat lebih rendah karena kata Bahasa "
           "Indonesia rata-rata lebih banyak suku katanya. FKGL memakai "
           "skala kelas Amerika Serikat."),
    "en": ("The Flesch formulas were calibrated for English; for "
           "Indonesian text this score is an indication, not a verdict. "
           "Indonesian academic text usually lands lower because "
           "Indonesian words average more syllables. FKGL uses the "
           "United States grade scale."),
}

_VOWELS = set("aeiou")
# EYD edisi V lists FOUR diphthongs: ai, au, ei, oi (Badan Bahasa,
# 2022 — ejaan.kemdikdasmen.go.id/eyd/penggunaan-huruf/
# gabungan-huruf-vokal/, verified 2026-11-13). The "ei" is the new
# one: PUEBI (Permendikbud 50/2015) added it for loanwords such as
# "survei", and EYD V kept all four. The old claim of only three
# diphthongs was wrong. (The pairs live in _VOWEL_PAIRS_SINGLE
# below, which adds "eu", the EYD V monophthong.)

# Whole ROOTS where a diphthong-looking vowel pair is NOT a
# diphthong: the pair is two syllables in the root itself
# (KBBI: ba·ik, ma·in, ka·in, la·ut, ko·in, ga·i·rah). The
# value is the pair(s) to NOT subtract for that root. Matched
# on the ROOT (after affix stripping) only, never as a
# substring: "main" is listed, "domain" is not, so a word that
# merely contains a listed word keeps the plain rule.
# Derivatives are NOT listed here — affix stripping derives
# them ("dimainkan" = di- + main + -kan = 4, "kebaikan" =
# ke- + baik + -an = 4). Curated, not complete: this is
# lexical, not rule-based, so anything unlisted falls back
# to the plain diphthong rule. Counts checked against KBBI
# syllabification (kbbi.web.id, 2026-11-13). Three entries
# from v1.27.2 were WRONG and are removed here: "capai" is
# ca-pai (2, a real diphthong), "mencapai"/"tercapai" are 3
# — only their suffixed forms split ("capaian" 4).
_SYLLABLE_EXCEPTIONS = {
    # "ai" is hiatus in these roots.
    "baik": ("ai",),
    "main": ("ai",),
    "sains": ("ai",),
    "air": ("ai",),
    "kain": ("ai",),
    "lain": ("ai",),
    "gaib": ("ai",),
    "kait": ("ai",),
    "cair": ("ai",),
    "raih": ("ai",),
    "naik": ("ai",),
    "saing": ("ai",),
    "kaidah": ("ai",),
    "gairah": ("ai",),
    # "ai" is hiatus in these roots (audit #6 H-3/H-4/T-6).
    "kail": ("ai",),
    "bait": ("ai",),
    "laik": ("ai",),
    "aib": ("ai",),
    "sair": ("ai",),
    "kais": ("ai",),
    "syair": ("ai",),
    "mozaik": ("ai",),
    # "ai" is hiatus in these roots (audit #7 H-4/T-6).
    # "raib" is ra·ib (2): the v1.27.4 CHANGELOG claim that it
    # has no KBBI entry was WRONG — the entry exists
    # (kbbi.web.id index + kbbi.co.id "hilang; gaib").
    "raib": ("ai",),
    "pais": ("ai",),   # pa·is (KBBI: pepes)
    "tais": ("ai",),   # ta·is (KBBI, arkais: kotor)
    # "au" is hiatus in these roots.
    "daun": ("au",),
    "laut": ("au",),
    "jauh": ("au",),
    "bau": ("au",),
    "kau": ("au",),
    "paus": ("au",),
    "saus": ("au",),
    "kaus": ("au",),
    "haus": ("au",),
    "kaum": ("au",),
    "maut": ("au",),
    "dedaun": ("au",),
    # "au" is hiatus in these roots (audit #6 H-3/H-4).
    "paut": ("au",),
    "taut": ("au",),
    "lauk": ("au",),
    "kaut": ("au",),
    "gaun": ("au",),
    "aum": ("au",),
    "raup": ("au",),
    # "au" is hiatus in these roots (audit #7 H-4/T-6).
    "laun": ("au",),  # la·un (KBBI: lambat; perlahan)
    "saur": ("au",),  # sa·ur (KBBI, Mk: berbelit)
    "kaul": ("au",),  # ka·ul (KBBI: janji; nazar)
    "saut": ("au",),  # sa·ut (KBBI: lihat "akar")
    "pauk": ("au",),  # pa·uk (KBBI: la·uk-pa·uk; pe·ma·uk)
    "taul": ("au",),  # ta·ul (KBBI, ark: me·na·ul)
    "gaut": ("au",),  # ga·ut (KBBI, Mk: dalam frasa "gaut gapai")
    # "ei" is hiatus in these roots (audit #6 H-3/T-6):
    # pro·te·in, ka·se·in, de·is·me, te·is·me — the "ei"
    # straddles two syllables, so it is not the EYD diphthong.
    "protein": ("ei",),
    "kasein": ("ei",),
    "deisme": ("ei",),
    "teisme": ("ei",),
    # "oi" is hiatus in these roots.
    "koin": ("oi",),
    "poin": ("oi",),
    "heroik": ("oi",),
    "stoik": ("oi",),
}

# What is left of a hiatus root after a nasal prefix assimilates
# (meluluh) its initial consonant — audit #6 H-4. meng-/peng- +
# k- leaves "ait" from "kait" ("mengait", "pengait"), meny-/peny-
# + s- leaves "yair" from "sair" ("penyair") and "yaing" from
# "saing" ("menyaingi", "penyaing"), pe- + r- leaves "aih" from
# "raih" ("peraih" — longest-first strips "per", not "pe") and
# "aup" from "raup" ("peraup"), and men- + t- leaves "naut" from
# "taut" ("menautkan": "men" cannot strip before a vowel, so "me"
# strips instead). The remnant's vowel pair is the root's hiatus,
# not a diphthong — but ONLY for these listed remnants. A blanket
# "split the first vowel pair after a nasal prefix" would break
# real diphthongs ("memandai" is mem- + pandai, 3, not 4), so the
# fix is lexical, like _SYLLABLE_EXCEPTIONS. Matched on the
# stripped ROOT only, never as a substring. Counts checked against
# KBBI syllabification (kbbi.web.id, 2026-11-13): me·nga·it,
# pe·nga·it, me·nga·il, pe·nga·il, me·nga·is, me·nga·is·kan,
# me·nga·ut, pe·nya·ir, me·nya·ingi, pe·nya·ing, me·na·ut·kan,
# pe·ra·up. NOT listed: "ain" (no meng- derivative of "kain" in
# KBBI), "aidah" (no meng- derivative of "kaidah"), "moin"/"oin"
# ("memoin"/"mengoin" unverified; "poin"/"koin" have no
# kbbi.web.id entry at all). "aib" is a real root (a·ib, via
# meng·a·ib·kan), so it lives in _SYLLABLE_EXCEPTIONS, not here.
# Audit #7 adds "aul", "yaur", "mauk", "naul" (me·nga·ul·kan,
# me·nya·ur, pe·ma·uk, me·na·ul — all KBBI). NOT added: "mais"
# (no "memais" in KBBI), "yaut" (no "menyaut"), "nais" (no
# "menais").
_NASAL_REMNANTS = {
    # "ai" is hiatus in these remnants.
    "ait": ("ai",),    # kait
    "ail": ("ai",),    # kail
    "ais": ("ai",),    # kais
    "aih": ("ai",),    # raih
    "yaing": ("ai",),  # saing
    "yair": ("ai",),   # sair
    # "au" is hiatus in these remnants.
    "aut": ("au",),    # kaut
    "aup": ("au",),    # raup
    "naut": ("au",),   # taut
    # "au" is hiatus in these remnants (audit #7 H-4/T-6).
    "aul": ("au",),    # kaul (me·nga·ul·kan, KBBI)
    "yaur": ("au",),   # saur (me·nya·ur, KBBI)
    "mauk": ("au",),   # pauk (pe·ma·uk, KBBI)
    "naul": ("au",),   # taul (me·na·ul, KBBI)
}

# Pairs that count as ONE syllable (EYD V diphthongs ai, au,
# ei, oi, plus "eu", the EYD V monophthong [ə]: "seudati" is
# 3, "euis" is 2). Used by _count_syllables; entries in
# _SYLLABLE_EXCEPTIONS above opt a root out of a pair.
_VOWEL_PAIRS_SINGLE = ("ai", "au", "ei", "oi", "eu")

# Whole words whose syllable count cannot be derived by rule:
# rare loanwords where the "eu" monophthong spans what looks
# like a prefix boundary. "seudati" is seu-da-ti (3) — the
# "eu" is one syllable — so stripping "se-" would break it
# ("udati" counts 3 on its own). Checked before affix
# stripping. Verified against the EYD V monophthong [ə].
_SYLLABLE_WHOLE_WORD = {"seudati": 3}

# Prefixes that never precede a vowel-initial root: men-/mem-/
# pen-/pem- are nasal assimilations before consonants (men- +
# a vowel would be meng- or me-/pe- instead). "menaiki" is
# me- + naik, not men- + aiki.
_NO_VOWEL_AFTER = ("men", "mem", "pen", "pem")

# Common Indonesian prefixes, longest first: (affix, syllables).
# "memper-"/"diper-" count 2 (mem-per-, di-per-); the rest 1.
# (Written without the trailing hyphen: "bermain" is ber +
# main, there is no literal "-" in the word.)
_PREFIXES = (
    ("memper", 2), ("diper", 2),
    ("ber", 1), ("ter", 1), ("meng", 1), ("mem", 1),
    ("men", 1), ("peng", 1), ("pem", 1), ("pen", 1),
    ("per", 1), ("me", 1), ("pe", 1), ("di", 1),
    ("ke", 1), ("se", 1),
)

# Common Indonesian suffixes, longest first: (affix, syllables).
# "-kan" is tried before "-an" because "mainkan" is main + -kan
# while "kebaikan" is kebaik + -an — _strip_id_affixes
# disambiguates via the hiatus-root dict.
_SUFFIXES = (
    ("kan", 1), ("nya", 1), ("lah", 1), ("kah", 1),
    ("pun", 1), ("an", 1), ("mu", 1), ("ku", 1), ("i", 1),
)

# A root-final diphthong splits before these suffixes
# ("capai" + "-an" is ca-pa-i-an = 4, "mau" + "-kah" is
# ma-u-kah = 3), but NOT before the possessive enclitics
# -nya/-ku/-mu ("maunya" is 2, "pulaunya" is 3: the diphthong
# stays intact there).
_SPLIT_SUFFIXES = frozenset({"kan", "an", "i", "lah", "kah", "pun"})

# English hiatus words where a vowel pair is two syllables
# (curated, not complete — like the Indonesian list), plus
# words the "-le" rule must not touch ("aisle"/"isle" are 1).
_ENGLISH_EXCEPTIONS = {
    "idea": 3, "area": 3, "real": 2, "poem": 2,
    "science": 2, "rhythm": 2,
    "aisle": 1, "isle": 1,
    # Audit #6 H-5: "oe"/"oo"/"ui" are genuinely ambiguous
    # ("book" 1 vs "cooperate" 4, "suit" 1 vs "ruin" 2), so no
    # rule can split them safely — these words are pinned here
    # instead of guessed by a rule. ("ea" has a narrow rule
    # now: only before "ct", as in "reaction".)
    "create": 2, "created": 2, "creating": 3, "creator": 3,
    "ideal": 3, "reality": 4, "theatre": 3, "theater": 3,
    "realize": 3, "realise": 3, "realistic": 4,
    "diarrhea": 4, "diarrhoea": 4,
    "poet": 2, "poems": 2,
    "cooperate": 4, "coordinate": 4, "cooperation": 5,
    "ruin": 2, "fluid": 2, "genuine": 3,
    # Audit #6 H-5: "-ed" is pronounced as its own syllable in
    # these words, so the silent-"-ed" rule below must not touch
    # them ("naked" 2 vs "walked" 1, "beloved" 3, "hatred" 2).
    "naked": 2, "wicked": 2, "rugged": 2, "beloved": 3,
    "learned": 2, "blessed": 2, "aged": 2, "dogged": 2,
    "jagged": 2, "sacred": 2, "crooked": 2, "wretched": 2,
    "ragged": 2, "hatred": 2, "hundred": 2, "kindred": 2,
    # Audit #6 N-7: irregular words no rule reaches. "chaotic"
    # (3) and "february" (4) are NOT listed: the "ao"/"ua" rules
    # below already count them right.
    "business": 2, "every": 2, "evening": 2, "definitely": 4,
    "wednesday": 2, "colonel": 2, "literature": 3, "vegetable": 3,
    # "Laos" is 1 (the "ao" rule would give 2: "chaos" 2 splits,
    # "Laos" does not — same letters, different word).
    "laos": 1,
    # "gue"/"que" is silent ("vague" 1, "antique" 2), except
    # these two, where the "u" is a real vowel: "argue" 2
    # (the "u" is /ju:/) and "segue" 2 (the "ue" is /weI/).
    # "arguing" is 3 (ar-gu-ing): the "-ing" keeps the /u:/
    # + /I/ split (audit #7 H-7, three syllable dictionaries).
    "argue": 2, "segue": 2, "arguing": 3,
    # "eu" has no rule: it is one sound word-initially
    # ("eulogy" 3) but two sounds across the re- boundary
    # ("reunion" 3, "reuse" 2, "reunite" 3, "reusable" 4,
    # "reunification" 6) and in "museum" 3 (mu-se-um). Pinned.
    "reunion": 3, "reuse": 2, "reunite": 3, "reusable": 4,
    "reunification": 6, "museum": 3,
    # "trial" 2 (tri-al): the only "t" + "ia" word where the
    # "ia" splits — the -tial rule would give 1 ("partial" 2
    # is one sound, "trial" is two).
    "trial": 2,
    # Audit #7 H-6/H-8/N-2: pinned irregulars. "chihuahua" is
    # 3 (Chi-hua-hua; the "ua" rule fires twice without the
    # pin) and "chihuahuas" likewise. "adobe" is 3 (a-do-be)
    # and "phoebe" is 2 (phoe-be): the final "e" is pronounced
    # after vowel + "b". "unscientific" is 5 (un-sci-en-tif-ic).
    # "interest" 2 / "interested" 3 are the common REDUCED
    # pronunciations (/ˈɪn.trest/, /ˈɪn.trə.stɪd/ — Cambridge,
    # Oxford); the full forms (3/4, howmanysyllables) are
    # variants, like "interesting" 4, which is deliberately
    # left unpinned for the same reason. NOT pinned: "gruel"
    # and "nescience" — audit #7's "want 1"/"want 3" were
    # wrong; the majority of syllable dictionaries give 2 for
    # both, and the code already counts 2.
    "chihuahua": 3, "chihuahuas": 3,
    "adobe": 3, "phoebe": 2, "unscientific": 5,
    "interest": 2, "interested": 3,
}


def _en_hiatus_extra(w: str) -> int:
    """Extra syllables from English vowel pairs that split.

    English spelling hides hiatus: "various" is var-i-ous (3),
    "media" is me-di-a (3), "theory" is the-o-ry (3) — but the
    plain vowel-run count sees one group for the pair. This scans
    the word left to right; when a listed pair fires it counts
    one extra syllable and consumes the pair, so a three-vowel
    run splits exactly once ("iou" in "various" is i + ou = 2,
    "iai" in "liaison" is i + ai = 2). Pairs that do NOT split
    are left alone:
    - "ia"/"io" after c/s/t are one syllable ("special",
      "official", "dictionary", "version" — the -cial/-tial/
      -tion/-sion endings), and "io" after c/t/x before "u" is
      one syllable ("precious", "cautious", "anxious" — the
      -cious/-tious/-xious endings). A word-initial "sc" before
      the pair is a real /s/ + vowel, not /ʃ/ ("scientific",
      "scion", "sciatic"), so it DOES split there.
    - "ua" after q/g is one syllable ("quality", "language",
      "guard"), and before "v" ("suave"); "-ually" always
      splits ("usually", "actually", "gradually", "casually",
      "spiritually" — the "ua" is /u/ + /@/ in every case).
    - "ue" splits before "l"/"n"/"t" ("cruel", "fuel",
      "fluent", "duet") and not after "q" ("sequel").
    - "ie" splits only before "t" + vowel/end ("diet", "quiet",
      "variety", "society") or before "nce"/"nt" when not after
      c/s/t ("experience", "audience", "client" — but not
      "patience", "ancient", "science").
    - "eo" splits except before "p" ("people", "leopard").
    - "ea" splits only before "ct" ("reaction", "reactor",
      "reactive", "react" — the "ea" straddles the re-/act-
      boundary; everywhere else it is one sound: "meal",
      "great", "measure", "peacock").
    - "ao" splits only before a consonant ("chaos", "chaotic";
      "Mao" stays 1).
    "oe", "oo", "ui" have no rule — they are genuinely
    ambiguous, so those words live in _ENGLISH_EXCEPTIONS.
    "io" after "n" is one syllable ("opinion", "companion",
    "union", "senior", "junior" — the "io" is /j@/).
    Known misses (documented, not guessed): "extraordinary" 6
    (AmE 5, BrE 6 — dialect, unpinned), "management" 4 (want 3
    — no "-ment" rule, it would break "element" 3). Former
    misses now pinned in _ENGLISH_EXCEPTIONS (audit #7):
    "unscientific" 5, "adobe" 3, "phoebe" 2. "nescience" 2
    and "gruel" 2 were listed here as misses by mistake —
    the majority of syllable dictionaries give 2 for both,
    and the code already counts 2, so they are not misses.
    """
    extra = 0
    i = 0
    n = len(w)
    while i + 1 < n:
        pair = w[i:i + 2]
        prev = w[i - 1] if i > 0 else ""
        nxt = w[i + 2] if i + 2 < n else ""
        # Word-initial "sc" (pair starts at index 2, "sc" at 0-1):
        # the "c" is /s/, so the following vowel is real — unlike
        # "ci" after a vowel, which is /ʃ/ ("ancient", "efficient",
        # "conscience", "suspicion").
        sc = i == 2 and w[0:2] == "sc"
        fire = False
        if pair == "ia":
            if prev == "g" and w[i + 2:i + 5] == "nce":
                # "allegiance": the "ia" is /@/, one syllable.
                fire = False
            elif prev == "c" and sc and nxt and nxt not in _VOWELS:
                # "sciatic", "sciatica" — but not "fascia" (sc not
                # word-initial) or "glacial" (c after a vowel).
                fire = True
            elif prev != "" and prev in "cst":
                # -cial/-tial ("special", "official", "partial",
                # "essential") are one syllable. Note prev is
                # checked non-empty: "" in "cst" is True in
                # Python, so a bare `prev in "cst"` would also
                # block word-initial "ia" ("iambic", "liaison").
                fire = False
            else:
                fire = True
        elif pair == "io":
            if prev != "" and prev in "tsn" and nxt == "n":
                fire = False
            elif prev == "c" and nxt == "n":
                fire = sc  # "scion" splits; "suspicion" does not
            elif prev != "" and prev in "ctx" and nxt == "u":
                fire = False
            elif prev == "n":
                # "-nion" ("opinion", "companion", "union",
                # "senior", "junior"): the "io" is /j@/, one sound.
                fire = False
            else:
                fire = True
        elif pair == "ua":
            # "-ually" ("usually", "actually", "gradually",
            # "casually", "spiritually") is always two sounds
            # (/u/ + /@/): there is no letter rule that separates
            # the s/t cases from the d/n/c cases, because they are
            # the same pattern — so no guard here at all.
            fire = (prev == "" or prev not in "qg") and nxt != "v"
        elif pair == "ie":
            if nxt == "t" and (i + 3 >= n or w[i + 3] in _VOWELS
                               or w[i + 3] == "y"):
                fire = True
            elif nxt == "n" and (w[i + 2:i + 5] == "nce"
                                 or (i + 3 < n and w[i + 3] == "t")):
                fire = (prev == "" or prev not in "cst"
                        or (prev == "c" and sc))
        elif pair == "eo":
            fire = nxt != "p"
        elif pair == "ue":
            # "ue" + l/n/t is two sounds ("cruel", "fluent",
            # "duet"); "ue" + d/s is one ("suede", "dues"). A
            # word-final "ue" is one sound ("tissue", "value",
            # "blue") — the empty next char is NOT in "lnt"
            # ("" in "lnt" is True in Python, so it is checked
            # explicitly). "ue" after q is /w/ ("sequel").
            fire = nxt != "" and nxt in "lnt" and prev != "q"
        elif pair == "ea":
            # Only before "ct" ("reaction", "reactor", "reactive",
            # "react" — the "ea" straddles the re-/act- boundary).
            # Everywhere else "ea" is one sound ("meal", "great",
            # "measure", "peacock"), so it has no general rule.
            fire = w[i + 2:i + 4] == "ct"
        elif pair == "ao":
            fire = bool(nxt) and nxt not in _VOWELS
        if fire:
            extra += 1
            i += 2
        else:
            i += 1
    return extra


def _en_silent_final_e(w: str) -> bool:
    """True if a word-final "e" is silent (so it subtracts one).

    The final "e" is pronounced — no subtraction — when it is
    part of a vowel digraph ("ee" in "agree", "oe" in "canoe",
    "ie" in "movie", "ae" in "sundae", "ye" in "goodbye"), when
    it is the "ue" of a real vowel after a consonant ("tissue",
    "value", "continue", "argue", "rescue" — but NOT "vague",
    "tongue", "league", "dialogue", where "ue" after a vowel
    is silent), or when it follows consonant + "r" ("centre",
    "acre", "fibre" — but not "more", "care", "desire", where
    the "r" follows a vowel). Caller also requires groups > 1.
    Known misses: "adobe", "phoebe" (the "e" after vowel + "b"
    is pronounced, the same letters as silent "globe", "robe").
    """
    if not w.endswith("e"):
        return False
    if w.endswith(("ee", "oe", "ie", "ae", "ye")):
        return False
    if w.endswith(("que", "gue")):
        # "qu"/"gu" is a glide + consonant ("antique",
        # "unique", "vague", "tongue", "league", "dialogue"):
        # the "u" is not a vowel, the "e" is silent. The two
        # words where the "u" IS a real vowel ("argue" 2,
        # "segue" 2) live in _ENGLISH_EXCEPTIONS instead.
        return True
    if w.endswith("ue") and len(w) >= 3 and w[-3] not in _VOWELS:
        return False
    if w.endswith("re") and len(w) >= 3 and w[-3] not in _VOWELS:
        return False
    return True


def _en_medial_silent_e(w: str, groups: int) -> int:
    """Syllables to subtract for a silent medial "e" (0 or 1).

    The "e" of the base word stays silent when a consonant-
    initial suffix follows it: "-ly" ("widely", "completely",
    "absolutely", "entirely", "carefully", "largely", "closely"),
    "-ful" ("hopeful", "careful", "useful", "grateful",
    "shameful", "tasteful", "rueful", "woeful"), "-less"
    ("careless", "hopeless", "useless", "homeless", "priceless",
    "timeless"), "-ness" ("awareness", "likeness", "politeness",
    "forgiveness"). The "e" must be preceded by a consonant
    ("rely" has two groups, so the "-ly" case also needs
    groups > 2; "freely" keeps its "ee"), and "-ful" fires on
    the substring alone ("rueful"/"woeful" have the silent "e"
    after a vowel). No rule for "-ment": "management" (want 3)
    and "element" (want 3) share the same "ement" letters, so
    that pair stays a known miss rather than trading one error
    for another.
    """
    if groups <= 1:
        return 0
    if (w.endswith("ely") and len(w) >= 4
            and w[-4] not in _VOWELS and w[-4] != "y" and groups > 2):
        return 1
    for pat in ("eful", "eless", "eness"):
        i = w.find(pat)
        # The "e" must start its own vowel group: preceded by a
        # consonant ("hopeful", "careless", "awareness"). In
        # "rueful"/"woeful" the "e" sits inside the "ue"/"oe"
        # run already counted as one, so there is nothing to
        # subtract — that is why "-ful" is not a bare substring
        # test.
        if i > 0 and w[i - 1] not in _VOWELS and w[i - 1] != "y":
            return 1
    return 0


def _root_ends_with_counted_pair(root: str) -> bool:
    """True if root ends in a vowel pair counted as one syllable.

    That is: the pair is in _VOWEL_PAIRS_SINGLE and the root is
    NOT in _SYLLABLE_EXCEPTIONS for that pair. Used to decide
    whether the pair splits before a split-eligible suffix.
    """
    for pair in _VOWEL_PAIRS_SINGLE:
        if root.endswith(pair) and pair not in _SYLLABLE_EXCEPTIONS.get(root, ()):
            return True
    return False


def _may_strip_i(rest: str) -> bool:
    """May the final "-i" be stripped as a suffix?

    "-i" is a real suffix in "menaiki" (me- + naik + -i) and
    "saingi" (saing + -i), but part of the root in "pantai",
    "damai", "ramai", "sampai", "survei" — and in "mencapai"
    (men- + capai, the "ai" is the root's own diphthong, not
    root + suffix). Allow the strip only when the remaining
    root is a hiatus root, or when it ends in a consonant
    (stripping there is count-neutral: one vowel out of the
    root, one suffix back in). Known miss: a genuine "-i"
    suffix on a vowel-final root is not stripped ("mencintai"
    counts 3, not 4; "melukai" 3, not 4) — the surface form
    is indistinguishable from a root diphthong ("capai"),
    and the diphthong reading is far more common in academic
    text, so the diphthong wins.
    """
    if rest in _SYLLABLE_EXCEPTIONS:
        return True
    return rest[-1] not in _VOWELS


def _strip_id_affixes(w: str):
    """Peel Indonesian prefixes/suffixes off w.

    Returns (root, affix_syllables, split). ``split`` is True
    when a suffix from _SPLIT_SUFFIXES was stripped right after
    a root ending in a counted diphthong — the pair then splits
    before that suffix ("capaian" = capai + -an = 4).
    A prefix/suffix is only stripped when at least 2 characters
    with a vowel remain, so short words ("ber", "di") are never
    gutted. Prefixes are stripped first, longest first, in a
    loop ("mempermainkan" -> "mainkan"); suffixes the same way.
    """
    affixes = 0
    while True:
        for pre, syl in _PREFIXES:
            if not w.startswith(pre):
                continue
            rest = w[len(pre):]
            if len(rest) < 2 or not any(c in _VOWELS for c in rest):
                continue
            if pre in _NO_VOWEL_AFTER and rest[0] in _VOWELS:
                continue
            w = rest
            affixes += syl
            break
        else:
            break
    split = False
    while True:
        for suf, syl in _SUFFIXES:
            if not w.endswith(suf):
                continue
            rest = w[:-len(suf)]
            if len(rest) < 2 or not any(c in _VOWELS for c in rest):
                continue
            if suf == "i" and not _may_strip_i(rest):
                continue
            if suf == "kan":
                # "-kan" vs "-an": prefer the parse whose root is
                # a hiatus root ("mainkan" -> main + -kan, but
                # "kebaikan" -> kebaik + -an). When neither is,
                # either parse counts the same (a trailing "k"
                # changes no vowel/diphthong count), so keep "-kan".
                if rest not in _SYLLABLE_EXCEPTIONS:
                    alt = w[:-2]
                    if alt in _SYLLABLE_EXCEPTIONS:
                        suf, syl = "an", 1
                        rest = alt
            if suf in _SPLIT_SUFFIXES and _root_ends_with_counted_pair(rest):
                split = True
            w = rest
            affixes += syl
            break
        else:
            break
    return w, affixes, split


def _count_syllables(word: str, lang: str = "id") -> int:
    """Syllables in one word.

    Source of truth: KBBI syllabification, word by word. EYD
    edisi V lists four diphthongs (ai, au, ei, oi) — and that
    claim is correct — but a diphthong only counts as one
    syllable when the vowel pair sits inside ONE syllable.
    KBBI decides that per word, and the two authorities
    disagree on some words: EYD says the "ai" diphthong is
    never split (example: "pandai"), while KBBI syllabifies
    "baik" as ba·ik (2 syllables), "naik" as na·ik, "kain" as
    ka·in. This function follows KBBI, because Flesch counts
    pronounced syllables, not spelling. The tension is real
    and deliberate: do not "fix" it back to the EYD-only rule.

    Indonesian (lang="id", the default): vowels are counted,
    minus one per diphthong/monophthong pair (ai, au, ei, oi,
    plus "eu", the EYD V monophthong [ə]: "seudati" is 3).
    Three mechanisms keep the pairs honest:
    (1) a curated list of hiatus ROOTS in _SYLLABLE_EXCEPTIONS
    ("baik", "kain", "laut", "naik", "koin", "gairah", ...),
    where the pair is two syllables; and
    (2) affix stripping — common prefixes (ber-, me-, pe-,
    di-, ke-, ter-, se-, memper-, ...) and suffixes (-kan,
    -an, -i, -nya, -mu, -ku, -lah, -kah, -pun) are peeled off
    and counted separately, so derivatives of a hiatus root
    stay right ("dimainkan" = di- + main + -kan = 4) without
    listing every derivative; and
    (3) a curated list of assimilation REMNANTS in
    _NASAL_REMNANTS ("ait" from "kait" in "mengait", "yair"
    from "sair" in "penyair", "aih" from "raih" in "peraih"):
    a nasal prefix melts the root's initial consonant, leaving
    a vowel-initial remnant whose pair is still the root's
    hiatus. Only listed remnants split — a blanket rule would
    break real diphthongs ("memandai" is mem- + pandai = 3). A root-final diphthong splits
    before a derivational suffix or particle
    (-kan, -an, -i, -lah, -kah, -pun: "capai" + "-an" is
    ca-pa-i-an = 4, "mau" + "-kah" is ma-u-kah = 3), but NOT
    before the possessive enclitics -nya/-ku/-mu ("maunya" is
    2, "pulaunya" is 3). Hyphenated reduplication is counted
    per part ("baik-baik" is 4). The list is curated, not
    complete — anything unlisted falls back to the plain
    diphthong rule.

    English (lang="en"): vowel-letter runs (a, e, i, o, u, y)
    minus a silent final "e", plus one for a final "-le"
    after a consonant ("table" is 2, "syllable" is 3), plus
    a small curated list of hiatus words ("idea" 3, "real" 2,
    "science" 2, "rhythm" 2 — "fire" and "hour" are 1 and
    need no exception). "aisle"/"isle" are 1 (the "-le" rule
    would otherwise overcount them). Hiatus pairs that split
    are counted by _en_hiatus_extra ("ia"/"io"/"ua"/"ie"/"eo"/
    "ue"/"ao" with guards — "various" 3, "media" 3, "theory" 3,
    "diet" 2, "chaos" 2 — and "ea" only before "ct", as in
    "reaction"); "oe"/"oo"/"ui" have no rule (genuinely
    ambiguous) and live in _ENGLISH_EXCEPTIONS, as do words
    where "-ed" is pronounced ("naked" 2) and irregular words
    ("business" 2, "colonel" 2). A final "e" is silent unless
    it is part of a vowel digraph ("agree", "movie", "canoe",
    "sundae", "goodbye"), the "ue" of a real vowel after a
    consonant ("tissue", "value"), or after consonant + "r"
    ("centre" 2) — see _en_silent_final_e. A medial "e" stays
    silent before "-ly"/"-ful"/"-less"/"-ness" ("widely" 2,
    "hopeful" 2, "careless" 2, "awareness" 3) — see
    _en_medial_silent_e — but there is no "-ment" rule
    ("management" counts 4, want 3; "element" is 3, and the
    same letters cannot tell them apart). "-ed" after a
    consonant is silent ("walked" 1) except after t/d
    ("wanted" 2), and only when the "e" starts its own vowel
    group ("enjoyed" 2, "delayed" 2 — the "e" inside a run
    like "oye" is already counted as one). Known misses:
    "management", "adobe", "phoebe", "gruel", "unscientific",
    "nescience", "extraordinary" (AmE 5, BrE 6), "casually"
    is 4 and "spiritually" is 5 — both correct, the "-ually"
    "ua" always splits.

    A word with no vowel (a number, an abbreviation) counts as 1.
    Non-letters at the ends of the word are stripped first; the
    word is lowercased.
    """
    w = re.sub(r"^[^a-z]+|[^a-z]+$", "", word.lower())
    if not w:
        return 1
    if w in _SYLLABLE_WHOLE_WORD:
        return _SYLLABLE_WHOLE_WORD[w]
    if "-" in w:
        parts = [p for p in w.split("-") if p]
        if parts:
            return sum(_count_syllables(p, lang) for p in parts)
        return 1
    if lang == "en":
        if w in _ENGLISH_EXCEPTIONS:
            return _ENGLISH_EXCEPTIONS[w]
        # Plural of an exception word ("ideas" -> "idea", "poems"
        # -> "poem", "realities" -> "reality"); anything else falls
        # through to the normal count.
        if w.endswith("s") and w[:-1] in _ENGLISH_EXCEPTIONS:
            return _ENGLISH_EXCEPTIONS[w[:-1]]
        if w.endswith("ies") and (w[:-3] + "y") in _ENGLISH_EXCEPTIONS:
            return _ENGLISH_EXCEPTIONS[w[:-3] + "y"]
        groups = 0
        in_group = False
        for ch in w:
            if ch in _VOWELS or ch == "y":
                if not in_group:
                    groups += 1
                    in_group = True
            else:
                in_group = False
        if groups == 0:
            return 1
        groups += _en_hiatus_extra(w)
        if w.endswith("e") and groups > 1 and _en_silent_final_e(w):
            groups -= 1
        groups -= _en_medial_silent_e(w, groups)
        if len(w) >= 3 and w.endswith("le") and w[-3] not in _VOWELS and w[-3] != "y":
            groups += 1
        if (w.endswith("ed") and groups > 1 and len(w) >= 4
                and w[-3] not in _VOWELS and w[-3] != "y"
                and w[-3] not in "td"):
            # "-ed" after a consonant is silent ("walked" 1,
            # "baked" 1, "bored" 1) — except after t/d ("wanted" 2,
            # "needed" 2, "decided" 3), where it is its own
            # syllable. The "e" must start its own vowel group:
            # after a vowel letter or "y" it sits inside a run
            # already counted as one ("enjoyed" 2, "delayed" 2,
            # "destroyed" 2, "indeed" 2), so no subtraction.
            # Words where "-ed" is pronounced anyway ("naked",
            # "beloved", "hatred") live in _ENGLISH_EXCEPTIONS.
            groups -= 1
        return max(1, groups)
    root, affixes, split = _strip_id_affixes(w)
    skip = _SYLLABLE_EXCEPTIONS.get(root, ())
    if not skip:
        # A nasal-assimilation remnant ("ait" in "mengait"):
        # the pair is the melted root's hiatus, not a diphthong.
        skip = _NASAL_REMNANTS.get(root, ())
    vowels = sum(1 for ch in root if ch in _VOWELS)
    if vowels == 0:
        return max(1, affixes + 1)
    pairs = 0
    for d in _VOWEL_PAIRS_SINGLE:
        if d in skip:
            continue
        n = root.count(d)
        if d == "eu" and n > 1:
            # "eu" is rare (Acehnese/Sundanese loans); the
            # verified words with two "eu" (peuyeum, eureun)
            # have exactly one true monophthong, so the
            # subtraction is capped at 1 per word.
            n = 1
        pairs += n
    count = vowels - pairs
    if split:
        count += 1
    return max(1, count + affixes)


def readability_score(text: str, lang: str = "id") -> dict:
    """Flesch Reading Ease + Flesch-Kincaid Grade Level for a text.

    RE = 206.835 - 1.015 * (words/sentence) - 84.6 * (syllables/word),
    clamped to [0, 100]; FKGL = 0.39 * (words/sentence)
    + 11.8 * (syllables/word) - 15.59, clamped to a minimum of 0.
    Both are rounded to 1 decimal. The band is the standard Flesch
    label for the RE (90+ Very easy, 80+ Easy, 70+ Fairly easy, 60+
    Standard, 50+ Fairly difficult, 30+ Difficult, below 30 Very
    difficult). Words come from text.split(), sentences from
    _split_sentences (so abbreviations do not split a sentence);
    syllables come from _count_syllables with the same lang, so
    lang="en" counts English vowel runs instead of EYD diphthongs.
    Raises ValueError("teks kosong") for an empty or whitespace-only
    text, like every other tool in this file — and for a text with
    no real word at all (no token containing a letter: "...",
    "!!!", "123 456" all raise the same error, instead of scoring
    a perfect 100). No minimum word count:
    the formulas are pure arithmetic, so even one sentence scores.
    Every result carries the honesty note (see _READABILITY_NOTE).
    Raises ValueError for an unsupported lang: only "id" and "en"
    are supported — an unknown lang used to fall back to "id"
    silently, which hid caller bugs (audit #5, N-10).
    """
    if not text or not text.strip():
        raise ValueError("teks kosong")
    if lang not in ("id", "en"):
        raise ValueError("lang harus 'id' atau 'en'")
    words = text.split()
    if not any(any(ch.isalpha() for ch in w) for w in words):
        # Punctuation and digits alone are not a text: without this
        # a "..." scores RE 100.0 / FKGL 0.0, "Sangat mudah".
        raise ValueError("teks kosong")
    sentences = _split_sentences(text)
    n_words = len(words)
    n_sentences = len(sentences) if sentences else 1
    total_syllables = sum(_count_syllables(w, lang) for w in words)
    avg_words = n_words / n_sentences
    avg_syllables = total_syllables / n_words if n_words else 0.0
    ease = 206.835 - 1.015 * avg_words - 84.6 * avg_syllables
    ease = round(max(0.0, min(100.0, ease)), 1)
    grade = 0.39 * avg_words + 11.8 * avg_syllables - 15.59
    grade = round(max(0.0, grade), 1)
    band = _READABILITY_BANDS[-1][1 if lang == "id" else 2]
    for low, label_id, label_en in _READABILITY_BANDS:
        if ease >= low:
            band = label_id if lang == "id" else label_en
            break
    return {"flesch_reading_ease": ease,
            "flesch_kincaid_grade": grade,
            "band": band,
            "words": n_words,
            "sentences": n_sentences,
            "avg_words_per_sentence": round(avg_words, 1),
            "avg_syllables_per_word": round(avg_syllables, 1),
            "total_syllables": total_syllables,
            "note": _READABILITY_NOTE[lang]}


_READABILITY_STRINGS = {
    "id": {
        "heading": "Keterbacaan",
        "score": "Flesch Reading Ease",
        "grade": "Flesch-Kincaid Grade Level",
        "band": "Pita",
        "detail": ("Rata-rata {wps} kata/kalimat, {spw} suku kata/kata "
                   "({words} kata, {sentences} kalimat, "
                   "{syllables} suku kata)"),
    },
    "en": {
        "heading": "Readability",
        "score": "Flesch Reading Ease",
        "grade": "Flesch-Kincaid Grade Level",
        "band": "Band",
        "detail": ("Average {wps} words/sentence, {spw} syllables/word "
                   "({words} words, {sentences} sentences, "
                   "{syllables} syllables)"),
    },
}


def format_readability(result: dict, lang: str = "id") -> str:
    """Render a readability_score() result as readable text."""
    s = _READABILITY_STRINGS.get(lang, _READABILITY_STRINGS["id"])
    lines = [s["heading"], "",
             _bold(f"{s['score']}: {result['flesch_reading_ease']}/100"),
             _green(_bar(result["flesch_reading_ease"], 100)),
             f"{s['band']}: {result['band']}",
             f"{s['grade']}: {result['flesch_kincaid_grade']}",
             s["detail"].format(
                 wps=result["avg_words_per_sentence"],
                 spw=result["avg_syllables_per_word"],
                 words=result["words"],
                 sentences=result["sentences"],
                 syllables=result["total_syllables"]),
             "",
             result["note"]]
    return "\n".join(lines) + "\n"


def readability_main(argv=None, *, version=None) -> int:
    p = argparse.ArgumentParser(
        description="Flesch Reading Ease and Flesch-Kincaid Grade Level "
                    "for a text — pure formulas (Flesch 1948), no "
                    "language model, no API. Informative only: it always "
                    "exits 0, unless the input itself is bad (missing "
                    "file, empty text).")
    p.add_argument("input", nargs="?", help="plain-text file to check")
    p.add_argument("--text", help="check this text instead of a file")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="output language (default: id)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {version or __version__}")
    args = p.parse_args(argv)

    if args.text is not None:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")
    result = readability_score(text, lang=args.lang)
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_readability(result, lang=args.lang))
    return 0


# ======================================================================
# Library — analysis history + personal bibliography (stdlib sqlite3)
# ======================================================================
# One local file, no account, no cloud. `analyze --save` records a
# run (scores, missing citations, DOI counts, style, suggestions, the
# text itself and its hash); the cited references are upserted into
# the personal bibliography. `library` reads it back: history, one
# run in detail, reference search, import/export of refs.json files.

DEFAULT_LIBRARY_DB = os.path.join(
    os.path.expanduser("~"), ".academic-tools", "library.db")

_LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    quality_score INTEGER NOT NULL,
    jargon_count INTEGER NOT NULL,
    citations_missing INTEGER NOT NULL,
    doi_ok INTEGER NOT NULL,
    doi_total INTEGER NOT NULL,
    style_score INTEGER NOT NULL,
    suggestions_count INTEGER NOT NULL,
    text_hash TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_references (
    analysis_id INTEGER NOT NULL REFERENCES analyses(id),
    ref_key TEXT NOT NULL,
    PRIMARY KEY (analysis_id, ref_key)
);
CREATE TABLE IF NOT EXISTS library_references (
    key TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,
    year INTEGER,
    doi TEXT,
    url TEXT,
    added_at TEXT NOT NULL,
    source TEXT,
    data TEXT NOT NULL
);
"""


def library_path(db: str | None = None) -> str:
    """Resolve the library database path.

    Explicit --db wins, then the ACADEMIC_LIBRARY_DB environment
    variable (used by the tests), then ~/.academic-tools/library.db.
    """
    if db:
        return db
    env = os.environ.get("ACADEMIC_LIBRARY_DB")
    if env:
        return env
    return DEFAULT_LIBRARY_DB


def open_library(db: str | None = None, *,
                 create: bool = True) -> sqlite3.Connection:
    """Open the library database.

    With `create` (the default) the file and its directory are
    created when missing. With `create=False` (read-only callers)
    a missing file raises FileNotFoundError instead of creating
    one — a read must never conjure a library into existence.
    A 0-byte file is the one exception: it holds no data, so the
    schema is created on read, exactly as a save would do it
    (audit #7 N-6, option a) — reads and writes then agree on
    it. A corrupt or unreadable file raises ValueError with a
    plain message instead of leaking a sqlite3 traceback to the
    user. The message names only the file's basename, never the
    absolute path (audit #6 N-3): the library lives under the
    user's home directory, and the full path is local detail the
    error does not need to disclose.
    """
    path = library_path(db)
    if path == ":memory:":
        # A real in-memory database (audit #6 T-7): ":memory:" is a
        # legitimate sqlite3 path, not a corrupt file — the old code
        # opened it as a URI in read-write mode, found no tables,
        # and reported the misleading "pustaka rusak: :memory:".
        # An in-memory database is always fresh, so the schema is
        # created unconditionally; nothing on disk is ever touched,
        # and create=False still returns an (empty) library rather
        # than raising.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(_LIBRARY_SCHEMA)
        return conn
    conn = None
    try:
        if create:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            conn = sqlite3.connect(path)
        else:
            conn = sqlite3.connect(
                f"file:{quote(path)}?mode=rw", uri=True)
        conn.row_factory = sqlite3.Row
        if create:
            conn.executescript(_LIBRARY_SCHEMA)
        elif os.path.exists(path) and os.path.getsize(path) == 0:
            # Audit #7 N-6(a): a 0-byte file holds no data, so
            # creating the schema on read loses nothing and makes
            # reads agree with writes (a save self-heals the same
            # file with 200). Wrong-schema and garbage files are
            # NOT healed — their tables may hold user data — and
            # still raise "pustaka rusak" below.
            conn.executescript(_LIBRARY_SCHEMA)
    except sqlite3.OperationalError:
        if conn is not None:
            conn.close()
        if not create:
            # Audit #7 N-5: only a truly missing file means
            # "empty library". A directory at the path (or any
            # other file that cannot be opened) is corrupt, not
            # missing — the old code mapped every
            # OperationalError to FileNotFoundError, so a
            # directory answered 200 with an empty library.
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"pustaka belum ada: {os.path.basename(path)}")
            raise ValueError(
                f"pustaka rusak: {os.path.basename(path)} — hapus atau ganti file databasenya")
        raise ValueError(
            f"pustaka rusak: {os.path.basename(path)} — hapus atau ganti file databasenya")
    except sqlite3.Error:
        if conn is not None:
            conn.close()
        raise ValueError(
            f"pustaka rusak: {os.path.basename(path)} — hapus atau ganti file databasenya")
    try:
        for table, columns in _LIBRARY_COLUMNS.items():
            actual = {row[1] for row in conn.execute(
                f"PRAGMA table_info({table})")}
            if not columns <= actual:
                raise ValueError(
                    f"pustaka rusak: {os.path.basename(path)} — hapus atau ganti file databasenya")
    except (ValueError, sqlite3.Error):
        conn.close()
        raise ValueError(
            f"pustaka rusak: {os.path.basename(path)} — hapus atau ganti file databasenya")
    return conn


_LIBRARY_COLUMNS = {
    "analyses": {"id", "created_at", "title", "quality_score",
                 "jargon_count", "citations_missing", "doi_ok",
                 "doi_total", "style_score", "suggestions_count",
                 "text_hash", "text"},
    "analysis_references": {"analysis_id", "ref_key"},
    "library_references": {"key", "title", "authors", "year", "doi",
                           "url", "added_at", "source", "data"},
}


def _ref_columns(ref: dict) -> dict:
    authors = ref.get("authors") or ref.get("author") or ""
    if isinstance(authors, list):
        authors = ", ".join(str(a) for a in authors)
    year = ref.get("year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None
    return {
        "title": ref.get("title") or "",
        "authors": str(authors),
        "year": year,
        "doi": ref.get("doi") or "",
        "url": ref.get("url") or "",
    }


def _upsert_reference(conn: sqlite3.Connection, key: str, ref: dict,
                      source: str) -> str:
    """Insert a reference, or update it when the key already exists.

    Returns "added" or "updated".
    """
    cols = _ref_columns(ref)
    # Local time, with offset: the history shows the user's date,
    # not the UTC date (which is a day behind in the evening, WIB).
    now = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")
    cur = conn.execute(
        "SELECT key FROM library_references WHERE key = ?", (key,))
    exists = cur.fetchone() is not None
    conn.execute(
        """INSERT INTO library_references
           (key, title, authors, year, doi, url, added_at, source, data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET
             title=excluded.title, authors=excluded.authors,
             year=excluded.year, doi=excluded.doi, url=excluded.url,
             source=excluded.source, data=excluded.data,
             added_at=excluded.added_at""",
        (key, cols["title"], cols["authors"], cols["year"], cols["doi"],
         cols["url"], now, source, json.dumps(ref, ensure_ascii=False)))
    return "updated" if exists else "added"


# The library stores at most this many characters of a run's text
# (see save_analysis): a 200k-character manuscript would otherwise
# bloat the database for text nobody re-reads in full. The
# self-match hash in find_duplicates is taken from the same stored
# form, so re-analyzing a long run still recognises its own copy.
_MAX_STORED_TEXT = 100_000


def _canonical_text(text: str) -> str:
    """The stored form of a manuscript: stripped, capped, re-stripped.

    One canonical form, used everywhere a text is stored or hashed:
    strip first, then truncate to _MAX_STORED_TEXT, then strip any
    trailing whitespace the cut itself exposed. The final rstrip is
    what makes the form idempotent: applying _canonical_text twice
    is a no-op, so a stored text re-hashed later always yields the
    hash it was saved with. Without it, a cut landing on a space
    left the stored text ending in whitespace that a second
    canonicalisation stripped away, and sha256(stored_text) no
    longer equalled text_hash (audit #4, B-2).
    """
    return text.strip()[:_MAX_STORED_TEXT].rstrip()


def _stored_hash(text: str) -> str:
    """SHA-256 of the canonical stored form of a text.

    _canonical_text is idempotent, so hashing a text that is
    already in stored form gives the hash of those exact bytes —
    the same value save_analysis stores for it. A lone surrogate
    (e.g. "\\ud800" from a JSON body) cannot be UTF-8-encoded:
    that is a plain ValueError with a clean message, never the
    raw codec error (audit #6 N-2).
    """
    try:
        return hashlib.sha256(
            _canonical_text(text).encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise ValueError(
            "teks mengandung karakter surrogate yang tidak valid") from None


def _ws_collapsed_hash(text: str) -> str:
    """SHA-256 of a text with every internal whitespace run collapsed
    to one space — for own-run COMPARISON only (audit #6 N-5).

    This is deliberately NOT _canonical_text and NOT
    _normalize_sentence: the stored form (and its hash) must stay
    byte-exact — sha256(stored_text) == text_hash (audit #5 B-2) —
    and the comparison must stay case- and punctuation-sensitive,
    collapsing whitespace only. A run saved from "a  b" and a query
    of "a b" are the same manuscript typed with different spacing.
    """
    collapsed = re.sub(r"\s+", " ", text)
    try:
        return hashlib.sha256(
            _canonical_text(collapsed).encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise ValueError(
            "teks mengandung karakter surrogate yang tidak valid") from None


def _legacy_stored_hash(text: str) -> str:
    """SHA-256 as stored by v1.25.2: truncate first, then strip.

    Kept only so runs saved by v1.25.2 are still recognised as
    their own text (see find_duplicates). New runs use
    _stored_hash. Same clean error as _stored_hash on a lone
    surrogate (audit #6 N-2).
    """
    try:
        return hashlib.sha256(
            text[:_MAX_STORED_TEXT].strip().encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise ValueError(
            "teks mengandung karakter surrogate yang tidak valid") from None


def save_analysis(text: str, result: dict,
                  references: dict | None = None,
                  title: str | None = None,
                  db: str | None = None) -> int:
    """Record an analyze_text_quality() run in the library.

    Every reference in the bibliography is upserted into the
    personal bibliography (source "analyze"); the cited ones are
    linked to the run. Returns the run id.

    A reference that cannot be serialized to JSON raises ValueError
    here, before anything is written — never a bare TypeError from
    deep inside the upsert. Only the canonical form of the text is
    stored (see _canonical_text: stripped, capped at 100_000
    characters, then re-stripped), and the stored hash is the
    SHA-256 of exactly those stored bytes — never a re-canonicalised
    hash — so sha256(stored_text) == text_hash always holds.

    The result shape is validated first, the same way references
    are: a missing 'quality_score' or 'style'/'style_score', or a
    mistyped container (jargon, citations, doi_verification,
    suggestions), raises ValueError before anything is written —
    never a bare KeyError/AttributeError from the INSERT below.
    """
    if not isinstance(result, dict):
        raise ValueError(
            "hasil analisis tidak valid: harus berupa objek")
    if "quality_score" not in result:
        raise ValueError(
            "hasil analisis tidak lengkap: 'quality_score' tidak ada")
    style = result.get("style")
    if not isinstance(style, dict) or "style_score" not in style:
        raise ValueError(
            "hasil analisis tidak lengkap: 'style.style_score' "
            "tidak ada")
    if "jargon" in result and result["jargon"] is not None \
            and not isinstance(result["jargon"], list):
        raise ValueError(
            "hasil analisis tidak valid: 'jargon' harus berupa daftar")
    if "citations" in result and result["citations"] is not None \
            and not isinstance(result["citations"], dict):
        raise ValueError(
            "hasil analisis tidak valid: 'citations' harus berupa "
            "objek")
    if "doi_verification" in result \
            and result["doi_verification"] is not None \
            and not isinstance(result["doi_verification"], dict):
        raise ValueError(
            "hasil analisis tidak valid: 'doi_verification' harus "
            "berupa objek")
    if "suggestions" in result \
            and not isinstance(result["suggestions"], dict):
        raise ValueError(
            "hasil analisis tidak valid: 'suggestions' harus berupa "
            "objek")
    text = _canonical_text(text)
    # Hash of the stored bytes themselves (text is already canonical
    # here): never canonicalise again, or a cut landing on whitespace
    # would hash a shorter string than the one stored (audit #4,
    # B-2). A lone surrogate cannot be UTF-8-encoded: that is a
    # plain ValueError with a clean message, never the raw codec
    # error (audit #6 N-2) — raised here, before any connection is
    # opened, so no partial row is ever written.
    try:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise ValueError(
            "teks mengandung karakter surrogate yang tidak valid") from None
    if references is not None:
        # Shape first (a non-dict reference is a ValueError, never
        # a bare AttributeError from deep inside the upsert), before
        # anything is written or any connection opened.
        _validate_references(references)
    if references:
        for key, ref in references.items():
            try:
                json.dumps(ref, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"referensi '{key}' tidak bisa disimpan: {e}")
    if title is None:
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        title = first_line[:60] or "tanpa judul"
    cit = result.get("citations") or {}
    dv = result.get("doi_verification") or {}
    with_doi = [v for v in dv.values() if v.get("doi")]
    conn = open_library(db)
    try:
        cur = conn.execute(
            """INSERT INTO analyses
               (created_at, title, quality_score, jargon_count,
                citations_missing, doi_ok, doi_total, style_score,
                suggestions_count, text_hash, text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.datetime.now().astimezone().isoformat(
                timespec="seconds"),
             title, result["quality_score"], len(result.get("jargon") or []),
             len(cit.get("missing") or []),
             sum(1 for v in with_doi if v.get("verdict") == "ok"),
             len(with_doi), result["style"]["style_score"],
             result.get("suggestions", {}).get("count", 0),
             text_hash, text))
        analysis_id = cur.lastrowid
        if references:
            # Every reference enters the personal bibliography, not
            # only the cited ones: an unused entry is still a
            # reference the author owns.
            for key, ref in references.items():
                _upsert_reference(conn, key, ref, "analyze")
            for key in cit.get("cited") or []:
                if key in references:
                    conn.execute(
                        "INSERT OR IGNORE INTO analysis_references "
                        "(analysis_id, ref_key) VALUES (?, ?)",
                        (analysis_id, key))
        conn.commit()
        return analysis_id
    finally:
        conn.close()


def list_analyses(db: str | None = None, limit: int = 20) -> list[dict]:
    """Past runs, newest first (id, date, title, scores)."""
    if limit is not None:
        limit = max(1, min(limit, 1000))
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return []
    try:
        rows = conn.execute(
            """SELECT id, created_at, title, quality_score, jargon_count,
                      citations_missing, doi_ok, doi_total, style_score,
                      suggestions_count
               FROM analyses ORDER BY id DESC LIMIT ?""",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_analysis(analysis_id: int,
                 db: str | None = None) -> dict | None:
    """One run in full: the row, its cited reference keys, the text.

    An id outside SQLite's signed 64-bit range can never match a
    row — and binding it raises OverflowError, which used to escape
    as a live 500 on GET /api/library/analysis (audit #6 T-1):
    it is simply "not found" here, like any other absent id.
    """
    if not isinstance(analysis_id, int) \
            or isinstance(analysis_id, bool) \
            or not -(2 ** 63) <= analysis_id <= 2 ** 63 - 1:
        return None
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return None
    try:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?",
            (analysis_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        refs = conn.execute(
            "SELECT ref_key FROM analysis_references "
            "WHERE analysis_id = ? ORDER BY ref_key",
            (analysis_id,)).fetchall()
        result["references"] = [r["ref_key"] for r in refs]
        return result
    finally:
        conn.close()


def list_references(db: str | None = None, limit: int = 20) -> list[dict]:
    """Personal bibliography, most recently added first."""
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return []
    try:
        rows = conn.execute(
            """SELECT key, title, authors, year, doi, url, added_at, source
               FROM library_references ORDER BY added_at DESC, key LIMIT ?""",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_references(query: str, db: str | None = None,
                      limit: int = 20) -> list[dict]:
    """Search the bibliography by key, title, authors, or DOI."""
    escaped = (query.replace("\\", "\\\\").replace("%", "\\%")
               .replace("_", "\\_"))
    like = f"%{escaped}%"
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return []
    try:
        rows = conn.execute(
            """SELECT key, title, authors, year, doi, url, added_at, source
               FROM library_references
               WHERE key LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\'
                     OR authors LIKE ? ESCAPE '\\'
                     OR doi LIKE ? ESCAPE '\\'
               ORDER BY added_at DESC, key LIMIT ?""",
            (like, like, like, like, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def import_references(refs: dict, db: str | None = None,
                      source: str = "import") -> dict:
    """Upsert a bibliography dict ({key: ref}) into the library.

    Returns {"added": n, "updated": m}. Shape is validated first —
    a non-dict reference is a ValueError, never a bare AttributeError
    from deep inside the upsert.
    """
    _validate_references(refs)
    conn = open_library(db)
    counts = {"added": 0, "updated": 0}
    try:
        for key, ref in refs.items():
            counts[_upsert_reference(conn, key, ref, source)] += 1
        conn.commit()
        return counts
    finally:
        conn.close()


def export_references(db: str | None = None) -> dict:
    """The whole personal bibliography as a {key: ref} dict."""
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return {}
    try:
        rows = conn.execute(
            "SELECT key, data FROM library_references ORDER BY key"
        ).fetchall()
        return {r["key"]: json.loads(r["data"]) for r in rows}
    finally:
        conn.close()


def format_history(rows: list[dict]) -> str:
    """Render list_analyses() rows as a readable table."""
    if not rows:
        return "Belum ada riwayat analisis — jalankan analyze --save dulu.\n"
    lines = ["Riwayat analisis:"]
    for r in rows:
        lines.append(
            f"  #{r['id']} {r['created_at'][:10]} {r['title']} — "
            f"skor {r['quality_score']}/100, gaya {r['style_score']}/25, "
            f"jargon {r['jargon_count']}, sitasi hilang "
            f"{r['citations_missing']}, DOI {r['doi_ok']}/{r['doi_total']}")
    return "\n".join(lines) + "\n"


def format_analysis_detail(analysis: dict) -> str:
    """Render one get_analysis() result in full."""
    lines = [
        f"Analisis #{analysis['id']} — {analysis['title']}",
        f"Tanggal: {analysis['created_at']}",
        f"Skor kualitas: {analysis['quality_score']}/100",
        f"Gaya: {analysis['style_score']}/25",
        f"Jargon: {analysis['jargon_count']} istilah",
        f"Sitasi hilang: {analysis['citations_missing']}",
        f"DOI terverifikasi: {analysis['doi_ok']}/{analysis['doi_total']}",
        f"Saran rewrite: {analysis['suggestions_count']}",
    ]
    if analysis["references"]:
        lines.append("Referensi dikutip: " + ", ".join(analysis["references"]))
    lines.append("")
    lines.append(analysis["text"])
    return "\n".join(lines) + "\n"


def format_references(rows: list[dict]) -> str:
    """Render list/search_reference rows as a readable list."""
    if not rows:
        return "Tidak ada referensi di pustaka.\n"
    lines = ["Referensi di pustaka:"]
    for r in rows:
        year = f" ({r['year']})" if r.get("year") else ""
        lines.append(f"  - {r['key']}{year}: {r.get('title') or '-'}"
                     + (f" — {r['authors']}" if r.get("authors") else "")
                     + (f" — doi:{r['doi']}" if r.get("doi") else ""))
    return "\n".join(lines) + "\n"


def library_stats(db=None, *, top_refs: int = 5) -> dict:
    """Statistics over the saved library: score trend + most-cited refs.

    Returns {"runs", "average_score", "best", "trend", "most_cited"}.
    "trend" is every run oldest first ({id, title, date, quality_score});
    "most_cited" is the top `top_refs` references by how many saved
    runs cite them ({key, title, count}). Empty library: runs 0,
    average_score None, best None, trend [], most_cited [].
    """
    top_refs = max(1, min(top_refs, 100))
    try:
        conn = open_library(db, create=False)
    except FileNotFoundError:
        return {"runs": 0, "average_score": None, "best": None,
                "trend": [], "most_cited": []}
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, quality_score FROM analyses "
            "ORDER BY id ASC").fetchall()
        cited = conn.execute(
            "SELECT ar.ref_key, COUNT(*) AS n FROM analysis_references ar "
            "GROUP BY ar.ref_key ORDER BY n DESC, ar.ref_key ASC "
            "LIMIT ?", (top_refs,)).fetchall()
        titles = {r["key"]: r["title"] for r in conn.execute(
            "SELECT key, title FROM library_references").fetchall()}
    finally:
        conn.close()
    scores = [r["quality_score"] for r in rows]
    best = None
    if rows:
        top = max(rows, key=lambda r: (r["quality_score"], -r["id"]))
        best = {"id": top["id"], "title": top["title"],
                "quality_score": top["quality_score"]}
    return {
        "runs": len(rows),
        "average_score": (round(sum(scores) / len(scores), 1)
                          if scores else None),
        "best": best,
        "trend": [{"id": r["id"], "title": r["title"],
                   "date": r["created_at"][:10],
                   "quality_score": r["quality_score"]} for r in rows],
        "most_cited": [{"key": c["ref_key"],
                        "title": titles.get(c["ref_key"]),
                        "count": c["n"]} for c in cited],
    }


_LIBRARY_STATS_STRINGS = {
    "id": {
        "heading": "Statistik pustaka",
        "runs": "analisis tersimpan",
        "average": "Rata-rata skor",
        "best": "Skor terbaik",
        "trend": "Tren skor",
        "most_cited": "Referensi paling sering dikutip",
        "none": "Belum ada riwayat analisis — jalankan analyze --save dulu.",
        "times": "kali",
    },
    "en": {
        "heading": "Library statistics",
        "runs": "saved analyses",
        "average": "Average score",
        "best": "Best score",
        "trend": "Score trend",
        "most_cited": "Most cited references",
        "none": "No analysis history yet — run analyze --save first.",
        "times": "times",
    },
}


def format_library_stats(stats: dict, lang: str = "id") -> str:
    """Render a library_stats() result as readable text."""
    s = _LIBRARY_STATS_STRINGS.get(lang, _LIBRARY_STATS_STRINGS["id"])
    if not stats["runs"]:
        return s["none"] + "\n"
    lines = [s["heading"],
             f"{stats['runs']} {s['runs']}",
             f"{s['average']}: {stats['average_score']}/100"]
    if stats["best"]:
        lines.append(f"{s['best']}: {stats['best']['title']} "
                     f"({stats['best']['quality_score']}/100)")
    lines.append(f"{s['trend']}:")
    for t in stats["trend"]:
        lines.append(f"  {t['date']} {t['title']} — "
                     f"{_bar(t['quality_score'], 100, width=10)} "
                     f"{t['quality_score']}/100")
    if stats["most_cited"]:
        lines.append(f"{s['most_cited']}:")
        for c in stats["most_cited"]:
            label = c["title"] or c["key"]
            lines.append(f"  - {c['key']}: {label} "
                         f"({c['count']} {s['times']})")
    return "\n".join(lines) + "\n"


def library_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Analysis history and personal bibliography in one "
                    "local SQLite file (~/.academic-tools/library.db). "
                    "Pick one action per call.")
    p.add_argument("--db", help="library database path "
                   "(default: ~/.academic-tools/library.db)")
    p.add_argument("--history", action="store_true",
                   help="list past analyze runs, newest first")
    p.add_argument("--stats", action="store_true",
                   help="show library statistics: score trend and "
                        "most-cited references")
    p.add_argument("--show", type=int, metavar="ID",
                   help="show one past run in full")
    p.add_argument("--refs", action="store_true",
                   help="list the personal bibliography")
    p.add_argument("--search", metavar="QUERY",
                   help="search the bibliography by key, title, authors, or DOI")
    p.add_argument("--import", dest="import_path", metavar="REFS.JSON",
                   help="import a bibliography JSON file into the library")
    p.add_argument("--export", dest="export_path", metavar="OUT.JSON",
                   help="export the personal bibliography to a JSON file")
    p.add_argument("--limit", type=int, default=20,
                   help="rows to show (default: 20)")
    p.add_argument("--json", action="store_true",
                   help="print the raw result as JSON instead of readable text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)
    try:
        return _library_run(args, p)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1


def _library_run(args, parser) -> int:
    if args.stats:
        stats = library_stats(db=args.db)
        if args.json:
            sys.stdout.write(json.dumps(stats, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_library_stats(stats))
        return 0
    if args.history:
        rows = list_analyses(db=args.db, limit=args.limit)
        if args.json:
            sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_history(rows))
        return 0
    if args.show is not None:
        analysis = get_analysis(args.show, db=args.db)
        if analysis is None:
            print(f"tidak ada analisis #{args.show} di pustaka",
                  file=sys.stderr)
            return 1
        if args.json:
            sys.stdout.write(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_analysis_detail(analysis))
        return 0
    if args.search is not None:
        rows = search_references(args.search, db=args.db, limit=args.limit)
        if args.json:
            sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_references(rows))
        return 0
    if args.refs:
        rows = list_references(db=args.db, limit=args.limit)
        if args.json:
            sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(format_references(rows))
        return 0
    if args.import_path:
        refs = load_references(args.import_path)
        counts = import_references(refs, db=args.db)
        print(f"Ditambahkan: {counts['added']}, diperbarui: {counts['updated']}")
        return 0
    if args.export_path:
        refs = export_references(db=args.db)
        with open(args.export_path, "w", encoding="utf-8") as f:
            json.dump(refs, f, ensure_ascii=False, indent=2)
        print(f"Diekspor: {len(refs)} referensi -> {args.export_path}")
        return 0
    parser.print_help()
    return 0


def cite_main(argv=None, *, version=None) -> int:
    p = argparse.ArgumentParser(description="Weave citations into narrative text.")
    p.add_argument("input", nargs="?", help="plain-text file with [cite:key] markers")
    p.add_argument("--text", help="weave this text instead of a file")
    p.add_argument("--refs", help="bibliography JSON file (required unless --list-*)")
    p.add_argument("--style", choices=STYLES, help="citation style")
    p.add_argument("--jurusan", help="major (Indonesian or English name); sets the recommended style")
    p.add_argument("--lang", choices=["id", "en"], default="id", help="output language (default: id)")
    p.add_argument("--list-styles", action="store_true", help="list citation styles and exit")
    p.add_argument("--list-jurusan", action="store_true", help="list majors and their recommended style, then exit")
    p.add_argument("--lookup", metavar="DOI-OR-TITLE",
                   help="fetch one reference by DOI or title (OpenAlex/Crossref) and print it as JSON")
    p.add_argument("--key", help="bibliography key to use with --add-to (default: auto)")
    p.add_argument("--add-to", metavar="REFS.JSON",
                   help="with --lookup: append the fetched reference to this bibliography file")
    p.add_argument("--export-bibtex", action="store_true",
                   help="export the bibliography to BibTeX (.bib) instead of weaving")
    p.add_argument("--export-ris", action="store_true",
                   help="export the bibliography to RIS (.ris) instead of weaving")
    p.add_argument("--out", metavar="FILE",
                   help="with --export-bibtex/--export-ris: write the file here (default: stdout)")
    p.add_argument("--audit", action="store_true",
                   help="audit citations: report markers with no bibliography entry, "
                   "and entries never cited, instead of weaving")
    p.add_argument("--check-links", action="store_true",
                   help="with --audit: also verify each cited reference's DOI/arXiv/URL resolves")
    p.add_argument("--verify", action="store_true",
                   help="verify every reference DOI against Crossref and OpenAlex")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {version or __version__}")
    args = p.parse_args(argv)

    if args.list_styles:
        print("Citation styles: " + ", ".join(STYLES))
        return 0
    if args.list_jurusan:
        for d in DISCIPLINES:
            print(f"{d['id']} / {d['en']} — {d['style']}")
        return 0

    if args.export_bibtex and args.export_ris:
        p.error("--export-bibtex and --export-ris cannot be combined")

    if args.lookup:
        try:
            ref = lookup_reference(args.lookup)
        except LookupNotFoundError as e:
            # A confirmed 404 is an ordinary failure, not a usage
            # error: exit 1 with a plain message, like every other
            # subcommand's failures (audit #6 N-6) — not argparse's
            # exit 2.
            print(f"cite: error: {e}", file=sys.stderr)
            return 1
        except LookupError as e:
            p.error(str(e))
        if args.add_to:
            key = save_reference(ref, args.add_to, key=args.key)
            print(f"Saved as [{key}] in {args.add_to}")
        else:
            print(json.dumps(ref, ensure_ascii=False, indent=2))
        return 0

    if args.export_bibtex:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --export-bibtex")
        references = load_references(args.refs)
        bib = export_bibtex(references)
        if args.out:
            try:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(bib)
            except FileNotFoundError:
                raise ValueError(f"File tidak ditemukan: {args.out}")
            print(f"Wrote {len(references)} entries to {args.out}")
        else:
            sys.stdout.write(bib)
        return 0

    if args.export_ris:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --export-ris")
        references = load_references(args.refs)
        ris = export_ris(references)
        if args.out:
            try:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(ris)
            except FileNotFoundError:
                raise ValueError(f"File tidak ditemukan: {args.out}")
            print(f"Wrote {len(references)} entries to {args.out}")
        else:
            sys.stdout.write(ris)
        return 0

    if args.audit:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --audit")
        if args.text:
            text = args.text
        elif args.input:
            if not os.path.isfile(args.input):
                raise ValueError(f"File tidak ditemukan: {args.input}")
            with open(args.input, encoding="utf-8") as f:
                text = f.read()
        else:
            p.error("give a file or --text")
        references = load_references(args.refs)
        result = audit_citations(text, references)
        links = None
        if args.check_links:
            links = check_reference_links(references, keys=result["cited"])
        sys.stdout.write(format_audit(result, lang=args.lang, links=links))
        dead = any(not v[1] for v in (links or {}).values())
        return 1 if result["missing"] or dead else 0

    if args.verify:
        if not args.refs:
            p.error("--refs <bibliography.json> is required with --verify")
        references = load_references(args.refs)
        result = verify_reference_dois(references)
        sys.stdout.write(format_verification(result, lang=args.lang))
        return 1 if any(r["verdict"] == "missing" for r in result.values()) else 0

    style = args.style
    if not style and args.jurusan:
        style = style_for_discipline(args.jurusan)
        if not style:
            p.error(f"unknown jurusan: {args.jurusan} (see --list-jurusan)")
    if not style:
        style = "apa"
    if not args.refs:
        p.error("--refs <bibliography.json> is required")

    if args.text:
        text = args.text
    elif args.input:
        if not os.path.isfile(args.input):
            raise ValueError(f"File tidak ditemukan: {args.input}")
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        p.error("give a file or --text")

    references = load_references(args.refs)
    output, _ = weave(text, references, style=style, lang=args.lang)
    sys.stdout.write(output)
    return 0


# ======================================================================
# Thesis Prompts (Prompt Skripsi)
# ======================================================================
# Ready-made prompt templates for writing a thesis (skripsi), one per
# task: research roadmap, each chapter, defense prep, publication.
# Each template has {placeholders} the student fills with their own
# title, theory, method, data, etc., then pastes into the recommended
# AI tool (ChatGPT, Grok, Claude, Gemini, Perplexity, Manus).
# Templates are original wording written for this repo: they follow the
# usual structure of thesis-writing prompts, they do not copy any
# third-party prompt collection. The skill in
# skills/research/skripsi-prompts/SKILL.md carries the same templates.
# Rules: these prompts help the student write their own thesis. They
# never write a whole thesis for the student, and no reference or data
# is ever invented — a missing reference stays missing.
PROMPTS = [
    {
        "id": "roadmap",
        "name": "Roadmap Penelitian",
        "name_en": "Research Roadmap",
        "category": "Persiapan",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "teori", "label": "Teori yang digunakan", "label_en": "Theory used"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "bulan", "label": "Jangka waktu (bulan)", "label_en": "Duration (months)"},
            {"key": "tanggal", "label": "Tanggal mulai", "label_en": "Start date"},
        ],
        "template": (
            "Saya sedang mengerjakan skripsi berjudul {judul}, memakai teori {teori} "
            "dan metode {metode}. Bantu saya menyusun rencana kerja penelitian dari awal "
            "sampai selesai: mulai dari merumuskan masalah, membaca literatur, menyiapkan "
            "instrumen, mengumpulkan data, menganalisis, hingga menulis laporan dan "
            "menyiapkan publikasi. Waktu yang saya punya {bulan} bulan, mulai {tanggal}. "
            "Tuliskan sebagai daftar langkah berurutan dengan perkiraan durasi tiap langkahnya."
        ),
        "template_en": (
            "I am working on a thesis titled {judul}, using {teori} theory and the "
            "{metode} method. Help me build a work plan for the research from start to "
            "finish: from formulating the problem, reading the literature, preparing "
            "instruments, collecting data, analyzing, to writing the report and preparing "
            "publication. I have {bulan} months, starting {tanggal}. Write it as an "
            "ordered list of steps with an estimated duration for each step."
        ),
    },
    {
        "id": "abstrak",
        "name": "Abstrak Skripsi",
        "name_en": "Thesis Abstract",
        "category": "Abstrak",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "masalah", "label": "Masalah yang diteliti", "label_en": "Problem studied"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "hasil", "label": "Hasil utama penelitian", "label_en": "Main findings"},
            {"key": "kunci", "label": "Kata kunci (3-5 kata)", "label_en": "Keywords (3-5 words)"},
        ],
        "template": (
            "Saya sedang menulis abstrak skripsi berjudul {judul}. Masalah yang saya "
            "teliti: {masalah}. Metode yang saya pakai: {metode}. Hasil utama penelitian "
            "saya: {hasil}. Tolong susun abstrak dalam satu paragraf (sekitar 150-250 kata) "
            "dengan struktur: latar belakang singkat, tujuan, metode, hasil utama, dan "
            "kesimpulan. Akhiri dengan kata kunci: {kunci}. Gunakan bahasa akademik yang "
            "ringkas dan jelas, tanpa menambahkan data atau klaim yang tidak saya sebutkan."
        ),
        "template_en": (
            "I am writing the abstract for my thesis titled {judul}. The problem I "
            "studied: {masalah}. The method I used: {metode}. My main findings: {hasil}. "
            "Please draft the abstract as a single paragraph (about 150-250 words) with "
            "this structure: brief background, objective, method, main findings, and "
            "conclusion. End with keywords: {kunci}. Use concise, clear academic language, "
            "and do not add any data or claims I did not mention."
        ),
    },
    {
        "id": "kata-pengantar",
        "name": "Kata Pengantar",
        "name_en": "Preface",
        "category": "Persiapan",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "pembimbing", "label": "Nama dosen pembimbing", "label_en": "Supervisor's name"},
            {"key": "ucapan", "label": "Pihak yang ingin diucapkan terima kasih", "label_en": "People to thank"},
        ],
        "template": (
            "Saya sedang menulis kata pengantar skripsi berjudul {judul}, dibimbing oleh "
            "{pembimbing}. Pihak-pihak yang ingin saya ucapkan terima kasih: {ucapan}. "
            "Tolong susun kata pengantar yang sopan dan formal: buka dengan puji syukur, "
            "sebutkan judul skripsi dan tujuannya, ucapkan terima kasih kepada pihak-pihak "
            "di atas dengan kalimat yang tulus dan spesifik, lalu tutup dengan harapan "
            "semoga skripsi ini bermanfaat. Jangan tambahkan nama atau pihak yang tidak "
            "saya sebutkan."
        ),
        "template_en": (
            "I am writing the preface for my thesis titled {judul}, supervised by "
            "{pembimbing}. The people I want to thank: {ucapan}. Please draft a polite, "
            "formal preface: open with gratitude, state the thesis title and its purpose, "
            "thank the people above with sincere and specific sentences, then close with "
            "a hope that this thesis will be useful. Do not add any names or parties I "
            "did not mention."
        ),
    },
    {
        "id": "latar-belakang",
        "name": "Latar Belakang (Bab 1)",
        "name_en": "Background (Chapter 1)",
        "category": "Bab 1",
        "tool": "Grok",
        "fields": [
            {"key": "topik", "label": "Topik penelitian", "label_en": "Research topic"},
            {"key": "catatan", "label": "Catatan / poin dari pembimbing", "label_en": "Notes from supervisor"},
            {"key": "paragraf", "label": "Jumlah paragraf", "label_en": "Number of paragraphs"},
        ],
        "template": (
            "Saya sedang menulis bagian latar belakang untuk skripsi bertopik {topik}. "
            "Berikut poin-poin dari saya dan dosen pembimbing: {catatan}. Tolong rangkai "
            "poin-poin itu menjadi latar belakang yang runtut dengan struktur piramida "
            "terbalik, dari isu umum ke konteks lokal, lalu ke masalah spesifik penelitian "
            "saya. Sertakan data atau referensi pendukung bila ada, gunakan bahasa akademik "
            "standar skripsi, dan buat dalam {paragraf} paragraf yang mengalir dan siap "
            "dipakai di dokumen skripsi."
        ),
        "template_en": (
            "I am writing the background section for a thesis on {topik}. Here are the "
            "points from me and my supervisor: {catatan}. Please weave these points into "
            "a coherent background with an inverted-pyramid structure, from the general "
            "issue to the local context, then to the specific problem of my research. "
            "Include supporting data or references where available, use standard academic "
            "thesis language, and make it {paragraf} paragraphs that flow and are ready "
            "to use in the thesis document."
        ),
    },
    {
        "id": "rumusan-masalah",
        "name": "Rumusan Masalah & Tujuan (Bab 1)",
        "name_en": "Problem Statement & Objectives (Chapter 1)",
        "category": "Bab 1",
        "tool": "ChatGPT",
        "fields": [
            {"key": "topik", "label": "Topik penelitian", "label_en": "Research topic"},
            {"key": "masalah", "label": "Masalah yang dihadapi", "label_en": "Problem faced"},
            {"key": "tujuan", "label": "Tujuan penelitian", "label_en": "Research objective"},
        ],
        "template": (
            "Saya sedang menulis Bab 1 skripsi bertopik {topik}. Masalah yang saya "
            "hadapi: {masalah}. Tujuan penelitian saya: {tujuan}. Tolong bantu saya "
            "merumuskan masalah penelitian dalam bentuk pertanyaan penelitian yang jelas "
            "dan terukur, lalu turunkan tujuan penelitian yang sesuai dengan pertanyaan "
            "itu. Beri 2-3 rumusan masalah beserta tujuan masing-masing, dan jelaskan "
            "singkat kenapa rumusan itu layak diteliti."
        ),
        "template_en": (
            "I am writing Chapter 1 of my thesis on {topik}. The problem I am facing: "
            "{masalah}. My research objective: {tujuan}. Please help me turn this into "
            "clear, measurable research questions, then derive matching research objectives "
            "for each question. Give 2-3 problem statements with their objectives, and "
            "briefly explain why each is worth researching."
        ),
    },
    {
        "id": "banding-teori",
        "name": "Membandingkan 3 Teori (Bab 2)",
        "name_en": "Comparing 3 Theories (Chapter 2)",
        "category": "Bab 2",
        "tool": "Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
        ],
        "template": (
            "Saya sedang menulis skripsi tentang {judul}. Tolong carikan tiga teori yang "
            "relevan dengan topik ini, lalu bandingkan ketiganya dalam tabel: nama teori, "
            "tokoh atau penelitinya, konsep utama, kelebihan dan keterbatasan, serta "
            "relevansinya dengan penelitian saya. Di akhir, beri rekomendasi teori mana "
            "yang paling cocok dijadikan landasan teori penelitian saya."
        ),
        "template_en": (
            "I am writing a thesis about {judul}. Please find three theories relevant to "
            "this topic, then compare them in a table: theory name, its figure or "
            "researcher, main concepts, strengths and limitations, and relevance to my "
            "research. At the end, recommend which theory fits best as the theoretical "
            "foundation of my research."
        ),
    },
    {
        "id": "review-terdahulu",
        "name": "Review Penelitian Terdahulu (Bab 2)",
        "name_en": "Review of Prior Research (Chapter 2)",
        "category": "Bab 2",
        "tool": "Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "daftar", "label": "Daftar penelitian terdahulu", "label_en": "List of prior studies"},
            {"key": "gaya", "label": "Gaya sitasi (mis. APA 7th)", "label_en": "Citation style (e.g. APA 7th)"},
        ],
        "template": (
            "Saya sedang meneliti {judul}. Berikut daftar penelitian terdahulu yang saya "
            "jadikan rujukan: {daftar}. Tolong buat ulasan kritis terhadap penelitian-"
            "penelitian itu, dengan fokus pada metode, sampel, hasil, dan keterbatasannya. "
            "Jelaskan celah penelitian (research gap) yang belum banyak diteliti dan "
            "bagaimana penelitian saya bisa mengisinya. Tulis dalam bahasa akademik, "
            "sekitar 3-4 paragraf, dengan sitasi gaya {gaya}."
        ),
        "template_en": (
            "I am researching {judul}. Here is the list of prior studies I am using as "
            "references: {daftar}. Please write a critical review of these studies, "
            "focusing on method, sample, findings, and limitations. Explain the research "
            "gap that has not been widely studied and how my research can fill it. Write "
            "in academic language, about 3-4 paragraphs, with citations in {gaya} style."
        ),
    },
    {
        "id": "metodologi",
        "name": "Metodologi Penelitian (Bab 3)",
        "name_en": "Research Methodology (Chapter 3)",
        "category": "Bab 3",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "jenis", "label": "Jenis penelitian", "label_en": "Research type"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "populasi", "label": "Populasi dan sampel", "label_en": "Population and sample"},
            {"key": "pengumpulan", "label": "Teknik pengumpulan data", "label_en": "Data collection technique"},
            {"key": "analisis", "label": "Teknik analisis data", "label_en": "Data analysis technique"},
        ],
        "template": (
            "Saya sedang menulis Bab 3 Metodologi Penelitian untuk skripsi berjudul {judul}. "
            "Jenis penelitian saya: {jenis}. Metode yang digunakan: {metode}. Populasi dan "
            "sampel: {populasi}. Teknik pengumpulan data: {pengumpulan}. Teknik analisis "
            "data: {analisis}. Susunlah Bab 3 yang lengkap dan logis, mencakup desain "
            "penelitian, definisi operasional variabel, populasi dan sampel, instrumen "
            "penelitian, teknik pengumpulan data, dan teknik analisis data. Pastikan isinya "
            "selaras dengan judul serta Bab 1 dan 2, dan jelaskan alasan metode ini paling "
            "tepat untuk penelitian saya, dengan bahasa akademik yang rapi."
        ),
        "template_en": (
            "I am writing Chapter 3, Research Methodology, for a thesis titled {judul}. "
            "My research type: {jenis}. Method used: {metode}. Population and sample: "
            "{populasi}. Data collection technique: {pengumpulan}. Data analysis technique: "
            "{analisis}. Draft a complete and logical Chapter 3, covering research design, "
            "operational definitions of variables, population and sample, research "
            "instruments, data collection techniques, and data analysis techniques. Make "
            "sure the content aligns with the title and Chapters 1 and 2, and explain why "
            "this method is the best fit for my research, in neat academic language."
        ),
    },
    {
        "id": "hubungan-variabel",
        "name": "Hubungan Antar Variabel (Bab 3)",
        "name_en": "Relationships Between Variables (Chapter 3)",
        "category": "Bab 3",
        "tool": "ChatGPT / Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "variabel_x", "label": "Variabel X", "label_en": "Variable X"},
            {"key": "variabel_y", "label": "Variabel Y", "label_en": "Variable Y"},
            {"key": "variabel_z", "label": "Variabel Z (bila ada)", "label_en": "Variable Z (if any)"},
        ],
        "template": (
            "Saya sedang menulis Bab 3 skripsi berjudul {judul}. Variabel penelitian saya: "
            "variabel X = {variabel_x}, variabel Y = {variabel_y}, variabel Z = "
            "{variabel_z} (bila ada). Tolong buat paragraf yang menjelaskan hubungan antar "
            "variabel ini berdasarkan teori yang relevan. Uraikan secara runtut, mulai dari "
            "hubungan X ke Y, lalu Z bila ada. Jelaskan mengapa hubungan ini penting untuk "
            "diteliti, dan dukung dengan minimal 3 referensi dari penelitian terdahulu "
            "(format APA 7th)."
        ),
        "template_en": (
            "I am writing Chapter 3 of a thesis titled {judul}. My research variables: "
            "variable X = {variabel_x}, variable Y = {variabel_y}, variable Z = "
            "{variabel_z} (if any). Please write a paragraph explaining the relationships "
            "between these variables based on relevant theory. Lay it out in order, "
            "starting with the X-to-Y relationship, then Z if any. Explain why this "
            "relationship is important to study, and support it with at least 3 references "
            "from prior research (APA 7th format)."
        ),
    },
    {
        "id": "hipotesis",
        "name": "Perkiraan Hipotesis (Bab 3)",
        "name_en": "Hypothesis Drafting (Chapter 3)",
        "category": "Bab 3",
        "tool": "Grok",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "variabel", "label": "Variabel yang diteliti", "label_en": "Variables studied"},
        ],
        "template": (
            "Saya sedang menyusun hipotesis untuk skripsi berjudul {judul}. Variabel yang "
            "saya teliti: {variabel}. Tolong carikan minimal 5 penelitian terdahulu yang "
            "meneliti hubungan serupa. Ringkas temuan utama masing-masing penelitian, lalu "
            "susun hipotesis yang logis dan bisa diuji. Format hasilnya: ringkasan penelitian "
            "terdahulu (penulis, tahun, temuan, relevansi), sintesis hubungan antar penelitian "
            "(pola, konsistensi, atau perdebatan yang ada), dan hipotesis saya (H0, H1, dst) "
            "dalam format yang jelas dan siap dimasukkan ke Bab 3."
        ),
        "template_en": (
            "I am drafting hypotheses for a thesis titled {judul}. The variables I am "
            "studying: {variabel}. Please find at least 5 prior studies that examined "
            "similar relationships. Summarize each study's main findings, then formulate "
            "logical, testable hypotheses. Format the result as: summary of prior research "
            "(author, year, findings, relevance), synthesis of the relationships between "
            "studies (patterns, consistencies, or debates), and my hypotheses (H0, H1, "
            "etc.) in a clear format ready for Chapter 3."
        ),
    },
    {
        "id": "mixed-methods",
        "name": "Analisis Mixed-Methods (Bab 4)",
        "name_en": "Mixed-Methods Analysis (Chapter 4)",
        "category": "Bab 4",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "kuantitatif", "label": "Metode kuantitatif", "label_en": "Quantitative method"},
            {"key": "kualitatif", "label": "Metode kualitatif", "label_en": "Qualitative method"},
        ],
        "template": (
            "Saya sedang menganalisis data penelitian mixed method untuk skripsi berjudul "
            "{judul}. Metode kuantitatif saya: {kuantitatif}. Metode kualitatif saya: "
            "{kualitatif}. Saya akan melampirkan file data mentah saya. Tolong analisis "
            "dengan langkah: (1) Analisis kuantitatif: bersihkan data dan jelaskan penanganan "
            "missing value, lakukan uji statistik yang sesuai, sajikan hasil dalam tabel "
            "beserta interpretasi (p-value, signifikansi, effect size), dan buat visualisasi "
            "sederhana bila relevan. (2) Analisis kualitatif: lakukan coding tematik, sajikan "
            "tema utama beserta kutipan perwakilan responden, dan interpretasikan maknanya. "
            "(3) Integrasi: gabungkan kedua hasil, tunjukkan apakah keduanya saling "
            "mendukung, melengkapi, atau bertentangan, dan buat kesimpulan sementara yang "
            "menjawab rumusan masalah. Gunakan bahasa akademik yang jelas dan sistematis, "
            "dengan format akhir yang siap dimasukkan ke Bab 4."
        ),
        "template_en": (
            "I am analyzing mixed-method research data for a thesis titled {judul}. My "
            "quantitative method: {kuantitatif}. My qualitative method: {kualitatif}. I "
            "will attach my raw data files. Please analyze with these steps: (1) "
            "Quantitative analysis: clean the data and explain how missing values are "
            "handled, run the appropriate statistical tests, present the results in tables "
            "with interpretation (p-value, significance, effect size), and make simple "
            "visualizations where relevant. (2) Qualitative analysis: do thematic coding, "
            "present the main themes with representative respondent quotes, and interpret "
            "their meaning. (3) Integration: combine both results, show whether they "
            "support, complement, or contradict each other, and draw a preliminary "
            "conclusion that answers the problem statement. Use clear, systematic academic "
            "language, with a final format ready for Chapter 4."
        ),
    },
    {
        "id": "saran",
        "name": "Saran Penelitian (Bab 5)",
        "name_en": "Research Suggestions (Chapter 5)",
        "category": "Bab 5",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "hasil", "label": "Ringkasan hasil penelitian", "label_en": "Summary of findings"},
        ],
        "template": (
            "Saya sedang menyusun Bab 5 skripsi berjudul {judul}. Berdasarkan hasil "
            "penelitian saya berikut: {hasil}, tolong buatkan saran penelitian yang "
            "konstruktif untuk tiga pihak: (1) praktisi atau industri, (2) akademisi, dan "
            "(3) peneliti berikutnya. Tulis dengan bahasa akademik, masing-masing satu "
            "paragraf, dan pastikan setiap saran bisa diterapkan dan relevan dengan temuan "
            "penelitian saya."
        ),
        "template_en": (
            "I am drafting Chapter 5 of a thesis titled {judul}. Based on my findings "
            "below: {hasil}, please write constructive research suggestions for three "
            "audiences: (1) practitioners or industry, (2) academics, and (3) future "
            "researchers. Write in academic language, one paragraph each, and make sure "
            "every suggestion is actionable and relevant to my findings."
        ),
    },
    {
        "id": "keterbatasan",
        "name": "Keterbatasan + Peluang Penelitian (Bab 5)",
        "name_en": "Limitations + Future Research (Chapter 5)",
        "category": "Bab 5",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "metode", "label": "Metode penelitian", "label_en": "Research method"},
            {"key": "data", "label": "Ringkasan data", "label_en": "Data summary"},
        ],
        "template": (
            "Saya sedang menulis Bab 5 skripsi berjudul {judul}. Metode penelitian saya: "
            "{metode}, dengan data: {data}. Tolong buatkan bagian keterbatasan penelitian "
            "yang ditulis secara elegan dan profesional, tanpa melemahkan hasil penelitian, "
            "lalu lanjutkan dengan peluang penelitian lanjutan. Berikan 3-5 ide penelitian "
            "berikutnya yang relevan, misalnya metode baru, populasi berbeda, atau variabel "
            "tambahan, dan jelaskan mengapa setiap ide penting untuk dikaji."
        ),
        "template_en": (
            "I am writing Chapter 5 of a thesis titled {judul}. My research method: "
            "{metode}, with data: {data}. Please write a limitations section that is "
            "elegant and professional, without weakening the findings, then continue with "
            "opportunities for future research. Give 3-5 ideas for follow-up studies, such "
            "as a new method, a different population, or additional variables, and explain "
            "why each idea matters to study."
        ),
    },
    {
        "id": "review-draf",
        "name": "Review Draf Skripsi (Persiapan Sidang)",
        "name_en": "Thesis Draft Review (Defense Prep)",
        "category": "Sidang",
        "tool": "Claude / Manus",
        "fields": [],
        "template": (
            "Saya akan melampirkan file skripsi saya (PDF/DOC). Tolong baca dan analisis "
            "seluruh isinya, dan berperan sebagai dosen pembimbing sekaligus dosen penguji "
            "yang objektif dan kritis. Beri masukan tentang bagian yang masih lemah, "
            "berpotensi jadi revisi, atau bisa memicu pertanyaan saat seminar dan sidang. "
            "Jelaskan secara spesifik letak masalahnya (bab atau subbab), alasan bagian itu "
            "dinilai kurang kuat, dan aspek apa yang sebaiknya diperdalam, tanpa langsung "
            "menuliskan revisinya. Sebutkan juga kekuatan skripsi saya, dari argumentasi, "
            "teori, metodologi, analisis, sampai kebaruan penelitian. Terakhir, evaluasi "
            "aspek teknis penulisan: sistematika, alur antarparagraf, konsistensi istilah, "
            "kualitas sitasi dan daftar pustaka, format tabel atau gambar, serta potensi "
            "kesalahan akademik lainnya. Sajikan evaluasi dalam kategori yang jelas, "
            "diurutkan berdasarkan prioritas (tinggi, sedang, rendah), agar saya tahu "
            "bagian mana yang harus diperbaiki dulu."
        ),
        "template_en": (
            "I will attach my thesis file (PDF/DOC). Please read and analyze all of it, "
            "and act as an objective, critical supervisor and examiner. Give feedback on "
            "the parts that are still weak, could trigger revisions, or could prompt "
            "questions during the seminar and defense. Explain specifically where the "
            "problem is (chapter or subchapter), why that part is considered weak, and what "
            "should be deepened, without writing the revision itself. Also mention my "
            "thesis's strengths, from argumentation, theory, methodology, analysis, to "
            "research novelty. Finally, evaluate the technical writing: structure, flow "
            "between paragraphs, term consistency, citation and bibliography quality, table "
            "or figure formatting, and other potential academic errors. Present the "
            "evaluation in clear categories, ordered by priority (high, medium, low), so "
            "I know which part to fix first."
        ),
    },
    {
        "id": "ppt",
        "name": "Skripsi Menjadi PowerPoint",
        "name_en": "Thesis to PowerPoint",
        "category": "Sidang",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "jumlah_slide", "label": "Jumlah slide", "label_en": "Number of slides"},
        ],
        "template": (
            "Saya ingin mengubah skripsi saya berjudul {judul} menjadi slide presentasi "
            "PowerPoint. Saya akan melampirkan file skripsinya. Tolong rangkum setiap bab "
            "menjadi slide dengan judul yang singkat dan menarik. Isi tiap slide berupa "
            "poin-poin penting (maksimal 5 poin per slide), ditambah 1-2 kalimat penjelas "
            "untuk setiap slide agar saya tahu apa yang harus diucapkan. Ikuti struktur "
            "presentasi skripsi: latar belakang, rumusan masalah, tujuan, tinjauan pustaka, "
            "metode, hasil, pembahasan, kesimpulan, dan saran. Bila perlu, rekomendasikan "
            "grafik, tabel, atau diagram untuk memperjelas. Hasil akhirnya adalah presentasi "
            "sebanyak {jumlah_slide} slide yang siap dipakai tanpa banyak edit."
        ),
        "template_en": (
            "I want to turn my thesis titled {judul} into a PowerPoint presentation. I "
            "will attach the thesis file. Please summarize each chapter into slides with "
            "short, engaging titles. Each slide's content should be key points (at most 5 "
            "points per slide), plus 1-2 explanatory sentences per slide so I know what to "
            "say. Follow the thesis presentation structure: background, problem statement, "
            "objectives, literature review, method, results, discussion, conclusions, and "
            "suggestions. Where needed, recommend charts, tables, or diagrams for clarity. "
            "The final result is a presentation of {jumlah_slide} slides ready to use with "
            "little editing."
        ),
    },
    {
        "id": "cue-card",
        "name": "Cue Card Presentasi",
        "name_en": "Presentation Cue Cards",
        "category": "Sidang",
        "tool": "ChatGPT",
        "fields": [],
        "template": (
            "Tolong buatkan cue card singkat dan padat untuk membantu saya saat presentasi "
            "skripsi. Bagi per slide sesuai urutan PPT skripsi saya. Tulis poin-poin atau "
            "kalimat kunci yang harus saya ucapkan, dengan bahasa lisan yang natural tapi "
            "tetap profesional. Jangan terlalu panjang, cukup 2-3 kalimat per slide supaya "
            "mudah dihafalkan. Tambahkan tips intonasi atau gestur (misalnya: senyum di awal, "
            "lihat audiens saat menyebut hasil utama). Pastikan cue card ini membuat saya "
            "percaya diri, tidak terdengar kaku, dan membantu menjawab kemungkinan pertanyaan "
            "dari penguji."
        ),
        "template_en": (
            "Please make short, compact cue cards to help me during my thesis "
            "presentation. Split them per slide following my thesis PPT order. Write the "
            "key points or sentences I must say, in natural spoken language that stays "
            "professional. Keep it short, just 2-3 sentences per slide so it is easy to "
            "memorize. Add tips on intonation or gestures (for example: smile at the start, "
            "look at the audience when stating the main result). Make sure these cue cards "
            "make me confident, not stiff, and help me answer possible questions from the "
            "examiners."
        ),
    },
    {
        "id": "blog",
        "name": "Skripsi Menjadi Artikel Blog",
        "name_en": "Thesis to Blog Article",
        "category": "Publikasi",
        "tool": "ChatGPT",
        "fields": [
            {"key": "judul", "label": "Judul penelitian", "label_en": "Research title"},
            {"key": "platform", "label": "Platform / blog / media", "label_en": "Platform / blog / media"},
            {"key": "kata", "label": "Panjang artikel (kata)", "label_en": "Article length (words)"},
        ],
        "template": (
            "Saya ingin mengubah skripsi saya berjudul {judul} menjadi artikel pendek yang "
            "siap dipublikasikan di {platform}. Saya akan melampirkan file skripsinya. "
            "Tolong ambil intisarinya lalu tulis ulang dengan bahasa yang santai, mudah "
            "dipahami pembaca awam, dan tetap menarik. Panjang artikel sekitar {kata} kata. "
            "Susun dengan struktur yang runtut: mulai dari pembuka yang menarik perhatian "
            "(fakta menarik, pertanyaan, atau fenomena terkini), lalu paparkan masalah yang "
            "saya teliti dan relevansinya, jelaskan metode dan temuan utama secara singkat "
            "tanpa terlalu banyak jargon, dan tutup dengan manfaat praktis penelitian ini "
            "bagi pembaca. Bila perlu, tambahkan statistik, contoh kasus, atau call-to-action, "
            "dan pastikan artikel mencantumkan kredit ke penelitian saya agar bisa dipakai "
            "sebagai portofolio."
        ),
        "template_en": (
            "I want to turn my thesis titled {judul} into a short article ready to publish "
            "on {platform}. I will attach the thesis file. Please take its essence and "
            "rewrite it in relaxed language that is easy for lay readers to understand, and "
            "still engaging. The article should be about {kata} words long. Structure it in "
            "order: start with an attention-grabbing opening (an interesting fact, a "
            "question, or a current phenomenon), then present the problem I studied and its "
            "relevance, briefly explain the method and main findings without too much "
            "jargon, and close with the practical benefit of this research for readers. "
            "Where needed, add statistics, case examples, or a call-to-action, and make "
            "sure the article credits my research so it can serve as a portfolio."
        ),
    },
    {
        "id": "jurnal",
        "name": "Skripsi Menjadi Artikel Jurnal",
        "name_en": "Thesis to Journal Article",
        "category": "Publikasi",
        "tool": "ChatGPT",
        "fields": [
            {"key": "bagian", "label": "Bagian skripsi (mis. Pendahuluan/Bab 1)", "label_en": "Thesis section (e.g. Introduction/Chapter 1)"},
            {"key": "jumlah", "label": "Jumlah paragraf/kata", "label_en": "Number of paragraphs/words"},
        ],
        "template": (
            "Saya ingin memublikasikan jurnal berdasarkan skripsi saya. Ini bagian yang "
            "perlu dirangkum menjadi paragraf yang lebih singkat untuk jurnal saya: {bagian}. "
            "Buatkan maksimal sebanyak {jumlah} paragraf atau kata. Pertahankan sitasinya "
            "dan jangan membuang inti tiap paragraf. Gunakan bahasa yang humanis dan tidak "
            "terkesan robotik. Hindari kata yang berulang dan struktur kalimat yang generik, "
            "variasikan panjang kalimat, dan hindari em-dash dan titik koma. Berikut paragraf "
            "yang perlu dipersingkat: [tempel paragraf kamu di sini, satu bagian saja]."
        ),
        "template_en": (
            "I want to publish a journal article based on my thesis. This is the section "
            "that needs to be condensed into shorter paragraphs for my journal: {bagian}. "
            "Make at most {jumlah} paragraphs or words. Keep the citations and do not drop "
            "the core of each paragraph. Use human, non-robotic language. Avoid repeated "
            "words and generic sentence structures, vary sentence length, and avoid "
            "em-dashes and semicolons. Here is the paragraph to shorten: [paste your "
            "paragraph here, one section only]."
        ),
    },
]


def list_prompts(category: str | None = None):
    """All thesis prompts, optionally filtered by category."""
    if category is None:
        return list(PROMPTS)
    return [p for p in PROMPTS if p["category"].lower() == category.lower()]


def get_prompt(prompt_id: str):
    """One prompt by id, or None when unknown."""
    for p in PROMPTS:
        if p["id"] == prompt_id:
            return p
    return None


def fill_prompt(prompt_id: str, values: dict, lang: str = "id") -> str:
    """Fill a prompt template with the student's own values.

    `lang` picks the template language ("id" or "en"); English falls
    back to the Indonesian template when a prompt has no English one.
    Raises KeyError for an unknown prompt id, ValueError naming any
    placeholder left empty. Never invents values: a missing field is
    an error, not a guess.
    """
    prompt = get_prompt(prompt_id)
    if prompt is None:
        raise KeyError(f"unknown prompt: {prompt_id}")
    missing = [f["key"] for f in prompt["fields"]
               if f["key"] not in values or values[f["key"]] == ""]
    if missing:
        raise ValueError(f"missing values for: {', '.join(missing)}")
    template = prompt["template"]
    if lang == "en" and prompt.get("template_en"):
        template = prompt["template_en"]
    return template.format(**values)


def prompts_main(argv=None, *, version=None) -> int:
    p = argparse.ArgumentParser(
        description="Thesis prompts: ready-made prompts for each thesis chapter.")
    p.add_argument("prompt_id", nargs="?", help="prompt id (see --list)")
    p.add_argument("--list", action="store_true", help="list all prompts and exit")
    p.add_argument("--category", help="only list prompts from this category, e.g. 'Bab 3'")
    p.add_argument("--lang", choices=["id", "en"], default="id",
                   help="template language (default: id)")
    p.add_argument("--set", dest="set_values", action="append", default=[],
                   help="fill a placeholder: --set judul='...' (repeatable)")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {version or __version__}")
    args = p.parse_args(argv)

    if args.list or not args.prompt_id:
        for pr in list_prompts(category=args.category):
            name = pr["name_en"] if args.lang == "en" else pr["name"]
            print(f"{pr['id']} — {name} ({pr['category']}, {pr['tool']})")
        return 0

    prompt = get_prompt(args.prompt_id)
    if prompt is None:
        p.error(f"unknown prompt: {args.prompt_id} (see --list)")

    if not args.set_values:
        template = prompt["template"]
        if args.lang == "en" and prompt.get("template_en"):
            template = prompt["template_en"]
        print(template)
        return 0

    values = {}
    for item in args.set_values:
        if "=" not in item:
            p.error(f"--set needs key=value, got: {item}")
        key, value = item.split("=", 1)
        values[key.strip()] = value
    try:
        sys.stdout.write(fill_prompt(args.prompt_id, values, lang=args.lang) + "\n")
    except ValueError as e:
        p.error(str(e))
    return 0


# ======================================================================
# Interactive menu CLI
# ======================================================================
DEFAULT_REFS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "demos", "citation-weaver", "references.json",
)

STRINGS = {
    "id": {
        "banner": "Academic Tools",
        "motto": "Satu file. Semua alat. Tanpa referensi palsu.",
        "tagline": "Jargon Buster  ·  Citation Weaver  ·  Prompt Skripsi",
        "banner_hint": "id  ·  ketik angka, Enter untuk memilih",
        "menu_title": "Daftar isi:",
        "jargon": "Jargon Buster — terjemahkan istilah akademik",
        "cite": "Citation Weaver — sisipkan sitasi ke naskah",
        "prompts": "Prompt Skripsi — template prompt untuk tiap bab",
        "analyze": "Analisis Kualitas — cek jargon, sitasi, dan DOI sekaligus",
        "humanize": "Humanize — saran rewrite gaya (sebelum/sesudah)",
        "library": "Pustaka — riwayat & bibliografi",
        "detect": "Deteksi AI — cek apakah teks mirip tulisan AI",
        "save_analysis": "Simpan hasil ini ke pustaka? (y = ya, kosong = tidak)",
        "saved_analysis": "Tersimpan di pustaka",
        "history": "Lihat riwayat analisis",
        "detail": "Lihat satu analisis",
        "search_refs": "Cari referensi",
        "import_refs": "Impor bibliografi dari JSON",
        "export_refs": "Ekspor bibliografi ke JSON",
        "duplicates": "Cek duplikasi",
        "stats": "Statistik pustaka",
        "analysis_id": "Nomor analisis (#)",
        "analysis_missing": "Tidak ada analisis",
        "search_query": "Kata kunci (judul/penulis/DOI)",
        "imported": "Diimpor",
        "added_count": "ditambahkan",
        "updated_count": "diperbarui",
        "exported": "Diekspor",
        "list_prompts": "Lihat daftar prompt",
        "fill_prompt": "Isi prompt",
        "pick_prompt": "Pilih prompt:",
        "lang": "Ganti bahasa (id/en)",
        "exit": "Keluar",
        "back": "Kembali",
        "choice": "Pilihanmu",
        "invalid": "Pilihan tidak dikenal, coba lagi.",
        "goodbye": "Sampai jumpa!",
        "type_text": "Ketik teks (baris kosong = selesai):",
        "read_file": "Baca dari file",
        "read_folder": "Baca folder (.txt/.md)",
        "file_path": "Path file",
        "file_missing": "File tidak ditemukan:",
        "folder_path": "Path folder",
        "folder_missing": "Folder tidak ditemukan:",
        "field": "Bidang (kosong = semua bidang)",
        "format": "Format output: 1 = Markdown, 2 = CSV",
        "list_terms": "Lihat kamus",
        "add_terms": "Tambah istilah dari file JSON",
        "json_path": "Path file JSON",
        "added": "Istilah ditambahkan:",
        "refs": "File bibliografi JSON (kosong = contoh bawaan)",
        "refs_missing": "File bibliografi tidak ditemukan:",
        "pick_style": "Pilih gaya sitasi:",
        "pick_major": "Pilih jurusan (rekomendasi gaya otomatis):",
        "by_major": "Pilih dari jurusan",
        "out_lang": "Bahasa output: 1 = Indonesia, 2 = English",
        "list_styles": "Lihat gaya sitasi",
        "list_majors": "Lihat jurusan",
        "lookup": "Cari referensi online (DOI/judul)",
        "lookup_query": "DOI atau judul",
        "lookup_key": "Kunci bibliografi (kosong = otomatis)",
        "lookup_save": "Simpan ke file (kosong = jangan simpan)",
        "lookup_saved": "Tersimpan sebagai",
        "lookup_failed": "Pencarian gagal:",
        "bibtex": "Export bibliografi ke BibTeX (.bib)",
        "bibtex_out": "Simpan ke file .bib (kosong = tampilkan saja)",
        "bibtex_saved": "BibTeX tersimpan:",
        "ris": "Export bibliografi ke RIS (.ris)",
        "ris_out": "Simpan ke file .ris (kosong = tampilkan saja)",
        "ris_saved": "RIS tersimpan:",
        "audit": "Audit sitasi (cek rujukan hilang/tak terpakai)",
        "audit_check_links": "Cek juga DOI/link masih hidup? (y = ya, kosong = tidak)",
        "verify": "Verifikasi DOI referensi (Crossref/OpenAlex)",
        "save_fixed": "Simpan hasil perbaikan ke file (kosong = tidak)",
        "saved_fixed": "Tersimpan",
        "applied": "diterapkan",
        "skipped": "dilewati",
        "press_enter": "Tekan Enter untuk kembali...",
        "result": "Hasil:",
    },
    "en": {
        "banner": "Academic Tools",
        "motto": "One file. Every tool. No invented references.",
        "tagline": "Jargon Buster  ·  Citation Weaver  ·  Thesis Prompts",
        "banner_hint": "en  ·  type a number, Enter to choose",
        "menu_title": "Contents:",
        "jargon": "Jargon Buster — translate academic jargon",
        "cite": "Citation Weaver — weave citations into text",
        "prompts": "Thesis Prompts — ready-made prompts for each chapter",
        "analyze": "Quality Check — jargon, citations, and DOIs in one pass",
        "humanize": "Humanize — style rewrite suggestions (before/after)",
        "library": "Library — history & bibliography",
        "detect": "AI Detector — check whether text reads like AI writing",
        "save_analysis": "Save this run to the library? (y = yes, empty = no)",
        "saved_analysis": "Saved to the library",
        "history": "List past analyses",
        "detail": "Show one analysis",
        "search_refs": "Search references",
        "import_refs": "Import a bibliography JSON",
        "export_refs": "Export the bibliography to JSON",
        "duplicates": "Check duplication",
        "stats": "Library statistics",
        "analysis_id": "Analysis number (#)",
        "analysis_missing": "No such analysis",
        "search_query": "Keyword (title/author/DOI)",
        "imported": "Imported",
        "added_count": "added",
        "updated_count": "updated",
        "exported": "Exported",
        "list_prompts": "List prompts",
        "fill_prompt": "Fill a prompt",
        "pick_prompt": "Pick a prompt:",
        "lang": "Switch language (id/en)",
        "exit": "Exit",
        "back": "Back",
        "choice": "Your choice",
        "invalid": "Unknown choice, try again.",
        "goodbye": "Goodbye!",
        "type_text": "Type text (empty line = done):",
        "read_file": "Read from file",
        "read_folder": "Read a folder (.txt/.md)",
        "file_path": "File path",
        "file_missing": "File not found:",
        "folder_path": "Folder path",
        "folder_missing": "Folder not found:",
        "field": "Field (empty = all fields)",
        "format": "Output format: 1 = Markdown, 2 = CSV",
        "list_terms": "List dictionary terms",
        "add_terms": "Add terms from a JSON file",
        "json_path": "JSON file path",
        "added": "Terms added:",
        "refs": "Bibliography JSON file (empty = bundled sample)",
        "refs_missing": "Bibliography file not found:",
        "pick_style": "Pick a citation style:",
        "pick_major": "Pick a major (recommended style is automatic):",
        "by_major": "Pick from major",
        "out_lang": "Output language: 1 = Indonesian, 2 = English",
        "list_styles": "List citation styles",
        "list_majors": "List majors",
        "lookup": "Look up a reference online (DOI/title)",
        "lookup_query": "DOI or title",
        "lookup_key": "Bibliography key (empty = automatic)",
        "lookup_save": "Save to file (empty = don't save)",
        "lookup_saved": "Saved as",
        "lookup_failed": "Lookup failed:",
        "bibtex": "Export bibliography to BibTeX (.bib)",
        "bibtex_out": "Save to .bib file (empty = print only)",
        "bibtex_saved": "BibTeX saved:",
        "ris": "Export bibliography to RIS (.ris)",
        "ris_out": "Save to .ris file (empty = print only)",
        "ris_saved": "RIS saved:",
        "audit": "Audit citations (check missing/unused references)",
        "audit_check_links": "Also check DOI/links are still alive? (y = yes, empty = no)",
        "verify": "Verify reference DOIs (Crossref/OpenAlex)",
        "save_fixed": "Save the fixed text to a file (empty = skip)",
        "saved_fixed": "Saved",
        "applied": "applied",
        "skipped": "skipped",
        "press_enter": "Press Enter to go back...",
        "result": "Result:",
    },
}


BANNER_MIN_WIDTH = 60


def _unicode_ok() -> bool:
    """True when stdout can encode the box-drawing and block glyphs.

    UTF-8 and cp437/cp850 can; cp1252 cannot. A StringIO (tests,
    pipes) has no encoding, which means plain str: treat it as capable.
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "╭╮╰╯─│·█░".encode(enc)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _colors_enabled() -> bool:
    """Color only on a real terminal, unless forced off or on.

    NO_COLOR disables, ACADEMIC_COLOR=1 forces (used to preview the
    colored UI when stdout is piped), TERM=dumb disables.
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("ACADEMIC_COLOR") == "1":
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def _paint(text: str, code: str) -> str:
    if not _colors_enabled():
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def _bold(text: str) -> str:
    return _paint(text, "1")


def _green(text: str) -> str:
    return _paint(text, "32")


def _bar(value: float, maximum: float, width: int = 20) -> str:
    """A text bar: filled blocks for value/maximum, empty for the rest."""
    filled = max(0, min(width, round(value / maximum * width)))
    if _unicode_ok():
        return "█" * filled + "░" * (width - filled)
    return "#" * filled + "-" * (width - filled)


def _menu_line(number: str, name: str, desc: str = "",
               desc_col: int = 64) -> str:
    """One menu row with dot leaders: '  1  Jargon Buster ... desc'."""
    left = f"  {number}  {name} "
    if not desc:
        return left.rstrip()
    dots = max(2, desc_col - len(left) - len(desc))
    return left + "." * dots + " " + desc


def _section_header(name: str, width: int = 58) -> str:
    """A rule with the section name embedded: '── Jargon Buster ──...'."""
    if _unicode_ok():
        head = f"── {name} "
        return _bold(head + "─" * max(2, width - len(head)))
    head = f"-- {name.replace(' — ', ' - ')} "
    return head + "-" * max(2, width - len(head))


def format_banner(lang: str) -> str:
    """Cover-page banner for the interactive menu; width follows the text.

    A rounded box when stdout can encode it, plain ASCII otherwise
    (old Windows consoles). Colors only on a real terminal.
    """
    t = STRINGS[lang]
    title = t["banner"]
    version = f"v{__version__}"
    motto = t["motto"]
    tagline = t["tagline"]
    hint = t["banner_hint"]
    width = max(BANNER_MIN_WIDTH, len(title) + len(version) + 2,
                len(motto) + 2, len(tagline) + 2, len(hint) + 2)
    heading = title + " " * (width - len(title) - len(version)) + version
    if _unicode_ok():
        top = "╭" + "─" * (width + 2) + "╮"
        bot = "╰" + "─" * (width + 2) + "╯"
        rule = _green("─" * width)
        edge = "│"
    else:
        top = "+" + "=" * (width + 2) + "+"
        bot = top
        rule = "-" * width
        edge = "|"
    return "\n".join([
        f"  {top}",
        f"  {edge} {_bold(heading)} {edge}",
        f"  {edge} {rule} {edge}",
        f"  {edge} {motto.ljust(width)} {edge}",
        f"  {edge} {tagline.ljust(width)} {edge}",
        f"  {edge} {hint.ljust(width)} {edge}",
        f"  {bot}",
    ])


class CLI:
    """Interactive menu session. `lang` is the UI language (id/en)."""

    def __init__(self, lang: str = "id"):
        self.lang = lang if lang in STRINGS else "id"

    @property
    def t(self):
        return STRINGS[self.lang]

    def ask(self, prompt: str, default: str = "") -> str:
        """One line of input; returns default on empty line, '' on EOF."""
        try:
            answer = input(f"{prompt} " if not default else f"{prompt} [{default}] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return ""
        return answer.strip() or default

    def ask_choice(self, prompt: str, count: int) -> int | None:
        """Ask for a number 0..count.

        Returns None on empty line/EOF (means: back/exit), -1 on an
        invalid number (caller should re-prompt, not quit).
        """
        raw = self.ask(f"{prompt} (0-{count})")
        if not raw:
            return None
        try:
            n = int(raw)
        except ValueError:
            print(self.t["invalid"])
            return -1
        if 0 <= n <= count:
            return n
        print(self.t["invalid"])
        return -1

    def pause(self):
        try:
            input(f"\n{self.t['press_enter']}")
        except (EOFError, KeyboardInterrupt):
            print()

    def read_text(self, folder: bool = False) -> str | tuple | None:
        """Choice: type multi-line text, read from a file (or a folder).

        With folder=True a third choice appears; picking it returns
        ("folder", path) instead of text.
        """
        print(f"  1. {self.t['type_text'].split(' (')[0]}")
        print(f"  2. {self.t['read_file']}")
        if folder:
            print(f"  3. {self.t['read_folder']}")
        print(f"  0. {self.t['back']}")
        choice = self.ask_choice(self.t["choice"], 3 if folder else 2)
        if choice == 1:
            print(self.t["type_text"])
            lines = []
            try:
                while True:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line)
            except (EOFError, KeyboardInterrupt):
                print()
            return "\n".join(lines)
        if choice == 2:
            path = self.ask(self.t["file_path"])
            if not path:
                return None
            if not os.path.isfile(path):
                print(f"{self.t['file_missing']} {path}")
                return None
            with open(path, encoding="utf-8") as f:
                return f.read()
        if choice == 3 and folder:
            path = self.ask(self.t["folder_path"])
            if not path:
                return None
            if not os.path.isdir(path):
                print(f"{self.t['folder_missing']} {path}")
                return None
            return ("folder", path)
        return None

    # -- main menu ------------------------------------------------------

    def run(self) -> int:
        while True:
            print()
            print(format_banner(self.lang))
            print(self.t["menu_title"])
            for number, key in (("1", "jargon"), ("2", "cite"),
                                ("3", "prompts"), ("4", "analyze"),
                                ("5", "humanize"), ("6", "library"),
                                ("7", "detect")):
                name, _, desc = self.t[key].partition(" — ")
                print(_menu_line(number, name, desc))
            print(_menu_line("8", self.t["lang"]))
            print(_menu_line("0", self.t["exit"]))
            choice = self.ask_choice(self.t["choice"], 8)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_menu()
            elif choice == 2:
                self.cite_menu()
            elif choice == 3:
                self.prompts_menu()
            elif choice == 4:
                self.analyze_menu()
            elif choice == 5:
                self.humanize_menu()
            elif choice == 6:
                self.library_menu()
            elif choice == 7:
                self.detect_menu()
            elif choice == 8:
                self.lang = "en" if self.lang == "id" else "id"
            elif choice == 0 or choice is None:
                print(self.t["goodbye"])
                return 0

    # -- AI Detector --------------------------------------------------

    def detect_menu(self):
        while True:
            print(f"\n{_section_header(self.t['detect'].partition(' — ')[0])}")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 1)
            if choice == -1:
                continue
            if choice == 1:
                text = self.read_text()
                if not text:
                    continue
                try:
                    result = detect_ai(text, lang=self.lang)
                except ValueError as e:
                    print(str(e))
                    self.pause()
                    continue
                print(f"\n{format_detect(result, lang=self.lang)}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    # -- Jargon Buster --------------------------------------------------

    def jargon_menu(self):
        while True:
            print(f"\n{_section_header(self.t['jargon'])}")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_terms']}")
            print(f"3. {self.t['add_terms']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 3)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_annotate()
            elif choice == 2:
                field = self.ask(self.t["field"])
                for item in list_terms(field or None):
                    print(f"- {item['term']} ({item['field']}): {item['translation']}")
                self.pause()
            elif choice == 3:
                path = self.ask(self.t["json_path"])
                if path and os.path.isfile(path):
                    added = update_dictionary(path)
                    print(f"{self.t['added']} {', '.join(added) if added else '-'}")
                elif path:
                    print(f"{self.t['file_missing']} {path}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def jargon_annotate(self):
        text = self.read_text()
        if not text:
            return
        field = self.ask(self.t["field"])
        print(f"1. Markdown\n2. CSV")
        fmt = self.ask_choice(self.t["format"], 2)
        if fmt == 2:
            out = to_csv(text, field or None)
        else:
            out = to_annotated_markdown(text, field or None)
        print(f"\n{self.t['result']}\n{out}")
        self.pause()

    # -- Citation Weaver ------------------------------------------------

    def cite_menu(self):
        while True:
            print(f"\n{_section_header(self.t['cite'])}")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_styles']}")
            print(f"3. {self.t['list_majors']}")
            print(f"4. {self.t['lookup']}")
            print(f"5. {self.t['bibtex']}")
            print(f"6. {self.t['audit']}")
            print(f"7. {self.t['verify']}")
            print(f"8. {self.t['ris']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 8)
            if choice == -1:
                continue
            if choice == 1:
                self.cite_weave()
            elif choice == 2:
                for i, s in enumerate(STYLES, 1):
                    print(f"  {i}. {s}")
                self.pause()
            elif choice == 3:
                for i, d in enumerate(DISCIPLINES, 1):
                    print(f"  {i}. {d['id']} / {d['en']} -> {d['style']}")
                self.pause()
            elif choice == 4:
                self.cite_lookup()
            elif choice == 5:
                self.cite_export_bibtex()
            elif choice == 6:
                self.cite_audit()
            elif choice == 7:
                self.cite_verify()
            elif choice == 8:
                self.cite_export_ris()
            elif choice == 0 or choice is None:
                return

    def cite_audit(self):
        text = self.read_text()
        if not text:
            return
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        refs = load_references(refs_path)
        result = audit_citations(text, refs)
        check = self.ask(self.t["audit_check_links"])
        links = None
        if check.strip().lower() in ("y", "ya", "yes", "1"):
            links = check_reference_links(refs, keys=result["cited"])
        print(f"\n{format_audit(result, lang=self.lang, links=links)}")
        self.pause()

    def cite_verify(self):
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        result = verify_reference_dois(load_references(refs_path))
        print(f"\n{format_verification(result, lang=self.lang)}")
        self.pause()

    def analyze_menu(self):
        got = self.read_text(folder=True)
        if not got:
            return
        if isinstance(got, tuple):
            self.analyze_folder_menu(got[1])
            return
        text = got
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        refs = load_references(refs_path)
        result = analyze_text_quality(text, refs, lang=self.lang)
        print(f"\n{format_analyze(result, lang=self.lang)}")
        save = self.ask(self.t["save_analysis"])
        if save.strip().lower() in ("y", "ya", "yes"):
            analysis_id = save_analysis(text, result, refs)
            print(f"{self.t['saved_analysis']}: #{analysis_id}")
        self.pause()

    def analyze_folder_menu(self, folder: str):
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        refs = load_references(refs_path)
        result = analyze_folder(folder, refs, lang=self.lang)
        print(f"\n{format_folder_result(result, lang=self.lang)}")
        if not result["files"]:
            self.pause()
            return
        save = self.ask(self.t["save_analysis"])
        if save.strip().lower() in ("y", "ya", "yes"):
            saved = 0
            for e in result["files"]:
                if e["result"] is None or e["error"]:
                    continue
                save_analysis(e["text"], e["result"], refs,
                              title=e["file"])
                saved += 1
            print(f"{self.t['saved_analysis']}: {saved} file")
        self.pause()

    def library_menu(self):
        while True:
            print(f"\n{_section_header(self.t['library'])}")
            print(f"1. {self.t['history']}")
            print(f"2. {self.t['detail']}")
            print(f"3. {self.t['search_refs']}")
            print(f"4. {self.t['import_refs']}")
            print(f"5. {self.t['export_refs']}")
            print(f"6. {self.t['duplicates']}")
            print(f"7. {self.t['stats']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 7)
            if choice == -1:
                continue
            if choice == 1:
                print(f"\n{format_history(list_analyses())}")
                self.pause()
            elif choice == 2:
                raw = self.ask(self.t["analysis_id"])
                try:
                    # Audit #7 N-7: int() accepts a leading "+"
                    # ("+1" is id 1) where .isdigit() skipped it.
                    analysis_id = int(raw.strip())
                except ValueError:
                    analysis_id = -1
                if analysis_id >= 1:
                    analysis = get_analysis(analysis_id)
                    if analysis is None:
                        print(f"{self.t['analysis_missing']} {raw}")
                    else:
                        print(f"\n{format_analysis_detail(analysis)}")
                self.pause()
            elif choice == 3:
                query = self.ask(self.t["search_query"])
                if query:
                    print(f"\n{format_references(search_references(query))}")
                self.pause()
            elif choice == 4:
                path = self.ask(self.t["json_path"])
                if path and os.path.isfile(path):
                    counts = import_references(load_references(path))
                    print(f"{self.t['imported']}: "
                          f"{counts['added']} {self.t['added_count']}, "
                          f"{counts['updated']} {self.t['updated_count']}")
                elif path:
                    print(f"{self.t['file_missing']} {path}")
                self.pause()
            elif choice == 5:
                path = self.ask(self.t["json_path"])
                if path:
                    refs = export_references()
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(refs, f, ensure_ascii=False, indent=2)
                    print(f"{self.t['exported']}: {len(refs)} -> {path}")
                self.pause()
            elif choice == 6:
                text = self.read_text()
                if text:
                    try:
                        result = find_duplicates(text)
                    except ValueError as e:
                        print(str(e))
                    else:
                        print(f"\n{format_duplicates(result, lang=self.lang)}")
                self.pause()
            elif choice == 7:
                print(f"\n{format_library_stats(library_stats(), lang=self.lang)}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def humanize_menu(self):
        text = self.read_text()
        if not text:
            return
        result = suggest_style_fixes(text, lang=self.lang)
        print(f"\n{format_suggestions(result, lang=self.lang)}")
        mechanical = [s for s in result["suggestions"]
                      if s["replacement"] is not None]
        if mechanical:
            path = self.ask(self.t["save_fixed"])
            if path:
                full = suggest_style_fixes(text, lang=self.lang,
                                           limit=None)
                fixed = apply_suggestions(text, full)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(fixed["text"])
                print(f"{self.t['saved_fixed']}: {path} "
                      f"({len(fixed['applied'])} {self.t['applied']}, "
                      f"{len(fixed['skipped'])} {self.t['skipped']})")
        self.pause()

    def cite_export_bibtex(self):
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        out = self.ask(self.t["bibtex_out"])
        refs = load_references(refs_path)
        bib = export_bibtex(refs)
        if out:
            with open(out, "w", encoding="utf-8") as f:
                f.write(bib)
            print(f"{self.t['bibtex_saved']} {len(refs)} entries -> {out}")
        else:
            print(f"\n{bib}")
        self.pause()

    def cite_export_ris(self):
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        out = self.ask(self.t["ris_out"])
        refs = load_references(refs_path)
        ris = export_ris(refs)
        if out:
            with open(out, "w", encoding="utf-8") as f:
                f.write(ris)
            print(f"{self.t['ris_saved']} {len(refs)} entries -> {out}")
        else:
            print(f"\n{ris}")
        self.pause()

    def cite_lookup(self):
        query = self.ask(self.t["lookup_query"])
        if not query:
            return
        try:
            ref = lookup_reference(query)
        except LookupError as e:
            print(f"{self.t['lookup_failed']} {e}")
            self.pause()
            return
        print(f"\n{json.dumps(ref, ensure_ascii=False, indent=2)}")
        path = self.ask(self.t["lookup_save"])
        if not path:
            self.pause()
            return
        key = self.ask(self.t["lookup_key"])
        saved = save_reference(ref, path, key=key or None)
        print(f"{self.t['lookup_saved']} [{saved}] ({path})")
        self.pause()

    def pick_style(self) -> str | None:
        print(f"\n{self.t['pick_style']}")
        for i, s in enumerate(STYLES, 1):
            print(f"  {i}. {s}")
        print(f"  {len(STYLES) + 1}. {self.t['by_major']}")
        choice = self.ask_choice(self.t["choice"], len(STYLES) + 1)
        if choice is None or choice == 0:
            return None
        if choice == len(STYLES) + 1:
            return self.pick_style_by_major()
        return STYLES[choice - 1]

    def pick_style_by_major(self) -> str | None:
        print(f"\n{self.t['pick_major']}")
        for i, d in enumerate(DISCIPLINES, 1):
            print(f"  {i}. {d['id']} / {d['en']} -> {d['style']}")
        choice = self.ask_choice(self.t["choice"], len(DISCIPLINES))
        if choice is None or choice == 0:
            return None
        return DISCIPLINES[choice - 1]["style"]

    def cite_weave(self):
        text = self.read_text()
        if not text:
            return
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        style = self.pick_style()
        if not style:
            return
        print("1. Indonesia\n2. English")
        lang_choice = self.ask_choice(self.t["out_lang"], 2)
        lang = "en" if lang_choice == 2 else "id"
        refs = load_references(refs_path)
        out = weave(text, refs, style=style, lang=lang)
        # weave() returns (full output with bibliography, woven text only)
        if isinstance(out, tuple):
            out = out[0]
        print(f"\n{self.t['result']}\n{out}")
        self.pause()

    # -- Thesis Prompts -------------------------------------------------

    def prompts_menu(self):
        while True:
            print(f"\n{_section_header(self.t['prompts'])}")
            print(f"1. {self.t['fill_prompt']}")
            print(f"2. {self.t['list_prompts']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 2)
            if choice == -1:
                continue
            if choice == 1:
                self.prompts_fill()
            elif choice == 2:
                for pr in list_prompts():
                    name = pr["name_en"] if self.lang == "en" else pr["name"]
                    print(f"  {pr['id']} — {name} ({pr['category']}, {pr['tool']})")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def prompts_fill(self):
        prompts = list_prompts()
        print(f"\n{self.t['pick_prompt']}")
        for i, pr in enumerate(prompts, 1):
            name = pr["name_en"] if self.lang == "en" else pr["name"]
            print(f"  {i}. {pr['id']} — {name} ({pr['tool']})")
        choice = self.ask_choice(self.t["choice"], len(prompts))
        if choice is None or choice == 0:
            return
        pr = prompts[choice - 1]
        values = {}
        for f in pr["fields"]:
            label = f["label"] if self.lang == "id" else f["label_en"]
            values[f["key"]] = self.ask(f"{label}:")
        try:
            out = fill_prompt(pr["id"], values, lang=self.lang)
        except ValueError as e:
            print(e)
            return
        print(f"\n{self.t['result']}\n{out}")
        print(f"\n({pr['tool']})")
        self.pause()


# ======================================================================
# Local web UI (serve) — the same six tools in a browser page
# ======================================================================
# Design direction (our own brief, written for this page):
# - A tool page, not a landing page: no hero, the work (paste text,
#   press Analyze) is at the top; every section earns its place.
# - Paper background, ink text, one restrained green accent. No
#   gradients, no decoration without a purpose.
# - System font stack, one type scale, real Indonesian copy, honest
#   labels (a score is a score, not a verdict).
# - Zero external resources: no CDN, no webfonts, no analytics —
#   the page works offline and sends nothing anywhere.
# - Keyboard-accessible tabs and buttons, visible focus outlines.
# The HTML is a raw string so the JavaScript stays verbatim.
WEB_UI_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Academic Tools — Analisis Kualitas</title>
<style>
  /* Token: satu sumber kebenaran. Semua komponen memakai token ini,
     tidak ada warna atau ukuran ad-hoc di luar daftar ini. */
  :root {
    --paper: #fafaf7;
    --card: #ffffff;
    --ink: #1d1d1a;
    --muted: #6b6b64;
    --line: #e2e2da;
    --accent: #206040;
    --accent-soft: #e8f0e9;
    --accent-ink: #ffffff;
    --warn: #8a5a00;
    --bad: #9b2c2c;
    --radius: 6px;
    --radius-lg: 10px;
    --space: 16px;
    --sidebar-w: 248px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 16px;
    line-height: 1.55;
  }
  /* Shell: sidebar navigasi + area kerja. Sidebar hanya berisi lima alat
     yang memang ada (tiap tombol punya tujuan nyata) dan satu catatan
     lokal; tidak ada kartu statistik hiasan atau grafik tanpa pertanyaan. */
  .shell { display: grid; grid-template-columns: var(--sidebar-w) 1fr; min-height: 100vh; }
  .sidebar {
    background: var(--card); border-right: 1px solid var(--line);
    padding: 20px 16px; display: flex; flex-direction: column; gap: 20px;
  }
  .brand h1 { font-size: 20px; margin: 0; letter-spacing: -0.01em; }
  .brand .ver {
    font-size: 12px; font-weight: 600; color: var(--muted);
    border: 1px solid var(--line); border-radius: 999px;
    padding: 2px 8px; margin-left: 8px; vertical-align: middle;
  }
  .brand p { margin: 8px 0 0; color: var(--muted); font-size: 13px; }
  nav.tabs { display: flex; flex-direction: column; gap: 4px; }
  nav.tabs button {
    appearance: none; border: 1px solid transparent; background: none;
    font: inherit; text-align: left; padding: 10px 12px;
    border-radius: var(--radius); cursor: pointer; color: var(--ink);
  }
  nav.tabs button .nav-name { display: block; font-size: 14px; font-weight: 600; }
  nav.tabs button .nav-desc { display: block; font-size: 12px; color: var(--muted); margin-top: 2px; }
  nav.tabs button[aria-selected="true"] {
    background: var(--accent-soft);
    box-shadow: inset 3px 0 0 var(--accent);
  }
  nav.tabs button:focus-visible, button:focus-visible, select:focus-visible,
  textarea:focus-visible, input:focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  .local-note {
    margin-top: auto; padding-top: 16px; border-top: 1px solid var(--line);
    font-size: 13px; color: var(--muted);
  }
  main .content { max-width: 880px; margin: 0 auto; padding: 24px var(--space) 48px; }
  .panel { display: none; }
  .panel.active { display: block; }
  label { display: block; font-size: 14px; font-weight: 600; margin: 0 0 6px; }
  label .hint { font-weight: 400; color: var(--muted); }
  textarea, select, input[type="text"] {
    width: 100%; font: inherit; color: var(--ink);
    border: 1px solid var(--line); border-radius: var(--radius);
    background: var(--card); padding: 10px 12px;
  }
  textarea { min-height: 180px; resize: vertical; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
  .row > div { flex: 1 1 180px; }
  .actions { margin-top: 16px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  button.primary {
    appearance: none; border: 1px solid var(--accent); background: var(--accent);
    color: var(--accent-ink); font: inherit; font-weight: 600;
    padding: 10px 18px; border-radius: var(--radius); cursor: pointer;
  }
  button.primary:disabled { opacity: 0.55; cursor: wait; }
  button.ghost {
    appearance: none; border: 1px solid var(--line); background: var(--card);
    color: var(--ink); font: inherit; padding: 8px 14px;
    border-radius: var(--radius); cursor: pointer;
  }
  details { margin-top: 12px; font-size: 14px; }
  details summary { cursor: pointer; font-weight: 600; }
  details textarea { min-height: 110px; margin-top: 8px; }
  .status { font-size: 14px; color: var(--muted); }
  .error {
    margin-top: 16px; padding: 12px 14px; border: 1px solid var(--bad);
    border-radius: var(--radius); color: var(--bad); background: #fdf6f6;
    display: none; font-size: 14px;
  }
  .error.show { display: block; }
  .result { margin-top: 24px; }
  .card {
    background: var(--card); border: 1px solid var(--line);
    border-radius: var(--radius); padding: 16px; margin-top: 12px;
  }
  .card h2 { font-size: 15px; margin: 0 0 8px; }
  .card h2 .meta { font-weight: 400; color: var(--muted); font-size: 13px; }
  .card ul { margin: 0; padding-left: 20px; }
  .card li { margin: 4px 0; }
  .card li .src { color: var(--muted); font-size: 13px; }
  /* Kartu skor: satu-satunya kartu dengan radius besar — ia hasil utama
     halaman ini. Gauge menjawab "seberapa bagus naskah ini?"; empat baris
     di sampingnya menjawab "komponen mana yang menarik skor ke bawah?". */
  .gauge-card { border-radius: var(--radius-lg); }
  .gauge-card .caption { color: var(--muted); font-size: 14px; margin: 0 0 16px; }
  .gauge-body { display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }
  .gauge-wrap { position: relative; flex: 0 0 132px; width: 132px; height: 132px; }
  .gauge { width: 132px; height: 132px; display: block; }
  .gauge circle { fill: none; stroke-width: 10; }
  .gauge-track { stroke: var(--line); }
  .gauge-arc { stroke-linecap: round; transform: rotate(-90deg); transform-origin: center; }
  .gauge-center {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; text-align: center;
  }
  .gauge-num { font-size: 32px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
  .gauge-of { color: var(--muted); font-size: 13px; }
  .gauge-band { font-size: 12px; font-weight: 600; margin-top: 4px; padding: 0 8px; }
  .parts { flex: 1 1 240px; display: flex; flex-direction: column; gap: 10px; }
  .part-row { display: flex; align-items: center; gap: 10px; }
  .part-label { flex: 0 0 64px; font-size: 14px; font-weight: 600; }
  .part-row .bar { flex: 1; height: 8px; background: var(--line); border-radius: 999px; overflow: hidden; }
  .part-row .bar span { display: block; height: 100%; background: var(--accent); }
  .part-num { font-variant-numeric: tabular-nums; font-size: 13px; color: var(--muted); min-width: 44px; text-align: right; }
  /* Statistik pustaka: tiga ubin dari angka nyata (riwayat tersimpan di
     komputer ini). Tanpa delta, tanpa angka karangan. */
  .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 12px 0 4px; }
  .stat { border: 1px solid var(--line); border-radius: var(--radius); padding: 12px; }
  .stat-num { display: block; font-size: 28px; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
  .stat-label { display: block; font-size: 13px; color: var(--muted); margin-top: 4px; }
  .trend-row { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
  .trend-row .trend-label { flex: 0 0 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .trend-row .bar { flex: 1; height: 10px; background: var(--line); border-radius: 999px; overflow: hidden; }
  .trend-row .bar span { display: block; height: 100%; background: var(--accent); }
  .trend-row .num { font-variant-numeric: tabular-nums; min-width: 28px; text-align: right; }
  .panel h2 { font-size: 15px; margin: 20px 0 8px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--line); font-size: 14px; vertical-align: top; }
  hr { border: none; border-top: 1px solid var(--line); margin: 20px 0; }
  .flag { color: var(--warn); font-weight: 600; }
  pre {
    white-space: pre-wrap; word-wrap: break-word; font: inherit;
    margin: 0; background: var(--card);
  }
  .bib { font-size: 14px; color: var(--ink); }
  @media (max-width: 900px) {
    .shell { display: block; }
    .sidebar { border-right: none; border-bottom: 1px solid var(--line); padding: 16px; gap: 12px; }
    nav.tabs { flex-direction: row; flex-wrap: wrap; gap: 4px; }
    nav.tabs button { flex: 1 1 auto; }
    nav.tabs button .nav-desc { display: none; }
    nav.tabs button[aria-selected="true"] { box-shadow: inset 0 -3px 0 var(--accent); }
    .local-note { margin-top: 0; }
    .stats-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 560px) {
    .gauge-num { font-size: 28px; }
  }
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <div class="brand">
      <h1>Academic Tools <span class="ver">v__ACADEMIC_TOOLS_VERSION__</span></h1>
      <p>Satu file Python untuk tulisan mahasiswa: terjemahkan jargon, sisipkan sitasi, cek kualitas naskah, isi template prompt skripsi, deteksi tulisan AI, dan lihat riwayat di pustaka.</p>
    </div>
    <nav class="tabs" role="tablist" aria-label="Alat">
      <button role="tab" data-tab="analyze" aria-selected="true"><span class="nav-name">Analisis Kualitas</span><span class="nav-desc">Skor naskah dan apa yang diperbaiki</span></button>
      <button role="tab" data-tab="jargon" aria-selected="false"><span class="nav-name">Jargon Buster</span><span class="nav-desc">Istilah akademik, dijelaskan</span></button>
      <button role="tab" data-tab="cite" aria-selected="false"><span class="nav-name">Citation Weaver</span><span class="nav-desc">Sisipkan sitasi ke naskah</span></button>
      <button role="tab" data-tab="prompts" aria-selected="false"><span class="nav-name">Prompt Skripsi</span><span class="nav-desc">Template prompt skripsi</span></button>
      <button role="tab" data-tab="library" aria-selected="false"><span class="nav-name">Pustaka</span><span class="nav-desc">Riwayat analisis dan referensi</span></button>
      <button role="tab" data-tab="detect" aria-selected="false"><span class="nav-name">Deteksi AI</span><span class="nav-desc">Cek apakah teks mirip tulisan AI</span></button>
    </nav>
    <p class="local-note">Berjalan lokal di komputer Anda — halaman ini tidak mengirim data ke mana pun. Skor gaya hanya laporan: baca, lalu sunting sendiri. Referensi yang tidak ada di bibliografi tidak pernah dikarang.</p>
  </aside>
<main>
  <div class="content">

    <section class="panel active" id="panel-analyze" role="tabpanel" aria-label="Analisis Kualitas">
      <label for="analyze-text">Tempel naskah <span class="hint">— satu atau beberapa paragraf, bahasa Indonesia</span></label>
      <textarea id="analyze-text" placeholder="Tempel naskah di sini, misalnya satu paragraf Bab 1 atau abstrak."></textarea>
      <div class="row">
        <div>
          <label for="analyze-refs">Bibliografi</label>
          <select id="analyze-refs">
            <option value="sample">Contoh bawaan (7 referensi)</option>
            <option value="none">Tanpa bibliografi</option>
          </select>
        </div>
        <div>
          <label for="analyze-lang">Bahasa hasil</label>
          <select id="analyze-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
        <div>
          <label>&nbsp;</label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-verify"> Verifikasi DOI <span class="hint">(butuh internet)</span></label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-suggest"> Saran rewrite gaya</label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-duplicates"> Cek duplikasi dengan pustaka <span class="hint">(kalimat yang berulang)</span></label>
          <label style="font-weight:400"><input type="checkbox" id="analyze-save"> Simpan ke pustaka <span class="hint">(riwayat di komputer ini)</span></label>
        </div>
      </div>
      <details>
        <summary>Atau tempel bibliografi JSON sendiri</summary>
        <textarea id="analyze-refs-json" placeholder='{"devlin2019": {"title": "BERT: ...", "year": 2019}}'></textarea>
      </details>
      <div class="actions">
        <button class="primary" id="analyze-btn">Analisis naskah</button>
        <span class="status" id="analyze-status"></span>
      </div>
      <div class="error" id="analyze-error"></div>
      <div class="result" id="analyze-result"></div>
      <hr>
      <h2>Analisis se-folder</h2>
      <p>Pilih folder skripsi — hanya file <code>.txt</code>/<code>.md</code> tingkat atas yang dianalisis, urut nama file. File di subfolder dan file lain dilewati, bukan digagalkan. Bibliografi dan bahasa diambil dari pilihan di atas.</p>
      <div class="row">
        <div>
          <label for="folder-dir">Pilih folder</label>
          <input type="file" id="folder-dir" name="files" webkitdirectory>
        </div>
        <div>
          <label for="folder-files">Atau pilih beberapa file</label>
          <input type="file" id="folder-files" name="files" multiple accept=".txt,.md">
        </div>
        <div>
          <label>&nbsp;</label>
          <label style="font-weight:400"><input type="checkbox" id="folder-verify"> Verifikasi DOI <span class="hint">(butuh internet)</span></label>
          <label style="font-weight:400"><input type="checkbox" id="folder-duplicates"> Cek duplikasi dengan pustaka</label>
          <label style="font-weight:400"><input type="checkbox" id="folder-save"> Simpan ke pustaka</label>
        </div>
      </div>
      <div class="actions">
        <button class="primary" id="folder-btn">Analisis folder</button>
        <span class="status" id="folder-status"></span>
      </div>
      <div class="error" id="folder-error"></div>
      <div class="result" id="folder-result"></div>
    </section>

    <section class="panel" id="panel-jargon" role="tabpanel" aria-label="Jargon Buster">
      <label for="jargon-text">Tempel teks <span class="hint">— istilah akademik yang dikenali akan dijelaskan</span></label>
      <textarea id="jargon-text" placeholder="Tempel teks di sini."></textarea>
      <div class="actions">
        <button class="primary" id="jargon-btn">Cari istilah</button>
        <span class="status" id="jargon-status"></span>
      </div>
      <div class="error" id="jargon-error"></div>
      <div class="result" id="jargon-result"></div>
    </section>

    <section class="panel" id="panel-cite" role="tabpanel" aria-label="Citation Weaver">
      <label for="cite-text">Tempel naskah dengan penanda sitasi <span class="hint">— contoh: [cite:devlin2019]</span></label>
      <textarea id="cite-text" placeholder="Tulis naskah dengan [cite:kunci] di tempat sitasi."></textarea>
      <div class="row">
        <div>
          <label for="cite-refs">Bibliografi</label>
          <select id="cite-refs">
            <option value="sample">Contoh bawaan (7 referensi)</option>
            <option value="none">Tanpa bibliografi</option>
          </select>
        </div>
        <div>
          <label for="cite-style">Gaya sitasi</label>
          <select id="cite-style">
            <option value="apa">APA</option>
            <option value="mla">MLA</option>
            <option value="chicago">Chicago</option>
            <option value="ieee">IEEE</option>
            <option value="harvard">Harvard</option>
            <option value="vancouver">Vancouver</option>
          </select>
        </div>
        <div>
          <label for="cite-lang">Bahasa hasil</label>
          <select id="cite-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
      <details>
        <summary>Atau tempel bibliografi JSON sendiri</summary>
        <textarea id="cite-refs-json" placeholder='{"devlin2019": {"title": "BERT: ...", "year": 2019}}'></textarea>
      </details>
      <div class="actions">
        <button class="primary" id="cite-btn">Sisipkan sitasi</button>
        <span class="status" id="cite-status"></span>
      </div>
      <div class="error" id="cite-error"></div>
      <div class="result" id="cite-result"></div>
    </section>

    <section class="panel" id="panel-prompts" role="tabpanel" aria-label="Prompt Skripsi">
      <label for="prompt-select">Pilih prompt</label>
      <select id="prompt-select"></select>
      <div class="row" id="prompt-fields" style="margin-top:16px"></div>
      <div class="row">
        <div>
          <label for="prompt-lang">Bahasa prompt</label>
          <select id="prompt-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
      <div class="actions">
        <button class="primary" id="prompt-btn">Isi prompt</button>
        <button class="ghost" id="prompt-copy" disabled>Salin hasil</button>
        <span class="status" id="prompt-status"></span>
      </div>
      <div class="error" id="prompt-error"></div>
      <div class="result" id="prompt-result"></div>
    </section>

    <section class="panel" id="panel-library" role="tabpanel" aria-label="Pustaka">
      <p>Riwayat analisis yang disimpan dari tab Analisis Kualitas, dan bibliografi pribadi yang tumbuh dari referensi yang dikutip.</p>
      <div class="actions">
        <button class="primary" id="library-refresh">Muat ulang</button>
        <span class="status" id="library-status"></span>
      </div>
      <div class="error" id="library-error"></div>
      <div class="result" id="library-stats"></div>
      <div class="result" id="library-history"></div>
      <div class="result" id="library-detail"></div>
      <label for="library-search">Cari referensi <span class="hint">— judul, penulis, kunci, atau DOI</span></label>
      <input type="text" id="library-search" placeholder="misalnya: deep learning">
      <div class="actions">
        <button class="primary" id="library-search-btn">Cari</button>
      </div>
      <div class="result" id="library-refs"></div>
    </section>

    <section class="panel" id="panel-detect" role="tabpanel" aria-label="Deteksi AI">
      <label for="detect-text">Tempel teks <span class="hint">— minimal 30 kata</span></label>
      <textarea id="detect-text" placeholder="Tempel teks di sini."></textarea>
      <div class="row">
        <div>
          <label for="detect-lang">Bahasa teks</label>
          <select id="detect-lang">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
      <div class="actions">
        <button class="primary" id="detect-btn">Periksa teks</button>
        <span class="status" id="detect-status"></span>
      </div>
      <div class="error" id="detect-error"></div>
      <div class="result" id="detect-result"></div>
    </section>

  </div>
</main>
</div>
<script>
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
    });
  }
  function num(v, max) {
    // Numbers from the server are numbers — but a missing or
    // mistyped field must never render "NaN" or "undefined":
    // coerce and clamp (scores 0–100, components 0–25, counts 0+).
    var n = Number(v);
    if (!isFinite(n)) return 0;
    if (n < 0) n = 0;
    if (max !== undefined && n > max) n = max;
    return n;
  }
  function showError(id, msg) {
    var el = $(id);
    el.textContent = msg;
    el.classList.add("show");
  }
  function clearError(id) { $(id).classList.remove("show"); $(id).textContent = ""; }
  async function post(path, body) {
    var r = await fetch(path, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    var data = await r.json();
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }
  async function postForm(path, form) {
    var r = await fetch(path, {method: "POST", body: form});
    var data = await r.json();
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }
  async function get(path) {
    var r = await fetch(path);
    var data = await r.json();
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }
  function refsPayload(modeEl, jsonEl) {
    var custom = jsonEl.value.trim();
    if (custom) return {refs_json: custom};
    return {refs: modeEl.value};
  }

  document.querySelectorAll("nav.tabs button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("nav.tabs button").forEach(function (b) {
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      document.querySelectorAll(".panel").forEach(function (p) {
        p.classList.toggle("active", p.id === "panel-" + btn.dataset.tab);
      });
      if (btn.dataset.tab === "library") loadLibrary();
    });
  });

  function renderHistory(rows) {
    var h = "";
    if (!rows.length) {
      h += '<div class="card"><p>Belum ada riwayat analisis — centang "Simpan ke pustaka" di tab Analisis Kualitas.</p></div>';
    } else {
      h += '<div class="card"><h2>Riwayat analisis</h2><ul>';
      rows.forEach(function (a) {
        h += '<li><a href="#" data-analysis="' + num(a.id) + '">#' + num(a.id) + " " + esc(a.title) + "</a> — "
          + esc(a.created_at.slice(0, 10)) + ", skor " + num(a.quality_score, 100) + "/100, gaya "
          + num(a.style_score, 25) + "/25</li>";
      });
      h += "</ul></div>";
    }
    $("library-history").innerHTML = h;
  }
  function renderDetail(a) {
    var h = '<div class="card"><h2>Analisis #' + num(a.id) + " — " + esc(a.title) + "</h2>"
      + "<p>" + esc(a.created_at.slice(0, 10)) + " · Skor " + num(a.quality_score, 100) + "/100 · Gaya "
      + num(a.style_score, 25) + "/25 · Jargon " + num(a.jargon_count) + " · Sitasi hilang "
      + num(a.citations_missing) + " · DOI " + num(a.doi_ok) + "/" + num(a.doi_total) + "</p>";
    if (a.references && a.references.length) {
      h += "<p>Referensi dikutip: " + esc(a.references.join(", ")) + "</p>";
    }
    h += "<pre>" + esc(a.text) + "</pre></div>";
    $("library-detail").innerHTML = h;
  }
  function renderRefs(rows, query) {
    var h = "";
    if (!rows.length) {
      h += '<div class="card"><p>' + (query
        ? "Tidak ada referensi yang cocok dengan “" + esc(query) + "”."
        : "Tidak ada referensi di pustaka.") + "</p></div>";
    } else {
      h += '<div class="card"><h2>Referensi <span class="meta">' + rows.length + "</span></h2><ul>";
      rows.forEach(function (r) {
        h += "<li><strong>" + esc(r.key) + "</strong>" + (r.year ? " (" + num(r.year) + ")" : "")
          + ": " + esc(r.title || "-")
          + (r.authors ? ' <span class="src">' + esc(r.authors) + "</span>" : "")
          + (r.doi ? ' <span class="src">doi:' + esc(r.doi) + "</span>" : "") + "</li>";
      });
      h += "</ul></div>";
    }
    $("library-refs").innerHTML = h;
  }
  async function loadLibrary() {
    clearError("library-error");
    $("library-status").textContent = "Memuat…";
    try {
      var stats = await get("/api/library/stats");
      renderStats(stats.stats);
      var hist = await get("/api/library/history?limit=20");
      renderHistory(hist.analyses);
      var refs = await get("/api/library/refs?limit=20");
      renderRefs(refs.references, "");
    } catch (e) {
      showError("library-error", e.message);
    } finally {
      $("library-status").textContent = "";
    }
  }
  function renderStats(st) {
    if (!st.runs) {
      $("library-stats").innerHTML = '<div class="card"><h2>Statistik</h2><p>Belum ada riwayat analisis — jalankan analyze --save dulu.</p></div>';
      return;
    }
    var h = '<div class="card"><h2>Statistik</h2><div class="stats-grid">'
      + '<div class="stat"><span class="stat-num">' + num(st.runs) + '</span><span class="stat-label">Analisis tersimpan</span></div>'
      + '<div class="stat"><span class="stat-num">' + num(st.average_score, 100) + '</span><span class="stat-label">Rata-rata skor /100</span></div>';
    if (st.best) h += '<div class="stat"><span class="stat-num">' + num(st.best.quality_score, 100) + '</span><span class="stat-label">Terbaik: ' + esc(st.best.title) + '</span></div>';
    h += '</div><h3>Tren skor</h3>';
    st.trend.forEach(function (t) {
      h += '<div class="trend-row"><span class="trend-label">' + esc(t.title) + '</span><div class="bar"><span style="width:' + num(t.quality_score, 100) + '%"></span></div><span class="num">' + num(t.quality_score, 100) + '</span></div>';
    });
    if (st.most_cited.length) {
      h += '<h3>Referensi paling sering dikutip</h3><ul>';
      st.most_cited.forEach(function (c) {
        h += '<li><strong>' + esc(c.key) + '</strong> — ' + esc(c.title || c.key) + ' (' + num(c.count) + ' kali)</li>';
      });
      h += '</ul>';
    }
    h += '</div>';
    $("library-stats").innerHTML = h;
  }
  $("library-refresh").addEventListener("click", loadLibrary);
  $("library-search-btn").addEventListener("click", async function () {
    var q = $("library-search").value.trim();
    clearError("library-error");
    try {
      var res = await get("/api/library/refs?limit=20"
        + (q ? "&search=" + encodeURIComponent(q) : ""));
      renderRefs(res.references, q);
    } catch (e) {
      showError("library-error", e.message);
    }
  });
  $("library-search").addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      $("library-search-btn").click();
    }
  });
  $("library-history").addEventListener("click", async function (ev) {
    var link = ev.target.closest("a[data-analysis]");
    if (!link) return;
    ev.preventDefault();
    clearError("library-error");
    try {
      var res = await get("/api/library/analysis?id="
        + encodeURIComponent(link.dataset.analysis));
      renderDetail(res.analysis);
    } catch (e) {
      showError("library-error", e.message);
    }
  });

  function renderFolderResult(res, lang) {
    var f = res.folder;
    var h = '<div class="card"><h2>' + esc(f.folder) + ' <span class="meta">' + num(f.count) + ' file</span></h2>';
    if (f.average === null || f.average === undefined) {
      h += '<p>Tidak ada file .txt atau .md yang bisa dianalisis.</p>';
    } else {
      h += '<p>Rata-rata skor: <strong>' + num(f.average, 100) + '/100</strong></p>';
    }
    if (f.files.length) {
      h += '<table><thead><tr><th>File</th><th>Skor</th><th>Jargon</th><th>Sitasi</th><th>DOI</th><th>Gaya</th><th>Duplikat</th></tr></thead><tbody>';
      f.files.forEach(function (e) {
        h += '<tr><td>' + esc(e.file) + '</td>';
        if (e.error) {
          h += '<td colspan="6">Gagal: ' + esc(e.error) + '</td>';
        } else {
          h += '<td>' + num(e.quality_score, 100) + '/100</td><td>' + num(e.jargon_count) + '</td>';
          h += '<td>' + num(e.citations_cited) + ' dikutip' + (e.citations_missing.length ? ', ' + e.citations_missing.length + ' hilang' : '') + '</td>';
          h += '<td>' + num(e.doi_ok) + '/' + num(e.doi_total) + '</td><td>' + num(e.style_score, 25) + '/25</td>';
          h += '<td>' + ((e.duplicates === null || e.duplicates === undefined) ? '-' : num(e.duplicates)) + '</td>';
        }
        h += '</tr>';
      });
      h += '</tbody></table>';
    }
    // Audit #6 B-1: a truncated duplicates check must warn here
    // too, with the same wording as the single-file card — the
    // count in the table may be incomplete. num() with no max:
    // the spent count is never clamped (audit #6 H-2).
    f.files.forEach(function (e) {
      if (e.duplicates_truncated) {
        h += '<p><strong>\u26a0\ufe0f Peringatan (' + esc(e.file) + '): pemeriksaan duplikasi berhenti setelah ' + num(e.duplicates_comparisons_spent) + ' perbandingan (batas 2000) \u2014 hasil mungkin tidak lengkap; sebagian kalimat belum dibandingkan.</strong></p>';
      }
    });
    if (res.skipped && res.skipped.length) {
      h += '<p>Dilewati:</p><ul>';
      res.skipped.forEach(function (s) {
        h += '<li>' + esc(s.file) + ' — ' + esc(s.reason) + '</li>';
      });
      h += '</ul>';
    }
    h += '</div>';
    return h;
  }

  /* Pita skor: label dari angka, bukan karangan — ambang tetap. */
  function scoreBand(score, lang) {
    if (score >= 90) return {color: "var(--accent)", label: lang === "en" ? "Excellent" : "Sangat baik"};
    if (score >= 70) return {color: "var(--accent)", label: lang === "en" ? "Good — some fixes needed" : "Baik — ada yang diperbaiki"};
    if (score >= 50) return {color: "var(--warn)", label: lang === "en" ? "Needs revision" : "Perlu revisi"};
    return {color: "var(--bad)", label: lang === "en" ? "Needs major revision" : "Perlu banyak revisi"};
  }
  function scoreGauge(res, lang) {
    if (typeof res.quality_score !== "number") {
      return '<div class="card"><h2>Skor kualitas</h2><p>'
        + (lang === "en" ? "Score unavailable — please analyze again." : "Skor tidak tersedia — coba analisis lagi.")
        + '</p></div>';
    }
    var band = scoreBand(res.quality_score, lang);
    var h = '<div class="card gauge-card"><h2>Skor kualitas</h2>'
      + '<p class="caption">' + (lang === "en" ? "Score 0–100 from 4 components × 25 points." : "Skor 0–100 dari 4 komponen × 25 poin.") + '</p>'
      + '<div class="gauge-body"><div class="gauge-wrap">'
      + '<svg class="gauge" viewBox="0 0 120 120" role="img" aria-label="Skor kualitas ' + num(res.quality_score, 100) + ' dari 100">'
      + '<circle class="gauge-track" cx="60" cy="60" r="52"></circle>'
      + '<circle class="gauge-arc" cx="60" cy="60" r="52" pathLength="100" stroke-dasharray="100" stroke-dashoffset="' + (100 - num(res.quality_score, 100)) + '" style="stroke:' + band.color + '"></circle>'
      + '</svg><div class="gauge-center"><span class="gauge-num">' + num(res.quality_score, 100) + '</span><span class="gauge-of">/ 100</span><span class="gauge-band">' + band.label + '</span></div></div>';
    var parts = res.score_parts;
    if (parts && parts.length === 4) {
      var labels = lang === "en" ? ["Jargon", "Citations", "DOI", "Style"] : ["Jargon", "Sitasi", "DOI", "Gaya"];
      h += '<div class="parts">';
      parts.forEach(function (v, i) {
        v = Math.max(0, Math.min(25, Number(v) || 0));
        h += '<div class="part-row"><span class="part-label">' + labels[i] + '</span><div class="bar"><span style="width:' + (v / 25 * 100) + '%"></span></div><span class="part-num">' + Math.round(v) + '/25</span></div>';
      });
      h += '</div>';
    }
    h += '</div></div>';
    return h;
  }

  /* Pita skor AI: label dari angka, bukan karangan — ambang 60.
     Bila server men-cap verdict (kurang dari 3 sinyal berlaku),
     pita dipaksa ke Campuran apa pun skornya. Warnanya terbalik
     dari gauge kualitas: skor AI tinggi itu buruk. */
  function detectBand(score, lang, capped) {
    if (!capped && score >= 60) return {color: "var(--bad)", label: lang === "en" ? "Likely AI" : "Kemungkinan besar AI"};
    if (score >= 40) return {color: "var(--warn)", label: lang === "en" ? "Mixed / uncertain" : "Campuran / tidak pasti"};
    return {color: "var(--accent)", label: lang === "en" ? "Likely human" : "Kemungkinan besar manusia"};
  }

  function renderDetect(res, lang) {
    var h = "";
    if (typeof res.ai_score !== "number") {
      h += '<div class="card"><h2>Deteksi AI</h2><p>' + esc(res.verdict) + " — "
        + (lang === "en" ? "at least 30 words are needed to judge." : "butuh minimal 30 kata untuk menilai.") + "</p></div>";
    } else {
      var band = detectBand(res.ai_score, lang, res.verdict_capped);
      h += '<div class="card gauge-card"><h2>Deteksi AI</h2>'
        + '<p class="caption">' + (lang === "en" ? "Heuristic AI score 0–100 — an indication, not proof." : "Skor AI heuristik 0–100 — indikasi, bukan bukti.") + '</p>'
        + '<div class="gauge-body"><div class="gauge-wrap">'
        + '<svg class="gauge" viewBox="0 0 120 120" role="img" aria-label="Skor AI ' + num(res.ai_score, 100) + ' dari 100">'
        + '<circle class="gauge-track" cx="60" cy="60" r="52"></circle>'
        + '<circle class="gauge-arc" cx="60" cy="60" r="52" pathLength="100" stroke-dasharray="100" stroke-dashoffset="' + (100 - num(res.ai_score, 100)) + '" style="stroke:' + band.color + '"></circle>'
        + '</svg><div class="gauge-center"><span class="gauge-num">' + num(res.ai_score, 100) + '</span><span class="gauge-of">/ 100</span><span class="gauge-band">' + band.label + '</span></div></div>';
      if (res.verdict_capped && res.verdict_capped_reason) {
        h += '<p class="caption">' + esc(res.verdict_capped_reason) + "</p>";
      }
      var labels = lang === "en"
        ? {burstiness: "Sentence-length variation", template_phrases: "Template phrases", lexical_diversity: "Lexical diversity", starter_repetition: "Repeated sentence starters"}
        : {burstiness: "Variasi panjang kalimat", template_phrases: "Frasa template", lexical_diversity: "Keragaman kosakata", starter_repetition: "Pengulangan awalan kalimat"};
      h += '<div class="parts">';
      Object.keys(labels).forEach(function (k) {
        var s = res.signals[k];
        if (!s) return;
        var v = s.applicable ? num(s.score, 100) : 0;
        h += '<div class="part-row"><span class="part-label">' + labels[k] + '</span><div class="bar"><span style="width:' + v + '%"></span></div><span class="part-num">' + (s.applicable ? Math.round(v) + '/100' : '—') + '</span></div>';
      });
      h += '</div></div></div>';
      var top = (res.sentences || []).filter(function (x) { return x.score >= 70; });
      if (top.length) {
        h += '<div class="card"><h2>Kalimat paling mirip AI <span class="meta">' + top.length + '</span></h2><ul>';
        top.forEach(function (x) {
          h += "<li>" + esc(x.sentence) + ' <span class="meta">' + num(x.score, 100) + "/100</span></li>";
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Kalimat paling mirip AI</h2><p>Tidak ada kalimat yang melewati ambang 70/100.</p></div>';
      }
    }
    h += '<div class="card"><p>' + esc(res.note) + '</p></div>';
    return h;
  }

  function renderAnalyze(res, lang) {
    var h = "";
    h += scoreGauge(res, lang);
    /* Keterbacaan: Flesch Reading Ease + FKGL, dari /api/analyze —
       informatif saja, tidak memengaruhi skor 0-100. */
    if (res.readability) {
      var r = res.readability;
      h += '<div class="card"><h2>' + (lang === "en" ? "Readability" : "Keterbacaan") + '</h2><p>'
        + 'Flesch Reading Ease ' + num(r.flesch_reading_ease, 100).toFixed(1) + '/100 — ' + esc(r.band)
        + '<br>Flesch-Kincaid Grade Level ' + num(r.flesch_kincaid_grade)
        + '<br>' + (lang === "en" ? "Average " : "Rata-rata ") + num(r.avg_words_per_sentence) + (lang === "en" ? " words/sentence, " : " kata/kalimat, ") + num(r.avg_syllables_per_word) + (lang === "en" ? " syllables/word" : " suku kata/kata")
        + ' (' + num(r.words) + (lang === "en" ? " words, " : " kata, ") + num(r.sentences) + (lang === "en" ? " sentences, " : " kalimat, ") + num(r.total_syllables) + (lang === "en" ? " syllables)" : " suku kata)")
        + '</p><p>' + esc(r.note) + '</p></div>';
    }
    if (res.library_id) {
      h += '<div class="card"><p>Tersimpan di pustaka (id ' + num(res.library_id) + ").</p></div>";
    }
    if (res.jargon && res.jargon.length) {
      h += '<div class="card"><h2>Istilah jargon <span class="meta">' + res.jargon.length + ' ditemukan</span></h2><ul>';
      res.jargon.forEach(function (j) {
        h += "<li><strong>" + esc(j.term) + "</strong> — " + esc(j.translation)
          + ' <span class="src">(' + esc(j.field) + "; " + esc(j.source) + ")</span></li>";
      });
      h += "</ul></div>";
    } else {
      h += '<div class="card"><h2>Istilah jargon</h2><p>Tidak ada istilah jargon yang dikenali.</p></div>';
    }
    if (res.citations) {
      var c = res.citations;
      h += '<div class="card"><h2>Sitasi</h2><p>' + c.cited.length + " dikutip, "
        + c.missing.length + " hilang dari bibliografi, "
        + c.unused.length + " tak terpakai.</p>";
      if (c.missing.length) h += "<p><strong>Hilang:</strong> " + esc(c.missing.join(", ")) + "</p>";
      h += "</div>";
    } else {
      h += '<div class="card"><h2>Sitasi</h2><p>Tanpa bibliografi: audit sitasi dilewati.</p></div>';
    }
    var dv = res.doi_verification || {};
    var keys = Object.keys(dv);
    if (keys.length) {
      var ok = keys.filter(function (k) { return dv[k].verdict === "ok"; }).length;
      var withDoi = keys.filter(function (k) { return dv[k].doi; }).length;
      h += '<div class="card"><h2>Verifikasi DOI</h2><p>' + ok + " dari " + withDoi + " DOI terverifikasi.</p></div>";
    }
    var st = res.style;
    if (st) {
      if (st.flagged.length) {
        h += '<div class="card"><h2>Gaya <span class="meta">' + num(st.style_score, 25) + "/25</span></h2><ul>";
        st.flagged.forEach(function (name) {
          var s = st.signals[name];
          var label = {nominalization: "Verba ringan", connectors: "Konektor",
            passive: "Verba pasif", yang_mana: "'yang mana'/'dimana'",
            rhythm: "Ritme kalimat"}[name] || name;
          if (name === "rhythm") {
            h += "<li>" + esc(label) + ": " + Math.round(num(s.same_length_share, 1) * 100)
              + "% kalimat hampir sama panjang</li>";
          } else {
            h += "<li>" + esc(label) + ": " + num(s.count)
              + (s.examples && s.examples.length ? " (" + esc(s.examples.join(", ")) + ")" : "") + "</li>";
          }
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Gaya <span class="meta">' + num(st.style_score, 25) + '/25</span></h2><p>Tidak ada pola kaku yang terdeteksi.</p></div>';
      }
    }
    if (res.duplicates) {
      var d = res.duplicates;
      // Audit #5 B-1: when the work budget ran out the list below
      // is only partial — say so in the card, in both branches, so
      // a short or empty list is never mistaken for a complete check.
      var truncWarn = d.truncated ? '<p><strong>\u26a0\ufe0f Peringatan: pemeriksaan berhenti setelah ' + num(d.comparisons_spent) + ' perbandingan (batas 2000) \u2014 hasil mungkin tidak lengkap; sebagian kalimat belum dibandingkan.</strong></p>' : '';
      if (d.duplicates.length) {
        h += '<div class="card"><h2>Duplikasi <span class="meta">' + d.duplicates.length + ' kalimat berulang</span></h2>' + truncWarn + '<ul>';
        d.duplicates.forEach(function (x) {
          h += "<li>" + esc(x.sentence) + '<br><span class="meta">'
            + Math.round(num(x.similarity, 1) * 100) + "% mirip &ldquo;" + esc(x.match)
            + "&rdquo; — " + (x.source_id ? "pustaka #" + num(x.source_id) + " — " + esc(x.source_title) : "naskah ini") + "</span></li>";
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Duplikasi</h2>' + truncWarn + '<p>Tidak ada kalimat yang berulang dengan pustaka.</p></div>';
      }
    }
    if (res.recommendations && res.recommendations.length) {
      h += '<div class="card"><h2>Rekomendasi</h2><ul>';
      res.recommendations.forEach(function (r) { h += "<li>" + esc(r) + "</li>"; });
      h += "</ul></div>";
    }
    var sg = res.suggestions;
    if (sg && sg.suggestions && sg.suggestions.length) {
      var labels = {nominalization: "Verba ringan", connectors: "Konektor",
        passive: "Verba pasif", yang_mana: "'yang mana'/'dimana'",
        rhythm: "Ritme kalimat", typo: "Ejaan"};
      h += '<div class="card"><h2>Saran rewrite gaya <span class="meta">' + num(sg.count) + "</span></h2>";
      sg.suggestions.forEach(function (s, i) {
        h += "<p><strong>" + (i + 1) + ". " + esc(labels[s.pattern] || s.pattern) + "</strong> — “" + esc(s.original.trim()) + "”";
        if (s.replacement !== null) {
          h += " → “" + (s.replacement === "" ? "(hapus)" : esc(s.replacement)) + "”";
        }
        h += "<br><span class=\"hint\">Sebelum:</span> " + esc(s.context);
        if (s.fixed) {
          h += "<br><span class=\"hint\">Sesudah:</span> " + esc(s.fixed);
        } else {
          h += "<br>" + esc(s.note);
        }
        h += "</p>";
      });
      if (sg.count > sg.suggestions.length) {
        h += "<p>Menampilkan " + sg.suggestions.length + " dari " + num(sg.count) + " saran.</p>";
      }
      h += '<div class="actions"><button id="copy-fixed-btn" onclick="copyFixedText()">Salin teks yang diperbaiki</button> <span class="status" id="copy-fixed-status"></span></div>';
      h += "</div>";
    }
    return h;
  }

  async function copyFixedText() {
    var btn = $("copy-fixed-btn");
    var status = $("copy-fixed-status");
    if (!btn) return;
    btn.disabled = true;
    status.textContent = "Menyalin…";
    try {
      var res = await post("/api/humanize", {
        text: $("analyze-text").value,
        lang: $("analyze-lang").value,
        apply: true
      });
      var fixed = res.fixed_text || "";
      var n = (res.suggestions || []).filter(function (s) { return s.replacement !== null; }).length;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(fixed);
      } else {
        var ta = document.createElement("textarea");
        ta.value = fixed;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      status.textContent = "Disalin — " + n + " saran diterapkan.";
    } catch (e) {
      status.textContent = "Gagal: " + e.message;
    } finally { btn.disabled = false; }
  }

  $("analyze-btn").addEventListener("click", async function () {
    var btn = $("analyze-btn");
    clearError("analyze-error");
    $("analyze-result").innerHTML = "";
    var text = $("analyze-text").value.trim();
    if (!text) { showError("analyze-error", "Tempel naskah dulu."); return; }
    btn.disabled = true;
    $("analyze-status").textContent = "Menganalisis…";
    try {
      var body = refsPayload($("analyze-refs"), $("analyze-refs-json"));
      body.text = text;
      body.lang = $("analyze-lang").value;
      body.verify = $("analyze-verify").checked;
      body.suggest = $("analyze-suggest").checked;
      body.duplicates = $("analyze-duplicates").checked;
      body.save = $("analyze-save").checked;
      var res = await post("/api/analyze", body);
      $("analyze-result").innerHTML = renderAnalyze(res, body.lang);
      $("analyze-status").textContent = "";
    } catch (e) {
      showError("analyze-error", "Gagal: " + e.message);
      $("analyze-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  $("folder-btn").addEventListener("click", async function () {
    var btn = $("folder-btn");
    clearError("folder-error");
    $("folder-result").innerHTML = "";
    var dirFiles = $("folder-dir").files;
    var pickFiles = $("folder-files").files;
    if (!dirFiles.length && !pickFiles.length) {
      showError("folder-error", "Pilih folder atau beberapa file dulu.");
      return;
    }
    btn.disabled = true;
    $("folder-status").textContent = "Menganalisis folder…";
    try {
      var form = new FormData();
      var payload = refsPayload($("analyze-refs"), $("analyze-refs-json"));
      if (payload.refs) form.append("refs", payload.refs);
      if (payload.refs_json) form.append("refs_json", payload.refs_json);
      form.append("lang", $("analyze-lang").value);
      if ($("folder-verify").checked) form.append("verify", "1");
      if ($("folder-duplicates").checked) form.append("duplicates", "1");
      if ($("folder-save").checked) form.append("save", "1");
      var i;
      for (i = 0; i < dirFiles.length; i++) {
        form.append("files", dirFiles[i],
                    dirFiles[i].webkitRelativePath || dirFiles[i].name);
      }
      for (i = 0; i < pickFiles.length; i++) {
        form.append("files", pickFiles[i]);
      }
      var res = await postForm("/api/analyze-folder", form);
      $("folder-result").innerHTML = renderFolderResult(res, $("analyze-lang").value);
      $("folder-status").textContent = "";
    } catch (e) {
      showError("folder-error", "Gagal: " + e.message);
      $("folder-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  $("jargon-btn").addEventListener("click", async function () {
    var btn = $("jargon-btn");
    clearError("jargon-error");
    $("jargon-result").innerHTML = "";
    var text = $("jargon-text").value.trim();
    if (!text) { showError("jargon-error", "Tempel teks dulu."); return; }
    btn.disabled = true;
    $("jargon-status").textContent = "Mencari istilah…";
    try {
      var res = await post("/api/jargon", {text: text});
      var h = "";
      if (res.matches.length) {
        h += '<div class="card"><h2>Istilah ditemukan <span class="meta">' + res.matches.length + "</span></h2><ul>";
        res.matches.forEach(function (m) {
          h += "<li><strong>" + esc(m.term) + "</strong> — " + esc(m.translation)
            + ' <span class="src">(' + esc(m.field) + "; " + esc(m.source) + ")</span></li>";
        });
        h += "</ul></div>";
      } else {
        h += '<div class="card"><h2>Istilah ditemukan</h2><p>Tidak ada istilah kamus yang cocok dengan teks ini.</p></div>';
      }
      $("jargon-result").innerHTML = h;
      $("jargon-status").textContent = "";
    } catch (e) {
      showError("jargon-error", "Gagal: " + e.message);
      $("jargon-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  $("cite-btn").addEventListener("click", async function () {
    var btn = $("cite-btn");
    clearError("cite-error");
    $("cite-result").innerHTML = "";
    var text = $("cite-text").value.trim();
    if (!text) { showError("cite-error", "Tempel naskah dulu."); return; }
    btn.disabled = true;
    $("cite-status").textContent = "Menyisipkan sitasi…";
    try {
      var body = refsPayload($("cite-refs"), $("cite-refs-json"));
      body.text = text;
      body.style = $("cite-style").value;
      body.lang = $("cite-lang").value;
      var res = await post("/api/cite", body);
      $("cite-result").innerHTML = '<div class="card"><h2>Hasil</h2><pre class="bib">'
        + esc(res.output) + "</pre></div>";
      $("cite-status").textContent = "";
    } catch (e) {
      showError("cite-error", "Gagal: " + e.message);
      $("cite-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  var promptsCache = null;
  async function loadPrompts() {
    var r = await fetch("/api/prompts");
    var data = await r.json();
    promptsCache = data.prompts;
    var sel = $("prompt-select");
    var groups = {};
    data.prompts.forEach(function (p) {
      (groups[p.category] = groups[p.category] || []).push(p);
    });
    Object.keys(groups).forEach(function (cat) {
      var og = document.createElement("optgroup");
      og.label = cat;
      groups[cat].forEach(function (p) {
        var o = document.createElement("option");
        o.value = p.id;
        o.textContent = p.name;
        og.appendChild(o);
      });
      sel.appendChild(og);
    });
    renderPromptFields();
  }
  function currentPrompt() {
    var id = $("prompt-select").value;
    return promptsCache.find(function (p) { return p.id === id; });
  }
  function renderPromptFields() {
    var p = currentPrompt();
    var box = $("prompt-fields");
    box.innerHTML = "";
    if (!p) return;
    p.fields.forEach(function (f) {
      var div = document.createElement("div");
      var lab = document.createElement("label");
      lab.textContent = f.label;
      lab.setAttribute("for", "pf-" + f.key);
      var inp = document.createElement("input");
      inp.type = "text";
      inp.id = "pf-" + f.key;
      inp.dataset.key = f.key;
      div.appendChild(lab);
      div.appendChild(inp);
      box.appendChild(div);
    });
  }
  $("prompt-select").addEventListener("change", renderPromptFields);
  $("prompt-btn").addEventListener("click", async function () {
    var btn = $("prompt-btn");
    clearError("prompt-error");
    $("prompt-result").innerHTML = "";
    var p = currentPrompt();
    if (!p) { showError("prompt-error", "Pilih prompt dulu."); return; }
    var values = {};
    document.querySelectorAll("#prompt-fields input").forEach(function (inp) {
      values[inp.dataset.key] = inp.value;
    });
    btn.disabled = true;
    $("prompt-status").textContent = "Mengisi prompt…";
    try {
      var res = await post("/api/prompts/fill", {
        id: p.id, values: values, lang: $("prompt-lang").value
      });
      $("prompt-result").innerHTML = '<div class="card"><h2>Hasil</h2><pre>'
        + esc(res.text) + "</pre></div>";
      $("prompt-copy").disabled = false;
      $("prompt-status").textContent = "";
    } catch (e) {
      showError("prompt-error", "Gagal: " + e.message);
      $("prompt-status").textContent = "";
    } finally { btn.disabled = false; }
  });
  $("prompt-copy").addEventListener("click", async function () {
    var pre = document.querySelector("#prompt-result pre");
    if (!pre) return;
    try {
      await navigator.clipboard.writeText(pre.textContent);
      $("prompt-status").textContent = "Disalin.";
    } catch (e) {
      $("prompt-status").textContent = "Tidak bisa menyalin otomatis — blok lalu salin manual.";
    }
  });

  $("detect-btn").addEventListener("click", async function () {
    var btn = $("detect-btn");
    clearError("detect-error");
    $("detect-result").innerHTML = "";
    var text = $("detect-text").value.trim();
    if (!text) { showError("detect-error", "Tempel teks dulu."); return; }
    btn.disabled = true;
    $("detect-status").textContent = "Memeriksa…";
    try {
      var res = await post("/api/detect", {text: text, lang: $("detect-lang").value});
      $("detect-result").innerHTML = renderDetect(res, $("detect-lang").value);
      $("detect-status").textContent = "";
    } catch (e) {
      showError("detect-error", "Gagal: " + e.message);
      $("detect-status").textContent = "";
    } finally { btn.disabled = false; }
  });

  loadPrompts().catch(function (e) {
    showError("prompt-error", "Gagal memuat daftar prompt: " + e.message);
  });
})();
</script>
</body>
</html>
"""


_MAX_BODY = 1_000_000  # 1 MB cap on API request bodies
_DRAIN_CAP = 2_000_000  # most the server will read to discard an oversize body
_MAX_UPLOAD_BODY = 10_000_000  # 10 MB cap on a folder upload body
_DRAIN_UPLOAD_CAP = 12_000_000  # drain cap for an oversize upload
_MAX_FILE_BYTES = 1_000_000  # 1 MB cap per uploaded file


class RequestTooLargeError(ValueError):
    """Request body over the 1 MB cap (maps to HTTP 413)."""


def _error_message(e: Exception) -> str:
    """Plain message for an exception raised with one argument.

    str(KeyError("x")) is "'x'" (repr), so take args[0] instead.
    """
    return str(e.args[0]) if e.args else str(e)


def _load_ui_references(payload: dict) -> dict | None:
    """Resolve the UI's refs choice: 'sample' (default), 'none', or
    a pasted bibliography JSON string under 'refs_json'."""
    if payload.get("refs_json"):
        try:
            refs = json.loads(payload["refs_json"])
        except (json.JSONDecodeError, TypeError,
                RecursionError):
            # Audit #7 H-3: the decoder message itself (and the
            # TypeError text for a non-string refs_json, e.g.
            # "the JSON object must be str, bytes or bytearray,
            # not int") leaked raw into the API error. A fixed
            # generic message says the same thing to the user.
            raise ValueError("bibliografi JSON tidak valid") from None
        return _validate_references(refs)
    if payload.get("refs", "sample") == "none":
        return None
    try:
        return load_references(DEFAULT_REFS)
    except ValueError as e:
        # load_references reports a missing file as ValueError
        # ("File tidak ditemukan", audit #6 H-11); the UI keeps its
        # own friendlier wording for the shipped sample file, while
        # a genuinely malformed sample file still reports its own
        # error instead of being masked as "not found".
        if str(e).startswith("File tidak ditemukan"):
            raise ValueError(
                "contoh bibliografi tidak ditemukan di folder ini") from None
        raise


def _read_body(handler, max_body: int, drain_cap: int,
               label: str) -> bytes:
    """Read a request body, enforcing `max_body`. An oversize body is
    drained up to `drain_cap` so the client still reads the 413 and
    keep-alive stays usable; beyond the drain cap the connection is
    closed instead (see the v1.17.1 fix — unread bytes would otherwise
    be parsed as a new request line).

    A missing Content-Length means an empty body. A present one must
    be plain digits within the cap; anything else is a generic 400
    ("ukuran body tidak valid"), never a leaked int() traceback.
    Duplicate Content-Length headers with different values are also
    a 400 (RFC 7230 §3.3.2) — trusting the first one would leave
    the rest of the body unread and desync keep-alive. Identical
    duplicates are harmless and accepted.

    A Transfer-Encoding header is a 400, never silently ignored:
    chunked framing is not decoded here, so trusting the
    Content-Length next to it (or reading zero bytes when there is
    none) would leave the chunked body unread and desync
    keep-alive. The connection is closed for the same reason: the
    unread body must not be parsed as a new request.

    Whenever the length cannot be trusted (invalid or conflicting),
    the body cannot be drained, so the connection is closed instead
    of leaving unread bytes to be parsed as a new request.

    Accepted behaviour (audit #5, N-13): bytes a client sends
    BEYOND Content-Length are that client's framing error, and the
    stdlib parses them as the start of a pipelined next request
    (e.g. a 501 for a garbage method). Only that offending
    connection is affected — no other client sees it — and a
    well-behaved client (browser, fetch) never sends them, so this
    is documented, not fixed."""
    get_all = getattr(handler.headers, "get_all", None)
    if get_all is not None:
        raw_te = get_all("Transfer-Encoding") or []
    else:  # plain-dict headers (unit-test fakes): at most one value
        single = handler.headers.get("Transfer-Encoding")
        raw_te = [] if single is None else [single]
    if raw_te:
        handler.close_connection = True
        raise ValueError("Transfer-Encoding tidak didukung")
    if get_all is not None:
        raw_lengths = get_all("Content-Length") or []
    else:  # plain-dict headers (unit-test fakes): at most one value
        single = handler.headers.get("Content-Length")
        raw_lengths = [] if single is None else [single]
    if not raw_lengths:
        length = 0
    else:
        if len({v.strip() for v in raw_lengths}) > 1:
            handler.close_connection = True
            raise ValueError("ukuran body tidak valid")
        raw_length = raw_lengths[0].strip()
        if not re.fullmatch(r"\d+", raw_length):
            handler.close_connection = True
            raise ValueError("ukuran body tidak valid")
        length = int(raw_length)
    if length > max_body:
        if length <= drain_cap:
            remaining = length
            while remaining > 0:
                chunk = handler.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        else:
            handler.close_connection = True
        raise RequestTooLargeError(
            f"badan permintaan terlalu besar (maks {label})")
    return handler.rfile.read(length) if length else b""


def _read_json_body(handler) -> dict:
    raw = _read_body(handler, _MAX_BODY, _DRAIN_CAP, "1 MB") or b"{}"
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError,
            RecursionError):
        raise ValueError("badan permintaan harus JSON yang valid")
    if not isinstance(body, dict):
        raise ValueError("badan permintaan harus berupa objek JSON")
    return body


def _multipart_param(disposition: str, param: str):
    """One parameter out of a Content-Disposition header (RFC 7578).

    Splits on ';' outside quoted strings and unescapes \" and \\
    inside a quoted value, so a filename like "a;b.txt" — or one
    containing a quote — survives intact instead of being cut at
    the first semicolon.
    """
    pieces = []
    buf = []
    in_quotes = False
    i = 0
    n = len(disposition)
    while i < n:
        ch = disposition[i]
        # Inside quotes a backslash only escapes " and \ (RFC 7578):
        # "\n" is a literal backslash followed by n, not an escape,
        # so "a\nb.txt" keeps its backslash instead of becoming
        # "anb.txt".
        if ch == "\\" and in_quotes and i + 1 < n \
                and disposition[i + 1] in ('"', "\\"):
            buf.append(disposition[i + 1])
            i += 2
            continue
        if ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
        elif ch == ";" and not in_quotes:
            pieces.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    pieces.append("".join(buf))
    for piece in pieces:
        piece = piece.strip()
        if piece.startswith(param + "="):
            value = piece[len(param) + 1:].strip()
            if len(value) >= 2 and value.startswith('"') \
                    and value.endswith('"'):
                value = value[1:-1]
            return value
    return None


def _parse_multipart(body: bytes, boundary: bytes) -> list[dict]:
    """Parse a multipart/form-data body (stdlib only — `cgi` is gone
    in Python 3.13).

    Returns a list of parts: {"name", "filename" (or None for a plain
    field), "content_type" (or None), "data" (bytes)}. Raises
    ValueError on a malformed body.

    Line-oriented: a delimiter only counts when it fills a whole
    line ("--" + boundary, or "--" + boundary + "--" for the close),
    so a file whose content merely contains the boundary mid-line
    never splits the parse. Headers are read line by line, so
    LF-only and CRLF bodies parse the same way. Part bytes are
    reconstructed exactly (the CRLF before a delimiter is framing,
    not data); the one exception is a lone trailing CR at the very
    end of a part, which is indistinguishable from that framing.
    """
    if not boundary:
        raise ValueError("boundary multipart tidak ditemukan")
    delim = b"--" + boundary
    close = delim + b"--"
    lines = body.split(b"\n")
    parts = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i][:-1] if lines[i].endswith(b"\r") else lines[i]
        if line == close:
            break
        if line != delim:
            i += 1
            continue
        i += 1
        head_lines = []
        while i < n:
            head = lines[i][:-1] if lines[i].endswith(b"\r") else lines[i]
            if head == b"":
                break
            if head == delim or head == close:
                # A delimiter inside the headers means the blank
                # line between headers and body is missing: malformed.
                raise ValueError("bagian multipart tidak valid")
            head_lines.append(lines[i])
            i += 1
        if i >= n:
            raise ValueError("bagian multipart tidak valid")
        i += 1  # skip the blank line between headers and body
        data_lines = []
        while i < n:
            line = lines[i][:-1] if lines[i].endswith(b"\r") else lines[i]
            if line == delim or line == close:
                break
            data_lines.append(lines[i])
            i += 1
        headers = {}
        for raw in head_lines:
            # Header bytes are usually ASCII, but a filename may be
            # UTF-8: decode as UTF-8 first so "ünïcode-✓.txt" stays
            # readable instead of mojibake-ing through latin-1.
            # Anything that is not valid UTF-8 (e.g. a latin-1 byte)
            # falls back to latin-1, which never fails.
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            if ":" in text:
                key, value = text.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        name = _multipart_param(
            headers.get("content-disposition", ""), "name")
        if name is None:
            continue
        data = b""
        for j, raw in enumerate(data_lines):
            if j < len(data_lines) - 1:
                data += raw + b"\n"
            else:
                data += raw[:-1] if raw.endswith(b"\r") else raw
        parts.append({"name": name,
                      "filename": _multipart_param(
                          headers.get("content-disposition", ""),
                          "filename"),
                      "content_type": headers.get("content-type"),
                      "data": data})
    return parts


def _json_flag(body: dict, key: str) -> bool:
    """A JSON API boolean flag: only the JSON value `true` counts.

    Audit #7 H-1: `bool(body.get(key))` treated any truthy value
    as on, so a client sending the STRING "false" got the effect
    of `true` — `save: "false"` really WROTE a row to the library.
    Only an actual JSON `true` (Python `True`) enables the flag;
    strings, numbers, and anything else are ignored (not an
    error — the web UI always sends real booleans). The
    folder-upload path is form data, not JSON, and keeps its
    presence-based flags ("verify" in fields) — this helper is
    for the JSON handlers only.
    """
    return body.get(key) is True


def _json_text(body: dict) -> str:
    """The `text` field of a JSON API request, validated.

    Audit #7 H-2: `str(body.get("text") or "")` silently coerced
    a list/dict/bool into its repr and analyzed it with a 200
    ("['a']" was even echoed back by humanize+apply). A missing
    or null text still means "teks kosong" (as before); any other
    non-string is a plain 400.
    """
    raw = body.get("text")
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raise ValueError("text harus berupa string")
    text = raw.strip()
    if not text:
        raise ValueError("teks kosong")
    return text


class _UIHandler(http.server.BaseHTTPRequestHandler):
    """Serves the embedded page plus a small JSON API for the five tabs."""

    protocol_version = "HTTP/1.1"

    def setup(self):
        # A stalled connection must not hold one of the 8 handler
        # slots forever: 30 seconds, then the socket gives up.
        super().setup()
        self.connection.settimeout(30)

    def send_error(self, code, message=None, explain=None):
        # The stdlib error page is HTML without the security
        # headers; send the same page with them — and keep a
        # hostile method token out of the raw status line. The
        # Content-Length matters: without it an HTTP/1.1 client
        # waits forever for the body to end.
        # Close the connection after any error from the stdlib
        # parse path: a failed request line leaves its header
        # lines unread, and handle() would otherwise parse them
        # as a brand-new (HTTP/0.9) request and send a second
        # error body that desyncs keep-alive. This also covers
        # HTTP/0.9 requests, whose responses carry no headers at
        # all under the stdlib — closing is the safe alternative
        # to sending a header-less response on a live connection.
        # Accepted stdlib behaviours, documented not fixed
        # (audit #5, N-14/N-15): a blank line before the request
        # line closes the connection with no response at all
        # (RFC 7230 §3.5 says a server SHOULD ignore one empty
        # line; http.server does not), and HTTP/0.9-style and 505
        # responses carry no headers on Python <=3.12 — the stdlib
        # skips them there, while 3.13 sends the full response.
        # Neither leaks data to another client; the connection
        # close above is what keeps it safe.
        self.close_connection = True
        safe = (message or "").replace("\r", " ").replace("\n", " ")
        body = ("<!DOCTYPE HTML><html><head><title>%d</title></head>"
                "<body><h1>%d</h1></body></html>"
                % (code, code)).encode("utf-8")
        self.send_response(code, safe or None)
        if self.close_connection:
            self.send_header("Connection", "close")
        self.send_header("Content-Type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def version_string(self):
        # No "BaseHTTP/0.6 Python/3.12.3": the Server header must
        # not advertise the interpreter version.
        return "academic-tools"

    def _security_headers(self):
        # Every response carries the same three headers. The page
        # uses inline CSS/JS, so the CSP must allow 'unsafe-inline'
        # for style and script (default-src stays 'self').
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

    def log_message(self, *args):  # keep the console quiet
        pass

    def _connection_header(self) -> None:
        # Audit #6 H-1 / audit #7 N-4: say so when the connection
        # is being closed (bad framing, oversize body, timeout) —
        # without this header a reusing client gets EOF instead.
        # HTTP/1.0 defaults to close, so a client that asked to
        # keep the connection alive needs the header to know the
        # reuse is honoured (audit #6 N-8).
        if self.close_connection:
            self.send_header("Connection", "close")
        elif self.request_version == "HTTP/1.0":
            self.send_header("Connection", "keep-alive")

    def _send_json(self, status: int, payload: dict) -> None:
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            # A lone surrogate in the payload (an echoed input text,
            # e.g. /api/humanize + apply) cannot be UTF-8-encoded:
            # answer 400 with a clean message instead of leaking
            # the raw codec error (audit #6 N-2). The fallback
            # payload is plain ASCII, so it always encodes.
            status = 400
            payload = {"error":
                       "teks mengandung karakter surrogate yang tidak valid"}
            data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        # Audit #6 H-1: like send_error, say so when the connection
        # is being closed (bad framing, oversize body, timeout) —
        # without this header a reusing client gets EOF instead.
        self._connection_header()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(data)

    def _send_page(self) -> None:
        data = WEB_UI_HTML.replace(
            "__ACADEMIC_TOOLS_VERSION__", __version__).encode("utf-8")
        self.send_response(200)
        # Audit #7 N-4: the page used to skip the Connection
        # header _send_json sends — same logic, same helper.
        self._connection_header()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)
        try:
            if path in ("/", "/index.html"):
                self._send_page()
            elif path == "/api/prompts":
                self._send_json(200, {"prompts": [
                    {"id": p["id"], "name": p["name"], "name_en": p["name_en"],
                     "category": p["category"], "tool": p["tool"],
                     "fields": p["fields"]}
                    for p in PROMPTS
                ]})
            elif path == "/api/library/history":
                self._send_json(200, self._library_history(query))
            elif path == "/api/library/analysis":
                self._send_json(200, self._library_analysis(query))
            elif path == "/api/library/refs":
                self._send_json(200, self._library_refs(query))
            elif path == "/api/library/stats":
                self._send_json(200, self._library_stats())
            else:
                self._send_json(404, {"error": "tidak ditemukan"})
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except KeyError as e:
            self._send_json(404, {"error": _error_message(e)})
        except (TimeoutError, socket.timeout):
            # A stalled read or a write to a client that stopped
            # reading is not a server crash: send no misleading
            # 500 — and the socket is unusable for further reads
            # after a timeout, so close it. (Both names: on
            # Python 3.9 socket.timeout is not TimeoutError yet.)
            self.close_connection = True
        except Exception:
            self._send_json(500, {"error": "kesalahan server, coba lagi"})

    @staticmethod
    def _query_int(query: dict, name: str, default: int) -> int:
        raw = (query.get(name) or [None])[0]
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            raise ValueError(f"{name} harus angka")
        return max(1, min(100, value))

    def _library_history(self, query: dict) -> dict:
        return {"analyses": list_analyses(
            limit=self._query_int(query, "limit", 20))}

    def _library_analysis(self, query: dict) -> dict:
        raw = (query.get("id") or [None])[0]
        if raw is None:
            raise ValueError("id analisis harus angka")
        try:
            # Audit #7 N-7: int() accepts a leading "+" ("+1" is
            # id 1) where the old .isdigit() check rejected it.
            # A negative id is not a valid analysis id (400);
            # zero falls through to get_analysis, which returns
            # None, so id=0 still answers 404 like before
            # (audit #6 T-1 pins that).
            analysis_id = int(raw)
        except (TypeError, ValueError):
            raise ValueError("id analisis harus angka")
        if analysis_id < 0:
            raise ValueError("id analisis harus angka")
        analysis = get_analysis(analysis_id)
        if analysis is None:
            raise KeyError(f"tidak ada analisis #{raw}")
        return {"analysis": analysis}

    def _library_refs(self, query: dict) -> dict:
        limit = self._query_int(query, "limit", 20)
        search = (query.get("search") or [""])[0].strip()
        if search:
            rows = search_references(search, limit=limit)
        else:
            rows = list_references(limit=limit)
        return {"references": rows}

    def _library_stats(self) -> dict:
        return {"stats": library_stats()}

    def do_POST(self):
        path = urlsplit(self.path).path
        try:
            if path == "/api/analyze-folder":
                self._send_json(200, self._analyze_folder_upload())
                return
            body = _read_json_body(self)
            if path == "/api/analyze":
                self._send_json(200, self._analyze(body))
            elif path == "/api/humanize":
                self._send_json(200, self._humanize(body))
            elif path == "/api/jargon":
                self._send_json(200, self._jargon(body))
            elif path == "/api/cite":
                self._send_json(200, self._cite(body))
            elif path == "/api/prompts/fill":
                self._send_json(200, self._fill_prompt(body))
            elif path == "/api/detect":
                self._send_json(200, self._detect(body))
            else:
                self._send_json(404, {"error": "tidak ditemukan"})
        except RequestTooLargeError as e:
            self._send_json(413, {"error": str(e)})
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except (LookupError, KeyError) as e:
            self._send_json(400, {"error": _error_message(e)})
        except (TimeoutError, socket.timeout):
            # A client that stalls mid-body is not a server crash:
            # no misleading 500 — and the socket is unusable for
            # further reads after a timeout, so close it instead
            # of letting handle() re-parse the stream and log a
            # traceback for the follow-up read. (Both names: on
            # Python 3.9 socket.timeout is not TimeoutError yet.)
            self.close_connection = True
        except Exception:
            self._send_json(500, {"error": "kesalahan server, coba lagi"})

    def _analyze_folder_upload(self) -> dict:
        """POST /api/analyze-folder: a multipart/form-data upload of a
        whole folder (the browser's webkitdirectory input) or several
        files at once. Same rules as `analyze <folder>` on the CLI:
        only top-level .txt/.md files are analyzed, in name order;
        files in subfolders and other extensions are reported under
        "skipped" instead of failing the run. Form fields mirror the
        Analisis Kualitas tab: refs / refs_json, lang, and the
        verify / duplicates / save checkboxes (present = checked).
        Body cap 10 MB. Returns {"folder": <analyze_folder result>,
        "skipped": [{"file", "reason"}]}.
        """
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            raise ValueError("unggahan folder harus multipart/form-data")
        # Quote-aware: a boundary like "a;b" must survive intact —
        # a naive split(";") would cut it at the semicolon.
        boundary = _multipart_param(ctype, "boundary")
        if not boundary:
            raise ValueError("boundary multipart tidak ditemukan")
        raw = _read_body(self, _MAX_UPLOAD_BODY, _DRAIN_UPLOAD_CAP,
                         "10 MB")
        parts = _parse_multipart(raw, boundary.encode("latin-1"))
        fields = {}
        files = []
        for part in parts:
            if part["filename"]:
                files.append(part)
            elif part["filename"] is None:
                fields[part["name"]] = part["data"].decode("utf-8",
                                                           "replace")
            # filename="" (an unchosen file input) is neither a
            # file nor a field: ignore it, so an upload of only
            # empty filenames is a 400 via the check below instead
            # of a 200 with count 0.
        if not files:
            raise ValueError(
                "tidak ada file yang diunggah — pilih folder dulu")
        lang = fields.get("lang", "id")
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        payload = {"refs": fields.get("refs", "sample")}
        if fields.get("refs_json", "").strip():
            payload["refs_json"] = fields["refs_json"]
        refs = _load_ui_references(payload)
        files.sort(key=lambda p: (p["filename"] or "").replace("\\", "/"))
        entries = []
        skipped = []
        rels = []
        for part in files:
            rel = (part["filename"] or "").replace("\\", "/")
            rels.append(rel)
            name = rel.rsplit("/", 1)[-1]
            if "/" in rel:
                skipped.append({"file": name,
                                "reason": "bukan file tingkat atas"})
                continue
            if name.startswith("."):
                # Like `analyze <folder>` on the CLI (audit #6 N-4):
                # dotfiles are not manuscripts.
                skipped.append({"file": name,
                                "reason": "file tersembunyi"})
                continue
            if not name.lower().endswith(_FOLDER_EXTENSIONS):
                skipped.append({"file": name,
                                "reason": "bukan .txt atau .md"})
                continue
            if len(part["data"]) > _MAX_FILE_BYTES:
                skipped.append({"file": name,
                                "reason": "file lebih dari 1 MB"})
                continue
            entry = _blank_folder_entry(name)
            try:
                text = part["data"].decode("utf-8")
            except UnicodeDecodeError:
                # Audit #7 H-3: the raw codec message ("'utf-8'
                # codec can't decode byte 0xff ...") leaked into
                # the entry error. Fixed generic message.
                entry["error"] = "file bukan teks UTF-8 yang valid"
                entries.append(entry)
                continue
            entries.append(_analyze_one_file(
                entry, text, refs, lang=lang,
                verify_dois="verify" in fields,
                duplicates="duplicates" in fields,
                save="save" in fields))
        firsts = {r.split("/", 1)[0] for r in rels if "/" in r}
        folder_name = "unggahan"
        if len(firsts) == 1:
            only = firsts.pop()
            # Never name the folder ".." (or "."): a filename like
            # "../../etc/passwd.txt" is skipped as non-top-level,
            # but its first component must not become the display
            # name — fall back to "unggahan".
            if only and only not in (".", ".."):
                folder_name = only
        scores = [e["quality_score"] for e in entries
                  if e["quality_score"] is not None and not e.get("error")]
        average = round(sum(scores) / len(scores), 1) if scores else None
        # The browser's recap table never reads the file text,
        # so it is not sent back: a folder upload would otherwise
        # echo every manuscript. (The CLI folder --json keeps "text".)
        for e in entries:
            e.pop("text", None)
        return {"folder": {"folder": folder_name, "files": entries,
                           "count": len(entries), "average": average},
                "skipped": skipped}

    def _analyze(self, body: dict) -> dict:
        text = _json_text(body)
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        refs = _load_ui_references(body)
        result = analyze_text_quality(
            text, refs, lang=lang, verify_dois=_json_flag(body, "verify"),
            suggest=_json_flag(body, "suggest"))
        # The dashboard gauge reads the four 25-point components from
        # here, so the browser never recomputes the score.
        result["score_parts"] = _score_parts(result)
        if _json_flag(body, "duplicates"):
            result["duplicates"] = find_duplicates(text)
        if _json_flag(body, "save"):
            result["library_id"] = save_analysis(text, result, refs)
        return result

    def _humanize(self, body: dict) -> dict:
        text = _json_text(body)
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        result = suggest_style_fixes(text, lang=lang, limit=None)
        if _json_flag(body, "apply"):
            result["fixed_text"] = apply_suggestions(text, result)["text"]
        return result

    def _jargon(self, body: dict) -> dict:
        text = _json_text(body)
        field = body.get("field") or None
        if field is not None:
            # Audit #7 N-8: an unknown field used to be silently
            # ignored (zero matches), unlike an unknown lang/style
            # which answers 400. The known fields come from the
            # merged dictionary (built-in + user-added), so a field
            # a user added in dictionary.json stays valid.
            known = {v[1] for v in load_dictionary().values()}
            if not isinstance(field, str) or field not in known:
                raise ValueError(f"bidang tidak dikenal: {field}")
        matches = find_terms(text, field)
        return {"matches": matches, "count": len(matches)}

    def _cite(self, body: dict) -> dict:
        text = _json_text(body)
        refs = _load_ui_references(body)
        if refs is None:
            raise ValueError("sitasi butuh bibliografi (pilih contoh bawaan atau tempel JSON)")
        style = body.get("style") or "apa"
        if style not in STYLES:
            raise ValueError(f"gaya tidak dikenal: {style}")
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        output, woven = weave(text, refs, style=style, lang=lang)
        return {"output": output, "woven": woven}

    def _detect(self, body: dict) -> dict:
        text = _json_text(body)
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        return detect_ai(text, lang=lang)

    def _fill_prompt(self, body: dict) -> dict:
        prompt_id = str(body.get("id") or "")
        prompt = get_prompt(prompt_id)
        if prompt is None:
            raise ValueError(f"prompt tidak dikenal: {prompt_id}")
        values = body.get("values") or {}
        if not isinstance(values, dict):
            raise ValueError("values harus berupa objek {kunci: nilai}")
        lang = body.get("lang") or "id"
        if lang not in ("id", "en"):
            raise ValueError("lang harus 'id' atau 'en'")
        return {"text": fill_prompt(prompt_id, values, lang=lang)}


class _BoundedThreadingHTTPServer(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer with a cap on concurrent handlers (8):
    an unbounded thread pool lets one client exhaust the process
    with slow parallel uploads. The semaphore is held for the whole
    request handling (process_request_thread), not just the spawn —
    holding it only while spawning would bound nothing. The cap is
    per-instance, not a class attribute: two servers in one process
    (the test suite does this) must not share one 8-slot pool."""

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def process_request_thread(self, request, client_address):
        with self._slots:
            super().process_request_thread(request, client_address)

    def handle_error(self, request, client_address):
        # process_request_thread calls the SERVER's handle_error
        # (not the handler's): a client that aborts mid-request
        # (broken pipe / reset) — or stalls past the socket
        # timeout — is not a server error. Swallow it instead of
        # logging a traceback to stderr. Anything else still goes
        # to the default handler, traceback and all. (Both timeout
        # names: on Python 3.9 socket.timeout is not TimeoutError
        # yet; on 3.10+ they are the same.)
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError,
                            TimeoutError, socket.timeout)):
            return
        super().handle_error(request, client_address)


class _BoundedThreadingHTTPServer6(_BoundedThreadingHTTPServer):
    """The same capped server, for the IPv6 loopback (::1)."""

    address_family = socket.AF_INET6


def make_server(host: str = "127.0.0.1", port: int = 8000):
    """Build the local web UI server (port 0 picks a free port).

    Only loopback hosts are allowed: the UI has no authentication
    and must never listen on a LAN or public interface.
    """
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError(
            "serve hanya boleh di localhost: host harus 127.0.0.1, "
            "localhost, atau ::1")
    cls = (_BoundedThreadingHTTPServer6 if host == "::1"
           else _BoundedThreadingHTTPServer)
    try:
        return cls((host, port), _UIHandler)
    except OSError as e:
        # A machine without IPv6 cannot bind ::1 at all: say so
        # plainly (exit 1, no traceback) instead of leaking the
        # socket.gaierror.
        if host == "::1":
            raise ValueError("IPv6 tidak didukung di mesin ini") from e
        raise


def serve_main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Serve a local web UI for all six tools (localhost only).")
    p.add_argument("--port", type=int, default=8000,
                   help="port to listen on (default: 8000)")
    p.add_argument("--host", default="127.0.0.1",
                   help="interface to bind (default: 127.0.0.1, localhost only)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)
    server = make_server(args.host, args.port)
    host, port = server.server_address[:2]
    # flush=True: as a service stdout is a pipe (block-buffered),
    # so without it the banner sits in the buffer until the
    # process stops and never shows in the service log.
    print(f"Academic Tools v{__version__} — buka http://{host}:{port}/",
          flush=True)
    print("Berhenti dengan Ctrl-C. Hanya localhost; tidak ada data yang keluar dari komputer ini.",
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.", flush=True)
    return 0


def main(argv=None, *, version=None) -> int:
    """Entry point. No args -> interactive menu; jargon/cite/prompts -> passthrough."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("jargon", "cite", "prompts", "analyze",
                           "humanize", "library", "serve", "duplicates",
                           "detect", "readability"):
        tool, rest = argv[0], argv[1:]
        try:
            if tool == "jargon":
                return jargon_main(rest)
            if tool == "cite":
                return cite_main(rest)
            if tool == "analyze":
                return analyze_main(rest)
            if tool == "humanize":
                return humanize_main(rest)
            if tool == "library":
                return library_main(rest)
            if tool == "duplicates":
                return duplicates_main(rest)
            if tool == "detect":
                return detect_main(rest)
            if tool == "readability":
                return readability_main(rest)
            if tool == "serve":
                return serve_main(rest)
            return prompts_main(rest)
        except ValueError as e:
            # Bad input (bad JSON, empty text, non-loopback host, ...)
            # is a plain stderr message and exit 1 — never a traceback.
            # SystemExit from argparse is deliberately not caught.
            print(str(e), file=sys.stderr)
            return 1
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] in ("-v", "--version"):
        if version is not None:
            # Invoked as a shim (python3 academic_cli.py --version):
            # print just this component's version, matching the
            # shim's __version__ (CLI_VERSION) — not the full list.
            print(f"{os.path.basename(sys.argv[0])} {version}")
            return 0
        print(f"academic_tools.py {__version__} "
              f"(cli {CLI_VERSION}; jargon_buster {JARGON_VERSION}; "
              f"citation_weaver {CITATION_VERSION}; "
              f"skripsi_prompts {PROMPTS_VERSION}; "
              f"academic_quality_check {QUALITY_VERSION}; "
              f"ai_detector {DETECTOR_VERSION}; "
              f"readability {READABILITY_VERSION})")
        return 0
    try:
        return CLI().run()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
