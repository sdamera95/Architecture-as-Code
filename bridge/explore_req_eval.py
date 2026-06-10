"""
Stage C.1: explore the Syside 0.9.0 `compiler.evaluate(req, stdlib=..., experimental_quantities=True)`
API surface against `demos/uav/uav_trade_study.sysml`.

Goal: characterize what RequirementDefinitions vs RequirementUsages look like in the
model, what the evaluation filter (`isinstance(req.owning_type, syside.Usage)`) admits
and excludes, and what the `(value, report)` tuple actually contains. This is a
de-risk script for C.4 (`extract_requirements()` integration into the bridge pipeline).

Run from project root:
    uv run python bridge/explore_req_eval.py
"""

from __future__ import annotations

import pathlib

import syside

MODEL_PATH = pathlib.Path(__file__).resolve().parents[1] / "demos" / "uav" / "uav_trade_study.sysml"
STDLIB = syside.Environment.get_default().lib


def safe_type(obj) -> str:
    return type(obj).__name__ if obj is not None else "None"


def main() -> None:
    print(f"loading model: {MODEL_PATH}")
    model, diagnostics = syside.load_model([str(MODEL_PATH)], warnings_as_errors=True)

    diag_list = list(diagnostics.collect()) if hasattr(diagnostics, "collect") else []
    n_errors = sum(1 for d in diag_list if getattr(d, "is_error", False))
    n_warnings = sum(1 for d in diag_list if getattr(d, "is_warning", False))
    print(f"  diagnostics: {n_errors} errors, {n_warnings} warnings, {len(diag_list)} total")
    print()

    # --- enumerate RequirementDefinition (defs are NOT Features; they don't have owning_type) ---
    print("=== RequirementDefinitions ===")
    req_defs = list(model.elements(syside.RequirementDefinition))
    for rd in req_defs:
        owner = getattr(rd, "owner", None) or getattr(rd, "owning_namespace", None)
        print(f"  def: {rd.qualified_name}")
        print(f"      owner: {safe_type(owner)} ({owner.qualified_name if owner else '—'})")
        # list owned constraint usages (these contain the `require constraint { ... }`)
        constraints = [
            e for e in rd.owned_elements.collect()
            if e.try_cast(syside.ConstraintUsage)
        ]
        print(f"      owned ConstraintUsages: {len(constraints)}")
    print(f"  total RequirementDefinitions: {len(req_defs)}")
    print()

    # --- enumerate RequirementUsage ---
    print("=== RequirementUsages (include_subtypes=True) ===")
    req_usages = list(model.elements(syside.RequirementUsage, include_subtypes=True))
    for ru in req_usages:
        ot = ru.owning_type
        is_usage = isinstance(ot, syside.Usage)
        is_composite = getattr(ru, "is_composite", "?")
        print(f"  usage: {ru.qualified_name}")
        print(f"      owning_type: {safe_type(ot)} ({ot.qualified_name if ot else '—'})  is_Usage={is_usage}  is_composite={is_composite}")
    print(f"  total RequirementUsages: {len(req_usages)}")
    print()

    # --- apply the canonical 0.9.0 filter from the Syside docs ---
    print("=== filtered (per Syside 0.9.0 docs example) ===")
    filtered = [
        req
        for req in req_usages
        if isinstance(req.owning_type, syside.Usage)
        and (not getattr(req, "is_composite", False)
             or not isinstance(req.owning_type, syside.RequirementUsage))
    ]
    print(f"  filter admits: {len(filtered)} of {len(req_usages)} usages")
    print()

    # --- key discovery: compiler.evaluate() actually accepts only
    # Expression | CalculationUsage | ConstraintUsage, NOT RequirementUsage.
    # So we drill into each requirement's owned ConstraintUsage and evaluate that.
    print("=== compiler.evaluate() on ConstraintUsages within each RequirementDefinition ===")
    compiler = syside.Compiler()
    for rd in req_defs:
        constraints = [
            cu for e in rd.owned_elements.collect()
            if (cu := e.try_cast(syside.ConstraintUsage))
        ]
        if not constraints:
            print(f"  [NO-CONSTRAINT] {rd.qualified_name}: no ConstraintUsage owned (only assume/calc?)")
            continue
        for cu in constraints:
            cu_name = cu.name or "(anon)"
            try:
                value, report = compiler.evaluate(
                    cu, stdlib=STDLIB, experimental_quantities=True
                )
                if isinstance(value, bool):
                    marker = "[ OK ]" if value else "[FAIL]"
                else:
                    marker = f"[??] type={safe_type(value)} value={value!r}"
                fatal = "FATAL" if getattr(report, "fatal", False) else "ok"
                print(f"  {marker} {rd.qualified_name} → constraint:{cu_name}  (report.fatal={fatal})")
            except Exception as e:  # noqa: BLE001
                print(f"  [EXC] {rd.qualified_name} → constraint:{cu_name}: {type(e).__name__}: {e}")

    print()
    print("=== compiler.evaluate() on RequirementUsages (no filter) ===")
    for ru in req_usages:
        try:
            value, report = compiler.evaluate(
                ru, stdlib=STDLIB, experimental_quantities=True
            )
            if isinstance(value, bool):
                marker = "[ OK ]" if value else "[FAIL]"
            else:
                marker = f"[??] type={safe_type(value)} value={value!r}"
            fatal = "FATAL" if getattr(report, "fatal", False) else "ok"
            print(f"  {marker} {ru.qualified_name}  (report.fatal={fatal})")
        except Exception as e:  # noqa: BLE001
            print(f"  [EXC] {ru.qualified_name}: {type(e).__name__}: {e}")

    print()
    print("done.")


if __name__ == "__main__":
    main()
