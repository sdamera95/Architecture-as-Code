package ShowcaseAGRNav2Full {
    doc /* Full multi-domain architecture model of an Autonomous Ground Robot
       with Nav2 navigation stack integration.

       Same multi-domain architecture as ShowcaseAGRFull (physical structure,
       electrical, use cases, requirements, V&V, views) but with custom
       sensors/perception/estimation feeding into a stock Nav2 stack instead
       of a fully custom autonomy pipeline.

       This demonstrates the hybrid integration pattern: custom ROS2 nodes
       coexist with Nav2's standard servers, and non-ROS2 structural elements
       coexist with both. The pipeline extracts only the ROS2-typed elements
       (custom + Nav2) and silently skips the rest. */

    // ═══════════════════════════════════════════════════════════════
    // Standard library imports
    // ═══════════════════════════════════════════════════════════════

    private import ScalarValues::*;
    private import SI::*;
    private import StandardViewDefinitions::*;
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

    // ═══════════════════════════════════════════════════════════════
    // 1. PHYSICAL STRUCTURE (non-ROS2)
    // ═══════════════════════════════════════════════════════════════

    part def Chassis {
        doc /* Steel tube frame for outdoor delivery robot. */
        attribute massKg : Real = 5.0;
        attribute lengthM : Real = 0.8;
        attribute widthM : Real = 0.5;
        attribute material : String = "steel_tube";
    }

    part def Wheel {
        attribute diameterM : Real = 0.2;
        attribute massKg : Real = 0.5;
    }

    part def Drivetrain {
        doc /* Skid-steer 4WD drivetrain. */
        part frontLeft : Wheel;
        part frontRight : Wheel;
        part rearLeft : Wheel;
        part rearRight : Wheel;
    }

    part def Battery {
        doc /* 6S LiPo for extended outdoor operation. */
        attribute voltageV : Real = 22.2;
        attribute capacityAh : Real = 16.0;
        attribute massKg : Real = 1.5;
    }

    part def OnboardComputer {
        doc /* Jetson AGX Orin — runs ROS2 Jazzy + Nav2 + SLAM. */
        attribute massKg : Real = 0.28;
        attribute powerW : Real = 40.0;
        attribute ramGb : Integer = 32;
    }

    part def LidarUnit {
        doc /* Ouster OS1-64 3D LiDAR. */
        attribute massKg : Real = 0.45;
        attribute rangeM : Real = 120.0;
        attribute powerW : Real = 14.0;
    }

    part def DepthCameraUnit {
        doc /* Intel RealSense D455 depth camera. */
        attribute massKg : Real = 0.1;
        attribute powerW : Real = 4.5;
    }

    part def ImuUnit {
        doc /* VectorNav VN-100 tactical-grade IMU. */
        attribute massKg : Real = 0.015;
        attribute powerW : Real = 0.4;
    }

    part def WeatherproofEnclosure {
        doc /* IP67-rated enclosure for electronics. */
        attribute massKg : Real = 0.8;
    }

    // ═══════════════════════════════════════════════════════════════
    // 2. CUSTOM ROS2 NODES (extracted by pipeline)
    // ═══════════════════════════════════════════════════════════════

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

    part def Nav2EKFLocalizer :> Estimator {
        satisfy requirement : GPSAccuracyReq {
            doc /* EKF fuses IMU at 100 Hz with LiDAR scan matching
                   and AMCL pose, achieving sub-1m outdoor localization. */
        }
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

    // ═══════════════════════════════════════════════════════════════
    // 3. USE CASES (non-ROS2)
    // ═══════════════════════════════════════════════════════════════

    part def Operator {
        doc /* Remote operator commanding outdoor delivery robot. */
    }

    use case def OutdoorDelivery {
        doc /* Robot navigates outdoor campus to deliver package. */
        subject robot : GroundRobotWithNav2;
        actor operator : Operator;
    }

    use case def ReturnToBase {
        doc /* Robot navigates back to charging station autonomously. */
        subject robot : GroundRobotWithNav2;
    }

    use case def ManualTeleop {
        doc /* Operator takes manual control via joystick/gamepad. */
        subject robot : GroundRobotWithNav2;
        actor operator : Operator;
    }

    // ═══════════════════════════════════════════════════════════════
    // 4. BEHAVIORAL MODELING (non-ROS2)
    //    Exercises: substates, event-triggered transitions, guard
    //    conditions, fork/join, if-else decision nodes.
    //    Nav2 behavioral model grounded in actual Nav2 source code:
    //    references/navigation2/nav2_bt_navigator/behavior_trees/
    // ═══════════════════════════════════════════════════════════════

    // ---- Event items for state machine triggers ----

    item def OrderReceived;
    item def PackageLoaded;
    item def PackageUnloaded;
    item def PathComputed;
    item def GoalReached;
    item def ControlError;
    item def RecoveryExhausted;
    item def ManualOverrideCmd;
    item def MissionCommand { attribute text : String; }
    item def TelemetryFrame { attribute text : String; }

    // ---- Delivery operational modes (Nav2-grounded state machine) ----

    state def DeliveryModes {
        doc /* Delivery robot operational modes with Nav2-grounded navigation
               substates. The navigating composite state is a parallel region:
               one region models Nav2's default behavior tree (ComputePathToPose
               at 1 Hz + FollowPath at 20 Hz + RoundRobin recovery with 6 retries),
               the other region concurrently monitors battery level with
               hysteresis.

               Top-level states model the delivery order lifecycle.
               The navigating state is reused for pickup transit, dropoff
               transit, and return-to-base; Nav2 does not distinguish
               these; only the goal pose changes. Entry/do/exit actions emit
               control messages to the Nav2 BT server via navPort. */

        attribute retryCount : Integer;
        attribute batteryLevel : Real;

        // Ports for event routing
        ref port dispatchPort;
        ref port navPort;
        ref port operatorPort;

        entry;
            then idle;

        state idle {
            doc /* Robot at base station, charged, awaiting delivery order. */
            entry send new TelemetryFrame("ready") via operatorPort;
        }

        // PARALLEL COMPOSITE: Nav2 navigation + battery monitoring concurrently
        state navigating parallel {
            doc /* Active Nav2 navigation with concurrent battery monitoring.
                   Navigation region models the Nav2 BT pipeline; monitoring
                   region runs independently and reports degraded battery
                   without halting navigation. */

            state navigationRegion {
                doc /* Nav2 BT: plan → control → recover with retry counter. */

                entry;
                    then planning;

                state planning {
                    doc /* Computing global path via ComputePathToPose action.
                           Nav2 PlannerServer with RateController at 1 Hz.
                           Error codes: NO_VALID_PATH, GOAL_OUTSIDE_MAP,
                           START_OCCUPIED, TIMEOUT. */
                    do send new MissionCommand("compute_path") via navPort;
                }
                state controlling {
                    doc /* Following path via FollowPath action.
                           Nav2 ControllerServer at 20 Hz control loop.
                           Error codes: PATIENCE_EXCEEDED,
                           FAILED_TO_MAKE_PROGRESS, NO_VALID_CONTROL. */
                    do send new MissionCommand("follow_path") via navPort;
                }
                state recovering {
                    doc /* Recovery behavior active after planning or control
                           failure. Nav2 BehaviorServer executes RoundRobin:
                           ClearEntireCostmap, Spin(1.57 rad), Wait(5 s),
                           BackUp(0.3 m at 0.15 m/s). Retry count incremented
                           per recovery cycle, max 6 before failure. */
                    entry send new MissionCommand("clear_costmap") via navPort;
                    exit send new TelemetryFrame("recovery_ended") via operatorPort;
                }
                state exhausted {
                    doc /* Retry limit reached from within navigation region. */
                }

                // Internal transitions within navigationRegion
                transition pathReady
                    first planning accept PathComputed via navPort then controlling;
                transition controlFailure
                    first controlling accept ControlError via navPort then recovering;
                transition controlTimeout
                    first controlling accept after 60 [s] then recovering;
                transition retryNavigation
                    first recovering
                    if retryCount < 6
                    do send new MissionCommand("backup_clear_spin") via navPort
                    then planning;
                transition recoveryTimeout
                    first recovering accept after 5 [s] then planning;
                transition retryExhausted
                    first recovering accept when retryCount >= 6 then exhausted;
            }

            state monitoringRegion {
                doc /* Battery-level monitoring concurrent with navigation.
                       Hysteresis between 0.20 and 0.30 prevents chatter. */

                entry;
                    then nominal;

                state nominal {
                    doc /* Battery within safe operating range. */
                }
                state degraded {
                    doc /* Battery below operating threshold. */
                    do send new TelemetryFrame("low_battery_warn") via operatorPort;
                }

                transition toDegraded
                    first nominal accept when batteryLevel < 0.20 then degraded;
                transition toNominal
                    first degraded accept when batteryLevel >= 0.30 then nominal;
            }
        }

        state atPickup {
            doc /* Robot arrived at pickup location, awaiting package load. */
            entry send new TelemetryFrame("arrived_pickup") via operatorPort;
        }
        state atDropoff {
            doc /* Robot arrived at delivery destination, awaiting unload. */
            entry send new TelemetryFrame("arrived_dropoff") via operatorPort;
        }
        state manual {
            doc /* Operator has taken manual control via joystick/gamepad. */
        }
        state failed {
            doc /* Navigation failed after 6 recovery attempts.
                   Requires operator intervention or autonomous return. */
            entry send new TelemetryFrame("navigation_failed") via operatorPort;
        }

        // EVENT-TRIGGERED transitions via ports (delivery order lifecycle)
        transition receiveOrder
            first idle accept OrderReceived via dispatchPort then navigating;
        transition arrivedAtPickup
            first navigating accept GoalReached via navPort then atPickup;
        transition packageLoaded
            first atPickup accept PackageLoaded via dispatchPort then navigating;
        transition arrivedAtDropoff
            first navigating accept GoalReached via navPort then atDropoff;
        transition packageUnloaded
            first atDropoff accept PackageUnloaded via dispatchPort then navigating;
        transition arrivedAtBase
            first navigating accept GoalReached via navPort then idle;

        // Failure and manual override
        transition navigationFailed
            first navigating accept RecoveryExhausted via navPort then failed;
        transition manualTakeover
            first navigating accept ManualOverrideCmd via operatorPort then manual;
        transition resumeFromManual
            first manual accept OrderReceived via dispatchPort then navigating;

        // GUARD CONDITION: reset from failure
        transition resetFromFailed
            first failed if retryCount == 0 then idle;
    }

    // ---- Delivery mission action flow (3-way fork + for-loop + nested if-else) ----

    attribute def Waypoint {
        doc /* Geographic waypoint for Nav2 NavigateToPose goal. */
        attribute lat : Real;
        attribute lon : Real;
    }

    attribute def DeliveryItem {
        doc /* Single manifest line-item with delivery policy flags. */
        attribute customerId : String;
        attribute requiresSignature : Boolean;
        attribute customerPresent : Boolean;
        attribute dropoffWaypoint : Waypoint;
    }

    // Parameterized action type definitions (referenced by DeliveryMission body)
    action def NavigateToWaypoint {
        doc /* Send NavigateToPose goal to a Waypoint; Nav2 plans/controls/recovers. */
        in attribute target : Waypoint;
    }
    action def AwaitSignature {
        doc /* Block awaiting customer signature capture (tablet or mobile). */
        out attribute received : Boolean;
    }
    action def HandoffWithSig {
        doc /* Signature-captured handoff path. */
        in attribute target : DeliveryItem;
    }
    action def ReturnPackage {
        doc /* Customer refused signature: return package to depot. */
        in attribute target : DeliveryItem;
    }
    action def HandoffToCustomer {
        doc /* Direct customer handoff (no signature required). */
        in attribute target : DeliveryItem;
    }
    action def LeaveAtDoor {
        doc /* Unattended drop at designated safe spot, photo proof. */
        in attribute target : DeliveryItem;
    }
    action def NotifyCustomer {
        doc /* Push per-item delivery notification to customer app. */
        in attribute target : DeliveryItem;
    }
    action def UpdateETA {
        doc /* Refresh ETA for remaining manifest items based on current progress. */
    }
    action def CheckBatteryLevel {
        doc /* Sample battery level; returns normalized [0..1] charge. */
        out attribute level : Real;
    }

    action def DeliveryMission {
        doc /* End-to-end delivery with 3-way parallel initialization (fork/join),
               per-item manifest iteration (for-loop) with nested if-else decisions
               (signature → handoff-or-return; else customer-present → handoff-or-leave),
               and per-iteration fork/join for telemetry + ETA + battery checks.
               Action references bind the loop variable `order` to parameterized
               action definitions via `in attribute redefines target = order`. */

        attribute manifest : DeliveryItem [*];

        first start;

        // FORK: 3-way parallel initialization (Nav2 + manifest + battery sample)
        then fork;
            then initNav2;
            then loadManifest;
            then primeBattery;

            action initNav2 {
                doc /* Bring up Nav2 stack via lifecycle manager.
                       Configure and activate all Nav2 servers. */
            }
                then j1;
            action loadManifest {
                doc /* Fetch manifest from dispatch: ordered DeliveryItems
                       with dropoff waypoints and signature flags. */
            }
                then j1;
            action primeBattery : CheckBatteryLevel;
                then j1;
        join j1;

        // Pickup phase (sequential)
        then action navigateToPickup {
            doc /* Send NavigateToPose goal to pickup waypoint.
                   Nav2 handles planning, control, and recovery. */
        }
        then action waitForLoading {
            doc /* Wait at pickup until all manifest packages placed on platform.
                   Confirm via weight sensor or operator signal. */
        }

        // FOR-LOOP: iterate over manifest with nested decisions + per-iter fork/join
        then for order in manifest {
            action navigateTo : NavigateToWaypoint {
                doc /* Send NavigateToPose goal to this order's dropoff waypoint. */
                in attribute redefines target = order.dropoffWaypoint;
            }
            then if order.requiresSignature {
                action awaitSig : AwaitSignature {
                    doc /* Block on tablet for customer signature. */
                }
                then if awaitSig.received {
                    action signedHandoff : HandoffWithSig {
                        doc /* Signature captured; handoff completed. */
                        in attribute redefines target = order;
                    }
                } else {
                    action returnPkg : ReturnPackage {
                        doc /* Signature refused; queue package for return. */
                        in attribute redefines target = order;
                    }
                }
            } else {
                if order.customerPresent {
                    action directHandoff : HandoffToCustomer {
                        doc /* Customer present; direct handoff, no signature. */
                        in attribute redefines target = order;
                    }
                } else {
                    action doorDrop : LeaveAtDoor {
                        doc /* No customer; leave at designated safe spot, photo proof. */
                        in attribute redefines target = order;
                    }
                }
            }
            // PER-ITERATION fork: notify customer + update ETA + sample battery
            then fork;
                then notifyCustomer;
                then updateETA;
                then checkBattery;

                action notifyCustomer : NotifyCustomer {
                    in attribute redefines target = order;
                }
                    then j2;
                action updateETA : UpdateETA;
                    then j2;
                action checkBattery : CheckBatteryLevel;
                    then j2;
            join j2;
        }

        then action returnToBase {
            doc /* Navigate back to charging station after full manifest complete. */
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 4b. SEQUENCE DIAGRAMS (inter-component message protocols)
    //     Uses event occurrence + message constructs for proper
    //     sequence diagram rendering with lifelines.
    // ═══════════════════════════════════════════════════════════════

    part def ExternalClient {
        doc /* External system that sends navigation goals
               (RViz, fleet manager, or mission planner). */
    }

    // ---- NavigateToPose Happy Path (sequence diagram) ----

    occurrence navigateToPoseHappyPath {
        doc /* Nav2 NavigateToPose action protocol — successful navigation.

               Modeled from ACTUAL Nav2 source code analysis:
               - BtNavigator is the sole orchestrator (never publishes cmd_vel)
               - All inter-server communication uses ROS2 actions (SYNC)
               - cmd_vel is topic-level output (ASYNC)
               - Planning at 1 Hz, control at 20 Hz (concurrent in Nav2,
                 shown sequentially here for clarity)

               Lifelines: client, btNavigator, plannerServer,
                          controllerServer, velocitySmoother */

        part client {
            event occurrence sendGoal;
            then event occurrence receiveFeedback;
            then event occurrence receiveResult;
        }

        part plannerServer {
            event occurrence receiveComputeGoal;
            then event occurrence returnPath;
        }

        part btNavigator {
            event occurrence receiveGoal;
            then event occurrence requestPath;
            then event occurrence receivePath;
            then event occurrence sendFollowPath;
            then event occurrence receiveControlFeedback;
            then event occurrence forwardFeedback;
            then event occurrence receiveGoalReached;
            then event occurrence reportResult;
        }

        part controllerServer {
            event occurrence receiveFollowGoal;
            then event occurrence publishCmdVel;
            then event occurrence sendFeedback;
            then event occurrence reportGoalReached;
        }

        part velocitySmoother {
            event occurrence receiveCmdVel;
        }

        // ── Messages ──

        // Messages with temporal ordering (then) for correct vertical sequencing
        message navGoal from client.sendGoal to btNavigator.receiveGoal;
        then message computePathGoal from btNavigator.requestPath to plannerServer.receiveComputeGoal;
        then message computePathResult from plannerServer.returnPath to btNavigator.receivePath;
        then message followPathGoal from btNavigator.sendFollowPath to controllerServer.receiveFollowGoal;
        then message cmdVelPublish from controllerServer.publishCmdVel to velocitySmoother.receiveCmdVel;
        then message followFeedback from controllerServer.sendFeedback to btNavigator.receiveControlFeedback;
        then message navFeedback from btNavigator.forwardFeedback to client.receiveFeedback;
        then message goalReached from controllerServer.reportGoalReached to btNavigator.receiveGoalReached;
        then message navResult from btNavigator.reportResult to client.receiveResult;
    }

    // ---- NavigateToPose Recovery Path (sequence diagram) ----

    occurrence navigateToPoseRecovery {
        doc /* Nav2 NavigateToPose with recovery — planner fails, BtNavigator
               triggers spin recovery via behavior_server, then retries.

               Shows the BT RecoveryNode pattern: when planning fails,
               the outer RecoveryNode triggers recovery behaviors
               (spin, wait, backup) before retrying the planning pipeline.
               Recovery behaviors publish cmd_vel directly, bypassing
               the controller_server.

               Lifelines: client, btNavigator, plannerServer,
                          behaviorServer, controllerServer */

        part client {
            event occurrence sendGoal;
            then event occurrence receiveResult;
        }

        part plannerServer {
            event occurrence receiveGoalFail;
            then event occurrence receiveGoalRetry;
            then event occurrence returnRetryPath;
        }

        part btNavigator {
            event occurrence receiveGoal;
            then event occurrence requestPathFail;
            then event occurrence triggerSpin;
            then event occurrence spinComplete;
            then event occurrence retryPath;
            then event occurrence receiveRetryPath;
            then event occurrence sendFollowPath;
            then event occurrence receiveGoalReached;
            then event occurrence reportResult;
        }

        part behaviorServer {
            event occurrence receiveSpinGoal;
            then event occurrence reportSpinDone;
        }

        part controllerServer {
            event occurrence receiveFollowGoal;
            then event occurrence reportGoalReached;
        }

        // ── Messages ──

        // Messages with temporal ordering (then) for correct vertical sequencing
        message navGoal from client.sendGoal to btNavigator.receiveGoal;
        then message planFail from btNavigator.requestPathFail to plannerServer.receiveGoalFail;
        then message spinRequest from btNavigator.triggerSpin to behaviorServer.receiveSpinGoal;
        then message spinDone from behaviorServer.reportSpinDone to btNavigator.spinComplete;
        then message replan from btNavigator.retryPath to plannerServer.receiveGoalRetry;
        then message replanResult from plannerServer.returnRetryPath to btNavigator.receiveRetryPath;
        then message followPath from btNavigator.sendFollowPath to controllerServer.receiveFollowGoal;
        then message goalReached from controllerServer.reportGoalReached to btNavigator.receiveGoalReached;
        then message navResult from btNavigator.reportResult to client.receiveResult;
    }

    // ═══════════════════════════════════════════════════════════════
    // 5. REQUIREMENTS (non-ROS2)
    // ═══════════════════════════════════════════════════════════════

    concern def DeliveryReliability {
        doc /* The robot must complete deliveries reliably in outdoor
               conditions including rain, wind, and uneven terrain. */
    }

    concern def PedestrianSafety {
        doc /* The robot must operate safely on shared pedestrian paths. */
    }

    // ---- Performance requirements (standalone defs for satisfy links) ----

    requirement def MaxSpeedReq {
        doc /* Maximum speed on pedestrian paths: 1.5 m/s. */
        subject robot : GroundRobotWithNav2;
        require constraint { robot.maxSpeedMs <= 1.5 }
    }

    requirement def OutdoorEnduranceReq {
        doc /* Minimum 6 hours outdoor operation on single charge. */
        subject robot : GroundRobotWithNav2;
        require constraint { robot.enduranceHours >= 6.0 }
    }

    requirement def PayloadCapacityReq {
        doc /* Minimum 10 kg payload for package delivery. */
        subject robot : GroundRobotWithNav2;
        require constraint { robot.payloadCapacityKg >= 10.0 }
    }

    requirement def GPSAccuracyReq {
        doc /* GPS-aided localization within 1 meter outdoors. */
        subject robot : GroundRobotWithNav2;
    }

    // ---- Safety requirements ----

    requirement def PedestrianBrakingReq {
        doc /* Full stop within 0.3 seconds of pedestrian detection. */
        frame concern PedestrianSafety;
        subject robot : GroundRobotWithNav2;
    }

    requirement def WeatherResistanceReq {
        doc /* IP67 rating for operation in rain and snow. */
        subject robot : GroundRobotWithNav2;
    }

    // ═══════════════════════════════════════════════════════════════
    // 6. VERIFICATION (non-ROS2)
    // ═══════════════════════════════════════════════════════════════

    verification def EnduranceFieldTest {
        doc /* Run delivery route loop for 6+ hours outdoors. */
        subject testRobot : GroundRobotWithNav2;
        action def RunFieldLoop {
            doc /* Execute standard campus delivery loop until
                   battery reaches 10%. Record elapsed time. */
        }
    }

    verification def PedestrianSafetyTest {
        doc /* Verify braking response with pedestrian dummy. */
        subject testRobot : GroundRobotWithNav2;
        action def RunBrakingTest {
            doc /* Drive at max speed, deploy dummy pedestrian
                   at 3m range, measure stopping distance and time. */
        }
    }

    analysis def DeliveryEfficiencyAnalysis {
        doc /* Analyze delivery throughput vs. battery/distance trade-offs. */
        subject robot : GroundRobotWithNav2;
        return deliveriesPerCharge : Real;
        objective {
            doc /* Maximize deliveries per charge cycle by optimizing
                   route selection and speed profiles. */
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 6b. ALLOCATION (non-ROS2)
    // ═══════════════════════════════════════════════════════════════

    allocation def SoftwareToHardware {
        doc /* Maps ROS2 software nodes to physical compute platform.
               All autonomy software runs on the Jetson AGX Orin. */
        end softwareNode;
        end hardwareNode;
    }

    // ═══════════════════════════════════════════════════════════════
    // 6b. SUBSYSTEM DECOMPOSITION
    //     System → Subsystem → [Sub-subsystem] → Element, variable depth.
    //
    //        GroundRobotWithNav2
    //         ├─ structure : MechanicalStructure
    //         ├─ power : PowerSystem
    //         ├─ sensors : SensorSuite
    //         │    ├─ lidar : LidarSubsystem      {hardware, driver}
    //         │    ├─ depthCamera : DepthCameraSubsystem {hardware, driver}
    //         │    └─ imu : ImuSubsystem          {hardware, driver}
    //         ├─ compute : ComputeSystem
    //         ├─ autonomyStack : Nav2AutonomyStack
    //         │    ├─ perception : PerceptionSubsystem
    //         │    ├─ localization : LocalizationSubsystem
    //         │    └─ nav2 : Nav2Stack  (library composite; own internal depth)
    //         └─ tfTree : FrameSubsystem
    //
    //     Rationale mirrors showcase_agr_full.sysml:
    //       • SensorSuite fuses sensor hardware with its ROS2 driver per
    //         channel — swapping commercial sensors is single-subsystem.
    //       • Nav2AutonomyStack delegates planning/control/safety to the
    //         vendor Nav2Stack composite (already depth-2 internally),
    //         so only custom perception + localization live as siblings.
    // ═══════════════════════════════════════════════════════════════

    // ---- Sensor channel sub-subsystems (hardware + driver fused) ----

    part def LidarSubsystem {
        doc /* 3D LiDAR sensor channel for outdoor use. Hardware + Nav2 driver
               co-located for commercial-alternative substitution coherence. */
        part hardware : LidarUnit;
        part driver : Nav2LidarDriver;
    }

    part def DepthCameraSubsystem {
        doc /* RGB-D depth camera sensor channel. Driver publishes
               pointcloud2 + rgb image streams. */
        part hardware : DepthCameraUnit;
        part driver : DepthCameraDriver;
    }

    part def ImuSubsystem {
        doc /* 9-DOF IMU with magnetometer for outdoor heading estimation. */
        part hardware : ImuUnit;
        part driver : Nav2ImuDriver;
    }

    // ---- Sensor suite (aggregates sensor channels) ----

    part def SensorSuite {
        doc /* Sensor payload aggregating lidar, depth camera, and IMU channels.
               Rollup attributes support sensor-payload trade studies. */
        part lidar : LidarSubsystem;
        part depthCamera : DepthCameraSubsystem;
        part imu : ImuSubsystem;
        attribute totalMassKg : Real;
        attribute totalPowerW : Real;
    }

    // ---- Autonomy functional sub-subsystems (custom, alongside Nav2Stack) ----

    part def PerceptionSubsystem {
        doc /* Custom perception stage upstream of Nav2: pointcloud filtering
               to strip ground plane and downsample for Nav2 costmap input. */
        part pointcloudFilter : PointCloudFilter;
    }

    part def LocalizationSubsystem {
        doc /* Custom localization: EKF fusion of IMU + wheel odometry + GPS.
               Publishes pose downstream to Nav2 ControllerServer. */
        part ekfLocalizer : Nav2EKFLocalizer;
    }

    // ---- Nav2-based autonomy stack ----

    part def Nav2AutonomyStack {
        doc /* Autonomy stack leveraging the stock Nav2 behavior tree for
               planning, control, and recovery. Custom perception and
               localization feed into Nav2 via the costmap and controller
               state inputs respectively. */
        part perception : PerceptionSubsystem;
        part localization : LocalizationSubsystem;
        part nav2 : Nav2Stack;
    }

    // ---- Non-software subsystems ----

    part def MechanicalStructure {
        doc /* Outdoor delivery robot structural subsystem: chassis, 4WD
               drivetrain, and weatherproof enclosure housing compute +
               electronics. */
        part chassis : Chassis;
        part drivetrain : Drivetrain;
        part enclosure : WeatherproofEnclosure;
        attribute totalMassKg : Real;
    }

    part def PowerSystem {
        doc /* 6S LiPo battery subsystem for extended outdoor operation.
               Motor controllers and distribution live in Nav2Stack's
               vendor hardware assumptions; modeled as a single battery
               here per the simpler delivery-robot scope. */
        part battery : Battery;
        attribute totalCapacityAh : Real;
        attribute nominalVoltageV : Real;
    }

    part def ComputeSystem {
        doc /* On-board compute subsystem hosting all ROS2 nodes
               (custom + Nav2 servers). */
        part computer : OnboardComputer;
    }

    part def FrameSubsystem {
        doc /* TF2 coordinate frame tree: root frames from StandardFrameTree
               plus per-sensor child frames for lidar, depth camera, and IMU.
               Static-transform connections between base_link and sensor
               frames are declared at the system-composition level. */
        part frames : StandardFrameTree;
        part lidarFrame : CoordinateFrame { :>> frameId = "lidar_link"; }
        part depthCameraFrame : CoordinateFrame { :>> frameId = "depth_camera_link"; }
        part imuFrame : CoordinateFrame { :>> frameId = "imu_link"; }
    }

    // ═══════════════════════════════════════════════════════════════
    // 7. SYSTEM COMPOSITION
    // ═══════════════════════════════════════════════════════════════

    part def GroundRobotWithNav2 {
        doc /* Complete outdoor delivery robot with Nav2 navigation.
               Multi-domain model: physical + electrical + ROS2 + Nav2.

               System-level requirement satisfaction is declared at package
               level (see the GroundRobotWithNav2Requirements group and the
               `satisfy … by theRobot;` statement below) so that structural
               views expose only composition, not requirement assertions. This
               follows OMG SysML v2 §7.21.4 which documents the `by` shorthand
               as equivalent to the nested-in-def form. */

        attribute totalMassKg : Real = 18.0;
        attribute maxSpeedMs : Real = 1.5;
        attribute enduranceHours : Real = 7.0;
        attribute payloadCapacityKg : Real = 15.0;

        // ──── Subsystem decomposition ────
        // System → Subsystem → [Sub-subsystem] → Element, variable depth.

        part structure : MechanicalStructure;
        part power : PowerSystem;
        part sensors : SensorSuite;
        part compute : ComputeSystem;
        part autonomyStack : Nav2AutonomyStack;
        part tfTree : FrameSubsystem;

        // ──── Static transforms (TF2 sensor mounts) ────

        connection lidarMount : StaticTransform
            connect tfTree.frames.baseLinkFrame to tfTree.lidarFrame;
        connection depthCameraMount : StaticTransform
            connect tfTree.frames.baseLinkFrame to tfTree.depthCameraFrame;
        connection imuMount : StaticTransform
            connect tfTree.frames.baseLinkFrame to tfTree.imuFrame;

        // ──── Custom data flow (sensors → custom autonomy) ────

        connection depthToFilter : TopicConnection
            connect sensors.depthCamera.driver.sensorPub
                 to autonomyStack.perception.pointcloudFilter.rawSub;
        connection imuToEkf : TopicConnection
            connect sensors.imu.driver.sensorPub
                 to autonomyStack.localization.ekfLocalizer.sensorSub;
        connection scanToEkf : TopicConnection
            connect sensors.lidar.driver.sensorPub
                 to autonomyStack.localization.ekfLocalizer.scanSub;

        // ──── Custom → Nav2 integration ────

        connection scanToLocalCostmap : TopicConnection
            connect sensors.lidar.driver.sensorPub
                 to autonomyStack.nav2.localCostmap.mapSub;
        connection scanToGlobalCostmap : TopicConnection
            connect sensors.lidar.driver.sensorPub
                 to autonomyStack.nav2.globalCostmap.mapSub;
        connection odomToController : TopicConnection
            connect autonomyStack.localization.ekfLocalizer.posePub
                 to autonomyStack.nav2.controller.stateSub;

        // ──── Operational modes (non-ROS2) ────
        exhibit state deliveryMode : DeliveryModes;

        // ──── Software-to-hardware allocation ────
        allocate sensors.lidar.driver to compute.computer;
        allocate sensors.depthCamera.driver to compute.computer;
        allocate sensors.imu.driver to compute.computer;
        allocate autonomyStack.perception.pointcloudFilter to compute.computer;
        allocate autonomyStack.localization.ekfLocalizer to compute.computer;
        allocate autonomyStack.nav2 to compute.computer;
    }

    // ═══════════════════════════════════════════════════════════════
    // 7b. SYSTEM INSTANCE + REQUIREMENT SATISFACTION
    //     Per OMG SysML v2 §7.21.4 (spec p. 136), satisfy-requirement
    //     usages may be declared inside a part def (implicit self subject)
    //     OR at package level with an explicit `by` clause. The latter
    //     form is used here so structural views expose only composition.
    //
    //     See docs/SysMLv2_Satisfy_Placement_Clarification.md for the
    //     full spec analysis.
    // ═══════════════════════════════════════════════════════════════

    requirement def GroundRobotWithNav2Requirements {
        doc /* System-level requirements group for the outdoor delivery robot.
               Binds the GroundRobotWithNav2 as subject; aggregates five
               requirements with per-requirement rationale preserved from the
               original satisfy docs. */

        subject robot : GroundRobotWithNav2;

        requirement maxSpeed : MaxSpeedReq {
            doc /* Nav2 ControllerServer max_vel parameter set to 1.5 m/s;
                   VelocitySmoother enforces acceleration limits. */
        }
        requirement outdoorEndurance : OutdoorEnduranceReq {
            doc /* 6S LiPo at 16 Ah with 40 W Orin + 19 W sensor load
                   provides 7+ hours continuous outdoor operation. */
        }
        requirement payloadCapacity : PayloadCapacityReq {
            doc /* Steel tube chassis rated for 33 kg total; with 18 kg
                   robot mass, 15 kg payload capacity remains. */
        }
        requirement pedestrianBraking : PedestrianBrakingReq {
            doc /* CollisionMonitor triggers zero-velocity command within
                   one control cycle (50 ms) upon pedestrian detection. */
        }
        requirement weatherResistance : WeatherResistanceReq {
            doc /* WeatherproofEnclosure provides IP67 rating for all
                   electronics; sensor units are individually sealed. */
        }
    }

    // Package-level system instance + satisfaction assertion.
    part theRobot : GroundRobotWithNav2;
    satisfy requirement robotRqts : GroundRobotWithNav2Requirements by theRobot;

    // ═══════════════════════════════════════════════════════════════
    // 8. VIEWS
    //    Rules (validated via A/B experiments, see debug/test15):
    //    - attribute depth = 1; in every view (prevents stdlib noise)
    //    - double expose: expose X; expose X::*; (bounds exposed set)
    //    - render asTreeDiagram; for structural decomposition
    //    - Tom Sawyer auto-detects diagram type from model elements
    // ═══════════════════════════════════════════════════════════════

    private import Views::*;

    // ---- Physical structure (tree decomposition) ----

    view physicalStructure {
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2;
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Autonomy topology (nodes + ports + connections) ----

    view autonomyTopology {
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2;
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Per-subsystem drill-down views (additive) ----

    view mechanicalStructureView {
        doc /* Outdoor delivery robot mechanical subsystem:
               chassis, drivetrain, weatherproof enclosure. */
        expose ShowcaseAGRNav2Full::MechanicalStructure;
        expose ShowcaseAGRNav2Full::MechanicalStructure::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    view powerSystemView {
        doc /* 6S LiPo battery-only power subsystem. */
        expose ShowcaseAGRNav2Full::PowerSystem;
        expose ShowcaseAGRNav2Full::PowerSystem::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    view sensorSuiteView {
        doc /* Sensor suite: lidar, depth camera, and IMU channels, each
               fusing hardware unit + ROS2 driver under a sensor-subsystem. */
        expose ShowcaseAGRNav2Full::SensorSuite;
        expose ShowcaseAGRNav2Full::SensorSuite::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    view autonomyStackDetail {
        doc /* Nav2-based autonomy stack: custom perception and
               localization sub-subsystems alongside the Nav2Stack
               vendor composite (which internally contains the full
               Nav2 server set). */
        expose ShowcaseAGRNav2Full::Nav2AutonomyStack;
        expose ShowcaseAGRNav2Full::Nav2AutonomyStack::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Behavioral: delivery state machine ----

    view deliveryModes {
        expose ShowcaseAGRNav2Full::DeliveryModes;
        expose ShowcaseAGRNav2Full::DeliveryModes::*;
        attribute depth = 1;
    }

    // ---- Behavioral: delivery mission action flow ----

    view deliveryMissionFlow {
        expose ShowcaseAGRNav2Full::DeliveryMission;
        expose ShowcaseAGRNav2Full::DeliveryMission::*;
        attribute depth = 1;
    }

    // ---- Requirements ----

    view systemRequirements {
        expose ShowcaseAGRNav2Full::MaxSpeedReq;
        expose ShowcaseAGRNav2Full::OutdoorEnduranceReq;
        expose ShowcaseAGRNav2Full::PayloadCapacityReq;
        expose ShowcaseAGRNav2Full::GPSAccuracyReq;
        expose ShowcaseAGRNav2Full::PedestrianBrakingReq;
        expose ShowcaseAGRNav2Full::WeatherResistanceReq;
        render asTreeDiagram;
        attribute depth = 1;
    }

    // ---- Verification & analysis ----

    view verificationPlan {
        expose ShowcaseAGRNav2Full::EnduranceFieldTest;
        expose ShowcaseAGRNav2Full::PedestrianSafetyTest;
        expose ShowcaseAGRNav2Full::DeliveryEfficiencyAnalysis;
        render asTreeDiagram;
        attribute depth = 1;
    }

    // ---- Software-to-hardware allocation ----

    view softwareAllocation {
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2;
        expose ShowcaseAGRNav2Full::SoftwareToHardware;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Sequence diagrams ----

    view nav2HappyPathSequence {
        expose ShowcaseAGRNav2Full::navigateToPoseHappyPath;
        attribute depth = 1;
    }

    view nav2RecoverySequence {
        expose ShowcaseAGRNav2Full::navigateToPoseRecovery;
        attribute depth = 1;
    }
    
}

