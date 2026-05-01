#!/usr/bin/env python3
"""
Automated SysML v2 -> Equinox Module Generation Demo.

Reads uav_trade_study.sysml via Syside Automator and AUTOMATICALLY
constructs a hierarchy of Equinox modules that mirrors the SysML v2
part hierarchy. No hand-crafted module definitions.

The pipeline:
  1. Load the SysML v2 model with Syside Automator
  2. Walk part definitions to discover attributes and nested parts
  3. Dynamically create eqx.Module subclasses for each part def
  4. Instantiate the top-level module with concrete values from part usages
  5. Demonstrate jax.grad through the auto-generated module tree

Run:
    .venv/bin/python tests/demo_auto_equinox.py
"""
import syside
import jax
import jax.numpy as jnp
import equinox as eqx
from pathlib import Path
from dataclasses import field as dataclass_field
from typing import Any

MODEL_PATH = Path(__file__).parent.parent / "syside-demos" / "uav_trade_study.sysml"


# ══════════════════════════════════════════════════════════════
# 1. SYSML MODEL INTROSPECTION
# ══════════════════════════════════════════════════════════════

def load_model(path: str):
    """Load the SysML v2 model and return the model object."""
    model, diag = syside.load_model([str(path)])
    if diag.contains_errors():
        raise RuntimeError(f"SysML model has parse errors")
    return model


def get_part_def_by_name(model, name: str):
    """Find a PartDefinition by name."""
    for pd in model.nodes(syside.PartDefinition):
        if pd.name == name:
            return pd
    return None


def analyze_part_def(part_def) -> dict:
    """Extract the structure of a PartDefinition: its attributes and nested part usages.

    Returns a dict:
      {
        "name": "Battery",
        "attributes": [{"name": "capacityWh", "is_derived": False}, ...],
        "parts": [{"name": "motor", "type_name": "Motor"}, ...],
      }
    """
    info = {
        "name": part_def.name,
        "qualified_name": part_def.qualified_name,
        "attributes": [],
        "parts": [],
    }

    for owned in part_def.owned_elements.collect():
        if attr := owned.try_cast(syside.AttributeUsage):
            expr = attr.feature_value_expression
            is_derived = expr is not None
            default_val = None
            if is_derived:
                try:
                    result, report = syside.Compiler().evaluate(expr)
                    if not report.fatal:
                        default_val = result
                except Exception:
                    pass

            info["attributes"].append({
                "name": attr.name,
                "is_derived": is_derived,
                "default_value": default_val,
            })

        elif pu := owned.try_cast(syside.PartUsage):
            types_list = list(pu.types.collect())
            type_name = types_list[0].name if types_list else None
            info["parts"].append({
                "name": pu.name,
                "type_name": type_name,
            })

    return info


def extract_instance_values(part_usage) -> dict:
    """Extract concrete attribute values from a part usage (the :>> overrides).

    Returns a dict of {attr_name: value} for all evaluable attributes,
    and nested part usage values as {part_name: dict}.
    """
    values = {}
    nested_parts = {}

    for owned in part_usage.owned_elements.collect():
        # Overridden attributes appear as ReferenceUsage
        if ref := owned.try_cast(syside.ReferenceUsage):
            expr = ref.feature_value_expression
            if expr is not None:
                try:
                    result, report = syside.Compiler().evaluate(expr)
                    if not report.fatal:
                        values[ref.name] = result
                except Exception:
                    pass

        # Nested part usages (e.g., propulsion.motor)
        elif pu := owned.try_cast(syside.PartUsage):
            nested_parts[pu.name] = extract_instance_values(pu)

    return {"attributes": values, "nested_parts": nested_parts}


# ══════════════════════════════════════════════════════════════
# 2. EQUINOX MODULE GENERATION
# ══════════════════════════════════════════════════════════════

# Registry of generated module classes, keyed by part def name
_module_registry: dict[str, type] = {}


def generate_module_class(model, part_def_name: str) -> type:
    """Dynamically create an eqx.Module subclass for a SysML PartDefinition.

    The generated class has:
      - A float field for each non-derived attribute
      - An int (static) field for integer-typed attributes
      - A module-typed field for each nested part usage
      - Derived attributes are NOT fields — they'll be evaluated at the
        system level using the SysML expression evaluator
    """
    if part_def_name in _module_registry:
        return _module_registry[part_def_name]

    part_def = get_part_def_by_name(model, part_def_name)
    if part_def is None:
        raise ValueError(f"No PartDefinition named '{part_def_name}' in model")

    info = analyze_part_def(part_def)

    # Build the class annotations and defaults
    annotations = {}
    namespace = {}

    # Collect names of nested parts so we can detect cross-part references
    part_names = {p["name"] for p in info["parts"]}

    # Process attributes
    for attr in info["attributes"]:
        name = _to_python_name(attr["name"])
        if attr["is_derived"] and attr["default_value"] is not None:
            # Check if this is a truly derived attribute (references other parts)
            # vs a simple constant (propulsiveConstant = 50.0)
            # Heuristic: if the attribute name matches a pattern that suggests
            # it's a rollup (contains names of child parts), skip it.
            # Otherwise, include it as a field with its evaluated default.
            # For robustness, include all attributes that evaluate to a concrete
            # value as fields — the endurance function will use them.
            pass  # fall through to the field creation below
        elif attr["is_derived"]:
            # Has expression but couldn't evaluate — skip
            continue

        if attr["default_value"] is not None:
            # Has a concrete default
            val = attr["default_value"]
            if isinstance(val, int) and not isinstance(val, bool):
                annotations[name] = int
                namespace[name] = eqx.field(default=val, static=True)
            else:
                annotations[name] = float
                namespace[name] = float(val)
        else:
            # Declared without default — use 0.0 as placeholder
            annotations[name] = float
            namespace[name] = 0.0

    # Process nested part usages
    for part in info["parts"]:
        sub_name = _to_python_name(part["name"])
        if part["type_name"]:
            # Recursively generate the sub-module class
            sub_cls = generate_module_class(model, part["type_name"])
            annotations[sub_name] = sub_cls
            namespace[sub_name] = sub_cls()

    # Create the class dynamically
    namespace["__annotations__"] = annotations
    namespace["__module__"] = __name__

    cls = type(part_def_name, (eqx.Module,), namespace)
    _module_registry[part_def_name] = cls

    return cls


def instantiate_module(cls: type, instance_values: dict) -> eqx.Module:
    """Create an instance of a generated module with concrete values from the SysML model.

    instance_values comes from extract_instance_values() and has:
      {"attributes": {"capacityWh": 100.0, ...}, "nested_parts": {"motor": {...}}}
    """
    kwargs = {}

    # Set attribute values
    for attr_name, value in instance_values.get("attributes", {}).items():
        py_name = _to_python_name(attr_name)
        if hasattr(cls, '__annotations__') and py_name in cls.__annotations__:
            if cls.__annotations__[py_name] == int:
                kwargs[py_name] = int(value)
            else:
                kwargs[py_name] = float(value)

    # Set nested part instances
    for part_name, part_values in instance_values.get("nested_parts", {}).items():
        py_name = _to_python_name(part_name)
        if hasattr(cls, '__annotations__') and py_name in cls.__annotations__:
            sub_cls = cls.__annotations__[py_name]
            kwargs[py_name] = instantiate_module(sub_cls, part_values)

    return cls(**kwargs)


def _to_python_name(sysml_name: str) -> str:
    """Convert SysML camelCase names to the same camelCase (preserve as-is).
    We keep camelCase to maintain traceability to the SysML model."""
    return sysml_name


# ══════════════════════════════════════════════════════════════
# 3. SYSTEM-LEVEL EVALUATION
# ══════════════════════════════════════════════════════════════

def build_system_evaluator(model, system_part_def_name: str):
    """Build a function that takes a top-level eqx.Module and evaluates
    all derived attributes using the SysML expression chain.

    Returns a dict of {attr_name: callable(module) -> float}.
    """
    part_def = get_part_def_by_name(model, system_part_def_name)
    info = analyze_part_def(part_def)

    # Collect derived attribute names and their evaluated values
    # We'll build a function that recomputes them from the module's live values
    derived_attrs = [a for a in info["attributes"] if a["is_derived"]]

    return derived_attrs


def make_endurance_fn(module_cls):
    """Build a JAX-differentiable endurance function that operates on
    the auto-generated module.

    This function mirrors the SysML expression chain:
      totalMassKg = airframe.massKg + battery.massKg + propulsion.massKg + ...
      hoverPowerW = propulsiveConstant * totalMassKg
      totalPowerW = hoverPowerW + avionicsPowerW + payloadPowerW
      enduranceMin = (battery.capacityWh / totalPowerW) * 60
    """
    def endurance(uav):
        # Mass rollup (mirrors UAV.totalMassKg expression)
        batt_mass = uav.battery.capacityWh / uav.battery.specificEnergy
        prop_mass = uav.propulsion.numMotors * uav.propulsion.motor.massKg
        avionics_mass = (uav.avionics.fcc.massKg + uav.avionics.imu.massKg +
                         uav.avionics.gps.massKg + uav.avionics.baro.massKg)
        total_mass = (uav.airframe.massKg + batt_mass + prop_mass +
                      avionics_mass + uav.payload.massKg)

        # Power rollup (mirrors UAV.totalPowerW expression)
        hover_power = uav.propulsiveConstant * total_mass
        avionics_power = (uav.avionics.fcc.powerW + uav.avionics.imu.powerW +
                          uav.avionics.gps.powerW + uav.avionics.baro.powerW)
        total_power = hover_power + avionics_power + uav.payload.powerW

        # Endurance (mirrors UAV.enduranceMin expression)
        return (uav.battery.capacityWh / total_power) * 60.0

    return endurance


# ══════════════════════════════════════════════════════════════
# 4. MAIN DEMO
# ══════════════════════════════════════════════════════════════

def section(title: str):
    print(f"\n{'═' * 65}")
    print(f"  {title}")
    print(f"{'═' * 65}")


def print_module_tree(module, prefix="", depth=0):
    """Print the structure of an auto-generated Equinox module."""
    if isinstance(module, eqx.Module):
        for name in sorted(vars(module)):
            value = getattr(module, name)
            if isinstance(value, eqx.Module):
                print(f"{'  ' * depth}{prefix}{name}: {type(value).__name__}")
                print_module_tree(value, prefix="", depth=depth + 1)
            else:
                print(f"{'  ' * depth}{prefix}{name} = {value}")


def main():
    # ── Step 1: Load the SysML model ────────────────────────

    section("1. Load SysML v2 Model")
    model = load_model(MODEL_PATH)
    print(f"  Loaded: {MODEL_PATH.name}")

    # ── Step 2: Analyze part definitions ────────────────────

    section("2. Analyze Part Definitions")
    for pd in model.nodes(syside.PartDefinition):
        info = analyze_part_def(pd)
        n_attrs = len(info["attributes"])
        n_derived = sum(1 for a in info["attributes"] if a["is_derived"])
        n_parts = len(info["parts"])
        print(f"  {pd.name:25s}  attrs: {n_attrs} ({n_derived} derived)  parts: {n_parts}")

    # ── Step 3: Generate Equinox module classes ─────────────

    section("3. Generate Equinox Module Classes from SysML")

    # Generate all part def classes (UAV triggers recursive generation)
    UAVModule = generate_module_class(model, "UAV")

    print(f"  Generated {len(_module_registry)} module classes:")
    for name, cls in _module_registry.items():
        annotations = getattr(cls, '__annotations__', {})
        fields = list(annotations.keys())
        print(f"    {name}: {fields}")

    # ── Step 4: Instantiate with concrete values ────────────

    section("4. Instantiate UAV with Concrete Values from SysML")

    # Find the UAV part def and extract instance values from its part usages
    uav_def = get_part_def_by_name(model, "UAV")
    uav_instance_values = {"attributes": {}, "nested_parts": {}}

    for owned in uav_def.owned_elements.collect():
        # Direct attributes on UAV (only non-derived ones)
        if attr := owned.try_cast(syside.AttributeUsage):
            expr = attr.feature_value_expression
            if expr is not None:
                try:
                    result, report = syside.Compiler().evaluate(expr)
                    if not report.fatal and not any(
                        a["name"] == attr.name and a["is_derived"]
                        for a in analyze_part_def(uav_def)["attributes"]
                    ):
                        uav_instance_values["attributes"][attr.name] = result
                except Exception:
                    pass

        # Part usages with their overridden values
        elif pu := owned.try_cast(syside.PartUsage):
            uav_instance_values["nested_parts"][pu.name] = extract_instance_values(pu)

    # Also extract non-derived UAV-level attributes that have defaults
    # propulsiveConstant is the only non-derived one with a value in the def
    uav_info = analyze_part_def(uav_def)
    for attr in uav_info["attributes"]:
        if not attr["is_derived"] and attr["default_value"] is not None:
            uav_instance_values["attributes"][attr["name"]] = attr["default_value"]

    uav = instantiate_module(UAVModule, uav_instance_values)

    print("  Auto-generated module tree:")
    print_module_tree(uav, prefix="  ", depth=1)

    # ── Step 5: Forward evaluation ──────────────────────────

    section("5. Forward Evaluation")

    endurance_fn = make_endurance_fn(UAVModule)
    endurance = endurance_fn(uav)

    print(f"  Endurance (auto-generated model): {endurance:.1f} min")
    print(f"  Endurance (SysML Automator):      57.7 min")
    assert abs(endurance - 57.75) < 0.1, f"Mismatch: {endurance} vs 57.75"
    print(f"  [PASS] Values match!")

    # ── Step 6: Automatic differentiation ───────────────────

    section("6. Autodiff Through Auto-Generated Modules")

    grad_fn = jax.grad(endurance_fn)
    grads = grad_fn(uav)

    print("  Gradient tree (auto-generated, same structure as SysML model):\n")
    print_module_tree(grads, prefix="  d(endurance)/d(", depth=1)

    # ── Step 7: Key sensitivities ───────────────────────────

    section("7. Key Sensitivities")

    print(f"  d(endurance)/d(battery.capacityWh)      = {grads.battery.capacityWh:+.4f} min/Wh")
    print(f"  d(endurance)/d(battery.specificEnergy)   = {grads.battery.specificEnergy:+.4f} min/(Wh/kg)")
    print(f"  d(endurance)/d(payload.massKg)           = {grads.payload.massKg:+.4f} min/kg")
    print(f"  d(endurance)/d(payload.powerW)           = {grads.payload.powerW:+.4f} min/W")
    print(f"  d(endurance)/d(propulsiveConstant)       = {grads.propulsiveConstant:+.4f} min/(W/kg)")
    print(f"  d(endurance)/d(propulsion.motor.massKg)  = {grads.propulsion.motor.massKg:+.4f} min/kg")

    # ── Step 8: Requirement checking ────────────────────────

    section("8. Requirement Satisfaction (from SysML requirements)")

    # Extract requirements from the model
    print("  Requirements from SysML model:\n")
    for req in model.nodes(syside.RequirementDefinition):
        # Get the doc text
        doc_text = ""
        for owned in req.owned_elements.collect():
            if doc := owned.try_cast(syside.Documentation):
                doc_text = str(doc.body) if hasattr(doc, 'body') else "(doc)"

        print(f"    {req.name}: {doc_text or '(no doc)'}")

    # Evaluate constraints
    batt_mass = uav.battery.capacityWh / uav.battery.specificEnergy
    prop_mass = uav.propulsion.numMotors * uav.propulsion.motor.massKg
    avionics_mass = (uav.avionics.fcc.massKg + uav.avionics.imu.massKg +
                     uav.avionics.gps.massKg + uav.avionics.baro.massKg)
    total_mass = (uav.airframe.massKg + batt_mass + prop_mass +
                  avionics_mass + uav.payload.massKg)

    print(f"\n    MassBudget (totalMass <= 5.0):     {total_mass:.2f} kg  "
          f"{'[PASS]' if total_mass <= 5.0 else '[FAIL]'}")
    print(f"    EnduranceReq (endurance >= 30 min): {endurance:.1f} min "
          f"{'[PASS]' if endurance >= 30.0 else '[FAIL]'}")

    hover_power = uav.propulsiveConstant * total_mass
    avionics_power = (uav.avionics.fcc.powerW + uav.avionics.imu.powerW +
                      uav.avionics.gps.powerW + uav.avionics.baro.powerW)
    total_power = hover_power + avionics_power + uav.payload.powerW
    print(f"    PowerBudget (totalPower <= 600 W):  {total_power:.1f} W  "
          f"{'[PASS]' if total_power <= 600.0 else '[FAIL]'}")

    # ── Summary ─────────────────────────────────────────────

    section("SUMMARY")
    print(f"""
  Pipeline: .sysml -> Syside Automator -> Dynamic eqx.Module classes -> jax.grad

  What was automated:
    - {len(_module_registry)} Equinox module classes generated from SysML PartDefinitions
    - Module hierarchy mirrors SysML part composition tree
    - Concrete parameter values extracted from SysML part usage overrides
    - Forward evaluation matches SysML Automator results
    - jax.grad produces architecture-shaped gradient tree

  What still requires manual specification:
    - The endurance_fn (derived expression chain) — this is the next
      automation target: auto-generating JAX functions from SysML
      attribute expressions that reference cross-part attributes

  The module STRUCTURE is fully automated. The EVALUATION LOGIC
  for derived attributes with cross-part references is the remaining
  step to full automation.
""")


if __name__ == "__main__":
    main()
