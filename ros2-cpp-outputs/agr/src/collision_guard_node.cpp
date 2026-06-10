// CollisionGuard — node implementation. EDIT ME.
//
// Generated ONCE by the ros2-sysmlv2 bridge pipeline and never overwritten
// (generation-gap pattern): this file is where demo/application logic lives.
// The architectural wiring is in collision_guard_node_base.hpp/.cpp, regenerated
// on every pipeline run.
#include "autonomous_ground_robot/collision_guard_node_base.hpp"

class CollisionGuard : public CollisionGuardBase
{
public:
  using CollisionGuardBase::CollisionGuardBase;

protected:
  void handle_cmdVelIn(const geometry_msgs::msg::Twist & msg) override
  {
    // /cmd_vel_smooth — TODO: implement message processing logic.
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
  auto node = std::make_shared<CollisionGuard>();
  rclcpp::spin(node->get_node_base_interface());
  rclcpp::shutdown();
  return 0;
}
