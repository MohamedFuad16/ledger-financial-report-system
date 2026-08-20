import json

from models import EXPECTED_ROW_COUNT, output_contract_text
from schema import ASSET_SCHEMA

SYSTEM_PROMPT = f"""
You are a financial-document extraction system.

Your job is to read the Annual Report supplied in the user message and fill the
requested asset-side balance-sheet table.

You are responsible for locating, interpreting, mapping, and calculating the
requested values from the supplied report.

RULES

1. Use only the Annual Report supplied in the user message.
2. Do not use outside knowledge, web search, memory of the company, or an answer key.
3. Detect the target fiscal year from the report content. Financial statements show
   two or more comparative columns; the target is the most recent completed fiscal
   year, which is normally the leftmost column. Read values from that column only.
4. Express every monetary value in millions of USD (M USD). If the statements are
   presented in thousands, billions, or another currency, convert and say so in the
   evidence field.
5. Pay careful attention to:
   - fiscal-year columns,
   - table row and column relationships,
   - units,
   - parentheses and negative values,
   - accumulated depreciation,
   - company terminology that may differ from the requested target field.
6. The target schema is fixed. Do not add, remove, rename, merge, or reorder rows.
7. When the schema defines a subtotal or total, calculate it from report-supported
   values when sufficient evidence exists, and check that it agrees with any
   corresponding total printed in the report.
8. Distinguish "not determinable" from "not present":
   - A row that decomposes a stated subtotal (its siblings must sum to that
     subtotal) is 0 when the report presents no such component. Reporting null
     there breaks the subtotal it belongs to.
   - A row that stands alone and whose value you cannot establish from the
     report is null with confidence 0.0.
   Do not invent a number, and never report a figure you cannot point to.
9. Preserve negative signs exactly. Accumulated depreciation is negative.
10. Return JSON only. Do not return Markdown or explanatory prose outside the JSON.
11. For each row, provide a confidence score between 0.0 and 1.0 indicating how
    confident you are that the extracted value is correct and well-supported by
    evidence in the report. Use at least 0.8 only when the value has clear,
    traceable support. Use below 0.8 for uncertain, inferred, or weakly supported
    answers; those values are retained for review but excluded from accepted output.
12. Include the detected fiscal year in your response as a top-level field.
13. The supplied text is machine-extracted and may be imperfect. If a page's text
    is unreadable (control characters, mojibake), do not guess values from it;
    prefer a readable page that discloses the same figure, otherwise return null.

MAPPING GUIDANCE (general, not company-specific)

- Balance sheets rarely use the schema's exact labels. Map by meaning, using the
  notes to the financial statements when the face of the balance sheet aggregates
  several schema items into one line.
- The property, plant and equipment note usually carries the gross breakdown
  (land, buildings, machinery, construction in progress) and the accumulated
  depreciation that the face of the balance sheet reports only as a net figure.
- Right-of-use and similar long-lived operating assets that are not separately
  requested belong with the closest tangible-asset row rather than being dropped.
- Goodwill and other non-physical long-lived assets both belong to Intangible Assets.
- A single "other assets" line often has to be split across Financial Assets and
  Other Fixed Assets using the corresponding note.
- "Advance Payments" means amounts advanced to suppliers or paid on account. It
  is not prepaid expenses / prepaid taxes: those belong in Other Current Assets.
  If the report shows no advances line, Advance Payments is 0, not the prepaids
  figure.
- Loan-receivable rows (short-term, long-term) are 0 when the company reports no
  lending receivable, not null.
- Before returning, check each subtotal against the sum of its components and
  check Total Assets against the total printed in the report. If they disagree,
  revisit the component rows rather than forcing the subtotal.

OUTPUT CONTRACT

{output_contract_text()}
""".strip()


_DIAGNOSTIC_LABELS = {
    "title": "Document title",
    "document_type": "Document type",
    "type_confidence": "Type confidence",
    "has_encoding_issues": "Text layer has encoding problems",
    "complex_layout": "Complex multi-column layout",
    "pages_with_tables": "Pages containing tables",
    "table_page_count": "Number of pages with tables",
    "table_count": "Tables detected",
    "largest_tables": "Table shapes (page: rows x cols)",
    "pages_with_multiple_columns": "Pages with multiple columns",
    "pages_needing_ocr": "Pages whose text layer is unreadable",
    "outline": "Document outline",
    "outline_entries_total": "Outline entries in document",
}


def render_diagnostics(diagnostics: dict | None) -> str:
    """
    Render whatever structural facts the parser discovered.

    Different parsing technologies know different amounts about a document:
    PyPDF little more than its title, pdf-inspector a full page map, Docling a
    typed table graph. Passing that through is deliberate — it is the capability
    being compared, and withholding it would test every parser as if it were a
    plain-text extractor.

    Returns an empty string when the parser supplied nothing, so the prompt is
    unchanged for parsers without this ability.
    """
    if not diagnostics:
        return ""
    source = diagnostics.get("source", "the parser")
    lines: list[str] = []
    for key, label in _DIAGNOSTIC_LABELS.items():
        if key not in diagnostics:
            continue
        value = diagnostics[key]
        if isinstance(value, bool):
            value = "yes" if value else "no"
        elif isinstance(value, list):
            if not value:
                continue
            lines.append(f"- {label}:")
            lines.extend(f"    {item}" for item in value)
            continue
        lines.append(f"- {label}: {value}")
    if not lines:
        return ""
    return (
        f"DOCUMENT MAP (reported by {source}, not by you)\n"
        "Structural facts about this PDF. Use them to navigate - for example to find\n"
        "the balance sheet and the notes faster, or to distrust pages flagged as\n"
        "unreadable. They contain no financial values and are not an answer key.\n\n"
        + "\n".join(lines)
        + "\n\n"
    )


def build_user_prompt(
    report_text: str,
    extraction_note: str = "raw page-by-page text. Page markers identify the source PDF page.",
    fiscal_year: str = "",
    diagnostics: dict | None = None,
) -> str:
    """
    Assemble the user message for any strategy.

    ``extraction_note`` describes how the PDF was converted, so the model knows
    what kind of text it is looking at. Each strategy supplies its own note
    instead of the caller string-patching a shared template.
    """
    schema_json = json.dumps(ASSET_SCHEMA, ensure_ascii=False, indent=2)

    fy_instruction = ""
    if fiscal_year and fiscal_year.strip():
        fy_instruction = (
            "TARGET FISCAL YEAR HINT\n"
            f"The user suggests the target fiscal year may be {fiscal_year.strip()}.\n"
            "However, you must verify this by examining the report content and detect the\n"
            "correct fiscal year independently.\n\n"
        )

    # Ordering is deliberate and load-bearing for cost. Prompt caching on
    # OpenRouter / OpenAI / DeepSeek is a *prefix* cache: only a byte-identical
    # leading span is reused. TARGET_SCHEMA is ~1,400 tokens and identical on
    # every single request, so it goes first, before anything that varies.
    # Putting the fiscal-year hint or the document map ahead of it — as an
    # earlier version did — makes the schema uncacheable on every call.
    return f"""TARGET_SCHEMA
{schema_json}

{fy_instruction}{render_diagnostics(diagnostics)}ANNUAL REPORT
The uploaded PDF was converted to {extraction_note}

{report_text}

Detect the fiscal year from the report, fill all {EXPECTED_ROW_COUNT} TARGET_SCHEMA rows,
and return the required JSON including detected_fiscal_year and a confidence score for
each row.
"""
