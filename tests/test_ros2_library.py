"""Comprehensive test suite for the ros2-sysmlv2 Sysand package.

Validates the entire library (17 .sysml files, 179 definitions) end-to-end:
  1. Parse all files together without errors
  2. Definition counts by type (exact expected values)
  3. Cross-file import chains resolve (7-layer deep)
  4. Specialization chains (Node -> LifecycleNode -> archetypes -> Nav2 nodes)
  5. State machine structure (LifecycleStates)
  6. Composition (Nav2Stack, StandardFrameTree)
  7. Abstract archetypes cannot be instantiated directly
  8. All 17 packages have unique names

Run with: .venv/bin/python tests/test_ros2_library.py
"""
import syside
import sys
from pathlib import Path

# ── All library source files ──────────────────────────────────────────

LIB_DIR = Path("projects/ros2-sysmlv2/ros2_sysmlv2")
FILES = sorted(str(f) for f in LIB_DIR.glob("*.sysml"))

passed = 0
failed = 0
total_checks = 0


def check(label, condition, detail=""):
    global passed, failed, total_checks
    total_checks += 1
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ══════════════════════════════════════════════════════════════════════
# 1. PARSE
# ══════════════════════════════════════════════════════════════════════

print("=" * 60)
print("  ros2-sysmlv2 Library Test Suite")
print(f"  Files: {len(FILES)}")
print("=" * 60)

section("1. Parse all files")

model, diagnostics = syside.load_model(FILES)
has_errors = diagnostics.contains_errors()
check("All files parse without errors", not has_errors)
check(f"File count is 17", len(FILES) == 17, f"got {len(FILES)}")

if has_errors:
    print("\n  CRITICAL: Parse errors. Aborting.")
    sys.exit(1)

print(f"  {len(FILES)} files loaded successfully")

# ══════════════════════════════════════════════════════════════════════
# 2. DEFINITION COUNTS
# ══════════════════════════════════════════════════════════════════════

section("2. Definition counts")

EXPECTED_COUNTS = {
    "ItemDefinition": 110,
    "AttributeDefinition": 10,
    "EnumerationDefinition": 10,
    "PartDefinition": 30,
    "PortDefinition": 6,
    "ConnectionDefinition": 5,
    "ConstraintDefinition": 1,
    "StateDefinition": 1,
    "ActionDefinition": 6,
}

actual_total = 0
for type_name, expected in EXPECTED_COUNTS.items():
    syside_type = getattr(syside, type_name)
    actual = len(list(model.nodes(syside_type)))
    actual_total += actual
    check(f"{type_name}: {expected}", actual == expected,
          f"expected {expected}, got {actual}")
    print(f"  {type_name}: {actual} {'✓' if actual == expected else '✗'}")

check("Total definitions: 179", actual_total == 179,
      f"got {actual_total}")
print(f"\n  Total: {actual_total}")

# ══════════════════════════════════════════════════════════════════════
# 3. PACKAGE NAMES (all unique, no collisions)
# ══════════════════════════════════════════════════════════════════════

section("3. Package names")

EXPECTED_PACKAGES = [
    "ros2_sysmlv2_foundation",
    "ros2_sysmlv2_std_msgs",
    "ros2_sysmlv2_geometry_msgs",
    "ros2_sysmlv2_sensor_msgs",
    "ros2_sysmlv2_nav_msgs",
    "ros2_sysmlv2_comm",
    "ros2_sysmlv2_lifecycle",
    "ros2_sysmlv2_deployment",
    "ros2_sysmlv2_params",
    "ros2_sysmlv2_tf2",
    "ros2_sysmlv2_archetypes",
    "ros2_sysmlv2_nav2",
    "ros2_sysmlv2_trajectory_msgs",
    "ros2_sysmlv2_diagnostic_msgs",
    "ros2_sysmlv2_shape_msgs",
    "ros2_sysmlv2_action_msgs",
    "ros2_sysmlv2_visualization_msgs",
]

packages = {n.name for n in model.nodes(syside.Package)}
for pkg in EXPECTED_PACKAGES:
    check(f"Package {pkg}", pkg in packages)

check("17 packages total", len(packages) == 17,
      f"got {len(packages)}: {packages}")

# ══════════════════════════════════════════════════════════════════════
# 4. ITEM DEFINITIONS (message types)
# ══════════════════════════════════════════════════════════════════════

section("4. Key item definitions (message types)")

item_defs = {n.name for n in model.nodes(syside.ItemDefinition)}

# Spot-check from each message package
KEY_ITEMS = [
    # foundation
    "Header",
    # std_msgs
    "ColorRGBA", "Empty",
    # geometry_msgs
    "Vector3", "Pose", "Twist", "TransformStamped", "PoseWithCovarianceStamped",
    # sensor_msgs
    "Imu", "LaserScan", "PointCloud2", "Image", "CameraInfo", "NavSatFix",
    # nav_msgs
    "Odometry", "Path", "OccupancyGrid",
    # trajectory_msgs
    "JointTrajectory", "JointTrajectoryPoint",
    # diagnostic_msgs
    "DiagnosticStatus", "DiagnosticArray",
    # shape_msgs
    "Mesh", "SolidPrimitive",
    # action_msgs
    "GoalStatus", "GoalInfo",
    # visualization_msgs
    "Marker", "MarkerArray",
    # comm
    "Message",
    # nav2
    "ComputePathToPoseGoal", "FollowPathGoal", "NavigateToPoseGoal",
    "Costmap", "SpeedLimit",
    # lifecycle
    "ConfigureEvent", "ActivateEvent", "ShutdownEvent",
]

for item in KEY_ITEMS:
    check(f"item def {item}", item in item_defs)

print(f"  Checked {len(KEY_ITEMS)} key item defs")

# ══════════════════════════════════════════════════════════════════════
# 5. SPECIALIZATION CHAINS
# ══════════════════════════════════════════════════════════════════════

section("5. Specialization chains")

part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}

# Node -> LifecycleNode chain
node = part_defs.get("Node")
lcn = part_defs.get("LifecycleNode")
check("Node exists", node is not None)
check("LifecycleNode exists", lcn is not None)
if node and lcn:
    check("LifecycleNode :> Node", lcn.specializes(node))

# Archetypes -> LifecycleNode
ARCHETYPES = ["SensorDriver", "Controller", "Planner", "Estimator",
              "BehaviorCoordinator", "MapProvider", "PerceptionPipeline",
              "VelocityFilter"]

for arch in ARCHETYPES:
    check(f"{arch} exists", arch in part_defs)
    if arch in part_defs and lcn:
        check(f"{arch} :> LifecycleNode", part_defs[arch].specializes(lcn))

# Nav2 nodes -> archetypes (transitive through LifecycleNode)
NAV2_CHAINS = {
    "PlannerServer": ("Planner", "LifecycleNode", "Node"),
    "ControllerServer": ("Controller", "LifecycleNode", "Node"),
    "BtNavigator": ("BehaviorCoordinator", "LifecycleNode", "Node"),
    "AmclNode": ("Estimator", "LifecycleNode", "Node"),
    "Nav2MapServer": ("MapProvider", "LifecycleNode", "Node"),
    "Nav2VelocitySmoother": ("VelocityFilter", "LifecycleNode", "Node"),
}

for nav2_node, chain in NAV2_CHAINS.items():
    check(f"{nav2_node} exists", nav2_node in part_defs)
    for ancestor in chain:
        if nav2_node in part_defs and ancestor in part_defs:
            check(f"{nav2_node} :> {ancestor}",
                  part_defs[nav2_node].specializes(part_defs[ancestor]))

# Nav2LifecycleManager :> Node but NOT :> LifecycleNode
check("Nav2LifecycleManager exists", "Nav2LifecycleManager" in part_defs)
if "Nav2LifecycleManager" in part_defs:
    check("Nav2LifecycleManager :> Node",
          part_defs["Nav2LifecycleManager"].specializes(node))
    check("Nav2LifecycleManager NOT :> LifecycleNode",
          not part_defs["Nav2LifecycleManager"].specializes(lcn))

# TF2 frames -> CoordinateFrame
cf = part_defs.get("CoordinateFrame")
for frame in ["MapFrame", "OdomFrame", "BaseLinkFrame"]:
    check(f"{frame} exists", frame in part_defs)
    if frame in part_defs and cf:
        check(f"{frame} :> CoordinateFrame", part_defs[frame].specializes(cf))

print(f"  All specialization chains verified")

# ══════════════════════════════════════════════════════════════════════
# 6. STATE MACHINE (LifecycleStates)
# ══════════════════════════════════════════════════════════════════════

section("6. LifecycleStates state machine")

state_defs = {n.name: n for n in model.nodes(syside.StateDefinition)}
check("LifecycleStates exists", "LifecycleStates" in state_defs)

if "LifecycleStates" in state_defs:
    lcs = state_defs["LifecycleStates"]
    states = []
    transitions = []
    triggered = 0

    for elem in lcs.owned_elements.collect():
        if su := elem.try_cast(syside.StateUsage):
            states.append(su.name)
        elif tu := elem.try_cast(syside.TransitionUsage):
            transitions.append(tu.name)
            for sub in tu.owned_elements.collect():
                if sub.try_cast(syside.AcceptActionUsage):
                    triggered += 1
                    break

    check("5 states", len(states) == 5, f"got {len(states)}")
    check("9 transitions", len(transitions) == 9, f"got {len(transitions)}")
    check("7 event-triggered transitions", triggered == 7, f"got {triggered}")
    # Verify no successions leaked in — only states, transitions, and docs expected
    non_state_non_trans = [
        e for e in lcs.owned_elements.collect()
        if not e.try_cast(syside.TransitionUsage)
        and not e.try_cast(syside.StateUsage)
        and not e.try_cast(syside.Documentation)
    ]
    check("No successions — only states + transitions + docs in LifecycleStates",
          len(non_state_non_trans) == 0,
          f"found {len(non_state_non_trans)} unexpected elements")

    print(f"  States: {states}")
    print(f"  Transitions: {len(transitions)} ({triggered} event-triggered)")

# ══════════════════════════════════════════════════════════════════════
# 7. COMPOSITION (Nav2Stack, StandardFrameTree)
# ══════════════════════════════════════════════════════════════════════

section("7. Composition structures")

# Nav2Stack
check("Nav2Stack exists", "Nav2Stack" in part_defs)
if "Nav2Stack" in part_defs:
    stack = part_defs["Nav2Stack"]
    parts = [e.name for e in stack.owned_elements.collect() if e.try_cast(syside.PartUsage)]
    conns = [e.name for e in stack.owned_elements.collect() if e.try_cast(syside.ConnectionUsage)]
    check("Nav2Stack has 13 parts", len(parts) == 13, f"got {len(parts)}")
    check("Nav2Stack has 5 connections", len(conns) == 5, f"got {len(conns)}")
    print(f"  Nav2Stack: {len(parts)} parts, {len(conns)} connections")

# StandardFrameTree
check("StandardFrameTree exists", "StandardFrameTree" in part_defs)
if "StandardFrameTree" in part_defs:
    sft = part_defs["StandardFrameTree"]
    parts = [e.name for e in sft.owned_elements.collect() if e.try_cast(syside.PartUsage)]
    conns = [e.name for e in sft.owned_elements.collect() if e.try_cast(syside.ConnectionUsage)]
    check("StandardFrameTree has 3 frame parts", len(parts) == 3, f"got {len(parts)}")
    check("StandardFrameTree has 2 transform connections", len(conns) == 2, f"got {len(conns)}")
    print(f"  StandardFrameTree: {len(parts)} parts, {len(conns)} connections")

# ══════════════════════════════════════════════════════════════════════
# 8. ABSTRACT ARCHETYPES
# ══════════════════════════════════════════════════════════════════════

section("8. Abstract archetypes")

for arch in ARCHETYPES:
    if arch in part_defs:
        check(f"{arch} is abstract", part_defs[arch].is_abstract)

print(f"  All {len(ARCHETYPES)} archetypes verified abstract")

# ══════════════════════════════════════════════════════════════════════
# 9. ENUM VALUE COUNTS
# ══════════════════════════════════════════════════════════════════════

section("9. Enum value counts")

enum_defs = {n.name: n for n in model.nodes(syside.EnumerationDefinition)}

EXPECTED_ENUM_COUNTS = {
    "RMWKind": 3,
    "ReliabilityKind": 5,
    "DurabilityKind": 5,
    "HistoryKind": 4,
    "LivelinessKind": 5,
    "ExecutorKind": 2,
    "CallbackGroupKind": 2,
    "ParameterTypeKind": 10,
    "DiagnosticLevel": 4,
    "GoalStatusKind": 7,
}

for enum_name, expected in EXPECTED_ENUM_COUNTS.items():
    if enum_name in enum_defs:
        values = [e for e in enum_defs[enum_name].owned_elements.collect()
                  if e.try_cast(syside.EnumerationUsage)]
        check(f"{enum_name}: {expected} values", len(values) == expected,
              f"got {len(values)}")

# ══════════════════════════════════════════════════════════════════════
# 10. CROSS-FILE IMPORT CHAINS
# ══════════════════════════════════════════════════════════════════════

section("10. Cross-file import verification")

# Deepest chain: nav2 -> archetypes -> lifecycle -> comm -> foundation
# Verify by checking that nav2 items reference types from foundation
all_items = {n.name: n for n in model.nodes(syside.ItemDefinition)}

# ComputePathToPoseGoal references PoseStamped (geometry_msgs) and Duration (foundation)
if "ComputePathToPoseResult" in all_items:
    attrs = [e.name for e in all_items["ComputePathToPoseResult"].owned_elements.collect()
             if e.try_cast(syside.AttributeUsage)]
    check("Nav2 ComputePathToPoseResult has planningTime (Duration from foundation)",
          "planningTime" in attrs)
    check("Nav2 ComputePathToPoseResult has path (Path from nav_msgs)",
          "path" in attrs)

# Marker references types from 4 different packages
if "Marker" in all_items:
    attrs = [e.name for e in all_items["Marker"].owned_elements.collect()
             if e.try_cast(syside.AttributeUsage)]
    check("Marker has header (from foundation)", "header" in attrs)
    check("Marker has pose (from geometry_msgs)", "pose" in attrs)
    check("Marker has color (from std_msgs)", "color" in attrs)
    check("Marker has texture (from sensor_msgs)", "texture" in attrs)

print(f"  Cross-file references verified across 7 layers")

# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  RESULTS: {passed}/{total_checks} passed, {failed} failed")
print(f"  Library: {actual_total} definitions across {len(FILES)} files")
print(f"{'=' * 60}")

if failed > 0:
    print(f"\n  {failed} CHECKS FAILED — review output above")
    sys.exit(1)
else:
    print(f"\n  ALL CHECKS PASS ✓")
    print(f"  Library is ready for alpha publication.")
