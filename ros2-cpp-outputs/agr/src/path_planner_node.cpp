// PathPlanner — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in path_planner_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "autonomous_ground_robot/path_planner_node_base.hpp"

class PathPlanner : public PathPlannerBase
{
public:
  using PathPlannerBase::PathPlannerBase;

protected:
  void handle_mapSub(const nav_msgs::msg::OccupancyGrid & msg) override
  {
    // /map — TODO: implement message processing logic.
    (void)msg;
  }
  void handle_detectionsSub(const sensor_msgs::msg::PointCloud2 & msg) override
  {
    // /detections — TODO: implement message processing logic.
    (void)msg;
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<PathPlanner>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
