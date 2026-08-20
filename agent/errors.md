# Errors, gotchas & known issues

## Contract failures were not semantically retried (resolved)
- Symptom: A provider could return evidence-bearing JSON with one schema defect, but the run failed immediately after deterministic normalization.
- Cause: Existing retries covered only 429/eligible 5xx transport responses and repeated the same request; no repair turn included the invalid assistant response or Pydantic error.
- Resolution: Added one bounded repair turn with full prior context and separate `_repair_1` request/response artifacts. Confidence prompt wording now matches the 0.80 downstream gate.
- First seen: 2026-08-21

## Final theme layer hardcoded light colors (resolved)
- Symptom: Switching to dark mode changed the page shell but left cards, task rows, result sheets, inputs, and labels in the light palette.
- Cause: `editor-theme.css` loaded last, but many of its component rules used literal light colors instead of the theme tokens it also defined.
- Resolution: Added semantic dark overrides for every component family and kept the same slate/blue/peach visual system across both modes. In-app browser checks now cover the rendered dark Settings and Strategy 2 states.
- First seen: 2026-08-21

## Runtime checkbox inherited text-input width (resolved)
- Symptom: “Automatic batch sizing” wrapped vertically and the checkbox consumed most of the Settings card.
- Cause: `.runtime-grid input:not([type='range'])` also matched checkbox inputs.
- Resolution: Added a higher-specificity checkbox rule and rendered the control as a bounded 44px switch.
- First seen: 2026-08-21

## UI had no regression boundary (resolved)
- Symptom: Strategy 1 and Strategy 2 behavior can diverge or break without test failures.
- Cause: The legacy UI is a large static HTML/CSS/JS surface with duplicated DOM-id branches; the Python contract suite does not exercise it.
- Resolution: Replaced the delivery surface with typed React components, a tested SSE adapter, and browser QA across all routes.
- First seen: 2026-08-20

## FY2021 PDF has an unusable text layer
- Symptom: All text-only strategies score approximately 3.7% on FY2021.
- Cause: The source PDF's balance-sheet text layer is broken.
- Resolution: Detect and explain the condition; a future OCR strategy is required for recovery.
- First seen: 2026-08-20

## System Python lacks test dependencies
- Symptom: `python3 -m pytest` fails because pytest is absent.
- Cause: Project dependencies are installed in `.venv`; the test suite is a standalone script, not pytest-based.
- Resolution: Use `.venv/bin/python test_contract.py`.
- First seen: 2026-08-20

## FY2025 uses a partial golden key
- Symptom: Accuracy and coverage can differ because only 19 of 27 FY2025 rows are scored.
- Cause: The supplied benchmark omits eight rows rather than inventing answers.
- Resolution: Score only defined golden rows and continue reporting 27-row output coverage independently.
- First seen: 2026-08-20
