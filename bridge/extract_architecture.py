#!/usr/bin/env python3
"""Extract ROS2 architecture from a SysML v2 model.

Reads a user's .sysml model (that imports the ros2-sysmlv2 library) via
Syside Automator and produces a language-agnostic architecture.json.

Usage:
    .venv/bin/python bridge/extract_architecture.py \\
        tests/consumer_test_robot.sysml \\
        --system TestRobot \\
        --library-dir projects/ros2-sysmlv2/ros2_sysmlv2/ \\
        --output architecture.json
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import syside

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ══════════════════════════════════════════════════════════════════════
# SysML package name → ROS2 package name mapping
# ══════════════════════════════════════════════════════════════════════

SYSML_PKG_TO_ROS2 = {
    "ros2_sysmlv2_geometry_msgs": "geometry_msgs",
    "ros2_sysmlv2_sensor_msgs": "sensor_msgs",
    "ros2_sysmlv2_nav_msgs": "nav_msgs",
    "ros2_sysmlv2_std_msgs": "std_msgs",
    "ros2_sysmlv2_trajectory_msgs": "trajectory_msgs",
    "ros2_sysmlv2_diagnostic_msgs": "diagnostic_msgs",
    "ros2_sysmlv2_shape_msgs": "shape_msgs",
    "ros2_sysmlv2_action_msgs": "action_msgs",
    "ros2_sysmlv2_visualization_msgs": "visualization_msgs",
    "ros2_sysmlv2_nav2": "nav2_msgs",
    "ros2_sysmlv2_foundation": "builtin_interfaces",
}

# Nav2 action goal/feedback/result suffixes
ACTION_SUFFIXES = ("Goal", "Feedback", "Result")

# QoS preset lookup (qualified name → profile dict)
QOS_PRESETS = {
    "ros2_sysmlv2_comm::sensorDataQoS": {
        "preset": "sensor_data", "reliability": "best_effort",
        "durability": "volatile", "depth": 5,
    },
    "ros2_sysmlv2_comm::defaultQoS": {
        "preset": "default", "reliability": "reliable",
        "durability": "volatile", "depth": 10,
    },
    "ros2_sysmlv2_comm::servicesDefaultQoS": {
        "preset": "services_default", "reliability": "reliable",
        "durability": "volatile", "depth": 10,
    },
    "ros2_sysmlv2_comm::parametersQoS": {
        "preset": "parameters", "reliability": "reliable",
        "durability": "volatile", "depth": 1000,
    },
    "ros2_sysmlv2_comm::parameterEventsQoS": {
        "preset": "parameter_events", "reliability": "reliable",
        "durability": "volatile", "depth": 1000,
    },
    "ros2_sysmlv2_comm::systemDefaultQoS": {
        "preset": "system_default", "reliability": "system_default",
        "durability": "system_default", "depth": 0,
    },
    "ros2_sysmlv2_comm::bestAvailableQoS": {
        "preset": "best_available", "reliability": "best_available",
        "durability": "best_available", "depth": 10,
    },
}


# ══════════════════════════════════════════════════════════════════════
# Model Loading
# ══════════════════════════════════════════════════════════════════════

def load_model(user_files: list[str], library_dir: str):
    """Load user model + library files, return model and lookup tables."""
    lib_path = Path(library_dir)
    lib_files = sorted(str(f) for f in lib_path.glob("*.sysml"))
    all_files = lib_files + user_files

    print(f"Loading {len(all_files)} files ({len(lib_files)} library + {len(user_files)} user)...")
    model, diag = syside.load_model(all_files)
    if diag.contains_errors():
        print("ERROR: SysML model has parse errors. Check Syside Editor.", file=sys.stderr)
        sys.exit(1)

    # Build lookup tables
    part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}
    port_defs = {n.name: n for n in model.nodes(syside.PortDefinition)}
    item_defs = {}
    for n in model.nodes(syside.ItemDefinition):
        item_defs[n.name] = n

    return model, part_defs, port_defs, item_defs


# ══════════════════════════════════════════════════════════════════════
# Item def → ROS2 import path mapping
# ══════════════════════════════════════════════════════════════════════

def build_msg_type_map(model) -> dict:
    """Build {sysml_item_name: ros2_import_path} mapping."""
    type_map = {}
    for item in model.nodes(syside.ItemDefinition):
        qn = str(item.qualified_name) if item.qualified_name else ""
        if "::" not in qn:
            continue

        pkg_name = qn.split("::")[0]
        item_name = item.name

        ros2_pkg = SYSML_PKG_TO_ROS2.get(pkg_name)
        if not ros2_pkg:
            continue

        # Check if this is a Nav2 action type (Goal/Feedback/Result suffix)
        is_action_part = any(item_name.endswith(s) for s in ACTION_SUFFIXES)
        if is_action_part and ros2_pkg == "nav2_msgs":
            # FollowPathGoal → nav2_msgs.action.FollowPath.Goal
            for suffix in ACTION_SUFFIXES:
                if item_name.endswith(suffix):
                    base = item_name[:-len(suffix)]
                    type_map[item_name] = f"{ros2_pkg}.action.{base}.{suffix}"
                    break
        else:
            type_map[item_name] = f"{ros2_pkg}.msg.{item_name}"

    return type_map


# ══════════════════════════════════════════════════════════════════════
# Attribute / ReferenceUsage value extraction
# ══════════════════════════════════════════════════════════════════════

def extract_ref_value(elem):
    """Extract a scalar value from a ReferenceUsage or AttributeUsage."""
    expr = elem.feature_value_expression
    if expr is None:
        return None
    try:
        result, report = syside.Compiler().evaluate(expr)
        if not report.fatal:
            return result
    except Exception as e:
        name = getattr(elem, 'name', '?')
        log.warning(f"Failed to evaluate expression for '{name}': {e}")
    return None


def get_owned_ref_values(owner) -> dict:
    """Walk owned elements and extract all ReferenceUsage values as {name: value}."""
    values = {}
    for elem in owner.owned_elements.collect():
        if ref := elem.try_cast(syside.ReferenceUsage):
            val = extract_ref_value(ref)
            if val is not None:
                values[ref.name] = val
        elif attr := elem.try_cast(syside.AttributeUsage):
            val = extract_ref_value(attr)
            if val is not None and attr.name:
                values[attr.name] = val
    return values


# ══════════════════════════════════════════════════════════════════════
# Port extraction
# ══════════════════════════════════════════════════════════════════════

PORT_KINDS = {
    "TopicPublisher", "TopicSubscriber",
    "ServiceServer", "ServiceClient",
    "ActionServer", "ActionClient",
}


def classify_port(port_usage, port_defs) -> str | None:
    """Classify a PortUsage by checking its types against known port defs."""
    for pt in port_usage.types.collect():
        if pt.name in PORT_KINDS:
            return pt.name
    return None


def extract_item_type(port_usage, msg_type_map) -> str | None:
    """Extract the concrete message type from a port's item usages."""
    for sub in port_usage.owned_elements.collect():
        if iu := sub.try_cast(syside.ItemUsage):
            for it in iu.types.collect():
                qn = str(it.qualified_name) if it.qualified_name else ""
                if "ros2_sysmlv2" in qn and it.name != "Message":
                    return msg_type_map.get(it.name, it.name)
    return None


def extract_item_types_by_name(port_usage, msg_type_map) -> dict:
    """Extract {item_name: ros2_type} for all item usages in a port."""
    items = {}
    for sub in port_usage.owned_elements.collect():
        if iu := sub.try_cast(syside.ItemUsage):
            name = iu.name
            for it in iu.types.collect():
                qn = str(it.qualified_name) if it.qualified_name else ""
                if "ros2_sysmlv2" in qn and it.name != "Message":
                    items[name] = msg_type_map.get(it.name, it.name)
    return items


def extract_port(port_usage, port_defs, msg_type_map) -> dict | None:
    """Extract a port's full specification."""
    kind = classify_port(port_usage, port_defs)
    if not kind:
        return None

    values = get_owned_ref_values(port_usage)

    port_info = {
        "port_name": port_usage.name,
        "kind": kind,
    }

    if kind in ("TopicPublisher", "TopicSubscriber"):
        port_info["topic_name"] = values.get("topicName")
        port_info["msg_type"] = extract_item_type(port_usage, msg_type_map)
        qos_ref = values.get("qos")
        if qos_ref:
            qos_str = str(qos_ref)
            port_info["qos_preset"] = QOS_PRESETS.get(qos_str, {}).get("preset", qos_str)
        else:
            port_info["qos_preset"] = None

    elif kind in ("ServiceServer", "ServiceClient"):
        port_info["service_name"] = values.get("serviceName")
        items = extract_item_types_by_name(port_usage, msg_type_map)
        port_info["request_type"] = items.get("request")
        port_info["response_type"] = items.get("response")

    elif kind in ("ActionServer", "ActionClient"):
        port_info["action_name"] = values.get("actionName")
        items = extract_item_types_by_name(port_usage, msg_type_map)
        port_info["goal_type"] = items.get("goal")
        port_info["feedback_type"] = items.get("feedback")
        port_info["result_type"] = items.get("result")

    return port_info


# ══════════════════════════════════════════════════════════════════════
# Node extraction
# ══════════════════════════════════════════════════════════════════════

def extract_node(part_def, part_defs, port_defs, msg_type_map) -> dict:
    """Extract a node's full specification from its PartDefinition."""
    node_def = part_defs.get("Node")
    lcn_def = part_defs.get("LifecycleNode")

    values = get_owned_ref_values(part_def)

    # Determine lifecycle flag
    is_lifecycle = lcn_def and part_def.specializes(lcn_def)

    # Determine archetype
    archetype = None
    ARCHETYPE_NAMES = [
        "SensorDriver", "Controller", "Planner", "Estimator",
        "BehaviorCoordinator", "MapProvider", "PerceptionPipeline",
        "VelocityFilter",
    ]
    for arch_name in ARCHETYPE_NAMES:
        if arch_name in part_defs and part_def.specializes(part_defs[arch_name]):
            archetype = arch_name
            break

    # Check if standard (from library nav2 package)
    qn_str = str(part_def.qualified_name) if part_def.qualified_name else ""
    is_standard = qn_str.startswith("ros2_sysmlv2_nav2::")

    # Extract ports
    publishers = []
    subscribers = []
    action_servers = []
    action_clients = []
    service_servers = []
    service_clients = []

    for elem in part_def.owned_elements.collect():
        if pu := elem.try_cast(syside.PortUsage):
            port_info = extract_port(pu, port_defs, msg_type_map)
            if port_info:
                kind = port_info.pop("kind")
                if kind == "TopicPublisher":
                    publishers.append(port_info)
                elif kind == "TopicSubscriber":
                    subscribers.append(port_info)
                elif kind == "ActionServer":
                    action_servers.append(port_info)
                elif kind == "ActionClient":
                    action_clients.append(port_info)
                elif kind == "ServiceServer":
                    service_servers.append(port_info)
                elif kind == "ServiceClient":
                    service_clients.append(port_info)

    # Extract parameters (DeclaredParameter attributes)
    parameters = []
    for elem in part_def.owned_elements.collect():
        if au := elem.try_cast(syside.AttributeUsage):
            # Check if this is a DeclaredParameter
            for at in au.types.collect():
                if at.name == "DeclaredParameter":
                    param_values = get_owned_ref_values(au)
                    # Try to extract default value from nested attribute
                    default_val = None
                    for sub in au.owned_elements.collect():
                        if attr := sub.try_cast(syside.AttributeUsage):
                            if attr.name == "defaultValue":
                                default_val = extract_ref_value(attr)
                    parameters.append({
                        "name": param_values.get("name", au.name),
                        "type": param_values.get("parameterType", "unknown"),
                        "default": default_val,
                    })
                    break

    return {
        "name": values.get("nodeName", part_def.name),
        "type_name": part_def.name,
        "namespace": values.get("namespace", "/"),
        "lifecycle": is_lifecycle,
        "archetype": archetype,
        "is_standard": is_standard,
        "publishers": publishers,
        "subscribers": subscribers,
        "action_servers": action_servers,
        "action_clients": action_clients,
        "service_servers": service_servers,
        "service_clients": service_clients,
        "parameters": parameters,
    }


# ══════════════════════════════════════════════════════════════════════
# System walking: discover nodes, connections, frames
# ══════════════════════════════════════════════════════════════════════

# ROS2-specific connection types from the library
ROS2_CONNECTION_TYPES = {
    "TopicConnection", "ServiceBinding", "ActionBinding",
    "StaticTransform", "DynamicTransform",
}


def walk_system(system_pd, part_defs, port_defs, msg_type_map, prefix=""):
    """Recursively walk a system part def to discover ROS2 nodes, connections, frames.

    Only elements typed against the ros2-sysmlv2 library are extracted.
    Non-ROS2 structural elements (mechanical parts, electrical connections,
    thermal components, etc.) are silently skipped. This allows the SysML v2
    model to contain the full multi-domain system architecture while the
    pipeline extracts only the software/communication layer.
    """
    node_def = part_defs.get("Node")
    lcn_def = part_defs.get("LifecycleNode")
    cf_def = part_defs.get("CoordinateFrame")

    nodes = []
    connections = []
    tf_frames = []
    tf_transforms = []

    for elem in system_pd.owned_elements.collect():
        # ── Part usages (nodes, composites, frames) ──
        if pu := elem.try_cast(syside.PartUsage):
            pu_types = list(pu.types.collect())
            if not pu_types:
                continue
            pu_type = pu_types[0]
            part_path = f"{prefix}{pu.name}" if prefix else pu.name

            # Is it a node?
            is_node = (node_def and pu_type.specializes(node_def))
            # Is it a coordinate frame?
            is_frame = (cf_def and pu_type.specializes(cf_def))

            if is_node:
                node_info = extract_node(pu_type, part_defs, port_defs, msg_type_map)
                node_info["instance_name"] = part_path
                nodes.append(node_info)

            elif is_frame:
                frame_values = get_owned_ref_values(pu)
                # Also check the type def for default frameId
                type_values = get_owned_ref_values(pu_type)
                frame_id = frame_values.get("frameId") or type_values.get("frameId") or pu.name
                tf_frames.append({
                    "name": part_path,
                    "frame_id": frame_id,
                    "type_name": pu_type.name,
                })

            else:
                # Check if it's a composite (has nested parts that are nodes/frames)
                # Recurse into it
                sub_nodes, sub_conns, sub_frames, sub_transforms = walk_system(
                    pu_type, part_defs, port_defs, msg_type_map,
                    prefix=f"{part_path}."
                )
                nodes.extend(sub_nodes)
                connections.extend(sub_conns)
                tf_frames.extend(sub_frames)
                tf_transforms.extend(sub_transforms)

        # ── Connection usages (only ROS2-typed connections) ──
        elif cu := elem.try_cast(syside.ConnectionUsage):
            conn_types = list(cu.types.collect())
            conn_type_name = conn_types[0].name if conn_types else ""
            if conn_type_name in ROS2_CONNECTION_TYPES:
                conn_info = extract_connection(cu, prefix)
                if conn_info:
                    connections.append(conn_info)
            # Non-ROS2 connections (mechanical, electrical, etc.) are skipped

    return nodes, connections, tf_frames, tf_transforms


# ══════════════════════════════════════════════════════════════════════
# Connection extraction
# ══════════════════════════════════════════════════════════════════════

def extract_endpoint_chain(end_feature) -> list[str]:
    """Extract the chaining feature path from a connection end feature."""
    for sub in end_feature.owned_elements.collect():
        try:
            chains = list(sub.chaining_features.collect())
            if chains:
                return [cf.name for cf in chains]
        except (AttributeError, TypeError) as e:
            log.debug(f"Endpoint chain resolution failed for '{end_feature.name}': {e}")
    return []


def extract_connection(conn_usage, prefix="") -> dict | None:
    """Extract a connection's type and endpoints."""
    conn_types = list(conn_usage.types.collect())
    if not conn_types:
        return None

    conn_type = conn_types[0].name  # TopicConnection, StaticTransform, etc.

    # Extract endpoints from end_features
    endpoints = []
    for ef in conn_usage.end_features.collect():
        chain = extract_endpoint_chain(ef)
        endpoints.append({
            "end_name": ef.name,
            "chain": chain,
            "path": ".".join(chain) if chain else ef.name,
        })

    # Determine if this is a TF transform
    is_static = conn_type == "StaticTransform"
    is_dynamic = conn_type == "DynamicTransform"
    is_tf = is_static or is_dynamic

    conn_info = {
        "name": conn_usage.name,
        "connection_type": conn_type,
        "endpoints": endpoints,
    }

    if is_tf and len(endpoints) >= 2:
        conn_info["parent_frame"] = endpoints[0]["path"]
        conn_info["child_frame"] = endpoints[1]["path"]
        conn_info["is_static"] = is_static

    if len(endpoints) >= 2:
        conn_info["source"] = endpoints[0]["path"]
        conn_info["target"] = endpoints[1]["path"]

    return conn_info


# ══════════════════════════════════════════════════════════════════════
# Main pipeline
# ══════════════════════════════════════════════════════════════════════

def extract_architecture(user_files, system_name, library_dir, output_path):
    """Run the full extraction pipeline."""
    model, part_defs, port_defs, item_defs = load_model(user_files, library_dir)
    msg_type_map = build_msg_type_map(model)

    # Find the system part def
    if system_name not in part_defs:
        print(f"ERROR: Part def '{system_name}' not found.", file=sys.stderr)
        print(f"Available part defs: {sorted(part_defs.keys())}", file=sys.stderr)
        sys.exit(1)

    system_pd = part_defs[system_name]
    print(f"Extracting system: {system_name}")

    # Walk the system
    nodes, connections, tf_frames, tf_transforms = walk_system(
        system_pd, part_defs, port_defs, msg_type_map
    )

    # Separate TF transforms from regular connections
    regular_connections = []
    for conn in connections:
        if conn["connection_type"] in ("StaticTransform", "DynamicTransform"):
            tf_transforms.append({
                "name": conn["name"],
                "parent_frame": conn.get("parent_frame", ""),
                "child_frame": conn.get("child_frame", ""),
                "is_static": conn.get("is_static", False),
            })
        else:
            regular_connections.append(conn)

    # Build architecture JSON
    architecture = {
        "metadata": {
            "model_name": system_name,
            "extracted_from": user_files,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "library_version": "0.1.0-alpha",
        },
        "nodes": nodes,
        "connections": regular_connections,
        "tf_frames": tf_frames,
        "tf_transforms": tf_transforms,
    }

    # Write output
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(architecture, f, indent=2, default=str)

    # Summary
    custom_nodes = [n for n in nodes if not n["is_standard"]]
    standard_nodes = [n for n in nodes if n["is_standard"]]
    print(f"\nExtraction complete:")
    print(f"  Nodes: {len(nodes)} ({len(custom_nodes)} custom, {len(standard_nodes)} standard)")
    print(f"  Connections: {len(regular_connections)}")
    print(f"  TF frames: {len(tf_frames)}")
    print(f"  TF transforms: {len(tf_transforms)}")
    print(f"  Output: {output}")

    return architecture


def main():
    parser = argparse.ArgumentParser(
        description="Extract ROS2 architecture from a SysML v2 model."
    )
    parser.add_argument("model_files", nargs="+",
                        help="Path(s) to user .sysml file(s)")
    parser.add_argument("--system", required=True,
                        help="Name of the system PartDefinition to extract")
    parser.add_argument("--library-dir",
                        default="projects/ros2-sysmlv2/ros2_sysmlv2/",
                        help="Path to the ros2-sysmlv2 library directory")
    parser.add_argument("--output", default="architecture.json",
                        help="Output JSON file path")

    args = parser.parse_args()
    extract_architecture(args.model_files, args.system, args.library_dir, args.output)


if __name__ == "__main__":
    main()
