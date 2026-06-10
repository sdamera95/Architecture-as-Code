"""Nav2LidarDriver — node implementation. EDIT ME.

Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
(generation-gap pattern): this file is where demo/application logic lives.
The architectural wiring (endpoints, parameters, lifecycle transitions) is in
nav2_lidar_driver_node_base.py, which is regenerated on every pipeline run.
"""
import rclpy

from .nav2_lidar_driver_node_base import Nav2LidarDriverBase


class Nav2LidarDriver(Nav2LidarDriverBase):
    """lidar application logic."""

    # Override on_configure_hook / on_activate_hook / on_deactivate_hook here.


def main(args=None):
    rclpy.init(args=args)
    node = Nav2LidarDriver()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
