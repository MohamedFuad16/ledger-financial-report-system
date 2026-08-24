"""Dated correction for the Juju gazette gold (run from repo root).

Both printed component sets independently sum to 1,226,820 thousand yen
(assets: 790,717+435,286+817; liabilities+equity: 142,089+552,815+531,916)
while both printed 合計 lines read 1,266,820 — a print transposition. The
double-closure value is authoritative.
"""
import json
from pathlib import Path

for fixture in (Path("benchmark_data/bakuraku_statutory_gold.json"), Path("benchmark_data/year_expansion_gold.json")):
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    documents = payload.get("documents") or {}
    changed = False
    for sha, entry in documents.items():
        if entry.get("company") != "株式会社寿々":
            continue
        answers = entry.get("answers") or {}
        answers.update({"Total Assets": 1226.820, "Current Assets": 790.717, "Fixed Assets": 435.286, "Deferred Charges": 0.817})
        for item in ("Current Assets", "Fixed Assets", "Deferred Charges"):
            if item in (entry.get("unscorable_rows") or []):
                entry["unscorable_rows"].remove(item)
        entry["answers"] = answers
        entry["scorable_rows"] = sum(1 for v in answers.values() if v is not None)
        entry.setdefault("citations", {})["Total Assets"] = (
            "2026-08-25 correction (dated): the gazette prints 合計 1,266,820 on both sides, but the printed "
            "components independently sum to 1,226,820 on the asset side (790,717+435,286+817) AND on the "
            "liabilities+equity side (142,089+552,815+531,916) — a print transposition in the totals. The "
            "double-closure value 1,226,820 thousand yen is authoritative. Previous gold (1,266.82) followed the misprint."
        )
        for item in ("Current Assets", "Fixed Assets", "Deferred Charges"):
            entry["citations"][item] = (
                "2026-08-25 expansion: printed on the gazette page; visually verified; closes both balance-sheet identities."
            )
        changed = True
    if changed:
        fixture.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Juju corrected in", fixture.name)
