// EKFLocalizerBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in e_k_f_localizer_node.cpp.
#include "autonomous_ground_robot/e_k_f_localizer_node_base.hpp"

#include <chrono>
#include <functional>

EKFLocalizerBase::EKFLocalizerBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("ekf_localizer", options)
{
  RCLCPP_INFO(get_logger(), "EKFLocalizer created (unconfigured)");
}

EKFLocalizerBase::CallbackReturn
EKFLocalizerBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: posePub → /odom_filtered
  posePub_ = create_publisher<nav_msgs::msg::Odometry>(
    "/odom_filtered", rclcpp::QoS(10));

  // Subscriber: sensorSub ← /imu/data
  sensorSub_ = create_subscription<sensor_msgs::msg::Imu>(
    "/imu/data", rclcpp::QoS(10),
    std::bind(&EKFLocalizerBase::sensorSub_callback, this,
              std::placeholders::_1));

  // Subscriber: scanSub ← /scan
  scanSub_ = create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan", rclcpp::QoS(10),
    std::bind(&EKFLocalizerBase::scanSub_callback, this,
              std::placeholders::_1));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

EKFLocalizerBase::CallbackReturn
EKFLocalizerBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  posePub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&EKFLocalizerBase::posePub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

EKFLocalizerBase::CallbackReturn
EKFLocalizerBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  posePub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

EKFLocalizerBase::CallbackReturn
EKFLocalizerBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

EKFLocalizerBase::CallbackReturn
EKFLocalizerBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void EKFLocalizerBase::sensorSub_callback(const sensor_msgs::msg::Imu & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /imu/data");
  handle_sensorSub(msg);
}

void EKFLocalizerBase::scanSub_callback(const sensor_msgs::msg::LaserScan & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /scan");
  handle_scanSub(msg);
}

void EKFLocalizerBase::posePub_wired_publish()
{
  // Wired-mode publisher for /odom_filtered — emits default nav_msgs::msg::Odometry.
  nav_msgs::msg::Odometry msg;
  posePub_->publish(msg);
}
