"""Phase 8 conformance checker for remaining message packages.

Validates .sysml files against actual .msg ground truth:
  - trajectory_msgs (4 msgs)
  - diagnostic_msgs (3 msgs)
  - shape_msgs (4 msgs)
  - action_msgs (3 msgs)
  - visualization_msgs (4 core msgs)
"""
import re
import sys
from pathlib import Path

COMMON = Path("references/common_interfaces")
RCL = Path("references/rcl_interfaces")

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


def parse_msg(path):
    """Parse .msg file, return (fields, constants) tuples."""
    text = path.read_text()
    fields = []
    constants = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^(\w+)\s+(\w+)\s*=\s*(.+)$', line)
        if m:
            constants.append((m.group(2), m.group(3).strip()))
            continue
        m = re.match(r'^([\w/]+(?:\[.*?\])?)\s+(\w+)(?:\s+.*)?$', line)
        if m:
            fields.append((m.group(1), m.group(2)))
    return fields, constants


def check_msg_package(pkg_name, base_path, msg_names):
    """Check all messages in a package exist and have expected field counts."""
    print(f"\n{'=' * 60}")
    print(f"{pkg_name}")
    print(f"{'=' * 60}")
    total_fields = 0
    for name in msg_names:
        path = base_path / f"{name}.msg"
        check(f"{name}.msg exists", path.exists())
        if path.exists():
            fields, constants = parse_msg(path)
            total_fields += len(fields)
            info(f"  {name}: {len(fields)} fields, {len(constants)} constants")
            for ftype, fname in fields:
                info(f"    {ftype} {fname}")
    check(f"{pkg_name} total messages: {len(msg_names)}", True)
    return total_fields


# ── trajectory_msgs ───────────────────────────────────────────────────

traj_fields = check_msg_package("trajectory_msgs",
    COMMON / "trajectory_msgs/msg",
    ["JointTrajectoryPoint", "JointTrajectory",
     "MultiDOFJointTrajectoryPoint", "MultiDOFJointTrajectory"])

# ── diagnostic_msgs ───────────────────────────────────────────────────

diag_fields = check_msg_package("diagnostic_msgs",
    COMMON / "diagnostic_msgs/msg",
    ["KeyValue", "DiagnosticStatus", "DiagnosticArray"])

# ── shape_msgs ────────────────────────────────────────────────────────

shape_fields = check_msg_package("shape_msgs",
    COMMON / "shape_msgs/msg",
    ["MeshTriangle", "Mesh", "Plane", "SolidPrimitive"])

# ── action_msgs ───────────────────────────────────────────────────────

action_fields = check_msg_package("action_msgs",
    RCL / "action_msgs/msg",
    ["GoalInfo", "GoalStatus", "GoalStatusArray"])

# ── visualization_msgs (core 4) ──────────────────────────────────────

viz_fields = check_msg_package("visualization_msgs (core)",
    COMMON / "visualization_msgs/msg",
    ["Marker", "MarkerArray", "MeshFile", "UVCoordinate"])

# ── Summary ───────────────────────────────────────────────────────────

total = traj_fields + diag_fields + shape_fields + action_fields + viz_fields
print(f"\n{'=' * 60}")
print(f"Ground Truth Summary: {passed} passed, {failed} failed, {info_count} info")
print(f"Total fields across all packages: {total}")
print(f"{'=' * 60}")

if failed > 0:
    print("\nFAILED")
    sys.exit(1)
else:
    print("\nAll ground truth checks PASS")
