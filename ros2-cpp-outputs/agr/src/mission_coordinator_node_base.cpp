// MissionCoordinatorBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in mission_coordinator_node.cpp.
#include "autonomous_ground_robot/mission_coordinator_node_base.hpp"

#include <chrono>
#include <functional>

MissionCoordinatorBase::MissionCoordinatorBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("mission_coordinator", options)
{
  RCLCPP_INFO(get_logger(), "MissionCoordinator created (unconfigured)");
}

MissionCoordinatorBase::CallbackReturn
MissionCoordinatorBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: statusPub → /mission_status
  statusPub_ = create_publisher<nav_msgs::msg::Path>(
    "/mission_status", rclcpp::QoS(10));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

MissionCoordinatorBase::CallbackReturn
MissionCoordinatorBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  statusPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&MissionCoordinatorBase::statusPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

MissionCoordinatorBase::CallbackReturn
MissionCoordinatorBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  statusPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

MissionCoordinatorBase::CallbackReturn
MissionCoordinatorBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

MissionCoordinatorBase::CallbackReturn
MissionCoordinatorBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void MissionCoordinatorBase::statusPub_wired_publish()
{
  // Wired-mode publisher for /mission_status — emits default nav_msgs::msg::Path.
  nav_msgs::msg::Path msg;
  statusPub_->publish(msg);
}
