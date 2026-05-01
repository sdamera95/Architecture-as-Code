"""Render the AGR_nav2 Equinox PyTree using treescope for authentic JAX-community visualization.

Produces docs/sysml_pytree_treescope.html — a standalone HTML page containing
treescope's native interactive pytree rendering of the GroundRobotWithNav2 module
hierarchy that mirrors showcase_agr_nav2_full.sysml.

This is Option A in the SysML->PyTree visualization comparison: authentic rendering
from the actual JAX tooling rather than a hand-drawn schematic.
"""
from __future__ import annotations

from pathlib import Path

import equinox as eqx
import jax
import jax.numpy as jnp
import treescope


# ══════════════════════════════════════════════════════════════════════════
# Leaf element types (mirror showcase_agr_nav2_full.sysml part defs)
# ══════════════════════════════════════════════════════════════════════════

class LidarUnit(eqx.Module):
    """3D LiDAR hardware (e.g., Ouster OS1-64)."""
    range_m: float = 30.0
    scan_rate_hz: float = 10.0
    mass_kg: float = 0.84
    power_w: float = 8.5
    frame_id: str = eqx.field(default="lidar_link", static=True)


class Nav2LidarDriver(eqx.Module):
    """Nav2-compatible lidar driver node (inherits SensorDriver)."""
    update_rate_hz: float = 10.0
    topic_name: str = eqx.field(default="/scan", static=True)
    qos_preset: str = eqx.field(default="SENSOR_DATA", static=True)


class DepthCameraUnit(eqx.Module):
    fov_deg: float = 87.0
    max_range_m: float = 6.0
    mass_kg: float = 0.72
    power_w: float = 3.5
    frame_id: str = eqx.field(default="depth_camera_link", static=True)


class DepthCameraDriver(eqx.Module):
    update_rate_hz: float = 30.0
    topic_name: str = eqx.field(default="/depth/points", static=True)


class ImuUnit(eqx.Module):
    sample_rate_hz: float = 200.0
    mass_kg: float = 0.05
    power_w: float = 0.5
    frame_id: str = eqx.field(default="imu_link", static=True)


class Nav2ImuDriver(eqx.Module):
    update_rate_hz: float = 100.0
    topic_name: str = eqx.field(default="/imu/data", static=True)


class Chassis(eqx.Module):
    mass_kg: float = 5.0
    length_m: float = 0.8
    width_m: float = 0.5
    material: str = eqx.field(default="steel_tube", static=True)


class Wheel(eqx.Module):
    diameter_m: float = 0.2
    mass_kg: float = 0.5


class Drivetrain(eqx.Module):
    front_left: Wheel = Wheel()
    front_right: Wheel = Wheel()
    rear_left: Wheel = Wheel()
    rear_right: Wheel = Wheel()


class WeatherproofEnclosure(eqx.Module):
    mass_kg: float = 1.2
    ip_rating: str = eqx.field(default="IP67", static=True)


class Battery(eqx.Module):
    voltage_v: float = 22.2
    capacity_ah: float = 16.0
    mass_kg: float = 2.8
    chemistry: str = eqx.field(default="LiPo_6S", static=True)


class OnboardComputer(eqx.Module):
    mass_kg: float = 0.6
    power_w: float = 40.0
    platform: str = eqx.field(default="Jetson_Orin_AGX", static=True)


class PointCloudFilter(eqx.Module):
    voxel_size_m: float = 0.05
    max_z_m: float = 2.0
    topic_in: str = eqx.field(default="/depth/points", static=True)
    topic_out: str = eqx.field(default="/depth/filtered", static=True)


class Nav2EKFLocalizer(eqx.Module):
    process_noise_q: float = 0.01
    measurement_noise_r: float = 0.05
    publish_rate_hz: float = 50.0
    odom_topic: str = eqx.field(default="/odometry/filtered", static=True)


# Nav2Stack: simplified as a single composite placeholder
class Nav2PlannerServer(eqx.Module):
    expected_planner_frequency: float = 1.0
    planner_plugin: str = eqx.field(default="NavfnPlanner", static=True)


class Nav2ControllerServer(eqx.Module):
    controller_frequency_hz: float = 20.0
    max_vel_x: float = 1.5
    controller_plugin: str = eqx.field(default="RegulatedPurePursuit", static=True)


class Nav2LifecycleManager(eqx.Module):
    bond_timeout_s: float = 4.0
    autostart: bool = eqx.field(default=True, static=True)
    managed_nodes: str = eqx.field(default="planner,controller,bt_navigator", static=True)


class Nav2Stack(eqx.Module):
    planner: Nav2PlannerServer = Nav2PlannerServer()
    controller: Nav2ControllerServer = Nav2ControllerServer()
    lifecycle_manager: Nav2LifecycleManager = Nav2LifecycleManager()
    # (13 more servers elided for figure legibility)


# ══════════════════════════════════════════════════════════════════════════
# Subsystem types (mirror Section 6b of showcase_agr_nav2_full.sysml)
# ══════════════════════════════════════════════════════════════════════════

class LidarSubsystem(eqx.Module):
    hardware: LidarUnit = LidarUnit()
    driver: Nav2LidarDriver = Nav2LidarDriver()


class DepthCameraSubsystem(eqx.Module):
    hardware: DepthCameraUnit = DepthCameraUnit()
    driver: DepthCameraDriver = DepthCameraDriver()


class ImuSubsystem(eqx.Module):
    hardware: ImuUnit = ImuUnit()
    driver: Nav2ImuDriver = Nav2ImuDriver()


class SensorSuite(eqx.Module):
    lidar: LidarSubsystem = LidarSubsystem()
    depth_camera: DepthCameraSubsystem = DepthCameraSubsystem()
    imu: ImuSubsystem = ImuSubsystem()
    total_mass_kg: float = 2.4          # rollup (illustrative)
    total_power_w: float = 15.0


class MechanicalStructure(eqx.Module):
    chassis: Chassis = Chassis()
    drivetrain: Drivetrain = Drivetrain()
    enclosure: WeatherproofEnclosure = WeatherproofEnclosure()
    total_mass_kg: float = 8.2


class PowerSystem(eqx.Module):
    battery: Battery = Battery()
    total_capacity_ah: float = 16.0
    nominal_voltage_v: float = 22.2


class ComputeSystem(eqx.Module):
    computer: OnboardComputer = OnboardComputer()


class PerceptionSubsystem(eqx.Module):
    pointcloud_filter: PointCloudFilter = PointCloudFilter()


class LocalizationSubsystem(eqx.Module):
    ekf_localizer: Nav2EKFLocalizer = Nav2EKFLocalizer()


class Nav2AutonomyStack(eqx.Module):
    perception: PerceptionSubsystem = PerceptionSubsystem()
    localization: LocalizationSubsystem = LocalizationSubsystem()
    nav2: Nav2Stack = Nav2Stack()


class CoordinateFrame(eqx.Module):
    frame_id: str = eqx.field(default="base_link", static=True)


class FrameSubsystem(eqx.Module):
    lidar_frame: CoordinateFrame = CoordinateFrame(frame_id="lidar_link")
    depth_camera_frame: CoordinateFrame = CoordinateFrame(frame_id="depth_camera_link")
    imu_frame: CoordinateFrame = CoordinateFrame(frame_id="imu_link")


# ══════════════════════════════════════════════════════════════════════════
# System root (mirrors part def GroundRobotWithNav2)
# ══════════════════════════════════════════════════════════════════════════

class GroundRobotWithNav2(eqx.Module):
    """Top-level system — mirrors part def GroundRobotWithNav2."""
    structure: MechanicalStructure = MechanicalStructure()
    power: PowerSystem = PowerSystem()
    sensors: SensorSuite = SensorSuite()
    compute: ComputeSystem = ComputeSystem()
    autonomy_stack: Nav2AutonomyStack = Nav2AutonomyStack()
    tf_tree: FrameSubsystem = FrameSubsystem()

    total_mass_kg: float = 18.0
    max_speed_ms: float = 1.5
    endurance_hours: float = 7.0
    payload_capacity_kg: float = 15.0


# ══════════════════════════════════════════════════════════════════════════
# Render and save
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    robot = GroundRobotWithNav2()

    # Also build a gradient pytree (same shape, values are ∂endurance/∂x)
    # to include alongside — demonstrates "gradient tree = architecture shape"
    def endurance(r: GroundRobotWithNav2) -> jax.Array:
        # Simplified objective: maximize endurance_hours while penalizing mass
        return r.endurance_hours - 0.05 * r.total_mass_kg

    grads = jax.grad(endurance)(robot)

    # Render to standalone HTML
    param_html = treescope.render_to_html(
        robot,
        roundtrip_mode=False,
    )
    grad_html = treescope.render_to_html(
        grads,
        roundtrip_mode=False,
    )

    # Compose a single page showing both
    out_path = Path(__file__).parent.parent / "docs" / "sysml_pytree_treescope.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_wrap_page(param_html, grad_html))
    print(f"Wrote {out_path}")


def _wrap_page(param_html: str, grad_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SysML -> PyTree (Treescope authentic rendering)</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f8fafc;
    color: #1e293b;
    max-width: 1500px;
    margin: 40px auto;
    padding: 0 24px;
    line-height: 1.6;
  }}
  h1 {{ font-weight: 600; font-size: 22px; margin-bottom: 4px; }}
  h2 {{ font-weight: 500; font-size: 17px; color: #475569; margin-top: 36px; }}
  p.caption {{ color: #64748b; font-size: 13px; max-width: 900px; }}
  .figure {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 20px 24px;
    margin: 16px 0 32px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    overflow-x: auto;
  }}
  .figure-title {{
    font-weight: 600;
    font-size: 14px;
    color: #334155;
    margin-bottom: 10px;
  }}
</style>
</head>
<body>

<h1>SysML v2 -> PyTree (Option A: Treescope authentic rendering)</h1>
<p class="caption">
  Produced by <code>treescope.render_to_html(robot)</code> on the GroundRobotWithNav2
  Equinox module instance defined in <code>tests/render_pytree_treescope.py</code>.
  The module hierarchy mirrors the part-def hierarchy of
  <code>syside-demos/showcase_agr_nav2_full.sysml</code>.
  This is what a researcher reproducing the work sees in a Jupyter notebook -
  interactive, collapsible, with type badges and values surfaced directly from JAX.
</p>

<h2>1. Parameter pytree (the GroundRobotWithNav2 instance)</h2>
<div class="figure">
  <div class="figure-title">robot = GroundRobotWithNav2()</div>
  {param_html}
</div>

<h2>2. Gradient pytree (same shape, values are &part;endurance / &part;parameter)</h2>
<div class="figure">
  <div class="figure-title">grads = jax.grad(lambda r: r.endurance_hours - 0.05 * r.total_mass_kg)(robot)</div>
  {grad_html}
</div>

<p class="caption">
  The two trees have <em>identical structure</em>. Every module and leaf in the parameter
  tree has a corresponding entry in the gradient tree. Static fields
  (<code>eqx.field(static=True)</code>) appear in the parameter tree but are absent from
  the gradient tree because JAX does not differentiate through them - this is visible
  directly in treescope's output.
</p>

</body>
</html>
"""


if __name__ == "__main__":
    main()
