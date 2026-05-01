"""Lifecycle + Deployment conformance checker for Phase 4.

Validates lifecycle.sysml and deployment.sysml against ROS2 Jazzy source:
  - lifecycle_msgs/msg/State.msg (4 primary states, 6 transition states)
  - lifecycle_msgs/msg/Transition.msg (9 public transitions)
  - lifecycle_msgs/srv/ (4 lifecycle services)
  - rclpy/lifecycle/node.py (LifecycleNode callbacks)
  - rclpy/executors.py (SingleThreadedExecutor, MultiThreadedExecutor)
  - rclpy/callback_groups.py (ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup)
"""
import re
import sys
from pathlib import Path

# ── Ground truth extraction ────────────────────────────────────────────

REFS = Path("references")
LIFECYCLE_MSG = REFS / "rcl_interfaces/lifecycle_msgs/msg"
LIFECYCLE_SRV = REFS / "rcl_interfaces/lifecycle_msgs/srv"
RCLPY = REFS / "rclpy/rclpy/rclpy"

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


# ── Parse State.msg ────────────────────────────────────────────────────

print("=" * 60)
print("1. Lifecycle State Ground Truth (State.msg)")
print("=" * 60)

state_msg = (LIFECYCLE_MSG / "State.msg").read_text()

# Extract PRIMARY_STATE constants
primary_states = {}
for m in re.finditer(r'uint8 (PRIMARY_STATE_\w+)\s*=\s*(\d+)', state_msg):
    primary_states[m.group(1)] = int(m.group(2))

# Extract TRANSITION_STATE constants
transition_states = {}
for m in re.finditer(r'uint8 (TRANSITION_STATE_\w+)\s*=\s*(\d+)', state_msg):
    transition_states[m.group(1)] = int(m.group(2))

print(f"\nPrimary states ({len(primary_states)}):")
for name, val in primary_states.items():
    info(f"  {name} = {val}")

print(f"\nTransition states ({len(transition_states)}):")
for name, val in transition_states.items():
    info(f"  {name} = {val}")

check("State.msg has 5 primary states (including UNKNOWN)",
      len(primary_states) == 5)
check("State.msg has 6 transition states",
      len(transition_states) == 6)

# The 4 modeled primary states (excluding UNKNOWN)
EXPECTED_PRIMARY = {
    "Unconfigured": 1,
    "Inactive": 2,
    "Active": 3,
    "Finalized": 4,
}

# ── Parse Transition.msg ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("2. Lifecycle Transition Ground Truth (Transition.msg)")
print("=" * 60)

trans_msg = (LIFECYCLE_MSG / "Transition.msg").read_text()

# Extract public transition constants (IDs 0-9)
public_transitions = {}
for m in re.finditer(r'uint8 (TRANSITION_\w+)\s*=\s*(\d+)', trans_msg):
    tid = int(m.group(2))
    if tid < 10:
        public_transitions[m.group(1)] = tid

print(f"\nPublic transitions ({len(public_transitions)}):")
for name, val in public_transitions.items():
    info(f"  {name} = {val}")

# The transitions we model (excluding CREATE and DESTROY which are
# construction/destruction, not state machine transitions)
EXPECTED_TRANSITIONS = {
    "configure": ("unconfigured", "inactive"),
    "cleanup": ("inactive", "unconfigured"),
    "activate": ("inactive", "active"),
    "deactivate": ("active", "inactive"),
    "shutdownFromUnconfigured": ("unconfigured", "finalized"),
    "shutdownFromInactive": ("inactive", "finalized"),
    "shutdownFromActive": ("active", "finalized"),
}

check("Transition.msg has 9 public transitions (IDs 0-8)",
      len(public_transitions) == 9,
      f"got {len(public_transitions)}")

# ── Parse lifecycle services ──────────────────────────────────────────

print("\n" + "=" * 60)
print("3. Lifecycle Services Ground Truth (lifecycle_msgs/srv/)")
print("=" * 60)

EXPECTED_SERVICES = [
    "ChangeState",
    "GetState",
    "GetAvailableStates",
    "GetAvailableTransitions",
]

srv_files = sorted(LIFECYCLE_SRV.glob("*.srv"))
srv_names = [f.stem for f in srv_files]
print(f"\nService files found: {srv_names}")

for srv in EXPECTED_SERVICES:
    check(f"Service {srv}.srv exists", srv in srv_names)

# ── Parse rclpy LifecycleNode callbacks ───────────────────────────────

print("\n" + "=" * 60)
print("4. LifecycleNode Callback Ground Truth (rclpy lifecycle)")
print("=" * 60)

lifecycle_node = (RCLPY / "lifecycle/node.py").read_text()

EXPECTED_CALLBACKS = [
    "on_configure",
    "on_cleanup",
    "on_shutdown",
    "on_activate",
    "on_deactivate",
    "on_error",
]

for cb in EXPECTED_CALLBACKS:
    found = f"def {cb}" in lifecycle_node
    check(f"Callback {cb}() defined in LifecycleNode", found)

# ── Parse rclpy executors ─────────────────────────────────────────────

print("\n" + "=" * 60)
print("5. Executor Ground Truth (rclpy/executors.py)")
print("=" * 60)

executors_src = (RCLPY / "executors.py").read_text()

check("SingleThreadedExecutor class exists",
      "class SingleThreadedExecutor" in executors_src)
check("MultiThreadedExecutor class exists",
      "class MultiThreadedExecutor" in executors_src)

# MultiThreadedExecutor has num_threads parameter
check("MultiThreadedExecutor has num_threads param",
      "num_threads" in executors_src)

# ── Parse rclpy callback groups ───────────────────────────────────────

print("\n" + "=" * 60)
print("6. Callback Group Ground Truth (rclpy/callback_groups.py)")
print("=" * 60)

cbg_src = (RCLPY / "callback_groups.py").read_text()

check("ReentrantCallbackGroup class exists",
      "class ReentrantCallbackGroup" in cbg_src)
check("MutuallyExclusiveCallbackGroup class exists",
      "class MutuallyExclusiveCallbackGroup" in cbg_src)

# ── Parse rclpy Node.__init__ for base node params ────────────────────

print("\n" + "=" * 60)
print("7. Node Base Parameters Ground Truth (rclpy/node.py)")
print("=" * 60)

node_src = (RCLPY / "node.py").read_text()

# Key parameters from Node.__init__
NODE_PARAMS = ["node_name", "namespace"]
for param in NODE_PARAMS:
    check(f"Node.__init__ has '{param}' parameter",
          param in node_src)

# ── Summary ───────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print(f"Ground Truth Summary: {passed} passed, {failed} failed, {info_count} info")
print("=" * 60)

if failed > 0:
    print("\nFAILED — ground truth extraction has issues")
    sys.exit(1)
else:
    print("\nAll ground truth checks PASS — ready to build lifecycle.sysml and deployment.sysml")

# ── Export expected data for post-build validation ────────────────────

print("\n" + "-" * 60)
print("Expected SysML definitions to produce:")
print("-" * 60)

print("\nlifecycle.sysml:")
print("  - item def: ConfigureEvent, ActivateEvent, DeactivateEvent, CleanupEvent, ShutdownEvent, ErrorEvent")
print("  - action def: OnConfigure, OnCleanup, OnShutdown, OnActivate, OnDeactivate, OnError")
print(f"  - state def: LifecycleStates (5 states: {', '.join(EXPECTED_PRIMARY.keys())} + errorProcessing)")
print(f"  - transitions: {len(EXPECTED_TRANSITIONS)} named transitions")
print("  - part def: Node (nodeName, namespace)")
print("  - part def: LifecycleNode :> Node (exhibit state lifecycleState : LifecycleStates)")
print("  - port def: LifecycleServicePort (4 services: ChangeState, GetState, GetAvailableStates, GetAvailableTransitions)")

print("\ndeployment.sysml:")
print("  - enum def: ExecutorKind (SingleThreaded, MultiThreaded)")
print("  - enum def: CallbackGroupKind (MutuallyExclusive, Reentrant)")
print("  - part def: CallbackGroup")
print("  - part def: Executor")
print("  - part def: Container")
print("  - attribute def: NodeDeployment (remappings, parameterFile, rmwConfig)")
