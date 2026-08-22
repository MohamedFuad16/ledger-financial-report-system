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
        self.assertIn("filetype:pdf", client.query)
        self.assertEqual(50, client.assertions[0])
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

    def test_exact_issuer_edinet_search_result_is_trusted(self):
        class EdinetSearch(_FakeFirecrawl):
            def search(self, query, *, limit, country):
                return [{
                    "url": "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100TEST.pdf",
                    "title": "Example株式会社 有価証券報告書 2024年12月期",
                    "description": "",
                }]

        reports = discover_company_reports(
            EdinetSearch(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2024],
        )
        self.assertEqual(1, len(reports[2024]))
        self.assertTrue(reports[2024][0].source_verified)

    def test_parent_company_edinet_result_is_rejected(self):
        class ParentEdinetSearch(_FakeFirecrawl):
            def search(self, query, *, limit, country):
                return [{
                    "url": "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100PARENT.pdf",
                    "title": "Parent Holdings株式会社 有価証券報告書 2024年12月期",
                    "description": "",
                }]

        reports = discover_company_reports(
            ParentEdinetSearch(), company="Example株式会社",
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

    def test_year_stamped_official_pdf_without_report_language_is_rejected(self):
        class NewsRelease(_FakeFirecrawl):
            def map(self, _url, *, search):
                return [{
                    "url": "https://example.jp/news/release_2022.pdf",
                    "title": "2022 新サービスのお知らせ",
                    "description": "",
                }]

            def scrape_links(self, _url):
                return []

            def search(self, query, *, limit, country):
                return []

        reports = discover_company_reports(
            NewsRelease(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2022],
        )
        self.assertEqual([], reports[2022])

    def test_quarterly_filing_is_not_an_annual_report(self):
        class QuarterlySearch(_FakeFirecrawl):
            def search(self, query, *, limit, country):
                return [{
                    "url": "https://example.jp/ir/2022_q1.pdf",
                    "title": "2022年3月期 第1四半期決算短信",
                    "description": "有価証券報告書ライブラリ",
                }]

        reports = discover_company_reports(
            QuarterlySearch(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2022],
        )
        self.assertEqual([], reports[2022])

    def test_one_result_is_assigned_to_only_its_primary_year(self):
        class ComparativeSnippet(_FakeFirecrawl):
            def search(self, query, *, limit, country):
                return [{
                    "url": "https://example.jp/ir/annual_report.pdf",
                    "title": "2022年3月期 有価証券報告書",
                    "description": "2021年との比較情報",
                }]

        reports = discover_company_reports(
            ComparativeSnippet(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2021, 2022],
        )
        self.assertEqual([], reports[2021])
        self.assertEqual(1, len(reports[2022]))

    def test_comparative_year_still_receives_a_deep_retry(self):
        class ComparativeDeep(_FakeFirecrawl):
            def __init__(self):
                super().__init__()
                self.queries = []

            def search(self, query, *, limit, country):
                self.queries.append(query)
                if query == '"Example株式会社" 有価証券報告書 filetype:pdf':
                    return [{
                        "url": "https://example.jp/ir/report_2022.pdf",
                        "title": "2022年3月期 有価証券報告書",
                        "description": "2021年比較",
                    }]
                if 'FY2021' in query:
                    return [{
                        "url": "https://example.jp/ir/report_2021.pdf",
                        "title": "2021 Annual Report",
                        "description": "",
                    }]
                return []

        client = ComparativeDeep()
        reports = discover_company_reports(
            client, company="Example株式会社", official_url="https://example.jp/",
            country="JP", years=[2021, 2022], deep_search=True,
        )
        self.assertEqual(1, len(reports[2021]))
        self.assertEqual(1, len(reports[2022]))

    def test_future_reporting_period_is_not_relabelled_as_requested_year(self):
        class FuturePeriod(_FakeFirecrawl):
            def search(self, query, *, limit, country):
                return [{
                    "url": "https://example.jp/ir/annual_report.pdf",
                    "title": "有価証券報告書 第62期 (2025/04/01-2026/03/31)",
                    "description": "",
                }]

        reports = discover_company_reports(
            FuturePeriod(), company="Example株式会社",
            official_url="https://example.jp/", country="JP", years=[2025],
        )
        self.assertEqual([], reports[2025])

    def test_deep_search_retries_each_missing_year_with_broader_queries(self):
        class DeepSearch(_FakeFirecrawl):
            def __init__(self):
                super().__init__()
                self.queries = []

            def search(self, query, *, limit, country):
                self.queries.append((query, limit, country))
                if "FY2023" in query:
                    return [{
                        "url": "https://example.jp/ir/annual_report_2023.pdf",
                        "title": "2023 Annual Report",
                        "description": "Example株式会社",
                    }]
                return []

        client = DeepSearch()
        reports = discover_company_reports(
            client, company="Example株式会社", official_url="https://example.jp/",
            country="JP", years=[2023], deep_search=True,
        )

        self.assertEqual(3, len(client.queries))
        self.assertTrue(any("FY2023" in query for query, _, _ in client.queries))
        self.assertEqual(1, len(reports[2023]))


if __name__ == "__main__":
    unittest.main()
