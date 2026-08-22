"""Materialize the twice-audited Bakuraku FY2022 benchmark fixture.

The listed Strategy 3 runs were navigation aids only. Their rows were checked
once against the exact source PDF with Poppler ``pdftotext -layout`` and again
against PyMuPDF's embedded-text extraction plus deterministic schema
reconciliation. Model confidence is never used as an approval criterion.

Resol omits three gross consolidated PPE categories from its filing. Those rows
are removed rather than inferred from net categories and aggregate depreciation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline import load_prediction  # noqa: E402


OUTPUT = ROOT / "benchmark_data" / "bakuraku_fy2022_gold.json"

AUDITED_RUNS = {
    "AppBank株式会社": "S3_20260822T102508Z_001",
    "note株式会社": "S3_20260822T102704Z_002",
    "ダイニチ工業株式会社": "S3_20260822T102905Z_003",
    "ラクスル株式会社": "S3_20260822T103120Z_004",
    "リソルホールディングス株式会社": "S3_20260822T103318Z_005",
    "株式会社グッドパッチ": "S3_20260822T103557Z_006",
    "株式会社ストライダーズ": "S3_20260822T103803Z_007",
    "株式会社プレイド": "S3_20260822T104021Z_008",
    "株式会社ベルク": "S3_20260822T104214Z_009",
    "株式会社帝国ホテル": "S3_20260822T104406Z_010",
}

OMITTED_UNDISCLOSED = {
    "リソルホールディングス株式会社": {
        "Buildings",
        "Plant & Machinery",
        "Other Equipment",
    }
}

# Source-audited corrections where the navigation run used a semantically
# plausible but wrong schema bucket. Under Japanese presentation,
# 長期前払費用 belongs to investments/other assets; only 繰延資産 maps to the
# separate Deferred Charges schema row.
AUDITED_OVERRIDES = {
    "ダイニチ工業株式会社": {
        "Fixed Assets": 9922.370,
        "Other Fixed Assets": 168.076,
        "Deferred Charges": 0.0,
    },
    "ラクスル株式会社": {
        "Fixed Assets": 8973.0,
        "Other Fixed Assets": 1321.0,
        "Deferred Charges": 0.0,
    },
    "リソルホールディングス株式会社": {
        "Financial Assets": 3370.911,
        "Investments": 23.526,
        "Other Fixed Assets": 1802.534,
    },
    "株式会社ストライダーズ": {
        "Financial Assets": 327.367,
        "Investments": 327.557,
        "Other Financial Assets": -0.190,
        "Other Fixed Assets": 77.006,
    },
    "株式会社プレイド": {
        "Short-term Loan": 2.156,
        "Other Current Assets": 195.670,
    },
}

SOURCE_VALUE_QUANTUM = {
    "AppBank株式会社": 0.001,
    "note株式会社": 0.001,
    "ダイニチ工業株式会社": 0.001,
    "ラクスル株式会社": 1.0,
    "リソルホールディングス株式会社": 0.001,
    "株式会社グッドパッチ": 0.001,
    "株式会社ストライダーズ": 0.001,
    "株式会社プレイド": 0.001,
    "株式会社ベルク": 1.0,
    "株式会社帝国ホテル": 1.0,
}

AUDITED_CITATION_OVERRIDES = {
    "ダイニチ工業株式会社": {
        "Fixed Assets": {"page": 34, "source_label": "固定資産合計", "evidence": "9,922,370千円"},
        "Other Fixed Assets": {
            "page": 34,
            "source_label": "長期前払費用 + 繰延税金資産 + その他 − 貸倒引当金",
            "evidence": "10,767 + 144,040 + 13,269 = 168,076千円; allowance is assigned to the financial receivable bucket",
        },
        "Deferred Charges": {"page": 34, "source_label": "繰延資産なし", "evidence": "No separate 繰延資産 category is presented"},
    },
    "ラクスル株式会社": {
        "Fixed Assets": {"page": 65, "source_label": "固定資産合計", "evidence": "8,973百万円"},
        "Other Fixed Assets": {
            "page": 65,
            "source_label": "長期前払費用 + 繰延税金資産 + その他",
            "evidence": "202 + 968 + 151 = 1,321百万円",
        },
        "Deferred Charges": {"page": 65, "source_label": "繰延資産なし", "evidence": "No separate 繰延資産 category is presented"},
    },
    "リソルホールディングス株式会社": {
        "Financial Assets": {"page": 72, "source_label": "投資有価証券 + 出資金 + 差入保証金", "evidence": "311 + 23,215 + 3,347,385 = 3,370,911千円"},
        "Investments": {"page": 72, "source_label": "投資有価証券 + 出資金", "evidence": "311 + 23,215 = 23,526千円"},
        "Other Fixed Assets": {"page": 48, "source_label": "繰延税金資産 + その他（純額）− 出資金", "evidence": "1,304,735 + 521,014 − 23,215 = 1,802,534千円"},
    },
    "株式会社ストライダーズ": {
        "Financial Assets": {"page": 42, "source_label": "投資有価証券 + 関係会社株式 + 貸倒引当金", "evidence": "256,941 + 70,616 − 190 = 327,367千円"},
        "Investments": {"page": 42, "source_label": "投資有価証券 + 関係会社株式", "evidence": "256,941 + 70,616 = 327,557千円"},
        "Other Financial Assets": {"page": 42, "source_label": "貸倒引当金（投資その他の資産）", "evidence": "−190千円"},
        "Other Fixed Assets": {"page": 42, "source_label": "繰延税金資産 + その他", "evidence": "8,182 + 68,824 = 77,006千円"},
    },
    "株式会社プレイド": {
        "Short-term Loan": {"page": 84, "source_label": "従業員に対する長期貸付金の1年以内償還予定", "evidence": "2,156千円"},
        "Other Current Assets": {"page": 64, "source_label": "その他 − 短期貸付金", "evidence": "197,826 − 2,156 = 195,670千円"},
    },
}


def materialize() -> dict:
    documents: dict[str, dict] = {}
    for company, run_id in AUDITED_RUNS.items():
        prediction = load_prediction(run_id)
        if not prediction:
            raise RuntimeError(f"Audited run is missing: {run_id}")
        if prediction.get("company") != company or prediction.get("currency") != "JPY":
            raise RuntimeError(f"Identity/unit mismatch in {run_id}")
        omitted = OMITTED_UNDISCLOSED.get(company, set())
        rows = [row for row in prediction["rows"] if row["item"] not in omitted]
        overrides = AUDITED_OVERRIDES.get(company, {})
        citation_overrides = AUDITED_CITATION_OVERRIDES.get(company, {})
        source_hash = str(prediction["source_pdf_sha256"])
        documents[source_hash] = {
            "company": company,
            "fiscal_year": "2022",
            "currency": "JPY",
            "value_scale": "millions",
            "source_value_quantum": SOURCE_VALUE_QUANTUM[company],
            "status": "independently_verified",
            "scorable_rows": len(rows),
            "unscorable_rows": sorted(omitted),
            "candidate_navigation_run": run_id,
            "audit_passes": [
                "Poppler pdftotext -layout inspection of cited PDF pages",
                "PyMuPDF embedded-text inspection plus deterministic schema reconciliation",
            ],
            "answers": {
                row["item"]: overrides.get(row["item"], row["answer_m_usd"])
                for row in rows
            },
            "citations": {
                row["item"]: citation_overrides.get(row["item"], {
                    "page": row.get("source_page"),
                    "source_label": row.get("source_label"),
                    "evidence": row.get("evidence"),
                })
                for row in rows
            },
        }
    return {
        "version": 1,
        "benchmark": "Bakuraku customer FY2022 native-currency asset schema",
        "answer_unit": "M JPY",
        "documents": documents,
    }


if __name__ == "__main__":
    payload = materialize()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['documents'])} audited documents to {OUTPUT}")
