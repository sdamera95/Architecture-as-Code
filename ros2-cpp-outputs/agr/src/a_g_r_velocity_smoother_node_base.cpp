// AGRVelocitySmootherBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in a_g_r_velocity_smoother_node.cpp.
#include "autonomous_ground_robot/a_g_r_velocity_smoother_node_base.hpp"

#include <chrono>
#include <functional>

AGRVelocitySmootherBase::AGRVelocitySmootherBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("velocity_smoother", options)
{
  RCLCPP_INFO(get_logger(), "AGRVelocitySmoother created (unconfigured)");
}

AGRVelocitySmootherBase::CallbackReturn
AGRVelocitySmootherBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: cmdVelOut → /cmd_vel_smooth
  cmdVelOut_ = create_publisher<geometry_msgs::msg::Twist>(
    "/cmd_vel_smooth", rclcpp::SystemDefaultsQoS());

  // Subscriber: cmdVelIn ← /cmd_vel
  cmdVelIn_ = create_subscription<geometry_msgs::msg::Twist>(
    "/cmd_vel", rclcpp::QoS(10),
    std::bind(&AGRVelocitySmootherBase::cmdVelIn_callback, this,
              std::placeholders::_1));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

AGRVelocitySmootherBase::CallbackReturn
AGRVelocitySmootherBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  cmdVelOut_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&AGRVelocitySmootherBase::cmdVelOut_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

AGRVelocitySmootherBase::CallbackReturn
AGRVelocitySmootherBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  cmdVelOut_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

AGRVelocitySmootherBase::CallbackReturn
AGRVelocitySmootherBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

AGRVelocitySmootherBase::CallbackReturn
AGRVelocitySmootherBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void AGRVelocitySmootherBase::cmdVelIn_callback(const geometry_msgs::msg::Twist & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /cmd_vel");
  handle_cmdVelIn(msg);
}

void AGRVelocitySmootherBase::cmdVelOut_wired_publish()
{
  // Wired-mode publisher for /cmd_vel_smooth — emits default geometry_msgs::msg::Twist.
  geometry_msgs::msg::Twist msg;
  cmdVelOut_->publish(msg);
}
