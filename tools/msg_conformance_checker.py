#!/usr/bin/env python3
"""
ROS2 .msg to SysML v2 Conformance Checker.

Parses ROS2 .msg files and compares them against the corresponding
SysML v2 item definitions loaded via Syside Automator. Reports:
  - Missing fields (in .msg but not in SysML)
  - Extra fields (in SysML but not in .msg)
  - Type mismatches (field exists but type differs)
  - Constants in .msg (reported but not required in SysML — modeled as enums)

Usage:
    .venv/bin/python tools/msg_conformance_checker.py \\
        --msg-dir references/common_interfaces/geometry_msgs/msg \\
        --sysml-files projects/ros2-sysmlv2/ros2_sysmlv2/geometry_msgs.sysml \\
                      projects/ros2-sysmlv2/ros2_sysmlv2/foundation.sysml \\
        --mapping geometry_msgs_mapping.json  # optional explicit mapping file

    Or use the built-in mapping:
    .venv/bin/python tools/msg_conformance_checker.py \\
        --msg-dir references/common_interfaces/geometry_msgs/msg \\
        --sysml-files projects/ros2-sysmlv2/ros2_sysmlv2/*.sysml

Run:
    .venv/bin/python tools/msg_conformance_checker.py --help
"""
import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════
# 1. ROS2 .MSG PARSER
# ══════════════════════════════════════════════════════════════

# ROS2 primitive type → SysML v2 type mapping
ROS2_TYPE_MAP = {
    # Boolean
    "bool": "Boolean",
    # Integers
    "int8": "Integer", "int16": "Integer", "int32": "Integer", "int64": "Integer",
    "uint8": "Integer", "uint16": "Integer", "uint32": "Integer", "uint64": "Integer",
    "byte": "Integer",
    # Floating point
    "float32": "Real", "float64": "Real",
    # String
    "string": "String",
    # Time primitives (from builtin_interfaces)
    "builtin_interfaces/Time": "Time",
    "builtin_interfaces/Duration": "Duration",
    # Standard header
    "std_msgs/Header": "Header",
}

# Known ROS2 package prefixes → SysML package/item name mapping
# For qualified types like geometry_msgs/Vector3 → Vector3
MSG_TYPE_SIMPLIFY = {
    "geometry_msgs/": "",
    "sensor_msgs/": "",
    "nav_msgs/": "",
    "std_msgs/": "",
    "trajectory_msgs/": "",
    "diagnostic_msgs/": "",
    "visualization_msgs/": "",
    "shape_msgs/": "",
    "action_msgs/": "",
    "builtin_interfaces/": "",
}


@dataclass
class MsgField:
    """A field parsed from a .msg file."""
    name: str
    ros2_type: str
    is_array: bool = False
    array_size: Optional[int] = None  # None = variable, int = fixed
    sysml_type: Optional[str] = None  # resolved SysML type


@dataclass
class MsgConstant:
    """A constant defined in a .msg file."""
    name: str
    ros2_type: str
    value: str


@dataclass
class ParsedMsg:
    """A fully parsed .msg file."""
    name: str  # e.g., "Twist"
    package: str  # e.g., "geometry_msgs"
    fields: list[MsgField] = field(default_factory=list)
    constants: list[MsgConstant] = field(default_factory=list)


def parse_msg_file(path: Path, package: str) -> ParsedMsg:
    """Parse a ROS2 .msg file into structured fields and constants."""
    msg_name = path.stem  # e.g., "Twist" from "Twist.msg"
    result = ParsedMsg(name=msg_name, package=package)

    for line in path.read_text().splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Strip inline comments
        if "#" in line:
            line = line[:line.index("#")].strip()

        if not line:
            continue

        # Check for constants: type NAME = value
        const_match = re.match(
            r'^(\w+(?:/\w+)?)\s+([A-Z][A-Z0-9_]*)\s*=\s*(.+)$', line
        )
        if const_match:
            result.constants.append(MsgConstant(
                name=const_match.group(2),
                ros2_type=const_match.group(1),
                value=const_match.group(3).strip(),
            ))
            continue

        # Parse field: type[array] name [default]
        # Examples: "float64 x", "float64 x 0", "float32[] ranges", "float64[36] covariance"
        field_match = re.match(
            r'^(\w+(?:/\w+)?)\s*(\[(\d*)\])?\s+(\w+)(?:\s+.*)?$', line
        )
        if field_match:
            ros2_type = field_match.group(1)
            array_bracket = field_match.group(2)
            array_size_str = field_match.group(3)
            field_name = field_match.group(4)

            is_array = array_bracket is not None
            array_size = int(array_size_str) if array_size_str else None

            # Resolve SysML type
            sysml_type = resolve_sysml_type(ros2_type)

            result.fields.append(MsgField(
                name=field_name,
                ros2_type=ros2_type,
                is_array=is_array,
                array_size=array_size,
                sysml_type=sysml_type,
            ))
            continue

        # If we get here, the line didn't match any pattern
        # (shouldn't happen for well-formed .msg files)

    return result


def resolve_sysml_type(ros2_type: str) -> str:
    """Map a ROS2 type to its expected SysML v2 type name."""
    # Direct primitive mapping
    if ros2_type in ROS2_TYPE_MAP:
        return ROS2_TYPE_MAP[ros2_type]

    # Qualified type (e.g., geometry_msgs/Vector3 → Vector3)
    for prefix, replacement in MSG_TYPE_SIMPLIFY.items():
        if ros2_type.startswith(prefix):
            return replacement + ros2_type[len(prefix):]

    # Unqualified type within same package (e.g., Vector3 in geometry_msgs)
    return ros2_type


# ══════════════════════════════════════════════════════════════
# 2. SYSML ITEM DEF EXTRACTOR (via Syside Automator)
# ══════════════════════════════════════════════════════════════

@dataclass
class SysmlItemDef:
    """An item definition extracted from a SysML v2 model."""
    name: str
    qualified_name: str
    attributes: dict[str, str] = field(default_factory=dict)  # name → type name


def extract_sysml_items(sysml_files: list[str]) -> dict[str, SysmlItemDef]:
    """Load SysML v2 files and extract all item definitions with their attributes."""
    import syside

    model, diag = syside.load_model(sysml_files)
    if diag.contains_errors():
        print("ERROR: SysML model has parse errors:")
        for d in diag.diagnostics:
            print(f"  {d}")
        sys.exit(1)

    items = {}
    for item_def in model.nodes(syside.ItemDefinition):
        sysml_item = SysmlItemDef(
            name=item_def.name,
            qualified_name=item_def.qualified_name,
        )

        for owned in item_def.owned_elements.collect():
            if attr := owned.try_cast(syside.AttributeUsage):
                # Get the attribute's type name
                types_list = list(attr.types.collect())
                type_name = types_list[0].name if types_list else "Unknown"
                sysml_item.attributes[attr.name] = type_name

        items[item_def.name] = sysml_item

    # Also check attribute definitions (Time, Duration are attr defs, not item defs)
    for attr_def in model.nodes(syside.AttributeDefinition):
        sysml_item = SysmlItemDef(
            name=attr_def.name,
            qualified_name=attr_def.qualified_name,
        )

        for owned in attr_def.owned_elements.collect():
            if attr := owned.try_cast(syside.AttributeUsage):
                types_list = list(attr.types.collect())
                type_name = types_list[0].name if types_list else "Unknown"
                sysml_item.attributes[attr.name] = type_name

        items[attr_def.name] = sysml_item

    return items


# ══════════════════════════════════════════════════════════════
# 3. CONFORMANCE CHECKER
# ══════════════════════════════════════════════════════════════

@dataclass
class FieldCheck:
    """Result of checking one .msg field against SysML."""
    field_name: str
    ros2_type: str
    expected_sysml_type: str
    status: str  # "PASS", "MISSING", "TYPE_MISMATCH"
    actual_sysml_type: Optional[str] = None
    note: str = ""


@dataclass
class MsgCheck:
    """Result of checking one .msg file against SysML."""
    msg_name: str
    package: str
    sysml_item_found: bool
    field_checks: list[FieldCheck] = field(default_factory=list)
    extra_sysml_attrs: list[str] = field(default_factory=list)
    constants: list[MsgConstant] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.sysml_item_found and all(
            fc.status == "PASS" for fc in self.field_checks
        )

    @property
    def n_pass(self) -> int:
        return sum(1 for fc in self.field_checks if fc.status == "PASS")

    @property
    def n_fail(self) -> int:
        return sum(1 for fc in self.field_checks if fc.status != "PASS")


def check_msg_against_sysml(
    parsed_msg: ParsedMsg,
    sysml_items: dict[str, SysmlItemDef],
    name_mapping: Optional[dict[str, str]] = None,
) -> MsgCheck:
    """Check a parsed .msg against the SysML item definitions."""

    # Resolve the SysML item name (may differ from .msg name)
    sysml_name = parsed_msg.name
    if name_mapping and parsed_msg.name in name_mapping:
        sysml_name = name_mapping[parsed_msg.name]

    result = MsgCheck(
        msg_name=parsed_msg.name,
        package=parsed_msg.package,
        sysml_item_found=sysml_name in sysml_items,
        constants=parsed_msg.constants,
    )

    if not result.sysml_item_found:
        # Mark all fields as missing
        for f in parsed_msg.fields:
            result.field_checks.append(FieldCheck(
                field_name=f.name,
                ros2_type=f.ros2_type,
                expected_sysml_type=f.sysml_type or "?",
                status="MISSING",
                note=f"No item def '{sysml_name}' found in SysML model",
            ))
        return result

    sysml_item = sysml_items[sysml_name]
    sysml_attrs = dict(sysml_item.attributes)  # copy for tracking extras

    for msg_field in parsed_msg.fields:
        if msg_field.name in sysml_attrs:
            actual_type = sysml_attrs.pop(msg_field.name)
            expected_type = msg_field.sysml_type

            # Type check (flexible: allow SysML name variations)
            if types_match(expected_type, actual_type):
                result.field_checks.append(FieldCheck(
                    field_name=msg_field.name,
                    ros2_type=msg_field.ros2_type,
                    expected_sysml_type=expected_type,
                    actual_sysml_type=actual_type,
                    status="PASS",
                ))
            else:
                result.field_checks.append(FieldCheck(
                    field_name=msg_field.name,
                    ros2_type=msg_field.ros2_type,
                    expected_sysml_type=expected_type,
                    actual_sysml_type=actual_type,
                    status="TYPE_MISMATCH",
                    note=f"Expected '{expected_type}', got '{actual_type}'",
                ))
        else:
            # Field name might differ (camelCase in SysML vs snake_case in .msg)
            camel_name = to_camel_case(msg_field.name)
            if camel_name in sysml_attrs:
                actual_type = sysml_attrs.pop(camel_name)
                expected_type = msg_field.sysml_type

                if types_match(expected_type, actual_type):
                    result.field_checks.append(FieldCheck(
                        field_name=msg_field.name,
                        ros2_type=msg_field.ros2_type,
                        expected_sysml_type=expected_type,
                        actual_sysml_type=actual_type,
                        status="PASS",
                        note=f"Matched via camelCase: {camel_name}",
                    ))
                else:
                    result.field_checks.append(FieldCheck(
                        field_name=msg_field.name,
                        ros2_type=msg_field.ros2_type,
                        expected_sysml_type=expected_type,
                        actual_sysml_type=actual_type,
                        status="TYPE_MISMATCH",
                        note=f"Matched via camelCase: {camel_name}, but type differs",
                    ))
            else:
                result.field_checks.append(FieldCheck(
                    field_name=msg_field.name,
                    ros2_type=msg_field.ros2_type,
                    expected_sysml_type=msg_field.sysml_type or "?",
                    status="MISSING",
                    note="Field not found in SysML item def (tried snake_case and camelCase)",
                ))

    # Any remaining SysML attributes are "extra" (not in .msg)
    result.extra_sysml_attrs = list(sysml_attrs.keys())

    return result


def types_match(expected: str, actual: str) -> bool:
    """Flexible type matching between ROS2-resolved type and SysML type."""
    if expected == actual:
        return True

    # Common equivalences
    equivalences = {
        ("Real", "Real"), ("Integer", "Integer"), ("Boolean", "Boolean"),
        ("String", "String"), ("Natural", "Integer"),
    }

    # CovarianceMatrix6x6 for float64[36] covariance fields
    if expected == "Real" and actual in ("CovarianceMatrix6x6", "Real"):
        return True

    # Accept any match where the base names are the same
    if expected and actual and expected.split("::")[-1] == actual.split("::")[-1]:
        return True

    return (expected, actual) in equivalences or (actual, expected) in equivalences


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase. e.g., 'frame_id' → 'frameId'."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# ══════════════════════════════════════════════════════════════
# 4. REPORTING
# ══════════════════════════════════════════════════════════════

def print_report(checks: list[MsgCheck], verbose: bool = False):
    """Print a conformance report."""
    total_msgs = len(checks)
    msgs_found = sum(1 for c in checks if c.sysml_item_found)
    msgs_passed = sum(1 for c in checks if c.passed)
    total_fields = sum(len(c.field_checks) for c in checks)
    fields_passed = sum(c.n_pass for c in checks)

    print("=" * 70)
    print("ROS2 .msg → SysML v2 Conformance Report")
    print("=" * 70)
    print()

    for check in checks:
        status = "PASS" if check.passed else "FAIL" if check.sysml_item_found else "MISSING"
        icon = "✓" if check.passed else "✗" if check.sysml_item_found else "?"
        print(f"  [{icon}] {check.package}/{check.msg_name}: "
              f"{check.n_pass}/{len(check.field_checks)} fields | {status}")

        if verbose or not check.passed:
            for fc in check.field_checks:
                if fc.status == "PASS" and not verbose:
                    continue
                status_str = {"PASS": "  OK ", "MISSING": " MISS", "TYPE_MISMATCH": " TYPE"}[fc.status]
                print(f"        [{status_str}] {fc.field_name}: "
                      f"{fc.ros2_type} → {fc.expected_sysml_type}"
                      f"{f' (got {fc.actual_sysml_type})' if fc.actual_sysml_type and fc.status != 'PASS' else ''}"
                      f"{f' — {fc.note}' if fc.note and fc.status != 'PASS' else ''}")

            if check.extra_sysml_attrs:
                print(f"        [EXTRA] SysML attrs not in .msg: {check.extra_sysml_attrs}")

            if check.constants and verbose:
                print(f"        [CONST] {len(check.constants)} constants in .msg "
                      f"(modeled as enum defs, not checked here)")

    print()
    print("-" * 70)
    print(f"  Messages: {msgs_found}/{total_msgs} found in SysML, "
          f"{msgs_passed}/{total_msgs} fully conformant")
    print(f"  Fields:   {fields_passed}/{total_fields} matched")
    print("-" * 70)

    return msgs_passed == total_msgs


# ══════════════════════════════════════════════════════════════
# 5. MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Check ROS2 .msg files against SysML v2 item definitions"
    )
    parser.add_argument(
        "--msg-dir", required=True,
        help="Directory containing .msg files (e.g., references/common_interfaces/geometry_msgs/msg)"
    )
    parser.add_argument(
        "--sysml-files", nargs="+", required=True,
        help="SysML v2 files to load (e.g., projects/ros2-sysmlv2/ros2_sysmlv2/*.sysml)"
    )
    parser.add_argument(
        "--package", default=None,
        help="ROS2 package name (default: inferred from msg-dir parent)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show all field checks, not just failures"
    )
    parser.add_argument(
        "--filter", default=None,
        help="Only check .msg files matching this pattern (e.g., 'Twist,Pose,Vector3')"
    )

    args = parser.parse_args()

    msg_dir = Path(args.msg_dir)
    if not msg_dir.exists():
        print(f"ERROR: Message directory not found: {msg_dir}")
        sys.exit(1)

    # Infer package name from directory structure
    package = args.package or msg_dir.parent.name

    # Parse all .msg files
    msg_files = sorted(msg_dir.glob("*.msg"))
    if args.filter:
        filter_names = set(args.filter.split(","))
        msg_files = [f for f in msg_files if f.stem in filter_names]

    if not msg_files:
        print(f"No .msg files found in {msg_dir}")
        sys.exit(1)

    parsed_msgs = [parse_msg_file(f, package) for f in msg_files]
    print(f"Parsed {len(parsed_msgs)} .msg files from {package}")

    # Load SysML model
    sysml_files = [str(f) for f in args.sysml_files]
    print(f"Loading {len(sysml_files)} SysML files...")
    sysml_items = extract_sysml_items(sysml_files)
    print(f"Found {len(sysml_items)} item/attribute definitions in SysML model")
    print()

    # Run conformance checks
    checks = [check_msg_against_sysml(msg, sysml_items) for msg in parsed_msgs]

    # Print report
    all_passed = print_report(checks, verbose=args.verbose)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
