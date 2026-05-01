# AGR Pillar Views — Inventory for Manuscript Mosaic

**Source model:** [`syside-demos/showcase_agr_full.sysml`](../../syside-demos/showcase_agr_full.sysml) (the ab initio AGR — Tier 1 per `idempotent-dancing-axolotl.md`)

**Scope:** All views below render REAL AGR architectural elements. No invented content.

## Rendered Pillar Views

Each SVG is a separate file in this directory, ready for the user's mosaic composition.

| Pillar | View | SVG | Source elements |
|---|---|---|---|
| **Structure (system tree)** | `robotStructure` | `diagram-robotStructure.svg` (60 KB) | `AutonomousGroundRobot::*` at depth=1, tree layout |
| **Structure (focused IBD)** | `prototype_safetyTopology` | `diagram-prototype_safetyTopology.svg` (42 KB) | `SafetyChainFocus` (lidar + obstacleDetector + velocitySmoother + collisionGuard) at depth=3 with ports + wires |
| **Behavior (state machine)** | `operationalModes` | `diagram-operationalModes.svg` (23 KB) | `OperationalModes` state def at depth=1: idle, autonomous {planning, executing, recovering}, manual, emergency, charging; accept-via-port; guards |
| **Behavior (action flow)** | `missionFlow` | `diagram-missionFlow.svg` (37 KB) | `ExecuteMission` action def at depth=1: fork {initSensors, loadMap} → join → planRoute → navigate → if missionSuccess {returnToBase, shutdown} else handleFailure |
| **Behavior (sequence)** | `emergencyStopSequence` | `diagram-emergencyStopSequence.svg` (14 KB) | `emergencyStopProtocol` occurrence with 5 lifelines + temporal message ordering |
| **Requirements** | `systemRequirements` | `diagram-systemRequirements.svg` (41 KB) | All 9 requirement defs: MaxVelocityReq, MinEnduranceReq, MaxMassReq, LocalizationAccuracyReq, ObstacleDetectionRangeReq, EmergencyStopReq, CollisionAvoidanceReq, HumanDetectionReq, FailSafeReq |
| **V&V (verification cases)** | `verificationPlan` | `diagram-verificationPlan.svg` (26 KB) | 4 verification defs (MassVerification, EnduranceVerification, EmergencyStopVerification, LocalizationVerification) + PowerBudgetAnalysis |
| **Constraints (parametric)** | `prototype_constraintBudget` | `diagram-prototype_constraintBudget.svg` (7 KB) | `EmergencyStopBudget` constraint def with 4 attributes + sum constraint |

## Text-Based Cross-Pillar Interconnections (REAL AGR bindings)

The following relationships are present in the AGR model and are candidates for hand-drawn cross-pillar arrows in the mosaic.

### `satisfy` (Structure → Requirements)

| Source part | Target requirement | Line |
|---|---|---|
| `ObstacleDetector` | `ObstacleDetectionRangeReq` | 198 |
| `EKFLocalizer` | `LocalizationAccuracyReq` | 225 |
| `TrajectoryTracker` | `MaxVelocityReq` | 275 |
| `CollisionGuard` | `EmergencyStopReq` | 329 |
| `CollisionGuard` | `CollisionAvoidanceReq` | 333 |
| `AutonomousGroundRobot` | `MaxMassReq` | 791 |
| `AutonomousGroundRobot` | `MinEnduranceReq` | 796 |
| `AutonomousGroundRobot` | `FailSafeReq` | 800 |
| `AutonomousGroundRobot` | `HumanDetectionReq` | 804 |

### `exhibit state` (Structure → Behavior)

| Part | State machine | Line |
|---|---|---|
| `AutonomousGroundRobot` | `OperationalModes` | 899 |

### `allocate` (Software → Hardware)

11 software node usages allocated to `computer : OnboardComputer` (lines 902–912):
`lidar`, `imu`, `camera`, `obstacleDetector`, `ekfLocalizer`, `pathPlanner`, `trajectoryTracker`, `velocitySmoother`, `collisionGuard`, `mapServer`, `missionCoordinator`

### `accept ... via safetyPort` (architectural channel between Structure and Behavior)

`OperationalModes::triggerEmergency` transition: `accept EmergencyTrigger via safetyPort` — the model edge through which the structural `CollisionGuard` exercises its safety responsibility on the behavior model.

## Known CLI Limitations (still open)

- **Tom Sawyer cannot suppress compartments via filter** (Simonas, forum #447: "The filter is not supposed to suppress the doc compartment, only its node"). Inherited `«^stateTransitions»`, `«^entryAction»`, `«abstract action»` etc. surface at depth>=2.
- **Use case views with actor stick figures crash CLI Batik** (per CLAUDE.md). Use cases must be rendered in interactive Modeler.
- **`asInterconnectionDiagram` directive ignored by CLI** — only tree and nested supported (Experiment 3, 2026-04-15).
- **depth=3 needed for ports + wires on IBD** (Experiment 19), but at the cost of stdlib leak on richer types.

## Recommendation

For publication-quality output of the complex behavioral views (state machine, action flow), the user should re-render them in the **interactive Syside Modeler** which does not exhibit the same compartment leak as the CLI. The model + view definitions are ready; the user opens them in the Modeler, right-clicks each view → "Visualize view (labs)", exports SVG.

The structural / requirements / V&V / constraint views above are usable as-is from the CLI output for low-density panels.
