import unittest

from corpus.screen import (
    _balance_sheet_page,
    _statement_currency,
    _statement_years,
    _year_mentions,
)


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

    def test_japanese_construction_statement_terms_are_located(self):
        text = """--- PAGE 53 ---
連結貸借対照表
流動資産 113,270
現金預金 29,015
未成工事支出金 6,577
資産合計 301,599
--- PAGE 54 ---
負債の部
"""
        self.assertEqual(53, _balance_sheet_page(text))

    def test_statement_currency_ignores_foreign_currency_notes(self):
        text = """--- PAGE 132 ---
CONSOLIDATED STATEMENT OF FINANCIAL POSITION
Yen in millions
Assets
Current assets 23,722,290
Cash and cash equivalents 6,113,655
Inventories 3,821,356
Total assets 67,688,771
--- PAGE 200 ---
U.S. dollars in millions
"""
        self.assertEqual("JPY", _statement_currency(text, 132))

    def test_annual_report_with_quarterly_cross_reference_is_still_annual(self):
        from corpus.screen import _is_annual_document

        annual = (
            "【表紙】\n【提出書類】\n有価証券報告書\n【根拠条文】\n金融商品取引法第24条第１項\n"
            "【会社名】\nテスト株式会社\n"
            "……当社は四半期報告書を関東財務局長に提出しています。\n"
        )
        quarterly = (
            "【表紙】\n【提出書類】\n四 半 期 報 告 書\n【根拠条文】\n金融商品取引法第24条の４の７第１項\n"
            "【会社名】\nテスト株式会社\n"
        )
        self.assertTrue(_is_annual_document(annual))
        self.assertFalse(_is_annual_document(quarterly))

    def test_statement_year_uses_current_not_comparative_year(self):
        text = """--- PAGE 5 ---
連結貸借対照表
2022年3月31日 2021年3月31日
流動資産 100
現金及び預金 50
棚卸資産 10
資産合計 500
負債合計 250
"""
        self.assertEqual([2021, 2022], _statement_years(text, 5))


if __name__ == "__main__":
    unittest.main()
