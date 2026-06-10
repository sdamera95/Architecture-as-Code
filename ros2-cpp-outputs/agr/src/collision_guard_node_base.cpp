// CollisionGuardBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in collision_guard_node.cpp.
#include "autonomous_ground_robot/collision_guard_node_base.hpp"

#include <chrono>
#include <functional>

CollisionGuardBase::CollisionGuardBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("collision_guard", options)
{
  RCLCPP_INFO(get_logger(), "CollisionGuard created (unconfigured)");
}

CollisionGuardBase::CallbackReturn
CollisionGuardBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: cmdVelOut → /cmd_vel_out
  cmdVelOut_ = create_publisher<geometry_msgs::msg::Twist>(
    "/cmd_vel_out", rclcpp::QoS(10));

  // Subscriber: cmdVelIn ← /cmd_vel_smooth
  cmdVelIn_ = create_subscription<geometry_msgs::msg::Twist>(
    "/cmd_vel_smooth", rclcpp::SystemDefaultsQoS(),
    std::bind(&CollisionGuardBase::cmdVelIn_callback, this,
              std::placeholders::_1));

  // Subscriber: scanSub ← /scan
  scanSub_ = create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan", rclcpp::SensorDataQoS(),
    std::bind(&CollisionGuardBase::scanSub_callback, this,
              std::placeholders::_1));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

CollisionGuardBase::CallbackReturn
CollisionGuardBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  cmdVelOut_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&CollisionGuardBase::cmdVelOut_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

CollisionGuardBase::CallbackReturn
CollisionGuardBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  cmdVelOut_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

CollisionGuardBase::CallbackReturn
CollisionGuardBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

CollisionGuardBase::CallbackReturn
CollisionGuardBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void CollisionGuardBase::cmdVelIn_callback(const geometry_msgs::msg::Twist & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /cmd_vel_smooth");
  handle_cmdVelIn(msg);
}

void CollisionGuardBase::scanSub_callback(const sensor_msgs::msg::LaserScan & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /scan");
  handle_scanSub(msg);
}

void CollisionGuardBase::cmdVelOut_wired_publish()
{
  // Wired-mode publisher for /cmd_vel_out — emits default geometry_msgs::msg::Twist.
  geometry_msgs::msg::Twist msg;
  cmdVelOut_->publish(msg);
}
