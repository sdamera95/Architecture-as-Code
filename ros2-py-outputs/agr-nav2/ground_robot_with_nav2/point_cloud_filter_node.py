"""PointCloudFilter — node implementation. EDIT ME.

Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
(generation-gap pattern): this file is where demo/application logic lives.
The architectural wiring (endpoints, parameters, lifecycle transitions) is in
point_cloud_filter_node_base.py, which is regenerated on every pipeline run.
"""
import rclpy

from .point_cloud_filter_node_base import PointCloudFilterBase


class PointCloudFilter(PointCloudFilterBase):
    """pointcloud_filter application logic."""

    def handle_rawSub(self, msg) -> None:
        """/depth/image (Image).

        TODO: implement message processing logic.
        """


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudFilter()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
