package ShowcaseAGR {
    doc /* Autonomous Ground Robot — ab initio stack.

       Demonstrates building a complete robot navigation stack from
       scratch using ros2-sysmlv2 library archetypes. No Nav2 dependency.
       Every node is a custom specialization of a library archetype.

       Subsystems:
         - Sensors: LiDAR, IMU, stereo camera (3 SensorDrivers)
         - Perception: obstacle detector (PerceptionPipeline)
         - Estimation: EKF localizer (Estimator)
         - Planning: path planner (Planner)
         - Control: trajectory tracker (Controller)
         - Safety: velocity smoother + collision guard (2 VelocityFilters)
         - Map: static map server (MapProvider)
         - Coordination: mission coordinator (BehaviorCoordinator)

       12 nodes, ~15 topics, full TF tree, parameters. */

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

    // ===============================================================
    // Sensors (3 SensorDrivers)
    // ===============================================================

    part def LidarDriver :> SensorDriver {
        :>> nodeName = "lidar";
        :>> namespace = "/sensors";
        :>> updateRateHz = 10.0;
        :>> frameId = "lidar_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/scan";
            :>> qos = sensorDataQoS;
            out item :>> msg : LaserScan;
        }
    }

    part def ImuDriver :> SensorDriver {
        :>> nodeName = "imu";
        :>> namespace = "/sensors";
        :>> updateRateHz = 200.0;
        :>> frameId = "imu_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/imu/data";
            :>> qos = sensorDataQoS;
            out item :>> msg : Imu;
        }
    }

    part def CameraDriver :> SensorDriver {
        :>> nodeName = "camera";
        :>> namespace = "/sensors";
        :>> updateRateHz = 30.0;
        :>> frameId = "camera_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/camera/image";
            :>> qos = sensorDataQoS;
            out item :>> msg : Image;
        }
    }

    // ===============================================================
    // Perception (PerceptionPipeline)
    // ===============================================================

    part def ObstacleDetector :> PerceptionPipeline {
        :>> nodeName = "obstacle_detector";
        :>> namespace = "/perception";

        port :>> rawSub : TopicSubscriber {
            :>> topicName = "/scan";
            :>> qos = sensorDataQoS;
            in item :>> msg : LaserScan;
        }

        port cameraSub : TopicSubscriber {
            :>> topicName = "/camera/image";
            :>> qos = sensorDataQoS;
            in item :>> msg : Image;
        }

        port :>> processedPub : TopicPublisher {
            :>> topicName = "/detections";
            :>> qos = defaultQoS;
            out item :>> msg : PointCloud2;
        }
    }

    // ===============================================================
    // Estimation (Estimator)
    // ===============================================================

    part def EKFLocalizer :> Estimator {
        :>> nodeName = "ekf_localizer";
        :>> namespace = "/estimation";

        port :>> sensorSub : TopicSubscriber {
            :>> topicName = "/imu/data";
            in item :>> msg : Imu;
        }

        port scanSub : TopicSubscriber {
            :>> topicName = "/scan";
            in item :>> msg : LaserScan;
        }

        port :>> posePub : TopicPublisher {
            :>> topicName = "/odom_filtered";
            :>> qos = defaultQoS;
            out item :>> msg : Odometry;
        }

        attribute maxIterations : DeclaredParameter {
            :>> name = "max_iterations";
            :>> parameterType = ParameterTypeKind::Integer;
        }
    }

    // ===============================================================
    // Planning (Planner)
    // ===============================================================

    part def PathPlanner :> Planner {
        :>> nodeName = "path_planner";
        :>> namespace = "/planning";

        port :>> planPub : TopicPublisher {
            :>> topicName = "/plan";
            :>> qos = defaultQoS;
            out item :>> msg : Path;
        }

        port mapSub : TopicSubscriber {
            :>> topicName = "/map";
            :>> qos = bestAvailableQoS;
            in item :>> msg : OccupancyGrid;
        }

        port detectionsSub : TopicSubscriber {
            :>> topicName = "/detections";
            :>> qos = defaultQoS;
            in item :>> msg : PointCloud2;
        }

        port :>> planAction : ActionServer {
            :>> actionName = "compute_path";
        }

        attribute plannerAlgorithm : DeclaredParameter {
            :>> name = "planner_algorithm";
            :>> parameterType = ParameterTypeKind::StringType;
        }
    }

    // ===============================================================
    // Control (Controller)
    // ===============================================================

    part def TrajectoryTracker :> Controller {
        :>> nodeName = "trajectory_tracker";
        :>> namespace = "/control";
        :>> controlFrequencyHz = 50.0;

        port :>> commandPub : TopicPublisher {
            :>> topicName = "/cmd_vel";
            :>> qos = defaultQoS;
            out item :>> msg : Twist;
        }

        port :>> stateSub : TopicSubscriber {
            :>> topicName = "/odom_filtered";
            :>> qos = defaultQoS;
            in item :>> msg : Odometry;
        }

        port planSub : TopicSubscriber {
            :>> topicName = "/plan";
            :>> qos = defaultQoS;
            in item :>> msg : Path;
        }

        port :>> controlAction : ActionServer {
            :>> actionName = "follow_trajectory";
        }

        attribute maxLinearVelocity : DeclaredParameter {
            :>> name = "max_linear_velocity";
            :>> parameterType = ParameterTypeKind::Double;
        }

        attribute maxAngularVelocity : DeclaredParameter {
            :>> name = "max_angular_velocity";
            :>> parameterType = ParameterTypeKind::Double;
        }
    }

    // ===============================================================
    // Safety chain (2 VelocityFilters)
    // ===============================================================

    part def VelocitySmoother :> VelocityFilter {
        :>> nodeName = "velocity_smoother";
        :>> namespace = "/safety";

        port :>> cmdVelIn : TopicSubscriber {
            :>> topicName = "/cmd_vel";
            :>> qos = defaultQoS;
            in item :>> msg : Twist;
        }

        port :>> cmdVelOut : TopicPublisher {
            :>> topicName = "/cmd_vel_smooth";
            :>> qos = systemDefaultQoS;
            out item :>> msg : Twist;
        }

        attribute smoothingFrequency : DeclaredParameter {
            :>> name = "smoothing_frequency";
            :>> parameterType = ParameterTypeKind::Double;
        }
    }

    part def CollisionGuard :> VelocityFilter {
        :>> nodeName = "collision_guard";
        :>> namespace = "/safety";

        port :>> cmdVelIn : TopicSubscriber {
            :>> topicName = "/cmd_vel_smooth";
            :>> qos = systemDefaultQoS;
            in item :>> msg : Twist;
        }

        port :>> cmdVelOut : TopicPublisher {
            :>> topicName = "/cmd_vel_out";
            :>> qos = defaultQoS;
            out item :>> msg : Twist;
        }

        port scanSub : TopicSubscriber {
            :>> topicName = "/scan";
            :>> qos = sensorDataQoS;
            in item :>> msg : LaserScan;
        }

        attribute minObstacleDistance : DeclaredParameter {
            :>> name = "min_obstacle_distance";
            :>> parameterType = ParameterTypeKind::Double;
        }
    }

    // ===============================================================
    // Map (MapProvider)
    // ===============================================================

    part def StaticMapServer :> MapProvider {
        :>> nodeName = "map_server";
        :>> namespace = "/";

        port :>> mapPub : TopicPublisher {
            :>> topicName = "/map";
            :>> qos = bestAvailableQoS;
            out item :>> msg : OccupancyGrid;
        }

        port :>> mapService : ServiceServer {
            :>> serviceName = "get_map";
        }
    }

    // ===============================================================
    // Coordination (BehaviorCoordinator)
    // ===============================================================

    part def MissionCoordinator :> BehaviorCoordinator {
        :>> nodeName = "mission_coordinator";
        :>> namespace = "/";

        port :>> goalAction : ActionServer {
            :>> actionName = "execute_mission";
        }

        port statusPub : TopicPublisher {
            :>> topicName = "/mission_status";
            out item :>> msg : Path;
        }
    }

    // ===============================================================
    // System composition
    // ===============================================================

    part def AutonomousGroundRobot {
        doc /* Complete autonomous ground robot stack.
               12 custom nodes, all lifecycle-managed, fully connected. */

        // ---- Sensors ----
        part lidar : LidarDriver;
        part imu : ImuDriver;
        part camera : CameraDriver;

        // ---- Perception ----
        part obstacleDetector : ObstacleDetector;

        // ---- Estimation ----
        part ekfLocalizer : EKFLocalizer;

        // ---- Planning ----
        part pathPlanner : PathPlanner;

        // ---- Control ----
        part trajectoryTracker : TrajectoryTracker;

        // ---- Safety chain ----
        part velocitySmoother : VelocitySmoother;
        part collisionGuard : CollisionGuard;

        // ---- Map ----
        part mapServer : StaticMapServer;

        // ---- Coordination ----
        part missionCoordinator : MissionCoordinator;

        // ---- TF frame tree ----
        part frames : StandardFrameTree;

        // Sensor frames
        part lidarFrame : CoordinateFrame { :>> frameId = "lidar_link"; }
        part imuFrame : CoordinateFrame { :>> frameId = "imu_link"; }
        part cameraFrame : CoordinateFrame { :>> frameId = "camera_link"; }

        // Sensor mounts (static transforms)
        connection lidarMount : StaticTransform
            connect frames.baseLinkFrame to lidarFrame;
        connection imuMount : StaticTransform
            connect frames.baseLinkFrame to imuFrame;
        connection cameraMount : StaticTransform
            connect frames.baseLinkFrame to cameraFrame;

        // ---- Data flow connections ----

        // Sensor → Perception
        connection scanToDetector : TopicConnection
            connect lidar.sensorPub to obstacleDetector.rawSub;
        connection cameraToDetector : TopicConnection
            connect camera.sensorPub to obstacleDetector.cameraSub;

        // Sensor → Estimation
        connection imuToEkf : TopicConnection
            connect imu.sensorPub to ekfLocalizer.sensorSub;
        connection scanToEkf : TopicConnection
            connect lidar.sensorPub to ekfLocalizer.scanSub;

        // Perception → Planning
        connection detectionsToPlanner : TopicConnection
            connect obstacleDetector.processedPub to pathPlanner.detectionsSub;

        // Map → Planning
        connection mapToPlanner : TopicConnection
            connect mapServer.mapPub to pathPlanner.mapSub;

        // Planning → Control
        connection planToTracker : TopicConnection
            connect pathPlanner.planPub to trajectoryTracker.planSub;

        // Estimation → Control
        connection odomToTracker : TopicConnection
            connect ekfLocalizer.posePub to trajectoryTracker.stateSub;

        // Control → Safety chain
        connection cmdVelToSmoother : TopicConnection
            connect trajectoryTracker.commandPub to velocitySmoother.cmdVelIn;
        connection smootherToGuard : TopicConnection
            connect velocitySmoother.cmdVelOut to collisionGuard.cmdVelIn;

        // Safety → Collision check (scan feedback)
        connection scanToGuard : TopicConnection
            connect lidar.sensorPub to collisionGuard.scanSub;
    }
}
