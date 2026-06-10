// AGRVelocitySmoother — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in a_g_r_velocity_smoother_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "autonomous_ground_robot/a_g_r_velocity_smoother_node_base.hpp"

class AGRVelocitySmoother : public AGRVelocitySmootherBase
{
public:
  using AGRVelocitySmootherBase::AGRVelocitySmootherBase;

protected:
  void handle_cmdVelIn(const geometry_msgs::msg::Twist & msg) override
  {
    // /cmd_vel — TODO: implement message processing logic.
    (void)msg;
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<AGRVelocitySmoother>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
