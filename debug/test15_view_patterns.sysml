// Experiment 15: Simonas' view definition patterns
// Tests depth control, double expose, doc filtering, render directives.
//
// Key finding from reading Views.sysml and StandardViewDefinitions.sysml:
//   - StandardViewDefinitions defines VIEW TYPES (SequenceView, StateTransitionView, etc.)
//     but Tom Sawyer ignores these and auto-detects diagram type from model elements
//   - Views defines RENDERING MODES (asTreeDiagram, asInterconnectionDiagram, asElementTable)
//     which Tom Sawyer does use for layout selection
//   - These are two independent axes: what-type vs how-to-render

private import StandardViewDefinitions::*;
private import Views::*;

part def Sensor;
part def Processor;
part def Actuator;

state def RobotModes {
    doc /* Operating modes for a simple robot. */
    state idle;
    state active;
    state errorState;

    transition activate first idle then active;
    transition fault first active then errorState;
    transition recover first errorState then idle;
}

action def SensorPipeline {
    doc /* Sensor data processing pipeline. */
    action readSensor;
    action filterNoise;
    action publishData;

    first readSensor then filterNoise;
    first filterNoise then publishData;
}

part def SimpleRobot {
    doc /* A minimal robot for view testing. */
    part sensor : Sensor;
    part processor : Processor;
    part actuator : Actuator;
}

// ---- View A: Simonas pattern (double expose + depth + filter) ----

view robotStructureSimonas {
    expose SimpleRobot;
    expose SimpleRobot::*;
    render asTreeDiagram;
    filter not @SysML::Documentation;
    attribute depth = 1;
}

// ---- View B: Our current pattern (single expose, no depth) ----

view robotStructureOurs : GeneralView {
    expose SimpleRobot;
}

// ---- View C: State machine with Simonas pattern ----

view robotModesSimonas {
    expose RobotModes;
    expose RobotModes::*;
    attribute depth = 1;
}

// ---- View D: State machine with our pattern ----

view robotModesOurs : StateTransitionView {
    expose RobotModes;
}

// ---- View E: Action flow with Simonas pattern ----

view sensorPipelineSimonas {
    expose SensorPipeline;
    expose SensorPipeline::*;
    attribute depth = 1;
}

// ---- View F: Action flow with our pattern ----

view sensorPipelineOurs : ActionFlowView {
    expose SensorPipeline;
}
