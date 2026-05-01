#!/usr/bin/env python3
"""Generate a ROS2 ament_python package from architecture.json.

Reads the architecture extracted by extract_architecture.py and generates:
  - Node skeletons (lifecycle nodes with pre-wired pubs/subs/params)
  - package.xml, setup.py, setup.cfg
  - Launch file wiring all nodes
  - Parameter YAML with defaults
  - Conformance monitor node

Usage:
    .venv/bin/python bridge/generate_ros2.py \\
        generated/architecture.json \\
        --output generated/test_robot
"""
import argparse
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

log = logging.getLogger(__name__)

from jinja2 import Environment, FileSystemLoader


# ══════════════════════════════════════════════════════════════════════
# ROS2 QoS preset names → rclpy import expressions
# ══════════════════════════════════════════════════════════════════════

QOS_PRESETS_RCLPY = {
    "sensor_data": "qos_profile_sensor_data",
    "default": "10",
    "services_default": "qos_profile_services_default",
    "parameters": "qos_profile_parameters",
    "parameter_events": "qos_profile_parameter_events",
    "system_default": "qos_profile_system_default",
    "best_available": "10",
}

# QoS preset → expected reliability/durability for conformance checking
QOS_PRESET_PROPERTIES = {
    "sensor_data": {"reliability": "BEST_EFFORT", "durability": "VOLATILE"},
    "default": {"reliability": "RELIABLE", "durability": "VOLATILE"},
    "services_default": {"reliability": "RELIABLE", "durability": "VOLATILE"},
    "parameters": {"reliability": "RELIABLE", "durability": "VOLATILE"},
    "parameter_events": {"reliability": "RELIABLE", "durability": "VOLATILE"},
    "system_default": {"reliability": "SYSTEM_DEFAULT", "durability": "SYSTEM_DEFAULT"},
    "best_available": {"reliability": "RELIABLE", "durability": "VOLATILE"},
}


def check_qos_compatibility(pub_preset: str | None, sub_preset: str | None) -> dict:
    """Check DDS QoS compatibility between publisher and subscriber presets.

    Applies the asymmetric compatibility rules from the DDS specification:
    - BEST_EFFORT publisher + RELIABLE subscriber = INCOMPATIBLE (silent data loss)
    - VOLATILE publisher + TRANSIENT_LOCAL subscriber = INCOMPATIBLE (missed messages)
    - SYSTEM_DEFAULT or BEST_AVAILABLE = indeterminate (runtime negotiation)

    Returns dict with 'compatible' (bool), 'warning' (str or None).
    """
    if not pub_preset or not sub_preset:
        return {"compatible": True, "warning": None}

    pub_props = QOS_PRESET_PROPERTIES.get(pub_preset, {})
    sub_props = QOS_PRESET_PROPERTIES.get(sub_preset, {})

    pub_rel = pub_props.get("reliability", "UNKNOWN")
    pub_dur = pub_props.get("durability", "UNKNOWN")
    sub_rel = sub_props.get("reliability", "UNKNOWN")
    sub_dur = sub_props.get("durability", "UNKNOWN")

    issues = []

    # Reliability: best-effort pub -> reliable sub = silent data loss
    if pub_rel == "BEST_EFFORT" and sub_rel == "RELIABLE":
        issues.append("INCOMPATIBLE reliability: best-effort publisher -> reliable subscriber")

    # Durability: volatile pub -> transient-local sub = missed messages
    if pub_dur == "VOLATILE" and sub_dur == "TRANSIENT_LOCAL":
        issues.append("INCOMPATIBLE durability: volatile publisher -> transient-local subscriber")

    # Indeterminate: system-default policies depend on runtime negotiation
    all_policies = [pub_rel, pub_dur, sub_rel, sub_dur]
    if any(p in ("SYSTEM_DEFAULT", "BEST_AVAILABLE") for p in all_policies):
        issues.append("INDETERMINATE: system-default or best-available policy requires runtime check")

    compatible = not any("INCOMPATIBLE" in i for i in issues)
    return {
        "compatible": compatible,
        "warning": "; ".join(issues) if issues else None,
    }


def resolve_connections(arch: dict) -> list[dict]:
    """Cross-reference connections with nodes to produce topic-level data.

    Each connection in the architecture has endpoints like 'lidar.sensorPub'
    (instance_name.port_name). This function resolves those paths against the
    node list to produce the actual topic name, message type, QoS, and
    node identity for both publisher and subscriber.
    """
    # Build instance_name → node lookup
    node_by_instance = {}
    for node in arch["nodes"]:
        node_by_instance[node.get("instance_name", node["name"])] = node

    def find_node_and_port(path, node_lookup):
        """Resolve 'nav.localCostmap.mapSub' → (node for nav.localCostmap, 'mapSub').

        The path is instance_path.port_name. The instance_path may be multi-level
        (e.g., 'nav.localCostmap') for nodes inside composites. We find the longest
        matching instance name prefix.
        """
        parts = path.split(".")
        # Try progressively longer prefixes: longest match wins
        for i in range(len(parts) - 1, 0, -1):
            instance = ".".join(parts[:i])
            port = parts[i]
            if instance in node_lookup:
                return node_lookup[instance], port
        return None, parts[-1] if parts else None

    resolved = []
    for conn in arch.get("connections", []):
        source_path = conn.get("source", "")
        target_path = conn.get("target", "")

        if "." not in source_path or "." not in target_path:
            resolved.append({
                "name": conn.get("name", ""),
                "topic": None,
                "resolved": False,
            })
            continue

        pub_node, pub_port_name = find_node_and_port(source_path, node_by_instance)
        sub_node, sub_port_name = find_node_and_port(target_path, node_by_instance)

        if not pub_node or not sub_node:
            resolved.append({
                "name": conn.get("name", ""),
                "topic": None,
                "resolved": False,
            })
            continue

        # Find the publisher port on the publishing node
        pub_port = None
        for p in pub_node.get("publishers", []):
            if p.get("port_name") == pub_port_name:
                pub_port = p
                break

        # Find the subscriber port on the subscribing node
        sub_port = None
        for s in sub_node.get("subscribers", []):
            if s.get("port_name") == sub_port_name:
                sub_port = s
                break

        topic_name = pub_port.get("topic_name") if pub_port else None

        pub_qos = pub_port.get("qos_preset") if pub_port else None
        sub_qos = sub_port.get("qos_preset") if sub_port else None
        qos_compat = check_qos_compatibility(pub_qos, sub_qos)

        resolved.append({
            "name": conn.get("name", ""),
            "topic": topic_name,
            "msg_type": (pub_port.get("msg_type") if pub_port else None),
            "pub_node": pub_node.get("name", pub_node.get("type_name", "")),
            "pub_namespace": pub_node.get("namespace", "/"),
            "pub_qos": pub_qos,
            "sub_node": sub_node.get("name", sub_node.get("type_name", "")),
            "sub_namespace": sub_node.get("namespace", "/"),
            "sub_qos": sub_qos,
            "qos_compatible": qos_compat["compatible"],
            "qos_warning": qos_compat["warning"],
            "resolved": bool(pub_port and sub_port and topic_name),
        })

        # Static QoS compatibility check
        conn_name = conn.get("name", "?")
        if not qos_compat["compatible"]:
            log.warning(f"QoS INCOMPATIBLE on '{conn_name}' ({topic_name}): {qos_compat['warning']}")
        elif qos_compat["warning"]:
            log.info(f"QoS indeterminate on '{conn_name}' ({topic_name}): {qos_compat['warning']}")

        conn_name = conn.get("name", "?")
        if not pub_node:
            log.warning(f"Connection '{conn_name}': publisher instance not found in '{source_path}'")
        elif not pub_port:
            log.warning(f"Connection '{conn_name}': publisher port '{pub_port_name}' not found on node '{pub_node.get('name')}'")
        if not sub_node:
            log.warning(f"Connection '{conn_name}': subscriber instance not found in '{target_path}'")
        elif not sub_port:
            log.warning(f"Connection '{conn_name}': subscriber port '{sub_port_name}' not found on node '{sub_node.get('name')}'")

    return resolved


def collect_service_endpoints(arch: dict) -> list[dict]:
    """Collect all service server endpoints declared across nodes."""
    services = []
    for node in arch["nodes"]:
        for svc in node.get("service_servers", []):
            svc_name = svc.get("service_name")
            if svc_name:
                services.append({
                    "service_name": svc_name,
                    "node_name": node.get("name", node.get("type_name", "")),
                    "namespace": node.get("namespace", "/"),
                })
    return services


def collect_action_endpoints(arch: dict) -> list[dict]:
    """Collect all action server endpoints declared across nodes."""
    actions = []
    for node in arch["nodes"]:
        for act in node.get("action_servers", []):
            act_name = act.get("action_name")
            if act_name:
                actions.append({
                    "action_name": act_name,
                    "node_name": node.get("name", node.get("type_name", "")),
                    "namespace": node.get("namespace", "/"),
                })
    return actions


def collect_parameter_declarations(arch: dict) -> list[dict]:
    """Collect all declared parameters across custom nodes."""
    params = []
    for node in arch["nodes"]:
        if node.get("is_standard", False):
            continue
        for param in node.get("parameters", []):
            params.append({
                "param_name": param.get("name", ""),
                "node_name": node.get("name", node.get("type_name", "")),
                "namespace": node.get("namespace", "/"),
            })
    return params


def collect_qos_expectations(arch: dict) -> list[dict]:
    """Collect per-topic QoS expectations from publisher ports."""
    qos_list = []
    seen = set()
    for node in arch["nodes"]:
        for pub in node.get("publishers", []):
            topic = pub.get("topic_name")
            preset = pub.get("qos_preset")
            if topic and preset and topic not in seen:
                props = QOS_PRESET_PROPERTIES.get(preset, {})
                qos_list.append({
                    "topic": topic,
                    "preset": preset,
                    "reliability": props.get("reliability", "UNKNOWN"),
                    "durability": props.get("durability", "UNKNOWN"),
                })
                seen.add(topic)
    return qos_list


def msg_type_to_import(msg_type_str: str) -> tuple[str, str]:
    """Convert 'sensor_msgs.msg.LaserScan' → ('from sensor_msgs.msg import LaserScan', 'LaserScan')."""
    parts = msg_type_str.rsplit(".", 1)
    if len(parts) == 2:
        module, cls = parts
        return f"from {module} import {cls}", cls
    return f"# Unknown type: {msg_type_str}", msg_type_str


def to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return s


def prepare_node_context(node: dict) -> dict:
    """Prepare a node dict for template rendering with resolved imports and class names."""
    imports = set()
    qos_symbols_used = set()

    # Process publishers
    for pub in node.get("publishers", []):
        if pub.get("msg_type"):
            imp, cls = msg_type_to_import(pub["msg_type"])
            imports.add(imp)
            pub["msg_class"] = cls
        else:
            pub["msg_class"] = "# TODO: set message type"

        preset = pub.get("qos_preset")
        qos_arg = QOS_PRESETS_RCLPY.get(preset, "10") if preset else "10"
        pub["qos_arg"] = qos_arg
        # Track named QoS profiles for import
        if qos_arg.startswith("qos_profile_"):
            qos_symbols_used.add(qos_arg)

        # Fully-wired mode period: sensor topics at 10 Hz, others at 1 Hz
        if preset == "sensor_data":
            pub["wired_period"] = "0.1"  # 10 Hz
        else:
            pub["wired_period"] = "1.0"  # 1 Hz

    # Process subscribers
    for sub in node.get("subscribers", []):
        if sub.get("msg_type"):
            imp, cls = msg_type_to_import(sub["msg_type"])
            imports.add(imp)
            sub["msg_class"] = cls
        else:
            sub["msg_class"] = "# TODO: set message type"

        preset = sub.get("qos_preset")
        qos_arg = QOS_PRESETS_RCLPY.get(preset, "10") if preset else "10"
        sub["qos_arg"] = qos_arg
        if qos_arg.startswith("qos_profile_"):
            qos_symbols_used.add(qos_arg)

    # Process parameters
    for param in node.get("parameters", []):
        default = param.get("default")
        if default is None:
            param_type = str(param.get("type", ""))
            if "Double" in param_type:
                param["default_value"] = "0.0"
                param["yaml_value"] = "0.0"
            elif "Integer" in param_type:
                param["default_value"] = "0"
                param["yaml_value"] = "0"
            elif "Bool" in param_type:
                param["default_value"] = "False"
                param["yaml_value"] = "false"
            elif "String" in param_type:
                param["default_value"] = "''"
                param["yaml_value"] = "''"
            else:
                param["default_value"] = "None"
                param["yaml_value"] = "null"
        else:
            param["default_value"] = repr(default)
            param["yaml_value"] = str(default)

    # Add QoS import with only the profiles actually used
    if qos_symbols_used:
        imports.add(f"from rclpy.qos import {', '.join(sorted(qos_symbols_used))}")

    return {
        "node": node,
        "imports": sorted(imports),
    }


def generate_package(arch: dict, output_dir: str, wired: bool = False):
    """Generate a complete ament_python ROS2 package.

    Args:
        arch: Architecture dict from extract_architecture.py.
        output_dir: Output directory for the generated package.
        wired: If True, fully-wired mode: seed all publishers with periodic
               default messages and all subscribers with logging callbacks,
               so the complete topology is verifiable before implementing
               real callback logic.
    """
    system_name = arch["metadata"]["model_name"]
    pkg_name = to_snake_case(system_name)

    if wired:
        print("  Mode: FULLY-WIRED (all endpoints seeded with default data)")

    output = Path(output_dir)

    # Clean and create directory structure
    if output.exists():
        shutil.rmtree(output)

    pkg_dir = output / pkg_name
    pkg_dir.mkdir(parents=True)
    (output / "launch").mkdir()
    (output / "config").mkdir()
    (output / "resource").mkdir()
    (output / "resource" / pkg_name).touch()

    # Set up Jinja2
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # ── Identify custom nodes ──
    custom_nodes = [n for n in arch["nodes"] if not n.get("is_standard", False)]
    all_nodes = arch["nodes"]

    # ── Collect message dependencies ──
    msg_deps = set()
    for node in all_nodes:
        for pub in node.get("publishers", []):
            mt = pub.get("msg_type", "")
            if "." in mt:
                msg_deps.add(mt.split(".")[0])
        for sub in node.get("subscribers", []):
            mt = sub.get("msg_type", "")
            if "." in mt:
                msg_deps.add(mt.split(".")[0])
        for act in node.get("action_servers", []) + node.get("action_clients", []):
            for key in ("goal_type", "feedback_type", "result_type"):
                mt = act.get(key, "") or ""
                if "." in mt:
                    msg_deps.add(mt.split(".")[0])
    msg_deps.discard("rclpy")
    msg_deps.discard("")

    # ── Generate package.xml ──
    tmpl = env.get_template("package.xml.j2")
    (output / "package.xml").write_text(
        tmpl.render(pkg_name=pkg_name, system_name=system_name, msg_deps=sorted(msg_deps)))

    # ── Generate setup.py ──
    entry_points = []
    for node in custom_nodes:
        module_name = to_snake_case(node["type_name"]) + "_node"
        executable = to_snake_case(node["type_name"])
        entry_points.append({"executable": executable, "module": module_name})
    entry_points.append({"executable": "conformance_monitor", "module": "conformance_monitor"})
    entry_points.append({"executable": "activate_nodes", "module": "activate_nodes"})

    tmpl = env.get_template("setup_py.j2")
    (output / "setup.py").write_text(
        tmpl.render(pkg_name=pkg_name, system_name=system_name, entry_points=entry_points))

    # ── Generate setup.cfg ──
    tmpl = env.get_template("setup_cfg.j2")
    (output / "setup.cfg").write_text(tmpl.render(pkg_name=pkg_name))

    # ── Generate __init__.py ──
    (pkg_dir / "__init__.py").write_text("")

    # ── Generate node skeletons ──
    node_tmpl = env.get_template("lifecycle_node.py.j2")
    for node in custom_nodes:
        ctx = prepare_node_context(node)
        ctx["wired"] = wired
        module_name = to_snake_case(node["type_name"]) + "_node"
        node_file = pkg_dir / f"{module_name}.py"
        node_file.write_text(node_tmpl.render(**ctx))

    # ── Generate conformance monitor ──
    monitor_tmpl = env.get_template("conformance_monitor.py.j2")

    # Build topic list from all nodes' publishers
    topics = []
    seen_topics = set()
    for node in all_nodes:
        for pub in node.get("publishers", []):
            tn = pub.get("topic_name")
            mt = pub.get("msg_type")
            if tn and tn not in seen_topics:
                topics.append({"name": tn, "msg_type": mt or "unknown"})
                seen_topics.add(tn)

    # Resolve connections to topic-level data for real endpoint verification
    resolved_connections = resolve_connections(arch)

    # Report static QoS compatibility results
    qos_issues = [c for c in resolved_connections if c.get("resolved") and not c.get("qos_compatible")]
    qos_warnings = [c for c in resolved_connections if c.get("resolved") and c.get("qos_compatible") and c.get("qos_warning")]
    if qos_issues:
        print(f"  QoS INCOMPATIBLE: {len(qos_issues)} connection(s) will cause silent data loss:")
        for c in qos_issues:
            print(f"    {c['name']}: {c['qos_warning']}")
    elif qos_warnings:
        print(f"  QoS: {len(qos_warnings)} connection(s) indeterminate (runtime-dependent)")
    else:
        resolved_count = sum(1 for c in resolved_connections if c.get("resolved"))
        print(f"  QoS: all {resolved_count} connections statically compatible")

    # Collect service, action, parameter, and QoS expectations
    services = collect_service_endpoints(arch)
    actions = collect_action_endpoints(arch)
    param_declarations = collect_parameter_declarations(arch)
    qos_expectations = collect_qos_expectations(arch)

    # Build frame list
    frames = arch.get("tf_frames", [])

    # Build node list for monitor
    monitor_nodes = []
    for node in all_nodes:
        monitor_nodes.append({
            "name": node.get("name", node.get("type_name", "")),
            "namespace": node.get("namespace", "/"),
            "lifecycle": node.get("lifecycle", False),
        })

    monitor_file = pkg_dir / "conformance_monitor.py"
    monitor_file.write_text(monitor_tmpl.render(
        system_name=system_name,
        nodes=monitor_nodes,
        topics=topics,
        connections=resolved_connections,
        services=services,
        actions=actions,
        param_declarations=param_declarations,
        qos_expectations=qos_expectations,
        frames=frames,
    ))

    # ── Generate activate_nodes script ──
    activator_tmpl = env.get_template("activate_nodes.py.j2")
    lifecycle_nodes_for_activator = []
    for node in custom_nodes:
        if node.get("lifecycle", False):
            lifecycle_nodes_for_activator.append({
                "name": node.get("name", node["type_name"]),
                "namespace": node.get("namespace", "/"),
            })
    activator_file = pkg_dir / "activate_nodes.py"
    activator_file.write_text(activator_tmpl.render(
        pkg_name=pkg_name, lifecycle_nodes=lifecycle_nodes_for_activator))

    # ── Generate launch file ──
    launch_tmpl = env.get_template("launch.py.j2")
    launch_nodes = []
    for node in custom_nodes:
        launch_nodes.append({
            "instance_var": to_snake_case(node["type_name"]),
            "executable": to_snake_case(node["type_name"]),
            "name": node.get("name", node["type_name"]),
            "namespace": node.get("namespace", "/"),
        })
    launch_file = output / "launch" / f"{pkg_name}.launch.py"
    launch_file.write_text(launch_tmpl.render(
        pkg_name=pkg_name, system_name=system_name, custom_nodes=launch_nodes))

    # ── Generate params.yaml ──
    params_tmpl = env.get_template("params_yaml.j2")
    nodes_with_params = []
    for node in custom_nodes:
        if node.get("parameters"):
            ctx = prepare_node_context(node)
            nodes_with_params.append(ctx["node"])
    params_file = output / "config" / "params.yaml"
    params_file.write_text(params_tmpl.render(
        system_name=system_name, nodes_with_params=nodes_with_params))

    # ── Clean __pycache__ directories (created by py_compile during testing) ──
    for cache_dir in output.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)

    # ── Summary ──
    generated_files = list(output.rglob("*"))
    py_files = [f for f in generated_files if f.suffix == ".py" and f.is_file()]
    print(f"\nGenerated ROS2 package: {output}")
    print(f"  Package name: {pkg_name}")
    print(f"  Custom nodes: {len(custom_nodes)}")
    print(f"  Python files: {len(py_files)}")
    print(f"  Entry points: {len(entry_points)}")
    print(f"  Message deps: {sorted(msg_deps)}")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate a ROS2 package from architecture.json.")
    parser.add_argument("architecture_json",
                        help="Path to architecture.json")
    parser.add_argument("--output", default="generated/ros2_pkg",
                        help="Output directory for the generated package")
    parser.add_argument("--wired", action="store_true",
                        help="Fully-wired mode: seed all endpoints with default data "
                             "for topology verification in rqt_graph")

    args = parser.parse_args()

    with open(args.architecture_json) as f:
        arch = json.load(f)

    generate_package(arch, args.output, wired=args.wired)


if __name__ == "__main__":
    main()
