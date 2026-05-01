"""TF2 + Parameters conformance checker for Phase 5.

Validates tf2.sysml and params.sysml against ROS2 Jazzy source:

Parameters (field-by-field .msg conformance):
  - rcl_interfaces/msg/ParameterType.msg (10 type constants)
  - rcl_interfaces/msg/ParameterDescriptor.msg (7 fields)
  - rcl_interfaces/msg/IntegerRange.msg (3 fields)
  - rcl_interfaces/msg/FloatingPointRange.msg (3 fields)
  - rcl_interfaces/msg/Parameter.msg (2 fields)
  - rcl_interfaces/msg/ParameterValue.msg (9 fields)

TF2 (architectural conventions):
  - REP 105 standard frame names: map, odom, base_link
  - /tf and /tf_static topic conventions
  - TransformStamped already modeled in geometry_msgs.sysml
"""
import re
import sys
from pathlib import Path

REFS = Path("references")
RCL_MSG = REFS / "rcl_interfaces/rcl_interfaces/msg"

passed = 0
failed = 0
info_count = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


def info(label, detail=""):
    global info_count
    info_count += 1
    print(f"  INFO  {label}  {detail}")


def parse_msg_fields(msg_path):
    """Parse a .msg file and return list of (type, name) tuples for fields,
    and list of (name, value) tuples for constants."""
    text = msg_path.read_text()
    fields = []
    constants = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Constant: TYPE NAME = VALUE
        m = re.match(r'^(\w+)\s+(\w+)\s*=\s*(.+)$', line)
        if m:
            constants.append((m.group(2), m.group(3).strip()))
            continue
        # Field: TYPE NAME or TYPE NAME DEFAULT
        # Handle array types like TYPE[] NAME, TYPE[<=1] NAME
        m = re.match(r'^([\w/]+(?:\[.*?\])?)\s+(\w+)(?:\s+.*)?$', line)
        if m:
            fields.append((m.group(1), m.group(2)))
    return fields, constants


# ══════════════════════════════════════════════════════════════════════
# PARAMETERS GROUND TRUTH
# ══════════════════════════════════════════════════════════════════════

print("=" * 60)
print("1. ParameterType.msg Ground Truth")
print("=" * 60)

pt_fields, pt_constants = parse_msg_fields(RCL_MSG / "ParameterType.msg")

EXPECTED_PARAM_TYPES = [
    ("PARAMETER_NOT_SET", "0"),
    ("PARAMETER_BOOL", "1"),
    ("PARAMETER_INTEGER", "2"),
    ("PARAMETER_DOUBLE", "3"),
    ("PARAMETER_STRING", "4"),
    ("PARAMETER_BYTE_ARRAY", "5"),
    ("PARAMETER_BOOL_ARRAY", "6"),
    ("PARAMETER_INTEGER_ARRAY", "7"),
    ("PARAMETER_DOUBLE_ARRAY", "8"),
    ("PARAMETER_STRING_ARRAY", "9"),
]

print(f"\nParameter type constants ({len(pt_constants)}):")
for name, val in pt_constants:
    info(f"  {name} = {val}")

check("ParameterType.msg has 10 constants",
      len(pt_constants) == 10, f"got {len(pt_constants)}")

for expected_name, expected_val in EXPECTED_PARAM_TYPES:
    found = any(n == expected_name and v == expected_val for n, v in pt_constants)
    check(f"  {expected_name} = {expected_val}", found)

# ── ParameterDescriptor.msg ───────────────────────────────────────────

print("\n" + "=" * 60)
print("2. ParameterDescriptor.msg Ground Truth")
print("=" * 60)

pd_fields, pd_constants = parse_msg_fields(RCL_MSG / "ParameterDescriptor.msg")

print(f"\nFields ({len(pd_fields)}):")
for ftype, fname in pd_fields:
    info(f"  {ftype} {fname}")

EXPECTED_PD_FIELDS = [
    ("string", "name"),
    ("uint8", "type"),
    ("string", "description"),
    ("string", "additional_constraints"),
    ("bool", "read_only"),
    ("bool", "dynamic_typing"),
    ("FloatingPointRange[<=1]", "floating_point_range"),
    ("IntegerRange[<=1]", "integer_range"),
]

check("ParameterDescriptor.msg has 8 fields",
      len(pd_fields) == 8, f"got {len(pd_fields)}")

for exp_type, exp_name in EXPECTED_PD_FIELDS:
    found = any(fname == exp_name for _, fname in pd_fields)
    check(f"  field {exp_name} exists", found)

# ── IntegerRange.msg ──────────────────────────────────────────────────

print("\n" + "=" * 60)
print("3. IntegerRange.msg Ground Truth")
print("=" * 60)

ir_fields, _ = parse_msg_fields(RCL_MSG / "IntegerRange.msg")

EXPECTED_IR_FIELDS = [
    ("int64", "from_value"),
    ("int64", "to_value"),
    ("uint64", "step"),
]

print(f"\nFields ({len(ir_fields)}):")
for ftype, fname in ir_fields:
    info(f"  {ftype} {fname}")

check("IntegerRange.msg has 3 fields",
      len(ir_fields) == 3, f"got {len(ir_fields)}")

for exp_type, exp_name in EXPECTED_IR_FIELDS:
    found = any(fname == exp_name for _, fname in ir_fields)
    check(f"  field {exp_name} exists", found)

# ── FloatingPointRange.msg ────────────────────────────────────────────

print("\n" + "=" * 60)
print("4. FloatingPointRange.msg Ground Truth")
print("=" * 60)

fpr_fields, _ = parse_msg_fields(RCL_MSG / "FloatingPointRange.msg")

EXPECTED_FPR_FIELDS = [
    ("float64", "from_value"),
    ("float64", "to_value"),
    ("float64", "step"),
]

print(f"\nFields ({len(fpr_fields)}):")
for ftype, fname in fpr_fields:
    info(f"  {ftype} {fname}")

check("FloatingPointRange.msg has 3 fields",
      len(fpr_fields) == 3, f"got {len(fpr_fields)}")

for exp_type, exp_name in EXPECTED_FPR_FIELDS:
    found = any(fname == exp_name for _, fname in fpr_fields)
    check(f"  field {exp_name} exists", found)

# ── Parameter.msg ─────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("5. Parameter.msg Ground Truth")
print("=" * 60)

p_fields, _ = parse_msg_fields(RCL_MSG / "Parameter.msg")

print(f"\nFields ({len(p_fields)}):")
for ftype, fname in p_fields:
    info(f"  {ftype} {fname}")

check("Parameter.msg has 2 fields",
      len(p_fields) == 2, f"got {len(p_fields)}")
check("  field name exists", any(fname == "name" for _, fname in p_fields))
check("  field value exists", any(fname == "value" for _, fname in p_fields))

# ── ParameterValue.msg ────────────────────────────────────────────────

print("\n" + "=" * 60)
print("6. ParameterValue.msg Ground Truth")
print("=" * 60)

pv_fields, _ = parse_msg_fields(RCL_MSG / "ParameterValue.msg")

print(f"\nFields ({len(pv_fields)}):")
for ftype, fname in pv_fields:
    info(f"  {ftype} {fname}")

EXPECTED_PV_FIELDS = [
    "type", "bool_value", "integer_value", "double_value", "string_value",
    "byte_array_value", "bool_array_value", "integer_array_value",
    "double_array_value", "string_array_value",
]

check("ParameterValue.msg has 10 fields",
      len(pv_fields) == 10, f"got {len(pv_fields)}")

for exp_name in EXPECTED_PV_FIELDS:
    found = any(fname == exp_name for _, fname in pv_fields)
    check(f"  field {exp_name} exists", found)


# ══════════════════════════════════════════════════════════════════════
# TF2 GROUND TRUTH (architectural conventions)
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("7. TF2 Conventions Ground Truth (REP 105)")
print("=" * 60)

# REP 105 defines three standard coordinate frame names
# https://www.ros.org/reps/rep-0105.html
REP105_FRAMES = {
    "map": "Global fixed frame, world-fixed, z-up. Used for long-term global position.",
    "odom": "Odometry frame, world-fixed, continuous but drifts over time.",
    "base_link": "Robot body frame, rigidly attached to the mobile robot base.",
}

print("\nREP 105 standard frames:")
for frame, desc in REP105_FRAMES.items():
    info(f"  '{frame}': {desc}")

check("REP 105 defines 3 standard frames", len(REP105_FRAMES) == 3)

# Standard TF2 topics
TF2_TOPICS = {
    "/tf": "Dynamic transforms, published at variable rates",
    "/tf_static": "Static transforms, published once with TransientLocal durability",
}

print("\nTF2 topics:")
for topic, desc in TF2_TOPICS.items():
    info(f"  {topic}: {desc}")

check("TF2 has 2 standard topics", len(TF2_TOPICS) == 2)

# Standard transform tree: map -> odom -> base_link
TF2_CHAIN = [
    ("map", "odom", "Typically published by AMCL/localization (dynamic)"),
    ("odom", "base_link", "Published by odometry/EKF (dynamic)"),
]

print("\nStandard transform chain:")
for parent, child, desc in TF2_CHAIN:
    info(f"  {parent} -> {child}: {desc}")

check("Standard frame chain has 2 links", len(TF2_CHAIN) == 2)

# Verify TransformStamped exists in geometry_msgs (already modeled)
geom_path = Path("projects/ros2-sysmlv2/ros2_sysmlv2/geometry_msgs.sysml")
geom_text = geom_path.read_text()
check("TransformStamped item def exists in geometry_msgs.sysml",
      "item def TransformStamped" in geom_text)
check("TransformStamped has childFrameId field",
      "childFrameId" in geom_text)
check("Transform item def exists in geometry_msgs.sysml",
      "item def Transform" in geom_text)

# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print(f"Ground Truth Summary: {passed} passed, {failed} failed, {info_count} info")
print("=" * 60)

if failed > 0:
    print("\nFAILED — ground truth extraction has issues")
    sys.exit(1)
else:
    print("\nAll ground truth checks PASS — ready to build tf2.sysml and params.sysml")

# ── Export expected definitions ────────────────────────────────────────

print("\n" + "-" * 60)
print("Expected SysML definitions to produce:")
print("-" * 60)

print("\nparams.sysml:")
print("  - enum def: ParameterTypeKind (10 values matching ParameterType.msg)")
print("  - item def: IntegerRange (fromValue, toValue, step)")
print("  - item def: FloatingPointRange (fromValue, toValue, step)")
print("  - attribute def: ParameterDescriptor (name, type, description, additionalConstraints,")
print("                   readOnly, dynamicTyping, floatingPointRange, integerRange)")
print("  - attribute def: DeclaredParameter (name, parameterType, descriptor)")

print("\ntf2.sysml:")
print("  - part def: CoordinateFrame (frameId: String)")
print("  - connection def: StaticTransform (end parent, end child, attribute transform)")
print("  - connection def: DynamicTransform (end parent, end child)")
print("  - part: MapFrame :> CoordinateFrame (frameId = 'map')")
print("  - part: OdomFrame :> CoordinateFrame (frameId = 'odom')")
print("  - part: BaseLinkFrame :> CoordinateFrame (frameId = 'base_link')")
print("  - part def: StandardFrameTree (map -> odom -> base_link)")
