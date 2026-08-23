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
4. Express every monetary value in the OUTPUT UNIT specified in the user message.
   Scale the report's stated figures to millions. Never invent an exchange rate and
   never convert between currencies unless the user message supplies an explicit
   rate. Record any scale conversion in the evidence field.
   Preserve the precision disclosed by the report after scaling; do not round a
   thousands-based source to one decimal million.
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
    answers. Confidence prioritizes human review; it never suppresses a value.
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
  requested belong in the schema's catch-all Other Equipment row. Do not add
  them to Buildings merely because the underlying leases include facilities.
- Goodwill and other non-physical long-lived assets both belong to Intangible Assets.
- A single "other assets" line often has to be split across Financial Assets and
  Other Fixed Assets using the corresponding note.
- Classify long-lived financial claims by economic substance: pension or
  postretirement assets, insurance receivables, cash surrender values of life
  insurance, deposits, loans, and investments belong in Financial Assets.
  Equity contributions and capital contributions (出資金) are Investments,
  including when the face statement nests them inside an "other" line and a
  financial-instruments note discloses the amount.
  Deferred-tax assets and a note's residual non-financial "other" line belong
  in Other Fixed Assets unless the report gives evidence for another row.
  If an "other (net)" line contains one specifically disclosed financial
  component, move only that component (net of its related allowance) into
  Financial Assets; keep the undisclosed residual in Other Fixed Assets. The
  presence of a receivable allowance does not make the entire residual line a
  financial asset. Move a component only when the note presents it as a
  quantified financial instrument (a loan, deposit, or insurance-related
  asset); an intercompany or related-party receivable mentioned narratively
  inside a residual "other" line stays in Other Fixed Assets.
- "Advance Payments" means amounts advanced to suppliers or paid on account. It
  is not prepaid expenses / prepaid taxes: those belong in Other Current Assets.
  If the report shows no advances line, Advance Payments is 0, not the prepaids
  figure.
- Loan-receivable rows (short-term, long-term) are 0 when the company reports no
  lending receivable, not null.
- Classify loan receivables by contractual maturity, even when a note labels the
  instrument "long-term loan (including the current portion)": amounts due
  within one year belong in Short-term Loan and amounts due after one year in
  Long-term Loan. If the face statement embeds the current portion in a generic
  current "other" line, subtract it from Other Current Assets.
- An unallocated allowance for doubtful accounts (貸倒引当金) offsets the
  corresponding receivable bucket: current allowances normally net Accounts
  Receivable - Trade, and long-term allowances normally net Other Financial
  Assets. This holds even when no financial receivable is separately presented
  in the section — a small negative Other Financial Assets balance is the
  correct result. Do not move the allowance into residual Other Current Assets
  or Other Fixed Assets unless the report explicitly ties it there.
- Deferred Charges means a separately presented deferred-assets/deferred-charges
  category (for example Japanese 繰延資産). Prepaid expenses and long-term prepaid
  expenses (長期前払費用) remain in Other Current Assets or Other Fixed Assets;
  they are not Deferred Charges merely because their cost is recognized over time.
  When no deferred-charges category is presented and Total Assets equals Current
  Assets plus Fixed Assets, Deferred Charges is the established residual 0, not null.
- In a condensed statutory balance-sheet summary (貸借対照表の要旨), identify
  Total Assets by reconciliation, never by size or repetition: the assets total
  must equal the sum of the printed asset components AND equal liabilities plus
  net assets computed from the printed equity components. The largest printed
  figure is often a capital reserve, not the total, when the company carries an
  accumulated deficit, and equity sub-lines (資本剰余金 and its 資本準備金
  component) can legitimately print the same value twice.
- Before returning, check each subtotal against the sum of its components and
  check Total Assets against the total printed in the report. Allow only the
  small arithmetic difference mathematically possible when the report prints
  each line in rounded whole millions; do not alter a printed line to force it.
  Otherwise, revisit the component rows rather than forcing the subtotal.

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
    "ocr_pages": "Pages replaced by OCR",
    "native_text_fallback_pages": "Text-based pages recovered from their embedded text layer",
    "selected_pages": "Pages retained by the intelligent scanning gate",
    "selected_page_count": "Pages sent for semantic mapping",
    "character_reduction_percent": "Markdown character reduction (%)",
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
    output_currency: str = "USD",
) -> str:
    """
    Assemble the user message for any strategy.

    ``extraction_note`` describes how the PDF was converted, so the model knows
    what kind of text it is looking at. Each strategy supplies its own note
    instead of the caller string-patching a shared template.
    """
    schema_json = json.dumps(ASSET_SCHEMA, ensure_ascii=False, indent=2)
    currency = str(output_currency or "USD").strip().upper()
    if not currency or not currency.replace("_", "").isalnum():
        currency = "USD"
    output_unit = f"M {currency}"

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

OUTPUT UNIT
Return every monetary answer in {output_unit}. The legacy JSON field name
"answer_m_usd" is retained for API compatibility; for this run it means {output_unit}.
Use the report's own currency and scale. No foreign-exchange conversion is authorized.

{fy_instruction}{render_diagnostics(diagnostics)}ANNUAL REPORT
The uploaded PDF was converted to {extraction_note}

{report_text}

Detect the fiscal year from the report, fill all {EXPECTED_ROW_COUNT} TARGET_SCHEMA rows,
and return the required JSON including detected_fiscal_year and a confidence score for
each row.
"""


def build_evidence_retry_prompt(
    *,
    additional_pages_text: str,
    missing_items: list[str],
    detected_fiscal_year: str = "",
    output_currency: str = "USD",
    original_packet_text: str = "",
) -> str:
    """
    Second bounded Strategy 3 pass: the first semantic mapping left specific
    schema rows without a value, so additional ranked pages are supplied and
    only those rows are re-asked. Contains schema labels and parser output
    only — never any expected value.
    """
    schema_json = json.dumps(ASSET_SCHEMA, ensure_ascii=False, indent=2)
    currency = str(output_currency or "USD").strip().upper()
    if not currency or not currency.replace("_", "").isalnum():
        currency = "USD"
    output_unit = f"M {currency}"
    items_list = "\n".join(f"- {item}" for item in missing_items)
    fy_note = (
        f"The first pass detected fiscal year {detected_fiscal_year.strip()}.\n"
        if detected_fiscal_year and detected_fiscal_year.strip()
        else ""
    )
    packet_section = (
        "PREVIOUSLY SUPPLIED PAGES (re-read them carefully — the correct figure "
        "may already be here; distinguish look-alike note amounts by their labels)\n"
        f"{original_packet_text}\n\n"
        if original_packet_text.strip()
        else ""
    )
    if not additional_pages_text.strip():
        additional_section = (
            "NO ADDITIONAL PAGES EXIST\n"
            "The previously supplied pages are the complete readable content of "
            "this report, so absence from them IS absence from the report — "
            "apply the normal null/zero rules directly. For a partially garbled "
            "statutory summary, commit the reading whose totals reconcile with "
            "the printed components (with reduced confidence) rather than "
            "returning null; never pick a figure merely because it is the "
            "largest or appears twice.\n"
        )
    else:
        additional_section = f"ADDITIONAL ANNUAL REPORT PAGES\n{additional_pages_text}\n"
    return f"""TARGET_SCHEMA
{schema_json}

OUTPUT UNIT
Return every monetary answer in {output_unit}. The legacy JSON field name
"answer_m_usd" is retained for API compatibility; for this run it means {output_unit}.
Use the report's own currency and scale. No foreign-exchange conversion is authorized.

EVIDENCE RETRY
A first extraction pass over other pages of the same Annual Report either could
not establish values for the rows listed below or produced values that failed a
deterministic balance-sheet identity check. {fy_note}Additional complete pages
from the same report follow. Re-derive ONLY these rows from the additional
evidence:

{items_list}

{packet_section}{additional_section}

Return the full required JSON for all {EXPECTED_ROW_COUNT} TARGET_SCHEMA rows,
including detected_fiscal_year and a confidence score per row. For the listed
rows, supply a value only when these pages provide traceable evidence, following
the same null/zero rules as before; check that related subtotals reconcile. For
every row NOT listed above, return null; those rows are already answered and
will not be read from this reply.
"""
