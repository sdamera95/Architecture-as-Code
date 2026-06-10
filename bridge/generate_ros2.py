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

# QoS preset names → rclcpp constructor expressions. `best_available` maps to
# QoS(10) (not rclcpp::BestAvailableQoS) deliberately: the rclpy side maps it to
# depth-10 default, so both languages exhibit identical wire QoS and satisfy the
# monitor's QOS_PRESET_PROPERTIES expectations.
QOS_PRESETS_RCLCPP = {
    "sensor_data": "rclcpp::SensorDataQoS()",
    "default": "rclcpp::QoS(10)",
    "services_default": "rclcpp::ServicesQoS()",
    "parameters": "rclcpp::ParametersQoS()",
    "parameter_events": "rclcpp::ParameterEventsQoS()",
    "system_default": "rclcpp::SystemDefaultsQoS()",
    "best_available": "rclcpp::QoS(10)",
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
    """Convert CamelCase to snake_case.

    NOTE: splits before EVERY capital (EKFLocalizer -> e_k_f_localizer). Kept
    as-is for module/executable names so Python and C++ executables match and
    the shared launch template needs no changes. NOT suitable for C++ message
    header derivation — use rosidl_snake_case for that.
    """
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return s


def rosidl_snake_case(name: str) -> str:
    """CamelCase message name -> header basename, using the exact rosidl rule
    (rosidl_pycommon.convert_camel_case_to_lower_case_underscore):
    acronym/word boundaries split once (TFMessage -> tf_message), digits attach
    (PointCloud2 -> point_cloud2). Deliberately NOT to_snake_case, which would
    produce t_f_message and break the generated #include paths."""
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower()


def msg_type_to_cpp(msg_type_str: str) -> dict:
    """'sensor_msgs.msg.LaserScan' -> {'cpp_type': 'sensor_msgs::msg::LaserScan',
    'include': 'sensor_msgs/msg/laser_scan.hpp', 'package': 'sensor_msgs'}.
    Generic over package.kind.Type[.Sub] so action sub-types work if the IR
    ever fills them (include derives from the Type segment only)."""
    parts = msg_type_str.split(".")
    if len(parts) < 3:
        return {"cpp_type": msg_type_str, "include": "", "package": ""}
    package, kind, type_name = parts[0], parts[1], parts[2]
    cpp_type = "::".join(parts)
    include = f"{package}/{kind}/{rosidl_snake_case(type_name)}.hpp"
    return {"cpp_type": cpp_type, "include": include, "package": package}


def param_default_cpp(param_type: str, default) -> str:
    """C++ literal for declare_parameter, mirroring the Python type-substring
    branches in prepare_node_context."""
    if default is None:
        if "Double" in param_type:
            return "0.0"
        if "Integer" in param_type:
            return "0"
        if "Bool" in param_type:
            return "false"
        if "String" in param_type:
            return 'std::string("")'
        return "0.0  /* TODO: unknown parameter type */"
    if isinstance(default, bool):
        return "true" if default else "false"
    if isinstance(default, float):
        s = repr(default)
        return s if "." in s or "e" in s else s + ".0"
    if isinstance(default, int):
        return str(default)
    escaped = str(default).replace("\\", "\\\\").replace('"', '\\"')
    return f'std::string("{escaped}")'


def write_if_absent(path: Path, text: str) -> bool:
    """Generation-gap guard: write only when the file does not exist.
    Returns True if written."""
    if path.exists():
        return False
    path.write_text(text)
    return True


def prepare_node_context(node: dict, lang: str = "py") -> dict:
    """Prepare a node dict for template rendering with resolved imports and class names."""
    imports = set()
    qos_symbols_used = set()
    cpp_includes = set()

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
            pub["wired_period_ms"] = 100
        else:
            pub["wired_period"] = "1.0"  # 1 Hz
            pub["wired_period_ms"] = 1000

        if lang == "cpp" and pub.get("msg_type"):
            cpp = msg_type_to_cpp(pub["msg_type"])
            pub["cpp_type"] = cpp["cpp_type"]
            cpp_includes.add(cpp["include"])
            pub["cpp_qos_arg"] = QOS_PRESETS_RCLCPP.get(preset, "rclcpp::QoS(10)") if preset else "rclcpp::QoS(10)"

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

        if lang == "cpp" and sub.get("msg_type"):
            cpp = msg_type_to_cpp(sub["msg_type"])
            sub["cpp_type"] = cpp["cpp_type"]
            cpp_includes.add(cpp["include"])
            sub["cpp_qos_arg"] = QOS_PRESETS_RCLCPP.get(preset, "rclcpp::QoS(10)") if preset else "rclcpp::QoS(10)"

    # Process parameters
    for param in node.get("parameters", []):
        default = param.get("default")
        param_type = str(param.get("type", ""))
        if default is None:
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
        if lang == "cpp":
            param["cpp_default"] = param_default_cpp(param_type, default)

    # Add QoS import with only the profiles actually used
    if qos_symbols_used:
        imports.add(f"from rclpy.qos import {', '.join(sorted(qos_symbols_used))}")

    return {
        "node": node,
        "imports": sorted(imports),
        "cpp_includes": sorted(cpp_includes),
    }


def _emit_py_sources(env, output, pkg_dir, pkg_name, system_name,
                     custom_nodes, msg_deps, wired) -> tuple[list, int]:
    """ament_python build files + gen-gap node sources. Returns (entry_points, n_impl_preserved)."""
    tmpl = env.get_template("package.xml.j2")
    (output / "package.xml").write_text(
        tmpl.render(pkg_name=pkg_name, system_name=system_name, msg_deps=sorted(msg_deps)))

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
    tmpl = env.get_template("setup_cfg.j2")
    (output / "setup.cfg").write_text(tmpl.render(pkg_name=pkg_name))
    (pkg_dir / "__init__.py").write_text("")

    # Generation gap: the *_node_base.py wiring is rewritten on every run;
    # the derived *_node.py (demo logic + main) is generated only if absent.
    base_tmpl = env.get_template("node_base.py.j2")
    impl_tmpl = env.get_template("node_impl.py.j2")
    preserved = 0
    for node in custom_nodes:
        ctx = prepare_node_context(node)
        ctx["wired"] = wired
        module_name = to_snake_case(node["type_name"]) + "_node"
        ctx["module_name"] = module_name
        (pkg_dir / f"{module_name}_base.py").write_text(base_tmpl.render(**ctx))
        if not write_if_absent(pkg_dir / f"{module_name}.py", impl_tmpl.render(**ctx)):
            preserved += 1
    return entry_points, preserved


def _emit_cpp_sources(env, output, pkg_name, system_name,
                      custom_nodes, msg_deps, custom_msg_deps, wired) -> tuple[list, int]:
    """ament_cmake build files + gen-gap C++ node sources. Returns (executables, n_impl_preserved)."""
    (output / "src").mkdir(parents=True, exist_ok=True)
    (output / "include" / pkg_name).mkdir(parents=True, exist_ok=True)
    (output / "scripts").mkdir(parents=True, exist_ok=True)

    hpp_tmpl = env.get_template("node_base.hpp.j2")
    base_tmpl = env.get_template("node_base.cpp.j2")
    impl_tmpl = env.get_template("node_impl.cpp.j2")
    executables = []
    preserved = 0
    for node in custom_nodes:
        ctx = prepare_node_context(node, lang="cpp")
        ctx["wired"] = wired
        ctx["pkg_name"] = pkg_name
        module_name = to_snake_case(node["type_name"]) + "_node"
        ctx["module_name"] = module_name
        executables.append({"executable": to_snake_case(node["type_name"]),
                            "module": module_name})
        (output / "include" / pkg_name / f"{module_name}_base.hpp").write_text(
            hpp_tmpl.render(**ctx))
        (output / "src" / f"{module_name}_base.cpp").write_text(base_tmpl.render(**ctx))
        if not write_if_absent(output / "src" / f"{module_name}.cpp", impl_tmpl.render(**ctx)):
            preserved += 1

    tmpl = env.get_template("package_cmake.xml.j2")
    (output / "package.xml").write_text(
        tmpl.render(pkg_name=pkg_name, system_name=system_name,
                    msg_deps=sorted(msg_deps), custom_msg_deps=sorted(custom_msg_deps)))
    tmpl = env.get_template("CMakeLists.txt.j2")
    (output / "CMakeLists.txt").write_text(
        tmpl.render(pkg_name=pkg_name, executables=executables,
                    custom_msg_deps=sorted(custom_msg_deps)))
    return executables, preserved


def generate_package(arch: dict, output_dir: str, wired: bool = False,
                     lang: str = "py", force: bool = False):
    """Generate a complete ROS2 package (ament_python or ament_cmake).

    Args:
        arch: Architecture dict from extract_architecture.py.
        output_dir: Output directory for the generated package.
        wired: If True, fully-wired mode: seed all publishers with periodic
               default messages and all subscribers with logging callbacks,
               so the complete topology is verifiable before implementing
               real callback logic.
        lang: "py" (ament_python, rclpy) or "cpp" (ament_cmake, rclcpp_lifecycle).
        force: Delete the output directory first, discarding any hand-written
               derived node implementations (generation-gap files).
    """
    system_name = arch["metadata"]["model_name"]
    pkg_name = to_snake_case(system_name)

    if wired:
        print("  Mode: FULLY-WIRED (all endpoints seeded with default data)")

    output = Path(output_dir)

    # Generation gap: only --force wipes the tree (hand-written derived
    # implementations survive ordinary regeneration).
    if force and output.exists():
        shutil.rmtree(output)

    pkg_dir = output / pkg_name
    if lang == "py":
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (output / "resource").mkdir(exist_ok=True)
        (output / "resource" / pkg_name).touch()
    else:
        output.mkdir(parents=True, exist_ok=True)
    (output / "launch").mkdir(exist_ok=True)
    (output / "config").mkdir(exist_ok=True)

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

    # C++ compile deps: only what the generated node sources actually #include
    # (custom-node pubs/subs); the full msg_deps set stays in package.xml.
    custom_msg_deps = set()
    for node in custom_nodes:
        for ep in node.get("publishers", []) + node.get("subscribers", []):
            mt = ep.get("msg_type", "")
            if "." in mt:
                custom_msg_deps.add(mt.split(".")[0])

    # ── Build files + node sources (per language) ──
    if lang == "py":
        entry_points, preserved = _emit_py_sources(
            env, output, pkg_dir, pkg_name, system_name, custom_nodes, msg_deps, wired)
    else:
        entry_points, preserved = _emit_cpp_sources(
            env, output, pkg_name, system_name, custom_nodes, msg_deps, custom_msg_deps, wired)

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

    monitor_text = monitor_tmpl.render(
        system_name=system_name,
        nodes=monitor_nodes,
        topics=topics,
        connections=resolved_connections,
        services=services,
        actions=actions,
        param_declarations=param_declarations,
        qos_expectations=qos_expectations,
        frames=frames,
    )
    # The monitor is language-neutral Python (graph introspection only): the same
    # script ships inside the py package and as an installed program in the cpp
    # package, so one monitor validates both implementations identically.
    if lang == "py":
        (pkg_dir / "conformance_monitor.py").write_text(monitor_text)
    else:
        monitor_file = output / "scripts" / "conformance_monitor"
        monitor_file.write_text(monitor_text)
        monitor_file.chmod(0o755)

    # ── Generate requirements report (Tier 1 design-time evaluation, Syside 0.9.0) ──
    requirements = arch.get("requirements", [])
    if requirements:
        req_tmpl = env.get_template("requirements_report.md.j2")
        req_report = output / "requirements_report.md"
        req_report.write_text(req_tmpl.render(
            system_name=system_name,
            requirements=requirements,
            # Reuse the extraction timestamp: the report documents that
            # extraction's Tier 1 evaluation, and this keeps regeneration
            # deterministic (no fresh now() on content-identical reruns).
            timestamp=arch["metadata"]["extraction_timestamp"],
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
    activator_text = activator_tmpl.render(
        pkg_name=pkg_name, lifecycle_nodes=lifecycle_nodes_for_activator)
    if lang == "py":
        (pkg_dir / "activate_nodes.py").write_text(activator_text)
    else:
        activator_file = output / "scripts" / "activate_nodes"
        activator_file.write_text(activator_text)
        activator_file.chmod(0o755)

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
    generated_files = [f for f in output.rglob("*") if f.is_file()]
    src_files = [f for f in generated_files
                 if f.suffix in (".py", ".cpp", ".hpp")]
    print(f"\nGenerated ROS2 package: {output}")
    print(f"  Package name: {pkg_name}")
    print(f"  Language: {lang}")
    print(f"  Custom nodes: {len(custom_nodes)}")
    print(f"  Source files: {len(src_files)}")
    print(f"  Entry points: {len(entry_points)}")
    print(f"  Message deps: {sorted(msg_deps)}")
    if preserved:
        print(f"  Preserved {preserved} existing node implementation file(s) "
              f"(generation gap; use force=True to reset)")

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
    parser.add_argument("--lang", choices=["py", "cpp"], default="py",
                        help="Target implementation language (default: py)")
    parser.add_argument("--force", action="store_true",
                        help="Wipe the output directory first, discarding hand-written "
                             "node implementations (generation-gap files)")

    args = parser.parse_args()

    with open(args.architecture_json) as f:
        arch = json.load(f)

    generate_package(arch, args.output, wired=args.wired, lang=args.lang, force=args.force)


if __name__ == "__main__":
    main()
