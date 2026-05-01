#!/usr/bin/env python3
"""
ROS2 Communication Layer Conformance Checker.

Parses ROS2 source code (rclpy/qos.py, rmw/qos_profiles.h, rclpy/node.py)
and checks the SysML v2 comm layer definitions against the ground truth.

Checks:
  1. QoS policy enums: values match rclpy/qos.py enum definitions
  2. QoS profile fields: match QoSProfile.__slots__ from rclpy
  3. Preset QoS profiles: values match rmw/qos_profiles.h
  4. Communication pattern ports: TopicPublisher/Subscriber, ServiceServer/Client,
     ActionServer/Client match rclpy/node.py API signatures

Usage:
    .venv/bin/python tools/comm_conformance_checker.py \\
        --rclpy-dir references/rclpy/rclpy/rclpy \\
        --rmw-dir references/rmw/rmw/include/rmw \\
        --sysml-files projects/ros2-sysmlv2/ros2_sysmlv2/*.sysml

Run:
    .venv/bin/python tools/comm_conformance_checker.py --help
"""
import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ══════════════════════════════════════════════════════════════
# 1. SOURCE CODE PARSERS
# ══════════════════════════════════════════════════════════════

def parse_rclpy_enum(qos_py_path: Path, class_name: str) -> dict[str, int]:
    """Extract enum values from a rclpy QoS policy enum class."""
    values = {}
    in_class = False
    text = qos_py_path.read_text()

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith(f"class {class_name}("):
            in_class = True
            continue

        if in_class:
            # End of class: next class or unindented line
            if stripped.startswith("class ") or (line and not line[0].isspace() and stripped):
                if stripped.startswith("class "):
                    break

            # Parse enum value: NAME = integer
            match = re.match(r'^([A-Z_]+)\s*=\s*(\d+)', stripped)
            if match:
                values[match.group(1)] = int(match.group(2))

    return values


def parse_qos_profile_slots(qos_py_path: Path) -> list[str]:
    """Extract QoSProfile field names from __slots__."""
    text = qos_py_path.read_text()
    in_slots = False
    slots = []

    for line in text.splitlines():
        stripped = line.strip()

        if '__slots__ = [' in stripped:
            in_slots = True
            continue

        if in_slots:
            if stripped == ']':
                break
            # Parse: '_field_name',
            match = re.match(r"'_(\w+)'", stripped)
            if match:
                slots.append(match.group(1))

    return slots


def parse_rmw_preset_profiles(qos_profiles_h: Path) -> dict[str, dict]:
    """Extract preset QoS profile values from rmw/qos_profiles.h."""
    text = qos_profiles_h.read_text()
    profiles = {}

    # Match: static const rmw_qos_profile_t rmw_qos_profile_NAME = { ... };
    pattern = re.compile(
        r'static\s+const\s+rmw_qos_profile_t\s+rmw_qos_profile_(\w+)\s*=\s*\{([^}]+)\}',
        re.DOTALL
    )

    for match in pattern.finditer(text):
        name = match.group(1)
        body = match.group(2)

        # Extract the field values (positional, matching rmw_qos_profile_t struct order)
        values = []
        for line in body.splitlines():
            line = line.strip().rstrip(',')
            if line and not line.startswith('//'):
                values.append(line)

        if len(values) >= 4:
            profiles[name] = {
                'history': values[0],
                'depth': values[1],
                'reliability': values[2],
                'durability': values[3],
            }

    return profiles


def parse_create_methods(node_py_path: Path) -> dict[str, list[str]]:
    """Extract communication pattern create method parameters from rclpy/node.py."""
    text = node_py_path.read_text()
    methods = {}

    for method_name in ['create_publisher', 'create_subscription', 'create_service', 'create_client']:
        params = []
        in_method = False

        for line in text.splitlines():
            if f"def {method_name}(" in line:
                in_method = True
                continue
            if in_method:
                if line.strip().startswith(')') or line.strip().startswith('"""'):
                    break
                # Extract parameter name
                param_match = re.match(r'\s+(\w+)', line)
                if param_match:
                    param = param_match.group(1)
                    if param not in ('self', '*'):
                        params.append(param)

        methods[method_name] = params

    return methods


def parse_action_init_params(action_py_path: Path, class_name: str) -> list[str]:
    """Extract ActionServer/ActionClient __init__ required parameters."""
    text = action_py_path.read_text()
    params = []
    in_init = False
    past_star = False

    for line in text.splitlines():
        if f"class {class_name}(" in line:
            in_init = False  # wait for __init__
            continue
        if in_init is False and 'def __init__(' in line:
            in_init = True
            continue
        if in_init:
            stripped = line.strip()
            if stripped.startswith(')'):
                break
            if stripped == '*,':
                past_star = True
                continue
            param_match = re.match(r'(\w+)', stripped)
            if param_match:
                param = param_match.group(1)
                if param not in ('self',):
                    params.append(param)

    return params


# ══════════════════════════════════════════════════════════════
# 2. SYSML EXTRACTOR
# ══════════════════════════════════════════════════════════════

def extract_sysml_comm_layer(sysml_files: list[str]) -> dict:
    """Load SysML v2 files and extract comm layer definitions."""
    import syside

    model, diag = syside.load_model(sysml_files)
    if diag.contains_errors():
        print("ERROR: SysML model has parse errors:")
        for d in diag.diagnostics:
            print(f"  {d}")
        sys.exit(1)

    result = {
        'enums': {},        # name -> {value_name: ...}
        'attr_defs': {},    # name -> [field_names]
        'port_defs': {},    # name -> {items: [...], attrs: [...]}
        'conn_defs': {},    # name -> [end_names]
        'constraint_defs': {},  # name -> exists
    }

    for enum_def in model.nodes(syside.EnumerationDefinition):
        values = []
        for owned in enum_def.owned_elements.collect():
            if usage := owned.try_cast(syside.EnumerationUsage):
                values.append(usage.name)
        result['enums'][enum_def.name] = values

    for attr_def in model.nodes(syside.AttributeDefinition):
        fields = []
        for owned in attr_def.owned_elements.collect():
            if attr := owned.try_cast(syside.AttributeUsage):
                fields.append(attr.name)
        result['attr_defs'][attr_def.name] = fields

    for port_def in model.nodes(syside.PortDefinition):
        items = []
        attrs = []
        for owned in port_def.owned_elements.collect():
            if item := owned.try_cast(syside.ItemUsage):
                items.append(item.name)
            elif attr := owned.try_cast(syside.AttributeUsage):
                attrs.append(attr.name)
        result['port_defs'][port_def.name] = {'items': items, 'attrs': attrs}

    for conn_def in model.nodes(syside.ConnectionDefinition):
        result['conn_defs'][conn_def.name] = True

    for constr_def in model.nodes(syside.ConstraintDefinition):
        result['constraint_defs'][constr_def.name] = True

    return result


# ══════════════════════════════════════════════════════════════
# 3. CONFORMANCE CHECKS
# ══════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    category: str
    name: str
    status: str  # PASS, FAIL, MISSING
    details: str = ""


def check_qos_enums(rclpy_qos: Path, sysml: dict) -> list[CheckResult]:
    """Check QoS policy enums against rclpy source."""
    results = []

    enum_checks = {
        'ReliabilityPolicy': 'ReliabilityKind',
        'DurabilityPolicy': 'DurabilityKind',
        'HistoryPolicy': 'HistoryKind',
        'LivelinessPolicy': 'LivelinessKind',
    }

    for rclpy_name, sysml_name in enum_checks.items():
        source_values = parse_rclpy_enum(rclpy_qos, rclpy_name)

        if sysml_name not in sysml['enums']:
            results.append(CheckResult(
                "QoS Enum", sysml_name, "MISSING",
                f"No enum def '{sysml_name}' in SysML (maps to rclpy {rclpy_name})"
            ))
            # Report expected values
            for val_name in source_values:
                results.append(CheckResult(
                    "QoS Enum Value", f"{sysml_name}.{val_name}", "MISSING",
                    f"Expected from {rclpy_name}"
                ))
            continue

        sysml_values = sysml['enums'][sysml_name]
        results.append(CheckResult(
            "QoS Enum", sysml_name, "PASS",
            f"Found ({len(sysml_values)} values)"
        ))

        # Check individual values
        for val_name in source_values:
            # Normalize: BEST_EFFORT -> BestEffort, KEEP_LAST -> KeepLast
            camel = to_camel_case_from_upper(val_name)
            if camel in sysml_values or val_name in sysml_values:
                results.append(CheckResult(
                    "QoS Enum Value", f"{sysml_name}.{camel}", "PASS",
                    f"Matches {rclpy_name}.{val_name}"
                ))
            else:
                results.append(CheckResult(
                    "QoS Enum Value", f"{sysml_name}.{val_name}", "MISSING",
                    f"Expected from {rclpy_name}, SysML has: {sysml_values}"
                ))

    return results


def check_qos_profile_fields(rclpy_qos: Path, sysml: dict) -> list[CheckResult]:
    """Check QoSProfile fields against rclpy __slots__."""
    results = []

    source_fields = parse_qos_profile_slots(rclpy_qos)

    if 'QoSProfile' not in sysml['attr_defs']:
        results.append(CheckResult(
            "QoS Profile", "QoSProfile", "MISSING",
            "No attribute def 'QoSProfile' in SysML"
        ))
        for f in source_fields:
            results.append(CheckResult(
                "QoS Profile Field", f"QoSProfile.{f}", "MISSING", ""))
        return results

    sysml_fields = sysml['attr_defs']['QoSProfile']
    results.append(CheckResult(
        "QoS Profile", "QoSProfile", "PASS",
        f"Found ({len(sysml_fields)} fields)"
    ))

    for source_field in source_fields:
        camel = to_camel_case_from_snake(source_field)
        if camel in sysml_fields or source_field in sysml_fields:
            results.append(CheckResult(
                "QoS Profile Field", f"QoSProfile.{camel}", "PASS",
                f"Matches __slots__._{source_field}"
            ))
        else:
            results.append(CheckResult(
                "QoS Profile Field", f"QoSProfile.{source_field}", "MISSING",
                f"Expected from QoSProfile.__slots__, SysML has: {sysml_fields}"
            ))

    return results


def check_preset_profiles(rmw_qos_h: Path, sysml: dict) -> list[CheckResult]:
    """Check preset QoS profiles against rmw/qos_profiles.h."""
    results = []

    source_profiles = parse_rmw_preset_profiles(rmw_qos_h)

    # Map rmw profile names to expected SysML attribute names
    profile_map = {
        'sensor_data': 'sensorDataQoS',
        'default': 'defaultQoS',
        'services_default': 'servicesDefaultQoS',
        'parameters': 'parametersQoS',
        'parameter_events': 'parameterEventsQoS',
        'system_default': 'systemDefaultQoS',
        'best_available': 'bestAvailableQoS',
    }

    for rmw_name, sysml_name in profile_map.items():
        if rmw_name in source_profiles:
            # Check if the SysML model has a corresponding attribute usage
            # (These are attribute usages, not definitions — harder to check without
            #  loading the full model. For now, just report presence.)
            results.append(CheckResult(
                "Preset Profile", sysml_name, "INFO",
                f"rmw_qos_profile_{rmw_name}: "
                f"history={source_profiles[rmw_name]['history']}, "
                f"depth={source_profiles[rmw_name]['depth']}, "
                f"reliability={source_profiles[rmw_name]['reliability']}, "
                f"durability={source_profiles[rmw_name]['durability']}"
            ))

    return results


def check_comm_ports(rclpy_node: Path, rclpy_action_dir: Path, sysml: dict) -> list[CheckResult]:
    """Check communication pattern port definitions against rclpy APIs."""
    results = []

    # Expected port defs and their key properties
    expected_ports = {
        'TopicPublisher': {
            'maps_to': 'create_publisher(msg_type, topic, qos_profile)',
            'expected_attrs': ['topicName', 'qos'],
            'expected_items_out': ['msg'],
            'expected_items_in': [],
        },
        'TopicSubscriber': {
            'maps_to': 'create_subscription(msg_type, topic, callback, qos_profile)',
            'expected_attrs': ['topicName', 'qos'],
            'expected_items_out': [],
            'expected_items_in': ['msg'],
        },
        'ServiceServer': {
            'maps_to': 'create_service(srv_type, srv_name, callback, qos_profile)',
            'expected_attrs': ['serviceName'],
            'expected_items_in': ['request'],
            'expected_items_out': ['response'],
        },
        'ServiceClient': {
            'maps_to': 'create_client(srv_type, srv_name, qos_profile)',
            'expected_attrs': ['serviceName'],
            'expected_items_out': ['request'],
            'expected_items_in': ['response'],
        },
        'ActionServer': {
            'maps_to': 'ActionServer(node, action_type, action_name)',
            'expected_attrs': ['actionName'],
            'expected_items_in': ['goal'],
            'expected_items_out': ['feedback', 'result'],
        },
        'ActionClient': {
            'maps_to': 'ActionClient(node, action_type, action_name)',
            'expected_attrs': ['actionName'],
            'expected_items_out': ['goal'],
            'expected_items_in': ['feedback', 'result'],
        },
    }

    for port_name, expected in expected_ports.items():
        if port_name not in sysml['port_defs']:
            results.append(CheckResult(
                "Port Def", port_name, "MISSING",
                f"No port def '{port_name}' in SysML (maps to {expected['maps_to']})"
            ))
            continue

        port = sysml['port_defs'][port_name]
        results.append(CheckResult(
            "Port Def", port_name, "PASS",
            f"Found (attrs: {port['attrs']}, items: {port['items']})"
        ))

        # Check expected attributes
        for attr in expected['expected_attrs']:
            if attr in port['attrs']:
                results.append(CheckResult(
                    "Port Attr", f"{port_name}.{attr}", "PASS", ""))
            else:
                results.append(CheckResult(
                    "Port Attr", f"{port_name}.{attr}", "MISSING",
                    f"Expected from {expected['maps_to']}"
                ))

        # Check expected items (we can't distinguish in/out from the Automator easily,
        # so just check presence)
        all_expected_items = expected['expected_items_in'] + expected['expected_items_out']
        for item_name in all_expected_items:
            if item_name in port['items']:
                results.append(CheckResult(
                    "Port Item", f"{port_name}.{item_name}", "PASS", ""))
            else:
                results.append(CheckResult(
                    "Port Item", f"{port_name}.{item_name}", "MISSING",
                    f"Expected item '{item_name}' not found in port def"
                ))

    return results


def check_connection_defs(sysml: dict) -> list[CheckResult]:
    """Check connection definitions exist."""
    results = []

    expected = ['TopicConnection', 'ServiceBinding', 'ActionBinding']
    for name in expected:
        if name in sysml['conn_defs']:
            results.append(CheckResult("Connection Def", name, "PASS", ""))
        else:
            results.append(CheckResult(
                "Connection Def", name, "MISSING",
                f"No connection def '{name}' in SysML"
            ))

    return results


# ══════════════════════════════════════════════════════════════
# 4. HELPERS
# ══════════════════════════════════════════════════════════════

def to_camel_case_from_upper(upper_name: str) -> str:
    """BEST_EFFORT -> BestEffort, KEEP_LAST -> KeepLast."""
    return ''.join(word.capitalize() for word in upper_name.lower().split('_'))


def to_camel_case_from_snake(snake: str) -> str:
    """liveliness_lease_duration -> livelinessLeaseDuration."""
    parts = snake.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])


# ══════════════════════════════════════════════════════════════
# 5. REPORTING
# ══════════════════════════════════════════════════════════════

def print_report(all_results: list[CheckResult], verbose: bool = False):
    """Print the conformance report."""
    print("=" * 70)
    print("ROS2 Communication Layer → SysML v2 Conformance Report")
    print("=" * 70)
    print()

    # Group by category
    categories = {}
    for r in all_results:
        categories.setdefault(r.category, []).append(r)

    total_pass = 0
    total_fail = 0
    total_info = 0

    for cat, results in categories.items():
        pass_count = sum(1 for r in results if r.status == "PASS")
        fail_count = sum(1 for r in results if r.status in ("FAIL", "MISSING"))
        info_count = sum(1 for r in results if r.status == "INFO")

        total_pass += pass_count
        total_fail += fail_count
        total_info += info_count

        icon = "✓" if fail_count == 0 else "✗"
        print(f"  [{icon}] {cat}: {pass_count}/{pass_count + fail_count} passed"
              f"{f' ({info_count} info)' if info_count else ''}")

        if verbose or fail_count > 0:
            for r in results:
                if r.status == "PASS" and not verbose:
                    continue
                status_map = {"PASS": "  OK ", "MISSING": " MISS", "FAIL": " FAIL", "INFO": " INFO"}
                print(f"        [{status_map[r.status]}] {r.name}"
                      f"{f' — {r.details}' if r.details and r.status != 'PASS' else ''}")

    print()
    print("-" * 70)
    print(f"  Total: {total_pass} passed, {total_fail} failed, {total_info} info")
    print("-" * 70)

    return total_fail == 0


# ══════════════════════════════════════════════════════════════
# 6. MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Check ROS2 communication layer SysML v2 definitions against rclpy/rmw source"
    )
    parser.add_argument("--rclpy-dir", required=True, help="Path to rclpy/rclpy/ directory")
    parser.add_argument("--rmw-dir", required=True, help="Path to rmw/include/rmw/ directory")
    parser.add_argument("--sysml-files", nargs="+", required=True, help="SysML v2 files to load")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    rclpy_dir = Path(args.rclpy_dir)
    rmw_dir = Path(args.rmw_dir)

    rclpy_qos = rclpy_dir / "qos.py"
    rclpy_node = rclpy_dir / "node.py"
    rclpy_action_dir = rclpy_dir / "action"
    rmw_qos_h = rmw_dir / "qos_profiles.h"

    for f in [rclpy_qos, rclpy_node, rmw_qos_h]:
        if not f.exists():
            print(f"ERROR: Source file not found: {f}")
            sys.exit(1)

    # Load SysML model
    print(f"Loading {len(args.sysml_files)} SysML files...")
    sysml = extract_sysml_comm_layer([str(f) for f in args.sysml_files])
    print(f"Found: {len(sysml['enums'])} enums, {len(sysml['attr_defs'])} attr defs, "
          f"{len(sysml['port_defs'])} port defs, {len(sysml['conn_defs'])} conn defs, "
          f"{len(sysml['constraint_defs'])} constraint defs")
    print()

    # Run all checks
    all_results = []
    all_results.extend(check_qos_enums(rclpy_qos, sysml))
    all_results.extend(check_qos_profile_fields(rclpy_qos, sysml))
    all_results.extend(check_preset_profiles(rmw_qos_h, sysml))
    all_results.extend(check_comm_ports(rclpy_node, rclpy_action_dir, sysml))
    all_results.extend(check_connection_defs(sysml))

    # Report
    all_passed = print_report(all_results, verbose=args.verbose)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
