"""
Offline checks for the pieces that used to break silently.

No API key and no network required:

    .venv/bin/python test_contract.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import api_client as api_client_module
from api_client import parse_assistant_json, run_extraction
from extraction import (
    _finalize,
    garble_ratio,
    get_strategy,
    mixed_token_ratio,
    normalize_text,
    page_is_unreadable,
)
from models import (
    rows_as_dicts,
    CANONICAL_ITEMS,
    EXPECTED_ROW_COUNT,
    SchemaValidationError,
    validate_extraction,
)
from normalize import canonical_item, normalize_payload, parse_confidence, parse_money
from pipeline import compute_metrics
from prompts import SYSTEM_PROMPT, build_user_prompt
from reconcile import reconcile
from schema import (
    ASSET_SCHEMA,
    ASSIGNMENT_GOLDEN_SOURCE_SHA256,
    GOLDEN_ANSWERS_STORE,
    SOURCE_BOUND_GOLDEN_ANSWERS,
)

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        FAILURES.append(name)


def expect_error(name: str, fn, fragment: str = "") -> None:
    try:
        fn()
    except (SchemaValidationError, ValueError) as exc:
        check(name, fragment.lower() in str(exc).lower(), f"message was: {exc}")
    else:
        check(name, False, "no error raised")


def golden_rows(year: str, **overrides) -> list[dict]:
    golden = GOLDEN_ANSWERS_STORE[year]
    rows = []
    for item in CANONICAL_ITEMS:
        value = overrides[item] if item in overrides else golden[item]
        rows.append({"item": item, "answer_m_usd": value, "confidence": 0.9})
    return rows


print("\nSchema arithmetic (golden answers are internally consistent)")
SUBTOTALS = [
    ("Quick Assets", ["Cash & Cash Equivalents", "Accounts Receivable - Trade", "Other Quick Assets"]),
    ("Other Current Assets (subtotal)", ["Marketable Securities", "Short-term Loan", "Advance Payments", "Other Current Assets"]),
    ("Current Assets", ["Quick Assets", "Inventories, Net", "Other Current Assets (subtotal)"]),
    ("Tangible Assets", ["Land", "Buildings", "Plant & Machinery", "Construction in Progress", "Other Equipment", "Accumulated Depreciation"]),
    ("Financial Assets", ["Investments", "Long-term Loan", "Other Financial Assets"]),
    ("Fixed Assets", ["Tangible Assets", "Intangible Assets", "Financial Assets", "Other Fixed Assets"]),
    ("Total Assets", ["Current Assets", "Fixed Assets", "Deferred Charges"]),
]
check(
    "runtime gold contains only the assignment-supplied FY2022 key",
    set(GOLDEN_ANSWERS_STORE) == {"2022"},
)
check(
    "cross-year audit keys are bound to exact 64-character PDF hashes",
    {"2021", "2023", "2024", "2025"}.issubset(
        set(item["fiscal_year"] for item in SOURCE_BOUND_GOLDEN_ANSWERS.values())
    )
    and all(len(source_hash) == 64 for source_hash in SOURCE_BOUND_GOLDEN_ANSWERS),
)
for source_hash, audited in sorted(SOURCE_BOUND_GOLDEN_ANSWERS.items()):
    answers = audited["answers"]
    year = audited["fiscal_year"]
    if len(answers) == 27:
        report = reconcile(
            [{"item": row["item"], "answer_m_usd": answers[row["item"]]} for row in ASSET_SCHEMA],
            value_quantum=float(audited.get("source_value_quantum") or 1.0),
        )
        check(
            f"source-bound FY{year} subtotals reconcile",
            report["consistency"] == 100.0,
            str([item for item in report["checks"] if item["status"] == "failed"]),
        )
    else:
        unscorable = set(audited.get("unscorable_rows") or [])
        check(
            f"source-bound FY{year} partial key explicitly accounts for every schema row",
            set(answers).isdisjoint(unscorable)
            and set(answers).union(unscorable) == set(CANONICAL_ITEMS),
            f"answers={len(answers)}, unscorable={sorted(unscorable)}",
        )

for year, answers in sorted(GOLDEN_ANSWERS_STORE.items()):
    if len(answers) < 27:
        continue
    bad = [
        f"{total}={answers[total]} but parts sum to {sum(answers[p] for p in parts)}"
        for total, parts in SUBTOTALS
        if sum(answers[p] for p in parts) != answers[total]
    ]
    check(f"FY{year} subtotals reconcile", not bad, "; ".join(bad))

print("\nSchema shape")
check("schema has 27 rows", len(ASSET_SCHEMA) == 27 == EXPECTED_ROW_COUNT)
check("item names are unique", len(set(CANONICAL_ITEMS)) == len(CANONICAL_ITEMS))
import re as _re

ALL_GOLDEN = {v for answers in GOLDEN_ANSWERS_STORE.values() for v in answers.values() if abs(v) > 100}


def _leaks(text: str) -> list[int]:
    """Golden values appearing as standalone numbers (not inside a longer one)."""
    return sorted(v for v in ALL_GOLDEN if _re.search(rf"(?<!\d){abs(v)}(?!\d)", text))


check("no golden answer leaks into the system prompt", not _leaks(SYSTEM_PROMPT), str(_leaks(SYSTEM_PROMPT)))
user_prompt = build_user_prompt("--- PAGE 1 ---\nhello", "test extraction note", "2022")
check("user prompt carries the schema", '"Total Assets"' in user_prompt)
check("user prompt carries the extraction note", "test extraction note" in user_prompt)
check("user prompt carries the fiscal-year hint", "2022" in user_prompt)
check("no golden answer leaks into the user prompt", not _leaks(user_prompt), str(_leaks(user_prompt)))
jpy_prompt = build_user_prompt(
    "--- PAGE 1 ---\n（単位：百万円）", "test extraction note", "2022", output_currency="JPY"
)
check("JPY reports declare M JPY without authorizing FX", "means M JPY" in jpy_prompt
      and "No foreign-exchange conversion is authorized" in jpy_prompt
      and "means M USD" not in jpy_prompt)

def repaired(payload):
    """What the pipeline does: repair representation, then enforce the contract."""
    fixed, _ = normalize_payload(payload)
    return validate_extraction(fixed)


print("\nContract purity — models.py validates, it does not repair")
expect_error(
    "a formatted number string is a contract violation, not silently parsed",
    lambda: validate_extraction({"rows": golden_rows("2022", **{"Land": "255"})}),
    "must be a JSON number",
)
expect_error(
    "an unknown item name is a contract violation, not aliased away",
    lambda: validate_extraction({"rows": [{**r, "item": "Cash and Cash Equivalents"} if r["item"] == "Cash & Cash Equivalents" else r for r in golden_rows("2022")]}),
    "not one of the",
)
expect_error(
    "out-of-order rows are a contract violation, not silently sorted",
    lambda: validate_extraction({"rows": list(reversed(golden_rows("2022")))}),
    "order",
)
expect_error(
    "a non-4-digit fiscal year is rejected",
    lambda: validate_extraction({"detected_fiscal_year": "FY2022", "rows": golden_rows("2022")}),
    "4-digit",
)
check(
    "models.py exposes no coercion or scoring helpers",
    not any(hasattr(__import__("models"), n) for n in ("coerce_money", "canonical_item", "compute_metrics")),
)

print("\nNumber parsing (normalize.py)")
cases = {
    1234: 1234.0,
    "1,234": 1234.0,
    "$1,234": 1234.0,
    "(16,820)": -16820.0,
    "-16820": -16820.0,
    "−16820": -16820.0,
    "": None,
    "—": None,
    "N/A": None,
    None: None,
    "1234 M": 1234.0,
}
for raw, expected in cases.items():
    check(f"parse_money({raw!r}) == {expected!r}", parse_money(raw) == expected)
check("an unparseable value is passed through untouched, not guessed", parse_money("about four") == "about four")
check("parse_confidence('95%') == 0.95", abs(parse_confidence("95%") - 0.95) < 1e-9)
check("parse_confidence(92) == 0.92", abs(parse_confidence(92) - 0.92) < 1e-9)
check("missing confidence is not promoted to certainty", parse_confidence(None) is None)
check("canonical_item maps a known variant", canonical_item("Cash and Cash Equivalents") == "Cash & Cash Equivalents")
check("canonical_item returns None for an unknown name", canonical_item("Crypto Holdings") is None)

print("\nRepair + validate (the pipeline path)")
result = repaired({"detected_fiscal_year": "FY2022", "rows": golden_rows("2022")})
check("fiscal year normalized to 4 digits", result.detected_fiscal_year == "2022")
check("all rows validated", len(result.rows) == EXPECTED_ROW_COUNT)
check(
    "classification is taken from the schema, not the model",
    result.rows[0].classification == ASSET_SCHEMA[0]["classification"],
)

shuffled = list(reversed(golden_rows("2022")))
check(
    "normalize reorders rows, then the contract accepts them",
    [r.item for r in repaired({"rows": shuffled}).rows] == CANONICAL_ITEMS,
)
_, notes = normalize_payload({"rows": shuffled})
check("the reorder is reported as a repair, not hidden", any("reorder" in n for n in notes), str(notes))

aliased = golden_rows("2022")
aliased[3]["item"] = "Accounts Receivable (Trade)"
aliased[2]["item"] = "Cash and Cash Equivalents"
check(
    "common item-name variants are repaired, then accepted",
    [r.item for r in repaired({"rows": aliased}).rows] == CANONICAL_ITEMS,
)
_, notes = normalize_payload({"rows": aliased})
check("the rename is reported as a repair", any("renamed" in n for n in notes), str(notes))

stringly = golden_rows("2022")
stringly[0]["answer_m_usd"] = "14,688"
stringly[18]["answer_m_usd"] = "(16,820)"
stringly[0]["confidence"] = "95%"
stringly[1]["confidence"] = 92
parsed = repaired({"rows": stringly})
check("string money is parsed", parsed.rows[0].answer_m_usd == 14688.0)
check("parenthesised negative is parsed", parsed.rows[18].answer_m_usd == -16820.0)
check("percent confidence is scaled to 0-1", abs(parsed.rows[0].confidence - 0.95) < 1e-9)
check("0-100 confidence is scaled to 0-1", abs(parsed.rows[1].confidence - 0.92) < 1e-9)

bare_list = repaired(golden_rows("2022"))
check("a bare list of rows is accepted", len(bare_list.rows) == EXPECTED_ROW_COUNT)

print("\nRejections that survive repair")
expect_error("missing rows are rejected", lambda: repaired({"rows": golden_rows("2022")[:10]}), "expected exactly")
expect_error(
    "an unrecognizable item name is rejected",
    lambda: repaired({"rows": golden_rows("2022") + [{"item": "Crypto Holdings", "answer_m_usd": 1, "confidence": 0.5}]}),
    "not one of the",
)
duplicated = golden_rows("2022")
duplicated[5]["item"] = duplicated[4]["item"]
expect_error("duplicate rows are rejected", lambda: repaired({"rows": duplicated}), "duplicate")
expect_error("unparseable money is rejected", lambda: repaired({"rows": golden_rows("2022", Land="about four")}), "must be a JSON number")
missing_confidence = golden_rows("2022")
missing_confidence[0].pop("confidence")
expect_error(
    "missing confidence survives repair and is rejected by the contract",
    lambda: repaired({"rows": missing_confidence}),
    "confidence",
)
expect_error("a non-object payload is rejected", lambda: repaired("nope"), "rows")

print("\nMetrics")
from pipeline import CONFIDENCE_THRESHOLD
check("confidence threshold is the measured 0.8, not 0.5", CONFIDENCE_THRESHOLD == 0.8)
_borderline = golden_rows("2022")
for _r in _borderline:
    _r["confidence"] = 0.75
_b = rows_as_dicts(repaired({"rows": _borderline}))
check(
    "a 0.75-confidence answer remains covered but is flagged for review",
    compute_metrics(_b, "2022")["filled_fields"] == EXPECTED_ROW_COUNT
    and compute_metrics(_b, "2022")["confidence_accepted_fields"] == 0,
)
_ok = golden_rows("2022")
for _r in _ok:
    _r["confidence"] = 0.85
check(
    "a 0.85-confidence answer is counted",
    compute_metrics(rows_as_dicts(repaired({"rows": _ok})), "2022")["filled_fields"] == EXPECTED_ROW_COUNT,
)
perfect = rows_as_dicts(repaired({"rows": golden_rows("2022")}))
m = compute_metrics(perfect, "2022", company="3M", source_pdf_sha256=ASSIGNMENT_GOLDEN_SOURCE_SHA256)
check("a perfect prediction scores 100%", m["accuracy"] == 100.0, json.dumps(m))
check("a perfect prediction has full coverage", m["coverage"] == 100.0)

one_wrong = rows_as_dicts(repaired({"rows": golden_rows("2022", Land=999)}))
m = compute_metrics(one_wrong, "2022", company="3M", source_pdf_sha256=ASSIGNMENT_GOLDEN_SOURCE_SHA256)
check("one wrong value costs exactly one item", m["exact_matches"] == EXPECTED_ROW_COUNT - 1)

nulled = golden_rows("2022")
for row in nulled:
    if row["item"] in ("Other Quick Assets", "Short-term Loan", "Advance Payments", "Long-term Loan", "Deferred Charges"):
        row["answer_m_usd"] = None
        row["confidence"] = 0.0
nulled_rows = rows_as_dicts(repaired({"rows": nulled}))
m = compute_metrics(nulled_rows, "2022", company="3M", source_pdf_sha256=ASSIGNMENT_GOLDEN_SOURCE_SHA256)
check("null never counts as a match for a golden 0", m["exact_matches"] == EXPECTED_ROW_COUNT - 5, json.dumps(m))
check("null values do not count as coverage", m["filled_fields"] == EXPECTED_ROW_COUNT - 5)

m = compute_metrics(perfect, "2019")
check("a year with no answer key is not scored", m["accuracy"] is None and m["has_golden"] is False)
check("coverage is still reported without an answer key", m["coverage"] == 100.0)

m = compute_metrics(perfect, "2025")
check(
    "a non-assignment year remains unscored until human approval",
    m["accuracy"] is None and m["has_golden"] is False and m["total_compared"] == 0,
    json.dumps(m),
)

print("\nProvider reply parsing")
payload = json.dumps({"detected_fiscal_year": "2022", "rows": []})
check(
    "fenced JSON is unwrapped",
    parse_assistant_json({"choices": [{"message": {"content": f"```json\n{payload}\n```"}}]})["detected_fiscal_year"] == "2022",
)
check(
    "JSON with a prose preamble is recovered",
    parse_assistant_json({"choices": [{"message": {"content": f"Sure, here it is:\n{payload}"}}]})["detected_fiscal_year"] == "2022",
)
check(
    "braces inside strings do not break recovery",
    parse_assistant_json({"choices": [{"message": {"content": 'note {\n{"a": "}", "b": 2}'}}]})["b"] == 2,
)

print("\nText normalization")
check("non-breaking spaces are folded", normalize_text("Total assets") == "Total assets")
check("unicode minus is folded", normalize_text("−16,820") == "-16,820")
check("ligatures are expanded", normalize_text("beneﬁt") == "benefit")
check("clean text is not flagged as garbled", garble_ratio("Total current assets 14,688") < 0.01)
check("glyph-code text is flagged as garbled", garble_ratio("\x1cIFF9BH\x015GG9HG\x01\x11\t\x12\x13\x11") > 0.15)

# Docling maps the same unmapped glyphs into printable ASCII, so a character-class
# test alone reports those pages as readable. Measured on this corpus: mojibake
# pages score 0.38-0.45 on mixed_token_ratio, every readable page scores 0.00.
_MOJIBAKE = "B@C4AL 4A7 *H5F<7<4E<8F BAFB?<74G87 4?4A68 *;88G G 868@58E B??4EF <A @<??<BAF " * 4
_TABLE = "United States International Total 3,861 3,716 3,795 Millions Income Before Taxes 2,531 3,488 " * 4
_MARKDOWN = "|**$**<br>**3,861**|$ 3,716|**Deferred income taxes**|**959**|$ 581|" * 8
check("printable-ASCII mojibake is detected", mixed_token_ratio(_MOJIBAKE) >= 0.15, f"{mixed_token_ratio(_MOJIBAKE):.2f}")
check("a numeric financial table is not flagged", mixed_token_ratio(_TABLE) < 0.15, f"{mixed_token_ratio(_TABLE):.2f}")
check("a markdown table is not flagged", mixed_token_ratio(_MARKDOWN) < 0.15, f"{mixed_token_ratio(_MARKDOWN):.2f}")
check("page_is_unreadable combines both tests", page_is_unreadable(_MOJIBAKE) and not page_is_unreadable(_TABLE))
# PyMuPDF4LLM substitutes U+FFFD for the same unmapped glyphs PyPDF leaves as
# control bytes; both extractors must flag the same page.
check("replacement characters are flagged as garbled", garble_ratio("\ufffd" * 20 + "abcd") > 0.15)
_empty_extract = _finalize([(1, ""), (2, "")], 2, "test parser")
check("empty-page PDFs are reported as unreadable", _empty_extract.readable_pages == 0)
check("empty-page PDFs carry an actionable OCR warning",
      any("OCR" in warning for warning in _empty_extract.warnings))

from corpus.screen import _balance_sheet_page
_screen_text = """--- PAGE 38 ---
Balance Sheet:\nCurrent assets 10\nCash 5\nInventory 2\nLiabilities 4
--- PAGE 50 ---
Consolidated Balance Sheet\nAssets\nCurrent assets\nCash and cash equivalents 5\nInventories 2\nProperty, plant and equipment 3\nAccumulated depreciation (1)\nGoodwill 4\nIntangible assets 2\nTotal assets 15\nLiabilities 8
"""
check("screening prefers the audited statement over earlier balance-sheet prose",
      _balance_sheet_page(_screen_text) == 50)

# --- Adaptive rate limiting --------------------------------------------------
print("\nAdaptive rate limiting")
from ratelimit import AdaptiveLimiter, estimate_batch_plan, retry_after_seconds

limiter = AdaptiveLimiter(concurrency=8)
check("starts at the requested concurrency", limiter.snapshot()["permitted_concurrency"] == 8)
limiter.note_throttled(retry_after=0.01)
check("a 429 halves permitted concurrency", limiter.snapshot()["permitted_concurrency"] == 4)
limiter.note_throttled(retry_after=0.01)
check("a second 429 halves it again", limiter.snapshot()["permitted_concurrency"] == 2)
for _ in range(4):
    limiter.note_success()
check("sustained success restores one permit", limiter.snapshot()["permitted_concurrency"] == 3)
check("never drops below 1", AdaptiveLimiter(1).note_throttled(0.01) > 0)
limiter.note_headers({"X-RateLimit-Limit-Requests": "60", "Retry-After": "12"})
check("provider headers are recorded", limiter.snapshot()["observed_headers"]["requests_limit"] == "60")
check("Retry-After seconds are parsed", retry_after_seconds({"retry-after": "30"}, None) == 30.0)
check("compound durations are parsed", retry_after_seconds({"retry-after": "1m30s"}, None) == 90.0)

plan = estimate_batch_plan([{"name": "a.pdf", "pages": 141, "approx_tokens": 130000}], 5)
check("a batch plan reports estimated tokens", plan["total_approx_tokens"] == 130000)
check("a batch plan never recommends more lanes than files", plan["recommended_concurrency"] == 1)
check("routine plans do not surface an unpublished-limit advisory", not any("RPM/TPM" in a for a in plan["advisories"]))

# --- Deterministic reconciliation (reconcile.py) ------------------------------
print("\nArithmetic reconciliation")
from reconcile import TOLERANCE, reconcile, reconciliation_summary
from schema import SUBTOTAL_IDENTITIES

check("every identity references only schema items",
      all(t in CANONICAL_ITEMS and all(p in CANONICAL_ITEMS for p in parts)
          for t, parts in SUBTOTAL_IDENTITIES))
check("all seven identities are covered", len(SUBTOTAL_IDENTITIES) == 7)

_perfect = [{"item": i, "answer_m_usd": GOLDEN_ANSWERS_STORE["2022"][i]} for i in CANONICAL_ITEMS]
_rep = reconcile(_perfect)
check("a correct answer reconciles fully", _rep["consistency"] == 100.0 and _rep["failed"] == 0)

_rounded = [{**row} for row in _perfect]
next(row for row in _rounded if row["item"] == "Current Assets")["answer_m_usd"] += 2
_rounded_check = next(
    check_row for check_row in reconcile(_rounded, value_quantum=1.0)["checks"]
    if check_row["total_item"] == "Current Assets"
)
check("whole-million rounding uses the schema-leaf propagation bound",
      _rounded_check["status"] == "ok" and _rounded_check["tolerance"] == 4.5)

_bad = [{"item": i, "answer_m_usd": (GOLDEN_ANSWERS_STORE["2022"][i] + 500 if i == "Land"
                                     else GOLDEN_ANSWERS_STORE["2022"][i])} for i in CANONICAL_ITEMS]
_rb = reconcile(_bad)
check("a broken component fails its identity", "Tangible Assets" in _rb["failed_identities"])
check("only the affected identity fails", _rb["failed"] == 1, str(_rb["failed_identities"]))

_null = [{"item": i, "answer_m_usd": (None if i == "Land" else GOLDEN_ANSWERS_STORE["2022"][i])}
         for i in CANONICAL_ITEMS]
_rn = reconcile(_null)
check("a null makes its identity unevaluable, not failed", _rn["skipped"] == 1 and _rn["failed"] == 0)

_allnull = [{"item": i, "answer_m_usd": None} for i in CANONICAL_ITEMS]
check("an all-null answer does not score 100% consistency",
      reconcile(_allnull)["consistency"] is None)

check("reconciliation never mutates the rows",
      [r["answer_m_usd"] for r in _bad] ==
      [GOLDEN_ANSWERS_STORE["2022"][i] + 500 if i == "Land" else GOLDEN_ANSWERS_STORE["2022"][i]
       for i in CANONICAL_ITEMS])
check("summary is human readable", "identities hold" in reconciliation_summary(_rep))

# --- The confidence gate and reconciliation must agree -----------------------
print("\nGate consistency across scoring and reconciliation")
from pipeline import apply_confidence_gate

_rows = [{"item": i, "answer_m_usd": GOLDEN_ANSWERS_STORE["2022"][i], "confidence": 0.95}
         for i in CANONICAL_ITEMS]
for _r in _rows:
    if _r["item"] == "Land":
        _r["confidence"] = 0.4          # correct value, but the model was unsure

_gated = apply_confidence_gate(_rows)
_land = next(r for r in _gated if r["item"] == "Land")
check("the gate stamps 'accepted' rather than nulling the value",
      _land["accepted"] is False and _land["answer_m_usd"] == GOLDEN_ANSWERS_STORE["2022"]["Land"])

_m = compute_metrics(_gated, "2022")
check("scoring retains a low-confidence extracted row", _m["filled_fields"] == EXPECTED_ROW_COUNT)
check("confidence acceptance remains separately observable",
      _m["confidence_accepted_fields"] == EXPECTED_ROW_COUNT - 1)

_rec = reconcile(_gated)
check("reconciliation uses a correct low-confidence value",
      "Tangible Assets" not in [c["total_item"] for c in _rec["checks"] if c["status"] == "skipped"],
      str(_rec["failed_identities"]))
check("a correct low-confidence value preserves arithmetic", _rec["failed"] == 0)

# --- Run records must identify the parser that produced them ------------------
print("\nParser identity in run records")
from extraction import STRATEGIES

check("every strategy has a unique run-id prefix",
      len({s.run_prefix for s in STRATEGIES.values()}) == len(STRATEGIES))
check("Strategy 1 is no-OCR and Strategy 2 is OCR-enabled",
      all(STRATEGIES[key].label.startswith("Strategy 1") and not STRATEGIES[key].ocr_enabled
          for key in ("s1", "s1-pymupdf", "s1-docling", "s1-inspector"))
      and all(STRATEGIES[key].label.startswith("Strategy 2") and STRATEGIES[key].ocr_enabled
              for key in ("s2-pypdf", "s2", "s2-docling", "s2-inspector"))
      and get_strategy(None).key == "s1")
check(
    "the matched four-by-two arms and finalized Strategy 3 are registered",
    set(STRATEGIES) == {
        "s1", "s1-pymupdf", "s1-docling", "s1-inspector",
        "s2-pypdf", "s2", "s2-docling", "s2-inspector",
        "s3",
    }
    and {strategy.parser for strategy in STRATEGIES.values()} == {
        "pypdf", "pymupdf", "docling", "inspector", "inspector-gate",
    }
    and {strategy.experiment for strategy in STRATEGIES.values()} == {"no_ocr", "ocr", "intelligent_scan"},
)
expect_error("unknown strategy keys do not silently run Strategy 1",
             lambda: get_strategy("s9"), "Unknown strategy")

from pipeline import result_table
_export_rows = apply_confidence_gate([
    {"classification": "A", "subclassification": "", "item": "A",
     "description": "", "answer_m_usd": 10, "confidence": 0.4}
])
check("generic exports retain confidence-flagged values for review",
      result_table(_export_rows)[0]["Answer (M USD)"] == 10)

# --- Run storage layout ------------------------------------------------------
print("\nRun storage layout")
from pipeline import PENDING, fiscal_year_folder

check("fiscal year folder is FY-prefixed", fiscal_year_folder("2022") == "FY2022")
check("a detected 'FY 2022' still files under FY2022", fiscal_year_folder("FY 2022") == "FY2022")
check("a missing year files under FY-unknown", fiscal_year_folder("") == "FY-unknown")
check("pending folder is namespaced", PENDING.startswith("_"))


# --- Quota exhaustion is not a retryable rate limit ---------------------------
print("\nQuota vs rate limit")
from api_client import _quota_message

check("provider code 1308 is recognised as spent allowance",
      _quota_message({"error": {"code": "1308", "message": "Usage limit reached for 5 hour."}}) is not None)
check("an ordinary rate limit is not treated as quota exhaustion",
      _quota_message({"error": {"code": "1302", "message": "Rate limit reached for requests"}}) is None)
check("the provider's reset time is preserved for the user",
      "reset" in (_quota_message({"error": {"code": "1308",
          "message": "Usage limit reached. Your limit will reset at 19:35:47"}}) or ""))


# --- Multi-provider config and prompt caching --------------------------------
print("\nProviders, reasoning and prompt caching")
from providers import (DEFAULT_PROVIDER, PROVIDERS, REASONING_EFFORTS, cache_usage,
                       get_provider, reasoning_payload)

check("OpenRouter is the default provider", DEFAULT_PROVIDER == "openrouter")
check("DeepSeek V4 Flash is the default model",
      PROVIDERS["openrouter"].default_model == "deepseek/deepseek-v4-flash-0731")
check("Z.AI uses the thinking parameter",
      "thinking" in reasoning_payload(get_provider("zai"), "high"))
check("OpenRouter uses the reasoning parameter",
      reasoning_payload(get_provider("openrouter"), "high") == {"reasoning": {"effort": "high"}})
check("effort 'none' disables reasoning on OpenAI-style providers",
      reasoning_payload(get_provider("openrouter"), "none") == {"reasoning": {"effort": "none"}})
check("effort 'none' disables thinking on Z.AI",
      reasoning_payload(get_provider("zai"), "none") == {"thinking": {"type": "disabled"}})
check("an unknown effort falls back to medium, not to an invalid value",
      reasoning_payload(get_provider("openrouter"), "banana") == {"reasoning": {"effort": "medium"}})
check("every effort level is accepted by every provider",
      all(reasoning_payload(p, e) for p in PROVIDERS.values() for e in REASONING_EFFORTS))

_usage = cache_usage({"prompt_tokens": 100, "completion_tokens": 10,
                      "prompt_tokens_details": {"cached_tokens": 25}, "cost": 0.5})
check("cache hits are read from prompt_tokens_details", _usage["cached_tokens"] == 25)
check("cache hit rate is derived", _usage["cache_hit_rate"] == 25.0)
check("absent usage yields no invented numbers", cache_usage(None) == {})

# The cacheable prefix must stay a prefix: fixed content before anything variable.
_a = build_user_prompt("DOC A", "note A", "2022", {"source": "pdf-inspector"})
_b = build_user_prompt("DOC B entirely different", "note B", "", {"source": "PyPDF"})
_shared = 0
for _x, _y in zip(_a, _b):
    if _x != _y:
        break
    _shared += 1
check("TARGET_SCHEMA sits inside the shared prefix", _a.index("TARGET_SCHEMA") < _shared)
check("the fiscal-year hint sits after it", _a.index("TARGET_SCHEMA") < _a.index("ANNUAL REPORT"))
check("cacheable prefix clears OpenAI's 1024-token minimum",
      (len(SYSTEM_PROMPT) + _shared) // 4 > 1024, f"{(len(SYSTEM_PROMPT) + _shared)//4} tokens")

_original_post_json = api_client_module._post_json
try:
    api_client_module._post_json = lambda **_kwargs: ({
        "choices": [{"message": {"content": "{}"}}],
        "usage": {},
    }, 0.01, 200)
    with TemporaryDirectory() as _tmp:
        _repair_messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "original"},
            {"role": "assistant", "content": "invalid"},
            {"role": "user", "content": "repair"},
        ]
        run_extraction(
            api_key="test", model="test-model", base_url="https://example.invalid",
            system_prompt="system", user_prompt="original", run_dir=Path(_tmp),
            enable_reasoning=False, messages=_repair_messages, artifact_suffix="_repair_1",
        )
        _repair_request = json.loads((Path(_tmp) / "request_repair_1.json").read_text())
        check("contract repair preserves the complete prior message context",
              _repair_request["payload"]["messages"] == _repair_messages)
        check("contract repair artifacts do not overwrite the original response",
              (Path(_tmp) / "raw_response_repair_1.json").is_file()
              and not (Path(_tmp) / "raw_response.json").exists())
finally:
    api_client_module._post_json = _original_post_json


# --- Firecrawl credential probe ---------------------------------------------
print("\nFirecrawl credential verification")
from corpus.client import FirecrawlClient, FirecrawlError


class _CreditResponse:
    def __init__(self, status: int, body: dict):
        self.status_code = status
        self._body = body
        self.ok = 200 <= status < 300
        self.text = json.dumps(body)

    def json(self):
        return self._body


class _CreditSession:
    def __init__(self, response: _CreditResponse):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


_fc = FirecrawlClient("fc-test", timeout=90)
_fc.session = _CreditSession(_CreditResponse(200, {
    "success": True,
    "data": {"remainingCredits": 9988, "planCredits": 10000},
}))
_credits = _fc.credit_usage()
check("credit-usage verifies a key without starting a crawl",
      _credits["remainingCredits"] == 9988 and len(_fc.session.calls) == 1)
check("the credential probe has a short bounded timeout",
      _fc.session.calls[0][1]["timeout"] == 20)

_bad_fc = FirecrawlClient("fc-test")
_bad_fc.session = _CreditSession(_CreditResponse(401, {"success": False, "error": "Unauthorized"}))
try:
    _bad_fc.credit_usage()
except FirecrawlError as _exc:
    check("an invalid Firecrawl key is rejected before persistence", "401" in str(_exc))
else:
    check("an invalid Firecrawl key is rejected before persistence", False)


print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
    sys.exit(1)
print("All checks passed.")
