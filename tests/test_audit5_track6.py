"""Track 6 (audit #5): N-7 detector limit note in CLI output.

A short text can never reach "Kemungkinan besar AI" — lexical
diversity only applies at >=100 words and starter repetition only
at >=6 sentences — but before this fix the CLI only printed the cap
reason ("only 2 of 4 signals apply") without stating that structural
limit. format_detect now appends it whenever the verdict is capped.
"""

import unittest

import academic_tools as tools

# 5 uniform sentences, under 100 words: only 2 signals apply, so a
# score >= 60 is capped at "Campuran" (same fixture family as
# test_detector.py's capped cases).
CAPPED_ID = (
    "Teknologi informasi telah mengubah cara perusahaan beroperasi dalam satu dekade terakhir. "
    "Perusahaan yang mengadopsi teknologi digital dapat meningkatkan efisiensi operasional mereka. "
    "Selain itu, teknologi digital memungkinkan perusahaan menjangkau pasar yang lebih luas. "
    "Dalam hal ini, transformasi digital menjadi kebutuhan bagi perusahaan modern. "
    "Perusahaan harus berinvestasi dalam teknologi untuk tetap kompetitif di pasar global."
)
CAPPED_EN = (
    "This study uses a survey method. "
    "Data were collected through a questionnaire distributed to "
    "the respondents. "
    "Moreover, interviews were conducted with several key "
    "informants. "
    "The collected data were analyzed using descriptive "
    "statistics. "
    "In conclusion, this method was chosen because it fits the "
    "purpose of the study."
)


class TestDetectorLimitNoteAudit5(unittest.TestCase):
    """N-7: format_detect states the detector's structural limit."""

    def test_capped_id_format_states_the_limit(self):
        result = tools.detect_ai(CAPPED_ID)
        self.assertTrue(result["verdict_capped"])
        out = tools.format_detect(result)
        self.assertIn("Batas detektor", out)
        self.assertIn("<100 kata", out)
        self.assertIn("<6 kalimat", out)

    def test_capped_en_format_states_the_limit(self):
        result = tools.detect_ai(CAPPED_EN, lang="en")
        self.assertTrue(result["verdict_capped"])
        out = tools.format_detect(result, lang="en")
        self.assertIn("Detector limit", out)
        self.assertIn("<100 words", out)
        self.assertIn("<6 sentences", out)

    def test_uncapped_format_has_no_limit_note(self):
        # A long AI-like text reaches the top band without the cap,
        # so the limit note must not appear.
        text = (" ".join(
            ["Selain itu, penelitian ini menggunakan metode survei "
             "untuk mengumpulkan data dari responden yang dipilih "
             "secara acak di berbagai wilayah penelitian."] * 12))
        result = tools.detect_ai(text)
        self.assertFalse(result["verdict_capped"])
        self.assertNotIn("Batas detektor",
                         tools.format_detect(result))

    def test_cap_reason_itself_is_unchanged(self):
        # The dict's verdict_capped_reason keeps its exact wording
        # (other tests pin "2 dari 4" on it); the limit lives only
        # in the rendered output.
        result = tools.detect_ai(CAPPED_ID)
        self.assertIn("2 dari 4", result["verdict_capped_reason"])
        self.assertNotIn("Batas detektor",
                         result["verdict_capped_reason"])


if __name__ == "__main__":
    unittest.main()
