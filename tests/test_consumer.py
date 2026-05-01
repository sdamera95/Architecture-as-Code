"""Consumer test: validate a downstream robot model imports the library.

Simulates a user creating a robot model that uses ros2-sysmlv2 definitions.
Loads the library files + the consumer test model together and verifies
the consumer model composes correctly.
"""
import syside
import sys
from pathlib import Path

# Library files
LIB_DIR = Path("projects/ros2-sysmlv2/ros2_sysmlv2")
LIB_FILES = sorted(str(f) for f in LIB_DIR.glob("*.sysml"))

# Consumer model
CONSUMER_FILE = "tests/consumer_test_robot.sysml"

ALL_FILES = LIB_FILES + [CONSUMER_FILE]

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
print("Consumer Test: Robot model using ros2-sysmlv2 library")
print(f"Library files: {len(LIB_FILES)}")
print(f"Consumer file: {CONSUMER_FILE}")
print("=" * 60)

# ── Parse ─────────────────────────────────────────────────────────────

model, diagnostics = syside.load_model(ALL_FILES)
has_errors = diagnostics.contains_errors()
check("All files parse without errors (library + consumer)", not has_errors)

if has_errors:
    print("\nCritical: parse errors. Consumer model cannot use the library.")
    sys.exit(1)

# ── Consumer definitions exist ────────────────────────────────────────

part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}

check("MyLidarDriver exists", "MyLidarDriver" in part_defs)
check("MyController exists", "MyController" in part_defs)
check("TestRobot exists", "TestRobot" in part_defs)

# ── Consumer specialization chains ────────────────────────────────────

if "MyLidarDriver" in part_defs and "SensorDriver" in part_defs:
    check("MyLidarDriver :> SensorDriver",
          part_defs["MyLidarDriver"].specializes(part_defs["SensorDriver"]))
    check("MyLidarDriver :> LifecycleNode (transitive)",
          part_defs["MyLidarDriver"].specializes(part_defs["LifecycleNode"]))
    check("MyLidarDriver :> Node (transitive)",
          part_defs["MyLidarDriver"].specializes(part_defs["Node"]))

if "MyController" in part_defs and "Controller" in part_defs:
    check("MyController :> Controller",
          part_defs["MyController"].specializes(part_defs["Controller"]))

# ── TestRobot composition ─────────────────────────────────────────────

if "TestRobot" in part_defs:
    robot = part_defs["TestRobot"]
    parts = []
    conns = []
    for elem in robot.owned_elements.collect():
        if pu := elem.try_cast(syside.PartUsage):
            parts.append(pu.name)
        elif cu := elem.try_cast(syside.ConnectionUsage):
            conns.append(cu.name)

    check("TestRobot has lidar part", "lidar" in parts)
    check("TestRobot has nav part (Nav2Stack)", "nav" in parts)
    check("TestRobot has controller part", "controller" in parts)
    check("TestRobot has frames part (StandardFrameTree)", "frames" in parts)
    check("TestRobot has lidarFrame part", "lidarFrame" in parts)
    check("TestRobot has lidarMount connection (StaticTransform)", "lidarMount" in conns)
    check("TestRobot has lidarToLocalCostmap connection", "lidarToLocalCostmap" in conns)

# ── Summary ───────────────────────────────────────────────────────────

print(f"\n{'=' * 60}")
print(f"Consumer Test: {passed}/{passed + failed} passed, {failed} failed")
print(f"{'=' * 60}")

if failed > 0:
    print("\nConsumer test FAILED")
    sys.exit(1)
else:
    print("\nConsumer test PASSED — library is usable by downstream models")
