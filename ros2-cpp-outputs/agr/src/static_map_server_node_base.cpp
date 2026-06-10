// StaticMapServerBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in static_map_server_node.cpp.
#include "autonomous_ground_robot/static_map_server_node_base.hpp"

#include <chrono>
#include <functional>

StaticMapServerBase::StaticMapServerBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("map_server", options)
{
  RCLCPP_INFO(get_logger(), "StaticMapServer created (unconfigured)");
}

StaticMapServerBase::CallbackReturn
StaticMapServerBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: mapPub → /map
  mapPub_ = create_publisher<nav_msgs::msg::OccupancyGrid>(
    "/map", rclcpp::QoS(10));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

StaticMapServerBase::CallbackReturn
StaticMapServerBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  mapPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&StaticMapServerBase::mapPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

StaticMapServerBase::CallbackReturn
StaticMapServerBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  mapPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

StaticMapServerBase::CallbackReturn
StaticMapServerBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

StaticMapServerBase::CallbackReturn
StaticMapServerBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void StaticMapServerBase::mapPub_wired_publish()
{
  // Wired-mode publisher for /map — emits default nav_msgs::msg::OccupancyGrid.
  nav_msgs::msg::OccupancyGrid msg;
  mapPub_->publish(msg);
}
