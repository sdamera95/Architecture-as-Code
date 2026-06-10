"""Offline tests for the C++ backend + generation-gap pattern (no ROS2 needed).

Covers: helper-function correctness (rosidl naming, type/include/QoS/param
mapping), template parseability, generation smoke for {py,cpp} x {wired,clean}
over both committed IRs, gen-gap semantics (derived files survive regeneration,
force resets), C++ static sanity (brace balance, CMake cross-checks), and
byte-identity of the shared language-neutral artifacts.

colcon build verification is deferred to the Ubuntu ROS2 Jazzy box (RUNBOOK).
"""
import json
import py_compile
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from generate_ros2 import (  # noqa: E402
    QOS_PRESETS_RCLCPP,
    generate_package,
    msg_type_to_cpp,
    param_default_cpp,
    rosidl_snake_case,
    to_snake_case,
)

REPO = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO / "bridge" / "templates"
IRS = {
    "agr": REPO / "ros2-py-outputs" / "agr" / "architecture.json",
    "agr-nav2": REPO / "ros2-py-outputs" / "agr-nav2" / "architecture.json",
}

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


def section(title):
    print(f"\n{'-' * 60}\n{title}")


# ------------------------------------------------------------------
# 1. helper functions
# ------------------------------------------------------------------
section("1. C++ mapping helpers")

check("rosidl: LaserScan", rosidl_snake_case("LaserScan") == "laser_scan")
check("rosidl: PointCloud2 (digit attaches)", rosidl_snake_case("PointCloud2") == "point_cloud2")
check("rosidl: TFMessage (acronym boundary)", rosidl_snake_case("TFMessage") == "tf_message")
check("rosidl: UInt8MultiArray", rosidl_snake_case("UInt8MultiArray") == "u_int8_multi_array")
check("to_snake_case unchanged (executable parity)", to_snake_case("EKFLocalizer") == "e_k_f_localizer")

m = msg_type_to_cpp("sensor_msgs.msg.LaserScan")
check("cpp type", m["cpp_type"] == "sensor_msgs::msg::LaserScan")
check("cpp include", m["include"] == "sensor_msgs/msg/laser_scan.hpp")
a = msg_type_to_cpp("nav2_msgs.action.FollowPath.Goal")
check("action sub-type", a["cpp_type"] == "nav2_msgs::action::FollowPath::Goal"
      and a["include"] == "nav2_msgs/action/follow_path.hpp")

check("param default Double", param_default_cpp("DoubleParameter", None) == "0.0")
check("param default String", param_default_cpp("StringParameter", None) == 'std::string("")')
check("param literal bool", param_default_cpp("BoolParameter", True) == "true")
check("param literal float gets dot", param_default_cpp("DoubleParameter", 5) == "5")
check("qos preset table covers sensor_data",
      QOS_PRESETS_RCLCPP["sensor_data"] == "rclcpp::SensorDataQoS()")

# ------------------------------------------------------------------
# 2. every template parses
# ------------------------------------------------------------------
section("2. Template syntax")

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
for tpl in sorted(TEMPLATE_DIR.glob("*.j2")):
    try:
        env.parse(tpl.read_text())
        check(f"parse {tpl.name}", True)
    except Exception as e:  # noqa: BLE001
        check(f"parse {tpl.name}", False, str(e))

# ------------------------------------------------------------------
# 3. generation smoke over {py,cpp} x {wired,clean} x both IRs
# ------------------------------------------------------------------
section("3. Generation smoke + inventories")

workdir = Path(tempfile.mkdtemp(prefix="cppgen_"))
outputs = {}
for ir_name, ir_path in IRS.items():
    arch = json.loads(ir_path.read_text())
    n_nodes = len([n for n in arch["nodes"] if not n.get("is_standard", False)])
    for lang in ("py", "cpp"):
        for wired in (True, False):
            out = workdir / f"{ir_name}_{lang}_{'wired' if wired else 'clean'}"
            generate_package(arch, str(out), wired=wired, lang=lang, force=True)
            outputs[(ir_name, lang, wired)] = out
            pkg_name = to_snake_case(arch["metadata"]["model_name"])
            if lang == "py":
                bases = list((out / pkg_name).glob("*_node_base.py"))
                impls = [f for f in (out / pkg_name).glob("*_node.py")]
                check(f"{ir_name}/py/{'wired' if wired else 'clean'}: {n_nodes} base + {n_nodes} impl",
                      len(bases) == n_nodes and len(impls) == n_nodes,
                      f"got {len(bases)} base, {len(impls)} impl")
            else:
                hpps = list((out / "include" / pkg_name).glob("*_base.hpp"))
                base_cpps = list((out / "src").glob("*_base.cpp"))
                impl_cpps = [f for f in (out / "src").glob("*_node.cpp")]
                check(f"{ir_name}/cpp/{'wired' if wired else 'clean'}: {n_nodes} hpp/base/impl",
                      len(hpps) == n_nodes and len(base_cpps) == n_nodes and len(impl_cpps) == n_nodes,
                      f"got {len(hpps)}/{len(base_cpps)}/{len(impl_cpps)}")
                check(f"{ir_name}/cpp/{'wired' if wired else 'clean'}: build files + scripts",
                      (out / "CMakeLists.txt").exists() and (out / "package.xml").exists()
                      and (out / "scripts" / "conformance_monitor").exists()
                      and (out / "scripts" / "activate_nodes").exists())

# ------------------------------------------------------------------
# 4. generated Python compiles
# ------------------------------------------------------------------
section("4. py_compile sweep")

py_out = outputs[("agr", "py", True)]
compile_failures = []
for f in py_out.rglob("*.py"):
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e:
        compile_failures.append(f"{f.name}: {e}")
check("all generated .py compile", not compile_failures, "; ".join(compile_failures[:3]))

# ------------------------------------------------------------------
# 5. generation-gap semantics (both languages)
# ------------------------------------------------------------------
section("5. Generation gap")

arch = json.loads(IRS["agr"].read_text())
for lang, impl_glob, base_glob in (
    ("py", "autonomous_ground_robot/*_node.py", "autonomous_ground_robot/*_node_base.py"),
    ("cpp", "src/*_node.cpp", "src/*_base.cpp"),
):
    out = workdir / f"gengap_{lang}"
    generate_package(arch, str(out), wired=True, lang=lang, force=True)
    impl = sorted(out.glob(impl_glob))[0]
    sentinel = "// HAND-WRITTEN SENTINEL" if lang == "cpp" else "# HAND-WRITTEN SENTINEL"
    impl.write_text(impl.read_text() + f"\n{sentinel}\n")
    base = sorted(out.glob(base_glob))[0]
    base_before = base.read_text()
    base.write_text(base_before + "\n// STALE BASE EDIT\n" if lang == "cpp"
                    else base_before + "\n# STALE BASE EDIT\n")

    generate_package(arch, str(out), wired=True, lang=lang)  # no force
    check(f"{lang}: derived file survives regeneration", sentinel in impl.read_text())
    check(f"{lang}: base file rewritten", "STALE BASE EDIT" not in base.read_text())

    generate_package(arch, str(out), wired=True, lang=lang, force=True)
    check(f"{lang}: force resets derived file", sentinel not in impl.read_text())

# ------------------------------------------------------------------
# 6. C++ static sanity
# ------------------------------------------------------------------
section("6. C++ static sanity")

cpp_out = outputs[("agr", "cpp", True)]
unbalanced = []
for f in list(cpp_out.rglob("*.cpp")) + list(cpp_out.rglob("*.hpp")):
    text = f.read_text()
    if text.count("{") != text.count("}") or text.count("(") != text.count(")"):
        unbalanced.append(f.name)
check("brace/paren balance in all C++ files", not unbalanced, ", ".join(unbalanced[:3]))

cmake = (cpp_out / "CMakeLists.txt").read_text()
arch = json.loads(IRS["agr"].read_text())
n_nodes = len([n for n in arch["nodes"] if not n.get("is_standard", False)])
check("one add_executable per node", cmake.count("add_executable(") == n_nodes)
check("lifecycle dep in CMake", "rclcpp_lifecycle" in cmake)

includes = set()
for f in cpp_out.rglob("*.hpp"):
    for line in f.read_text().splitlines():
        if line.startswith("#include <") and "/msg/" in line:
            includes.add(line.split("<")[1].split("/")[0])
missing_fp = [pkg for pkg in includes if f"find_package({pkg} REQUIRED)" not in cmake]
check("every msg include has find_package", not missing_fp, ", ".join(missing_fp))

pkg_xml = ET.parse(cpp_out / "package.xml")
check("cpp build_type is ament_cmake",
      pkg_xml.findtext(".//export/build_type") == "ament_cmake")
py_pkg_xml = ET.parse(outputs[("agr", "py", True)] / "package.xml")
check("py build_type is ament_python",
      py_pkg_xml.findtext(".//export/build_type") == "ament_python")

# ------------------------------------------------------------------
# 7. shared artifacts byte-identical across languages
# ------------------------------------------------------------------
section("7. Shared language-neutral artifacts")

py_o = outputs[("agr", "py", True)]
cpp_o = outputs[("agr", "cpp", True)]
check("conformance monitor byte-identical",
      (py_o / "autonomous_ground_robot" / "conformance_monitor.py").read_text()
      == (cpp_o / "scripts" / "conformance_monitor").read_text())
check("activator byte-identical",
      (py_o / "autonomous_ground_robot" / "activate_nodes.py").read_text()
      == (cpp_o / "scripts" / "activate_nodes").read_text())
check("launch file byte-identical",
      (py_o / "launch" / "autonomous_ground_robot.launch.py").read_text()
      == (cpp_o / "launch" / "autonomous_ground_robot.launch.py").read_text())
check("params.yaml byte-identical",
      (py_o / "config" / "params.yaml").read_text()
      == (cpp_o / "config" / "params.yaml").read_text())
check("monitor script is executable", (cpp_o / "scripts" / "conformance_monitor").stat().st_mode & 0o111)

shutil.rmtree(workdir)

print()
print("=" * 60)
print(f"  {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
