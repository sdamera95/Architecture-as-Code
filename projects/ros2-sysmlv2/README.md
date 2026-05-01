# ros2-sysmlv2

The first SysML v2 domain library for ROS2 robotics system architectures.

**179 definitions** across **17 source files** covering message types, communication patterns, lifecycle, deployment, TF2, parameters, node archetypes, and the Nav2 navigation stack.

## Installation

```bash
# From local .kpar (development)
sysand add file:///path/to/ros2_sysmlv2-0.1.0-alpha.kpar

# From registry (once published)
sysand add urn:kpar:ros2-sysmlv2
```

## Quick Start

```sysml
package MyRobot {
    private import ros2_sysmlv2_lifecycle::*;
    private import ros2_sysmlv2_comm::*;
    private import ros2_sysmlv2_sensor_msgs::*;
    private import ros2_sysmlv2_archetypes::*;

    part def MyLidarNode :> SensorDriver {
        :>> nodeName = "lidar_driver";
        :>> updateRateHz = 10.0;
        :>> frameId = "lidar_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/scan";
            :>> qos = sensorDataQoS;
            out item :>> msg : LaserScan;
        }
    }
}
```

## Library Structure

| Layer | File(s) | Definitions | Description |
|-------|---------|-------------|-------------|
| Foundation | `foundation.sysml`, `std_msgs.sysml` | 10 | Time, Duration, Header, ColorRGBA, etc. |
| Messages | `geometry_msgs.sysml`, `sensor_msgs.sysml`, `nav_msgs.sysml`, `trajectory_msgs.sysml`, `diagnostic_msgs.sysml`, `shape_msgs.sysml`, `action_msgs.sysml`, `visualization_msgs.sysml` | 100 | 85 ROS2 message types as `item def` |
| Communication | `comm.sysml` | 16 | QoS, TopicPublisher/Subscriber, ServiceServer/Client, ActionServer/Client, connections |
| Lifecycle | `lifecycle.sysml` | 14 | Node, LifecycleNode, LifecycleStates (5 states, 9 event-triggered transitions) |
| Deployment | `deployment.sysml` | 5 | Executor, Container, CallbackGroup, NodeDeployment |
| Parameters | `params.sysml` | 5 | ParameterTypeKind (10 values), ParameterDescriptor, ranges |
| TF2 | `tf2.sysml` | 7 | CoordinateFrame, StaticTransform, DynamicTransform, REP 105 frames |
| Archetypes | `archetypes.sysml` | 8 | 8 abstract node patterns (SensorDriver, Controller, Planner, etc.) |
| Nav2 | `nav2.sysml` | 14 | 11 Nav2 server nodes, Nav2Stack composite, 13 action/message types |

## Mapping Conventions

| SysML v2 | ROS2 |
|----------|------|
| `item def` | `.msg` type |
| `port def` with `out item` | Topic publisher |
| `port def` with `in item` | Topic subscriber |
| `port def` with `in` + `out` items | Service or Action |
| `part def` | Node class |
| `part` usage | Node instance |
| `connection` | Topic/service/action binding |
| `state def` with `transition` | Lifecycle state machine |
| `attribute def` | Parameter type |

## Ground Truth

All definitions are validated against actual ROS2 Jazzy source code:

- **Message types**: field-by-field against `.msg` files from `ros2/common_interfaces` and `ros2/rcl_interfaces`
- **Communication**: against `rclpy/qos.py`, `rclpy/node.py`, `rmw/qos_profiles.h`
- **Lifecycle**: against `lifecycle_msgs/msg/State.msg`, `Transition.msg`, `rclpy/lifecycle/node.py`
- **Parameters**: against `rcl_interfaces/msg/ParameterDescriptor.msg`, `ParameterType.msg`
- **Nav2 nodes**: against Nav2 Jazzy server node C++ source (class inheritance, topic names, action servers)

## Requirements

- [Sysand](https://docs.sysand.org/) >= 0.0.10
- [Syside Editor](https://docs.sensmetry.com/editor/) (free) for authoring
- [Syside Automator](https://docs.sensmetry.com/automator/) (paid) for programmatic access

## License

Apache-2.0

## Authors

Sai Sandeep Damera (sdamera@umd.edu)
University of Maryland, College Park
