"""Phase 5 validation: tf2.sysml + params.sysml

Loads all 10 library .sysml files together and validates:
  1. Parse success (no errors)
  2. Parameter definitions present and correct
  3. TF2 definitions present and correct
  4. Cross-layer imports resolve (tf2 -> geometry_msgs, params -> foundation)
  5. Specialization: MapFrame/OdomFrame/BaseLinkFrame :> CoordinateFrame
  6. StandardFrameTree composition
"""
import syside
import sys

# All library files (layers 1-5)
FILES = [
    "projects/ros2-sysmlv2/ros2_sysmlv2/foundation.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/std_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/geometry_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/sensor_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/nav_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/comm.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/lifecycle.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/deployment.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/params.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/tf2.sysml",
]

passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


# ── Load model ────────────────────────────────────────────────────────

print("=" * 60)
print("Phase 5 Validation: params.sysml + tf2.sysml")
print("=" * 60)

model, diagnostics = syside.load_model(FILES)
has_errors = diagnostics.contains_errors()
check("All 10 files parse without errors", not has_errors)

if has_errors:
    print("\nCritical: parse errors found. Cannot continue.")
    sys.exit(1)

# ── Parameter enum: ParameterTypeKind ─────────────────────────────────

print("\n" + "-" * 60)
print("ParameterTypeKind enum")
print("-" * 60)

enum_defs = {n.name: n for n in model.nodes(syside.EnumerationDefinition)}
check("enum def ParameterTypeKind exists", "ParameterTypeKind" in enum_defs)

if "ParameterTypeKind" in enum_defs:
    ptk = enum_defs["ParameterTypeKind"]
    values = []
    for elem in ptk.owned_elements.collect():
        if eu := elem.try_cast(syside.EnumerationUsage):
            values.append(eu.name)

    EXPECTED_VALUES = [
        "NotSet", "Bool", "Integer", "Double", "StringType",
        "ByteArray", "BoolArray", "IntegerArray", "DoubleArray", "StringArray",
    ]
    print(f"  Values found: {values}")
    for v in EXPECTED_VALUES:
        check(f"  enum {v} exists", v in values)
    check(f"  10 values total", len(values) == 10, f"got {len(values)}")

# ── Parameter attribute defs ──────────────────────────────────────────

print("\n" + "-" * 60)
print("Parameter attribute definitions")
print("-" * 60)

attr_defs = {n.name: n for n in model.nodes(syside.AttributeDefinition)}

EXPECTED_ATTR_DEFS = ["IntegerRange", "FloatingPointRange",
                      "ParameterDescriptor", "DeclaredParameter"]
for ad in EXPECTED_ATTR_DEFS:
    check(f"attribute def {ad} exists", ad in attr_defs)

# Check IntegerRange fields
if "IntegerRange" in attr_defs:
    ir_attrs = [elem.name for elem in attr_defs["IntegerRange"].owned_elements.collect()
                if elem.try_cast(syside.AttributeUsage)]
    check("  IntegerRange has fromValue", "fromValue" in ir_attrs)
    check("  IntegerRange has toValue", "toValue" in ir_attrs)
    check("  IntegerRange has step", "step" in ir_attrs)

# Check FloatingPointRange fields
if "FloatingPointRange" in attr_defs:
    fpr_attrs = [elem.name for elem in attr_defs["FloatingPointRange"].owned_elements.collect()
                 if elem.try_cast(syside.AttributeUsage)]
    check("  FloatingPointRange has fromValue", "fromValue" in fpr_attrs)
    check("  FloatingPointRange has toValue", "toValue" in fpr_attrs)
    check("  FloatingPointRange has step", "step" in fpr_attrs)

# Check ParameterDescriptor fields
if "ParameterDescriptor" in attr_defs:
    pd_attrs = [elem.name for elem in attr_defs["ParameterDescriptor"].owned_elements.collect()
                if elem.try_cast(syside.AttributeUsage)]
    print(f"  ParameterDescriptor fields: {pd_attrs}")
    EXPECTED_PD = ["name", "parameterType", "description", "additionalConstraints",
                   "readOnly", "dynamicTyping", "floatingPointRange", "integerRange"]
    for f in EXPECTED_PD:
        check(f"  ParameterDescriptor has {f}", f in pd_attrs)
    check(f"  ParameterDescriptor has 8 fields", len(pd_attrs) == 8, f"got {len(pd_attrs)}")

# Check DeclaredParameter fields
if "DeclaredParameter" in attr_defs:
    dp_attrs = [elem.name for elem in attr_defs["DeclaredParameter"].owned_elements.collect()
                if elem.try_cast(syside.AttributeUsage)]
    check("  DeclaredParameter has name", "name" in dp_attrs)
    check("  DeclaredParameter has parameterType", "parameterType" in dp_attrs)
    check("  DeclaredParameter has descriptor", "descriptor" in dp_attrs)

# ── TF2: CoordinateFrame ──────────────────────────────────────────────

print("\n" + "-" * 60)
print("TF2 definitions")
print("-" * 60)

part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}

check("part def CoordinateFrame exists", "CoordinateFrame" in part_defs)

if "CoordinateFrame" in part_defs:
    cf_attrs = [elem.name for elem in part_defs["CoordinateFrame"].owned_elements.collect()
                if elem.try_cast(syside.AttributeUsage)]
    check("  CoordinateFrame has frameId", "frameId" in cf_attrs)

# ── TF2: REP 105 frame specializations ────────────────────────────────

print("\n" + "-" * 60)
print("REP 105 frame specializations")
print("-" * 60)

REP105_FRAMES = ["MapFrame", "OdomFrame", "BaseLinkFrame"]
for frame_name in REP105_FRAMES:
    check(f"part def {frame_name} exists", frame_name in part_defs)
    if frame_name in part_defs and "CoordinateFrame" in part_defs:
        specializes = part_defs[frame_name].specializes(part_defs["CoordinateFrame"])
        check(f"  {frame_name} specializes CoordinateFrame", specializes)

# ── TF2: Connection definitions ───────────────────────────────────────

print("\n" + "-" * 60)
print("Transform connection definitions")
print("-" * 60)

conn_defs = {n.name: n for n in model.nodes(syside.ConnectionDefinition)}

check("connection def StaticTransform exists", "StaticTransform" in conn_defs)
check("connection def DynamicTransform exists", "DynamicTransform" in conn_defs)

# Check StaticTransform has transform attribute
if "StaticTransform" in conn_defs:
    st_elems = []
    for elem in conn_defs["StaticTransform"].owned_elements.collect():
        if au := elem.try_cast(syside.AttributeUsage):
            st_elems.append(au.name)
    check("  StaticTransform has transform attribute", "transform" in st_elems)

# ── TF2: StandardFrameTree ────────────────────────────────────────────

print("\n" + "-" * 60)
print("StandardFrameTree composition")
print("-" * 60)

check("part def StandardFrameTree exists", "StandardFrameTree" in part_defs)

if "StandardFrameTree" in part_defs:
    sft = part_defs["StandardFrameTree"]
    parts = []
    connections = []
    for elem in sft.owned_elements.collect():
        if pu := elem.try_cast(syside.PartUsage):
            parts.append(pu.name)
        elif cu := elem.try_cast(syside.ConnectionUsage):
            connections.append(cu.name)

    print(f"  Parts: {parts}")
    print(f"  Connections: {connections}")

    check("  has mapFrame part", "mapFrame" in parts)
    check("  has odomFrame part", "odomFrame" in parts)
    check("  has baseLinkFrame part", "baseLinkFrame" in parts)
    check("  has mapToOdom connection", "mapToOdom" in connections)
    check("  has odomToBaseLink connection", "odomToBaseLink" in connections)

# ── Cumulative definition counts ──────────────────────────────────────

print("\n" + "-" * 60)
print("Cumulative definition counts (all 10 files)")
print("-" * 60)

counts = {
    "ItemDefinition": len(list(model.nodes(syside.ItemDefinition))),
    "AttributeDefinition": len(list(model.nodes(syside.AttributeDefinition))),
    "EnumerationDefinition": len(list(model.nodes(syside.EnumerationDefinition))),
    "PartDefinition": len(list(model.nodes(syside.PartDefinition))),
    "PortDefinition": len(list(model.nodes(syside.PortDefinition))),
    "ConnectionDefinition": len(list(model.nodes(syside.ConnectionDefinition))),
    "ConstraintDefinition": len(list(model.nodes(syside.ConstraintDefinition))),
    "StateDefinition": len(list(model.nodes(syside.StateDefinition))),
    "ActionDefinition": len(list(model.nodes(syside.ActionDefinition))),
}

for typename, count in counts.items():
    print(f"  {typename}: {count}")

total = sum(counts.values())
print(f"\n  TOTAL: {total}")

# ── Summary ───────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print(f"Validation Summary: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print("\nSome checks FAILED — review output above")
    sys.exit(1)
else:
    print("\nAll Phase 5 checks PASS")
