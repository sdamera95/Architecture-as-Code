// Nav2EKFLocalizerBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in nav2_e_k_f_localizer_node.cpp.
#include "ground_robot_with_nav2/nav2_e_k_f_localizer_node_base.hpp"

#include <chrono>
#include <functional>

Nav2EKFLocalizerBase::Nav2EKFLocalizerBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("ekf_localizer", options)
{
  RCLCPP_INFO(get_logger(), "Nav2EKFLocalizer created (unconfigured)");
}

Nav2EKFLocalizerBase::CallbackReturn
Nav2EKFLocalizerBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: posePub → /odom
  posePub_ = create_publisher<nav_msgs::msg::Odometry>(
    "/odom", rclcpp::QoS(10));

  // Publisher: poseCovPub → /amcl_pose
  poseCovPub_ = create_publisher<geometry_msgs::msg::PoseWithCovarianceStamped>(
    "/amcl_pose", rclcpp::QoS(10));

  // Subscriber: sensorSub ← /imu/data
  sensorSub_ = create_subscription<sensor_msgs::msg::Imu>(
    "/imu/data", rclcpp::QoS(10),
    std::bind(&Nav2EKFLocalizerBase::sensorSub_callback, this,
              std::placeholders::_1));

  // Subscriber: scanSub ← /scan
  scanSub_ = create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan", rclcpp::QoS(10),
    std::bind(&Nav2EKFLocalizerBase::scanSub_callback, this,
              std::placeholders::_1));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

Nav2EKFLocalizerBase::CallbackReturn
Nav2EKFLocalizerBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  posePub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&Nav2EKFLocalizerBase::posePub_wired_publish, this));
  poseCovPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&Nav2EKFLocalizerBase::poseCovPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

Nav2EKFLocalizerBase::CallbackReturn
Nav2EKFLocalizerBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  posePub_timer_->cancel();
  poseCovPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

Nav2EKFLocalizerBase::CallbackReturn
Nav2EKFLocalizerBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

Nav2EKFLocalizerBase::CallbackReturn
Nav2EKFLocalizerBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void Nav2EKFLocalizerBase::sensorSub_callback(const sensor_msgs::msg::Imu & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /imu/data");
  handle_sensorSub(msg);
}

void Nav2EKFLocalizerBase::scanSub_callback(const sensor_msgs::msg::LaserScan & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /scan");
  handle_scanSub(msg);
}

void Nav2EKFLocalizerBase::posePub_wired_publish()
{
  // Wired-mode publisher for /odom — emits default nav_msgs::msg::Odometry.
  nav_msgs::msg::Odometry msg;
  posePub_->publish(msg);
}

void Nav2EKFLocalizerBase::poseCovPub_wired_publish()
{
  // Wired-mode publisher for /amcl_pose — emits default geometry_msgs::msg::PoseWithCovarianceStamped.
  geometry_msgs::msg::PoseWithCovarianceStamped msg;
  poseCovPub_->publish(msg);
}
