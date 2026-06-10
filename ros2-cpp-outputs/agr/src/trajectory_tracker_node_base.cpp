// TrajectoryTrackerBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in trajectory_tracker_node.cpp.
#include "autonomous_ground_robot/trajectory_tracker_node_base.hpp"

#include <chrono>
#include <functional>

TrajectoryTrackerBase::TrajectoryTrackerBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("trajectory_tracker", options)
{
  RCLCPP_INFO(get_logger(), "TrajectoryTracker created (unconfigured)");
}

TrajectoryTrackerBase::CallbackReturn
TrajectoryTrackerBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: commandPub → /cmd_vel
  commandPub_ = create_publisher<geometry_msgs::msg::Twist>(
    "/cmd_vel", rclcpp::QoS(10));

  // Subscriber: stateSub ← /odom_filtered
  stateSub_ = create_subscription<nav_msgs::msg::Odometry>(
    "/odom_filtered", rclcpp::QoS(10),
    std::bind(&TrajectoryTrackerBase::stateSub_callback, this,
              std::placeholders::_1));

  // Subscriber: planSub ← /plan
  planSub_ = create_subscription<nav_msgs::msg::Path>(
    "/plan", rclcpp::QoS(10),
    std::bind(&TrajectoryTrackerBase::planSub_callback, this,
              std::placeholders::_1));

  // Parameter: max_linear_velocity
  declare_parameter("max_linear_velocity", 0.0);

  // Parameter: max_angular_velocity
  declare_parameter("max_angular_velocity", 0.0);

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

TrajectoryTrackerBase::CallbackReturn
TrajectoryTrackerBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  commandPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&TrajectoryTrackerBase::commandPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

TrajectoryTrackerBase::CallbackReturn
TrajectoryTrackerBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  commandPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

TrajectoryTrackerBase::CallbackReturn
TrajectoryTrackerBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

TrajectoryTrackerBase::CallbackReturn
TrajectoryTrackerBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void TrajectoryTrackerBase::stateSub_callback(const nav_msgs::msg::Odometry & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /odom_filtered");
  handle_stateSub(msg);
}

void TrajectoryTrackerBase::planSub_callback(const nav_msgs::msg::Path & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /plan");
  handle_planSub(msg);
}

void TrajectoryTrackerBase::commandPub_wired_publish()
{
  // Wired-mode publisher for /cmd_vel — emits default geometry_msgs::msg::Twist.
  geometry_msgs::msg::Twist msg;
  commandPub_->publish(msg);
}
