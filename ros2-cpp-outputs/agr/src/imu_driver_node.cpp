// ImuDriver — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in imu_driver_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "autonomous_ground_robot/imu_driver_node_base.hpp"

class ImuDriver : public ImuDriverBase
{
public:
  using ImuDriverBase::ImuDriverBase;

protected:
  // Override on_configure_hook / on_activate_hook / on_deactivate_hook here.
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ImuDriver>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
