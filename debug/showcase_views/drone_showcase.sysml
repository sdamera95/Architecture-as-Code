package DroneShowcase {
    // SysML v2 modeling-feature showcase for the four-pillar manuscript figure.
    // Designed for clean Tom Sawyer rendering: NO doc strings on elements that
    // get rendered (Simonas forum #447: filter cannot strip the doc COMPARTMENT,
    // only its node). Each view exposes a tightly-scoped set of elements at
    // depth=1 to avoid stdlib leak.
    //
    // Domain: small autonomous aerial delivery drone. Showcases:
    //   - Structure (IBD with interfaces + flows)
    //   - Behavior state machine (parallel regions, entry/do/exit, guard, port-driven, time-driven)
    //   - Action flow (for/if-else/fork-join)
    //   - Requirement hierarchy with subjects + specialization + numeric constraints
    //   - Parametric constraint with sub-constraints and attribute binding
    //   - Use case with actors and includes

    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;

    // ─────────────────────────────────────────────────────────────────
    // SHARED DOMAIN ITEMS (events, payloads)
    // ─────────────────────────────────────────────────────────────────

    item def TakeoffCmd;
    item def LandCmd;
    item def AbortCmd;
    item def WaypointReached;
    item def PackageReleaseCmd;
    item def TelemetryFrame;

    item def CommandPacket {
        attribute opCode : String;
    }
    item def StatusPacket {
        attribute health : String;
    }
    item def GoalPose {
        attribute x : Real;
        attribute y : Real;
        attribute z : Real;
    }
    item def Acknowledgment;

    // Waypoint as a structured value
    attribute def Waypoint {
        attribute lat : Real;
        attribute lon : Real;
        attribute altitudeM : Real;
        attribute customerPresent : Boolean;
    }

    // ─────────────────────────────────────────────────────────────────
    // STRUCTURE — Internal Block Diagram with interfaces and flows
    // ─────────────────────────────────────────────────────────────────

    // --- Port definitions (directions describe the "ground / planner" side;
    //     drone-side ports use the conjugate ~ to flip directions). ---
    port def TelemetryEndpoint {
        out item commands : CommandPacket;
        in  item status   : StatusPacket;
    }
    port def MissionEndpoint {
        out item goal : GoalPose;
        in  item ack  : Acknowledgment;
    }
    port def PayloadEndpoint {
        in item releaseCmd : PackageReleaseCmd;
    }

    // --- Interface definitions with flows ---
    interface def TelemetryLink {
        end port radioSide : TelemetryEndpoint;
        end port avionicsSide : ~TelemetryEndpoint;
        flow of CommandPacket from radioSide.commands to avionicsSide.commands;
        flow of StatusPacket  from avionicsSide.status to radioSide.status;
    }
    interface def MissionLink {
        end port plannerSide : MissionEndpoint;
        end port avionicsSide : ~MissionEndpoint;
        flow of GoalPose       from plannerSide.goal to avionicsSide.goal;
        flow of Acknowledgment from avionicsSide.ack to plannerSide.ack;
    }

    // --- Component definitions ---
    part def TelemetryRadio {
        port radio : TelemetryEndpoint;
    }
    part def MissionPlanner {
        port mission : MissionEndpoint;
    }
    part def FlightAvionics {
        port telemetry : ~TelemetryEndpoint;
        port mission : ~MissionEndpoint;
        port payload : PayloadEndpoint;
        attribute maxClimbRateMs : Real;
        attribute maxCruiseSpeedMs : Real;
    }
    part def PayloadBay {
        port commandIn : ~PayloadEndpoint;
    }

    // --- System composition with internal connections ---
    part def DeliveryDrone {
        part radio : TelemetryRadio;
        part planner : MissionPlanner;
        part avionics : FlightAvionics;
        part payload : PayloadBay;

        connection telemetryWire : TelemetryLink
            connect radio.radio to avionics.telemetry;
        connection missionWire : MissionLink
            connect planner.mission to avionics.mission;
        connection payloadWire
            connect avionics.payload to payload.commandIn;
    }

    // ─────────────────────────────────────────────────────────────────
    // BEHAVIOR — Complex state machine with parallel regions
    // ─────────────────────────────────────────────────────────────────

    state def DroneFlightModes {
        attribute batteryPctRemaining : Real;
        attribute altitudeM : Real;
        attribute payloadCount : Integer;

        ref port commandPort;
        ref port mishapPort;
        ref port payloadPort;

        entry; then grounded;

        state grounded;
            accept TakeoffCmd via commandPort
            if batteryPctRemaining >= 25.0
            do send new CommandPacket("arm_motors") via commandPort
            then airborne;

        state airborne parallel {
            state navigationMode {
                entry; then idle;
                state idle;
                    accept g : GoalPose via commandPort
                    do send new CommandPacket("plan_route") via commandPort
                    then enroute;
                state enroute;
                    accept WaypointReached via commandPort
                    then hovering;
                state hovering;
                    accept after 30 [SI::s]
                    then idle;

                transition lowAltitudeAbort
                    first enroute
                    accept when altitudeM < 1.0
                    do send new CommandPacket("emergency_climb") via commandPort
                    then idle;
            }
            state payloadMode {
                entry; then carrying;
                state carrying;
                    accept PackageReleaseCmd via payloadPort
                    do send new StatusPacket("releasing_package") via commandPort
                    then releasing;
                state releasing;
                    accept after 2 [SI::s]
                    then empty;
                state empty;
                    accept after 10 [SI::s]
                    then carrying;
            }
        }

        accept LandCmd via commandPort
        if altitudeM > 0.0
        do send new CommandPacket("descend") via commandPort
        then grounded;

        accept AbortCmd via mishapPort
        do send new CommandPacket("emergency_land") via commandPort
        then grounded;
    }

    // ─────────────────────────────────────────────────────────────────
    // BEHAVIOR — Action flow with for / if-else / fork-join
    // ─────────────────────────────────────────────────────────────────

    action def NavigateToWaypoint {
        in attribute target : Waypoint;
    }
    action def TransmitTelemetry {
        in attribute payload : TelemetryFrame;
    }
    action def CheckBattery {
        out attribute level : Real;
    }
    action def HandoffPackage {
        in attribute target : Waypoint;
    }
    action def DropAtSafeZone {
        in attribute target : Waypoint;
    }
    action def ReturnToBase;

    action def DeliverRoute {
        in attribute route : Waypoint [*];

        first start;
        then for waypoint : Waypoint in route {
            action navigate : NavigateToWaypoint {
                in attribute redefines target = waypoint;
            }
            then if waypoint.customerPresent {
                action handoff : HandoffPackage {
                    in attribute redefines target = waypoint;
                }
            } else {
                action dropOff : DropAtSafeZone {
                    in attribute redefines target = waypoint;
                }
            }
            then fork;
                then telemetry;
                then battery;

                action telemetry : TransmitTelemetry;
                    then j;
                action battery : CheckBattery;
                    then j;
            join j;
        }
        then action returnHome : ReturnToBase;
    }

    // ─────────────────────────────────────────────────────────────────
    // REQUIREMENTS — hierarchy with subjects, specialization, numeric constraints
    // ─────────────────────────────────────────────────────────────────

    requirement def SizingRequirement {
        attribute toSize;
        attribute toFit;
        attribute minimumScale;
        assume constraint { toFit >= 0 }
        require constraint { toSize >= toFit * minimumScale }
    }

    requirement def <'M-1'> MissionRequirements {
        subject vehicle : DeliveryDrone;

        requirement payload : PayloadCapacityRequirement;
        requirement endurance : EnduranceRequirement;
        requirement safety : SafetyRequirements {
            subject :>> vehicle = MissionRequirements::vehicle;
        }
    }

    requirement def <'M-1.1'> PayloadCapacityRequirement specializes SizingRequirement {
        subject vehicle : DeliveryDrone;
        attribute :>> toSize = vehicle.avionics.maxClimbRateMs;
        attribute :>> toFit = 1.5;
        attribute :>> minimumScale = 2;
    }

    requirement def <'M-1.2'> EnduranceRequirement {
        subject vehicle : DeliveryDrone;
        attribute minFlightTimeMin : Real;
        require constraint {
            minFlightTimeMin >= 25.0
        }
    }

    requirement def <'M-1.3'> SafetyRequirements {
        subject vehicle : DeliveryDrone;

        requirement noFly : NoFlyZoneCompliance;
        requirement abort : EmergencyAbort;
    }

    requirement def <'M-1.3.1'> NoFlyZoneCompliance {
        subject vehicle : DeliveryDrone;
        attribute clearanceM : Real;
        require constraint {
            clearanceM >= 5.0
        }
    }

    requirement def <'M-1.3.2'> EmergencyAbort {
        subject vehicle : DeliveryDrone;
        attribute maxAbortLatencyMs : Real;
        require constraint {
            maxAbortLatencyMs <= 200.0
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // PARAMETRIC — constraint def with sub-constraints and bound attributes
    // ─────────────────────────────────────────────────────────────────

    constraint def HoverPower {
        attribute massKg : Real;
        attribute gravityMs2 : Real;
        attribute hoverEfficiency : Real;
        attribute hoverPowerW : Real;

        hoverPowerW == (massKg * gravityMs2) / hoverEfficiency
    }

    constraint def CruiseRange {
        attribute batteryEnergyJ : Real;
        attribute cruisePowerW : Real;
        attribute cruiseSpeedMs : Real;
        attribute cruiseRangeM : Real;

        cruiseRangeM == batteryEnergyJ / cruisePowerW * cruiseSpeedMs
    }

    constraint def FlightPerformance {
        attribute massKg : Real;
        attribute batteryEnergyJ : Real;
        attribute cruiseSpeedMs : Real;
        attribute hoverEfficiency : Real;
        attribute estimatedRangeM : Real;
        attribute estimatedHoverPowerW : Real;

        constraint hover : HoverPower {
            attribute :>> massKg = FlightPerformance::massKg;
            attribute :>> gravityMs2 = 9.81;
            attribute :>> hoverEfficiency = FlightPerformance::hoverEfficiency;
            attribute :>> hoverPowerW = FlightPerformance::estimatedHoverPowerW;
        }
        constraint range : CruiseRange {
            attribute :>> batteryEnergyJ = FlightPerformance::batteryEnergyJ;
            attribute :>> cruisePowerW = FlightPerformance::estimatedHoverPowerW * 1.2;
            attribute :>> cruiseSpeedMs = FlightPerformance::cruiseSpeedMs;
            attribute :>> cruiseRangeM = FlightPerformance::estimatedRangeM;
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // USE CASE — actor + subject + included use cases
    // ─────────────────────────────────────────────────────────────────

    part def HumanDispatcher;
    part def MaintenanceTechnician;

    use case def DispatchMission {
        subject vehicle : DeliveryDrone;
        actor dispatcher : HumanDispatcher;
    }

    use case def MonitorTelemetry {
        subject vehicle : DeliveryDrone;
        actor dispatcher : HumanDispatcher;
    }

    use case def TriggerEmergencyAbort {
        subject vehicle : DeliveryDrone;
        actor dispatcher : HumanDispatcher;
    }

    use case def PerformMaintenance {
        subject vehicle : DeliveryDrone;
        actor tech : MaintenanceTechnician;
    }

    use case def OperateDeliveryFleet {
        subject vehicle : DeliveryDrone;
        actor dispatcher : HumanDispatcher;
        actor tech : MaintenanceTechnician;

        include use case dispatch : DispatchMission;
        include use case monitor : MonitorTelemetry;
        include use case abort : TriggerEmergencyAbort;
        include use case maint : PerformMaintenance;
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW DEFINITIONS — one per pillar, depth=1, double expose
    // ═══════════════════════════════════════════════════════════════

    private import Views::*;

    view structure_ibd {
        // depth=3 surfaces ports + wires (Experiment 19 finding)
        expose DeliveryDrone;
        expose DeliveryDrone::*;
        attribute depth = 3;
    }

    view behavior_stateMachine {
        // depth=2 surfaces parallel regions and substates inside `airborne`
        expose DroneFlightModes;
        expose DroneFlightModes::*;
        attribute depth = 2;
    }

    view behavior_actionFlow {
        // depth=2 surfaces the for-loop body, if-else branches, fork-join
        expose DeliverRoute;
        expose DeliverRoute::*;
        attribute depth = 2;
    }

    view requirements_hierarchy {
        expose MissionRequirements;
        expose MissionRequirements::*;
        expose PayloadCapacityRequirement;
        expose EnduranceRequirement;
        expose SafetyRequirements;
        expose SafetyRequirements::*;
        expose NoFlyZoneCompliance;
        expose EmergencyAbort;
        render asTreeDiagram;
        attribute depth = 1;
    }

    view constraints_parametric {
        // depth=2 surfaces attribute redefinitions in the nested constraints
        expose FlightPerformance;
        expose FlightPerformance::*;
        attribute depth = 2;
    }

    view useCases_top {
        expose OperateDeliveryFleet;
        expose OperateDeliveryFleet::*;
        attribute depth = 1;
    }
}
