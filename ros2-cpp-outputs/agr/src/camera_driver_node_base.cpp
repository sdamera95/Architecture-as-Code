// CameraDriverBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in camera_driver_node.cpp.
#include "autonomous_ground_robot/camera_driver_node_base.hpp"

#include <chrono>
#include <functional>

CameraDriverBase::CameraDriverBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("camera", options)
{
  RCLCPP_INFO(get_logger(), "CameraDriver created (unconfigured)");
}

CameraDriverBase::CallbackReturn
CameraDriverBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: sensorPub → /camera/image
  sensorPub_ = create_publisher<sensor_msgs::msg::Image>(
    "/camera/image", rclcpp::SensorDataQoS());

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

CameraDriverBase::CallbackReturn
CameraDriverBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  sensorPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(100),
    std::bind(&CameraDriverBase::sensorPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

CameraDriverBase::CallbackReturn
CameraDriverBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  sensorPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

CameraDriverBase::CallbackReturn
CameraDriverBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

CameraDriverBase::CallbackReturn
CameraDriverBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void CameraDriverBase::sensorPub_wired_publish()
{
  // Wired-mode publisher for /camera/image — emits default sensor_msgs::msg::Image.
  sensor_msgs::msg::Image msg;
  sensorPub_->publish(msg);
}
