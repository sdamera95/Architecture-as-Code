#!/usr/bin/env python3
"""Regenerate the committed demo packages in ros2-py-outputs/ (and ros2-cpp-outputs/).

Each demo maps one validated showcase model to one generated, fully-wired ROS2
package, committed so a ROS2 Jazzy box can pull and colcon-build directly.
The extracted architecture.json is copied alongside each package for inspection.

Run from the repo root:
    uv run python bridge/regen_demos.py
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extract_architecture import extract_architecture
from generate_ros2 import generate_package

REPO = Path(__file__).resolve().parents[1]
LIBRARY_DIR = str(REPO / "projects" / "ros2-sysmlv2" / "ros2_sysmlv2")

DEMOS = {
    "agr": ("demos/agr/showcase_agr_full.sysml", "AutonomousGroundRobot"),
    "agr-nav2": ("demos/agr-nav2/showcase_agr_nav2_full.sysml", "GroundRobotWithNav2"),
}

LANGS = ["py", "cpp"]


def model_commit_epoch(model: Path) -> str | None:
    """Last git-commit time of the model file, for SOURCE_DATE_EPOCH pinning."""
    r = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", str(model)],
        capture_output=True, text=True, cwd=REPO,
    )
    return r.stdout.strip() or None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true",
                        help="Wipe output packages first, discarding hand-written "
                             "node implementations (generation-gap files)")
    args = parser.parse_args()

    scratch = REPO / "generated"
    scratch.mkdir(exist_ok=True)
    for name, (model, system) in DEMOS.items():
        epoch = model_commit_epoch(REPO / model)
        if epoch:
            os.environ["SOURCE_DATE_EPOCH"] = epoch
        json_path = scratch / f"{name}_architecture.json"
        arch = extract_architecture([str(REPO / model)], system, LIBRARY_DIR, str(json_path))
        for lang in LANGS:
            out = REPO / f"ros2-{lang}-outputs" / name
            generate_package(arch, str(out), wired=True, lang=lang, force=args.force)
            shutil.copy(json_path, out / "architecture.json")
            print(f"{name} [{lang}] -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
