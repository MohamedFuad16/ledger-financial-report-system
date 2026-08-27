"""
Deterministic arithmetic completion and verification of a prediction.

This runs *after* the Pydantic contract and is completely separate from it:

    reply -> normalize (repair shape) -> models (check types) -> reconcile (check maths)

The contract proves the reply is *well-formed*. Reconciliation proves it is
*internally consistent*: every subtotal equals the sum of its components, and
Total Assets equals Current + Fixed + Deferred.

Two properties make this worth having:

1. **No answer key required.** It works on any company's report, which is the
   only quality signal available once the corpus grows past the handful of
   filers we have golden data for.
2. **It never overwrites a reported value.** A null may be completed only when
   one and only one term in a schema identity is missing and every other term is
   available. That is algebra, not an answer-key lookup. Conflicting non-null
   values remain untouched and are reported as failed identities.
"""

from __future__ import annotations

import re
from typing import Any

from schema import SUBTOTAL_IDENTITIES

# Values are in millions. This is the fallback for legacy runs whose source
# statement precision was not recorded.
TOLERANCE = 0.5

_PARTS_BY_TOTAL = dict(SUBTOTAL_IDENTITIES)
_PPE_COMPONENTS = [
    "Land",
    "Buildings",
    "Plant & Machinery",
    "Construction in Progress",
    "Other Equipment",
    "Accumulated Depreciation",
]
_DEPRECIABLE_PPE_COMPONENTS = ["Buildings", "Plant & Machinery", "Other Equipment"]


def _number(value: str) -> float:
    return float(value.replace(",", ""))


def _different(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(left - right) > tolerance * max(1.0, abs(left), abs(right))


def detect_source_fidelity_issues(
    rows: list[dict],
    *,
    value_quantum: float = 0.0,
) -> list[dict[str, Any]]:
    """Find contradictions between a row value and its own cited source.

    This validator deliberately reads only the model's source label/evidence;
    it has no access to benchmark answers. It does not repair a value. Instead
    it identifies rows that warrant the existing bounded evidence retry when
    the citation itself proves a unit conversion, printed-total, classification,
    or direct-component inconsistency.
    """
    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(item: str, code: str, reason: str, retry_items: list[str] | None = None) -> None:
        key = (item, code)
        if key in seen:
            return
        seen.add(key)
        issues.append(
            {
                "status": "failed",
                "item": item,
                "code": code,
                "reason": reason,
                "retry_items": retry_items or [item],
            }
        )

    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = str(row.get("item") or "")
        value = row.get("answer_m_usd")
        if not item or not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        answer = float(value)
        label = str(row.get("source_label") or "")
        evidence = re.sub(r"\s+", " ", str(row.get("evidence") or "")).strip()
        combined = f"{label} {evidence}".strip()

        # Explicit source-unit equations are the strongest possible unit check.
        # For example, 4,676,003 thousand yen is 4,676.003 million yen, not
        # 4.676003 million yen. The model sometimes states both sides of that
        # contradiction in its own evidence while retaining the wrong value.
        thousand_equations = re.finditer(
            r"([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
            r"(?:千円|thousand(?:s)?(?:\s+of)?\s+yen)\s*"
            r"(?:=|equals?|is)\s*"
            r"([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
            r"(?:M\s*JPY|百万円|million(?:s)?(?:\s+of)?\s+yen)",
            evidence,
            flags=re.IGNORECASE,
        )
        for match in thousand_equations:
            source_millions = _number(match.group(1)) / 1_000.0
            claimed_millions = _number(match.group(2))
            # Reports commonly print accumulated depreciation as a positive
            # deduction while this schema requires the row to carry a negative
            # sign. A negative converted amount is therefore consistent when
            # the cited raw source number omitted the presentation sign.
            if item == "Accumulated Depreciation" and source_millions > 0 and claimed_millions < 0:
                source_millions = -source_millions
            if _different(source_millions, claimed_millions) or _different(answer, source_millions):
                add(
                    item,
                    "contradictory_thousands_to_millions_conversion",
                    "The row's own evidence converts a thousands-based source amount "
                    "to millions inconsistently; re-read the source unit and rescale it.",
                )
                break

        # A subtotal or total printed by the report is authoritative for that
        # row. Component arithmetic remains a validation signal and must not
        # silently overwrite a directly stated balance-sheet amount.
        direct_patterns = (
            r"printed (?:subtotal|total)(?: on page \d+)?\s+(?:is|of)\s*"
            r"([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*(千円|百万円|thousand yen|million yen)?",
            r"reported (?:subtotal|total)\s*[:：]?\s*"
            r"([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*(千円|百万円|thousand yen|million yen)?",
            r"貸借対照表(?:の)?(?:純額|表示額)は\s*"
            r"([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*(千円|百万円)?",
            r"balance sheet reports net\s*"
            r"([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*(千円|百万円|thousand yen|million yen)?",
        )
        for pattern in direct_patterns:
            direct_match = re.search(pattern, evidence, flags=re.IGNORECASE)
            if not direct_match:
                continue
            direct = _number(direct_match.group(1))
            unit = (direct_match.group(2) or "").lower()
            if unit in {"千円", "thousand yen"}:
                direct /= 1_000.0
            if _different(answer, direct):
                add(
                    item,
                    "direct_reported_value_overwritten_by_arithmetic",
                    "The row's own evidence cites a directly printed balance-sheet "
                    "subtotal or total that differs from the first-pass value; preserve "
                    "the printed amount and use component arithmetic only as a check.",
                )
            break

        # A residual back-solve is weaker than a complete, quantified list of
        # the residual row's direct components. If the model cites both and
        # they differ, the direct component sum should be re-verified.
        component_match = re.search(r"\bcomprising\b(.+)", evidence, flags=re.IGNORECASE)
        if component_match:
            component_values = [
                _number(number)
                for number in re.findall(
                    r"(?<![A-Za-z0-9.])([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)",
                    component_match.group(1),
                )
            ]
            # Each displayed component and the displayed subtotal may differ
            # from the unrounded amount by q/2. Do not turn an exactly bounded
            # whole-million rounding difference into a retry warning.
            component_tolerance = (
                (len(component_values) + 1) * float(value_quantum) / 2 + 1e-9 if value_quantum > 0 else 1e-9
            )
            if len(component_values) >= 2 and abs(answer - sum(component_values)) > component_tolerance:
                add(
                    item,
                    "residual_disagrees_with_direct_components",
                    "The row's own evidence gives a quantified component list whose sum "
                    "differs from a residual back-solve; verify the direct components and "
                    "do not assume a separately reported financial subtotal is exhaustive.",
                )

        if item == "Cash & Cash Equivalents" and "預け金" in combined:
            add(
                item,
                "custody_deposit_included_in_cash",
                "The Cash row includes 預け金. Treat it as Other Quick Assets unless "
                "the report explicitly identifies it as an immediately available cash equivalent.",
                ["Cash & Cash Equivalents", "Other Quick Assets"],
            )

    return issues


def derive_identity_values(rows: list[dict]) -> tuple[list[dict], list[dict[str, Any]]]:
    """Complete uniquely solvable nulls without consulting benchmark gold.

    Each schema identity has the form ``total = part + part ...``.  If exactly
    one value in that equation is null, the remaining values establish a unique
    residual.  Preserve every non-null model value, stamp the derivation into
    the row evidence, and repeat because resolving an inner subtotal can make an
    outer identity solvable.
    """
    completed = [dict(row) for row in rows]
    by_item = {str(row.get("item")): row for row in completed if isinstance(row, dict) and row.get("item")}
    derivations: list[dict[str, Any]] = []

    changed = True
    while changed:
        changed = False
        for total_item, parts in SUBTOTAL_IDENTITIES:
            equation_items = [total_item, *parts]
            missing = [item for item in equation_items if by_item.get(item, {}).get("answer_m_usd") is None]
            if len(missing) != 1:
                continue
            missing_item = missing[0]
            try:
                total_value = by_item[total_item].get("answer_m_usd")
                part_values = [by_item[part].get("answer_m_usd") for part in parts]
                derived: float
                if missing_item == total_item:
                    derived = sum(float(value) for value in part_values if value is not None)
                    operands = parts
                else:
                    if total_value is None:
                        continue
                    derived = float(total_value) - sum(
                        float(value)
                        for part, value in zip(parts, part_values, strict=True)
                        if part != missing_item and value is not None
                    )
                    operands = [
                        total_item,
                        *[part for part in parts if part != missing_item],
                    ]
            except (KeyError, TypeError, ValueError):
                continue

            target = by_item[missing_item]
            confidences = []
            for item in operands:
                confidence = by_item[item].get("confidence")
                if isinstance(confidence, (int, float)):
                    confidences.append(float(confidence))
            identity = f"{total_item} = {' + '.join(parts)}"
            prior_evidence = str(target.get("evidence") or "").strip()
            derivation_evidence = f"Deterministically derived from schema identity: {identity}."
            target.update(
                {
                    "answer_m_usd": round(derived, 9),
                    "confidence": min(confidences) if confidences else 0.8,
                    "accepted": False,
                    "source_label": target.get("source_label") or f"Calculated: {identity}",
                    "evidence": f"{prior_evidence} {derivation_evidence}".strip(),
                }
            )
            derivations.append(
                {
                    "item": missing_item,
                    "value": round(derived, 9),
                    "identity": identity,
                }
            )
            changed = True

    return completed, derivations


def _leaf_count(item: str) -> int:
    parts = _PARTS_BY_TOTAL.get(item)
    return sum(_leaf_count(part) for part in parts) if parts else 1


def _identity_tolerance(total_item: str, value_quantum: float) -> float:
    if value_quantum <= 0:
        return TOLERANCE
    # A nested subtotal may be reconstructed from every schema leaf below it.
    # Each displayed leaf and the stated total can differ by q/2.
    return (_leaf_count(total_item) + 1) * float(value_quantum) / 2 + 1e-9


def _values(rows: list[dict]) -> dict[str, float | None]:
    """
    Map item -> the extracted value, regardless of model confidence.

    Confidence is a review-priority hint, not a correctness oracle. Arithmetic
    validation must inspect the actual returned values or it will skip valid
    identities solely because a model assigned itself 0.79 instead of 0.80.
    """
    out: dict[str, float | None] = {}
    for row in rows or []:
        if not isinstance(row, dict) or "item" not in row:
            continue
        value = row.get("answer_m_usd")
        out[row["item"]] = float(value) if isinstance(value, (int, float)) else None
    return out


def detect_ppe_measurement_basis_issue(
    rows: list[dict],
    evidence_text: str,
    *,
    value_quantum: float = 0.0,
) -> dict[str, Any] | None:
    """Detect a reconciled net-PPE answer that suppresses disclosed depreciation.

    Arithmetic alone cannot distinguish gross components plus negative
    accumulated depreciation from already-net component values plus zero. This
    validator fires only when the latter representation reconciles *and* the
    supplied report text contains both an explicit numeric accumulated-
    depreciation disclosure and a net/carrying-value marker. It never supplies
    or changes a number; it only opens the bounded evidence-verification path.
    """
    values = _values(rows)
    tangible = values.get("Tangible Assets")
    components = [values.get(item) for item in _PPE_COMPONENTS]
    accumulated = values.get("Accumulated Depreciation")
    if tangible is None or any(value is None for value in components):
        return None
    tolerance = _identity_tolerance("Tangible Assets", value_quantum)
    if accumulated is None or abs(accumulated) > tolerance:
        return None
    if not any(float(values.get(item) or 0.0) > 0 for item in _DEPRECIABLE_PPE_COMPONENTS):
        return None
    computed = sum(float(value) for value in components if value is not None)
    if abs(computed - tangible) > tolerance:
        return None

    normalized = re.sub(r"\s+", " ", str(evidence_text or ""))
    depreciation_marker = r"(?:減価償却累計額|accumulated depreciation)"
    numeric_disclosure = bool(
        re.search(rf"{depreciation_marker}.{{0,220}}\d", normalized, flags=re.IGNORECASE)
        or re.search(rf"\d.{{0,120}}{depreciation_marker}", normalized, flags=re.IGNORECASE)
    )
    net_basis_marker = bool(
        re.search(
            r"純額|帳簿価額|net book value|net carrying (?:amount|value)|carrying amount",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    if not numeric_disclosure or not net_basis_marker:
        return None

    return {
        "status": "failed",
        "code": "net_ppe_with_zero_accumulated_depreciation",
        "reason": (
            "The first pass reconciles only because PPE component rows appear to use net "
            "carrying values while Accumulated Depreciation is zero, even though the "
            "supplied report discloses a numeric accumulated-depreciation amount."
        ),
        "identity": "Tangible Assets = gross PPE components + Accumulated Depreciation",
        "stated_tangible_assets": tangible,
        "computed_first_pass_components": computed,
        "accumulated_depreciation": accumulated,
        "tolerance": tolerance,
        "retry_items": list(_PPE_COMPONENTS),
    }


def reconcile(rows: list[dict], *, value_quantum: float = 0.0) -> dict[str, Any]:
    """
    Check every subtotal identity the schema implies.

    Returns a report listing each identity as ``ok`` (the parts sum to the
    stated total), ``failed`` (they do not), or ``skipped`` (a value the
    identity needs is null, so the identity cannot be evaluated at all).
    """
    values = _values(rows)
    checks: list[dict[str, Any]] = []

    for total_item, parts in SUBTOTAL_IDENTITIES:
        stated = values.get(total_item)
        part_values = [values.get(p) for p in parts]

        if stated is None or any(v is None for v in part_values):
            missing = [p for p, v in zip(parts, part_values, strict=True) if v is None]
            if stated is None:
                missing.append(total_item)
            checks.append(
                {
                    "identity": f"{total_item} = {' + '.join(parts)}",
                    "total_item": total_item,
                    "status": "skipped",
                    "reason": f"no extracted value for {', '.join(missing)}",
                    "stated": stated,
                    "computed": None,
                    "delta": None,
                }
            )
            continue

        computed = sum(part_values)  # type: ignore[arg-type]
        delta = computed - stated
        # If every printed line is rounded to q (for example q=1 for a report
        # stated in whole millions), the total and each component can each be
        # off by q/2. Accept exactly that mathematical bound and no more.
        tolerance = _identity_tolerance(total_item, value_quantum)
        checks.append(
            {
                "identity": f"{total_item} = {' + '.join(parts)}",
                "total_item": total_item,
                "status": "ok" if abs(delta) <= tolerance else "failed",
                "reason": None,
                "stated": stated,
                "computed": computed,
                "delta": round(delta, 2),
                "tolerance": round(tolerance, 6),
            }
        )

    evaluated = [c for c in checks if c["status"] != "skipped"]
    passed = [c for c in evaluated if c["status"] == "ok"]

    return {
        "checks": checks,
        "total_identities": len(checks),
        "evaluated": len(evaluated),
        "passed": len(passed),
        "failed": len(evaluated) - len(passed),
        "skipped": len(checks) - len(evaluated),
        # Share of the identities we could actually evaluate that hold. None
        # when nothing could be evaluated, so an all-null answer does not score
        # a misleading 100%.
        "consistency": round(len(passed) / len(evaluated) * 100, 1) if evaluated else None,
        "failed_identities": [c["total_item"] for c in evaluated if c["status"] == "failed"],
        "value_quantum": float(value_quantum or 0.0),
    }


def reconciliation_summary(report: dict[str, Any]) -> str:
    """One-line human summary for logs and the UI."""
    if report["evaluated"] == 0:
        return "no identity could be checked (too many null values)"
    if report["failed"] == 0:
        return f"all {report['passed']}/{report['evaluated']} arithmetic identities hold"
    return (
        f"{report['passed']}/{report['evaluated']} identities hold; "
        f"failed: {', '.join(report['failed_identities'])}"
    )
