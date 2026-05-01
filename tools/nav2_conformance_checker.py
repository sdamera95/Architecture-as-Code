"""Nav2 conformance checker for merged Phase 6+7.

Validates archetypes.sysml and nav2.sysml against Nav2 Jazzy source:
  - nav2_msgs/action/*.action (action type structures)
  - Nav2 server node source (class inheritance, communication endpoints)

This checker validates that:
  1. Nav2 action types exist as .action files
  2. All key server nodes inherit from LifecycleNode (except LifecycleManager)
  3. Core communication endpoints match source (pub/sub/action topics)
"""
import re
import sys
from pathlib import Path

REFS = Path("references")
NAV2 = REFS / "navigation2"
NAV2_MSGS = NAV2 / "nav2_msgs"

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


# ══════════════════════════════════════════════════════════════════════
# 1. Nav2 Action Types
# ══════════════════════════════════════════════════════════════════════

print("=" * 60)
print("1. Nav2 Action Types (nav2_msgs/action/)")
print("=" * 60)

action_files = sorted((NAV2_MSGS / "action").glob("*.action"))
action_names = [f.stem for f in action_files]

print(f"\nAction files found ({len(action_names)}):")
for name in action_names:
    info(f"  {name}")

# Key actions we model
KEY_ACTIONS = [
    "ComputePathToPose",
    "FollowPath",
    "NavigateToPose",
    "SmoothPath",
    "Spin",
    "BackUp",
    "Wait",
]

for act in KEY_ACTIONS:
    check(f"Action {act}.action exists", act in action_names)

# ══════════════════════════════════════════════════════════════════════
# 2. Nav2 Message Types
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("2. Nav2 Message Types (nav2_msgs/msg/)")
print("=" * 60)

msg_files = sorted((NAV2_MSGS / "msg").glob("*.msg"))
msg_names = [f.stem for f in msg_files]

KEY_MSGS = ["Costmap", "CostmapMetaData", "SpeedLimit", "ParticleCloud",
            "CollisionMonitorState"]

for msg in KEY_MSGS:
    check(f"Message {msg}.msg exists", msg in msg_names)

# ══════════════════════════════════════════════════════════════════════
# 3. Nav2 Service Types
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("3. Nav2 Service Types (nav2_msgs/srv/)")
print("=" * 60)

srv_files = sorted((NAV2_MSGS / "srv").glob("*.srv"))
srv_names = [f.stem for f in srv_files]

KEY_SRVS = ["IsPathValid", "LoadMap", "ManageLifecycleNodes", "GetCostmap"]

for srv in KEY_SRVS:
    check(f"Service {srv}.srv exists", srv in srv_names)

# ══════════════════════════════════════════════════════════════════════
# 4. Server Node Inheritance (all should be LifecycleNode)
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("4. Server Node Base Classes")
print("=" * 60)

SERVER_NODES = {
    "PlannerServer": ("nav2_planner", "planner_server.hpp", "LifecycleNode"),
    "ControllerServer": ("nav2_controller", "controller_server.hpp", "LifecycleNode"),
    "BtNavigator": ("nav2_bt_navigator", "bt_navigator.hpp", "LifecycleNode"),
    "BehaviorServer": ("nav2_behaviors", "behavior_server.hpp", "LifecycleNode"),
    "SmootherServer": ("nav2_smoother", "nav2_smoother.hpp", "LifecycleNode"),
    "AmclNode": ("nav2_amcl", "amcl_node.hpp", "LifecycleNode"),
    "MapServer": ("nav2_map_server", "map_server.hpp", "LifecycleNode"),
    "VelocitySmoother": ("nav2_velocity_smoother", "velocity_smoother.hpp", "LifecycleNode"),
    "CollisionMonitor": ("nav2_collision_monitor", "collision_monitor_node.hpp", "LifecycleNode"),
    "LifecycleManager": ("nav2_lifecycle_manager", "lifecycle_manager.hpp", "Node"),
}

for class_name, (pkg, header, expected_base) in SERVER_NODES.items():
    # Search for the header file
    headers = list(NAV2.glob(f"{pkg}/**/{header}"))
    if headers:
        src = headers[0].read_text()
        has_lifecycle = "LifecycleNode" in src
        has_plain_node = re.search(r':\s*public\s+.*Node\b', src) is not None
        if expected_base == "LifecycleNode":
            # Check for ": public ... LifecycleNode" pattern
            inherits_lc = bool(re.search(r'class\s+\w+\s*:\s*public\s+\S*LifecycleNode', src))
            check(f"{class_name} extends LifecycleNode", inherits_lc)
        else:
            # Check for ": public rclcpp::Node" (plain Node, not LifecycleNode)
            inherits_plain = bool(re.search(r'class\s+\w+\s*:\s*public\s+rclcpp::Node', src))
            check(f"{class_name} extends rclcpp::Node (plain)", inherits_plain)
    else:
        check(f"{class_name} header found", False, f"{header} not found in {pkg}")

# ══════════════════════════════════════════════════════════════════════
# 5. Core Communication Endpoints (spot checks from source)
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("5. Core Communication Endpoints (source verification)")
print("=" * 60)


def search_in_pkg(pkg, pattern):
    """Search all .cpp and .hpp files in a Nav2 package for a pattern."""
    for ext in ("*.cpp", "*.hpp"):
        for f in NAV2.glob(f"{pkg}/**/{ext}"):
            if re.search(pattern, f.read_text()):
                return True
    return False


# PlannerServer endpoints
check("PlannerServer has compute_path_to_pose action",
      search_in_pkg("nav2_planner", r'compute_path_to_pose'))
check("PlannerServer publishes plan topic",
      search_in_pkg("nav2_planner", r'"plan"'))

# ControllerServer endpoints
check("ControllerServer has follow_path action",
      search_in_pkg("nav2_controller", r'follow_path'))
check("ControllerServer publishes cmd_vel",
      search_in_pkg("nav2_controller", r'cmd_vel'))

# BtNavigator endpoints
check("BtNavigator has navigate_to_pose action",
      search_in_pkg("nav2_bt_navigator", r'navigate_to_pose'))

# SmootherServer endpoints
check("SmootherServer has smooth_path action",
      search_in_pkg("nav2_smoother", r'smooth_path'))

# AMCL endpoints
check("AMCL publishes amcl_pose topic",
      search_in_pkg("nav2_amcl", r'amcl_pose'))
check("AMCL subscribes to scan",
      search_in_pkg("nav2_amcl", r'scan'))
check("AMCL publishes TF (map->odom)",
      search_in_pkg("nav2_amcl", r'TransformBroadcaster'))

# MapServer endpoints
check("MapServer publishes map topic",
      search_in_pkg("nav2_map_server", r'"map"'))
check("MapServer has load_map service",
      search_in_pkg("nav2_map_server", r'load_map'))

# ══════════════════════════════════════════════════════════════════════
# 6. Action File Structure Validation
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("6. Action File Structure (goal/result/feedback)")
print("=" * 60)


def parse_action(path):
    """Parse a .action file into goal, result, feedback sections."""
    text = path.read_text()
    parts = text.split("---")
    return {
        "goal": parts[0].strip() if len(parts) > 0 else "",
        "result": parts[1].strip() if len(parts) > 1 else "",
        "feedback": parts[2].strip() if len(parts) > 2 else "",
    }


# ComputePathToPose: goal has PoseStamped, result has Path
cpt = parse_action(NAV2_MSGS / "action/ComputePathToPose.action")
check("ComputePathToPose goal has PoseStamped",
      "PoseStamped" in cpt["goal"])
check("ComputePathToPose result has Path",
      "Path" in cpt["result"])

# FollowPath: goal has Path, feedback has distance_to_goal
fp = parse_action(NAV2_MSGS / "action/FollowPath.action")
check("FollowPath goal has Path", "Path" in fp["goal"])
check("FollowPath feedback has distance_to_goal",
      "distance_to_goal" in fp["feedback"])

# NavigateToPose: goal has PoseStamped, feedback has current_pose
ntp = parse_action(NAV2_MSGS / "action/NavigateToPose.action")
check("NavigateToPose goal has PoseStamped",
      "PoseStamped" in ntp["goal"])
check("NavigateToPose feedback has distance_remaining",
      "distance_remaining" in ntp["feedback"])

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
    print("\nAll ground truth checks PASS — ready to build archetypes.sysml and nav2.sysml")
