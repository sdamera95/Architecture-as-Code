"""Phase 8 validation: 5 remaining message packages.

Loads all 17 library .sysml files and validates parse + definition counts.
"""
import syside
import sys

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
    "projects/ros2-sysmlv2/ros2_sysmlv2/archetypes.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/nav2.sysml",
    # Phase 8 new files
    "projects/ros2-sysmlv2/ros2_sysmlv2/trajectory_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/diagnostic_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/shape_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/action_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/visualization_msgs.sysml",
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


print("=" * 60)
print("Phase 8 Validation: 5 remaining message packages")
print("=" * 60)

model, diagnostics = syside.load_model(FILES)
has_errors = diagnostics.contains_errors()
check("All 17 files parse without errors", not has_errors)

if has_errors:
    print("\nCritical: parse errors found. Cannot continue.")
    sys.exit(1)

# ── New item defs from Phase 8 ────────────────────────────────────────

print("\n" + "-" * 60)
print("Phase 8 item defs")
print("-" * 60)

item_defs = {n.name for n in model.nodes(syside.ItemDefinition)}

PHASE8_ITEMS = {
    "trajectory_msgs": ["JointTrajectoryPoint", "JointTrajectory",
                        "MultiDOFJointTrajectoryPoint", "MultiDOFJointTrajectory"],
    "diagnostic_msgs": ["KeyValue", "DiagnosticStatus", "DiagnosticArray"],
    "shape_msgs": ["MeshTriangle", "Mesh", "Plane", "SolidPrimitive"],
    "action_msgs": ["GoalInfo", "GoalStatus", "GoalStatusArray"],
    "visualization_msgs": ["UVCoordinate", "MeshFile", "Marker", "MarkerArray"],
}

for pkg, items in PHASE8_ITEMS.items():
    print(f"\n  {pkg}:")
    for item in items:
        check(f"    item def {item}", item in item_defs)

# ── New enum defs ─────────────────────────────────────────────────────

print("\n" + "-" * 60)
print("Phase 8 enum defs")
print("-" * 60)

enum_defs = {n.name for n in model.nodes(syside.EnumerationDefinition)}
check("enum def DiagnosticLevel exists", "DiagnosticLevel" in enum_defs)
check("enum def GoalStatusKind exists", "GoalStatusKind" in enum_defs)

# ── Check field counts on key types ──────────────────────────────────

print("\n" + "-" * 60)
print("Field count spot checks")
print("-" * 60)

all_item_defs = {n.name: n for n in model.nodes(syside.ItemDefinition)}

def count_attrs(item_name):
    if item_name not in all_item_defs:
        return -1
    return len([e for e in all_item_defs[item_name].owned_elements.collect()
                if e.try_cast(syside.AttributeUsage)])

check("JointTrajectoryPoint has 5 attrs", count_attrs("JointTrajectoryPoint") == 5,
      f"got {count_attrs('JointTrajectoryPoint')}")
check("DiagnosticStatus has 5 attrs", count_attrs("DiagnosticStatus") == 5,
      f"got {count_attrs('DiagnosticStatus')}")
check("Marker has 19 attrs", count_attrs("Marker") == 19,
      f"got {count_attrs('Marker')}")
check("GoalStatus has 2 attrs", count_attrs("GoalStatus") == 2,
      f"got {count_attrs('GoalStatus')}")
check("Mesh has 2 attrs", count_attrs("Mesh") == 2,
      f"got {count_attrs('Mesh')}")

# ── Cumulative counts ─────────────────────────────────────────────────

print("\n" + "-" * 60)
print("Cumulative definition counts (all 17 files)")
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
    print("\nSome checks FAILED")
    sys.exit(1)
else:
    print("\nAll Phase 8 checks PASS")
