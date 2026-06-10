// Nav2LidarDriverBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in nav2_lidar_driver_node.cpp.
#include "ground_robot_with_nav2/nav2_lidar_driver_node_base.hpp"

#include <chrono>
#include <functional>

Nav2LidarDriverBase::Nav2LidarDriverBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("lidar", options)
{
  RCLCPP_INFO(get_logger(), "Nav2LidarDriver created (unconfigured)");
}

Nav2LidarDriverBase::CallbackReturn
Nav2LidarDriverBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: sensorPub → /scan
  sensorPub_ = create_publisher<sensor_msgs::msg::LaserScan>(
    "/scan", rclcpp::SensorDataQoS());

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

Nav2LidarDriverBase::CallbackReturn
Nav2LidarDriverBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  sensorPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(100),
    std::bind(&Nav2LidarDriverBase::sensorPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

Nav2LidarDriverBase::CallbackReturn
Nav2LidarDriverBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  sensorPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

Nav2LidarDriverBase::CallbackReturn
Nav2LidarDriverBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

Nav2LidarDriverBase::CallbackReturn
Nav2LidarDriverBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void Nav2LidarDriverBase::sensorPub_wired_publish()
{
  // Wired-mode publisher for /scan — emits default sensor_msgs::msg::LaserScan.
  sensor_msgs::msg::LaserScan msg;
  sensorPub_->publish(msg);
}
