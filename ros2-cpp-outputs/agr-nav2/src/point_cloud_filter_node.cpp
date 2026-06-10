// PointCloudFilter — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in point_cloud_filter_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "ground_robot_with_nav2/point_cloud_filter_node_base.hpp"

class PointCloudFilter : public PointCloudFilterBase
{
public:
  using PointCloudFilterBase::PointCloudFilterBase;

protected:
  void handle_rawSub(const sensor_msgs::msg::Image & msg) override
  {
    // /depth/image — TODO: implement message processing logic.
    (void)msg;
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<PointCloudFilter>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
