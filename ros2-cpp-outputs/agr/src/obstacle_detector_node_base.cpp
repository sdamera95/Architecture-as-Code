// ObstacleDetectorBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in obstacle_detector_node.cpp.
#include "autonomous_ground_robot/obstacle_detector_node_base.hpp"

#include <chrono>
#include <functional>

ObstacleDetectorBase::ObstacleDetectorBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("obstacle_detector", options)
{
  RCLCPP_INFO(get_logger(), "ObstacleDetector created (unconfigured)");
}

ObstacleDetectorBase::CallbackReturn
ObstacleDetectorBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: processedPub → /detections
  processedPub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
    "/detections", rclcpp::QoS(10));

  // Subscriber: rawSub ← /scan
  rawSub_ = create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan", rclcpp::SensorDataQoS(),
    std::bind(&ObstacleDetectorBase::rawSub_callback, this,
              std::placeholders::_1));

  // Subscriber: cameraSub ← /camera/image
  cameraSub_ = create_subscription<sensor_msgs::msg::Image>(
    "/camera/image", rclcpp::SensorDataQoS(),
    std::bind(&ObstacleDetectorBase::cameraSub_callback, this,
              std::placeholders::_1));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

ObstacleDetectorBase::CallbackReturn
ObstacleDetectorBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  processedPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&ObstacleDetectorBase::processedPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

ObstacleDetectorBase::CallbackReturn
ObstacleDetectorBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  processedPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

ObstacleDetectorBase::CallbackReturn
ObstacleDetectorBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

ObstacleDetectorBase::CallbackReturn
ObstacleDetectorBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void ObstacleDetectorBase::rawSub_callback(const sensor_msgs::msg::LaserScan & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /scan");
  handle_rawSub(msg);
}

void ObstacleDetectorBase::cameraSub_callback(const sensor_msgs::msg::Image & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /camera/image");
  handle_cameraSub(msg);
}

void ObstacleDetectorBase::processedPub_wired_publish()
{
  // Wired-mode publisher for /detections — emits default sensor_msgs::msg::PointCloud2.
  sensor_msgs::msg::PointCloud2 msg;
  processedPub_->publish(msg);
}
