// ImuDriverBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in imu_driver_node.cpp.
#include "autonomous_ground_robot/imu_driver_node_base.hpp"

#include <chrono>
#include <functional>

ImuDriverBase::ImuDriverBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("imu", options)
{
  RCLCPP_INFO(get_logger(), "ImuDriver created (unconfigured)");
}

ImuDriverBase::CallbackReturn
ImuDriverBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: sensorPub → /imu/data
  sensorPub_ = create_publisher<sensor_msgs::msg::Imu>(
    "/imu/data", rclcpp::SensorDataQoS());

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

ImuDriverBase::CallbackReturn
ImuDriverBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  sensorPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(100),
    std::bind(&ImuDriverBase::sensorPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

ImuDriverBase::CallbackReturn
ImuDriverBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  sensorPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

ImuDriverBase::CallbackReturn
ImuDriverBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

ImuDriverBase::CallbackReturn
ImuDriverBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void ImuDriverBase::sensorPub_wired_publish()
{
  // Wired-mode publisher for /imu/data — emits default sensor_msgs::msg::Imu.
  sensor_msgs::msg::Imu msg;
  sensorPub_->publish(msg);
}
