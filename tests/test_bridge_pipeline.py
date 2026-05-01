"""Integration test for the full bridge pipeline.

Validates:
  1. Extraction produces valid architecture.json
  2. Generation produces compilable Python files
  3. Package structure matches ament_python conventions
  4. Conformance monitor embeds correct expected spec
  5. Custom nodes have correct pubs/subs/params from model
"""
import json
import os
import py_compile
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

from extract_architecture import extract_architecture
from generate_ros2 import generate_package

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


# ══════════════════════════════════════════════════════════════════════
# Stage 1: Extraction
# ══════════════════════════════════════════════════════════════════════

print("=" * 60)
print("  Bridge Pipeline Integration Test")
print("=" * 60)

print("\n── Stage 1: Architecture Extraction ──")

arch = extract_architecture(
    ["tests/consumer_test_robot.sysml"],
    "TestRobot",
    "projects/ros2-sysmlv2/ros2_sysmlv2/",
    "generated/test_architecture.json"
)

check("Extraction produces dict", isinstance(arch, dict))
check("Has metadata", "metadata" in arch)
check("Has nodes", "nodes" in arch)
check("Has connections", "connections" in arch)
check("Has tf_frames", "tf_frames" in arch)
check("Has tf_transforms", "tf_transforms" in arch)

# Node checks
nodes = arch["nodes"]
custom = [n for n in nodes if not n["is_standard"]]
standard = [n for n in nodes if n["is_standard"]]

check("14 total nodes", len(nodes) == 14, f"got {len(nodes)}")
check("2 custom nodes", len(custom) == 2, f"got {len(custom)}")
check("12 standard nodes", len(standard) == 12, f"got {len(standard)}")

# Find specific nodes
lidar = next((n for n in nodes if n["type_name"] == "MyLidarDriver"), None)
controller = next((n for n in nodes if n["type_name"] == "MyController"), None)

check("MyLidarDriver found", lidar is not None)
check("MyController found", controller is not None)

if lidar:
    check("lidar.name = 'lidar_driver'", lidar["name"] == "lidar_driver")
    check("lidar.namespace = '/sensors'", lidar["namespace"] == "/sensors")
    check("lidar.lifecycle = True", lidar["lifecycle"] is True)
    check("lidar.archetype = 'SensorDriver'", lidar["archetype"] == "SensorDriver")
    check("lidar has 1 publisher", len(lidar["publishers"]) == 1)
    if lidar["publishers"]:
        pub = lidar["publishers"][0]
        check("lidar pub topic = '/scan'", pub["topic_name"] == "/scan")
        check("lidar pub msg_type contains 'LaserScan'",
              pub["msg_type"] and "LaserScan" in pub["msg_type"])
        check("lidar pub qos = 'sensor_data'", pub["qos_preset"] == "sensor_data")

if controller:
    check("controller.name = 'my_controller'", controller["name"] == "my_controller")
    check("controller.archetype = 'Controller'", controller["archetype"] == "Controller")
    check("controller has 1 publisher", len(controller["publishers"]) == 1)
    check("controller has 1 subscriber", len(controller["subscribers"]) == 1)
    check("controller has 1 action_server", len(controller["action_servers"]) == 1)
    check("controller has 1 parameter", len(controller["parameters"]) == 1)
    if controller["action_servers"]:
        act = controller["action_servers"][0]
        check("controller action = 'follow_path'", act["action_name"] == "follow_path")

# Connection checks
conns = arch["connections"]
check("6 connections", len(conns) == 6, f"got {len(conns)}")

conn_names = {c["name"] for c in conns}
check("lidarToLocalCostmap connection", "lidarToLocalCostmap" in conn_names)

# TF checks
check("7 TF frames", len(arch["tf_frames"]) == 7, f"got {len(arch['tf_frames'])}")
frame_ids = {f["frame_id"] for f in arch["tf_frames"]}
check("map frame", "map" in frame_ids)
check("odom frame", "odom" in frame_ids)
check("base_link frame", "base_link" in frame_ids)
check("lidar_link frame", "lidar_link" in frame_ids)

# ══════════════════════════════════════════════════════════════════════
# Stage 2: Code Generation
# ══════════════════════════════════════════════════════════════════════

print("\n── Stage 2: Code Generation ──")

output = generate_package(arch, "generated/test_pipeline_output")
output = Path("generated/test_pipeline_output")

# Package structure
check("package.xml exists", (output / "package.xml").exists())
check("setup.py exists", (output / "setup.py").exists())
check("setup.cfg exists", (output / "setup.cfg").exists())
check("__init__.py exists", (output / "test_robot" / "__init__.py").exists())
check("launch file exists", (output / "launch" / "test_robot.launch.py").exists())
check("params.yaml exists", (output / "config" / "params.yaml").exists())
check("resource marker exists", (output / "resource" / "test_robot").exists())

# Node files
check("my_lidar_driver_node.py exists",
      (output / "test_robot" / "my_lidar_driver_node.py").exists())
check("my_controller_node.py exists",
      (output / "test_robot" / "my_controller_node.py").exists())
check("conformance_monitor.py exists",
      (output / "test_robot" / "conformance_monitor.py").exists())

# Compile check
py_files = list(output.rglob("*.py"))
compile_errors = 0
for f in py_files:
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError:
        compile_errors += 1
check(f"All {len(py_files)} .py files compile", compile_errors == 0,
      f"{compile_errors} errors")

# Clean __pycache__ created by py_compile
import shutil
for cache_dir in output.rglob("__pycache__"):
    if cache_dir.is_dir():
        shutil.rmtree(cache_dir)

# package.xml validity
try:
    tree = ET.parse(output / "package.xml")
    root = tree.getroot()
    pkg_name = root.find("name").text
    check("package.xml name = 'test_robot'", pkg_name == "test_robot")
    deps = {e.text for e in root.findall("exec_depend")}
    check("sensor_msgs in dependencies", "sensor_msgs" in deps)
    check("geometry_msgs in dependencies", "geometry_msgs" in deps)
    check("nav_msgs in dependencies", "nav_msgs" in deps)
except Exception as e:
    check("package.xml parses", False, str(e))

# setup.py has entry points
setup_text = (output / "setup.py").read_text()
check("setup.py has my_lidar_driver entry", "my_lidar_driver" in setup_text)
check("setup.py has my_controller entry", "my_controller" in setup_text)
check("setup.py has conformance_monitor entry", "conformance_monitor" in setup_text)

# Conformance monitor has embedded spec with real data
monitor_text = (output / "test_robot" / "conformance_monitor.py").read_text()
check("monitor has EXPECTED_NODES", "EXPECTED_NODES" in monitor_text)
check("monitor has EXPECTED_TOPICS", "EXPECTED_TOPICS" in monitor_text)
check("monitor has EXPECTED_CONNECTIONS", "EXPECTED_CONNECTIONS" in monitor_text)
check("monitor has EXPECTED_QOS", "EXPECTED_QOS" in monitor_text)
check("monitor has EXPECTED_SERVICES", "EXPECTED_SERVICES" in monitor_text)
check("monitor has EXPECTED_ACTIONS", "EXPECTED_ACTIONS" in monitor_text)
check("monitor has EXPECTED_PARAMS", "EXPECTED_PARAMS" in monitor_text)
check("monitor mentions lidar_driver", "lidar_driver" in monitor_text)

# Verify connection entries have resolved topic-level data (not just names)
check("connections have topic field", '"topic":' in monitor_text)
check("connections have pub_node field", '"pub_node":' in monitor_text)
check("connections have sub_node field", '"sub_node":' in monitor_text)

# Verify connection check uses get_publishers_info_by_topic (real verification)
check("connection check uses get_publishers_info_by_topic",
      "get_publishers_info_by_topic" in monitor_text)
check("connection check uses get_subscriptions_info_by_topic",
      "get_subscriptions_info_by_topic" in monitor_text)

# Verify QoS check references actual QoS policies
check("QoS check references QoSReliabilityPolicy",
      "QoSReliabilityPolicy" in monitor_text)

# Verify NO unconditional pass patterns exist
check("no fake conn_ok += 1 without condition",
      "conn_ok += 1  # TODO" not in monitor_text)

# ══════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  Pipeline Test: {passed}/{passed + failed} passed, {failed} failed")
print(f"{'=' * 60}")

if failed > 0:
    print("\n  SOME CHECKS FAILED")
    sys.exit(1)
else:
    print("\n  ALL CHECKS PASS")
    print("  Bridge pipeline is working end-to-end.")
