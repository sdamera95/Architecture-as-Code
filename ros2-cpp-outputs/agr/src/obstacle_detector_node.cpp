// ObstacleDetector — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in obstacle_detector_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "autonomous_ground_robot/obstacle_detector_node_base.hpp"

class ObstacleDetector : public ObstacleDetectorBase
{
public:
  using ObstacleDetectorBase::ObstacleDetectorBase;

protected:
  void handle_rawSub(const sensor_msgs::msg::LaserScan & msg) override
  {
    // /scan — TODO: implement message processing logic.
    (void)msg;
  }
  void handle_cameraSub(const sensor_msgs::msg::Image & msg) override
  {
    // /camera/image — TODO: implement message processing logic.
    (void)msg;
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ObstacleDetector>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
