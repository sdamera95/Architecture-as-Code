#!/usr/bin/env python3
"""
Equinox + JAX autodiff demo: UAV architecture as a differentiable pytree.

Demonstrates the core insight from the Architecture-Driven Differentiable
Twins report: SysML v2 part hierarchy maps to Equinox module composition,
and jax.grad produces gradients with the same architecture as the system.

The UAV model here mirrors the structure of syside-demos/uav_trade_study.sysml:
  - Battery (capacity, specific_energy -> derived mass)
  - PropulsionSubsystem (num_motors, motor_mass -> derived mass, hover power)
  - AvionicsSubsystem (fcc, imu, gps, baro -> total power)
  - CameraPayload (mass, power)
  - Airframe (mass)
  - UAV (composes all above, computes endurance)

Run:
    .venv/bin/python tests/demo_equinox_autodiff.py
"""
import jax
import jax.numpy as jnp
import equinox as eqx

# ══════════════════════════════════════════════════════════════
# 1. ARCHITECTURE AS EQUINOX MODULES
#    Each part def in the SysML model becomes an eqx.Module.
#    Attributes become fields. Derived quantities become methods.
#    Composition (part usage) becomes a module-typed field.
# ══════════════════════════════════════════════════════════════


class Battery(eqx.Module):
    """Maps to: part def Battery in uav_trade_study.sysml"""
    capacity_wh: float = 100.0
    specific_energy: float = 200.0  # Wh/kg (technology constant)
    nominal_voltage: float = 22.2   # 6S Li-Po

    @property
    def mass_kg(self) -> float:
        """Derived: massKg = capacityWh / specificEnergy"""
        return self.capacity_wh / self.specific_energy


class Motor(eqx.Module):
    """Maps to: part def Motor"""
    mass_kg: float = 0.065
    max_power_w: float = 250.0
    efficiency_pct: float = 85.0


class PropulsionSubsystem(eqx.Module):
    """Maps to: part def PropulsionSubsystem
    Contains: part motor : Motor (composed, not inherited)"""
    num_motors: int = eqx.field(default=4, static=True)  # discrete — not differentiable
    motor: Motor = Motor()

    @property
    def mass_kg(self) -> float:
        """Derived: massKg = numMotors * motor.massKg"""
        return self.num_motors * self.motor.mass_kg


class FlightController(eqx.Module):
    """Maps to: part def FlightController"""
    mass_kg: float = 0.05
    power_w: float = 5.0


class IMU(eqx.Module):
    """Maps to: part def IMU"""
    mass_kg: float = 0.01
    power_w: float = 0.5


class GPS(eqx.Module):
    """Maps to: part def GPS"""
    mass_kg: float = 0.015
    power_w: float = 0.8


class Barometer(eqx.Module):
    """Maps to: part def Barometer"""
    mass_kg: float = 0.005
    power_w: float = 0.1


class AvionicsSubsystem(eqx.Module):
    """Maps to: part def AvionicsSubsystem
    Contains: part fcc, imu, gps, baro"""
    fcc: FlightController = FlightController()
    imu: IMU = IMU()
    gps: GPS = GPS()
    baro: Barometer = Barometer()

    @property
    def mass_kg(self) -> float:
        return self.fcc.mass_kg + self.imu.mass_kg + self.gps.mass_kg + self.baro.mass_kg

    @property
    def total_power_w(self) -> float:
        return self.fcc.power_w + self.imu.power_w + self.gps.power_w + self.baro.power_w


class CameraPayload(eqx.Module):
    """Maps to: part def CameraPayload"""
    mass_kg: float = 0.15
    power_w: float = 8.0


class Airframe(eqx.Module):
    """Maps to: part def Airframe"""
    mass_kg: float = 0.8
    wingspan_m: float = 0.5


class UAV(eqx.Module):
    """Maps to: part def UAV — the top-level system.

    Composes all subsystems. Derived attributes (totalMassKg,
    hoverPowerW, totalPowerW, enduranceMin) are methods that
    JAX can differentiate through.
    """
    airframe: Airframe = Airframe()
    battery: Battery = Battery()
    propulsion: PropulsionSubsystem = PropulsionSubsystem()
    avionics: AvionicsSubsystem = AvionicsSubsystem()
    payload: CameraPayload = CameraPayload()
    propulsive_constant: float = 50.0  # W/kg (empirical)

    def total_mass_kg(self) -> float:
        """Maps to: UAV.totalMassKg expression in SysML"""
        return (self.airframe.mass_kg +
                self.battery.mass_kg +
                self.propulsion.mass_kg +
                self.avionics.mass_kg +
                self.payload.mass_kg)

    def hover_power_w(self) -> float:
        """Maps to: UAV.hoverPowerW = propulsiveConstant * totalMassKg"""
        return self.propulsive_constant * self.total_mass_kg()

    def total_power_w(self) -> float:
        """Maps to: UAV.totalPowerW = hoverPowerW + avionicsPowerW + payloadPowerW"""
        return (self.hover_power_w() +
                self.avionics.total_power_w +
                self.payload.power_w)

    def endurance_min(self) -> float:
        """Maps to: UAV.enduranceMin = (capacityWh / totalPowerW) * 60"""
        return (self.battery.capacity_wh / self.total_power_w()) * 60.0


# ══════════════════════════════════════════════════════════════
# 2. HELPERS
# ══════════════════════════════════════════════════════════════

def section(title: str):
    print(f"\n{'═' * 65}")
    print(f"  {title}")
    print(f"{'═' * 65}")


def print_gradient_tree(grads, prefix="", depth=0):
    """Recursively print the gradient pytree, mirroring the architecture."""
    if isinstance(grads, eqx.Module):
        fields = vars(grads)
        for name, value in fields.items():
            if isinstance(value, eqx.Module):
                print(f"{'  ' * depth}{prefix}{name}:")
                print_gradient_tree(value, prefix="", depth=depth + 1)
            elif isinstance(value, (float, jnp.ndarray)):
                val = float(value) if isinstance(value, jnp.ndarray) else value
                if abs(val) > 1e-10:
                    print(f"{'  ' * depth}{prefix}{name}: {val:+.6f}")
    elif isinstance(grads, (float, jnp.ndarray)):
        val = float(grads) if isinstance(grads, jnp.ndarray) else grads
        print(f"{'  ' * depth}{prefix}{val:+.6f}")


# ══════════════════════════════════════════════════════════════
# 3. DEMONSTRATIONS
# ══════════════════════════════════════════════════════════════

def main():

    # ── 3.1 Forward evaluation ──────────────────────────────

    section("3.1 Forward Evaluation (matches SysML model)")

    uav = UAV()

    print(f"  Battery mass:      {uav.battery.mass_kg:.2f} kg")
    print(f"  Propulsion mass:   {uav.propulsion.mass_kg:.3f} kg")
    print(f"  Avionics mass:     {uav.avionics.mass_kg:.3f} kg")
    print(f"  Total mass:        {uav.total_mass_kg():.2f} kg")
    print(f"  Hover power:       {uav.hover_power_w():.1f} W")
    print(f"  Total power:       {uav.total_power_w():.1f} W")
    print(f"  Endurance:         {uav.endurance_min():.1f} min")

    # Verify against SysML Automator results
    assert abs(uav.total_mass_kg() - 1.79) < 0.01, "Mass mismatch with SysML model"
    assert abs(uav.total_power_w() - 103.9) < 0.1, "Power mismatch with SysML model"
    assert abs(uav.endurance_min() - 57.75) < 0.1, "Endurance mismatch with SysML model"
    print("\n  [PASS] All values match SysML Automator evaluation")

    # ── 3.2 Gradient computation ────────────────────────────

    section("3.2 Gradient of Endurance w.r.t. ALL Parameters")

    grad_fn = jax.grad(lambda u: u.endurance_min())
    grads = grad_fn(uav)

    print("  Gradient tree (d(endurance_min) / d(parameter)):\n")
    print_gradient_tree(grads)

    # ── 3.3 Key sensitivities ───────────────────────────────

    section("3.3 Key Sensitivities (interpretation)")

    print(f"  d(endurance)/d(battery.capacity_wh)      = {grads.battery.capacity_wh:+.4f} min/Wh")
    print(f"    -> 10 Wh more battery = {grads.battery.capacity_wh * 10:+.2f} min endurance")
    print()
    print(f"  d(endurance)/d(battery.specific_energy)   = {grads.battery.specific_energy:+.4f} min/(Wh/kg)")
    print(f"    -> Better battery chemistry (200->210 Wh/kg) = {grads.battery.specific_energy * 10:+.2f} min")
    print()
    print(f"  d(endurance)/d(payload.mass_kg)           = {grads.payload.mass_kg:+.4f} min/kg")
    print(f"    -> 100g heavier payload = {grads.payload.mass_kg * 0.1:+.2f} min endurance")
    print()
    print(f"  d(endurance)/d(payload.power_w)           = {grads.payload.power_w:+.4f} min/W")
    print(f"    -> 1W more payload power = {grads.payload.power_w:+.2f} min endurance")
    print()
    print(f"  d(endurance)/d(propulsive_constant)       = {grads.propulsive_constant:+.4f} min/(W/kg)")
    print(f"    -> Less efficient airframe (50->55 W/kg) = {grads.propulsive_constant * 5:+.2f} min")

    # ── 3.4 Requirement sensitivity ─────────────────────────

    section("3.4 Requirement Sensitivity Analysis")

    # MassBudget: totalMassKg <= 5.0
    # How sensitive is the mass margin to each parameter?
    mass_margin = lambda u: 5.0 - u.total_mass_kg()  # positive = satisfied
    grad_mass = jax.grad(mass_margin)
    gm = grad_mass(uav)

    print("  MassBudget requirement: totalMassKg <= 5.0 kg")
    print(f"  Current margin: {mass_margin(uav):.2f} kg (positive = satisfied)")
    print(f"  Most sensitive parameters:")
    print(f"    d(margin)/d(battery.capacity_wh)    = {gm.battery.capacity_wh:+.6f} kg/Wh")
    print(f"    d(margin)/d(airframe.mass_kg)        = {gm.airframe.mass_kg:+.6f} kg/kg")
    print(f"    d(margin)/d(propulsion.motor.mass_kg) = {gm.propulsion.motor.mass_kg:+.6f} kg/kg")

    print()

    # EnduranceRequirement: enduranceMin >= 30.0
    endurance_margin = lambda u: u.endurance_min() - 30.0  # positive = satisfied
    grad_endurance = jax.grad(endurance_margin)
    ge = grad_endurance(uav)

    print("  EnduranceRequirement: enduranceMin >= 30.0 min")
    print(f"  Current margin: {endurance_margin(uav):.2f} min (positive = satisfied)")
    print(f"  Most sensitive parameters:")
    print(f"    d(margin)/d(battery.capacity_wh)      = {ge.battery.capacity_wh:+.6f} min/Wh")
    print(f"    d(margin)/d(battery.specific_energy)   = {ge.battery.specific_energy:+.6f} min/(Wh/kg)")
    print(f"    d(margin)/d(payload.power_w)           = {ge.payload.power_w:+.6f} min/W")

    # ── 3.5 Jacobian: all outputs w.r.t. all parameters ────

    section("3.5 Multi-Output Sensitivity (endurance + mass + power)")

    def system_outputs(u):
        return jnp.array([u.endurance_min(), u.total_mass_kg(), u.total_power_w()])

    # Jacobian: 3 outputs x all parameters
    # jax.jacrev returns a pytree of shape (3,) for each parameter leaf
    jac_fn = jax.jacrev(system_outputs)
    jac = jac_fn(uav)

    print("  Jacobian rows: [endurance_min, total_mass_kg, total_power_w]")
    print(f"\n  w.r.t. battery.capacity_wh:")
    print(f"    d(endurance)/d(cap) = {float(jac.battery.capacity_wh[0]):+.4f} min/Wh")
    print(f"    d(mass)/d(cap)      = {float(jac.battery.capacity_wh[1]):+.4f} kg/Wh")
    print(f"    d(power)/d(cap)     = {float(jac.battery.capacity_wh[2]):+.4f} W/Wh")

    print(f"\n  w.r.t. payload.mass_kg:")
    print(f"    d(endurance)/d(m)   = {float(jac.payload.mass_kg[0]):+.4f} min/kg")
    print(f"    d(mass)/d(m)        = {float(jac.payload.mass_kg[1]):+.4f} kg/kg")
    print(f"    d(power)/d(m)       = {float(jac.payload.mass_kg[2]):+.4f} W/kg")

    # ── 3.6 Gradient-based optimization ─────────────────────

    section("3.6 Gradient-Based Design Optimization (optax)")

    # Objective: maximize endurance subject to mass <= 5 kg
    # We optimize battery.capacity_wh only, using manual gradient descent.
    # This is clearer than optax for a demo and avoids pytree compatibility issues.

    def objective(u):
        """Negative endurance + penalty for mass violation."""
        endurance = u.endurance_min()
        mass_penalty = jnp.maximum(0.0, u.total_mass_kg() - 5.0) * 100.0
        return -endurance + mass_penalty  # minimize this

    grad_objective = jax.grad(objective)
    lr = 5.0

    print(f"  Optimizing battery.capacity_wh to maximize endurance (mass <= 5 kg)")
    print(f"  {'Step':>6} {'Capacity':>10} {'Mass':>8} {'Power':>8} {'Endurance':>10} {'Loss':>10}")

    current_uav = uav
    for step in range(200):
        loss = objective(current_uav)
        grads = grad_objective(current_uav)

        # Update only battery.capacity_wh (manual projected gradient descent)
        new_cap = current_uav.battery.capacity_wh - lr * grads.battery.capacity_wh
        new_cap = jnp.clip(new_cap, 10.0, 2000.0)  # keep in feasible range
        new_battery = eqx.tree_at(
            lambda b: b.capacity_wh, current_uav.battery, new_cap
        )
        current_uav = eqx.tree_at(
            lambda u: u.battery, current_uav, new_battery
        )

        if step % 40 == 0 or step == 199:
            cap = float(current_uav.battery.capacity_wh)
            mass = float(current_uav.total_mass_kg())
            power = float(current_uav.total_power_w())
            endur = float(current_uav.endurance_min())
            print(f"  {step:>6} {cap:>10.1f} {mass:>8.2f} {power:>8.1f} {endur:>10.1f} {float(loss):>10.2f}")

    final = current_uav
    print(f"\n  Optimal battery capacity: {float(final.battery.capacity_wh):.1f} Wh")
    print(f"  Final endurance:          {float(final.endurance_min()):.1f} min")
    print(f"  Final total mass:         {float(final.total_mass_kg()):.2f} kg")
    print(f"  Mass budget satisfied:    {float(final.total_mass_kg()) <= 5.0}")

    # ── 3.7 Pytree structure visualization ──────────────────

    section("3.7 Architecture Mirror: pytree structure = SysML hierarchy")

    print("  UAV pytree leaves (each is a differentiable parameter):\n")
    leaves, treedef = jax.tree.flatten(uav)
    leaf_names = []

    def label_leaves(prefix, module):
        for name, value in vars(module).items():
            full = f"{prefix}.{name}" if prefix else name
            if isinstance(value, eqx.Module):
                label_leaves(full, value)
            else:
                leaf_names.append((full, value))

    label_leaves("uav", uav)
    for name, value in leaf_names:
        print(f"    {name} = {value}")

    print(f"\n  Total differentiable parameters: {len(leaves)}")
    print(f"  Pytree structure depth: {str(treedef).count('PyTreeDef')}")

    # ── Summary ─────────────────────────────────────────────

    section("SUMMARY")
    print("""
  This demo showed:
    1. Forward evaluation matching SysML Automator results exactly
    2. jax.grad computing endurance sensitivity to ALL parameters at once
    3. Requirement margin sensitivity (which parameter threatens which requirement)
    4. Full Jacobian: 3 outputs x all parameters in one call
    5. Gradient-based optimization of battery capacity with mass constraint
    6. The pytree structure mirrors the SysML v2 part hierarchy

  The gradient tree has the same architecture as the system.
  Every node in the gradient corresponds to a part in the SysML model.
""")


if __name__ == "__main__":
    main()
