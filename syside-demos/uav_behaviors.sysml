package UAVBehaviors {
    doc
    /* Minimal model focused on behavioral modeling in SysML v2:
       state machines, action sequences with dataflow, and mission
       composition. Stripped of structural detail so it fits within
       CATIA Magic Community Edition element limits. */

    private import ScalarValues::*;

    // ===============================================================
    // 1. Minimal item defs (just enough for action I/O typing)
    // ===============================================================

    item def Pose {
        attribute x : Real;
        attribute y : Real;
        attribute z : Real;
    }

    item def Path {
        attribute numWaypoints : Integer;
    }

    item def NavigationGoal {
        attribute targetX : Real;
        attribute targetY : Real;
    }

    // ===============================================================
    // 2. State machine definitions
    // ===============================================================

    state def FlightModes {
        doc /* Primary flight mode state machine.
               7 states representing operational modes. */

        state grounded;
        state preflight;
        state hovering;
        state cruising;
        state surveying;
        state landing;
        state emergency;

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
        doc /* Battery SOC monitoring. */

        state nominal;
        state warning;
        state critical;

        first nominal then warning;
        first warning then critical;
    }

    state def NavigationStates {
        doc /* Waypoint following state machine. */

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
    // 3. Leaf action definitions (atomic operations)
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

    // ===============================================================
    // 4. Composite action: plan-then-follow pipeline
    // ===============================================================

    action def PlanPath {
        doc /* Compute a collision-free path. */
        in item currentPose : Pose;
        in item goal : NavigationGoal;
        out item plannedPath : Path;
    }

    action def FollowPath {
        doc /* Execute a planned path. */
        in item path : Path;
        in item currentPose : Pose;
        out item reachedGoal : Boolean;
    }

    action def NavigateToWaypoint {
        doc /* Full navigation pipeline: plan then follow.
               Demonstrates action composition with dataflow. */
        in item goal : NavigationGoal;
        out item success : Boolean;

        action plan : PlanPath;
        action follow : FollowPath;

        flow from goal to plan.goal;
        flow from plan.plannedPath to follow.path;

        first plan then follow;
    }

    // ===============================================================
    // 5. Mission sequence (top-level behavioral composition)
    // ===============================================================

    action def Mission {
        doc /* Complete UAV mission: takeoff, cruise, survey, return, land.
               Each phase is a typed action usage with succession ordering. */

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
}
