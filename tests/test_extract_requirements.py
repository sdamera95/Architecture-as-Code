"""Test the Tier 1 design-time requirement evaluation added in Stage C.

Loads `demos/uav/uav_trade_study.sysml` and asserts that
`bridge.extract_architecture.extract_requirements()` returns the expected 3
RequirementDefinition records with names, docs, and passed states matching the
trade-study's baseline (all 3 should evaluate to `passed=True` against the
default attribute values declared in the `part def UAV`).

Run directly:
    uv run python tests/test_extract_requirements.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make bridge/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))

import syside  # noqa: E402
from extract_architecture import extract_requirements  # noqa: E402

MODEL = Path(__file__).resolve().parents[1] / "demos" / "uav" / "uav_trade_study.sysml"

passed = 0
failed = 0
total = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}{(' — ' + detail) if detail else ''}")


print(f"=" * 60)
print(f"  Stage C — Tier 1 requirement evaluation")
print(f"  Model: {MODEL.name}")
print(f"=" * 60)

model, diagnostics = syside.load_model([str(MODEL)], warnings_as_errors=True)
n_errors = sum(1 for d in (diagnostics.collect() if hasattr(diagnostics, "collect") else []) if getattr(d, "is_error", False))
check("Model loads without errors", n_errors == 0, f"{n_errors} errors")

reqs = extract_requirements(model)
check("extract_requirements() returns 3 records", len(reqs) == 3, f"got {len(reqs)}")

names = {r["name"] for r in reqs}
expected = {"MassBudget", "EnduranceRequirement", "PowerBudget"}
check("Names match expected", names == expected, f"got {names}, expected {expected}")

for r in reqs:
    check(f"{r['name']}: kind=='definition'", r["kind"] == "definition", f"got {r['kind']}")
    check(f"{r['name']}: constraint_count==1", r["constraint_count"] == 1, f"got {r['constraint_count']}")
    check(f"{r['name']}: doc is non-empty", bool(r["doc"]), "doc was empty/None")
    check(f"{r['name']}: passed==True (baseline)", r["passed"] is True, f"got {r['passed']}")
    check(f"{r['name']}: fatal==False", r["fatal"] is False, f"got {r['fatal']}")

# Verify JSON-serializability (the architecture.json downstream consumer requires this)
import json
try:
    serialized = json.dumps(reqs, indent=2)
    check("Records are JSON-serializable", True)
    check("Serialized output is non-trivial", len(serialized) > 100, f"length={len(serialized)}")
except (TypeError, ValueError) as e:
    check("Records are JSON-serializable", False, str(e))

print(f"\n{'=' * 60}")
print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
print(f"{'=' * 60}")

if failed > 0:
    sys.exit(1)
