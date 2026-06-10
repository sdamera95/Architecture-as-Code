#!/usr/bin/env python3
"""Run the full conformance suite against the ROS2 Jazzy reference sources.

Aggregates the six conformance checkers (message packages via
msg_conformance_checker, comm via comm_conformance_checker, and the
lifecycle / tf2+params / nav2 / phase-8 checkers via their validate_phase
drivers) and exits nonzero if any group fails.

Run from the repo root:
    uv run python tools/run_all_conformance.py
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIB = sorted(str(p) for p in (REPO / "projects/ros2-sysmlv2/ros2_sysmlv2").glob("*.sysml"))

MSG_PACKAGES = [
    "std_msgs", "geometry_msgs", "sensor_msgs", "nav_msgs",
    "diagnostic_msgs", "shape_msgs", "trajectory_msgs", "visualization_msgs",
]


def run(label, cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    ok = r.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(r.stdout[-2500:])
        print(r.stderr[-500:])
    return ok


def main():
    results = []
    for pkg in MSG_PACKAGES:
        msg_dir = REPO / "references" / "common_interfaces" / pkg / "msg"
        results.append(run(f"msg:{pkg}", [
            sys.executable, str(REPO / "tools/msg_conformance_checker.py"),
            "--msg-dir", str(msg_dir), "--sysml-files", *LIB,
        ]))
    results.append(run("comm", [
        sys.executable, str(REPO / "tools/comm_conformance_checker.py"),
        "--rclpy-dir", str(REPO / "references/rclpy/rclpy/rclpy"),
        "--rmw-dir", str(REPO / "references/rmw/rmw/include/rmw"),
        "--sysml-files", *LIB,
    ]))
    for label, script in [
        ("lifecycle+deployment", "validate_phase4.py"),
        ("tf2+params", "validate_phase5.py"),
        ("nav2", "validate_phase6_7.py"),
        ("remaining-msg-pkgs", "validate_phase8.py"),
    ]:
        results.append(run(label, [sys.executable, str(REPO / "tests" / script)]))

    print(f"\n{sum(results)}/{len(results)} conformance groups passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
