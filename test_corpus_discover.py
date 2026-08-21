import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from corpus.client import FirecrawlClient, FirecrawlRateGate
from corpus.discover import discover_company_reports


class _FakeFirecrawl:
    def __init__(self):
        self.map_search = ""
        self.query = ""

    def map(self, _url, *, search):
        self.map_search = search
        return []

    def search(self, query, *, limit, country):
        self.query = query
        self.assertions = (limit, country)
        return [{
            "url": "https://example.jp/ir/library/yuho_2024.pdf",
            "title": "2024年12月期 有価証券報告書",
            "description": "",
        }]

    def scrape_links(self, _url):
        return []


class JapaneseCorpusDiscoveryTests(unittest.TestCase):
    def test_shared_rate_gate_spaces_requests_and_honors_cooldown(self):
        now = [0.0]
        sleeps: list[float] = []

        def sleep(seconds: float) -> None:
            sleeps.append(seconds)
            now[0] += seconds

        gate = FirecrawlRateGate(7.0, clock=lambda: now[0], sleeper=sleep)
        self.assertEqual(0.0, gate.wait())
        self.assertEqual(7.0, gate.wait())
        gate.defer(10.0)
        self.assertEqual(10.0, gate.wait())
        self.assertEqual([7.0, 10.0], sleeps)

    def test_file_backed_gate_coordinates_multiple_worker_instances(self):
        now = [100.0]
        sleeps: list[float] = []

        def sleep(seconds: float) -> None:
            sleeps.append(seconds)
            now[0] += seconds

        with TemporaryDirectory() as directory:
            state_path = Path(directory) / "firecrawl-rate"
            first = FirecrawlRateGate(12.5, clock=lambda: now[0], sleeper=sleep, state_path=state_path)
            second = FirecrawlRateGate(12.5, clock=lambda: now[0], sleeper=sleep, state_path=state_path)
            self.assertEqual(0.0, first.wait())
            self.assertEqual(12.5, second.wait())
            first.defer(9.0)
            self.assertEqual(12.5, second.wait())
            self.assertEqual([12.5, 12.5], sleeps)

    def test_scraped_anchor_inherits_nearest_year_heading(self):
        client = object.__new__(FirecrawlClient)
        client._post = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
            "data": {
                "markdown": "2024年12月期(第13期)\n[有価証券報告書](https://cdn.example/S100VI2R.pdf)",
                "links": [],
            },
        }
        links = client.scrape_links("https://example.jp/ir/library/")
        self.assertEqual("2024 有価証券報告書", links[0]["title"])

    def test_japanese_ir_vocabulary_is_discovered(self):
        client = _FakeFirecrawl()
        reports = discover_company_reports(
            client,
            company="Example株式会社",
            official_url="https://example.jp/",
            country="JP",
            years=[2024],
        )

        self.assertIn("有価証券報告書", client.map_search)
        self.assertIn("有価証券報告書", client.query)
        self.assertEqual("JP", client.assertions[1])
        self.assertEqual(1, len(reports[2024]))
        self.assertEqual("https://example.jp/ir/library/yuho_2024.pdf", reports[2024][0].url)
        self.assertTrue(reports[2024][0].source_verified)

    def test_unrelated_search_result_is_rejected(self):
        class UnrelatedSearch(_FakeFirecrawl):
            def search(self, query, *, limit, country):
                return [{
                    "url": "https://unrelated.example/filings/annual_report_2024.pdf",
                    "title": "2024 Annual Report",
                    "description": "",
                }]

        reports = discover_company_reports(
            UnrelatedSearch(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2024],
        )
        self.assertEqual([], reports[2024])

    def test_official_map_may_delegate_pdf_to_verified_cdn(self):
        class CdnMap(_FakeFirecrawl):
            def map(self, _url, *, search):
                return [{
                    "url": "https://disclosure-cdn.example/yuho_2024.pdf",
                    "title": "2024年12月期 有価証券報告書",
                    "description": "",
                }]

            def search(self, query, *, limit, country):
                raise AssertionError("map candidate should satisfy the requested year")

        reports = discover_company_reports(
            CdnMap(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2024],
        )
        self.assertEqual(1, len(reports[2024]))
        self.assertEqual("map", reports[2024][0].discovery)
        self.assertTrue(reports[2024][0].source_verified)

    def test_official_page_anchor_can_verify_a_disclosure_cdn(self):
        class PageLinks(_FakeFirecrawl):
            def scrape_links(self, _url):
                return [{
                    "url": "https://data.cdn.example/report_20250328.pdf",
                    "title": "2024年12月期 有価証券報告書",
                    "description": "",
                }]

            def search(self, query, *, limit, country):
                raise AssertionError("official page anchor should satisfy the year")

        reports = discover_company_reports(
            PageLinks(), company="Example株式会社",
            official_url="https://example.jp/ir/library/", country="JP", years=[2024],
        )
        self.assertEqual(1, len(reports[2024]))
        self.assertEqual("page", reports[2024][0].discovery)
        self.assertTrue(reports[2024][0].source_verified)


if __name__ == "__main__":
    unittest.main()
