// Test Sensmetry's own L18 Reindeer Controller — proven complex state machine.
// Compare what the CLI Tom Sawyer can do vs. interactive Modeler.

private import L18_States::*;
private import Views::*;

view reindeer_d1 {
    expose ReindeerController;
    expose ReindeerController::*;
    attribute depth = 1;
}

view reindeer_d2 {
    expose ReindeerController;
    expose ReindeerController::*;
    attribute depth = 2;
}

view reindeer_d3 {
    expose ReindeerController;
    expose ReindeerController::*;
    attribute depth = 3;
}
