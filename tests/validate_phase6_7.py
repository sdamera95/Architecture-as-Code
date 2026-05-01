"""Phase 6+7 validation: archetypes.sysml + nav2.sysml

Loads all 12 library .sysml files and validates:
  1. Parse success
  2. Archetypes are abstract and specialize LifecycleNode
  3. Nav2 server nodes specialize correct archetypes
  4. Nav2Stack composition
  5. Cumulative definition counts
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
print("Phase 6+7 Validation: archetypes.sysml + nav2.sysml")
print("=" * 60)

model, diagnostics = syside.load_model(FILES)
has_errors = diagnostics.contains_errors()
check("All 12 files parse without errors", not has_errors)

if has_errors:
    print("\nCritical: parse errors found. Cannot continue.")
    sys.exit(1)

# ── Build lookup tables ───────────────────────────────────────────────

part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}
item_defs = {n.name for n in model.nodes(syside.ItemDefinition)}
conn_defs = {n.name for n in model.nodes(syside.ConnectionDefinition)}

# ── Archetypes: exist and are abstract ────────────────────────────────

print("\n" + "-" * 60)
print("Archetype definitions")
print("-" * 60)

ARCHETYPES = [
    "SensorDriver", "Controller", "Planner", "Estimator",
    "BehaviorCoordinator", "MapProvider", "PerceptionPipeline",
    "VelocityFilter",
]

for arch in ARCHETYPES:
    check(f"part def {arch} exists", arch in part_defs)
    if arch in part_defs:
        pd = part_defs[arch]
        check(f"  {arch} is abstract", pd.is_abstract)

# ── Archetype specialization chains ──────────────────────────────────

print("\n" + "-" * 60)
print("Archetype specialization chains")
print("-" * 60)

lcn = part_defs.get("LifecycleNode")
if lcn:
    for arch in ARCHETYPES:
        if arch in part_defs:
            check(f"  {arch} specializes LifecycleNode",
                  part_defs[arch].specializes(lcn))

# ── Nav2 action item defs ────────────────────────────────────────────

print("\n" + "-" * 60)
print("Nav2 action item defs")
print("-" * 60)

NAV2_ITEMS = [
    "ComputePathToPoseGoal", "ComputePathToPoseResult",
    "FollowPathGoal", "FollowPathFeedback",
    "NavigateToPoseGoal", "NavigateToPoseFeedback",
    "SmoothPathGoal", "SmoothPathResult",
    "SpinGoal", "BackUpGoal", "WaitGoal",
    "Costmap", "SpeedLimit",
]

for item in NAV2_ITEMS:
    check(f"item def {item} exists", item in item_defs)

# ── Nav2 server nodes ────────────────────────────────────────────────

print("\n" + "-" * 60)
print("Nav2 server nodes")
print("-" * 60)

NAV2_NODES = [
    "PlannerServer", "ControllerServer", "BtNavigator",
    "BehaviorServer", "SmootherServer", "Costmap2DROS",
    "AmclNode", "Nav2MapServer", "Nav2VelocitySmoother",
    "Nav2CollisionMonitor", "Nav2LifecycleManager",
]

for node in NAV2_NODES:
    check(f"part def {node} exists", node in part_defs)

# ── Nav2 node specialization chains ──────────────────────────────────

print("\n" + "-" * 60)
print("Nav2 node specialization chains")
print("-" * 60)

SPECIALIZATIONS = {
    "PlannerServer": "Planner",
    "ControllerServer": "Controller",
    "BtNavigator": "BehaviorCoordinator",
    "SmootherServer": "Planner",
    "AmclNode": "Estimator",
    "Nav2MapServer": "MapProvider",
    "Nav2VelocitySmoother": "VelocityFilter",
    "Nav2CollisionMonitor": "VelocityFilter",
}

for node, archetype in SPECIALIZATIONS.items():
    if node in part_defs and archetype in part_defs:
        check(f"  {node} specializes {archetype}",
              part_defs[node].specializes(part_defs[archetype]))

# BehaviorServer and Costmap2DROS specialize LifecycleNode directly
for node in ["BehaviorServer", "Costmap2DROS"]:
    if node in part_defs and lcn:
        check(f"  {node} specializes LifecycleNode",
              part_defs[node].specializes(lcn))

# Nav2LifecycleManager specializes Node (NOT LifecycleNode)
node_base = part_defs.get("Node")
if "Nav2LifecycleManager" in part_defs and node_base:
    check("  Nav2LifecycleManager specializes Node",
          part_defs["Nav2LifecycleManager"].specializes(node_base))
    if lcn:
        check("  Nav2LifecycleManager does NOT specialize LifecycleNode",
              not part_defs["Nav2LifecycleManager"].specializes(lcn))

# ── Nav2Stack composition ─────────────────────────────────────────────

print("\n" + "-" * 60)
print("Nav2Stack composition")
print("-" * 60)

check("part def Nav2Stack exists", "Nav2Stack" in part_defs)

if "Nav2Stack" in part_defs:
    stack = part_defs["Nav2Stack"]
    parts = []
    connections = []
    for elem in stack.owned_elements.collect():
        if pu := elem.try_cast(syside.PartUsage):
            parts.append(pu.name)
        elif cu := elem.try_cast(syside.ConnectionUsage):
            connections.append(cu.name)

    print(f"  Parts ({len(parts)}): {parts}")
    print(f"  Connections ({len(connections)}): {connections}")

    EXPECTED_PARTS = [
        "planner", "controller", "btNavigator", "behaviors",
        "smoother", "globalCostmap", "localCostmap", "amcl",
        "mapServer", "velocitySmoother", "collisionMonitor",
        "lifecycleManager", "frames",
    ]
    for p in EXPECTED_PARTS:
        check(f"  has {p} part", p in parts)

    check(f"  has velToSmoother connection", "velToSmoother" in connections)
    check(f"  has smootherToMonitor connection", "smootherToMonitor" in connections)
    check(f"  has mapToAmcl connection", "mapToAmcl" in connections)

# ── Cumulative counts ─────────────────────────────────────────────────

print("\n" + "-" * 60)
print("Cumulative definition counts (all 12 files)")
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
    print("\nAll Phase 6+7 checks PASS")
