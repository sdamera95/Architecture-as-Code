// Experiment 18: Cross-pillar composite view
//
// Question: Can a single view render structure + behavior + requirements + V&V
// together coherently? This is Figure 2 (fig:mbse_architecture), the central
// thesis figure. Prior experience with satisfy links (test17) shows edges do
// NOT connect parts to requirements — relationships appear as compartments
// inside parts. This experiment tests whether a multi-pillar view is still
// readable when nothing links across pillars visually.

private import Views::*;

// --- Behavior: state machine ---

state def OperationalModes {
    doc /* Simple operational mode state machine. */
    state idle;
    state active;
    state faulted;

    transition activate first idle then active;
    transition fault first active then faulted;
    transition recover first faulted then idle;
}

// --- Requirements ---

requirement def MaxVelocity {
    doc /* Speed shall not exceed limit. */
    attribute maxSpeed : ScalarValues::Real;
    require constraint { maxSpeed > 0 }
}

// --- Verification ---

verification def MaxVelocityVerification {
    doc /* Test that max velocity is observed. */
    subject sut : Vehicle;
}

// --- Components ---

part def TrajectoryTracker;
part def Battery;

// --- System exhibiting behavior and satisfying requirements ---

part def Vehicle {
    doc /* Vehicle integrating structure, behavior, requirements. */
    part tracker : TrajectoryTracker;
    part battery : Battery;

    exhibit state modes : OperationalModes;

    satisfy requirement : MaxVelocity {
        doc /* Satisfied by the trajectory tracker enforcing the limit. */
    }
}

// --- View A: Everything exposed, tree layout ---

view crossPillarTree {
    expose Vehicle;
    expose Vehicle::*;
    expose OperationalModes;
    expose OperationalModes::*;
    expose MaxVelocity;
    expose MaxVelocityVerification;
    render asTreeDiagram;
    attribute depth = 1;
}

// --- View B: Same content, nested layout ---

view crossPillarNested {
    expose Vehicle;
    expose Vehicle::*;
    expose OperationalModes;
    expose OperationalModes::*;
    expose MaxVelocity;
    expose MaxVelocityVerification;
    attribute depth = 1;
}

// --- View C: System only, relying on exhibit/satisfy to pull in other pillars ---

view systemCentric {
    expose Vehicle;
    expose Vehicle::*;
    attribute depth = 2;
}
