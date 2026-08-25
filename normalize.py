"""
Repair layer: messy LLM reply → the shape the contract expects.

This is deliberately separate from `models.py`. The contract states what a valid
reply looks like; this module makes a best effort to turn a nearly-valid reply
into one, and **reports every change it made** so the repairs are visible in the
run record rather than hidden inside validation.

Anything this module cannot fix is left alone, so the contract still rejects it.
Nothing here computes, infers or scores a value — it only fixes representation
(number formatting, item spelling, row order).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from models import CANONICAL_ITEMS

# Tokens a model may emit instead of a number when a field is absent.
_NULL_TOKENS = {
    "",
    "-",
    "--",
    "—",
    "–",
    "n/a",
    "na",
    "n.a.",
    "none",
    "null",
    "nil",
    "not found",
    "not disclosed",
    "not applicable",
    "not presented",
}

# Item-name variants seen from models, keyed by normalized form.
_ITEM_ALIASES: dict[str, str] = {
    "other current assets subtotal": "Other Current Assets (subtotal)",
    "other current assets total": "Other Current Assets (subtotal)",
    "subtotal other current assets": "Other Current Assets (subtotal)",
    "total other current assets": "Other Current Assets (subtotal)",
    "accounts receivable trade": "Accounts Receivable - Trade",
    "accounts receivable": "Accounts Receivable - Trade",
    "trade receivables": "Accounts Receivable - Trade",
    "cash and cash equivalents": "Cash & Cash Equivalents",
    "cash cash equivalents": "Cash & Cash Equivalents",
    "inventories net": "Inventories, Net",
    "inventories": "Inventories, Net",
    "plant and machinery": "Plant & Machinery",
    "plant machinery": "Plant & Machinery",
    "machinery and equipment": "Plant & Machinery",
    "less accumulated depreciation": "Accumulated Depreciation",
    "short term loan": "Short-term Loan",
    "long term loan": "Long-term Loan",
    "construction in process": "Construction in Progress",
}


def _fold(name: Any) -> str:
    text = unicodedata.normalize("NFKC", str(name or "")).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_BY_FOLDED: dict[str, str] = {_fold(item): item for item in CANONICAL_ITEMS}
for _alias, _target in _ITEM_ALIASES.items():
    _BY_FOLDED.setdefault(_fold(_alias), _target)


def canonical_item(name: Any) -> str | None:
    """Canonical schema name for ``name``, or None if it is not recognizable."""
    return _BY_FOLDED.get(_fold(name))


def parse_money(value: Any) -> Any:
    """
    Turn a monetary cell into a float, or None, or return it unchanged.

    Handles "1,234", "$1,234", "(16,820)", unicode minus and null-ish words.
    A value that cannot be read is returned **as-is** so the contract rejects it
    rather than this module inventing something.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return value

    text = unicodedata.normalize("NFKC", value).strip()
    if text.lower() in _NULL_TOKENS:
        return None

    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace("−", "-")
    text = re.sub(r"[$¥€£,\s]", "", text)
    text = re.sub(r"(?i)(usd|mm|millions|million|m)$", "", text).strip()

    if text in {"", "-", "+"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return value
    return -number if negative else number


def parse_confidence(value: Any) -> Any:
    """Fold 0-100 and "95%" forms into the 0.0-1.0 the contract requires."""
    if value is None:
        # Confidence is a required part of the model contract. Treating a
        # missing/null value as 1.0 silently turned unknown certainty into the
        # strongest possible claim and bypassed the confidence gate.
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip()
        is_percent = text.endswith("%")
        try:
            number = float(text.rstrip("%").strip())
        except ValueError:
            return value
        if is_percent:
            number /= 100.0
    elif isinstance(value, (int, float)):
        number = float(value)
    else:
        return value

    if 1.0 < number <= 100.0:
        number /= 100.0
    return min(max(number, 0.0), 1.0)


def parse_page(value: Any) -> Any:
    """Accept "p. 58" / "58" for source_page; leave anything else alone."""
    if value is None or isinstance(value, bool):
        return None if value is None else value
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float) and value.is_integer():
        return int(value) if value > 0 else None
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            page = int(match.group())
            return page if page > 0 else None
        return None
    return value


def parse_year(value: Any) -> Any:
    """Pull a 4-digit year out of "FY2022", "fiscal 2022", etc."""
    if value is None:
        return None
    match = re.search(r"(?:19|20)\d{2}", str(value))
    return match.group() if match else value


def normalize_payload(payload: Any) -> tuple[Any, list[str]]:
    """
    Best-effort repair of a parsed model reply.

    Returns ``(payload, repairs)`` where ``repairs`` lists the changes made, in
    plain language, for the run record. The payload is still handed to the
    contract afterwards; this never guarantees validity.
    """
    repairs: list[str] = []

    if isinstance(payload, list):
        payload = {"rows": payload}
        repairs.append("wrapped a bare rows array in the expected object")

    if not isinstance(payload, dict):
        return payload, repairs

    payload = dict(payload)

    if "rows" not in payload:
        for key in ("result", "data", "balance_sheet", "output", "items"):
            nested = payload.get(key)
            if isinstance(nested, dict) and "rows" in nested:
                payload.update(nested)
                repairs.append(f"unwrapped the payload nested under '{key}'")
                break
            if isinstance(nested, list):
                payload["rows"] = nested
                repairs.append(f"used '{key}' as the rows array")
                break

    if "detected_fiscal_year" in payload:
        original = payload["detected_fiscal_year"]
        fixed = parse_year(original)
        if fixed != original:
            payload["detected_fiscal_year"] = fixed
            repairs.append(f"read fiscal year {fixed!r} out of {original!r}")

    rows = payload.get("rows")
    if not isinstance(rows, list):
        return payload, repairs

    normalized_rows: list[Any] = []
    renamed: list[str] = []
    reformatted = 0

    for row in rows:
        if not isinstance(row, dict):
            normalized_rows.append(row)
            continue
        row = dict(row)

        canonical = canonical_item(row.get("item"))
        if canonical is not None and canonical != row.get("item"):
            renamed.append(f"{row.get('item')!r}→{canonical!r}")
            row["item"] = canonical

        for key, parser in (
            ("answer_m_usd", parse_money),
            ("confidence", parse_confidence),
            ("source_page", parse_page),
        ):
            if key in row:
                before = row[key]
                after = parser(before)
                if after != before and not (before is None and after is None):
                    row[key] = after
                    if key == "answer_m_usd":
                        reformatted += 1
                else:
                    row[key] = after

        normalized_rows.append(row)

    if renamed:
        shown = ", ".join(renamed[:3])
        more = "" if len(renamed) <= 3 else f" (+{len(renamed) - 3} more)"
        repairs.append(f"renamed {len(renamed)} item(s) to their schema name: {shown}{more}")
    if reformatted:
        repairs.append(f"parsed {reformatted} numeric value(s) that were sent as formatted strings")

    # Reorder only when every row is identifiable; a partial sort would hide a
    # missing row behind a confusing order error.
    order = {item: index for index, item in enumerate(CANONICAL_ITEMS)}
    items = [r.get("item") for r in normalized_rows if isinstance(r, dict)]
    if len(items) == len(normalized_rows) and set(items) == set(CANONICAL_ITEMS) and items != CANONICAL_ITEMS:
        normalized_rows.sort(key=lambda r: order[r["item"]])
        repairs.append("reordered rows into TARGET_SCHEMA order")

    payload["rows"] = normalized_rows
    return payload, repairs
