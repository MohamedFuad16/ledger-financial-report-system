import unittest

from corpus.screen import _balance_sheet_page, _year_mentions


class JapaneseCorpusScreenTests(unittest.TestCase):
    def test_japanese_business_period_confirms_fiscal_year(self):
        text = "【事業年度】 第13期 (自 2024年１月１日　至 2024年12月31日)"
        self.assertIn("2024", _year_mentions(text))

    def test_japanese_balance_sheet_is_located(self):
        text = """--- PAGE 70 ---
貸借対照表
流動資産 100
現金及び預金 50
棚卸資産 10
資産合計 500
負債合計 250
--- PAGE 71 ---
注記事項
"""
        self.assertEqual(70, _balance_sheet_page(text))


if __name__ == "__main__":
    unittest.main()
