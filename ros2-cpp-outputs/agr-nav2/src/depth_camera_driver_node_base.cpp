// DepthCameraDriverBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in depth_camera_driver_node.cpp.
#include "ground_robot_with_nav2/depth_camera_driver_node_base.hpp"

#include <chrono>
#include <functional>

DepthCameraDriverBase::DepthCameraDriverBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("depth_camera", options)
{
  RCLCPP_INFO(get_logger(), "DepthCameraDriver created (unconfigured)");
}

DepthCameraDriverBase::CallbackReturn
DepthCameraDriverBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: sensorPub → /depth/image
  sensorPub_ = create_publisher<sensor_msgs::msg::Image>(
    "/depth/image", rclcpp::SensorDataQoS());

  // Publisher: cameraInfoPub → /depth/camera_info
  cameraInfoPub_ = create_publisher<sensor_msgs::msg::CameraInfo>(
    "/depth/camera_info", rclcpp::QoS(10));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

DepthCameraDriverBase::CallbackReturn
DepthCameraDriverBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  sensorPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(100),
    std::bind(&DepthCameraDriverBase::sensorPub_wired_publish, this));
  cameraInfoPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&DepthCameraDriverBase::cameraInfoPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

DepthCameraDriverBase::CallbackReturn
DepthCameraDriverBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  sensorPub_timer_->cancel();
  cameraInfoPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

DepthCameraDriverBase::CallbackReturn
DepthCameraDriverBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

DepthCameraDriverBase::CallbackReturn
DepthCameraDriverBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void DepthCameraDriverBase::sensorPub_wired_publish()
{
  // Wired-mode publisher for /depth/image — emits default sensor_msgs::msg::Image.
  sensor_msgs::msg::Image msg;
  sensorPub_->publish(msg);
}

void DepthCameraDriverBase::cameraInfoPub_wired_publish()
{
  // Wired-mode publisher for /depth/camera_info — emits default sensor_msgs::msg::CameraInfo.
  sensor_msgs::msg::CameraInfo msg;
  cameraInfoPub_->publish(msg);
}
