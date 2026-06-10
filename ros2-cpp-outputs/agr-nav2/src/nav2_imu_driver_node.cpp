// Nav2ImuDriver — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in nav2_imu_driver_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "ground_robot_with_nav2/nav2_imu_driver_node_base.hpp"

class Nav2ImuDriver : public Nav2ImuDriverBase
{
public:
  using Nav2ImuDriverBase::Nav2ImuDriverBase;

protected:
  // Override on_configure_hook / on_activate_hook / on_deactivate_hook here.
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<Nav2ImuDriver>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
