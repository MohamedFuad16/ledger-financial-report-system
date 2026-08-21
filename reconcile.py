"""
Deterministic arithmetic verification of a prediction.

This runs *after* the Pydantic contract and is completely separate from it:

    reply -> normalize (repair shape) -> models (check types) -> reconcile (check maths)

The contract proves the reply is *well-formed*. Reconciliation proves it is
*internally consistent*: every subtotal equals the sum of its components, and
Total Assets equals Current + Fixed + Deferred.

Two properties make this worth having:

1. **No answer key required.** It works on any company's report, which is the
   only quality signal available once the corpus grows past the handful of
   filers we have golden data for.
2. **It never changes a value.** Repairing a mismatch means guessing which side
   is wrong; guessing here would corrupt the very measurement the benchmark
   exists to produce. This module reports, and nothing else. Re-asking the model
   about failed identities is outside this project's two-strategy scope.
"""

from __future__ import annotations

from typing import Any, Optional

from schema import SUBTOTAL_IDENTITIES

# Values are in millions; anything below this is rounding, not disagreement.
TOLERANCE = 0.5


def _values(rows: list[dict]) -> dict[str, Optional[float]]:
    """
    Map item -> the value we are willing to treat as an answer.

    A row the confidence gate rejected is read as null here, exactly as it is
    when scoring. Reconciling against a number the rest of the system refuses to
    count would let a discarded value silently prop up a subtotal.
    """
    out: dict[str, Optional[float]] = {}
    for row in rows or []:
        if not isinstance(row, dict) or "item" not in row:
            continue
        value = row.get("answer_m_usd")
        accepted = row.get("accepted")
        if accepted is False:
            value = None
        out[row["item"]] = float(value) if isinstance(value, (int, float)) else None
    return out


def reconcile(rows: list[dict]) -> dict[str, Any]:
    """
    Check every subtotal identity the schema implies.

    Returns a report listing each identity as ``ok`` (the parts sum to the
    stated total), ``failed`` (they do not), or ``skipped`` (a value the
    identity needs is null - or was rejected by the confidence gate - so the
    identity cannot be evaluated at all).
    """
    values = _values(rows)
    checks: list[dict[str, Any]] = []

    for total_item, parts in SUBTOTAL_IDENTITIES:
        stated = values.get(total_item)
        part_values = [values.get(p) for p in parts]

        if stated is None or any(v is None for v in part_values):
            missing = [p for p, v in zip(parts, part_values) if v is None]
            if stated is None:
                missing.append(total_item)
            checks.append({
                "identity": f"{total_item} = {' + '.join(parts)}",
                "total_item": total_item,
                "status": "skipped",
                "reason": f"no accepted value for {', '.join(missing)}",
                "stated": stated,
                "computed": None,
                "delta": None,
            })
            continue

        computed = sum(part_values)  # type: ignore[arg-type]
        delta = computed - stated
        checks.append({
            "identity": f"{total_item} = {' + '.join(parts)}",
            "total_item": total_item,
            "status": "ok" if abs(delta) < TOLERANCE else "failed",
            "reason": None,
            "stated": stated,
            "computed": computed,
            "delta": round(delta, 2),
        })

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
