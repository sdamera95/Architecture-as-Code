// Experiment 16: Validate ALL advanced SysML v2 constructs needed for
// publication-quality showcase figures.
//
// Syntax patterns derived from WORKING examples:
//   - Fork/join: debug/advent-of-sysml-v2/lesson17/
//   - Fork (named): debug/sfriedenthal_Flashlight_Starter_Model
//   - If-else: debug/advent-of-sysml-v2/lesson17/
//   - Substates + parallel: debug/advent-of-sysml-v2/lesson18/
//   - Guards: tests/test_state_transition_syntax.sysml
//   - Satisfy: debug/advent-of-sysml-v2/lesson24/
//   - Verify: debug/sfriedenthal_Flashlight_Starter_Model

package TestAdvancedConstructs {

    private import ScalarValues::*;

    // ═══════════════════════════════════════════════════════════════
    // Event items for state machine transitions
    // ═══════════════════════════════════════════════════════════════

    item def MissionCommand;
    item def ManualOverrideEvent;
    item def EmergencyTrigger;
    item def ClearanceEvent;
    item def ObstacleDetected;

    // ═══════════════════════════════════════════════════════════════
    // TEST 1: State machine with substates, guards, event triggers
    // ═══════════════════════════════════════════════════════════════

    state def OperationalModes {
        doc /* Rich state machine: substates, event triggers, guard. */

        attribute batteryLevel : Real;

        state idle;

        // SUBSTATES within autonomous
        state autonomous {
            state planning;
            state executing;
            state recovering;

            transition startPlanning
                first planning then executing;
            transition obstacleHit
                first executing accept ObstacleDetected then recovering;
            transition recoveryDone
                first recovering then planning;
        }

        state manual;
        state emergency;
        state charging;

        // EVENT-TRIGGERED transitions
        transition startMission
            first idle accept MissionCommand then autonomous;
        transition takeManual
            first autonomous accept ManualOverrideEvent then manual;
        transition triggerEmergency
            first autonomous accept EmergencyTrigger then emergency;
        transition returnToAuto
            first manual accept MissionCommand then autonomous;
        transition clearEmergency
            first emergency accept ClearanceEvent then idle;

        // GUARD CONDITION
        transition startCharging
            first idle if batteryLevel < 0.2 then charging;
        transition doneCharging
            first charging if batteryLevel > 0.9 then idle;
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 2: Parallel/concurrent state regions
    // ═══════════════════════════════════════════════════════════════

    state def MissionExecution {
        doc /* Parallel regions: monitoring + control run concurrently. */

        state active parallel {
            state monitoring {
                state nominal;
                state degraded;
                transition degrade first nominal then degraded;
                transition recover first degraded then nominal;
            }
            state controlling {
                state navigating;
                state holding;
                transition holdPos first navigating then holding;
                transition resumeNav first holding then navigating;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 3: Action flow with fork/join (lesson17 pattern)
    // ═══════════════════════════════════════════════════════════════

    action def InitSequence {
        doc /* Fork/join: two branches run in parallel then sync. */

        first start;
        then fork;
            then initSensors;
            then loadMap;

            action initSensors;
                then j;
            action loadMap;
                then j;
        join j;
        then action planRoute;
        then done;
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 4: Action flow with if-else decision (lesson17 pattern)
    // ═══════════════════════════════════════════════════════════════

    action def MissionWithRetry {
        doc /* If-else decision: success vs failure branch. */

        attribute missionComplete : Boolean;

        first start;
        then action plan;
        then action execute;
        then if missionComplete {
            action goHome;
        } else {
            action handleError;
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 5: Combined fork/join + if-else in one action
    // ═══════════════════════════════════════════════════════════════

    action def ExecuteMission {
        doc /* Full mission: fork init, then plan/execute, if-else outcome. */

        attribute missionSuccess : Boolean;

        first start;

        // Parallel initialization
        then fork;
            then initSensors;
            then loadMap;

            action initSensors;
                then joinInit;
            action loadMap;
                then joinInit;
        join joinInit;

        // Sequential execution
        then action planRoute;
        then action executeRoute;

        // Decision
        then if missionSuccess {
            action returnToBase;
            then action shutdown;
        } else {
            action retryPlanning;
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 6: Requirements with constraint predicates
    // ═══════════════════════════════════════════════════════════════

    part def Robot {
        attribute maxSpeedMs : Real;
        attribute totalMassKg : Real;
        attribute enduranceHours : Real;
    }

    requirement def MaxVelocityReq {
        doc /* Maximum speed on pedestrian paths. */
        subject robot : Robot;
        require constraint { robot.maxSpeedMs <= 2.0 }
    }

    requirement def MaxMassReq {
        doc /* Maximum system mass. */
        subject robot : Robot;
        require constraint { robot.totalMassKg <= 25.0 }
    }

    requirement def MinEnduranceReq {
        doc /* Minimum operational endurance. */
        subject robot : Robot;
        require constraint { robot.enduranceHours >= 4.0 }
    }

    requirement def EmergencyStopReq {
        doc /* Must stop within 0.5 seconds. */
        subject robot : Robot;
    }

    requirement def CollisionAvoidanceReq {
        doc /* Must detect and avoid obstacles. */
        subject robot : Robot;
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 7: Satisfy requirement links (lesson24 pattern)
    //         satisfy requirement : RequirementDef;
    // ═══════════════════════════════════════════════════════════════

    part def TrajectoryTracker {
        satisfy requirement : MaxVelocityReq;
    }

    part def CollisionGuard {
        satisfy requirement : EmergencyStopReq;
        satisfy requirement : CollisionAvoidanceReq;
    }

    part def TestRobot :> Robot {
        :>> maxSpeedMs = 1.5;
        :>> totalMassKg = 18.0;
        :>> enduranceHours = 7.0;

        part tracker : TrajectoryTracker;
        part guard : CollisionGuard;

        satisfy requirement : MaxMassReq;
        satisfy requirement : MinEnduranceReq;

        exhibit state operationalMode : OperationalModes;
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 8: Verification (flashlight pattern)
    //         verification name { subject ...; objective { verify req; } }
    // ═══════════════════════════════════════════════════════════════

    verification def MassVerification {
        doc /* Verify mass budget. */
        subject testRobot : TestRobot;

        action def WeighProcedure {
            doc /* Place robot on scale, record mass. */
        }
    }

    verification def EnduranceVerification {
        doc /* Verify operational endurance. */
        subject testRobot : TestRobot;

        action def RunEnduranceLoop {
            doc /* Execute delivery loop until battery at 10%. */
        }
    }

    verification def EmergencyStopVerification {
        doc /* Verify braking response time. */
        subject testRobot : TestRobot;

        action def BrakingTest {
            doc /* Drive at max speed, trigger e-stop, measure time. */
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // TEST 9: Allocation definition
    // ═══════════════════════════════════════════════════════════════

    part def OnboardComputer;

    allocation def SoftwareToHardware {
        doc /* Maps software nodes to compute platform. */
        end softwareNode;
        end hardwareNode;
    }
}
