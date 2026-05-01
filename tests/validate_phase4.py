"""Phase 4 validation: lifecycle.sysml + deployment.sysml

Loads all 8 library .sysml files together and validates:
  1. Parse success (no errors)
  2. Lifecycle definitions present and correct
  3. Deployment definitions present and correct
  4. State machine structure (states, transitions)
  5. Specialization chain: LifecycleNode :> Node
  6. Cross-layer imports resolve
"""
import syside
import sys

# All library files (layers 1-4)
FILES = [
    "projects/ros2-sysmlv2/ros2_sysmlv2/foundation.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/std_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/geometry_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/sensor_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/nav_msgs.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/comm.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/lifecycle.sysml",
    "projects/ros2-sysmlv2/ros2_sysmlv2/deployment.sysml",
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
print("Phase 4 Validation: lifecycle.sysml + deployment.sysml")
print("=" * 60)

model, diagnostics = syside.load_model(FILES)
has_errors = diagnostics.contains_errors()
check("All 8 files parse without errors", not has_errors)

if has_errors:
    print("\nCritical: parse errors found. Cannot continue validation.")
    # Try to extract diagnostic info
    try:
        for d in diagnostics:
            print(f"  {d}")
    except TypeError:
        print("  (diagnostics not iterable — check Syside Editor for details)")
    sys.exit(1)

# ── Lifecycle item defs (trigger events) ──────────────────────────────

print("\n" + "-" * 60)
print("Lifecycle Trigger Events (item defs)")
print("-" * 60)

EXPECTED_EVENTS = [
    "ConfigureEvent", "CleanupEvent", "ActivateEvent",
    "DeactivateEvent", "ShutdownEvent", "ErrorEvent",
]

item_defs = {n.name for n in model.nodes(syside.ItemDefinition)}
for ev in EXPECTED_EVENTS:
    check(f"item def {ev} exists", ev in item_defs)

# ── Lifecycle action defs (callbacks) ─────────────────────────────────

print("\n" + "-" * 60)
print("Lifecycle Callbacks (action defs)")
print("-" * 60)

EXPECTED_ACTIONS = [
    "OnConfigure", "OnCleanup", "OnActivate",
    "OnDeactivate", "OnShutdown", "OnError",
]

action_defs = {n.name for n in model.nodes(syside.ActionDefinition)}
for act in EXPECTED_ACTIONS:
    check(f"action def {act} exists", act in action_defs)

# ── State machine: LifecycleStates ────────────────────────────────────

print("\n" + "-" * 60)
print("LifecycleStates state machine")
print("-" * 60)

state_defs = {n.name: n for n in model.nodes(syside.StateDefinition)}
check("state def LifecycleStates exists", "LifecycleStates" in state_defs)

if "LifecycleStates" in state_defs:
    lcs = state_defs["LifecycleStates"]
    states = []
    transitions = []

    for elem in lcs.owned_elements.collect():
        if su := elem.try_cast(syside.StateUsage):
            states.append(su.name)
        elif tu := elem.try_cast(syside.TransitionUsage):
            transitions.append(tu.name)

    print(f"\n  States found: {states}")
    print(f"  Transitions found: {transitions}")

    EXPECTED_STATES = ["unconfigured", "inactive", "active", "finalized", "errorProcessing"]
    for s in EXPECTED_STATES:
        check(f"  state {s} exists", s in states)

    check(f"  5 states total", len(states) == 5, f"got {len(states)}")

    EXPECTED_TRANSITIONS = [
        "configure", "cleanup", "activate", "deactivate",
        "shutdownFromUnconfigured", "shutdownFromInactive",
        "shutdownFromActive", "errorRecoverySuccess", "errorRecoveryFailure",
    ]
    for t in EXPECTED_TRANSITIONS:
        check(f"  transition {t} exists", t in transitions)

    check(f"  9 transitions total", len(transitions) == 9, f"got {len(transitions)}")

    # Check that transitions are TransitionUsage (not SuccessionAsUsage)
    succession_count = 0
    for elem in lcs.owned_elements.collect():
        if elem.try_cast(syside.SuccessionAsUsage):
            succession_count += 1
    # TransitionUsage also contains SuccessionAsUsage internally,
    # so we check that the top-level owned elements are TransitionUsage
    transition_usage_count = sum(1 for elem in lcs.owned_elements.collect()
                                 if elem.try_cast(syside.TransitionUsage))
    check("  All transitions are TransitionUsage (not plain successions)",
          transition_usage_count == 9, f"got {transition_usage_count}")

    # Check for AcceptActionUsage in triggered transitions
    triggered_count = 0
    for elem in lcs.owned_elements.collect():
        if tu := elem.try_cast(syside.TransitionUsage):
            for sub in tu.owned_elements.collect():
                if sub.try_cast(syside.AcceptActionUsage):
                    triggered_count += 1
                    break
    check(f"  7 transitions have AcceptActionUsage (event triggers)",
          triggered_count == 7, f"got {triggered_count}")

# ── Part defs: Node and LifecycleNode ─────────────────────────────────

print("\n" + "-" * 60)
print("Node and LifecycleNode part defs")
print("-" * 60)

part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}
check("part def Node exists", "Node" in part_defs)
check("part def LifecycleNode exists", "LifecycleNode" in part_defs)

if "Node" in part_defs:
    node_attrs = []
    for elem in part_defs["Node"].owned_elements.collect():
        if au := elem.try_cast(syside.AttributeUsage):
            node_attrs.append(au.name)
    check("  Node has nodeName attribute", "nodeName" in node_attrs)
    check("  Node has namespace attribute", "namespace" in node_attrs)

if "LifecycleNode" in part_defs and "Node" in part_defs:
    lcn = part_defs["LifecycleNode"]
    node = part_defs["Node"]
    # specializes(Type) -> bool: checks if LifecycleNode :> Node
    check("  LifecycleNode specializes Node", lcn.specializes(node))

    # Check exhibit state
    has_exhibit = False
    for elem in lcn.owned_elements.collect():
        if su := elem.try_cast(syside.StateUsage):
            if su.name == "lifecycleState":
                has_exhibit = True
    check("  LifecycleNode exhibits lifecycleState", has_exhibit)

# ── Deployment definitions ────────────────────────────────────────────

print("\n" + "-" * 60)
print("Deployment definitions")
print("-" * 60)

# Enum defs
enum_defs = {n.name for n in model.nodes(syside.EnumerationDefinition)}
check("enum def ExecutorKind exists", "ExecutorKind" in enum_defs)
check("enum def CallbackGroupKind exists", "CallbackGroupKind" in enum_defs)

# Part defs
check("part def CallbackGroup exists", "CallbackGroup" in part_defs)
check("part def Executor exists", "Executor" in part_defs)
check("part def Container exists", "Container" in part_defs)

# Attribute defs
attr_defs = {n.name for n in model.nodes(syside.AttributeDefinition)}
check("attribute def NodeDeployment exists", "NodeDeployment" in attr_defs)

# Check Executor attributes
if "Executor" in part_defs:
    exec_attrs = []
    for elem in part_defs["Executor"].owned_elements.collect():
        if au := elem.try_cast(syside.AttributeUsage):
            exec_attrs.append(au.name)
    check("  Executor has kind attribute", "kind" in exec_attrs)
    check("  Executor has numThreads attribute", "numThreads" in exec_attrs)

# Check Container has executor part
if "Container" in part_defs:
    container_parts = []
    container_attrs = []
    for elem in part_defs["Container"].owned_elements.collect():
        if pu := elem.try_cast(syside.PartUsage):
            container_parts.append(pu.name)
        elif au := elem.try_cast(syside.AttributeUsage):
            container_attrs.append(au.name)
    check("  Container has executor part", "executor" in container_parts)
    check("  Container has containerName attribute", "containerName" in container_attrs)

# ── Cumulative definition counts ──────────────────────────────────────

print("\n" + "-" * 60)
print("Cumulative definition counts (all 8 files)")
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
    print("\nAll Phase 4 checks PASS")
