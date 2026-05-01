package ShowcaseAGR_Nav2 {
    doc /* Autonomous Ground Robot with Nav2 — hybrid stack.

       Demonstrates building custom sensor/perception/estimation nodes
       that feed into a stock Nav2 navigation stack. The user writes
       only the custom nodes; Nav2 provides planning, control, behaviors,
       and lifecycle management.

       Custom nodes (generated, launchable):
         - LiDAR driver, depth camera driver, IMU driver (SensorDrivers)
         - Point cloud filter (PerceptionPipeline)
         - EKF localizer (Estimator, publishes map→odom TF)

       Nav2 nodes (referenced, launched via Nav2 bringup):
         - PlannerServer, ControllerServer, BtNavigator
         - SmootherServer, BehaviorServer
         - Costmap2DROS (global + local)
         - VelocitySmoother, CollisionMonitor

       This model shows the integration pattern: custom nodes produce
       the sensor data and localization that Nav2 consumes. */

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

    // ===============================================================
    // Custom sensors
    // ===============================================================

    part def Nav2LidarDriver :> SensorDriver {
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

    part def DepthCameraDriver :> SensorDriver {
        :>> nodeName = "depth_camera";
        :>> namespace = "/sensors";
        :>> updateRateHz = 15.0;
        :>> frameId = "depth_camera_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/depth/image";
            :>> qos = sensorDataQoS;
            out item :>> msg : Image;
        }

        port cameraInfoPub : TopicPublisher {
            :>> topicName = "/depth/camera_info";
            out item :>> msg : CameraInfo;
        }
    }

    part def Nav2ImuDriver :> SensorDriver {
        :>> nodeName = "imu";
        :>> namespace = "/sensors";
        :>> updateRateHz = 100.0;
        :>> frameId = "imu_link";

        port :>> sensorPub : TopicPublisher {
            :>> topicName = "/imu/data";
            :>> qos = sensorDataQoS;
            out item :>> msg : Imu;
        }
    }

    // ===============================================================
    // Custom perception
    // ===============================================================

    part def PointCloudFilter :> PerceptionPipeline {
        :>> nodeName = "pointcloud_filter";
        :>> namespace = "/perception";

        port :>> rawSub : TopicSubscriber {
            :>> topicName = "/depth/image";
            in item :>> msg : Image;
        }

        port :>> processedPub : TopicPublisher {
            :>> topicName = "/filtered_cloud";
            out item :>> msg : PointCloud2;
        }

        attribute voxelSize : DeclaredParameter {
            :>> name = "voxel_size";
            :>> parameterType = ParameterTypeKind::Double;
        }
    }

    // ===============================================================
    // Custom estimation (feeds Nav2 with TF and odometry)
    // ===============================================================

    part def Nav2EKFLocalizer :> Estimator {
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
            :>> topicName = "/odom";
            out item :>> msg : Odometry;
        }

        port poseCovPub : TopicPublisher {
            :>> topicName = "/amcl_pose";
            out item :>> msg : PoseWithCovarianceStamped;
        }
    }

    // ===============================================================
    // System composition
    // ===============================================================

    part def GroundRobotWithNav2 {
        doc /* Hybrid robot: custom sensors + estimation, Nav2 navigation.

               Custom nodes (5) are generated and launched by this package.
               Nav2 nodes (12) are launched via Nav2's own bringup.
               The custom nodes feed Nav2 through standard topics:
                 /scan → Nav2 costmaps
                 /odom → Nav2 controller
                 /amcl_pose → Nav2 localization (bypasses AMCL)
                 TF (map→odom) → Nav2 frame tree */

        // ---- Custom sensors ----
        part lidar : Nav2LidarDriver;
        part depthCamera : DepthCameraDriver;
        part imu : Nav2ImuDriver;

        // ---- Custom perception ----
        part pointcloudFilter : PointCloudFilter;

        // ---- Custom estimation ----
        part ekfLocalizer : Nav2EKFLocalizer;

        // ---- Nav2 stack (referenced, not generated) ----
        part nav : Nav2Stack;

        // ---- TF frame tree ----
        part frames : StandardFrameTree;

        // Sensor frames
        part lidarFrame : CoordinateFrame { :>> frameId = "lidar_link"; }
        part depthCameraFrame : CoordinateFrame { :>> frameId = "depth_camera_link"; }
        part imuFrame : CoordinateFrame { :>> frameId = "imu_link"; }

        // Sensor mounts
        connection lidarMount : StaticTransform
            connect frames.baseLinkFrame to lidarFrame;
        connection depthCameraMount : StaticTransform
            connect frames.baseLinkFrame to depthCameraFrame;
        connection imuMount : StaticTransform
            connect frames.baseLinkFrame to imuFrame;

        // ---- Custom data flow connections ----

        // Depth camera → perception
        connection depthToFilter : TopicConnection
            connect depthCamera.sensorPub to pointcloudFilter.rawSub;

        // Sensors → estimation
        connection imuToEkf : TopicConnection
            connect imu.sensorPub to ekfLocalizer.sensorSub;
        connection scanToEkf : TopicConnection
            connect lidar.sensorPub to ekfLocalizer.scanSub;

        // ---- Custom → Nav2 integration connections ----

        // LiDAR → Nav2 costmaps
        connection scanToLocalCostmap : TopicConnection
            connect lidar.sensorPub to nav.localCostmap.mapSub;
        connection scanToGlobalCostmap : TopicConnection
            connect lidar.sensorPub to nav.globalCostmap.mapSub;

        // Estimation → Nav2 controller (odometry)
        connection odomToController : TopicConnection
            connect ekfLocalizer.posePub to nav.controller.stateSub;
    }
}
