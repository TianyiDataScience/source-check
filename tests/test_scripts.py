"""Tests for the source-check scripts. Run from the repository root:

    python3 -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "source-check", "scripts")
EXAMPLE_PDF = os.path.join(ROOT, "examples", "water-report.pdf")

sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, SCRIPTS)
import make_fixture  # noqa: E402
from search import number_pattern, term_pattern  # noqa: E402


def have_pdf_backend():
    if shutil.which("pdftotext"):
        return True
    if sys.platform == "darwin" and shutil.which("osascript"):
        return True
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


def run(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
    )


class SearchPatterns(unittest.TestCase):
    def test_numbers_match_whole_numbers_only(self):
        pattern = term_pattern("7.6", False)
        self.assertTrue(pattern.search("U-6 was 7.6 percent"))
        self.assertTrue(pattern.search("rose to 7.6%."))
        self.assertFalse(pattern.search("17.6"))
        self.assertFalse(pattern.search("7.65"))

    def test_thousands_separators_are_optional(self):
        pattern = term_pattern("40367", False)
        self.assertTrue(pattern.search("$40,367 million"))
        self.assertTrue(pattern.search("40367"))
        self.assertFalse(pattern.search("140,367"))
        self.assertTrue(term_pattern("1,000", False).search("per 1000 gallons"))

    def test_number_pattern_keeps_sign(self):
        self.assertIn("\\-", number_pattern("-0.4"))

    def test_words_cross_line_breaks_and_hyphenation(self):
        self.assertTrue(term_pattern("residential", False).search("the residen-\ntial class"))
        self.assertTrue(term_pattern("up from 39.8", False).search("up\nfrom 39.8"))


@unittest.skipUnless(have_pdf_backend(), "needs pdftotext or pypdf")
class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.pages = os.path.join(cls.tmp, "source.pages.txt")
        result = run("extract_pages.py", EXAMPLE_PDF, "-o", cls.pages)
        assert result.returncode == 0, result.stderr
        cls.summary = result.stderr
        with open(cls.pages, encoding="utf-8") as handle:
            cls.text = handle.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def check(self, claims):
        path = os.path.join(self.tmp, "claims.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"claims": claims}, handle)
        return run("check_quotes.py", self.pages, path)

    def test_extracts_every_page_with_markers(self):
        self.assertIn("3 page(s)", self.summary)
        for number in (1, 2, 3):
            self.assertIn(f"=== Page {number} ===", self.text)
        self.assertIn("Not seasonally adjusted", self.text)

    def test_printed_page_labels(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("page labels need pypdf")
        labeled = os.path.join(self.tmp, "labeled.pdf")
        with open(labeled, "wb") as handle:
            handle.write(make_fixture.build(page_labels=True))
        result = run("extract_pages.py", labeled)
        self.assertIn("=== Page 1 (printed: i) ===", result.stdout)
        self.assertIn("=== Page 3 (printed: 2) ===", result.stdout)

    def test_search_reports_pages(self):
        result = run("search.py", self.pages, "42.9", "residential")
        self.assertIn('"42.9": 2 hit(s) on page(s) 2, 3', result.stdout)
        self.assertIn('"residential": 2 hit(s) on page(s) 2, 3', result.stdout)

    def test_example_claims_pass(self):
        result = self.check([
            {"id": 1, "verdict": "contradicted", "page": 3, "quote": "Total ... 39.8 41.2 42.9"},
            {"id": 2, "verdict": "supported", "page": 2,
             "quote": "most of the increase came from the residential and industrial classes"},
            {"id": 3, "verdict": "supported", "page": 2,
             "quote": "\"We expect no rate change before the spring review,\" said Director Ana Ruiz"},
            {"id": 4, "verdict": "supported", "page": 1, "quote": "Quarterly Report - Third Quarter 2026"},
            {"id": 5, "verdict": "supported", "page": "2-3",
             "quote": "does not publish demand forecasts in this report … Table 2"},
            {"id": 6, "verdict": "can't check", "page": 9},
        ])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("5 PASS", result.stdout)

    def test_wrong_page_is_reported(self):
        result = self.check([{"id": 1, "verdict": "supported", "page": 2, "quote": "Industrial 6.4 7.0"}])
        self.assertEqual(result.returncode, 1)
        self.assertIn("WRONG PAGE", result.stdout)
        self.assertIn("found on p. 3", result.stdout)

    def test_invented_quote_is_not_found(self):
        result = self.check([{"id": 1, "verdict": "contradicted", "page": 2,
                              "quote": "base rate at $4.25 per 1,000 gallons"}])
        self.assertEqual(result.returncode, 1)
        self.assertIn("NOT FOUND", result.stdout)

    def test_pieces_must_share_a_page(self):
        result = self.check([{"id": 1, "verdict": "supported", "page": 2,
                              "quote": "Ana Ruiz ... Residential 22.4"}])
        self.assertIn("each piece is in the source, but not together on the cited page(s)", result.stdout)

    def test_cells_from_another_row_are_caught(self):
        result = self.check([
            {"id": 1, "verdict": "supported", "page": 3, "quote": "Commercial ... 7.0"},
            {"id": 2, "verdict": "supported", "page": 3, "quote": "Commercial ... 11.0 11.3"},
            {"id": 3, "verdict": "supported", "page": 3, "quote": "Commercial ... 7.0", "split_row": True},
        ])
        self.assertIn("#1 OTHER ROW", result.stdout)
        self.assertIn("#2 PASS", result.stdout)
        self.assertIn("#3 PASS", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_extra_pages_and_missing_pages_are_reported(self):
        result = self.check([
            {"id": 1, "verdict": "supported", "page": [1, 3], "quote": "Industrial 6.4 7.0"},
            {"id": 2, "verdict": "supported", "page": 9, "quote": "Industrial 6.4 7.0"},
            {"id": 3, "verdict": "supported", "page": "1-2",
             "quote": "Every number in it is made up. ... 1. Demand"},
        ])
        self.assertIn("#1 WRONG PAGE [supported]: the whole quote is on p. 3", result.stdout)
        self.assertIn("p. 9 doesn't exist (the source has 3 pages)", result.stdout)
        self.assertIn("#3 PASS", result.stdout)

    def test_help_exits_zero(self):
        result = run("check_quotes.py", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Results per claim", result.stdout)

    def test_supported_needs_a_quote(self):
        result = self.check([{"id": 1, "verdict": "Supported", "page": 2}])
        self.assertEqual(result.returncode, 1)
        self.assertIn("NO QUOTE", result.stdout)

    def test_not_in_source_reports_searched_terms_that_exist(self):
        result = self.check([
            {"id": 1, "verdict": "not_in_source", "searched": ["forecast", "drought"]},
            {"id": 2, "verdict": "not in source", "searched": ["drought"]},
            {"id": 3, "verdict": "not_in_source", "page": 2,
             "quote": "We expect no rate change before the spring review", "searched": ["cut"]},
            {"id": 4, "verdict": "not_in_source", "page": 2,
             "quote": "does not publish demand forecasts", "searched": ["forecast"]},
        ])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('#1 OK [not_in_source]: searched terms appear: "forecast" on p. 2', result.stdout)
        self.assertIn("#2 OK [not_in_source]: no searched term appears", result.stdout)
        self.assertIn("#3 PASS [not_in_source]: p. 2. no searched term appears", result.stdout)
        self.assertIn('#4 PASS [not_in_source]: p. 2. searched terms appear: "forecast"', result.stdout)

    def test_not_in_source_needs_searched_terms(self):
        result = self.check([{"id": 1, "verdict": "not_in_source"}])
        self.assertEqual(result.returncode, 1)
        self.assertIn("NO SEARCH", result.stdout)

    def test_unknown_verdict_is_rejected(self):
        result = self.check([{"id": 1, "verdict": "partly supported", "page": 3,
                              "quote": "Industrial 6.4 7.0"}])
        self.assertEqual(result.returncode, 1)
        self.assertIn("BAD VERDICT", result.stdout)

    def test_numbers_inside_longer_numbers_do_not_pass(self):
        result = self.check([
            {"id": 1, "verdict": "supported", "page": 3, "quote": "Total ... 1.2"},
            {"id": 2, "verdict": "supported", "page": 2, "quote": "$4.1"},
            {"id": 3, "verdict": "supported", "page": 3, "quote": "Commercial ... 11.01"},
            {"id": 4, "verdict": "supported", "page": 3, "quote": "Total 39.8 41.24"},
            {"id": 5, "verdict": "supported", "page": 3, "quote": "Total 39.8 41.2"},
        ])
        self.assertEqual(result.returncode, 1)
        for claim_id in (1, 2, 3, 4):
            self.assertIn(f"#{claim_id} NOT FOUND", result.stdout)
        self.assertIn("#5 PASS", result.stdout)


class TextSources(unittest.TestCase):
    def test_html_and_text_become_one_page(self):
        tmp = tempfile.mkdtemp()
        try:
            page = os.path.join(tmp, "page.html")
            with open(page, "w", encoding="utf-8") as handle:
                handle.write("<html><style>p{}</style><body><h1>Title</h1><p>Rate: 4.15</p></body></html>")
            result = run("extract_pages.py", page)
            self.assertIn("=== Page 1 ===", result.stdout)
            self.assertIn("Rate: 4.15", result.stdout)
            self.assertNotIn("p{}", result.stdout)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
