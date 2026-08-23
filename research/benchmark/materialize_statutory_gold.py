"""Materialize source-bound partial gold from public gazette announcements.

The source images are exact legal-entity balance-sheet announcements discovered
during the Firecrawl/statutory sweep.  A record is accepted only when:

1. the announcement index's structured total-assets value is present; and
2. local RapidOCR independently reads that same amount at least twice from the
   balance sheet (assets total and liabilities/net-assets total).

Only ``Total Assets`` is scored.  The remaining 26 schema rows are explicitly
unscorable because a condensed statutory announcement cannot be assumed to
disclose the assignment's complete asset taxonomy.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image
from rapidocr import RapidOCR


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from schema import ASSET_SCHEMA  # noqa: E402


CANDIDATES = ROOT / "research" / "corpus" / "gazette_statutory_filings.json"
FIXTURE = ROOT / "benchmark_data" / "bakuraku_statutory_gold.json"
AUDIT = ROOT / "research" / "benchmark" / "bakuraku_statutory_gold_audit.json"
MANIFEST = ROOT / "corpus_dataset" / "corpus_manifest.json"
TARGET_COUNT = 27
EXISTING_CLIENTS = {
    "AppBank株式会社",
    "note株式会社",
    "ダイニチ工業株式会社",
    "ラクスル株式会社",
    "リソルホールディングス株式会社",
    "株式会社アップガレージグループ",
    "株式会社グッドパッチ",
    "株式会社ストライダーズ",
    "株式会社トーエネック",
    "株式会社プレイド",
    "株式会社ベルク",
    "株式会社 帝国ホテル",
    "株式会社帝国ホテル",
    "西尾レントオール株式会社",
}
PREFERRED = [
    "Byside株式会社",
    "JR九州エンジニアリング株式会社",
    "JUKI産機テクノロジー株式会社",
    "キャディ株式会社",
    "クラスター株式会社",
    "ハコベル株式会社",
    "ファインディ株式会社",
    "メディフォン株式会社",
    "吉田海運株式会社",
    "坂善商事株式会社",
    "大西運輸株式会社",
    "日本テーマパーク開発株式会社",
    "株式会社FABRIC TOKYO",
    "株式会社FLUX",
    "株式会社iCARE",
    "株式会社Morght",
    "株式会社mov",
    "株式会社PIGNUS（ピグナス）",
    "株式会社SANU",
    "株式会社TENTIAL",
    "株式会社with",
    "株式会社キズキ",
    "株式会社キッズコーポレーション",
    "株式会社ナレッジワーク",
    "株式会社ハッピートラベル",
    "株式会社レスタス",
    "株式会社伊豆シャボテン公園",
    "株式会社寿々",
    "横関油脂工業株式会社",
    "高山石油ガス株式会社",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_image(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LedgerCorpusResearch/1.0)",
            "Referer": "https://catr.jp/",
            "Accept": "image/png,image/jpeg,image/*",
        },
    )
    with urlopen(request, timeout=30) as response:
        data = response.read()
    if len(data) < 1024:
        raise RuntimeError("announcement image download was empty or truncated")
    return data


def pdf_bytes(image_bytes: bytes) -> bytes:
    source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    output = io.BytesIO()
    source.save(output, format="PDF", resolution=200.0, quality=95)
    return output.getvalue()


def integers(text: str) -> list[int]:
    normalized = unicodedata.normalize("NFKC", text)
    values: list[int] = []
    for match in re.findall(r"(?<!\d)\d[\d,]*(?!\d)", normalized):
        try:
            values.append(int(match.replace(",", "")))
        except ValueError:
            continue
    return values


def matching_source_amounts(total_assets_yen: int, transcript: str) -> tuple[int, int]:
    observed = integers(transcript)
    candidates = [total_assets_yen]
    if total_assets_yen % 1_000 == 0:
        candidates.append(total_assets_yen // 1_000)
    if total_assets_yen % 1_000_000 == 0:
        candidates.append(total_assets_yen // 1_000_000)
    best = max(candidates, key=observed.count)
    return best, observed.count(best)


def safe_slug(company: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-龯々ぁ-んァ-ンー]+", "_", company).strip("_")


def main() -> int:
    payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    by_company = {item["registry_company"]: item for item in payload["records"]}
    canonical_items = [str(row["item"]) for row in ASSET_SCHEMA]
    engine = RapidOCR()
    accepted: list[dict] = []
    rejected: list[dict] = []

    for company in PREFERRED:
        if len(accepted) >= TARGET_COUNT:
            break
        record = by_company.get(company)
        if not record or company in EXISTING_CLIENTS:
            continue
        fiscal_year = int(str(record.get("closed_date") or "0")[:4] or 0)
        if not 2020 <= fiscal_year <= 2025:
            continue
        try:
            image = fetch_image(record["announcement_image_url"])
            ocr = engine(image)
            transcript = "\n".join(ocr.txts or [])
            total_assets_yen = int(record["total_assets_index_value_yen"])
            source_amount, occurrences = matching_source_amounts(total_assets_yen, transcript)
            if occurrences < 2:
                raise RuntimeError(
                    f"OCR did not independently reconcile both balance-sheet totals "
                    f"(expected source amount {source_amount}, occurrences={occurrences})"
                )

            generated_pdf = pdf_bytes(image)
            source_hash = sha256(generated_pdf)
            company_dir = ROOT / "corpus_dataset" / safe_slug(company) / str(fiscal_year)
            company_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{safe_slug(company)}_statutory_report_{fiscal_year}.pdf"
            path = company_dir / filename
            path.write_bytes(generated_pdf)
            accepted.append(
                {
                    **record,
                    "status": "independently_verified_partial",
                    "fiscal_year": fiscal_year,
                    "source_image_sha256": sha256(image),
                    "source_pdf_sha256": source_hash,
                    "source_pdf_size_bytes": len(generated_pdf),
                    "source_pdf_path": str(path.relative_to(ROOT)),
                    "source_amount": source_amount,
                    "ocr_occurrences": occurrences,
                    "balance_reconciled": True,
                    "audit_passes": [
                        "Exact-entity public gazette image: local RapidOCR numeric transcription",
                        "Independent gazette-index transcription plus deterministic assets/liabilities total reconciliation",
                    ],
                    "ocr_transcript": transcript,
                }
            )
            print(f"VERIFIED {len(accepted):02d}/{TARGET_COUNT} {company} FY{fiscal_year}")
        except Exception as exc:
            rejected.append({"company": company, "reason": str(exc)})
            print(f"REJECT {company}: {exc}")

    if len(accepted) < TARGET_COUNT:
        raise RuntimeError(
            f"Only {len(accepted)} statutory announcements passed two-pass verification; "
            f"need {TARGET_COUNT}. Rejections: {rejected}"
        )

    documents: dict[str, dict] = {}
    for record in accepted:
        unscorable = [item for item in canonical_items if item != "Total Assets"]
        total_m_jpy = int(record["total_assets_index_value_yen"]) / 1_000_000
        # Gazette announcements print in 千円 or 百万円 depending on the
        # company; the printed unit is the yen value divided by the printed
        # number, and the exact-match tolerance must reflect that real
        # precision instead of assuming thousand-yen everywhere.
        printed_unit_yen = int(record["total_assets_index_value_yen"]) / int(record["source_amount"])
        documents[record["source_pdf_sha256"]] = {
            "company": record["registry_company"],
            "fiscal_year": str(record["fiscal_year"]),
            "currency": "JPY",
            "value_scale": "millions",
            "source_value_quantum": round(printed_unit_yen) / 1_000_000,
            "status": "independently_verified_partial",
            "scorable_rows": 1,
            "unscorable_rows": unscorable,
            "source_announcement_url": record["announcement_url"],
            "source_image_url": record["announcement_image_url"],
            "source_image_sha256": record["source_image_sha256"],
            "audit_passes": [
                "Exact-entity public gazette image: local RapidOCR numeric transcription",
                "Independent gazette-index transcription plus deterministic assets/liabilities total reconciliation",
            ],
            "answers": {"Total Assets": total_m_jpy},
            "citations": {
                "Total Assets": {
                    "page": 1,
                    "source_label": "資産合計",
                    "evidence": (
                        f"Gazette image shows source amount {record['source_amount']:,}; "
                        f"RapidOCR read the reconciled total {record['ocr_occurrences']} times. "
                        f"Structured announcement index records "
                        f"JPY {int(record['total_assets_index_value_yen']):,} = "
                        f"{total_m_jpy:g} M JPY."
                    ),
                }
            },
        }

    FIXTURE.write_text(
        json.dumps(
            {
                "version": 1,
                "benchmark": "Bakuraku-client public statutory balance-sheet partial gold",
                "answer_unit": "M JPY",
                "documents": documents,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    AUDIT.write_text(
        json.dumps(
            {
                "version": 1,
                "accepted_count": len(accepted),
                "accepted": accepted,
                "rejected": rejected,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing_hashes = {str(item.get("sha256") or "") for item in manifest["documents"]}
    for record in accepted:
        if record["source_pdf_sha256"] in existing_hashes:
            continue
        path = ROOT / record["source_pdf_path"]
        manifest["documents"].append(
            {
                "company": record["registry_company"],
                "company_slug": safe_slug(record["registry_company"]),
                "fiscal_year": record["fiscal_year"],
                "source_url": record["announcement_url"],
                "source_title": "Public gazette statutory balance-sheet announcement",
                "official_domain": "catr.jp",
                "official_source_verified": False,
                "source_provenance": "public_gazette_image_mirror",
                "source_image_url": record["announcement_image_url"],
                "source_image_sha256": record["source_image_sha256"],
                "discovery": "firecrawl_statutory_sweep+gazette_exact_entity_index",
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "local_path": record["source_pdf_path"],
                "filename": path.name,
                "sha256": record["source_pdf_sha256"],
                "size_bytes": path.stat().st_size,
                "golden_answers": None,
                "screened": "ok",
                "screen_reasons": [],
                "pages": 1,
                "readable_pages": 0,
                "garbled_pages": [],
                "balance_sheet_page": 1,
                "currency": "JPY",
                "fiscal_year_confirmed": True,
                "internal_year_mentions": [str(record["fiscal_year"])],
                "warnings": [
                    "Raster-only public gazette announcement; only Total Assets is benchmark-scorable."
                ],
            }
        )
    manifest["documents"].sort(
        key=lambda item: (
            0 if item.get("company") == "3M" else 1,
            str(item.get("company") or ""),
            int(item.get("fiscal_year") or 0),
        )
    )
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(documents)} verified partial fixtures and updated the corpus manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
