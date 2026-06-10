package ShowcaseAGRFull {
    doc /* Full multi-domain architecture model of an Autonomous Ground Robot.

       This model demonstrates that the SysML v2 architecture model captures
       the COMPLETE system — mechanical structure, electrical power, thermal
       constraints, use cases, requirements, V&V, and allocation — while the
       ros2-sysmlv2 bridge pipeline extracts ONLY the software/communication
       layer (nodes, ports, connections, frames) for ROS2 code generation.

       Non-ROS2 elements (mechanical parts, electrical buses, use cases,
       requirements, views) pass through the pipeline transparently. This is
       the library harness pattern: the library's type hierarchy defines the
       projection.

       Subsystems:
         - Physical: chassis, drivetrain, sensor mounts
         - Electrical: battery, power distribution, motor controllers
         - Autonomy (ROS2): sensors, perception, estimation, planning,
           control, safety, map, coordination
         - Requirements: performance, safety, operational
         - V&V: verification and analysis definitions
         - Views: structural, behavioral, requirements, V&V, allocation */

    // ═══════════════════════════════════════════════════════════════
    // Standard library imports
    // ═══════════════════════════════════════════════════════════════

    private import ScalarValues::*;
    private import SI::*;
    private import StandardViewDefinitions::*;

    // ros2-sysmlv2 library imports (only these define the ROS2 projection)
    private import ros2_sysmlv2_foundation::*;
    private import ros2_sysmlv2_geometry_msgs::*;
    private import ros2_sysmlv2_sensor_msgs::*;
    private import ros2_sysmlv2_nav_msgs::*;
    private import ros2_sysmlv2_comm::*;
    private import ros2_sysmlv2_lifecycle::*;
    private import ros2_sysmlv2_tf2::*;
    private import ros2_sysmlv2_params::*;
    private import ros2_sysmlv2_archetypes::*;

    // ═══════════════════════════════════════════════════════════════
    // 1. PHYSICAL STRUCTURE (non-ROS2 — invisible to pipeline)
    // ═══════════════════════════════════════════════════════════════

    // ---- Mechanical attribute types ----

    attribute def MassKg { attribute value : Real; }
    attribute def LengthM { attribute value : Real; }
    attribute def VoltageV { attribute value : Real; }
    attribute def CurrentA { attribute value : Real; }
    attribute def PowerW { attribute value : Real; }
    attribute def CapacityAh { attribute value : Real; }
    attribute def SpeedMs { attribute value : Real; }
    attribute def TemperatureC { attribute value : Real; }

    // ---- Mechanical part definitions ----

    part def Chassis {
        doc /* Welded aluminum 6061-T6 frame, 600mm x 400mm x 200mm. */
        attribute massKg : Real = 3.5;
        attribute lengthM : Real = 0.6;
        attribute widthM : Real = 0.4;
        attribute heightM : Real = 0.2;
        attribute material : String = "aluminum_6061_T6";
    }

    part def Wheel {
        doc /* 150mm diameter rubber tire on aluminum hub. */
        attribute diameterM : Real = 0.15;
        attribute massKg : Real = 0.3;
        attribute maxLoadKg : Real = 15.0;
    }

    part def Drivetrain {
        doc /* 4-wheel differential drive with independent motor per wheel. */
        part frontLeft : Wheel;
        part frontRight : Wheel;
        part rearLeft : Wheel;
        part rearRight : Wheel;
        attribute gearRatio : Real = 30.0;
    }

    part def SensorBracket {
        doc /* Adjustable mounting bracket for sensors. */
        attribute massKg : Real = 0.1;
        attribute maxPayloadKg : Real = 2.0;
    }

    part def LidarUnit {
        doc /* RPLidar A3 — 360° 2D LiDAR scanner.
               Physical sensor hardware, not the ROS2 driver node. */
        attribute massKg : Real = 0.19;
        attribute rangeM : Real = 25.0;
        attribute scanRateHz : Real = 10.0;
        attribute powerW : Real = 5.0;
    }

    part def ImuUnit {
        doc /* BNO055 9-axis IMU. */
        attribute massKg : Real = 0.01;
        attribute updateRateHz : Real = 200.0;
        attribute powerW : Real = 0.1;
    }

    part def StereoCamera {
        doc /* Intel RealSense D435i depth camera. */
        attribute massKg : Real = 0.072;
        attribute resolutionWidth : Integer = 640;
        attribute resolutionHeight : Integer = 480;
        attribute fpsHz : Real = 30.0;
        attribute powerW : Real = 3.5;
    }

    // ═══════════════════════════════════════════════════════════════
    // 2. ELECTRICAL SUBSYSTEM (non-ROS2 — invisible to pipeline)
    // ═══════════════════════════════════════════════════════════════

    part def Battery {
        doc /* 4S LiPo battery pack. */
        attribute voltageV : Real = 14.8;
        attribute capacityAh : Real = 10.0;
        attribute massKg : Real = 0.8;
        attribute maxDischargeC : Real = 25.0;
    }

    part def MotorController {
        doc /* Dual H-bridge motor controller for 2 motors. */
        attribute maxCurrentA : Real = 30.0;
        attribute powerW : Real = 2.0;
        attribute massKg : Real = 0.05;
    }

    part def PowerDistributionBoard {
        doc /* Power distribution with voltage regulation. */
        attribute inputVoltageV : Real = 14.8;
        attribute output5V : Boolean = true;
        attribute output12V : Boolean = true;
        attribute massKg : Real = 0.03;
    }

    part def OnboardComputer {
        doc /* NVIDIA Jetson Orin NX — runs ROS2 Jazzy stack. */
        attribute massKg : Real = 0.12;
        attribute powerW : Real = 25.0;
        attribute ramGb : Integer = 16;
        attribute gpuCores : Integer = 1024;
    }

    // ═══════════════════════════════════════════════════════════════
    // 3. AUTONOMY STACK (ROS2 — extracted by pipeline)
    //    These part defs specialize ros2-sysmlv2 library types,
    //    making them visible to the bridge pipeline.
    // ═══════════════════════════════════════════════════════════════

    // ---- Sensors ----

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

    // ---- Perception ----

    part def ObstacleDetector :> PerceptionPipeline {
        doc /* Obstacle detection pipeline; satisfies detection range req. */
        satisfy requirement : ObstacleDetectionRangeReq {
            doc /* RPLidar A3 provides 25 m range, fused with D435i depth
                   for 3D detection. Validated at 3+ meters in all directions. */
        }
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

    // ---- Estimation ----

    part def EKFLocalizer :> Estimator {
        doc /* Extended Kalman Filter localizer; satisfies localization accuracy. */
        satisfy requirement : LocalizationAccuracyReq {
            doc /* EKF fuses IMU at 200 Hz and LiDAR scan matching for
                   5 cm RMS accuracy in mapped environments. */
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
            :>> topicName = "/odom_filtered";
            :>> qos = defaultQoS;
            out item :>> msg : Odometry;
        }
    }

    // ---- Planning ----

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
    }

    // ---- Control ----

    part def TrajectoryTracker :> Controller {
        doc /* Trajectory tracking controller; satisfies velocity limit. */
        satisfy requirement : MaxVelocityReq {
            doc /* max_linear_velocity parameter caps commanded velocity
                   at 2.0 m/s; enforced at the controller output. */
        }
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

    // ---- Safety chain ----

    part def AGRVelocitySmoother :> VelocityFilter {
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
    }

    part def CollisionGuard :> VelocityFilter {
        doc /* Safety velocity filter; satisfies e-stop and collision avoidance. */
        satisfy requirement : EmergencyStopReq {
            doc /* Monitors /scan for imminent collision; commands zero
                   velocity within one control cycle (20 ms at 50 Hz). */
        }
        satisfy requirement : CollisionAvoidanceReq {
            doc /* Maintains 0.3 m minimum clearance by scaling velocity
                   proportionally to nearest obstacle distance. */
        }
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
    }

    // ---- Map ----

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

    // ---- Coordination ----

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

    // ═══════════════════════════════════════════════════════════════
    // 4. USE CASES (non-ROS2 — invisible to pipeline)
    // ═══════════════════════════════════════════════════════════════

    part def Operator {
        doc /* Human operator who commands the robot remotely. */
    }

    part def Environment {
        doc /* Physical operating environment (indoor warehouse). */
    }

    use case def AutonomousNavigation {
        doc /* The robot navigates autonomously from point A to B,
               avoiding obstacles, within a mapped environment. */
        subject robot : AutonomousGroundRobot;
        actor operator : Operator;
    }

    use case def ManualOverride {
        doc /* The operator takes manual control, overriding
               autonomous navigation, via teleop joystick. */
        subject robot : AutonomousGroundRobot;
        actor operator : Operator;
    }

    use case def EmergencyStop {
        doc /* The robot immediately halts all motion upon receiving
               an emergency stop command or detecting a critical fault. */
        subject robot : AutonomousGroundRobot;
        actor operator : Operator;
    }

    use case def MappingMission {
        doc /* The robot explores an unknown environment, builds a map
               using SLAM, and saves it for future navigation. */
        subject robot : AutonomousGroundRobot;
        actor operator : Operator;
    }

    // ═══════════════════════════════════════════════════════════════
    // 5. BEHAVIORAL MODELING (non-ROS2)
    //    Exercises: substates, event-triggered transitions, guard
    //    conditions, fork/join, if-else decision nodes.
    // ═══════════════════════════════════════════════════════════════

    // ---- Event items for state machine triggers ----

    item def MissionCommand { attribute text : String; }
    item def TelemetryFrame { attribute text : String; }
    item def ManualOverrideEvent;
    item def EmergencyTrigger;
    item def ClearanceEvent;
    item def ObstacleDetected;
    item def GoalReached;

    // ---- Operational modes (rich state machine) ----

    state def OperationalModes {
        doc /* System-level operational modes with substates, parallel composite
               regions, entry/do/exit actions, event/time/change triggers,
               and transition effects. Distinct from the ROS2 node lifecycle
               (per-node level).

               The autonomous state is a parallel composite: navigationRegion
               (plan-execute-recover cycle) runs concurrently with safetyRegion
               (battery-level monitoring with hysteresis). Emergency events
               halt both regions simultaneously. */

        attribute batteryLevel : Real;

        // Ports for event routing (L18 pattern: accept X via portName)
        ref port commandPort;
        ref port safetyPort;

        entry;
            then idle;

        state idle {
            doc /* Robot powered on, all systems initialized, awaiting command. */
            entry send new TelemetryFrame("ready") via commandPort;
        }

        // PARALLEL COMPOSITE: autonomous runs navigation and safety concurrently
        state autonomous parallel {
            doc /* Robot executing autonomous navigation mission.
                   Navigation region and safety monitoring run in parallel
                   regions; both must be exited together on emergency or
                   manual takeover. */

            state navigationRegion {
                doc /* Plan-execute-recover-arrive cycle. */

                entry;
                    then planning;

                state planning {
                    doc /* Computing global path from current pose to goal. */
                    entry send new MissionCommand("plan_route") via commandPort;
                }
                state executing {
                    doc /* Following the planned path with local obstacle avoidance. */
                    do send new TelemetryFrame("status") via commandPort;
                }
                state recovering {
                    doc /* Recovery behavior active (spin, backup, or wait)
                           after a planning or control failure. */
                    entry send new MissionCommand("recover") via commandPort;
                    exit send new MissionCommand("resumed") via commandPort;
                }
                state arrived {
                    doc /* Goal waypoint reached; awaiting next command. */
                    entry send new TelemetryFrame("arrived") via commandPort;
                }

                transition planReady
                    first planning then executing;
                transition obstacleHit
                    first executing accept ObstacleDetected via safetyPort then recovering;
                transition recoveryDone
                    first recovering then planning;
                transition recoveryTimeout
                    first recovering accept after 30 [s] then planning;
                transition goalReached
                    first executing accept GoalReached via commandPort then arrived;
            }

            state safetyRegion {
                doc /* Battery-level safety monitoring concurrent with navigation.
                       Hysteresis between 0.25 and 0.30 prevents chatter. */

                entry;
                    then nominal;

                state nominal {
                    doc /* Battery within safe operating range. */
                }
                state degraded {
                    doc /* Battery approaching critical threshold. */
                    do send new TelemetryFrame("low_battery_warn") via commandPort;
                }

                transition toDegraded
                    first nominal accept when batteryLevel < 0.25 then degraded;
                transition toNominal
                    first degraded accept when batteryLevel >= 0.30 then nominal;
            }
        }

        state manual {
            doc /* Operator has taken manual control via teleop. */
        }
        state emergency {
            doc /* Emergency stop active; all motion halted. */
            entry send new MissionCommand("halt_motors") via safetyPort;
            do send new TelemetryFrame("emergency_active") via commandPort;
        }
        state charging {
            doc /* Robot docked and charging battery. */
        }

        // EVENT-TRIGGERED transitions via ports
        transition startMission
            first idle accept MissionCommand via commandPort then autonomous;
        transition takeControl
            first autonomous accept ManualOverrideEvent via commandPort then manual;
        transition releaseControl
            first manual accept MissionCommand via commandPort then autonomous;
        transition triggerEmergency
            first autonomous
            accept EmergencyTrigger via safetyPort
            do send new MissionCommand("emergency_stop") via commandPort
            then emergency;
        transition manualEmergency
            first manual accept EmergencyTrigger via safetyPort then emergency;
        transition clearEmergency
            first emergency accept ClearanceEvent via commandPort then idle;

        // GUARD CONDITION transitions (no event, pure condition)
        transition startCharging
            first idle if batteryLevel < 0.2 then charging;
        transition finishCharging
            first charging if batteryLevel > 0.9 then idle;

        // TIME + GUARD transition (L18 pattern: accept after T if G)
        transition rechargeTimeout
            first charging
            accept after 60 [s]
            if batteryLevel >= 0.95
            then idle;
    }

    // ---- Mission action flow (3-way fork + for-loop + nested if-else + per-iteration fork) ----

    attribute def Waypoint {
        doc /* Single mission waypoint with coordinates, handoff flag,
               and confirmation state. Used by the ExecuteMission for-loop. */
        attribute lat : Real;
        attribute lon : Real;
        attribute requiresHandoff : Boolean;
        attribute confirmed : Boolean;
    }

    // Parameterized action type definitions (referenced by ExecuteMission body)
    action def NavigateToWaypoint {
        doc /* Navigate to a target waypoint; parameter-bound via `redefines target`. */
        in attribute target : Waypoint;
    }
    action def DeliverPayload {
        doc /* Deliver payload at a target waypoint. */
        in attribute target : Waypoint;
    }
    action def AwaitOperatorConfirm {
        doc /* Wait for operator confirmation; returns boolean outcome. */
        out attribute confirmed : Boolean;
    }
    action def SendTelemetry {
        doc /* Publish per-waypoint telemetry frame to operator console. */
    }
    action def CheckBattery {
        doc /* Sample battery level; returns normalized [0..1] charge. */
        out attribute level : Real;
    }
    action def WarmupCompute {
        doc /* Load ML model weights into GPU memory. */
    }

    action def ExecuteMission {
        doc /* Mission execution with 3-way parallel initialization (fork/join),
               waypoint iteration loop (for-loop) with nested if-else decisions
               and per-iteration fork/join for telemetry + battery checks, and a
               final outcome decision (if-else). Action references bind the
               loop variable `waypoint` to parameterized action definitions
               via `in attribute redefines target = waypoint`. */

        attribute missionSuccess : Boolean;
        attribute waypoints : Waypoint [*];

        first start;

        // FORK: 3-way parallel initialization (sensors + map + GPU warmup)
        then fork;
            then initSensors;
            then loadMap;
            then warmupCompute;

            action initSensors {
                doc /* Power on and calibrate all sensor drivers. */
            }
                then j1;
            action loadMap {
                doc /* Load static map from map server or SLAM. */
            }
                then j1;
            action warmupCompute : WarmupCompute;
                then j1;
        join j1;

        // Sequential route planning once all subsystems are ready
        then action planRoute {
            doc /* Compute global path through all waypoints from current pose. */
        }

        // FOR-LOOP: iterate over waypoints with nested decisions + per-iter fork
        then for waypoint in waypoints {
            action navigate : NavigateToWaypoint {
                doc /* Follow planned path to this waypoint. */
                in attribute redefines target = waypoint;
            }
            then if waypoint.requiresHandoff {
                action awaitConfirm : AwaitOperatorConfirm {
                    doc /* Block until operator confirms handoff safety. */
                }
                then if awaitConfirm.confirmed {
                    action handoff : DeliverPayload {
                        doc /* Operator-supervised handoff at this waypoint. */
                        in attribute redefines target = waypoint;
                    }
                } else {
                    action skipWaypoint {
                        doc /* Operator denied handoff; skip to next waypoint. */
                    }
                }
            } else {
                action autonomousDelivery : DeliverPayload {
                    doc /* Fully autonomous delivery at this waypoint. */
                    in attribute redefines target = waypoint;
                }
            }
            // PER-ITERATION fork: telemetry + battery check run parallel to each iter
            then fork;
                then sendTelemetry;
                then checkBattery;
                action sendTelemetry : SendTelemetry;
                    then j2;
                action checkBattery : CheckBattery;
                    then j2;
            join j2;
        }

        // IF-ELSE: final mission outcome decision
        then if missionSuccess {
            action returnToBase {
                doc /* Navigate back to the charging station. */
            }
            then action shutdown {
                doc /* Safely power down all subsystems. */
            }
        } else {
            action handleFailure {
                doc /* Log failure, attempt recovery or alert operator. */
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 5b. SEQUENCE DIAGRAMS (inter-participant message exchanges)
    // ═══════════════════════════════════════════════════════════════

    // ---- Message types for inter-system communication ----

    // ---- External system participants ----

    part def BaseStation {
        doc /* Remote operator workstation with e-stop button,
               telemetry display, and wireless link to robot. */
    }

    // ---- Emergency Stop Protocol (sequence diagram) ----
    // Uses event occurrence + message constructs for proper
    // sequence diagram rendering with lifelines.

    occurrence emergencyStopProtocol {
        doc
        /* Emergency stop protocol modeled as an interaction sequence.
         *
         * Uses 'occurrence' container (not part def) so Syside Modeler
         * renders this as a sequence diagram with lifelines and message arrows.
         *
         * Shows the inter-participant message exchange when an operator
         * triggers an emergency stop. Includes both synchronous
         * (request-response with ordered occurrences) and asynchronous
         * (fire-and-forget) message flows across 5 participants.
         *
         * Lifelines: operator, baseStation, coordinator, tracker, guard
         */

        // ── Lifelines (participants) ──

        part operator {
            event occurrence triggerEstop;
        }

        part baseStation {
            event occurrence receiveEstop;
            then event occurrence relayEstop;
            then event occurrence receiveAck;
        }

        part coordinator {
            event occurrence receiveEstopCmd;
            then event occurrence sendCancel;
            then event occurrence receiveCancelAck;
            then event occurrence sendZeroVel;
            then event occurrence sendAck;
        }

        part tracker {
            event occurrence receiveCancelCmd;
            then event occurrence confirmCancel;
        }

        part guard {
            event occurrence receiveZeroVel;
        }

        // ── Messages (arrows between lifelines) ──

        // Messages with temporal ordering (then) for correct vertical sequencing
        message estopTrigger from operator.triggerEstop to baseStation.receiveEstop;
        then message estopRelay from baseStation.relayEstop to coordinator.receiveEstopCmd;
        then message cancelRequest from coordinator.sendCancel to tracker.receiveCancelCmd;
        then message cancelConfirm from tracker.confirmCancel to coordinator.receiveCancelAck;
        then message zeroVelocity from coordinator.sendZeroVel to guard.receiveZeroVel;
        then message haltReport from coordinator.sendAck to baseStation.receiveAck;
    }

    // ═══════════════════════════════════════════════════════════════
    // 6. REQUIREMENTS (non-ROS2 — invisible to pipeline,
    //    but preserved in architecture.json as metadata for
    //    future Analysis Model consumption)
    // ═══════════════════════════════════════════════════════════════

    // ---- Concerns ----

    concern def MissionEffectiveness {
        doc /* The robot must complete warehouse delivery missions
               reliably and efficiently. */
    }

    concern def OperationalSafety {
        doc /* The robot must operate safely in environments with
               human workers present. */
    }

    concern def SystemReliability {
        doc /* The robot must maintain continuous operation for
               an 8-hour warehouse shift. */
    }

    // ---- Performance requirements (each a standalone def for satisfy links) ----

    requirement def MaxVelocityReq {
        doc /* Maximum velocity shall not exceed 2.0 m/s in
               autonomous mode (warehouse safety limit). */
        subject robot : AutonomousGroundRobot;
        require constraint { robot.maxSpeedMs <= 2.0 }
    }

    requirement def MinEnduranceReq {
        doc /* Operational endurance shall be at least 4 hours
               on a single battery charge. */
        subject robot : AutonomousGroundRobot;
        require constraint { robot.enduranceHours >= 4.0 }
    }

    requirement def MaxMassReq {
        doc /* Total system mass shall not exceed 25 kg
               for safe manual handling. */
        subject robot : AutonomousGroundRobot;
        require constraint { robot.totalMassKg <= 25.0 }
    }

    requirement def LocalizationAccuracyReq {
        doc /* Localization accuracy shall be within 5 cm RMS
               in a mapped environment. */
        subject robot : AutonomousGroundRobot;
    }

    requirement def ObstacleDetectionRangeReq {
        doc /* Obstacles shall be detected at minimum 3 meters
               range in all directions. */
        subject robot : AutonomousGroundRobot;
    }

    // ---- Safety requirements ----

    requirement def EmergencyStopReq {
        doc /* The robot shall halt all motion within 0.5 seconds
               of receiving an emergency stop command. */
        frame concern OperationalSafety;
        subject robot : AutonomousGroundRobot;
    }

    requirement def CollisionAvoidanceReq {
        doc /* The robot shall maintain a minimum clearance of
               0.3 meters from all detected obstacles. */
        frame concern OperationalSafety;
        subject robot : AutonomousGroundRobot;
    }

    requirement def HumanDetectionReq {
        doc /* The robot shall detect human presence within
               5 meters and reduce speed to 0.5 m/s. */
        frame concern OperationalSafety;
        subject robot : AutonomousGroundRobot;
    }

    requirement def FailSafeReq {
        doc /* Upon loss of communication with the operator
               station for more than 10 seconds, the robot
               shall execute autonomous stop. */
        frame concern OperationalSafety;
        subject robot : AutonomousGroundRobot;
    }

    // ═══════════════════════════════════════════════════════════════
    // 7. VERIFICATION AND VALIDATION (non-ROS2)
    // ═══════════════════════════════════════════════════════════════

    verification def MassVerification {
        doc /* Verify MaxMassReq: weigh the fully assembled robot
               on a calibrated scale. Pass if mass <= 25 kg. */
        subject testRobot : AutonomousGroundRobot;
        action def WeighRobot {
            doc /* Place robot on scale, record mass. */
        }
    }

    verification def EnduranceVerification {
        doc /* Verify MinEnduranceReq: continuous navigation test
               in a warehouse environment. Pass if >= 4 hours. */
        subject testRobot : AutonomousGroundRobot;
        action def RunEnduranceTest {
            doc /* Run standard warehouse patrol until battery
                   depletes to 10%. Record elapsed time. */
        }
    }

    verification def EmergencyStopVerification {
        doc /* Verify EmergencyStopReq: e-stop response time.
               Pass if full stop within 0.5 seconds. */
        subject testRobot : AutonomousGroundRobot;
        action def MeasureStopTime {
            doc /* Command max speed, trigger e-stop via remote,
                   measure elapsed time to zero velocity. */
        }
    }

    verification def LocalizationVerification {
        doc /* Verify LocalizationAccuracyReq: localization accuracy
               against motion capture ground truth. Pass if RMS < 5 cm. */
        subject testRobot : AutonomousGroundRobot;
        action def RunLocalizationTest {
            doc /* Navigate known path with OptiTrack ground
                   truth. Compute RMS position error. */
        }
    }

    // ---- Analysis case ----

    analysis def PowerBudgetAnalysis {
        doc /* Analyze power consumption across all subsystems
               to verify endurance requirements are met. */
        subject robot : AutonomousGroundRobot;
        return enduranceHours : Real;

        objective {
            doc /* Compute expected endurance from battery capacity
                   and total system power draw. Identify the highest
                   power consumers and explore trade-offs. */
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 7b. SUBSYSTEM DECOMPOSITION
    //     Intermediate part defs that group element-level parts into
    //     subsystems and sub-subsystems. Depth varies with meaningful
    //     abstraction (not a fixed tree depth):
    //
    //        System (AGR)
    //         ├─ Subsystem (MechanicalStructure, PowerSystem,
    //         │             SensorSuite, ComputeSystem, AutonomyStack,
    //         │             FrameSubsystem)
    //         └─ Sub-subsystem (LidarSubsystem, PerceptionSubsystem, …)
    //             └─ Element (LidarUnit + LidarDriver,
    //                         ObstacleDetector, …)
    //
    //     Rationale:
    //       • SensorSuite fuses sensor hardware with its ROS2 driver per
    //         channel — swapping a commercial LiDAR changes both together.
    //       • AutonomyStack decomposes into seven functional sub-subsystems
    //         reflecting canonical robotic autonomy: perception,
    //         localization, planning, control, safety, mapping, coordination.
    //       • MechanicalStructure, PowerSystem, ComputeSystem, FrameSubsystem
    //         group the non-software domains for mass/power/frame rollups.
    // ═══════════════════════════════════════════════════════════════

    // ---- Sensor channel sub-subsystems (hardware + driver fused) ----

    part def LidarSubsystem {
        doc /* 3D LiDAR sensor channel. Fuses hardware unit with its ROS2 driver
               so commercial substitution (e.g., RPLidar A3 → Ouster OS1-64) is
               a single-subsystem replacement rather than scattered edits. */
        part hardware : LidarUnit;
        part driver : LidarDriver;
    }

    part def ImuSubsystem {
        doc /* 9-DOF IMU sensor channel. Driver publishes imu/data at >= 100 Hz
               and feeds the EKF in the LocalizationSubsystem. */
        part hardware : ImuUnit;
        part driver : ImuDriver;
    }

    part def CameraSubsystem {
        doc /* Stereo camera sensor channel. Intrinsic/extrinsic calibration and
               driver configuration are per-channel concerns, motivating the
               hardware+driver co-location at this subsystem level. */
        part hardware : StereoCamera;
        part driver : CameraDriver;
    }

    // ---- Sensor suite (aggregates sensor channels) ----

    part def SensorSuite {
        doc /* Sensor payload aggregating all perception-adjacent sensor channels.
               Rollup attributes (totalMassKg, totalPowerW) support sensor-payload
               trade studies: a heavier LiDAR that halves the camera need still
               nets a mass win if channels are analyzed at the suite level. */
        part lidar : LidarSubsystem;
        part imu : ImuSubsystem;
        part camera : CameraSubsystem;
        attribute totalMassKg : Real;
        attribute totalPowerW : Real;
    }

    // ---- Autonomy functional sub-subsystems ----

    part def PerceptionSubsystem {
        doc /* Perception pipeline: obstacle detection fusing lidar scan
               and camera image to classify humans, vehicles, and generic
               obstacles. */
        part obstacleDetector : ObstacleDetector;
    }

    part def LocalizationSubsystem {
        doc /* Pose estimation via EKF fusion of IMU, wheel odometry,
               and scan-matching. Outputs continuous 6-DOF pose at 50 Hz. */
        part ekfLocalizer : EKFLocalizer;
    }

    part def PlanningSubsystem {
        doc /* Global path planning over a static map with detected-obstacle
               inflation. A-star and D-star variants chosen per computational
               budget. */
        part pathPlanner : PathPlanner;
    }

    part def ControlSubsystem {
        doc /* Trajectory tracking controller producing cmd_vel from a
               planned path and the estimated pose. Closed-loop at 20 Hz. */
        part trajectoryTracker : TrajectoryTracker;
    }

    part def SafetySubsystem {
        doc /* Safety chain: velocity smoothing followed by collision guard.
               All cmd_vel commands flow through this chain; the guard can
               zero velocity on imminent collision regardless of upstream intent. */
        part velocitySmoother : AGRVelocitySmoother;
        part collisionGuard : CollisionGuard;
    }

    part def MappingSubsystem {
        doc /* Static map provisioning via the map_server + map service. */
        part mapServer : StaticMapServer;
    }

    part def CoordinationSubsystem {
        doc /* Mission-level behavior coordination: goal dispatch, lifecycle
               orchestration, base-station heartbeat monitoring. */
        part missionCoordinator : MissionCoordinator;
    }

    // ---- Autonomy stack (aggregates the seven functional sub-subsystems) ----

    part def AutonomyStack {
        doc /* Complete autonomy software stack. Seven functional sub-subsystems
               reflect the canonical autonomous-robot decomposition:
                 perception → localization → planning → control → safety,
               with mapping and coordination crosscutting.
               All 11 ROS2 nodes allocate to ComputeSystem.computer. */
        part perception : PerceptionSubsystem;
        part localization : LocalizationSubsystem;
        part planning : PlanningSubsystem;
        part control : ControlSubsystem;
        part safety : SafetySubsystem;
        part mapping : MappingSubsystem;
        part coordination : CoordinationSubsystem;
    }

    // ---- Non-software subsystems ----

    part def MechanicalStructure {
        doc /* Structural subsystem: chassis, drivetrain, sensor mounting brackets.
               Aggregates physical mass and geometric footprint for system-level
               mass and dimension requirements. */
        part chassis : Chassis;
        part drivetrain : Drivetrain;
        part lidarBracket : SensorBracket;
        part cameraBracket : SensorBracket;
        attribute totalMassKg : Real;
    }

    part def PowerSystem {
        doc /* Electrical power subsystem: battery, motor current controllers,
               and power distribution. Supports endurance budget analysis via
               totalCapacityAh × nominalVoltageV / steady-state loads. */
        part battery : Battery;
        part motorControllerFront : MotorController;
        part motorControllerRear : MotorController;
        part distribution : PowerDistributionBoard;
        attribute totalCapacityAh : Real;
        attribute nominalVoltageV : Real;
    }

    part def ComputeSystem {
        doc /* On-board compute subsystem hosting the autonomy stack nodes.
               Scope kept minimal here; extend for heterogeneous compute
               (CPU + GPU + hardware accelerator) in downstream models. */
        part computer : OnboardComputer;
    }

    part def FrameSubsystem {
        doc /* TF2 coordinate frame tree. Root frames from StandardFrameTree
               plus sensor-link child frames. Static-transform connections
               between base_link and sensor frames are declared at the
               system-composition level so both endpoints resolve under
               one enclosing scope. */
        part frames : StandardFrameTree;
        part lidarFrame : CoordinateFrame { :>> frameId = "lidar_link"; }
        part imuFrame : CoordinateFrame { :>> frameId = "imu_link"; }
        part cameraFrame : CoordinateFrame { :>> frameId = "camera_link"; }
    }

    // ═══════════════════════════════════════════════════════════════
    // 8. SYSTEM COMPOSITION
    //    Combines physical, electrical, and autonomy subsystems.
    //    The pipeline extracts only the autonomy parts (Section 3)
    //    because only those specialize ros2-sysmlv2 library types.
    // ═══════════════════════════════════════════════════════════════

    part def AutonomousGroundRobot {
        doc /* Complete autonomous ground robot for warehouse operations.
               Multi-domain model: physical structure, electrical power,
               autonomy stack, coordinate frames.

               System-level requirement satisfaction is declared at package
               level (see the AutonomousGroundRobotRequirements group and the
               `satisfy … by theRobot;` statement below) so that structural
               views expose only composition, not requirement assertions. This
               follows OMG SysML v2 §7.21.4 which documents the `by` shorthand
               as equivalent to the nested-in-def form. */

        // System-level attributes (used by requirements)
        attribute totalMassKg : Real = 12.5;
        attribute maxSpeedMs : Real = 1.5;
        attribute enduranceHours : Real = 5.0;

        // ──── Subsystem decomposition ────
        // System → Subsystem → [Sub-subsystem] → Element, variable depth.
        // Each subsystem groups a cohesive domain: mechanical structure,
        // electrical power, sensor payload, onboard compute, autonomy
        // software stack, and TF frame tree.

        part structure : MechanicalStructure;
        part power : PowerSystem;
        part sensors : SensorSuite;
        part compute : ComputeSystem;
        part autonomyStack : AutonomyStack;
        part tfTree : FrameSubsystem;

        // ──── Static transforms (TF2 sensor mounts) ────
        // Declared at system composition level so both endpoints resolve
        // under one enclosing scope (the connections reach into tfTree).

        connection lidarMount : StaticTransform
            connect tfTree.frames.baseLinkFrame to tfTree.lidarFrame;
        connection imuMount : StaticTransform
            connect tfTree.frames.baseLinkFrame to tfTree.imuFrame;
        connection cameraMount : StaticTransform
            connect tfTree.frames.baseLinkFrame to tfTree.cameraFrame;

        // ──── Data flow connections (ROS2 topic connections) ────
        // All inter-subsystem wiring declared at system level; paths use
        // the full subsystem chain from AGR root.

        // Sensors → Perception
        connection scanToDetector : TopicConnection
            connect sensors.lidar.driver.sensorPub
                 to autonomyStack.perception.obstacleDetector.rawSub;
        connection cameraToDetector : TopicConnection
            connect sensors.camera.driver.sensorPub
                 to autonomyStack.perception.obstacleDetector.cameraSub;

        // Sensors → Localization
        connection imuToEkf : TopicConnection
            connect sensors.imu.driver.sensorPub
                 to autonomyStack.localization.ekfLocalizer.sensorSub;
        connection scanToEkf : TopicConnection
            connect sensors.lidar.driver.sensorPub
                 to autonomyStack.localization.ekfLocalizer.scanSub;

        // Perception → Planning
        connection detectionsToPlanner : TopicConnection
            connect autonomyStack.perception.obstacleDetector.processedPub
                 to autonomyStack.planning.pathPlanner.detectionsSub;

        // Mapping → Planning
        connection mapToPlanner : TopicConnection
            connect autonomyStack.mapping.mapServer.mapPub
                 to autonomyStack.planning.pathPlanner.mapSub;

        // Planning → Control
        connection planToTracker : TopicConnection
            connect autonomyStack.planning.pathPlanner.planPub
                 to autonomyStack.control.trajectoryTracker.planSub;

        // Localization → Control
        connection odomToTracker : TopicConnection
            connect autonomyStack.localization.ekfLocalizer.posePub
                 to autonomyStack.control.trajectoryTracker.stateSub;

        // Control → Safety chain (intra-subsystem hop inside safety)
        connection cmdVelToSmoother : TopicConnection
            connect autonomyStack.control.trajectoryTracker.commandPub
                 to autonomyStack.safety.velocitySmoother.cmdVelIn;
        connection smootherToGuard : TopicConnection
            connect autonomyStack.safety.velocitySmoother.cmdVelOut
                 to autonomyStack.safety.collisionGuard.cmdVelIn;

        // Sensors → Safety (scan feedback for collision checking)
        connection scanToGuard : TopicConnection
            connect sensors.lidar.driver.sensorPub
                 to autonomyStack.safety.collisionGuard.scanSub;

        // ──── Operational modes (non-ROS2 state machine) ────
        exhibit state operationalMode : OperationalModes;

        // ──── Software-to-hardware allocation ────
        // All 11 ROS2 nodes execute on the compute subsystem's onboard computer.
        allocate sensors.lidar.driver to compute.computer;
        allocate sensors.imu.driver to compute.computer;
        allocate sensors.camera.driver to compute.computer;
        allocate autonomyStack.perception.obstacleDetector to compute.computer;
        allocate autonomyStack.localization.ekfLocalizer to compute.computer;
        allocate autonomyStack.planning.pathPlanner to compute.computer;
        allocate autonomyStack.control.trajectoryTracker to compute.computer;
        allocate autonomyStack.safety.velocitySmoother to compute.computer;
        allocate autonomyStack.safety.collisionGuard to compute.computer;
        allocate autonomyStack.mapping.mapServer to compute.computer;
        allocate autonomyStack.coordination.missionCoordinator to compute.computer;
    }

    // ═══════════════════════════════════════════════════════════════
    // 8b. SYSTEM INSTANCE + REQUIREMENT SATISFACTION
    //     Per OMG SysML v2 §7.21.4, satisfy-requirement usages may be
    //     declared inside a part def (implicit self subject) OR at
    //     package level with an explicit `by` clause. The latter form is
    //     used here so structural views of the part def expose only
    //     composition features (parts, attributes, connections) and do
    //     not surface «satisfy» nodes as sibling boxes.
    //
    //     See docs/SysMLv2_Satisfy_Placement_Clarification.md for the
    //     full spec analysis and rationale behind this placement.
    // ═══════════════════════════════════════════════════════════════

    requirement def AutonomousGroundRobotRequirements {
        doc /* System-level requirements group. Binds the AGR as the
               subject for all four top-level requirements, with per-requirement
               rationale preserved from the original satisfy docs. */

        subject robot : AutonomousGroundRobot;

        requirement massBudget : MaxMassReq {
            doc /* Total assembled mass is 12.5 kg, verified by component
                   mass rollup: chassis 3.5 + drivetrain 1.2 + sensors 0.3
                   + compute 0.12 + battery 0.8 + structure 0.5 kg. */
        }
        requirement enduranceMin : MinEnduranceReq {
            doc /* 4S LiPo at 10 Ah provides 5+ hours at 25 W compute
                   plus 8.6 W sensor load, validated by PowerBudgetAnalysis. */
        }
        requirement failSafeBehavior : FailSafeReq {
            doc /* MissionCoordinator monitors heartbeat from BaseStation
                   and commands autonomous stop after 10 s timeout. */
        }
        requirement humanDetection : HumanDetectionReq {
            doc /* ObstacleDetector fuses LiDAR scan and camera image
                   to classify humans at 5 m range, triggering speed
                   reduction via CollisionGuard velocity limiting. */
        }
    }

    // Package-level system instance + satisfaction assertion.
    // Per OMG SysML v2 §7.21.4 (spec p. 136), `satisfy` must reference a
    // requirement usage, not a definition. The `satisfy requirement <name>
    // : <Def> by <part>` form declares the requirement usage and asserts
    // satisfaction in one statement.
    part theRobot : AutonomousGroundRobot;
    satisfy requirement robotRqts : AutonomousGroundRobotRequirements by theRobot;

    // ═══════════════════════════════════════════════════════════════
    // 9. ALLOCATION (non-ROS2 — invisible to pipeline)
    // ═══════════════════════════════════════════════════════════════

    // Allocation connects logical autonomy nodes to physical compute hardware.
    // This is a modeling concern, not a ROS2 deployment concern.

    allocation def SoftwareToHardware {
        doc /* Maps autonomy stack nodes to onboard compute platform.
               End features define the source (software) and target (hardware)
               of each allocation. */
        end softwareNode;
        end hardwareNode;
    }

    // ═══════════════════════════════════════════════════════════════
    // 10. VIEWS
    //     Rules (validated via A/B experiments, see debug/test12-15):
    //     - attribute depth = 1; in every view (prevents stdlib noise)
    //     - double expose: expose X; expose X::*; (bounds exposed set)
    //     - render asTreeDiagram; for structural decomposition
    //     - Tom Sawyer auto-detects diagram type from model elements
    // ═══════════════════════════════════════════════════════════════

    private import Views::*;

    // ---- Cross-pillar MBSE view (Figure 2: "bottom line up front") ----

    view mbseArchitecture {
        doc /* Unified MBSE view: structure + behavior + requirements +
               V&V + allocation in one diagram. The central thesis figure:
               what MBSE architecture actually means. */
        // Structure
        expose ShowcaseAGRFull::AutonomousGroundRobot;
        expose ShowcaseAGRFull::AutonomousGroundRobot::*;
        // Behavior
        expose ShowcaseAGRFull::OperationalModes;
        expose ShowcaseAGRFull::OperationalModes::*;
        // Requirements
        expose ShowcaseAGRFull::MaxVelocityReq;
        expose ShowcaseAGRFull::MaxMassReq;
        expose ShowcaseAGRFull::EmergencyStopReq;
        expose ShowcaseAGRFull::CollisionAvoidanceReq;
        // Verification
        expose ShowcaseAGRFull::MassVerification;
        expose ShowcaseAGRFull::EmergencyStopVerification;
        // Allocation
        expose ShowcaseAGRFull::SoftwareToHardware;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Physical structure (tree decomposition) ----

    view robotStructure {
        expose ShowcaseAGRFull::AutonomousGroundRobot;
        expose ShowcaseAGRFull::AutonomousGroundRobot::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Autonomy topology (ports + connections) ----

    view autonomyStack {
        doc /* ROS2 autonomy topology: nodes with ports, topic
               connections as wires, TF frame tree. */
        expose ShowcaseAGRFull::AutonomousGroundRobot;
        expose ShowcaseAGRFull::AutonomousGroundRobot::*;
        render asInterconnectionDiagram;
        attribute depth = 3;
    }

    // ---- Per-subsystem drill-down views (additive) ----
    // Each renders one subsystem of the AGR at depth=1, showing the
    // System → Subsystem → [Sub-subsystem] → Element hierarchy
    // without stdlib-noise risks from deeper view traversal.

    view mechanicalStructureView {
        doc /* Mechanical subsystem: chassis, drivetrain, mounting brackets. */
        expose ShowcaseAGRFull::MechanicalStructure;
        expose ShowcaseAGRFull::MechanicalStructure::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    view powerSystemView {
        doc /* Electrical power subsystem: battery, motor controllers,
               and distribution board. */
        expose ShowcaseAGRFull::PowerSystem;
        expose ShowcaseAGRFull::PowerSystem::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    view sensorSuiteView {
        doc /* Sensor suite: three sensor channels (lidar, imu, camera),
               each fusing hardware unit + ROS2 driver under a sensor-
               subsystem. Shows the designer-relevant substitution unit. */
        expose ShowcaseAGRFull::SensorSuite;
        expose ShowcaseAGRFull::SensorSuite::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    view autonomyStackDetail {
        doc /* Autonomy software stack decomposed into seven functional
               sub-subsystems: perception, localization, planning, control,
               safety, mapping, coordination. */
        expose ShowcaseAGRFull::AutonomyStack;
        expose ShowcaseAGRFull::AutonomyStack::*;
        render asTreeDiagram;
        attribute depth = 3;
    }

    // ---- Behavioral: state machine ----

    view operationalModes {
        expose ShowcaseAGRFull::OperationalModes;
        expose ShowcaseAGRFull::OperationalModes::*;
        attribute depth = 1;
    }

    // ---- Behavioral: action flow ----

    view missionFlow {
        expose ShowcaseAGRFull::ExecuteMission;
        expose ShowcaseAGRFull::ExecuteMission::*;
        attribute depth = 1;
    }

    // ---- Requirements ----

    view systemRequirements {
        expose ShowcaseAGRFull::MaxVelocityReq;
        expose ShowcaseAGRFull::MinEnduranceReq;
        expose ShowcaseAGRFull::MaxMassReq;
        expose ShowcaseAGRFull::EmergencyStopReq;
        expose ShowcaseAGRFull::CollisionAvoidanceReq;
        expose ShowcaseAGRFull::HumanDetectionReq;
        expose ShowcaseAGRFull::FailSafeReq;
        expose ShowcaseAGRFull::LocalizationAccuracyReq;
        expose ShowcaseAGRFull::ObstacleDetectionRangeReq;
        render asTreeDiagram;
        attribute depth = 1;
    }

    // ---- Verification & analysis ----

    view verificationPlan {
        expose ShowcaseAGRFull::MassVerification;
        expose ShowcaseAGRFull::EnduranceVerification;
        expose ShowcaseAGRFull::EmergencyStopVerification;
        expose ShowcaseAGRFull::LocalizationVerification;
        expose ShowcaseAGRFull::PowerBudgetAnalysis;
        render asTreeDiagram;
        attribute depth = 1;
    }

    // ---- Sequence diagram ----

    view emergencyStopSequence {
        expose ShowcaseAGRFull::emergencyStopProtocol;
        attribute depth = 1;
    }
}
