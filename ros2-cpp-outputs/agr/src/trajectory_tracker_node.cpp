// TrajectoryTracker — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in trajectory_tracker_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "autonomous_ground_robot/trajectory_tracker_node_base.hpp"

class TrajectoryTracker : public TrajectoryTrackerBase
{
public:
  using TrajectoryTrackerBase::TrajectoryTrackerBase;

protected:
  void handle_stateSub(const nav_msgs::msg::Odometry & msg) override
  {
    // /odom_filtered — TODO: implement message processing logic.
    (void)msg;
  }
  void handle_planSub(const nav_msgs::msg::Path & msg) override
  {
    // /plan — TODO: implement message processing logic.
    (void)msg;
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<TrajectoryTracker>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
