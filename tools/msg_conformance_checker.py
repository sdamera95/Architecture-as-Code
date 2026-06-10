#!/usr/bin/env python3
"""
ROS2 .msg to SysML v2 Conformance Checker.

Parses ROS2 .msg files and compares them against the corresponding
SysML v2 item definitions loaded via Syside Automator. Reports:
  - Missing fields (in .msg but not in SysML)
  - Extra fields (in SysML but not in .msg)
  - Type mismatches (field exists but type differs)
  - Cardinality mismatches (array size/bound differs from the SysML multiplicity)
  - Constants in .msg (reported but not required in SysML — modeled as enums)

Messages with no corresponding SysML item def are reported as SKIP, not FAIL:
the library is a deliberate subset of each package (see README "Library
architecture"), so unmodeled messages are out of scope by design.

Deliberate deviations from the IDL (encoded in FIELD_RENAMES / enum allowance):

  .msg field                          SysML field        Why
  ----------------------------------  -----------------  --------------------------
  DiagnosticStatus.message            diagnosticMessage  `message` is a SysML v2
                                                         reserved keyword
  Marker.id / .type / .action         markerId /         `action` is reserved;
                                      markerType /       id/type renamed for
                                      markerAction       consistency with it
  SolidPrimitive.type                 primitiveType      consistency with the above
  DiagnosticStatus.level (byte +      level :            integer constants are
  KEY=value constants)                DiagnosticLevel    modeled as an enum def

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
    array_size: Optional[int] = None   # None = variable, int = fixed ([N])
    array_bound: Optional[int] = None  # upper bound for bounded arrays ([<=N])
    sysml_type: Optional[str] = None   # resolved SysML type


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
        # Examples: "float64 x", "float64 x 0", "float32[] ranges",
        #           "float64[36] covariance", "float64[<=3] dimensions" (bounded)
        field_match = re.match(
            r'^(\w+(?:/\w+)?)\s*(\[(<=)?(\d*)\])?\s+(\w+)(?:\s+.*)?$', line
        )
        if field_match:
            ros2_type = field_match.group(1)
            array_bracket = field_match.group(2)
            bound_marker = field_match.group(3)
            array_size_str = field_match.group(4)
            field_name = field_match.group(5)

            is_array = array_bracket is not None
            array_size = int(array_size_str) if array_size_str and not bound_marker else None
            array_bound = int(array_size_str) if array_size_str and bound_marker else None

            # Resolve SysML type
            sysml_type = resolve_sysml_type(ros2_type)

            result.fields.append(MsgField(
                name=field_name,
                ros2_type=ros2_type,
                is_array=is_array,
                array_size=array_size,
                array_bound=array_bound,
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
    multiplicities: dict[str, str] = field(default_factory=dict)  # name → multiplicity descriptor ("scalar"/"[N]"/"[0..*]"/"[lo..hi]")
    enum_fields: set = field(default_factory=set)  # field names typed by an EnumerationDefinition


def extract_sysml_items(sysml_files: list[str]) -> dict[str, SysmlItemDef]:
    """Load SysML v2 files and extract all item definitions with their attributes."""
    import syside

    # Surface warnings as errors per project discipline. See § 7.7 OMG spec
    # and docs/v9-upgrade-path-log.md Stage A audit for rationale.
    model, diag = syside.load_model(sysml_files, warnings_as_errors=True)
    if diag.contains_errors():
        print("ERROR: SysML model has parse errors or warnings:")
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
            # After Syside 0.9.0 `attribute-usage-features`, fields with composite
            # (item-def) RHS are declared as `item`, not `attribute`. Look at both.
            field = owned.try_cast(syside.AttributeUsage) or owned.try_cast(syside.ItemUsage)
            if field is not None:
                types_list = list(field.types.collect())
                type_name = types_list[0].name if types_list else "Unknown"
                sysml_item.attributes[field.name] = type_name
                sysml_item.multiplicities[field.name] = sysml_multiplicity_descriptor(field)
                if types_list and types_list[0].try_cast(syside.EnumerationDefinition):
                    sysml_item.enum_fields.add(field.name)

        items[item_def.name] = sysml_item

    # Also check attribute definitions (e.g., QoSProfile, CovarianceMatrix6x6, RMWConfig).
    # As of the 2026-05-16 strict-fidelity fix, Time and Duration are item defs
    # (mirroring builtin_interfaces/Time.msg and Duration.msg structured types);
    # they appear in the loop above. See docs/7_GoverningRules.md for the rationale.
    for attr_def in model.nodes(syside.AttributeDefinition):
        sysml_item = SysmlItemDef(
            name=attr_def.name,
            qualified_name=attr_def.qualified_name,
        )

        for owned in attr_def.owned_elements.collect():
            field = owned.try_cast(syside.AttributeUsage) or owned.try_cast(syside.ItemUsage)
            if field is not None:
                types_list = list(field.types.collect())
                type_name = types_list[0].name if types_list else "Unknown"
                sysml_item.attributes[field.name] = type_name
                sysml_item.multiplicities[field.name] = sysml_multiplicity_descriptor(field)
                if types_list and types_list[0].try_cast(syside.EnumerationDefinition):
                    sysml_item.enum_fields.add(field.name)

        items[attr_def.name] = sysml_item

    return items


# ══════════════════════════════════════════════════════════════
# 3. CONFORMANCE CHECKER
# ══════════════════════════════════════════════════════════════

# Deliberate .msg → SysML field renames (SysML v2 reserved keywords and naming
# policy — see the module docstring table). Keyed (package, message, msg_field).
FIELD_RENAMES = {
    ("diagnostic_msgs", "DiagnosticStatus", "message"): "diagnosticMessage",
    ("shape_msgs", "SolidPrimitive", "type"): "primitiveType",
    ("visualization_msgs", "Marker", "id"): "markerId",
    ("visualization_msgs", "Marker", "type"): "markerType",
    ("visualization_msgs", "Marker", "action"): "markerAction",
}


@dataclass
class FieldCheck:
    """Result of checking one .msg field against SysML."""
    field_name: str
    ros2_type: str
    expected_sysml_type: str
    status: str  # "PASS", "MISSING", "TYPE_MISMATCH", "CARDINALITY_MISMATCH"
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
    def skipped(self) -> bool:
        """Unmodeled by design — the library is a deliberate subset per package."""
        return not self.sysml_item_found

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
        # Unmodeled message: SKIP (out of scope by design), no field checks generated.
        return result

    sysml_item = sysml_items[sysml_name]
    sysml_attrs = dict(sysml_item.attributes)  # copy for tracking extras
    sysml_mults = dict(sysml_item.multiplicities)

    for msg_field in parsed_msg.fields:
        # Match the .msg field to a SysML attribute by snake_case, then camelCase,
        # then the deliberate-rename table (reserved keywords etc.).
        rename_key = (parsed_msg.package, parsed_msg.name, msg_field.name)
        matched_name = None
        if msg_field.name in sysml_attrs:
            matched_name = msg_field.name
        elif to_camel_case(msg_field.name) in sysml_attrs:
            matched_name = to_camel_case(msg_field.name)
        elif FIELD_RENAMES.get(rename_key) in sysml_attrs:
            matched_name = FIELD_RENAMES[rename_key]

        if matched_name is None:
            result.field_checks.append(FieldCheck(
                field_name=msg_field.name,
                ros2_type=msg_field.ros2_type,
                expected_sysml_type=msg_field.sysml_type or "?",
                status="MISSING",
                note="Field not found in SysML item def (tried snake_case, camelCase, rename table)",
            ))
            continue

        actual_type = sysml_attrs.pop(matched_name)
        actual_mult = sysml_mults.get(matched_name, "scalar")
        expected_type = msg_field.sysml_type
        via_camel = matched_name == to_camel_case(msg_field.name) and matched_name != msg_field.name
        via_rename = matched_name == FIELD_RENAMES.get(rename_key)
        camel_note = (f"matched via camelCase: {matched_name}" if via_camel
                      else f"deliberate rename: {matched_name}" if via_rename else "")

        # 1. Type check (flexible: allow SysML name variations). Integer-like .msg
        #    fields whose SysML type is an enumeration def PASS: the .msg constants
        #    are modeled as the enum's literals (e.g. byte level : DiagnosticLevel).
        if not types_match(expected_type, actual_type):
            if expected_type == "Integer" and matched_name in sysml_item.enum_fields:
                result.field_checks.append(FieldCheck(
                    field_name=msg_field.name,
                    ros2_type=msg_field.ros2_type,
                    expected_sysml_type=expected_type,
                    actual_sysml_type=actual_type,
                    status="PASS",
                    note=f"constants modeled as enum def {actual_type}",
                ))
                continue
            result.field_checks.append(FieldCheck(
                field_name=msg_field.name,
                ros2_type=msg_field.ros2_type,
                expected_sysml_type=expected_type,
                actual_sysml_type=actual_type,
                status="TYPE_MISMATCH",
                note=(f"{camel_note}, but type differs" if camel_note
                      else f"Expected '{expected_type}', got '{actual_type}'"),
            ))
            continue

        # 2. Cardinality check (array multiplicity must match the .msg array size)
        card_ok, card_note = check_cardinality(msg_field, expected_type, actual_type, actual_mult)
        result.field_checks.append(FieldCheck(
            field_name=msg_field.name,
            ros2_type=msg_field.ros2_type,
            expected_sysml_type=expected_type,
            actual_sysml_type=actual_type,
            status="PASS" if card_ok else "CARDINALITY_MISMATCH",
            note=("; ".join(n for n in (camel_note, card_note) if n)
                  if not card_ok else camel_note),
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


# Primitive SysML/KerML value types. A ROS2 primitive array (float64[N]) must map to
# one of these WITH the [N] multiplicity. When a ROS2 primitive array maps instead to a
# named wrapper type (e.g. float64[36] → CovarianceMatrix6x6), the array cardinality is
# carried inside the wrapper (CovarianceMatrix6x6.values: Real[36]), so the field-level
# cardinality check is delegated/skipped. See docs/knowledge_docs/covariance_modeling_decision.md.
PRIMITIVE_SYSML_TYPES = {"Real", "Integer", "Boolean", "String", "Natural", "Rational", "Complex"}


def sysml_multiplicity_descriptor(field) -> str:
    """Normalize a SysML feature's multiplicity to a comparable string via the Syside API.

    "scalar" (no multiplicity, or [1]/[1..1]), "[N]" (fixed size N), "[0..*]" (variable),
    or "[lo..hi]" (bounded). MultiplicityRange.upper_bound is a LiteralInfinity for
    unbounded arrays and a LiteralInteger for fixed/bounded ones.
    """
    m = getattr(field, "multiplicity", None)
    if m is None:
        return "scalar"
    upper = getattr(m, "upper_bound", None)
    lower = getattr(m, "lower_bound", None)
    if upper is None or type(upper).__name__ == "LiteralInfinity":
        return "[0..*]"
    up_v = getattr(upper, "value", None)
    lo_v = getattr(lower, "value", None) if lower is not None else None
    if up_v is None:
        return "scalar"  # unreadable bound — treat as unconstrained rather than false-flag
    if lo_v is None or lo_v == up_v:
        return "scalar" if up_v == 1 else f"[{up_v}]"  # [N] shorthand is exactly N; [1] == scalar
    return f"[{lo_v}..{up_v}]"


def ros2_cardinality_descriptor(mf: MsgField) -> str:
    """The SysML multiplicity a ROS2 field requires:
    'scalar', '[N]' (fixed), '[0..N]' (bounded, IDL [<=N]), or '[0..*]' (variable)."""
    if not mf.is_array:
        return "scalar"
    if mf.array_size is not None:
        return f"[{mf.array_size}]"
    if mf.array_bound is not None:
        return f"[0..{mf.array_bound}]"
    return "[0..*]"


def check_cardinality(mf: MsgField, expected_type: str, actual_type: str, sysml_mult: str):
    """Return (ok, note). Compares ROS2 array cardinality to the SysML field multiplicity.

    Always ok (delegated) when a ROS2 primitive array maps to a non-primitive SysML wrapper
    type — the cardinality then lives inside that type. A ROS2 variable array ([]) also
    accepts a SysML bounded range ([lo..hi]) as a stricter-but-valid model.
    """
    if expected_type in PRIMITIVE_SYSML_TYPES and actual_type not in PRIMITIVE_SYSML_TYPES:
        return True, f"array cardinality delegated to wrapper type '{actual_type}'"
    want = ros2_cardinality_descriptor(mf)
    if want == sysml_mult:
        return True, ""
    if want == "[0..*]" and sysml_mult.startswith("[") and ".." in sysml_mult:
        return True, ""
    if not mf.is_array:
        ros2_decl = mf.ros2_type
    elif mf.array_size is not None:
        ros2_decl = f"{mf.ros2_type}[{mf.array_size}]"
    elif mf.array_bound is not None:
        ros2_decl = f"{mf.ros2_type}[<={mf.array_bound}]"
    else:
        ros2_decl = f"{mf.ros2_type}[]"
    return False, f"ROS2 '{ros2_decl}' requires SysML multiplicity {want}, got {sysml_mult}"


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase. e.g., 'frame_id' → 'frameId'."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# ══════════════════════════════════════════════════════════════
# 4. REPORTING
# ══════════════════════════════════════════════════════════════

def print_report(checks: list[MsgCheck], verbose: bool = False):
    """Print a conformance report. Skipped (unmodeled) messages don't count as failures."""
    modeled = [c for c in checks if not c.skipped]
    n_skipped = len(checks) - len(modeled)
    msgs_passed = sum(1 for c in modeled if c.passed)
    total_fields = sum(len(c.field_checks) for c in modeled)
    fields_passed = sum(c.n_pass for c in modeled)

    print("=" * 70)
    print("ROS2 .msg → SysML v2 Conformance Report")
    print("=" * 70)
    print()

    for check in checks:
        if check.skipped:
            if verbose:
                print(f"  [–] {check.package}/{check.msg_name}: SKIP (not modeled — library is a deliberate subset)")
            continue
        status = "PASS" if check.passed else "FAIL"
        icon = "✓" if check.passed else "✗"
        print(f"  [{icon}] {check.package}/{check.msg_name}: "
              f"{check.n_pass}/{len(check.field_checks)} fields | {status}")

        if verbose or not check.passed:
            for fc in check.field_checks:
                if fc.status == "PASS" and not verbose:
                    continue
                status_str = {"PASS": "  OK ", "MISSING": " MISS", "TYPE_MISMATCH": " TYPE",
                              "CARDINALITY_MISMATCH": " CARD"}.get(fc.status, " ??? ")
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
    print(f"  Messages: {msgs_passed}/{len(modeled)} modeled messages fully conformant"
          f"{f', {n_skipped} skipped (not modeled)' if n_skipped else ''}")
    print(f"  Fields:   {fields_passed}/{total_fields} matched")
    print("-" * 70)

    return msgs_passed == len(modeled)


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
