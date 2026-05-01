package ConsumerTestRobot {
    doc /* Consumer test: a minimal robot model built using the
           ros2-sysmlv2 library. Validates that a downstream user
           can import and compose library definitions into a
           working robot architecture. */

    private import ScalarValues::*;
    private import ros2_sysmlv2_foundation::*;
    private import ros2_sysmlv2_geometry_msgs::*;
    private import ros2_sysmlv2_sensor_msgs::*;
    private import ros2_sysmlv2_nav_msgs::*;
    private import ros2_sysmlv2_comm::*;
    private import ros2_sysmlv2_lifecycle::*;
    private import ros2_sysmlv2_tf2::*;
    private import ros2_sysmlv2_params::*;
    private import ros2_sysmlv2_archetypes::*;
    private import ros2_sysmlv2_nav2::*;

    // ---- Custom sensor driver ----

    part def MyLidarDriver :> SensorDriver {
        :>> nodeName = "lidar_driver";
        :>> namespace = "/sensors";
        :>> updateRateHz = 10.0;
        :>> frameId = "lidar_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/scan";
            :>> qos = sensorDataQoS;
            out item :>> msg : LaserScan;
        }
    }

    // ---- Custom controller ----

    part def MyController :> Controller {
        :>> nodeName = "my_controller";
        :>> namespace = "/";
        :>> controlFrequencyHz = 50.0;

        port :>> controlAction : ActionServer {
            :>> actionName = "follow_path";
            in item :>> goal : FollowPathGoal;
            out item :>> feedback : FollowPathFeedback;
        }

        port :>> commandPub : TopicPublisher {
            :>> topicName = "/cmd_vel";
            out item :>> msg : Twist;
        }

        port :>> stateSub : TopicSubscriber {
            :>> topicName = "/odom";
            in item :>> msg : Odometry;
        }

        attribute maxVelocity : DeclaredParameter {
            :>> name = "max_velocity";
            :>> parameterType = ParameterTypeKind::Double;
        }
    }

    // ---- Robot system ----

    part def TestRobot {
        doc /* Minimal robot using library definitions. */

        // Sensor
        part lidar : MyLidarDriver;

        // Navigation (reuse Nav2 stack)
        part nav : Nav2Stack;

        // Custom controller
        part controller : MyController;

        // TF frames
        part frames : StandardFrameTree;

        // Sensor frame (static transform from base_link)
        part lidarFrame : CoordinateFrame {
            :>> frameId = "lidar_link";
        }

        connection lidarMount : StaticTransform
            connect frames.baseLinkFrame to lidarFrame;

        // Wire lidar to nav stack costmap
        connection lidarToLocalCostmap : TopicConnection
            connect lidar.sensorPub to nav.localCostmap.mapSub;
    }
}
