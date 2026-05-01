#!/usr/bin/env python3
"""
Endurance Trade Study for the UAV system.

Sweeps battery capacity (Wh) across a range and evaluates:
  - Total mass (kg)
  - Total power draw (W)
  - Flight endurance (minutes)
  - Requirement satisfaction (mass budget, endurance, power budget)

The key trade-off: larger batteries increase endurance but also increase
mass, which increases propulsion power (P = k * m), which eats into the
endurance gain. At some point, adding more battery is counterproductive.

Approach:
  - Load the SysML v2 model with Syside Automator
  - For each battery capacity value, regenerate the .sysml file with the
    new value, reload, and evaluate the parametric chain
  - Collect results and print a trade table + identify the optimal point

Run:
    .venv/bin/python studies/endurance_trade_study.py
"""
import syside
import tempfile
import os
from pathlib import Path

MODEL_TEMPLATE = Path(__file__).parent.parent / "syside-demos" / "uav_trade_study.sysml"


def load_and_evaluate(model_path: str) -> dict:
    """Load a SysML v2 model and extract UAV system-level attributes."""
    model, diag = syside.load_model([model_path])
    if diag.contains_errors():
        return None

    results = {}
    for part_def in model.nodes(syside.PartDefinition):
        if part_def.name == "UAV":
            for owned in part_def.owned_elements.collect():
                if attr := owned.try_cast(syside.AttributeUsage):
                    expr = attr.feature_value_expression
                    if expr is not None:
                        try:
                            result, report = syside.Compiler().evaluate(expr)
                            if not report.fatal:
                                results[attr.name] = result
                        except Exception:
                            pass
    return results


def make_variant(template_text: str, capacity_wh: float) -> str:
    """Create a model variant by substituting battery capacity."""
    # Replace the capacityWh default value in the template
    # The line in the model: :>> capacityWh = 100.0;
    return template_text.replace(
        ":>> capacityWh = 100.0;",
        f":>> capacityWh = {capacity_wh};",
    )


def check_requirements(results: dict) -> dict:
    """Check requirement satisfaction against model values."""
    return {
        "MassBudget (≤5 kg)": {
            "value": results.get("totalMassKg"),
            "threshold": 5.0,
            "satisfied": results.get("totalMassKg", 999) <= 5.0,
        },
        "Endurance (≥30 min)": {
            "value": results.get("enduranceMin"),
            "threshold": 30.0,
            "satisfied": results.get("enduranceMin", 0) >= 30.0,
        },
        "PowerBudget (≤600 W)": {
            "value": results.get("totalPowerW"),
            "threshold": 600.0,
            "satisfied": results.get("totalPowerW", 999) <= 600.0,
        },
    }


def main():
    template_text = MODEL_TEMPLATE.read_text()

    # Sweep battery capacity from 20 Wh to 500 Wh
    sweep_values = [20, 40, 60, 80, 100, 150, 200, 300, 400, 500, 750, 1000]

    # Header
    print("=" * 100)
    print("UAV ENDURANCE TRADE STUDY")
    print("Sweep parameter: battery.capacityWh")
    print(f"Model: {MODEL_TEMPLATE.name}")
    print("=" * 100)
    print()
    print(f"{'Capacity':>10} {'Batt Mass':>10} {'Total Mass':>11} "
          f"{'Hover Pwr':>10} {'Total Pwr':>10} {'Endurance':>10} "
          f"{'Mass OK':>8} {'Endur OK':>9} {'Pwr OK':>7} {'ALL':>5}")
    print(f"{'(Wh)':>10} {'(kg)':>10} {'(kg)':>11} "
          f"{'(W)':>10} {'(W)':>10} {'(min)':>10} "
          f"{'≤5kg':>8} {'≥30min':>9} {'≤600W':>7} {'':>5}")
    print("-" * 100)

    best_endurance = 0
    best_capacity = 0
    all_results = []

    for cap in sweep_values:
        # Generate variant model
        variant_text = make_variant(template_text, float(cap))

        # Write to temp file, load, evaluate
        with tempfile.NamedTemporaryFile(
            suffix=".sysml", mode="w", delete=False, dir="/tmp"
        ) as f:
            f.write(variant_text)
            tmp_path = f.name

        try:
            results = load_and_evaluate(tmp_path)
        finally:
            os.unlink(tmp_path)

        if results is None:
            print(f"{cap:>10} {'PARSE ERROR':>60}")
            continue

        reqs = check_requirements(results)
        all_pass = all(r["satisfied"] for r in reqs.values())

        # Derived: battery mass = capacity / specific_energy
        batt_mass = cap / 200.0  # specificEnergy = 200 Wh/kg

        row = {
            "capacity": cap,
            "batt_mass": batt_mass,
            "total_mass": results["totalMassKg"],
            "hover_power": results["hoverPowerW"],
            "total_power": results["totalPowerW"],
            "endurance_min": results["enduranceMin"],
            "reqs": reqs,
            "all_pass": all_pass,
        }
        all_results.append(row)

        # Track best feasible design
        if all_pass and results["enduranceMin"] > best_endurance:
            best_endurance = results["enduranceMin"]
            best_capacity = cap

        mass_ok = "PASS" if reqs["MassBudget (≤5 kg)"]["satisfied"] else "FAIL"
        endur_ok = "PASS" if reqs["Endurance (≥30 min)"]["satisfied"] else "FAIL"
        pwr_ok = "PASS" if reqs["PowerBudget (≤600 W)"]["satisfied"] else "FAIL"
        verdict = "YES" if all_pass else "NO"

        print(
            f"{cap:>10.0f} {batt_mass:>10.2f} {results['totalMassKg']:>11.2f} "
            f"{results['hoverPowerW']:>10.1f} {results['totalPowerW']:>10.1f} "
            f"{results['enduranceMin']:>10.1f} "
            f"{mass_ok:>8} {endur_ok:>9} {pwr_ok:>7} {verdict:>5}"
        )

    # Summary
    print("-" * 100)
    print()
    print("ANALYSIS")
    print("-" * 40)

    # Find the turning point where endurance starts decreasing
    endurance_values = [r["endurance_min"] for r in all_results]
    peak_idx = endurance_values.index(max(endurance_values))
    peak = all_results[peak_idx]

    print(f"  Peak endurance:     {peak['endurance_min']:.1f} min "
          f"at {peak['capacity']} Wh battery")
    print(f"  Peak total mass:    {peak['total_mass']:.2f} kg")
    print(f"  Peak total power:   {peak['total_power']:.1f} W")
    print()

    if best_capacity > 0:
        best = next(r for r in all_results if r["capacity"] == best_capacity)
        print(f"  Best feasible design (all requirements satisfied):")
        print(f"    Battery capacity: {best_capacity} Wh")
        print(f"    Total mass:       {best['total_mass']:.2f} kg")
        print(f"    Endurance:        {best['endurance_min']:.1f} min")
        print(f"    Total power:      {best['total_power']:.1f} W")
    else:
        print("  No feasible design found in sweep range!")

    # Identify the trade-off
    print()
    print("TRADE-OFF INSIGHT")
    print("-" * 40)
    feasible = [r for r in all_results if r["all_pass"]]
    infeasible_mass = [r for r in all_results
                       if not r["reqs"]["MassBudget (≤5 kg)"]["satisfied"]]
    infeasible_endur = [r for r in all_results
                        if not r["reqs"]["Endurance (≥30 min)"]["satisfied"]]

    if infeasible_endur:
        print(f"  Battery < {min(r['capacity'] for r in feasible if r in feasible):.0f} Wh: "
              f"endurance too low (fails ≥30 min)")
    if infeasible_mass:
        print(f"  Battery > {min(r['capacity'] for r in infeasible_mass):.0f} Wh: "
              f"mass too high (fails ≤5 kg)")
    if feasible:
        caps = [r["capacity"] for r in feasible]
        print(f"  Feasible range: {min(caps)}-{max(caps)} Wh")
    print()


if __name__ == "__main__":
    main()
