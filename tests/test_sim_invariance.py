"""Extraction invariance: the Isaac Sim deployment model is invisible to the bridge.

The sim configuration (demos/agr-nav2/showcase_agr_nav2_sim.sysml) models the
simulator and workstation as plain SysML parts, deliberately not typed against
the ros2-sysmlv2 library. The library-harness projection must therefore produce
an identical architecture whether or not the sim file is loaded.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))

from extract_architecture import extract_architecture  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
LIB = str(REPO / "projects/ros2-sysmlv2/ros2_sysmlv2")
FULL = str(REPO / "demos/agr-nav2/showcase_agr_nav2_full.sysml")
SIM = str(REPO / "demos/agr-nav2/showcase_agr_nav2_sim.sysml")

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


def strip_metadata(arch):
    return {k: v for k, v in arch.items() if k != "metadata"}


with tempfile.TemporaryDirectory() as td:
    extract_architecture([FULL], "GroundRobotWithNav2", LIB, f"{td}/base.json")
    extract_architecture([FULL, SIM], "GroundRobotWithNav2", LIB, f"{td}/sim.json")
    # Compare the serialized files (the canonical pipeline artifact), not the
    # in-memory dicts, which may carry live syside objects.
    base = json.loads(Path(f"{td}/base.json").read_text())
    with_sim = json.loads(Path(f"{td}/sim.json").read_text())

check("node count unchanged", len(base["nodes"]) == len(with_sim["nodes"]),
      f"{len(base['nodes'])} vs {len(with_sim['nodes'])}")
check("connection count unchanged",
      len(base["connections"]) == len(with_sim["connections"]))
check("tf frames unchanged", base["tf_frames"] == with_sim["tf_frames"])
check("full projection identical (metadata aside)",
      json.dumps(strip_metadata(base), sort_keys=True)
      == json.dumps(strip_metadata(with_sim), sort_keys=True))
check("no simulator leaked into nodes",
      not any("isaac" in (n.get("type_name", "") + n.get("name", "")).lower()
              or "workstation" in (n.get("type_name", "") + n.get("name", "")).lower()
              for n in with_sim["nodes"]))

print()
print("=" * 60)
print(f"  {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
