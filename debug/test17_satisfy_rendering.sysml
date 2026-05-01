// Experiment 17: How do `satisfy` links render in views?
//
// Question: When a part contains `satisfy req : ReqDef;`, do views show
//   (a) an edge between the part and the requirement,
//   (b) an anonymous compartment listing the satisfaction,
//   (c) nothing at all,
//   (d) something else?
//
// Test variants: satisfy inside a part, system-level satisfy outside, and
// a view that exposes both the part and the requirement together.

private import Views::*;

// --- Requirements ---

requirement def MaxVelocity {
    doc /* Vehicle velocity shall not exceed maxSpeed. */
    attribute maxSpeed : ScalarValues::Real;
    require constraint { maxSpeed > 0 }
}

requirement def CollisionAvoidance {
    doc /* Vehicle shall not collide with obstacles. */
    attribute clearance : ScalarValues::Real;
    require constraint { clearance >= 0.5 }
}

// --- Components that satisfy requirements ---

part def TrajectoryTracker;
part def CollisionGuard;
part def Battery;

// --- System with satisfy links inside the part def ---

part def Vehicle {
    doc /* A vehicle that satisfies safety + performance requirements. */
    part tracker : TrajectoryTracker;
    part guard : CollisionGuard;
    part battery : Battery;

    satisfy requirement : MaxVelocity {
        doc /* Satisfied by the trajectory tracker enforcing the speed limit. */
    }
    satisfy requirement : CollisionAvoidance {
        doc /* Satisfied by the collision guard maintaining clearance. */
    }
}

// --- View A: Structure only (no requirements exposed) ---

view structureOnly {
    expose Vehicle;
    expose Vehicle::*;
    render asTreeDiagram;
    attribute depth = 1;
}

// --- View B: Requirements + structure (separate exposes) ---

view structureAndRequirements {
    expose Vehicle;
    expose Vehicle::*;
    expose MaxVelocity;
    expose CollisionAvoidance;
    render asTreeDiagram;
    attribute depth = 1;
}

// --- View C: Same content rendered nested instead of tree ---

view structureAndRequirementsNested {
    expose Vehicle;
    expose Vehicle::*;
    expose MaxVelocity;
    expose CollisionAvoidance;
    attribute depth = 1;
}

// --- View D: Requirements only (probe how requirement defs render alone) ---

view requirementsOnly {
    expose MaxVelocity;
    expose CollisionAvoidance;
    attribute depth = 1;
}

// --- View E: Deep depth to see if satisfy edges appear with more traversal ---

view structureDeep {
    expose Vehicle;
    expose Vehicle::*;
    expose MaxVelocity;
    expose CollisionAvoidance;
    attribute depth = 3;
}
