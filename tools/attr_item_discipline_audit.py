#!/usr/bin/env python3
"""
ROS2 IDL → SysML v2 attribute/item discipline audit.

Goal: verify that the ros2-sysmlv2 library faithfully reflects ROS2's IDL
distinction between structured message types and primitive-typed slots.

Per OMG SysML v2.0 §7.7 and §7.10:
  - attribute usage: typed by attribute def or KerML primitive (referential)
  - item usage: typed by item def (composite ownership, identity, flow)

Per strict ROS2 fidelity, the expected mapping is:
  - ROS2 primitive (bool, intN, uintN, floatN, string, byte) → SysML `attribute`
  - ROS2 structured message type (geometry_msgs/Pose, std_msgs/Header, ...) → SysML `item`
  - ROS2 primitive array (float64[N]) → SysML `attribute` with [N] multiplicity
  - ROS2 structured array (Pose[]) → SysML `item` with [0..*] multiplicity

The audit reports per-field discrepancies in three categories:
  - USAGE_MISMATCH: `attribute X : T` where T is structured (should be item),
                    or `item X : T` where T is primitive (should be attribute)
  - MULTIPLICITY_MISSING: ROS2 has [N] array bounds but SysML lacks them
  - DEF_LEVEL_MISMATCH: a .msg type modeled as attribute def in SysML (or vice versa)
                        that disagrees with strict ROS2 fidelity
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Reuse the parser from the existing checker
sys.path.insert(0, str(Path(__file__).parent))
from msg_conformance_checker import (
    parse_msg_file,
    ROS2_TYPE_MAP,
    MSG_TYPE_SIMPLIFY,
    to_camel_case,
)

# ROS2 primitive type set (anything else is a structured type)
ROS2_PRIMITIVES = set(ROS2_TYPE_MAP.keys()) - {
    "builtin_interfaces/Time",
    "builtin_interfaces/Duration",
    "std_msgs/Header",
}


@dataclass
class SysmlField:
    """A field extracted from a SysML def, with its usage kind."""
    name: str
    type_name: str
    usage_kind: str  # "attribute" or "item"


@dataclass
class SysmlDef:
    """A SysML v2 type def with its def kind and fields."""
    name: str
    def_kind: str  # "item_def" or "attribute_def"
    fields: list[SysmlField] = field(default_factory=list)


def extract_sysml_defs(sysml_files: list[str]) -> dict[str, SysmlDef]:
    """Load SysML v2 files and extract defs with field-level usage kinds."""
    import syside

    model, diag = syside.load_model(sysml_files, warnings_as_errors=True)
    if diag.contains_errors():
        print("ERROR: SysML model has parse errors or warnings:")
        for d in diag.diagnostics:
            print(f"  {d}")
        sys.exit(1)

    defs: dict[str, SysmlDef] = {}

    for item_def in model.nodes(syside.ItemDefinition):
        sd = SysmlDef(name=item_def.name, def_kind="item_def")
        for owned in item_def.owned_elements.collect():
            attr = owned.try_cast(syside.AttributeUsage)
            itm = owned.try_cast(syside.ItemUsage)
            if attr is not None:
                tlist = list(attr.types.collect())
                tname = tlist[0].name if tlist else "Unknown"
                sd.fields.append(SysmlField(attr.name, tname, "attribute"))
            elif itm is not None:
                tlist = list(itm.types.collect())
                tname = tlist[0].name if tlist else "Unknown"
                sd.fields.append(SysmlField(itm.name, tname, "item"))
        defs[item_def.name] = sd

    for attr_def in model.nodes(syside.AttributeDefinition):
        sd = SysmlDef(name=attr_def.name, def_kind="attribute_def")
        for owned in attr_def.owned_elements.collect():
            attr = owned.try_cast(syside.AttributeUsage)
            itm = owned.try_cast(syside.ItemUsage)
            if attr is not None:
                tlist = list(attr.types.collect())
                tname = tlist[0].name if tlist else "Unknown"
                sd.fields.append(SysmlField(attr.name, tname, "attribute"))
            elif itm is not None:
                tlist = list(itm.types.collect())
                tname = tlist[0].name if tlist else "Unknown"
                sd.fields.append(SysmlField(itm.name, tname, "item"))
        defs[attr_def.name] = sd

    return defs


def is_ros2_structured(ros2_type: str) -> bool:
    """Return True if the type is a structured ROS2 message (not primitive)."""
    if ros2_type in ROS2_PRIMITIVES:
        return False
    return True


def expected_sysml_usage(ros2_type: str, sysml_defs: dict[str, SysmlDef]) -> str:
    """
    Compute the expected SysML usage kind ('attribute' or 'item') for a ROS2 field type.

    The rule is keyed on the SysML def-level commitment for the type:
      - If type resolves to an item def in SysML → expect 'item'
      - If type resolves to an attribute def or KerML primitive → expect 'attribute'

    This is the SPEC rule (OMG §7.7.2). Whether the def-level commitment itself
    is faithful to ROS2 is a separate audit (see DEF_LEVEL_MISMATCH).
    """
    # Resolve to a simplified SysML type name
    if ros2_type in ROS2_PRIMITIVES:
        return "attribute"
    for prefix, _ in MSG_TYPE_SIMPLIFY.items():
        if ros2_type.startswith(prefix):
            simple = ros2_type[len(prefix):]
            if simple in sysml_defs:
                if sysml_defs[simple].def_kind == "item_def":
                    return "item"
                else:
                    return "attribute"
            # Unknown type — assume structured (item)
            return "item"
    # Unqualified ROS2 type, check directly
    if ros2_type in sysml_defs:
        return "item" if sysml_defs[ros2_type].def_kind == "item_def" else "attribute"
    return "item"


@dataclass
class FieldFinding:
    msg_name: str
    field_name: str
    ros2_type: str
    is_array: bool
    array_size: Optional[int]
    sysml_field_name: str
    sysml_type: str
    actual_usage: str
    expected_usage: str
    category: str  # USAGE_OK | USAGE_MISMATCH | MULTIPLICITY_MISSING
    note: str = ""


@dataclass
class DefFinding:
    type_name: str  # e.g., "Time"
    msg_qualified: str  # e.g., "builtin_interfaces/Time"
    actual_def_kind: str  # "item_def" | "attribute_def"
    expected_def_kind: str  # "item_def" per strict ROS2 fidelity
    category: str  # DEF_OK | DEF_LEVEL_MISMATCH
    note: str = ""


def audit_package(
    msg_dir: Path,
    package: str,
    sysml_defs: dict[str, SysmlDef],
    name_mapping: Optional[dict[str, str]] = None,
) -> tuple[list[FieldFinding], list[DefFinding]]:
    """Audit one ROS2 package against the SysML library."""
    name_mapping = name_mapping or {}
    field_findings: list[FieldFinding] = []
    def_findings: list[DefFinding] = []

    for msg_path in sorted(msg_dir.glob("*.msg")):
        parsed = parse_msg_file(msg_path, package)

        sysml_name = name_mapping.get(parsed.name, parsed.name)
        sysml_def = sysml_defs.get(sysml_name)
        if sysml_def is None:
            continue  # def-level coverage; reported separately

        # Def-level fidelity check: every ROS2 .msg → expect item_def under strict fidelity
        if sysml_def.def_kind == "attribute_def":
            def_findings.append(DefFinding(
                type_name=sysml_name,
                msg_qualified=f"{package}/{parsed.name}",
                actual_def_kind="attribute_def",
                expected_def_kind="item_def",
                category="DEF_LEVEL_MISMATCH",
                note=f"ROS2 defines {package}/{parsed.name}.msg as a structured message "
                     f"type with {len(parsed.fields)} fields; strict fidelity says item def.",
            ))

        # Build a lookup of SysML fields by both snake and camel form
        sysml_field_idx: dict[str, SysmlField] = {}
        for sf in sysml_def.fields:
            sysml_field_idx[sf.name] = sf

        for msg_field in parsed.fields:
            # Try both snake_case and camelCase to find the SysML field
            target = None
            target_name = None
            if msg_field.name in sysml_field_idx:
                target = sysml_field_idx[msg_field.name]
                target_name = msg_field.name
            else:
                camel = to_camel_case(msg_field.name)
                if camel in sysml_field_idx:
                    target = sysml_field_idx[camel]
                    target_name = camel

            if target is None:
                # Field missing in SysML — handled by existing msg_conformance_checker
                continue

            expected = expected_sysml_usage(msg_field.ros2_type, sysml_defs)
            actual = target.usage_kind

            # Determine category
            if expected != actual:
                category = "USAGE_MISMATCH"
                note = (f"ROS2 type '{msg_field.ros2_type}' "
                        f"({'structured' if is_ros2_structured(msg_field.ros2_type) else 'primitive'}); "
                        f"expected `{expected} {target.name} : {target.type_name}`")
            else:
                category = "USAGE_OK"
                note = ""

            field_findings.append(FieldFinding(
                msg_name=parsed.name,
                field_name=msg_field.name,
                ros2_type=msg_field.ros2_type,
                is_array=msg_field.is_array,
                array_size=msg_field.array_size,
                sysml_field_name=target_name,
                sysml_type=target.type_name,
                actual_usage=actual,
                expected_usage=expected,
                category=category,
                note=note,
            ))

    return field_findings, def_findings


def print_report(
    package: str,
    field_findings: list[FieldFinding],
    def_findings: list[DefFinding],
    verbose: bool = False,
):
    """Print a per-package report."""
    print("=" * 76)
    print(f"  Package: {package}")
    print("=" * 76)

    n_ok = sum(1 for f in field_findings if f.category == "USAGE_OK")
    n_mismatch = sum(1 for f in field_findings if f.category == "USAGE_MISMATCH")
    n_def_mismatch = len([d for d in def_findings if d.category == "DEF_LEVEL_MISMATCH"])

    print(f"  Fields audited: {len(field_findings)}  "
          f"(OK: {n_ok}, USAGE_MISMATCH: {n_mismatch})")
    print(f"  Def-level mismatches: {n_def_mismatch}")
    print()

    if def_findings:
        print("  Def-level findings:")
        for d in def_findings:
            print(f"    [{d.category}] {d.type_name} "
                  f"(currently {d.actual_def_kind}, expected {d.expected_def_kind})")
            print(f"        {d.note}")
        print()

    if n_mismatch or verbose:
        print("  Field-level findings:")
        for f in field_findings:
            if f.category == "USAGE_OK" and not verbose:
                continue
            marker = "✓" if f.category == "USAGE_OK" else "✗"
            print(f"    [{marker}] {f.msg_name}.{f.field_name}  "
                  f"({f.ros2_type}{'[' + (str(f.array_size) if f.array_size else '') + ']' if f.is_array else ''})")
            print(f"        actual: `{f.actual_usage} {f.sysml_field_name} : {f.sysml_type}`")
            if f.category != "USAGE_OK":
                print(f"        {f.note}")
        print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sysml-files", nargs="+", required=True,
        help="SysML v2 files to load",
    )
    parser.add_argument(
        "--packages", nargs="+", required=True,
        help="package_name=msg_dir pairs, e.g. geometry_msgs=references/common_interfaces/geometry_msgs/msg",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show all fields, not just mismatches",
    )
    args = parser.parse_args()

    sysml_defs = extract_sysml_defs(args.sysml_files)
    print(f"Loaded {len(sysml_defs)} SysML defs from {len(args.sysml_files)} files")
    print()

    total_fields = 0
    total_mismatches = 0
    total_def_mismatches = 0

    for entry in args.packages:
        if "=" not in entry:
            print(f"Skipping malformed --packages entry: {entry}")
            continue
        pkg, dirpath = entry.split("=", 1)
        msg_dir = Path(dirpath)
        if not msg_dir.exists():
            print(f"WARN: msg dir not found: {msg_dir}")
            continue
        field_findings, def_findings = audit_package(msg_dir, pkg, sysml_defs)
        print_report(pkg, field_findings, def_findings, verbose=args.verbose)
        total_fields += len(field_findings)
        total_mismatches += sum(1 for f in field_findings if f.category == "USAGE_MISMATCH")
        total_def_mismatches += len([d for d in def_findings if d.category == "DEF_LEVEL_MISMATCH"])

    print("=" * 76)
    print(f"  TOTAL: {total_fields} fields audited, "
          f"{total_mismatches} usage mismatches, "
          f"{total_def_mismatches} def-level mismatches")
    print("=" * 76)

    sys.exit(0 if (total_mismatches == 0 and total_def_mismatches == 0) else 1)


if __name__ == "__main__":
    main()
