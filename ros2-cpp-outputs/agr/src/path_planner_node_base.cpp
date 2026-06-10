// PathPlannerBase — auto-generated from SysML v2 model. DO NOT EDIT.
// Regenerated on every pipeline run; demo logic belongs in path_planner_node.cpp.
#include "autonomous_ground_robot/path_planner_node_base.hpp"

#include <chrono>
#include <functional>

PathPlannerBase::PathPlannerBase(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("path_planner", options)
{
  RCLCPP_INFO(get_logger(), "PathPlanner created (unconfigured)");
}

PathPlannerBase::CallbackReturn
PathPlannerBase::on_configure(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring...");

  // Publisher: planPub → /plan
  planPub_ = create_publisher<nav_msgs::msg::Path>(
    "/plan", rclcpp::QoS(10));

  // Subscriber: mapSub ← /map
  mapSub_ = create_subscription<nav_msgs::msg::OccupancyGrid>(
    "/map", rclcpp::QoS(10),
    std::bind(&PathPlannerBase::mapSub_callback, this,
              std::placeholders::_1));

  // Subscriber: detectionsSub ← /detections
  detectionsSub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
    "/detections", rclcpp::QoS(10),
    std::bind(&PathPlannerBase::detectionsSub_callback, this,
              std::placeholders::_1));

  on_configure_hook();
  return CallbackReturn::SUCCESS;
}

PathPlannerBase::CallbackReturn
PathPlannerBase::on_activate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Activating...");

  // ── Fully-wired mode: publish default messages for topology verification ──
  planPub_timer_ = create_wall_timer(
    std::chrono::milliseconds(1000),
    std::bind(&PathPlannerBase::planPub_wired_publish, this));
  on_activate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_activate(state);
}

PathPlannerBase::CallbackReturn
PathPlannerBase::on_deactivate(const rclcpp_lifecycle::State & state)
{
  RCLCPP_INFO(get_logger(), "Deactivating...");
  planPub_timer_->cancel();
  on_deactivate_hook();
  return rclcpp_lifecycle::LifecycleNode::on_deactivate(state);
}

PathPlannerBase::CallbackReturn
PathPlannerBase::on_cleanup(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up...");
  return CallbackReturn::SUCCESS;
}

PathPlannerBase::CallbackReturn
PathPlannerBase::on_shutdown(const rclcpp_lifecycle::State & /*state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down...");
  return CallbackReturn::SUCCESS;
}

void PathPlannerBase::mapSub_callback(const nav_msgs::msg::OccupancyGrid & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /map");
  handle_mapSub(msg);
}

void PathPlannerBase::detectionsSub_callback(const sensor_msgs::msg::PointCloud2 & msg)
{
  RCLCPP_DEBUG(get_logger(), "[wired] Received on /detections");
  handle_detectionsSub(msg);
}

void PathPlannerBase::planPub_wired_publish()
{
  // Wired-mode publisher for /plan — emits default nav_msgs::msg::Path.
  nav_msgs::msg::Path msg;
  planPub_->publish(msg);
}
