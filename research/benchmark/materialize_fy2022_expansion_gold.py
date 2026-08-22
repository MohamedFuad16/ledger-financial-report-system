"""Materialize five twice-audited FY2022 source-bound gold documents.

The Strategy 3 outputs named below were navigation aids only. Every retained
number was checked independently with Poppler ``pdftotext -layout`` and
PyMuPDF embedded-text extraction, then reconciled to the 27-row asset schema.
Where a filing combines categories that the schema splits, the affected rows
are omitted and named in ``unscorable_rows`` instead of being inferred.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "benchmark_data" / "fy2022_expansion_gold.json"

ROWS = [
    "Current Assets", "Quick Assets", "Cash & Cash Equivalents",
    "Accounts Receivable - Trade", "Other Quick Assets", "Inventories, Net",
    "Other Current Assets (subtotal)", "Marketable Securities", "Short-term Loan",
    "Advance Payments", "Other Current Assets", "Fixed Assets", "Tangible Assets",
    "Land", "Buildings", "Plant & Machinery", "Construction in Progress",
    "Other Equipment", "Accumulated Depreciation", "Intangible Assets",
    "Financial Assets", "Investments", "Long-term Loan", "Other Financial Assets",
    "Other Fixed Assets", "Deferred Charges", "Total Assets",
]


def citations(page: int, answers: dict[str, float], labels: dict[str, tuple[int, str, str]] | None = None) -> dict:
    labels = labels or {}
    return {
        item: {
            "page": labels.get(item, (page, item, "Twice checked against the cited consolidated filing page."))[0],
            "source_label": labels.get(item, (page, item, ""))[1],
            "evidence": labels.get(item, (page, "", "Twice checked against the cited consolidated filing page."))[2],
        }
        for item in answers
    }


def document(*, company: str, source_hash: str, run: str, quantum: float,
             page: int, answers: dict[str, float], omitted: set[str],
             labels: dict[str, tuple[int, str, str]] | None = None) -> tuple[str, dict]:
    if set(answers).intersection(omitted) or set(answers).union(omitted) != set(ROWS):
        raise ValueError(f"{company}: answers and omissions must partition all 27 rows")
    return source_hash, {
        "company": company,
        "fiscal_year": "2022",
        "currency": "JPY",
        "value_scale": "millions",
        "source_value_quantum": quantum,
        "status": "independently_verified" if not omitted else "independently_verified_partial",
        "scorable_rows": len(answers),
        "unscorable_rows": sorted(omitted),
        "candidate_navigation_run": run,
        "audit_passes": [
            "Poppler pdftotext -layout inspection of cited PDF pages",
            "PyMuPDF embedded-text inspection plus deterministic schema reconciliation",
        ],
        "answers": answers,
        "citations": citations(page, answers, labels),
    }


def materialize() -> dict:
    docs = dict([
        document(
            company="株式会社アップガレージグループ",
            source_hash="dc12bdf4b79485a558b6b04573f1cea34d0c11c062c06d6369523e3ed621e5d5",
            run="S3_20260822T134033Z_001", quantum=0.001, page=52, omitted=set(),
            answers={
                "Current Assets": 3535.891, "Quick Assets": 2850.076,
                "Cash & Cash Equivalents": 2074.588, "Accounts Receivable - Trade": 775.488,
                "Other Quick Assets": 0.0, "Inventories, Net": 555.258,
                "Other Current Assets (subtotal)": 130.555, "Marketable Securities": 0.0,
                "Short-term Loan": 7.207, "Advance Payments": 0.0,
                "Other Current Assets": 123.348, "Fixed Assets": 1802.282,
                "Tangible Assets": 907.489, "Land": 167.908, "Buildings": 988.710,
                "Plant & Machinery": 269.446, "Construction in Progress": 0.0,
                "Other Equipment": 391.752, "Accumulated Depreciation": -910.328,
                "Intangible Assets": 301.763, "Financial Assets": 508.118,
                "Investments": 18.936, "Long-term Loan": 167.800,
                "Other Financial Assets": 321.382, "Other Fixed Assets": 84.911,
                "Deferred Charges": 0.0, "Total Assets": 5338.173,
            },
            labels={
                "Short-term Loan": (66, "長期貸付金（1年以内）", "7,207千円 is contractually collectible within one year."),
                "Long-term Loan": (52, "長期貸付金", "167,800千円 is the non-current balance-sheet line."),
                "Other Equipment": (52, "工具器具備品 + リース資産", "329,074 + 62,678 = 391,752千円, before depreciation."),
                "Other Current Assets": (52, "その他 − 1年内回収予定長期貸付金", "130,555 − 7,207 = 123,348千円."),
            },
        ),
        document(
            company="株式会社トーエネック",
            source_hash="0a90950a2a311e44f18c570c9a1ab749a14a4ce5aa9763113d5268de80309b57",
            run="S3_20260822T134033Z_002", quantum=1.0, page=53,
            omitted={"Plant & Machinery", "Other Equipment", "Financial Assets", "Other Financial Assets", "Other Fixed Assets"},
            answers={
                "Current Assets": 113270.0, "Quick Assets": 99946.0,
                "Cash & Cash Equivalents": 29015.0, "Accounts Receivable - Trade": 69431.0,
                "Other Quick Assets": 1500.0, "Inventories, Net": 9865.0,
                "Other Current Assets (subtotal)": 3458.0, "Marketable Securities": 0.0,
                "Short-term Loan": 0.0, "Advance Payments": 0.0,
                "Other Current Assets": 3458.0, "Fixed Assets": 188328.0,
                "Tangible Assets": 145891.0, "Land": 31633.0, "Buildings": 58341.0,
                "Construction in Progress": 9634.0, "Accumulated Depreciation": -67373.0,
                "Intangible Assets": 4047.0, "Investments": 28877.0, "Long-term Loan": 15.0,
                "Deferred Charges": 0.0, "Total Assets": 301599.0,
            },
            labels={
                "Accounts Receivable - Trade": (53, "受取手形・完成工事未収入金等 − 貸倒引当金", "69,521 − 90 = 69,431百万円."),
                "Inventories, Net": (53, "未成工事支出金 + 材料貯蔵品 + 商品", "6,577 + 3,177 + 111 = 9,865百万円."),
                "Tangible Assets": (53, "有形固定資産合計", "145,891百万円 is directly disclosed; machinery and equipment are not split further."),
            },
        ),
        document(
            company="西尾レントオール株式会社",
            source_hash="fdf47701b4bb1704792dc3b320d7fe5bb0bf6e88ba89675dc820ea61e6fdff60",
            run="S3_20260822T134033Z_003", quantum=1.0, page=49,
            omitted={"Buildings", "Plant & Machinery", "Other Equipment", "Financial Assets", "Other Financial Assets", "Other Fixed Assets"},
            answers={
                "Current Assets": 105927.0, "Quick Assets": 89555.0,
                "Cash & Cash Equivalents": 47695.0, "Accounts Receivable - Trade": 41841.0,
                "Other Quick Assets": 19.0, "Inventories, Net": 6261.0,
                "Other Current Assets (subtotal)": 10107.0, "Marketable Securities": 0.0,
                "Short-term Loan": 0.0, "Advance Payments": 0.0,
                "Other Current Assets": 10107.0, "Fixed Assets": 155771.0,
                "Tangible Assets": 143825.0, "Land": 36516.0,
                "Construction in Progress": 5205.0, "Accumulated Depreciation": -181555.0,
                "Intangible Assets": 3547.0,
                "Investments": 2148.0, "Long-term Loan": 12.0,
                "Deferred Charges": 0.0, "Total Assets": 261699.0,
            },
            labels={
                "Accounts Receivable - Trade": (49, "受取手形、売掛金及び契約資産 − 貸倒引当金", "42,743 − 902 = 41,841百万円; page 63 confirms contract assets are zero."),
                "Inventories, Net": (49, "商品製品 + 仕掛品 + 原材料貯蔵品", "3,897 + 897 + 1,467 = 6,261百万円."),
                "Tangible Assets": (49, "有形固定資産合計", "143,825百万円 is directly disclosed; component classes are presented net."),
                "Accumulated Depreciation": (63, "有形固定資産減価償却累計額", "181,555百万円; the separate 34,097 line is leased assets included in rental assets, not depreciation."),
            },
        ),
        document(
            company="トヨタ自動車株式会社",
            source_hash="860863a86954f71d530d6efcb23695af09598fb8abba76ca31c9406c64f2e50c",
            run="S3_20260822T134304Z_004", quantum=1.0, page=132, omitted=set(),
            answers={
                "Current Assets": 23722290.0, "Quick Assets": 9256487.0,
                "Cash & Cash Equivalents": 6113655.0, "Accounts Receivable - Trade": 2426274.0,
                "Other Quick Assets": 716558.0, "Inventories, Net": 3821356.0,
                "Other Current Assets (subtotal)": 10644447.0, "Marketable Securities": 2507248.0,
                "Short-term Loan": 7181327.0, "Advance Payments": 0.0,
                "Other Current Assets": 955872.0, "Fixed Assets": 43966482.0,
                "Tangible Assets": 12775052.0, "Land": 1361791.0, "Buildings": 5284620.0,
                "Plant & Machinery": 13982362.0, "Construction in Progress": 565528.0,
                "Other Equipment": 7229641.0, "Accumulated Depreciation": -15648890.0,
                "Intangible Assets": 1191966.0, "Financial Assets": 28938292.0,
                "Investments": 4837895.0, "Long-term Loan": 14583130.0,
                "Other Financial Assets": 9517267.0, "Other Fixed Assets": 1061170.0,
                "Deferred Charges": 0.0, "Total Assets": 67688771.0,
            },
            labels={
                "Accounts Receivable - Trade": (161, "Accounts and notes receivables − allowance", "2,466,398 − 40,124 = 2,426,274 million yen."),
                "Other Quick Assets": (161, "Other receivables", "716,558 million yen."),
                "Marketable Securities": (164, "Other financial assets — current", "2,507,248 million yen; current financial instruments are assigned to the schema's tradable-financial bucket."),
                "Short-term Loan": (132, "Receivables related to financial services — current", "7,181,327 million yen."),
                "Other Equipment": (132, "Vehicles/equipment on operating leases + right-of-use assets", "6,781,229 + 448,412 = 7,229,641 million yen."),
            },
        ),
        document(
            company="ソニーグループ株式会社",
            source_hash="262c03e67a52e35033c248743db381a49530fd4833ca66aea3b7d457a8bcd441",
            run="S3_20260822T134338Z_005", quantum=1.0, page=111,
            omitted={"Quick Assets", "Accounts Receivable - Trade", "Other Quick Assets", "Plant & Machinery", "Other Equipment", "Investments", "Long-term Loan", "Other Financial Assets"},
            answers={
                "Current Assets": 5535208.0, "Cash & Cash Equivalents": 2049636.0,
                "Inventories, Net": 874007.0,
                "Other Current Assets (subtotal)": 983044.0, "Marketable Securities": 149301.0,
                "Short-term Loan": 360673.0, "Advance Payments": 0.0,
                "Other Current Assets": 473070.0, "Fixed Assets": 24945759.0,
                "Tangible Assets": 1526643.0, "Land": 78160.0, "Buildings": 832785.0,
                "Construction in Progress": 145940.0, "Accumulated Depreciation": -1897657.0,
                "Intangible Assets": 2745044.0, "Financial Assets": 19409907.0,
                "Other Fixed Assets": 1264165.0, "Deferred Charges": 0.0,
                "Total Assets": 30480967.0,
            },
            labels={
                "Tangible Assets": (111, "有形固定資産 + 使用権資産", "1,113,213 + 413,430 = 1,526,643百万円."),
                "Land": (174, "土地（取得原価）", "78,160百万円."),
                "Buildings": (174, "建物及び構築物（取得原価）", "832,785百万円."),
                "Construction in Progress": (174, "建設仮勘定（取得原価）", "145,940百万円."),
                "Accumulated Depreciation": (174, "減価償却累計額及び減損損失累計額", "−1,897,657百万円."),
                "Intangible Assets": (111, "のれん + コンテンツ資産 + その他無形", "952,895 + 1,342,046 + 450,103 = 2,745,044百万円."),
                "Financial Assets": (111, "持分法投資 + 金融分野投資貸付 + その他金融", "268,513 + 18,445,088 + 696,306 = 19,409,907百万円; child split is not scored."),
            },
        ),
    ])
    return {
        "version": 1,
        "benchmark": "FY2022 native-currency asset-schema expansion: three customer issuers plus two public controls",
        "answer_unit": "M JPY",
        "documents": docs,
    }


if __name__ == "__main__":
    payload = materialize()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['documents'])} audited documents to {OUTPUT}")
