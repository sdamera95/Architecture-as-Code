package UAVFullModel {
    doc
    /* Comprehensive UAV system model demonstrating the full breadth of
       SysML v2 modeling capabilities: structure, behavior, requirements,
       verification, allocation, variability, metadata, and analysis.

       NOT intended as a semantically perfect aerospace model —
       intended as an exploration of SysML v2 language features. */

    private import ScalarValues::*;

    // ===============================================================
    // 1. Metadata definitions (annotations on model elements)
    // ===============================================================

    metadata def SafetyCritical {
        attribute level : String;
    }

    metadata def TradeParameter {
        doc /* Marks an attribute as a design trade parameter for sweeps. */
        attribute sweepMin : Real;
        attribute sweepMax : Real;
    }

    // ===============================================================
    // 2. Enumeration definitions
    // ===============================================================

    enum def FlightPhase {
        enum ground;
        enum hover;
        enum cruise;
        enum survey;
        enum emergency;
    }

    enum def SensorModality {
        enum lidar;
        enum camera;
        enum imu;
        enum gps;
        enum barometer;
    }

    enum def QoSReliability {
        enum bestEffort;
        enum reliable;
    }

    // ===============================================================
    // 3. Item definitions (things that flow)
    // ===============================================================

    item def ElectricalPower {
        attribute voltage : Real;
        attribute currentDraw : Real;
    }

    item def CommandSignal {
        attribute commandId : Integer;
    }

    item def TelemetryData {
        attribute timestamp : Real;
    }

    item def SensorReading {
        attribute timestamp : Real;
        attribute modality : SensorModality;
    }

    item def NavigationGoal {
        attribute targetX : Real;
        attribute targetY : Real;
        attribute targetZ : Real;
    }

    item def Pose {
        attribute x : Real;
        attribute y : Real;
        attribute z : Real;
        attribute yaw : Real;
    }

    item def Path {
        attribute numWaypoints : Integer;
    }

    item def OccupancyMap {
        attribute resolution : Real;
        attribute width : Integer;
        attribute height : Integer;
    }

    // ===============================================================
    // 4. Port definitions
    // ===============================================================

    port def PowerPort {
        out item suppliedPower : ElectricalPower;
    }

    port def CommandPort {
        out item cmd : CommandSignal;
        in item ack : TelemetryData;
    }

    port def TelemetryPort {
        out item telemetry : TelemetryData;
    }

    port def SensorPort {
        out item reading : SensorReading;
    }

    port def NavigationPort {
        in item goal : NavigationGoal;
        out item currentPose : Pose;
    }

    port def PlannerPort {
        in item goal : NavigationGoal;
        in item currentMap : OccupancyMap;
        out item plan : Path;
    }

    port def ControllerPort {
        in item plan : Path;
        in item currentPose : Pose;
        out item cmd : CommandSignal;
    }

    // ===============================================================
    // 5. Connection definitions
    // ===============================================================

    connection def PowerConnection {
        end source : PowerPort;
        end target : PowerPort;
    }

    connection def CommandConnection {
        end source : CommandPort;
        end target : CommandPort;
    }

    connection def SensorConnection {
        end source : SensorPort;
        end target : SensorPort;
    }

    connection def TelemetryConnection {
        end source : TelemetryPort;
        end target : TelemetryPort;
    }

    // ===============================================================
    // 6. Constraint definitions (reusable predicates)
    // ===============================================================

    constraint def PositiveReal {
        in value : Real;
        value > 0.0
    }

    constraint def WithinRange {
        in value : Real;
        in minVal : Real;
        in maxVal : Real;
        value >= minVal and value <= maxVal
    }

    // ===============================================================
    // 7. Abstract base definitions (cannot be instantiated directly)
    // ===============================================================

    abstract part def Sensor {
        doc /* Abstract base for all sensor types. */
        attribute massKg : Real;
        attribute powerW : Real;
        attribute modality : SensorModality;
        port sensorOut : SensorPort;
    }

    abstract part def Actuator {
        doc /* Abstract base for all actuator types. */
        attribute massKg : Real;
        attribute maxPowerW : Real;
    }

    // ===============================================================
    // 8. Concrete part definitions with parameters
    // ===============================================================

    // ---- Battery ------------------------------------------------

    part def Battery {
        doc /* Lithium polymer battery pack. Key trade parameter:
               capacity drives both endurance and mass. */

        attribute capacityWh : Real;
        attribute specificEnergy : Real;
        attribute nominalVoltage : Real;
        attribute massKg : Real;

        port powerOut : PowerPort;
    }

    // ---- Sensors (specialize the abstract Sensor) ----------------

    part def IMU :> Sensor {
        :>> modality = SensorModality::imu;
        attribute updateRateHz : Real;
    }

    part def GPS :> Sensor {
        :>> modality = SensorModality::gps;
        attribute updateRateHz : Real;
        attribute accuracyM : Real;
    }

    part def Barometer :> Sensor {
        :>> modality = SensorModality::barometer;
        attribute updateRateHz : Real;
    }

    part def LiDAR :> Sensor {
        :>> modality = SensorModality::lidar;
        attribute channels : Integer;
        attribute rangeM : Real;
        attribute scanRateHz : Real;
    }

    part def Camera :> Sensor {
        :>> modality = SensorModality::camera;
        attribute resolutionH : Integer;
        attribute resolutionV : Integer;
        attribute fpsRate : Real;
    }

    // ---- Motors (specialize the abstract Actuator) ----------------

    part def BrushlessMotor :> Actuator {
        attribute efficiencyPct : Real;
        port powerIn : ~PowerPort;
        port cmdIn : ~CommandPort;
    }

    // ---- Flight Controller --------------------------------------

    part def FlightController {
        @SafetyCritical { level = "high"; }

        attribute massKg : Real;
        attribute powerW : Real;

        port powerIn : ~PowerPort;
        port imuIn : ~SensorPort;
        port gpsIn : ~SensorPort;
        port baroIn : ~SensorPort;
        port motorCmdOut : CommandPort;
        port telemetryOut : TelemetryPort;

        // FCC exhibits flight mode state machine
        exhibit state flightMode : FlightModes;
    }

    // ---- Propulsion Subsystem -----------------------------------

    part def PropulsionSubsystem {
        attribute numMotors : Integer;
        attribute massKg : Real;

        port powerIn : ~PowerPort;
        port cmdIn : ~CommandPort;

        part motor : BrushlessMotor;
    }

    // ---- Avionics Subsystem -------------------------------------

    part def AvionicsSubsystem {
        attribute massKg : Real;
        attribute totalPowerW : Real;

        port powerIn : ~PowerPort;
        port motorCmdOut : CommandPort;
        port telemetryOut : TelemetryPort;

        part fcc : FlightController;
        part imu : IMU;
        part gps : GPS;
        part baro : Barometer;

        connection : PowerConnection connect powerIn to fcc.powerIn;
        connection : SensorConnection connect imu.sensorOut to fcc.imuIn;
        connection : SensorConnection connect gps.sensorOut to fcc.gpsIn;
        connection : SensorConnection connect baro.sensorOut to fcc.baroIn;
        connection : CommandConnection connect fcc.motorCmdOut to motorCmdOut;
        connection : TelemetryConnection connect fcc.telemetryOut to telemetryOut;
    }

    // ---- Payload ------------------------------------------------

    part def CameraPayload {
        attribute massKg : Real;
        attribute powerW : Real;

        part camera : Camera;
        port powerIn : ~PowerPort;
        port telemetryOut : TelemetryPort;
    }

    // ---- Airframe -----------------------------------------------

    part def Airframe {
        attribute massKg : Real;
        attribute wingspanM : Real;
    }

    // ===============================================================
    // 9. State machine definitions (behavioral modes)
    // ===============================================================

    state def FlightModes {
        doc /* Primary flight mode state machine for the UAV.
               Managed by the flight controller.
               States represent operational modes; transitions represent
               mode changes triggered by commands or faults. */

        state grounded;
        state preflight;
        state hovering;
        state cruising;
        state surveying;
        state landing;
        state emergency;

        // Normal flight sequence (using successions)
        first grounded then preflight;
        first preflight then hovering;
        first hovering then cruising;
        first cruising then hovering;
        first hovering then surveying;
        first surveying then hovering;
        first hovering then landing;
        first landing then grounded;
    }

    state def BatteryStates {
        doc /* Battery state of charge monitoring.
               Transitions driven by SOC thresholds. */

        state nominal;
        state warning;
        state critical;

        first nominal then warning;
        first warning then critical;
    }

    state def NavigationStates {
        doc /* Navigation state machine for autonomous waypoint following. */

        state idle;
        state planning;
        state executing;
        state recovering;
        state goalReached;

        first idle then planning;
        first planning then executing;
        first executing then goalReached;
        first executing then recovering;
        first recovering then planning;
        first goalReached then idle;
    }

    // ===============================================================
    // 10. Action definitions (behavioral sequences)
    // ===============================================================

    action def Takeoff {
        doc /* Vertical takeoff to hover altitude. */
        in item targetAltitude : Real;
        out item reachedAltitude : Real;
    }

    action def Cruise {
        in item targetSpeed : Real;
        in item heading : Real;
    }

    action def Survey {
        in item surveyArea : NavigationGoal;
        out item coverage : Real;
    }

    action def ReturnToBase {
        in item homePosition : Pose;
        out item distanceToHome : Real;
    }

    action def Land {
        out item touchdownForce : Real;
    }

    action def PlanPath {
        doc /* Compute a collision-free path from current position to goal. */
        in item currentPose : Pose;
        in item goal : NavigationGoal;
        in item currentMap : OccupancyMap;
        out item plannedPath : Path;
        out item planningTimeMs : Real;
    }

    action def FollowPath {
        doc /* Execute a planned path using the control system. */
        in item path : Path;
        in item currentPose : Pose;
        out item trackingError : Real;
        out item reachedGoal : Boolean;
    }

    action def NavigateToWaypoint {
        doc /* Full navigation pipeline: plan then follow. */
        in item goal : NavigationGoal;
        out item success : Boolean;

        action plan : PlanPath;
        action follow : FollowPath;

        flow from goal to plan.goal;
        flow from plan.plannedPath to follow.path;

        first plan then follow;
    }

    action def Mission {
        doc /* Complete UAV mission sequence with all phases. */

        action takeoff      : Takeoff;
        action cruise       : Cruise;
        action survey       : Survey;
        action returnToBase : ReturnToBase;
        action land         : Land;

        first takeoff      then cruise;
        first cruise       then survey;
        first survey       then returnToBase;
        first returnToBase then land;
    }

    // ===============================================================
    // 11. Top-level UAV system
    // ===============================================================

    part def UAV {
        doc /* Quadrotor UAV system for autonomous survey missions.
               Composed of airframe, battery, propulsion, avionics,
               and payload subsystems with full parametric model. */

        // ---- Subsystem instances with concrete values ----

        part airframe : Airframe {
            :>> massKg = 0.8;
            :>> wingspanM = 0.5;
        }

        part battery : Battery {
            @TradeParameter { sweepMin = 20.0; sweepMax = 500.0; }
            :>> capacityWh = 100.0;
            :>> specificEnergy = 200.0;
            :>> massKg = capacityWh / specificEnergy;
            :>> nominalVoltage = 22.2;
        }

        part propulsion : PropulsionSubsystem {
            :>> numMotors = 4;

            part :>> motor {
                :>> massKg = 0.065;
                :>> maxPowerW = 250.0;
                :>> efficiencyPct = 85.0;
            }

            :>> massKg = numMotors * motor.massKg;
        }

        part avionics : AvionicsSubsystem {
            part :>> fcc {
                :>> massKg = 0.05;
                :>> powerW = 5.0;
            }
            part :>> imu {
                :>> massKg = 0.01;
                :>> powerW = 0.5;
                :>> updateRateHz = 400.0;
            }
            part :>> gps {
                :>> massKg = 0.015;
                :>> powerW = 0.8;
                :>> updateRateHz = 10.0;
                :>> accuracyM = 1.5;
            }
            part :>> baro {
                :>> massKg = 0.005;
                :>> powerW = 0.1;
                :>> updateRateHz = 50.0;
            }

            :>> massKg = fcc.massKg + imu.massKg + gps.massKg + baro.massKg;
            :>> totalPowerW = fcc.powerW + imu.powerW + gps.powerW + baro.powerW;
        }

        part payload : CameraPayload {
            :>> massKg = 0.15;
            :>> powerW = 8.0;

            part :>> camera {
                :>> massKg = 0.1;
                :>> powerW = 6.0;
                :>> resolutionH = 1920;
                :>> resolutionV = 1080;
                :>> fpsRate = 30.0;
            }
        }

        // ---- Power distribution topology ----

        connection : PowerConnection connect battery.powerOut to propulsion.powerIn;
        connection : PowerConnection connect battery.powerOut to avionics.powerIn;
        connection : PowerConnection connect battery.powerOut to payload.powerIn;
        connection : CommandConnection connect avionics.motorCmdOut to propulsion.cmdIn;

        // ---- Flows ----

        flow from battery.powerOut.suppliedPower to propulsion.powerIn.suppliedPower;
        flow from battery.powerOut.suppliedPower to avionics.powerIn.suppliedPower;
        flow from battery.powerOut.suppliedPower to payload.powerIn.suppliedPower;
        flow from avionics.motorCmdOut.cmd to propulsion.cmdIn.cmd;

        // ---- Derived system-level attributes ----

        attribute totalMassKg : Real =
            airframe.massKg + battery.massKg + propulsion.massKg +
            avionics.massKg + payload.massKg;

        attribute propulsiveConstant : Real = 50.0;
        attribute hoverPowerW : Real = propulsiveConstant * totalMassKg;
        attribute avionicsPowerW : Real = avionics.totalPowerW;
        attribute payloadPowerW : Real = payload.powerW;
        attribute totalPowerW : Real = hoverPowerW + avionicsPowerW + payloadPowerW;
        attribute enduranceHrs : Real = battery.capacityWh / totalPowerW;
        attribute enduranceMin : Real = enduranceHrs * 60.0;
        attribute cruiseSpeedMs : Real = 15.0;
        attribute maxAltitudeM : Real = 400.0;

        // ---- Behavioral bindings ----

        perform action mission : Mission;
    }

    // ===============================================================
    // 12. Battery variability (design library for trade studies)
    // ===============================================================

    variation part def BatteryOptions :> Battery {
        doc /* Battery design library for trade studies.
               Each variant represents a commercially available option. */

        variant part smallBattery : Battery {
            :>> capacityWh = 50.0;
            :>> specificEnergy = 180.0;
            :>> massKg = capacityWh / specificEnergy;
            :>> nominalVoltage = 14.8;
        }

        variant part mediumBattery : Battery {
            :>> capacityWh = 100.0;
            :>> specificEnergy = 200.0;
            :>> massKg = capacityWh / specificEnergy;
            :>> nominalVoltage = 22.2;
        }

        variant part largeBattery : Battery {
            :>> capacityWh = 200.0;
            :>> specificEnergy = 220.0;
            :>> massKg = capacityWh / specificEnergy;
            :>> nominalVoltage = 22.2;
        }

        variant part premiumBattery : Battery {
            :>> capacityWh = 300.0;
            :>> specificEnergy = 250.0;
            :>> massKg = capacityWh / specificEnergy;
            :>> nominalVoltage = 44.4;
        }
    }

    // ===============================================================
    // 13. Requirements (full hierarchy with satisfaction and concerns)
    // ===============================================================

    concern def MissionSuccess {
        doc /* The UAV must complete its survey mission autonomously. */
    }

    concern def OperationalSafety {
        doc /* The UAV must operate safely at all times. */
    }

    concern def CostEffectiveness {
        doc /* The UAV design must be economically viable. */
    }

    // ---- Top-level requirement decomposition ----

    requirement def SystemRequirements {
        doc /* Top-level requirements for the UAV system. */
        subject uav : UAV;

        // Performance requirements
        requirement massBudget {
            doc /* The UAV total mass shall not exceed 5 kg. */
            require constraint { uav.totalMassKg <= 5.0 }
        }

        requirement enduranceReq {
            doc /* Flight endurance shall be at least 30 minutes. */
            require constraint { uav.enduranceMin >= 30.0 }
        }

        requirement powerBudget {
            doc /* Total power shall not exceed 600 W. */
            require constraint { uav.totalPowerW <= 600.0 }
        }

        requirement cruiseSpeed {
            doc /* Cruise speed shall be at least 10 m/s. */
            require constraint { uav.cruiseSpeedMs >= 10.0 }
        }

        requirement maxAltitude {
            doc /* Maximum operating altitude shall be at least 400 m AGL. */
            require constraint { uav.maxAltitudeM >= 400.0 }
        }
    }

    // ---- Safety requirements (linked to concern) ----

    requirement def SafetyRequirements {
        doc /* Safety requirements for the UAV system. */
        frame concern OperationalSafety;
        subject uav : UAV;

        requirement batteryMargin {
            doc /* Battery capacity shall provide at least 20% reserve. */
        }

        requirement motorRedundancy {
            doc /* The UAV shall be able to maintain controlled flight
                   with one motor failed. */
        }

        requirement emergencyLanding {
            doc /* The UAV shall execute autonomous emergency landing
                   within 30 seconds of critical fault detection. */
        }
    }

    // ===============================================================
    // 14. Verification definitions
    // ===============================================================

    verification def MassVerification {
        doc /* Verify mass budget by weighing the assembled UAV. */
        subject testUAV : UAV;

        action def WeighProcedure {
            doc /* Place fully assembled UAV on calibrated scale.
                   Record mass. Compare to 5.0 kg limit. */
        }
    }

    verification def EnduranceVerification {
        doc /* Verify endurance by flight test. */
        subject testUAV : UAV;

        action def FlightTest {
            doc /* Fly UAV in hover at sea level until battery
                   reaches 20% SOC. Record flight time. */
        }
    }

    verification def SimulationVerification {
        doc /* Verify performance requirements via simulation. */
        subject testUAV : UAV;

        action def RunSimulation {
            doc /* Execute full mission profile in Gazebo/Isaac Sim.
                   Collect endurance, power, and mass telemetry.
                   Compare against requirements. */
        }
    }

    // ===============================================================
    // 15. Analysis case
    // ===============================================================

    analysis def EnduranceTradeStudy {
        doc /* Parametric trade study sweeping battery capacity
               and evaluating endurance, mass, and power impact.
               Returns endurance as the primary figure of merit. */

        subject uav : UAV;
        return enduranceMin : Real;

        objective {
            doc /* Find the battery capacity that maximizes endurance
                   while satisfying the mass and power budgets. */
        }
    }

    // ===============================================================
    // 16. Views and viewpoints
    // ===============================================================

    viewpoint def StructuralViewpoint {
        doc /* Shows the physical decomposition and composition. */
    }

    viewpoint def BehavioralViewpoint {
        doc /* Shows the behavioral modes and action sequences. */
    }

    viewpoint def RequirementsViewpoint {
        doc /* Shows the requirements hierarchy and traceability. */
    }

    view uavStructure : StructuralViewpoint {
        expose UAVFullModel::UAV;
    }

    view uavBehavior : BehavioralViewpoint {
        expose UAVFullModel::FlightModes;
        expose UAVFullModel::Mission;
        expose UAVFullModel::NavigateToWaypoint;
    }

    view uavRequirements : RequirementsViewpoint {
        expose UAVFullModel::SystemRequirements;
        expose UAVFullModel::SafetyRequirements;
    }
}
