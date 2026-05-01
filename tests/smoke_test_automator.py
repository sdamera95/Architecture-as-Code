#!/usr/bin/env python3
"""
Smoke test for Syside Automator against the UAV demo model.

Exercises every SysML v2 construct type present in demo.sysml:
  - PartDefinition / PartUsage (hierarchy navigation)
  - PortDefinition / PortUsage (with item directions)
  - ItemDefinition (flow items)
  - ConnectionDefinition / ConnectionUsage (wiring)
  - FlowUsage (directional data flows)
  - AttributeDefinition / AttributeUsage (typed quantities)
  - ActionDefinition / ActionUsage (behavioral sequencing)
  - RequirementDefinition (with doc blocks and subjects)

Run:
    .venv/bin/python tests/smoke_test_automator.py
"""
import syside
import sys
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "syside-demos" / "demo.sysml"

# ── Helpers ────────────────────────────────────────────────────

def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def check(description: str, condition: bool):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    return condition

# ── Load Model ─────────────────────────────────────────────────

def main():
    section("1. Load Model")
    model, diagnostics = syside.load_model([str(MODEL_PATH)])

    has_errors = diagnostics.contains_errors()
    check(f"Model loaded from {MODEL_PATH.name}", not has_errors)
    if has_errors:
        print("  FATAL: Model has parse errors. Aborting.")
        sys.exit(1)

    # ── Part Definitions ───────────────────────────────────────

    section("2. Part Definitions")
    part_defs = list(model.nodes(syside.PartDefinition))
    part_names = [p.name for p in part_defs]
    print(f"  Found {len(part_defs)} part definitions")

    expected_parts = [
        "Battery", "Motor", "Propeller", "PropulsionSubsystem",
        "IMU", "GPS", "Barometer", "FlightController",
        "AvionicsSubsystem", "CameraPayload", "Airframe", "UAV",
    ]
    for name in expected_parts:
        check(f"part def {name} exists", name in part_names)

    # ── Port Definitions ───────────────────────────────────────

    section("3. Port Definitions")
    port_defs = list(model.nodes(syside.PortDefinition))
    port_names = [p.name for p in port_defs]
    print(f"  Found {len(port_defs)} port definitions")

    expected_ports = ["PowerPort", "CommandPort", "TelemetryPort",
                      "ThrustPort", "SensorPort"]
    for name in expected_ports:
        check(f"port def {name} exists", name in port_names)

    # ── Item Definitions ───────────────────────────────────────

    section("4. Item Definitions (flow items)")
    item_defs = list(model.nodes(syside.ItemDefinition))
    item_names = [i.name for i in item_defs]
    print(f"  Found {len(item_defs)} item definitions")

    expected_items = ["ElectricalPower", "CommandSignal", "TelemetryData",
                      "ThrustForce", "SensorReading"]
    for name in expected_items:
        check(f"item def {name} exists", name in item_names)

    # Check ElectricalPower has voltage and power attributes
    ep = next(i for i in item_defs if i.name == "ElectricalPower")
    ep_attrs = []
    for owned in ep.owned_elements.collect():
        if attr := owned.try_cast(syside.AttributeUsage):
            ep_attrs.append(attr.name)
    check("ElectricalPower has 'voltage' attribute", "voltage" in ep_attrs)
    check("ElectricalPower has 'power' attribute", "power" in ep_attrs)

    # ── Connection Definitions ─────────────────────────────────

    section("5. Connection Definitions")
    conn_defs = list(model.nodes(syside.ConnectionDefinition))
    conn_names = [c.name for c in conn_defs]
    print(f"  Found {len(conn_defs)} connection definitions")

    expected_conns = ["PowerConnection", "CommandConnection",
                      "ShaftConnection", "ThrustConnection",
                      "SensorConnection", "TelemetryConnection"]
    for name in expected_conns:
        check(f"connection def {name} exists", name in conn_names)

    # ── Part Hierarchy (UAV composition) ───────────────────────

    section("6. Part Hierarchy — UAV Composition Tree")
    uav_def = next(p for p in part_defs if p.name == "UAV")

    # Walk owned elements to find nested part usages
    uav_parts = {}
    uav_ports = {}
    uav_connections = []
    uav_flows = []
    uav_attrs = []

    for owned in uav_def.owned_elements.collect():
        if part := owned.try_cast(syside.PartUsage):
            uav_parts[part.name] = part
        elif port := owned.try_cast(syside.PortUsage):
            uav_ports[port.name] = port
        elif conn := owned.try_cast(syside.ConnectionUsage):
            uav_connections.append(conn)
        elif flow := owned.try_cast(syside.FlowUsage):
            uav_flows.append(flow)
        elif attr := owned.try_cast(syside.AttributeUsage):
            uav_attrs.append(attr)

    print(f"  UAV has {len(uav_parts)} nested parts, "
          f"{len(uav_connections)} connections, "
          f"{len(uav_flows)} flows, "
          f"{len(uav_attrs)} attributes")

    expected_uav_parts = ["airframe", "battery", "propulsion",
                          "avionics", "payload"]
    for name in expected_uav_parts:
        check(f"part {name} in UAV", name in uav_parts)

    check("UAV has 4 connections (3 power + 1 command)",
          len(uav_connections) == 4)
    check("UAV has 4 flows (3 power + 1 command)",
          len(uav_flows) == 4)

    expected_uav_attrs = ["totalMass", "cruiseSpeed", "maxAltitude", "endurance"]
    for name in expected_uav_attrs:
        check(f"attribute {name} in UAV", name in [a.name for a in uav_attrs])

    # ── Subsystem Drill-Down (PropulsionSubsystem) ─────────────

    section("7. Subsystem Drill-Down — PropulsionSubsystem")
    prop_def = next(p for p in part_defs if p.name == "PropulsionSubsystem")

    prop_parts = []
    prop_ports = []
    prop_conns = []
    for owned in prop_def.owned_elements.collect():
        if part := owned.try_cast(syside.PartUsage):
            prop_parts.append(part.name)
        elif port := owned.try_cast(syside.PortUsage):
            prop_ports.append(port.name)
        elif conn := owned.try_cast(syside.ConnectionUsage):
            prop_conns.append(conn)

    check("PropulsionSubsystem contains 'motor'", "motor" in prop_parts)
    check("PropulsionSubsystem contains 'propeller'", "propeller" in prop_parts)
    check("PropulsionSubsystem has 3 ports (powerIn, cmdIn, thrustOut)",
          len(prop_ports) == 3)
    check("PropulsionSubsystem has 4 internal connections",
          len(prop_conns) == 4)

    # ── Port Item Directions ───────────────────────────────────

    section("8. Port Item Directions")
    # CommandPort should have: out cmd, in ack
    cmd_port_def = next(p for p in port_defs if p.name == "CommandPort")
    cmd_items = []
    for owned in cmd_port_def.owned_elements.collect():
        if item := owned.try_cast(syside.ItemUsage):
            cmd_items.append(item.name)
    check("CommandPort has 'cmd' item", "cmd" in cmd_items)
    check("CommandPort has 'ack' item", "ack" in cmd_items)
    print(f"  CommandPort items: {cmd_items}")

    # ── Conjugate Ports ────────────────────────────────────────

    section("9. Conjugate Ports (~PowerPort)")
    motor_def = next(p for p in part_defs if p.name == "Motor")
    motor_ports = []
    for owned in motor_def.owned_elements.collect():
        if port := owned.try_cast(syside.PortUsage):
            motor_ports.append(port.name)
    check("Motor has powerIn port (conjugate ~PowerPort)", "powerIn" in motor_ports)
    check("Motor has cmdIn port (conjugate ~CommandPort)", "cmdIn" in motor_ports)
    check("Motor has shaftOut port (ThrustPort)", "shaftOut" in motor_ports)
    print(f"  Motor ports: {motor_ports}")

    # ── Action Definitions (Mission Sequence) ──────────────────

    section("10. Action Definitions — Mission Sequence")
    action_defs = list(model.nodes(syside.ActionDefinition))
    action_names = [a.name for a in action_defs]
    print(f"  Found {len(action_defs)} action definitions")

    expected_actions = ["Takeoff", "Cruise", "Survey",
                        "ReturnToBase", "Land", "Mission"]
    for name in expected_actions:
        check(f"action def {name} exists", name in action_names)

    # Check Mission has nested action usages
    mission_def = next(a for a in action_defs if a.name == "Mission")
    mission_actions = []
    for owned in mission_def.owned_elements.collect():
        if action := owned.try_cast(syside.ActionUsage):
            mission_actions.append(action.name)
    check("Mission has 5 action usages",
          len(mission_actions) == 5)
    print(f"  Mission action sequence: {mission_actions}")

    # ── Requirement Definitions ────────────────────────────────

    section("11. Requirement Definitions")
    req_defs = list(model.nodes(syside.RequirementDefinition))
    req_names = [r.name for r in req_defs]
    print(f"  Found {len(req_defs)} requirement definitions")

    expected_reqs = ["MassBudget", "EnduranceRequirement", "AltitudeRequirement"]
    for name in expected_reqs:
        check(f"requirement def {name} exists", name in req_names)

    # Try to read the doc block from MassBudget
    mass_req = next(r for r in req_defs if r.name == "MassBudget")
    doc_elements = []
    for owned in mass_req.owned_elements.collect():
        doc_elements.append(f"{owned.__class__.__name__}: {owned.name}")
    print(f"  MassBudget owned elements: {doc_elements}")

    # ── Attribute Definitions ──────────────────────────────────

    section("12. Attribute Definitions (typed quantities)")
    attr_defs = list(model.nodes(syside.AttributeDefinition))
    attr_names = [a.name for a in attr_defs]
    print(f"  Found {len(attr_defs)} attribute definitions")

    expected_attr_defs = ["MassValue", "LengthValue", "SpeedValue",
                          "DurationValue", "PowerValue", "EnergyValue",
                          "VoltageValue", "AltitudeValue"]
    for name in expected_attr_defs:
        check(f"attribute def {name} exists", name in attr_names)

    # ── Summary ────────────────────────────────────────────────

    section("SUMMARY")
    print(f"""
  Model:                {MODEL_PATH.name}
  Part definitions:     {len(part_defs)}
  Port definitions:     {len(port_defs)}
  Item definitions:     {len(item_defs)}
  Connection defs:      {len(conn_defs)}
  Action definitions:   {len(action_defs)}
  Requirement defs:     {len(req_defs)}
  Attribute defs:       {len(attr_defs)}
  UAV nested parts:     {len(uav_parts)}
  UAV connections:      {len(uav_connections)}
  UAV flows:            {len(uav_flows)}
  Syside version:       {syside.__version__}
""")
    print("  All checks passed." if all_passed else "  Some checks FAILED.")


all_passed = True
_original_check = check
def check(description, condition):
    global all_passed
    if not condition:
        all_passed = False
    return _original_check(description, condition)

if __name__ == "__main__":
    main()
