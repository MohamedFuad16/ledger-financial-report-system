"""
The output contract. Nothing else.

This module answers exactly one question: **does the model's reply have the
required fields, in the required shape, with the required types?**

It deliberately does NOT:
  - rename or alias items,
  - reorder rows,
  - parse "1,234" or "(16,820)" into numbers,
  - compute subtotals, compare against golden answers, or score anything.

Repairing a messy reply is `normalize.py`, which runs *before* this. Scoring is
`pipeline.compute_metrics`, which runs *after*. Keeping those out of here means a
contract violation is always a real contract violation, not a coercion that
quietly succeeded.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import math

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from schema import ASSET_SCHEMA

CANONICAL_ITEMS: list[str] = [row["item"] for row in ASSET_SCHEMA]
SCHEMA_BY_ITEM: dict[str, dict[str, str]] = {row["item"]: row for row in ASSET_SCHEMA}
EXPECTED_ROW_COUNT: int = len(ASSET_SCHEMA)

_ITEM_SET = set(CANONICAL_ITEMS)


class SchemaValidationError(ValueError):
    """The model's reply does not satisfy the output contract."""


class AssetRow(BaseModel):
    """One row of the fixed 27-row asset-side balance sheet."""

    # extra="forbid" would reject harmless additions; extra fields are dropped,
    # but every field below must be present and correctly typed.
    model_config = ConfigDict(extra="ignore", strict=False)

    item: str
    answer_m_usd: Optional[float] = Field(
        default=...,
        description="Value in the run's declared million-unit currency, or null (legacy field name).",
    )
    confidence: float = Field(default=..., ge=0.0, le=1.0)
    source_page: Optional[int] = None
    source_label: Optional[str] = None
    evidence: Optional[str] = None

    # Copied from the schema after validation so the response is self-describing.
    # The model's own values for these are ignored, never trusted.
    classification: str = ""
    subclassification: str = ""
    description: str = ""

    @field_validator("item")
    @classmethod
    def _item_must_be_in_schema(cls, value: str) -> str:
        if value not in _ITEM_SET:
            raise ValueError(f"'{value}' is not one of the {EXPECTED_ROW_COUNT} TARGET_SCHEMA items")
        return value

    @field_validator("answer_m_usd", mode="before")
    @classmethod
    def _answer_must_be_number_or_null(cls, value: Any) -> Any:
        if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
            if value is not None:
                try:
                    finite = math.isfinite(float(value))
                except (OverflowError, ValueError) as exc:
                    # json.loads keeps an oversized integer literal as an
                    # arbitrary-precision int, and float() on it raises
                    # OverflowError. That is not a ValidationError, so without
                    # this it escaped validate_extraction uncaught and killed
                    # the run instead of triggering the bounded repair call.
                    raise ValueError(
                        "must be a finite JSON number or null; this value is too large to represent."
                    ) from exc
                if not finite:
                    raise ValueError(
                        "must be a finite JSON number or null; NaN and infinities are rejected."
                    )
            return value
        raise ValueError(
            f"must be a JSON number or null, got {type(value).__name__} ({value!r}). "
            "Thousands separators, currency symbols and parentheses are not allowed."
        )

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence_must_be_unit_number(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"must be a JSON number between 0.0 and 1.0, got {value!r}")
        return value

    @field_validator("source_page", mode="before")
    @classmethod
    def _source_page_must_be_int_or_null(cls, value: Any) -> Any:
        if value is None or (isinstance(value, int) and not isinstance(value, bool)):
            return value
        raise ValueError(f"must be an integer page number or null, got {value!r}")


class ExtractionResult(BaseModel):
    """The complete object a strategy must produce for one Annual Report."""

    model_config = ConfigDict(extra="ignore")

    detected_fiscal_year: Optional[str] = None
    rows: list[AssetRow]

    @field_validator("detected_fiscal_year", mode="before")
    @classmethod
    def _year_must_be_four_digits(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        if not (len(text) == 4 and text.isdigit()):
            raise ValueError(f'must be a 4-digit year string such as "2022", got {value!r}')
        return text

    @model_validator(mode="after")
    def _rows_must_match_the_schema_exactly(self) -> "ExtractionResult":
        returned = [row.item for row in self.rows]

        if len(returned) != EXPECTED_ROW_COUNT:
            raise ValueError(f"expected exactly {EXPECTED_ROW_COUNT} rows, got {len(returned)}")

        duplicates = {i for i in returned if returned.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate rows for: {', '.join(sorted(duplicates))}")

        missing = [i for i in CANONICAL_ITEMS if i not in returned]
        if missing:
            raise ValueError(
                f"missing {len(missing)} required row(s): {', '.join(missing[:5])}"
                f"{'…' if len(missing) > 5 else ''}"
            )

        if returned != CANONICAL_ITEMS:
            first = next(i for i, (a, b) in enumerate(zip(returned, CANONICAL_ITEMS)) if a != b)
            raise ValueError(
                f"rows are not in TARGET_SCHEMA order: position {first + 1} is "
                f"'{returned[first]}', expected '{CANONICAL_ITEMS[first]}'"
            )

        # Restate the descriptive columns from the schema. This is not a mapping
        # decision — the row identity is already proven correct above.
        for row in self.rows:
            meta = SCHEMA_BY_ITEM[row.item]
            row.classification = meta["classification"]
            row.subclassification = meta["subclassification"]
            row.description = meta["description"]

        return self


def validate_extraction(payload: Any) -> ExtractionResult:
    """
    Validate a payload against the contract.

    Expects the payload to have already been through ``normalize.normalize_payload``
    if it came from an LLM. Raises ``SchemaValidationError`` with a readable
    message listing what the contract rejected.
    """
    if not isinstance(payload, dict):
        raise SchemaValidationError(
            f'expected a JSON object with a "rows" array, got {type(payload).__name__}'
        )
    try:
        return ExtractionResult.model_validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(_format_validation_error(exc)) from exc


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:6]:
        location = ".".join(str(p) for p in err["loc"]) or "(root)"
        message = err["msg"].removeprefix("Value error, ")
        parts.append(f"{location}: {message}")
    suffix = "" if len(exc.errors()) <= 6 else f" (+{len(exc.errors()) - 6} more)"
    return "Output contract violated — " + "; ".join(parts) + suffix


def rows_as_dicts(result: ExtractionResult) -> list[dict[str, Any]]:
    """Serialize validated rows for prediction.json and API responses."""
    return [
        {
            "classification": row.classification,
            "subclassification": row.subclassification,
            "item": row.item,
            "description": row.description,
            "answer_m_usd": row.answer_m_usd,
            "confidence": row.confidence,
            "source_page": row.source_page,
            "source_label": row.source_label,
            "evidence": row.evidence,
        }
        for row in result.rows
    ]


def output_contract_text() -> str:
    """
    Render the OUTPUT CONTRACT block for the prompt from this module, so the
    instructions the model receives always match what is enforced here.
    """
    # Placeholder values only. Never put a real figure from any report in here:
    # the example is part of the prompt and would act as an answer key.
    example = {
        "detected_fiscal_year": "YYYY",
        "rows": [
            {
                "item": CANONICAL_ITEMS[0],
                "answer_m_usd": 9999,
                "confidence": 0.92,
                "source_page": 42,
                "source_label": "the line label used in the report",
                "evidence": "short supporting quote or explanation",
            }
        ],
    }
    return f"""Return exactly one JSON object with this shape:

{json.dumps(example, ensure_ascii=False, indent=2)}

Requirements:
- "detected_fiscal_year" is a 4-digit year string.
- "rows" contains exactly {EXPECTED_ROW_COUNT} objects, one per TARGET_SCHEMA item,
  in TARGET_SCHEMA order, with "item" copied verbatim from TARGET_SCHEMA.
- "answer_m_usd" is a JSON number in the OUTPUT UNIT declared by the user message,
  or null. The field name is retained for API compatibility and does not authorize
  currency conversion. No thousands separators, no currency symbols, no
  parentheses; write negatives with a leading minus sign.
- "confidence" is a JSON number between 0.0 and 1.0.
- "source_page" is an integer PDF page number or null.
- "source_label" is the line label used in the report, or null.
- "evidence" is a short supporting string, or null.
- Return JSON only. No Markdown fences, no prose outside the JSON."""
