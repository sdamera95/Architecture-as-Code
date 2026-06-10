// Nav2EKFLocalizer — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in nav2_e_k_f_localizer_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "ground_robot_with_nav2/nav2_e_k_f_localizer_node_base.hpp"

class Nav2EKFLocalizer : public Nav2EKFLocalizerBase
{
public:
  using Nav2EKFLocalizerBase::Nav2EKFLocalizerBase;

protected:
  void handle_sensorSub(const sensor_msgs::msg::Imu & msg) override
  {
    // /imu/data — TODO: implement message processing logic.
    (void)msg;
  }
  void handle_scanSub(const sensor_msgs::msg::LaserScan & msg) override
  {
    // /scan — TODO: implement message processing logic.
    (void)msg;
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<Nav2EKFLocalizer>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
