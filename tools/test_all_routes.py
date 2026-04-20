"""Brute-force every source-file × target-console combo through the engine.

Run from repo root:  python tools/test_all_routes.py

Writes a JSON report to .tmp/test_all_routes_report.json summarizing:
  - which files parse successfully by source console
  - which translation routes succeed
  - which routes fail, with the actual exception message
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "engine"))

from translator import translate, PARSERS, WRITERS, UnsupportedConsolePair  # noqa: E402

SAMPLES = REPO / "samples"
OUT = REPO / ".tmp" / "test_all_routes_report.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# Filename extension -> source console id
EXT_TO_SOURCE = {
    ".clf": "yamaha_cl",
    ".cle": "yamaha_cl",
    ".dm7f": "yamaha_dm7",
    ".tff": "yamaha_tf",
    ".rivagepm": "yamaha_rivage",
    ".show": "digico_sd",
}

# Targets we actually have writers for
TARGETS = [t for t in WRITERS.keys() if t != "ah_dlive"]

report: dict = {"files": {}, "summary": {}}

for f in sorted(SAMPLES.iterdir()):
    if not f.is_file():
        continue
    ext = f.suffix.lower()
    src = EXT_TO_SOURCE.get(ext)
    if src is None:
        continue

    entry: dict = {"source_console": src, "size_bytes": f.stat().st_size, "routes": {}}

    # First, try parsing alone (source console → any valid writer we know works)
    # Pick a target that isn't the same as source.
    for tgt in TARGETS:
        if tgt == src:
            continue
        try:
            result = translate(source_file=f, source_console=src, target_console=tgt)
            entry["routes"][tgt] = {
                "status": "ok",
                "channel_count": result.channel_count,
                "parse_gate_passed": result.parse_gate_passed,
                "fidelity_overall": (
                    round(result.fidelity_score.overall, 2)
                    if result.fidelity_score else None
                ),
                "output_bytes": len(result.output_bytes),
            }
        except UnsupportedConsolePair as e:
            entry["routes"][tgt] = {"status": "unsupported_pair", "error": str(e)}
        except Exception as e:  # noqa: BLE001
            entry["routes"][tgt] = {
                "status": "error",
                "error_type": type(e).__name__,
                "error": str(e),
                "trace": traceback.format_exc().splitlines()[-6:],
            }
    report["files"][f.name] = entry

# Roll up summary
totals = {"ok": 0, "error": 0, "unsupported_pair": 0}
errors_by_type: dict[str, list[str]] = {}
for fname, entry in report["files"].items():
    for tgt, rr in entry["routes"].items():
        totals[rr["status"]] = totals.get(rr["status"], 0) + 1
        if rr["status"] == "error":
            key = rr.get("error_type", "Unknown") + ": " + rr["error"][:120]
            errors_by_type.setdefault(key, []).append(f"{fname} → {tgt}")
report["summary"]["totals"] = totals
report["summary"]["errors_by_type"] = errors_by_type

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Wrote {OUT}")
print("Totals:", totals)
print("Unique error types:", len(errors_by_type))
for k, routes in errors_by_type.items():
    print(f"\n--- {k}")
    for r in routes[:5]:
        print(f"    {r}")
    if len(routes) > 5:
        print(f"    ... +{len(routes)-5} more")
