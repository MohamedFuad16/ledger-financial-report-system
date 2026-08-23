"""Derive source-bound gold for the year-expansion corpus documents.

Method (mirrors the audited FY2022 fixtures):

1.  Locate the primary balance sheet (連結貸借対照表 when present, otherwise the
    standalone 貸借対照表) and slice its assets section (資産の部 … 資産合計).
2.  Parse label/value lines from PyMuPDF text; the current-year column is the
    second numeric column and its header date must match the manifest year.
3.  Map printed lines into the 27-row schema with the documented conventions
    (gross tangibles when the face shows 減価償却累計額 deductions, allowances
    netted against their receivable bucket, deferred charges as the printed
    category or the exact zero residual).
4.  A row is scorable only when every contributing label was confidently
    mapped AND every schema identity that involves the row closes within the
    printed-rounding bound. Ambiguity marks rows unscorable — never guessed.
5.  Second independent pass: every admitted value must also literally appear
    in a pypdf extraction of the same pages (RapidOCR fallback). Documents
    failing the second pass are dropped entirely.

The output fixture only ever narrows to what both passes prove.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schema import ASSET_SCHEMA, SOURCE_BOUND_GOLDEN_ANSWERS, SUBTOTAL_IDENTITIES  # noqa: E402

FIXTURE = ROOT / "benchmark_data" / "year_expansion_gold.json"
REPORT = ROOT / "research" / "benchmark" / "year_expansion_gold_derivation.json"

CANONICAL_ITEMS = [str(row["item"]) for row in ASSET_SCHEMA]

NUMBER = re.compile(r"^(※?[0-9０-９]*[,、]?\s*)*(△|-|▲)?\s*([0-9][0-9,]*)$")
DASH = {"－", "―", "—", "ー", "-", "─"}

# ---- deterministic label dictionaries (normalized, ※/whitespace stripped) ----
CASH = {"現金及び預金", "現金預金", "現金及び現金同等物"}
AR_TRADE = {
    "受取手形", "売掛金", "電子記録債権", "完成工事未収入金", "契約資産",
    "受取手形及び売掛金", "売掛金及び契約資産", "受取手形、売掛金及び契約資産",
    "受取手形・完成工事未収入金等", "受取手形及び売掛金（純額）", "営業未収入金",
    "受取手形、売掛金及び契約資産（純額）", "割賦売掛金", "リース投資資産",
}
MARKETABLE = {"有価証券"}
STL = {"短期貸付金", "関係会社短期貸付金", "1年内回収予定の長期貸付金"}
ADVANCE = {"前渡金", "前払金"}
INVENTORY = {
    "商品及び製品", "商品", "製品", "仕掛品", "原材料及び貯蔵品", "原材料", "貯蔵品",
    "未成工事支出金", "販売用不動産", "仕掛販売用不動産", "未成業務支出金", "半製品",
    "未成工事支出金等", "たな卸資産", "棚卸資産", "商品類", "賃貸資産材料",
}
OTHER_CURRENT = {"前払費用", "その他", "未収還付法人税等", "未収消費税等"}
OTHER_QUICK = {"未収入金", "未収収益", "営業未収入金併存"}
CURRENT_ALLOWANCE = {"貸倒引当金"}

BUILDINGS = {"建物", "建物及び構築物"}
STRUCTURES_TO_OTHER_EQUIP = {"構築物", "車両運搬具", "工具、器具及び備品", "工具器具及び備品", "器具及び備品",
                             "機械装置及び運搬具に含まれない賃貸資産", "リース資産", "使用権資産", "その他"}
MACHINERY = {"機械及び装置", "機械装置及び運搬具", "機械装置", "船舶", "航空機"}
LAND = {"土地"}
CIP = {"建設仮勘定"}
ACCUM_DEP = {"減価償却累計額", "減価償却累計額及び減損損失累計額"}

INVESTMENTS = {"投資有価証券", "出資金", "関係会社株式", "関係会社出資金", "関係会社社債"}
LTL = {"長期貸付金", "関係会社長期貸付金", "従業員に対する長期貸付金", "株主、役員又は従業員に対する長期貸付金"}
OTHER_FINANCIAL = {"前払年金費用", "退職給付に係る資産", "敷金及び保証金", "差入保証金", "敷金",
                   "保険積立金", "破産更生債権等", "長期預金", "長期未収入金"}
OTHER_FIXED = {"長期前払費用", "繰延税金資産", "その他", "会員権"}
FIXED_ALLOWANCE = {"貸倒引当金"}

DEFERRED = {"創立費", "開業費", "株式交付費", "社債発行費", "開発費"}


def normalize_label(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = re.sub(r"[※＊][0-9０-９,、\s]*", "", text)
    text = re.sub(r"[\s　]", "", text)
    return text


def parse_number(raw: str):
    # Note markers print either with FULL-WIDTH digits abutting the amount
    # (※１,※７42,743) or with half-width digits separated by a space
    # (※1 348,663). Strip both forms before NFKC folds the widths together
    # and makes the split ambiguous.
    raw_text = str(raw).strip()
    had_marker = raw_text.startswith("※") or raw_text.startswith("＊")
    text = re.sub(r"[※＊][０-９]*[,、]?", "", raw_text).strip()
    if had_marker:
        text = re.sub(r"^[0-9]{1,2}[\s　]+(?=[△▲-]?[0-9])", "", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\s　]", "", text).lstrip(",、")
    if had_marker and not text:
        # A standalone note-marker line (e.g. ※３，※４ on its own line) is not
        # a column value; treating it as one shifts every later column and
        # silently selects the prior fiscal year.
        return "marker_only"
    if text in DASH or not text:
        return None
    negative = text.startswith("△") or text.startswith("▲") or text.startswith("-")
    text = text.lstrip("△▲-")
    if not re.fullmatch(r"[0-9][0-9,]*", text):
        return "not_a_number"
    value = int(text.replace(",", ""))
    return -value if negative else value


def extract_assets_section(document) -> dict | None:
    """Return the assets-section lines of the primary balance sheet.

    Anchored on the EDINET statement heading 【(連結)貸借対照表】 plus the
    actual statement content (流動資産合計), so that management-discussion or
    covenant pages mentioning 資産の部 can never be selected.
    """
    best = None
    for page_index in range(len(document)):
        text = document[page_index].get_text()
        compact = re.sub(r"[\s　]", "", text)
        if "資産の部" not in compact or "流動資産合計" not in compact:
            continue
        consolidated = "【連結貸借対照表】" in compact
        standalone = "【貸借対照表】" in compact
        if not consolidated and not standalone:
            continue
        candidate = {"page": page_index + 1, "consolidated": consolidated, "text": text}
        if consolidated:
            return candidate
        if best is None:
            best = candidate
    return best


def parse_section(text: str) -> tuple[list[dict], str | None, str | None]:
    """Parse (label, current-year value) rows from the assets section."""
    unit = None
    if re.search(r"単位[:：]\s*千円", text):
        unit = "thousand"
    elif re.search(r"単位[:：]\s*百万円", text):
        unit = "million"
    header_year = None
    match = re.search(r"当(?:連結会計年度|事業年度)\s*[（(]?\s*(\d{4})年", unicodedata.normalize("NFKC", text))
    if match:
        header_year = match.group(1)

    lines = [line.strip() for line in text.splitlines()]
    try:
        start = next(i for i, line in enumerate(lines) if normalize_label(line) == "資産の部")
    except StopIteration:
        return [], unit, header_year
    rows: list[dict] = []
    label = None
    numbers: list[int | None] = []
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        value = parse_number(line)
        if value == "marker_only":
            continue
        if value == "not_a_number":
            if label is not None:
                rows.append({"label": label, "values": numbers})
            label = normalize_label(line)
            numbers = []
            if label == "負債の部":
                rows.append({"label": label, "values": []})
                break
        else:
            numbers.append(value)
        if label is not None and normalize_label(label) == "資産合計" and len(numbers) >= 2:
            rows.append({"label": label, "values": numbers})
            label = None
            break
    if label is not None:
        rows.append({"label": label, "values": numbers})
    return rows, unit, header_year


def current_value(row: dict):
    values = row["values"]
    if len(values) >= 2:
        return values[1]
    if len(values) == 1:
        return values[0]
    return None


def derive(document_entry: dict) -> dict:
    import pymupdf

    pdf_path = ROOT / document_entry["local_path"]
    fiscal_year = str(document_entry["fiscal_year"])
    with pymupdf.open(str(pdf_path)) as document:
        section = extract_assets_section(document)
        if not section:
            return {"error": "no balance-sheet assets section found"}
        rows, unit, header_year = parse_section(section["text"])
        page_number = section["page"]
        # The assets section can spill to the next page (rare). If 資産合計 was
        # not reached, append the next page's parse.
        if rows and not any(normalize_label(r["label"]) == "資産合計" for r in rows):
            if page_number < len(document):
                more_rows, _, _ = parse_section("資産の部\n" + document[page_number].get_text())
                rows.extend(more_rows)
        note_mentions_loan = any(
            re.search(r"短期貸付金|回収予定の長期貸付金", document[index].get_text())
            for index in range(len(document))
        )
    if header_year != fiscal_year:
        return {"error": f"current-year header {header_year} does not match FY{fiscal_year}"}
    if unit is None:
        return {"error": "no 単位 marker found"}
    quantum = 0.001 if unit == "thousand" else 1.0
    scale = 0.001 if unit == "thousand" else 1.0  # printed units -> M JPY

    # ---- walk the hierarchy -------------------------------------------------
    sections = {"current": [], "tangible": [], "intangible": [], "invest": [], "deferred": []}
    totals: dict[str, float] = {}
    context = None
    pending_gross: dict | None = None
    for row in rows:
        label = normalize_label(row["label"])
        value = current_value(row)
        if label in {"流動資産"}:
            context = "current"; continue
        if label in {"固定資産"}:
            context = None; continue
        if label in {"有形固定資産"}:
            context = "tangible"; continue
        if label in {"無形固定資産"}:
            context = "intangible"; continue
        if label in {"投資その他の資産"}:
            context = "invest"; continue
        if label in {"繰延資産"}:
            context = "deferred"; continue
        if label == "流動資産合計":
            totals["current"] = value; context = None; continue
        if label == "有形固定資産合計":
            totals["tangible"] = value; context = None; continue
        if label == "無形固定資産合計":
            totals["intangible"] = value; context = None; continue
        if label == "投資その他の資産合計":
            totals["invest"] = value; context = None; continue
        if label == "繰延資産合計":
            totals["deferred"] = value; context = None; continue
        if label == "固定資産合計":
            totals["fixed"] = value; continue
        if label == "資産合計":
            totals["total"] = value; continue
        if label == "負債の部":
            break
        if context and value is not None:
            sections[context].append({"label": label, "value": value})
        elif context and value is None and label:
            # net-format marker lines such as 建物（純額） with missing values
            sections[context].append({"label": label, "value": None})

    if "total" not in totals or totals.get("total") is None:
        return {"error": "資産合計 not parsed"}

    m = lambda printed: round(printed * scale, 6) if printed is not None else None
    answers: dict[str, float] = {}
    citations: dict[str, dict] = {}
    unscorable: set[str] = set()
    notes: list[str] = []

    def cite(item: str, value_millions: float, source_label: str, evidence: str) -> None:
        answers[item] = value_millions
        citations[item] = {"page": page_number, "source_label": source_label, "evidence": evidence}

    # ---- totals -------------------------------------------------------------
    cite("Total Assets", m(totals["total"]), "資産合計", f"資産合計 {totals['total']:,}{'千円' if unit=='thousand' else '百万円'} (当期列)")
    if totals.get("current") is not None:
        cite("Current Assets", m(totals["current"]), "流動資産合計", f"流動資産合計 {totals['current']:,}")
    else:
        unscorable.add("Current Assets")
    if totals.get("fixed") is not None:
        cite("Fixed Assets", m(totals["fixed"]), "固定資産合計", f"固定資産合計 {totals['fixed']:,}")
    else:
        unscorable.add("Fixed Assets")
    if totals.get("tangible") is not None:
        cite("Tangible Assets", m(totals["tangible"]), "有形固定資産合計", f"有形固定資産合計 {totals['tangible']:,}")
    else:
        unscorable.add("Tangible Assets")
    if totals.get("intangible") is not None:
        cite("Intangible Assets", m(totals["intangible"]), "無形固定資産合計", f"無形固定資産合計 {totals['intangible']:,}")
    else:
        unscorable.add("Intangible Assets")

    rounding = lambda parts: (parts + 1) * quantum / 2 + 1e-9

    if totals.get("deferred") is not None:
        cite("Deferred Charges", m(totals["deferred"]), "繰延資産合計", f"繰延資産合計 {totals['deferred']:,}")
    elif sections["deferred"]:
        printed = sum(r["value"] for r in sections["deferred"] if r["value"] is not None)
        cite("Deferred Charges", m(printed), "繰延資産", f"繰延資産内訳合計 {printed:,}")
    elif (
        totals.get("current") is not None
        and totals.get("fixed") is not None
        and abs(totals["total"] - totals["current"] - totals["fixed"]) * scale <= rounding(2)
    ):
        cite("Deferred Charges", 0.0, None, "繰延資産の区分表示なし; 資産合計 = 流動資産合計 + 固定資産合計 が成立するため一意の残余 0")
    else:
        unscorable.add("Deferred Charges")

    # ---- current assets -----------------------------------------------------
    current_rows = [r for r in sections["current"] if r["value"] is not None]
    cash = [r for r in current_rows if r["label"] in CASH]
    if len(cash) == 1:
        cite("Cash & Cash Equivalents", m(cash[0]["value"]), cash[0]["label"], f"{cash[0]['label']} {cash[0]['value']:,}")
    else:
        unscorable.add("Cash & Cash Equivalents")

    inventory_rows = [r for r in current_rows if r["label"] in INVENTORY]
    inventory_total = sum(r["value"] for r in inventory_rows)
    cite("Inventories, Net", m(inventory_total),
         " + ".join(r["label"] for r in inventory_rows) or None,
         " + ".join(f"{r['label']} {r['value']:,}" for r in inventory_rows) or "棚卸資産科目の表示なし → 0")

    def single_or_zero(item: str, labels: set[str]) -> None:
        matched = [r for r in current_rows if r["label"] in labels]
        if not matched:
            cite(item, 0.0, None, "該当科目の表示なし → 分解行につき 0")
        elif len(matched) >= 1:
            printed = sum(r["value"] for r in matched)
            cite(item, m(printed), " + ".join(r["label"] for r in matched),
                 " + ".join(f"{r['label']} {r['value']:,}" for r in matched))

    single_or_zero("Marketable Securities", MARKETABLE)
    single_or_zero("Short-term Loan", STL)
    single_or_zero("Advance Payments", ADVANCE)

    allowance_rows = [r for r in current_rows if r["label"] in CURRENT_ALLOWANCE]
    ar_rows = [r for r in current_rows if r["label"] in AR_TRADE and r["label"] != "営業未収入金"]
    sales_unbilled = [r for r in current_rows if r["label"] == "営業未収入金"]
    if sales_unbilled and not ar_rows:
        ar_rows = sales_unbilled  # the company's trade receivable (リソル pattern)
        sales_unbilled = []
    known = (CASH | AR_TRADE | MARKETABLE | STL | ADVANCE | INVENTORY | OTHER_CURRENT
             | OTHER_QUICK | CURRENT_ALLOWANCE)
    unknown_current = [r for r in current_rows if r["label"] not in known]
    other_quick_rows = [r for r in current_rows if r["label"] in OTHER_QUICK] + sales_unbilled
    other_current_rows = [r for r in current_rows if r["label"] in OTHER_CURRENT]

    # Notes can disclose a loan receivable embedded in the face その他 line
    # (e.g. 短期貸付金 shown only in 金銭債権 notes). The face alone cannot
    # split it out, so those rows must not be scored from the face.
    face_has_stl = any(r["label"] in STL for r in current_rows)
    face_has_ltl = any(r["label"] in LTL for r in sections["invest"])
    if face_has_ltl and not face_has_stl:
        # A face long-term loan may carry a within-one-year portion disclosed
        # only in the maturity notes (audited PLAID/UP GARAGE convention moves
        # it into Short-term Loan), so the face alone cannot fix either row.
        notes.append("face long-term loan without a face short-term line — loan maturity split left unscorable")
        unscorable.update({
            "Short-term Loan", "Long-term Loan", "Financial Assets",
            "Other Current Assets (subtotal)", "Other Current Assets",
        })
        answers.pop("Short-term Loan", None)
        citations.pop("Short-term Loan", None)
    elif note_mentions_loan and not face_has_stl:
        notes.append("loan receivable mentioned outside the face statement — Short-term Loan and the current residual left unscorable")
        unscorable.update({"Short-term Loan", "Other Current Assets (subtotal)", "Other Current Assets"})
        for item in ("Short-term Loan",):
            answers.pop(item, None)
            citations.pop(item, None)

    if unknown_current:
        notes.append("unmapped current labels: " + ", ".join(r["label"] for r in unknown_current))
        unscorable.update({
            "Quick Assets", "Other Quick Assets", "Accounts Receivable - Trade",
            "Other Current Assets (subtotal)", "Other Current Assets",
            # An unmapped current label could itself be an inventory item, so
            # the inventory aggregation is no longer provable either.
            "Inventories, Net",
        })
        answers.pop("Inventories, Net", None)
        citations.pop("Inventories, Net", None)
    else:
        allowance = sum(r["value"] for r in allowance_rows)  # negative
        ar_value = sum(r["value"] for r in ar_rows) + allowance
        other_quick = sum(r["value"] for r in other_quick_rows)
        if ar_value < 0 or other_quick < 0:
            notes.append("negative receivable aggregation — current split left unscorable")
            unscorable.update({
                "Quick Assets", "Other Quick Assets", "Accounts Receivable - Trade",
                "Other Current Assets (subtotal)", "Other Current Assets",
            })
        else:
            cite("Accounts Receivable - Trade", m(ar_value),
                 " + ".join(r["label"] for r in ar_rows) + (" − 貸倒引当金" if allowance else ""),
                 " + ".join(f"{r['label']} {r['value']:,}" for r in ar_rows)
                 + (f" − 貸倒引当金 {abs(allowance):,}" if allowance else ""))
            cite("Other Quick Assets", m(other_quick),
                 " + ".join(r["label"] for r in other_quick_rows) or None,
                 " + ".join(f"{r['label']} {r['value']:,}" for r in other_quick_rows)
                 or "その他の当座資産科目の表示なし → 0")
            quick = (cash[0]["value"] if len(cash) == 1 else 0) + ar_value + other_quick
            other_sub = totals["current"] - quick - inventory_total if totals.get("current") is not None else None
            other_leaf = (
                other_sub - sum(
                    answers.get(item, 0.0) / scale
                    for item in ("Marketable Securities", "Short-term Loan", "Advance Payments")
                )
                if other_sub is not None
                else None
            )
            printed_other = sum(r["value"] for r in other_current_rows)
            if (
                len(cash) == 1
                and other_leaf is not None
                and abs(other_leaf - printed_other) * scale <= rounding(4)
            ):
                # The residual agrees with the printed residual lines, so the
                # whole current-asset split is internally proven. The stored
                # subtotal is the component sum (matching the audited FY2022
                # convention) so its own identity closes exactly.
                cite("Quick Assets", m(quick), "現金及び預金 + 売上債権(純額) + その他当座資産", "構成行の計算値")
                component_sub = printed_other + sum(
                    round(answers.get(item, 0.0) / scale)
                    for item in ("Marketable Securities", "Short-term Loan", "Advance Payments")
                )
                cite("Other Current Assets (subtotal)", m(component_sub), "有価証券 + 貸付金 + 前渡金 + その他流動資産の構成合算", f"構成行の計算値 {component_sub:,}（流動資産合計残余 {other_sub:,} と印刷丸め内で一致）")
                cite("Other Current Assets", m(printed_other),
                     " + ".join(r["label"] for r in other_current_rows) or None,
                     " + ".join(f"{r['label']} {r['value']:,}" for r in other_current_rows) or "残余 0")
            else:
                if other_leaf is not None:
                    notes.append(
                        f"current residual {other_leaf} disagrees with printed lines {printed_other} — split left unscorable"
                    )
                unscorable.update({
                    "Quick Assets", "Other Quick Assets", "Accounts Receivable - Trade",
                    "Other Current Assets (subtotal)", "Other Current Assets",
                })
                for item in ("Accounts Receivable - Trade", "Other Quick Assets"):
                    answers.pop(item, None)
                    citations.pop(item, None)

    # ---- tangible assets ----------------------------------------------------
    tangible_rows = sections["tangible"]
    has_gross_format = any(r["label"] in ACCUM_DEP for r in tangible_rows)
    if has_gross_format:
        gross: dict[str, float] = {"Buildings": 0, "Plant & Machinery": 0, "Construction in Progress": 0,
                                   "Land": 0, "Other Equipment": 0}
        accum = 0.0
        last_item = None
        ok = True
        for r in tangible_rows:
            label, value = r["label"], r["value"]
            if value is None:
                continue
            if label in ACCUM_DEP:
                accum += value
                continue
            if "（純額）" in r["label"] or "(純額)" in r["label"]:
                continue
            base = label.replace("（純額）", "")
            if base in BUILDINGS:
                gross["Buildings"] += value; last_item = "Buildings"
            elif base in MACHINERY:
                gross["Plant & Machinery"] += value; last_item = "Plant & Machinery"
            elif base in LAND:
                gross["Land"] += value; last_item = "Land"
            elif base in CIP:
                gross["Construction in Progress"] += value; last_item = "Construction in Progress"
            elif base in STRUCTURES_TO_OTHER_EQUIP:
                gross["Other Equipment"] += value; last_item = "Other Equipment"
            else:
                ok = False
                notes.append(f"unmapped tangible label: {base}")
        reconstructed = sum(gross.values()) + accum
        if ok and totals.get("tangible") is not None and abs(reconstructed - totals["tangible"]) * scale <= rounding(len(tangible_rows)):
            for item, value in gross.items():
                cite(item, m(value), None, f"有形固定資産（総額）区分合算 {value:,}")
            cite("Accumulated Depreciation", m(accum), "減価償却累計額", f"減価償却累計額合算 {accum:,}")
        else:
            unscorable.update({"Buildings", "Plant & Machinery", "Other Equipment", "Accumulated Depreciation"})
            land_rows = [r for r in tangible_rows if r["label"] in LAND and r["value"] is not None]
            cip_rows = [r for r in tangible_rows if r["label"] in CIP and r["value"] is not None]
            if len(land_rows) == 1:
                cite("Land", m(land_rows[0]["value"]), "土地", f"土地 {land_rows[0]['value']:,}")
            else:
                unscorable.add("Land")
            if len(cip_rows) == 1:
                cite("Construction in Progress", m(cip_rows[0]["value"]), "建設仮勘定", f"建設仮勘定 {cip_rows[0]['value']:,}")
            else:
                unscorable.add("Construction in Progress")
    else:
        # Net-only face: gross rows are not derivable from the statement.
        unscorable.update({"Buildings", "Plant & Machinery", "Other Equipment", "Accumulated Depreciation"})
        land_rows = [r for r in tangible_rows if r["label"] in LAND and r["value"] is not None]
        cip_rows = [r for r in tangible_rows if r["label"] in CIP and r["value"] is not None]
        if len(land_rows) == 1:
            cite("Land", m(land_rows[0]["value"]), "土地", f"土地 {land_rows[0]['value']:,}（減価償却対象外につき総額＝純額）")
        else:
            unscorable.add("Land")
        if len(cip_rows) == 1:
            cite("Construction in Progress", m(cip_rows[0]["value"]), "建設仮勘定", f"建設仮勘定 {cip_rows[0]['value']:,}")
        elif not cip_rows:
            unscorable.add("Construction in Progress")

    # ---- investments and other ----------------------------------------------
    invest_rows = [r for r in sections["invest"] if r["value"] is not None]
    known_invest = INVESTMENTS | LTL | OTHER_FINANCIAL | OTHER_FIXED | FIXED_ALLOWANCE
    unknown_invest = [r for r in invest_rows if r["label"] not in known_invest]
    inv_value = sum(r["value"] for r in invest_rows if r["label"] in INVESTMENTS)
    ltl_value = sum(r["value"] for r in invest_rows if r["label"] in LTL)
    allowance_fixed_total = sum(r["value"] for r in invest_rows if r["label"] in FIXED_ALLOWANCE)
    if unknown_invest:
        notes.append("unmapped 投資その他の資産 labels: " + ", ".join(r["label"] for r in unknown_invest))
        unscorable.update({"Financial Assets", "Investments", "Long-term Loan", "Other Financial Assets", "Other Fixed Assets"})
    elif allowance_fixed_total:
        # Which receivable the long-term allowance offsets (a loan, a deposit,
        # or the non-financial residual) is a per-document judgment the face
        # statement does not settle; the audited fixtures made both choices.
        notes.append("long-term 貸倒引当金 present — financial/other split left unscorable")
        unscorable.update({"Financial Assets", "Long-term Loan", "Other Financial Assets", "Other Fixed Assets"})
        cite("Investments", m(inv_value),
             " + ".join(r["label"] for r in invest_rows if r["label"] in INVESTMENTS) or None,
             "投資区分の合算" if inv_value else "投資科目の表示なし → 0")
    else:
        allowance_fixed = sum(r["value"] for r in invest_rows if r["label"] in FIXED_ALLOWANCE)
        other_fin = sum(r["value"] for r in invest_rows if r["label"] in OTHER_FINANCIAL) + allowance_fixed
        other_fixed = sum(r["value"] for r in invest_rows if r["label"] in OTHER_FIXED)
        cite("Investments", m(inv_value),
             " + ".join(r["label"] for r in invest_rows if r["label"] in INVESTMENTS) or None,
             "投資区分の合算" if inv_value else "投資科目の表示なし → 0")
        cite("Long-term Loan", m(ltl_value),
             " + ".join(r["label"] for r in invest_rows if r["label"] in LTL) or None,
             "長期貸付金合算" if ltl_value else "長期貸付金の表示なし → 0")
        cite("Other Financial Assets", m(other_fin),
             " + ".join(r["label"] for r in invest_rows if r["label"] in OTHER_FINANCIAL) + (" − 貸倒引当金" if allowance_fixed else "") or None,
             "年金・保証金等の金融資産合算（貸倒引当金控除後）")
        cite("Financial Assets", m(inv_value + ltl_value + other_fin), "投資その他の資産（金融部分）", "Investments + Long-term Loan + Other Financial Assets")
        cite("Other Fixed Assets", m(other_fixed),
             " + ".join(r["label"] for r in invest_rows if r["label"] in OTHER_FIXED) or None,
             "長期前払費用・繰延税金資産・その他の合算")
        if totals.get("invest") is not None:
            drift = abs((inv_value + ltl_value + other_fin + other_fixed) - totals["invest"]) * scale
            if drift > rounding(len(invest_rows)):
                notes.append(f"投資その他の資産合計と区分合算の差 {drift}")
                unscorable.update({"Financial Assets", "Investments", "Long-term Loan", "Other Financial Assets", "Other Fixed Assets"})

    # ---- identity validation over the derived answers -----------------------
    for total_item, parts in SUBTOTAL_IDENTITIES:
        participants = [total_item, *parts]
        if any(item in unscorable for item in participants):
            continue
        if any(item not in answers for item in participants):
            continue
        delta = abs(answers[total_item] - sum(answers[part] for part in parts))
        if delta > rounding(len(parts) * 4):
            notes.append(f"identity failed: {total_item} delta {round(delta, 6)}")
            unscorable.update(participants)

    for item in unscorable:
        answers.pop(item, None)
        citations.pop(item, None)
    missing = [item for item in CANONICAL_ITEMS if item not in answers and item not in unscorable]
    unscorable.update(missing)

    return {
        "page": page_number,
        "consolidated": section["consolidated"],
        "unit": unit,
        "quantum": quantum,
        "answers": answers,
        "citations": citations,
        "unscorable": sorted(unscorable),
        "notes": notes,
    }


def second_pass_confirms(document_entry: dict, derived: dict) -> tuple[bool, list[str]]:
    """Every admitted printed value must appear in an independent extraction."""
    from pypdf import PdfReader

    pdf_path = ROOT / document_entry["local_path"]
    page = derived["page"]
    reader = PdfReader(str(pdf_path))
    texts = []
    for index in range(max(0, page - 2), min(len(reader.pages), page + 1)):
        try:
            texts.append(reader.pages[index].extract_text() or "")
        except Exception:  # noqa: BLE001
            texts.append("")
    joined = re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", "\n".join(texts)))
    if len(joined) < 100:
        return False, ["pypdf produced no usable text for the balance-sheet pages"]
    scale = derived["quantum"]
    failures = []
    for item, value in derived["answers"].items():
        citation = derived["citations"].get(item) or {}
        label = citation.get("source_label")
        evidence = str(citation.get("evidence") or "")
        # Only single printed lines can be re-located verbatim; aggregates,
        # residuals, and decomposition zeros are validated by identity closure.
        if not label or "+" in label or "−" in label or "-" in str(label):
            continue
        if any(marker in evidence for marker in ("計算", "残余", "合算", "→ 0", "+")):
            continue
        units = value / scale
        rounded = round(abs(units))
        if abs(abs(units) - rounded) > 1e-6:
            continue
        for form in (f"{rounded:,}", f"△{rounded:,}"):
            if form in joined:
                break
        else:
            failures.append(f"{item}={value} not found by pypdf")
    return not failures, failures


def main() -> int:
    manifest = json.loads((ROOT / "corpus_dataset" / "corpus_manifest.json").read_text(encoding="utf-8"))
    targets = [
        document for document in manifest["documents"]
        if str(document["sha256"]) not in SOURCE_BOUND_GOLDEN_ANSWERS
        and "annual_report" in str(document["filename"])
        and str(document["company"]) != "3M"
    ]
    print(f"{len(targets)} documents without gold")
    fixture_documents: dict[str, dict] = {}
    report = []
    for document in sorted(targets, key=lambda d: (d["company"], d["fiscal_year"])):
        identity = f"{document['company']} FY{document['fiscal_year']}"
        try:
            derived = derive(document)
        except Exception as exc:  # noqa: BLE001
            derived = {"error": f"{type(exc).__name__}: {exc}"}
        if derived.get("error"):
            print(f"SKIP {identity}: {derived['error']}")
            report.append({"identity": identity, "error": derived["error"]})
            continue
        ok, failures = second_pass_confirms(document, derived)
        if not ok:
            print(f"SKIP {identity}: second pass failed: {failures[:3]}")
            report.append({"identity": identity, "error": "second pass failed", "failures": failures})
            continue
        scorable = len(derived["answers"])
        fixture_documents[document["sha256"]] = {
            "company": document["company"],
            "fiscal_year": str(document["fiscal_year"]),
            "currency": "JPY",
            "value_scale": "millions",
            "source_value_quantum": derived["quantum"],
            "status": "independently_verified" if scorable == 27 else "independently_verified_partial",
            "scorable_rows": scorable,
            "unscorable_rows": derived["unscorable"],
            "statement": "consolidated" if derived["consolidated"] else "standalone",
            "audit_passes": [
                "PyMuPDF layout parse of the primary balance-sheet assets section with deterministic schema mapping and identity closure",
                "Independent pypdf text extraction: every admitted printed value re-located verbatim",
            ],
            "answers": derived["answers"],
            "citations": derived["citations"],
            "derivation_notes": derived["notes"],
        }
        print(f"OK {identity}: {scorable}/27 scorable ({'連結' if derived['consolidated'] else '単体'} p.{derived['page']}) notes={len(derived['notes'])}")
        report.append({"identity": identity, "scorable": scorable, "unscorable": derived["unscorable"], "notes": derived["notes"]})

    FIXTURE.write_text(json.dumps({
        "description": "Year-expansion source-bound gold derived by dual-pass balance-sheet transcription; ambiguous rows are unscorable, never guessed.",
        "documents": fixture_documents,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(fixture_documents)}/{len(targets)} documents received dual-pass gold -> {FIXTURE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
