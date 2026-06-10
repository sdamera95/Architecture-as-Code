"""Cardinality (array-multiplicity) conformance test for the ros2-sysmlv2 message library.

Guards the 2026-06-03 decision (docs/knowledge_docs/covariance_modeling_decision.md):
ROS2 fixed-size matrix message fields are modeled with IDL-faithful array cardinality
(`Real[36]`/`Real[9]`/`Real[12]`), NOT scalar `Real`. The Syside validator accepts scalar
`Real` as valid SysML, so this gap is invisible to `syside check`; this test is the gate
that enforces it, by asserting each SysML field's multiplicity equals the .msg array size.

Two halves:
  1. END-TO-END (positive): load the real library and run the conformance checker over the
     covariance/intrinsic-bearing message types; every field must PASS (incl. cardinality).
  2. UNIT (the enforcement proof): drive check_cardinality directly — confirm it CATCHES
     scalar-vs-[N], wrong-N, scalar-vs-array, and correctly DELEGATES the wrapper case.

Run with: uv run python tests/test_msg_cardinality.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from msg_conformance_checker import (  # noqa: E402
    MsgField,
    parse_msg_file,
    extract_sysml_items,
    check_msg_against_sysml,
    check_cardinality,
)

ROOT = Path(__file__).resolve().parents[1]
LIB_FILES = sorted(str(f) for f in (ROOT / "projects/ros2-sysmlv2/ros2_sysmlv2").glob("*.sysml"))
REF = ROOT / "references/common_interfaces"

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
# 1. end-to-end: covariance/intrinsic-bearing types pass WITH cardinality
# ------------------------------------------------------------------
# (package, message, .msg subpath) — every one carries a fixed/variable array field.
TARGETS = [
    ("sensor_msgs", "Imu"),            # 3x float64[9] covariances
    ("sensor_msgs", "CameraInfo"),     # k/r float64[9], p float64[12], d float64[]
    ("sensor_msgs", "NavSatFix"),      # float64[9] position_covariance
    ("sensor_msgs", "MagneticField"),  # float64[9]
    ("sensor_msgs", "LaserScan"),      # float32[] ranges (variable)
    ("geometry_msgs", "PoseWithCovariance"),   # float64[36] via CovarianceMatrix6x6 (wrapper)
    ("geometry_msgs", "TwistWithCovariance"),  # float64[36] via wrapper
    ("geometry_msgs", "PoseArray"),    # Pose[] (variable array of struct)
]


def run_end_to_end():
    section("END-TO-END: cardinality enforced on covariance-bearing message types")
    sysml_items = extract_sysml_items(LIB_FILES)
    for pkg, msg in TARGETS:
        msg_path = REF / pkg / "msg" / f"{msg}.msg"
        if not msg_path.exists():
            check(f"{pkg}/{msg} .msg present", False, f"missing {msg_path}")
            continue
        parsed = parse_msg_file(msg_path, pkg)
        result = check_msg_against_sysml(parsed, sysml_items)
        card_fails = [fc for fc in result.field_checks if fc.status == "CARDINALITY_MISMATCH"]
        any_fail = [fc for fc in result.field_checks if fc.status != "PASS"]
        check(f"{pkg}/{msg}: all fields PASS (incl. cardinality)", result.passed,
              detail="; ".join(f"{fc.field_name}[{fc.status}] {fc.note}" for fc in any_fail))
        check(f"{pkg}/{msg}: zero CARDINALITY_MISMATCH", not card_fails,
              detail="; ".join(fc.field_name for fc in card_fails))


# ------------------------------------------------------------------
# 2. unit: the enforcement logic (this is what proves the gate is not a no-op)
# ------------------------------------------------------------------
def _mf(ros2_type, is_array, array_size):
    return MsgField(name="f", ros2_type=ros2_type, is_array=is_array, array_size=array_size, sysml_type="Real")


def card_ok(ros2_type, is_array, array_size, expected_type, actual_type, sysml_mult):
    return check_cardinality(_mf(ros2_type, is_array, array_size), expected_type, actual_type, sysml_mult)[0]


def run_unit_cardinality():
    section("UNIT: check_cardinality accepts correct, catches wrong, delegates wrappers")
    # fixed array: correct cardinality accepted
    check("float64[9] vs SysML [9] -> ok", card_ok("float64", True, 9, "Real", "Real", "[9]") is True)
    check("float64[36] vs SysML [36] -> ok", card_ok("float64", True, 36, "Real", "Real", "[36]") is True)
    # fixed array: the guarded regression — scalar Real must be CAUGHT
    check("float64[9] vs SysML scalar -> CAUGHT", card_ok("float64", True, 9, "Real", "Real", "scalar") is False)
    # fixed array: wrong size caught
    check("float64[9] vs SysML [8] -> CAUGHT", card_ok("float64", True, 9, "Real", "Real", "[8]") is False)
    # variable array
    check("float64[] vs SysML [0..*] -> ok", card_ok("float64", True, None, "Real", "Real", "[0..*]") is True)
    check("float64[] vs SysML scalar -> CAUGHT", card_ok("float64", True, None, "Real", "Real", "scalar") is False)
    check("float64[] vs SysML bounded [0..3] -> ok (stricter)", card_ok("float64", True, None, "Real", "Real", "[0..3]") is True)
    # scalar
    check("float64 scalar vs SysML scalar -> ok", card_ok("float64", False, None, "Real", "Real", "scalar") is True)
    check("float64 scalar vs SysML [9] -> CAUGHT", card_ok("float64", False, None, "Real", "Real", "[9]") is False)
    # wrapper delegation: ROS2 primitive array mapped to a named wrapper -> cardinality lives inside it
    check("float64[36] vs SysML CovarianceMatrix6x6 (scalar field) -> delegated/ok",
          card_ok("float64", True, 36, "Real", "CovarianceMatrix6x6", "scalar") is True)
    # struct array: cardinality still enforced (Pose[] must be variable, not scalar)
    check("Pose[] vs SysML Pose scalar -> CAUGHT", card_ok("geometry_msgs/Pose", True, None, "Pose", "Pose", "scalar") is False)


if __name__ == "__main__":
    run_unit_cardinality()  # fast, no model load
    run_end_to_end()        # loads the library once
    print(f"\n{'=' * 60}\n  {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
