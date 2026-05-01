#!/usr/bin/env python3
"""Single-command demo: .sysml → ROS2 package with conformance monitor.

Usage:
    .venv/bin/python bridge/run_demo.py \\
        tests/consumer_test_robot.sysml \\
        --system TestRobot

This runs:
  1. extract_architecture.py → architecture.json
  2. generate_ros2.py → ROS2 ament_python package
  3. Reports what was generated
"""
import argparse
import sys
from pathlib import Path

from extract_architecture import extract_architecture
from generate_ros2 import generate_package


def main():
    parser = argparse.ArgumentParser(
        description="SysML v2 → ROS2 bridge demo pipeline.")
    parser.add_argument("model_files", nargs="+",
                        help="Path(s) to user .sysml file(s)")
    parser.add_argument("--system", required=True,
                        help="Name of the system PartDefinition")
    parser.add_argument("--library-dir",
                        default="projects/ros2-sysmlv2/ros2_sysmlv2/",
                        help="Path to the ros2-sysmlv2 library directory")
    parser.add_argument("--output-dir", default="generated",
                        help="Base output directory")
    parser.add_argument("--wired", action="store_true",
                        help="Fully-wired mode: seed all endpoints with default data for topology verification")

    args = parser.parse_args()

    json_path = Path(args.output_dir) / "architecture.json"
    suffix = "_wired" if args.wired else "_clean"
    pkg_path = Path(args.output_dir) / f"{args.system.lower()}{suffix}"

    print("=" * 60)
    print("  ros2-sysmlv2 Bridge Pipeline Demo")
    print("=" * 60)

    # Stage 1: Extract
    print("\n── Stage 1: Architecture Extraction ──")
    arch = extract_architecture(
        args.model_files, args.system, args.library_dir, str(json_path))

    # Stage 2: Generate
    print(f"\n── Stage 2: ROS2 Package Generation{' (fully-wired)' if args.wired else ''} ──")
    output = generate_package(arch, str(pkg_path), smoke=args.wired)

    # Summary
    print("\n" + "=" * 60)
    print("  Pipeline Complete")
    print("=" * 60)
    print(f"\n  Input:  {args.model_files}")
    print(f"  System: {args.system}")
    print(f"  JSON:   {json_path}")
    print(f"  Package: {pkg_path}/")
    print(f"\n  To build with ROS2:")
    print(f"    cd {pkg_path} && colcon build")
    print(f"    ros2 launch {pkg_path.name} {pkg_path.name}.launch.py")


if __name__ == "__main__":
    main()
