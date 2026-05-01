#!/usr/bin/env python3
"""Activate lifecycle nodes — standalone alternative to nav2_lifecycle_manager.

Usage (after launching nodes):
    ros2 run test_robot activate_nodes

This script calls configure → activate on each lifecycle node in sequence.
Use this if nav2_lifecycle_manager is not installed.
"""
import rclpy
from rclpy.node import Node
from lifecycle_msgs.srv import ChangeState
from lifecycle_msgs.msg import Transition
import time


LIFECYCLE_NODES = [
    ('lidar_driver', '/sensors'),
    ('my_controller', '/'),
]


def call_transition(caller: Node, node_name: str, namespace: str, transition_id: int):
    """Call ChangeState service on a lifecycle node."""
    ns = namespace.rstrip('/')
    service_name = f'{ns}/{node_name}/change_state' if ns else f'/{node_name}/change_state'
    client = caller.create_client(ChangeState, service_name)

    if not client.wait_for_service(timeout_sec=5.0):
        caller.get_logger().warn(f'Service {service_name} not available')
        return False

    req = ChangeState.Request()
    req.transition.id = transition_id
    future = client.call_async(req)
    rclpy.spin_until_future_complete(caller, future, timeout_sec=5.0)

    if future.result() is not None and future.result().success:
        return True
    else:
        caller.get_logger().warn(f'Transition {transition_id} failed on {service_name}')
        return False


def main(args=None):
    rclpy.init(args=args)
    caller = Node('lifecycle_activator')

    succeeded = 0
    failed = 0
    for node_name, namespace in LIFECYCLE_NODES:
        caller.get_logger().info(f'Configuring {namespace}/{node_name}...')
        if call_transition(caller, node_name, namespace, Transition.TRANSITION_CONFIGURE):
            time.sleep(0.5)
            caller.get_logger().info(f'Activating {namespace}/{node_name}...')
            if call_transition(caller, node_name, namespace, Transition.TRANSITION_ACTIVATE):
                succeeded += 1
            else:
                failed += 1
        else:
            failed += 1
        time.sleep(0.5)

    if failed == 0:
        caller.get_logger().info(f'All {succeeded} nodes activated successfully.')
    else:
        caller.get_logger().warn(f'{failed} nodes failed, {succeeded} activated.')
    caller.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
