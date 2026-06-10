// PointCloudFilterBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in point_cloud_filter_node.cpp.
#include "ground_robot_with_nav2/point_cloud_filter_node_base.hpp"

#include <chrono>
#include <functional>

PointCloudFilterBase::PointCloudFilterBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("pointcloud_filter", options)
{
  RCLCPP_INFO(get_logger(), "PointCloudFilter created (unconfigured)");
}

PointCloudFilterBase::CallbackReturn
PointCloudFilterBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: processedPub → /filtered_cloud
  processedPub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
    "/filtered_cloud", rclcpp::QoS(10));

  // Subscriber: rawSub ← /depth/image
  rawSub_ = create_subscription<sensor_msgs::msg::Image>(
    "/depth/image", rclcpp::QoS(10),
    std::bind(&PointCloudFilterBase::rawSub_callback, this,
              std::placeholders::_1));

  // Parameter: voxel_size
  declare_parameter("voxel_size", 0.0);

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

PointCloudFilterBase::CallbackReturn
PointCloudFilterBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  processedPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&PointCloudFilterBase::processedPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

PointCloudFilterBase::CallbackReturn
PointCloudFilterBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  processedPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

PointCloudFilterBase::CallbackReturn
PointCloudFilterBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

PointCloudFilterBase::CallbackReturn
PointCloudFilterBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void PointCloudFilterBase::rawSub_callback(const sensor_msgs::msg::Image & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /depth/image");
  handle_rawSub(msg);
}

void PointCloudFilterBase::processedPub_wired_publish()
{
  // Wired-mode publisher for /filtered_cloud — emits default sensor_msgs::msg::PointCloud2.
  sensor_msgs::msg::PointCloud2 msg;
  processedPub_->publish(msg);
}
