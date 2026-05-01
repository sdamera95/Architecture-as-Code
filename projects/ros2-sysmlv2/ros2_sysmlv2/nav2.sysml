package ros2_sysmlv2_nav2 {
    doc
    /* Nav2 (Navigation2) application framework for ROS2 Jazzy.

       Models the core Nav2 server nodes, their communication patterns,
       custom action/message types, and the composite Nav2Stack that wires
       them together.

       All node definitions are grounded against the Nav2 Jazzy source
       in references/navigation2/. Each server node's base class, action
       servers, publishers, subscribers, and key parameters are verified
       against the actual C++ source.

       BT internals are NOT modeled — the behavior tree is referenced
       only as a btXml parameter. BT node modeling is deferred to a
       future behavior-trees-sysmlv2 package.

       Dependency: ros2_sysmlv2_foundation, ros2_sysmlv2_geometry_msgs,
                   ros2_sysmlv2_sensor_msgs, ros2_sysmlv2_nav_msgs,
                   ros2_sysmlv2_comm, ros2_sysmlv2_lifecycle,
                   ros2_sysmlv2_tf2, ros2_sysmlv2_archetypes. */

    private import ScalarValues::*;
    private import ros2_sysmlv2_foundation::*;
    private import ros2_sysmlv2_geometry_msgs::*;
    private import ros2_sysmlv2_sensor_msgs::*;
    private import ros2_sysmlv2_nav_msgs::*;
    private import ros2_sysmlv2_comm::*;
    private import ros2_sysmlv2_lifecycle::*;
    private import ros2_sysmlv2_tf2::*;
    private import ros2_sysmlv2_archetypes::*;

    // ===============================================================
    // Section A: Nav2 Action Type Definitions
    // Source: nav2_msgs/action/*.action
    //
    // Modeled as item defs (goal/result/feedback are data that flows).
    // ===============================================================

    // ---- ComputePathToPose (PlannerServer) ----

    item def ComputePathToPoseGoal {
        doc /* Maps to nav2_msgs/action/ComputePathToPose goal. */
        attribute goal : PoseStamped;
        attribute startPose : PoseStamped;
        attribute plannerId : String;
        attribute useStart : Boolean;
    }

    item def ComputePathToPoseResult {
        doc /* Maps to nav2_msgs/action/ComputePathToPose result. */
        attribute path : Path;
        attribute planningTime : Duration;
        attribute errorCode : Integer;
        attribute errorMsg : String;
    }

    // ---- FollowPath (ControllerServer) ----

    item def FollowPathGoal {
        doc /* Maps to nav2_msgs/action/FollowPath goal. */
        attribute path : Path;
        attribute controllerId : String;
        attribute goalCheckerId : String;
        attribute progressCheckerId : String;
    }

    item def FollowPathFeedback {
        doc /* Maps to nav2_msgs/action/FollowPath feedback. */
        attribute distanceToGoal : Real;
        attribute speed : Real;
    }

    // ---- NavigateToPose (BtNavigator) ----

    item def NavigateToPoseGoal {
        doc /* Maps to nav2_msgs/action/NavigateToPose goal. */
        attribute pose : PoseStamped;
        attribute behaviorTree : String;
    }

    item def NavigateToPoseFeedback {
        doc /* Maps to nav2_msgs/action/NavigateToPose feedback. */
        attribute currentPose : PoseStamped;
        attribute navigationTime : Duration;
        attribute estimatedTimeRemaining : Duration;
        attribute numberOfRecoveries : Integer;
        attribute distanceRemaining : Real;
    }

    // ---- SmoothPath (SmootherServer) ----

    item def SmoothPathGoal {
        doc /* Maps to nav2_msgs/action/SmoothPath goal. */
        attribute path : Path;
        attribute smootherId : String;
        attribute maxSmoothingDuration : Duration;
        attribute checkForCollisions : Boolean;
    }

    item def SmoothPathResult {
        doc /* Maps to nav2_msgs/action/SmoothPath result. */
        attribute path : Path;
        attribute smoothingDuration : Duration;
        attribute wasCompleted : Boolean;
        attribute errorCode : Integer;
    }

    // ---- Spin (BehaviorServer) ----

    item def SpinGoal {
        doc /* Maps to nav2_msgs/action/Spin goal. */
        attribute targetYaw : Real;
        attribute timeAllowance : Duration;
    }

    // ---- BackUp (BehaviorServer) ----

    item def BackUpGoal {
        doc /* Maps to nav2_msgs/action/BackUp goal. */
        attribute target : Point;
        attribute speed : Real;
        attribute timeAllowance : Duration;
    }

    // ---- Wait (BehaviorServer) ----

    item def WaitGoal {
        doc /* Maps to nav2_msgs/action/Wait goal. */
        attribute waitTime : Duration;
    }

    // ---- Nav2-specific messages ----

    item def Costmap {
        doc /* Maps to nav2_msgs/msg/Costmap.
               2D costmap with metadata and raw cell data. */
        attribute header : Header;
        attribute metadataResolution : Real;
        attribute metadataWidth : Integer;
        attribute metadataHeight : Integer;
        attribute data : Integer[0..*];
    }

    item def SpeedLimit {
        doc /* Maps to nav2_msgs/msg/SpeedLimit.
               Speed limit override for dynamic speed zones. */
        attribute header : Header;
        attribute speedLimit : Real;
        attribute percentage : Boolean;
    }

    // ===============================================================
    // Section B: Nav2 Server Nodes
    // Each specializes an archetype and is grounded against source.
    // ===============================================================

    // ---- PlannerServer ----
    // Source: nav2_planner/src/planner_server.cpp
    // Base: LifecycleNode
    // Actions: compute_path_to_pose (ComputePathToPose)
    // Pubs: plan (Path)
    // Services: is_path_valid

    part def PlannerServer :> Planner {
        doc /* Nav2 path planning server.
               Loads planner plugins (e.g., NavfnPlanner, SmacPlanner)
               and serves path computation requests.
               Source: nav2_planner/src/planner_server.cpp */

        port :>> planAction : ActionServer {
            :>> actionName = "compute_path_to_pose";
            in item :>> goal : ComputePathToPoseGoal;
            out item :>> result : ComputePathToPoseResult;
        }

        port :>> planPub : TopicPublisher {
            :>> topicName = "plan";
            out item :>> msg : Path;
        }

        attribute plannerPlugins : String;
        attribute expectedPlannerFrequency : Real;
    }

    // ---- ControllerServer ----
    // Source: nav2_controller/src/controller_server.cpp
    // Base: LifecycleNode
    // Actions: follow_path (FollowPath)
    // Pubs: cmd_vel (TwistStamped)
    // Subs: speed_limit, odom

    part def ControllerServer :> Controller {
        doc /* Nav2 path following / trajectory tracking server.
               Loads controller plugins (e.g., DWB, MPPI, RPP)
               and executes path following with velocity commands.
               Source: nav2_controller/src/controller_server.cpp */

        :>> controlFrequencyHz = 20.0;

        port :>> controlAction : ActionServer {
            :>> actionName = "follow_path";
            in item :>> goal : FollowPathGoal;
            out item :>> feedback : FollowPathFeedback;
        }

        port :>> commandPub : TopicPublisher {
            :>> topicName = "cmd_vel";
            out item :>> msg : TwistStamped;
        }

        port :>> stateSub : TopicSubscriber {
            :>> topicName = "odom";
            in item :>> msg : Odometry;
        }

        port speedLimitSub : TopicSubscriber {
            :>> topicName = "speed_limit";
            in item :>> msg : SpeedLimit;
        }

        attribute controllerPlugins : String;
    }

    // ---- BtNavigator ----
    // Source: nav2_bt_navigator/src/bt_navigator.cpp
    // Base: LifecycleNode
    // Actions: navigate_to_pose (NavigateToPose)
    // Subs: goal_pose
    // TF: buffer + listener

    part def BtNavigator :> BehaviorCoordinator {
        doc /* Nav2 behavior tree navigator.
               Receives NavigateToPose goals and orchestrates planner,
               controller, smoother, and behavior servers via a behavior
               tree loaded from btXml parameter.
               Source: nav2_bt_navigator/src/bt_navigator.cpp */

        port :>> goalAction : ActionServer {
            :>> actionName = "navigate_to_pose";
            in item :>> goal : NavigateToPoseGoal;
            out item :>> feedback : NavigateToPoseFeedback;
        }

        port goalPoseSub : TopicSubscriber {
            :>> topicName = "goal_pose";
            in item :>> msg : PoseStamped;
        }

        attribute globalFrame : String;
        attribute robotBaseFrame : String;
    }

    // ---- BehaviorServer ----
    // Source: nav2_behaviors/src/behavior_server.cpp
    // Base: LifecycleNode
    // Actions: spin, backup, wait (via plugins)
    // Pubs: cmd_vel
    // Subs: costmaps, footprints

    part def BehaviorServer :> LifecycleNode {
        doc /* Nav2 recovery behavior server.
               Hosts multiple behavior plugins (spin, backup,
               drive_on_heading, wait) as action servers.
               Source: nav2_behaviors/src/behavior_server.cpp */

        port spinAction : ActionServer {
            :>> actionName = "spin";
            in item :>> goal : SpinGoal;
        }

        port backupAction : ActionServer {
            :>> actionName = "backup";
            in item :>> goal : BackUpGoal;
        }

        port waitAction : ActionServer {
            :>> actionName = "wait";
            in item :>> goal : WaitGoal;
        }

        port cmdVelPub : TopicPublisher {
            :>> topicName = "cmd_vel";
            out item :>> msg : TwistStamped;
        }

        attribute behaviorPlugins : String;
        attribute cycleFrequency : Real;
    }

    // ---- SmootherServer ----
    // Source: nav2_smoother/src/nav2_smoother.cpp
    // Base: LifecycleNode
    // Actions: smooth_path (SmoothPath)
    // Pubs: plan_smoothed (Path)

    part def SmootherServer :> Planner {
        doc /* Nav2 path smoothing server.
               Smooths paths produced by the planner for better
               controller tracking performance.
               Source: nav2_smoother/src/nav2_smoother.cpp */

        port :>> planAction : ActionServer {
            :>> actionName = "smooth_path";
            in item :>> goal : SmoothPathGoal;
            out item :>> result : SmoothPathResult;
        }

        port :>> planPub : TopicPublisher {
            :>> topicName = "plan_smoothed";
            out item :>> msg : Path;
        }

        attribute smootherPlugins : String;
    }

    // ---- Costmap2DROS ----
    // Source: nav2_costmap_2d/src/costmap_2d_ros.cpp
    // Base: LifecycleNode
    // Pubs: costmap, published_footprint
    // Subs: map, sensor topics (via layers)

    part def Costmap2DROS :> LifecycleNode {
        doc /* Nav2 costmap node.
               Maintains a 2D costmap from sensor data and static maps.
               Used by planners and controllers for obstacle avoidance.
               Source: nav2_costmap_2d/src/costmap_2d_ros.cpp */

        port costmapPub : TopicPublisher {
            :>> topicName = "costmap";
            out item :>> msg : Costmap;
        }

        port footprintPub : TopicPublisher {
            :>> topicName = "published_footprint";
            out item :>> msg : PolygonStamped;
        }

        port mapSub : TopicSubscriber {
            :>> topicName = "map";
            in item :>> msg : OccupancyGrid;
        }

        attribute updateFrequency : Real;
        attribute publishFrequency : Real;
        attribute globalFrame : String;
        attribute robotBaseFrame : String;
        attribute resolution : Real;
    }

    // ---- AmclNode ----
    // Source: nav2_amcl/src/amcl_node.cpp
    // Base: LifecycleNode
    // Pubs: amcl_pose, particle_cloud
    // Subs: scan, map, initialpose
    // TF: publishes map->odom

    part def AmclNode :> Estimator {
        doc /* Nav2 Adaptive Monte Carlo Localization node.
               Particle filter localizer: subscribes to laser scan and
               map, publishes pose estimate and map->odom transform.
               Source: nav2_amcl/src/amcl_node.cpp */

        port :>> posePub : TopicPublisher {
            :>> topicName = "amcl_pose";
            out item :>> msg : PoseWithCovarianceStamped;
        }

        port :>> sensorSub : TopicSubscriber {
            :>> topicName = "scan";
            in item :>> msg : LaserScan;
        }

        port mapSub : TopicSubscriber {
            :>> topicName = "map";
            in item :>> msg : OccupancyGrid;
        }

        attribute minParticles : Integer;
        attribute maxParticles : Integer;
    }

    // ---- MapServer ----
    // Source: nav2_map_server/src/map_server/map_server.cpp
    // Base: LifecycleNode
    // Pubs: map (OccupancyGrid)
    // Services: map (GetMap), load_map (LoadMap)

    part def Nav2MapServer :> MapProvider {
        doc /* Nav2 map server node.
               Loads occupancy grid from YAML/image and publishes it.
               Provides services for map retrieval and runtime reloading.
               Source: nav2_map_server/src/map_server/map_server.cpp */

        port :>> mapPub : TopicPublisher {
            :>> topicName = "map";
            :>> qos = bestAvailableQoS;
            out item :>> msg : OccupancyGrid;
        }

        port :>> mapService : ServiceServer {
            :>> serviceName = "map";
        }

        port loadMapService : ServiceServer {
            :>> serviceName = "load_map";
        }
    }

    // ---- VelocitySmoother ----
    // Source: nav2_velocity_smoother/src/velocity_smoother.cpp
    // Base: LifecycleNode
    // Subs: cmd_vel
    // Pubs: cmd_vel_smoothed

    part def Nav2VelocitySmoother :> VelocityFilter {
        doc /* Nav2 velocity smoother node.
               Applies acceleration/deceleration limits to velocity
               commands for smooth robot motion.
               Source: nav2_velocity_smoother/src/velocity_smoother.cpp */

        port :>> cmdVelIn : TopicSubscriber {
            :>> topicName = "cmd_vel";
            in item :>> msg : Twist;
        }

        port :>> cmdVelOut : TopicPublisher {
            :>> topicName = "cmd_vel_smoothed";
            out item :>> msg : Twist;
        }

        attribute smoothingFrequency : Real;
    }

    // ---- CollisionMonitor ----
    // Source: nav2_collision_monitor/src/collision_monitor_node.cpp
    // Base: LifecycleNode
    // Subs: cmd_vel_in, sensor topics
    // Pubs: cmd_vel_out, state

    part def Nav2CollisionMonitor :> VelocityFilter {
        doc /* Nav2 collision monitor node.
               Monitors sensor data and reduces or stops velocity
               commands when collision risk is detected.
               Source: nav2_collision_monitor/src/collision_monitor_node.cpp */

        port :>> cmdVelIn : TopicSubscriber {
            :>> topicName = "cmd_vel_smoothed";
            in item :>> msg : Twist;
        }

        port :>> cmdVelOut : TopicPublisher {
            :>> topicName = "cmd_vel_out";
            out item :>> msg : Twist;
        }

        attribute baseFrameId : String;
    }

    // ---- LifecycleManager ----
    // Source: nav2_lifecycle_manager/src/lifecycle_manager.cpp
    // Base: rclcpp::Node (NOT LifecycleNode)
    // Services: manage_nodes, is_active

    part def Nav2LifecycleManager :> Node {
        doc /* Nav2 lifecycle manager node.
               Manages the lifecycle transitions of all Nav2 server nodes.
               This is a plain Node, NOT a LifecycleNode — it manages
               lifecycle, it does not participate in it.
               Source: nav2_lifecycle_manager/src/lifecycle_manager.cpp */

        attribute managedNodeNames : String;
        attribute autostart : Boolean;
    }

    // ===============================================================
    // Section C: Nav2Stack Composite
    // The full Nav2 navigation stack wired together.
    // ===============================================================

    part def Nav2Stack {
        doc /* Complete Nav2 navigation stack composition.
               All server nodes as nested parts with topic/action
               connections representing the Nav2 data flow.

               Velocity chain: controller -> velocity_smoother -> collision_monitor -> robot
               Planning chain: bt_navigator -> planner -> controller
               Localization: amcl -> TF (map->odom) */

        // ---- Server node instances ----

        part planner : PlannerServer;
        part controller : ControllerServer;
        part btNavigator : BtNavigator;
        part behaviors : BehaviorServer;
        part smoother : SmootherServer;
        part globalCostmap : Costmap2DROS;
        part localCostmap : Costmap2DROS;
        part amcl : AmclNode;
        part mapServer : Nav2MapServer;
        part velocitySmoother : Nav2VelocitySmoother;
        part collisionMonitor : Nav2CollisionMonitor;
        part lifecycleManager : Nav2LifecycleManager;

        // ---- TF frame tree ----

        part frames : StandardFrameTree;

        // ---- Key connections ----

        // Velocity chain: controller -> smoother -> collision_monitor
        connection velToSmoother : TopicConnection
            connect controller.commandPub to velocitySmoother.cmdVelIn;

        connection smootherToMonitor : TopicConnection
            connect velocitySmoother.cmdVelOut to collisionMonitor.cmdVelIn;

        // Map distribution: map_server -> amcl, map_server -> costmaps
        connection mapToAmcl : TopicConnection
            connect mapServer.mapPub to amcl.mapSub;

        connection mapToGlobalCostmap : TopicConnection
            connect mapServer.mapPub to globalCostmap.mapSub;

        connection mapToLocalCostmap : TopicConnection
            connect mapServer.mapPub to localCostmap.mapSub;
    }
}
