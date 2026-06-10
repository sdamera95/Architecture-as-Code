package ShowcaseAGRGridViews {
    doc
    /* Grid Views (Syside 0.9.0) for the AGR showcase: an allocation matrix
       and a satisfy matrix. Renders independently of Tom Sawyer via the
       Modeler's Grid Views pane; CSV-exportable.

       Authored from the design docs in
       docs/cowork/v9_candidates/grid_views/agr_allocation_design.md and
       agr_satisfy_design.md. See those docs for the row/column rationale
       and the current-vs-rich tradeoffs.

       Companion to syside-demos/showcase_agr_full.sysml. */

    private import SysideViews::*;
    private import ShowcaseAGRFull::*;

    // ==================================================================
    // 1. Allocation matrix — software components × subsystems
    // ==================================================================
    //
    // Rows: 11 ROS2 software components (autonomy stack + sensor drivers).
    // Columns: 6 top-level subsystems of AutonomousGroundRobot.
    // Cells: auto-populated from `AllocationUsage` (the 7 `allocate ... to ...`
    //        declarations at showcase_agr_full.sysml:1197-1203). Sparse
    //        single-column today; design doc lists rich-matrix options.

    view agrAllocationMatrix : SV::MVD::AllocationMatrixView {
        doc
        /* Software-to-hardware execution allocation for AGR. As of 2026-05-14
           the model declares 7 software→compute allocations (no others). */
        expose ShowcaseAGRFull::AutonomousGroundRobot;
        expose ShowcaseAGRFull::AutonomousGroundRobot::*;

        view :>> rowView {
            filter hastype SysML::PartUsage;
        }
        view :>> columnView {
            filter hastype SysML::PartUsage;
        }
        view :>> cellView {
            attribute :>> direction = Dir::row2col;
        }
    }

    // ==================================================================
    // 2. Satisfy matrix — requirements × parts that satisfy them
    // ==================================================================
    //
    // Rows: 9 individual requirement defs + 1 grouping = 10 rows.
    // Columns: parts that own `satisfy requirement` declarations
    //          (ObstacleDetector, EKFLocalizer, TrajectoryTracker,
    //           AGRVelocitySmoother, theRobot).
    // Cells: SatisfyRequirementUsage relationships.
    //
    // Uses base MatrixView with explicit satisfy filter rather than the
    // RequirementMatrixView preset, which filters by RequirementDerivation
    // (derive), not satisfy. See design doc for the distinction.

    view agrSatisfyMatrix : SV::MVD::MatrixView {
        doc
        /* Requirements-to-parts satisfy traceability for AGR. 6 of 50 cells
           populated. Empty rows surface system-level requirements without
           a single owning part (mass, endurance, human detection, fail-safe). */
        expose ShowcaseAGRFull;
        expose ShowcaseAGRFull::*;

        view :>> rowView {
            filter hastype SysML::RequirementDefinition;
        }
        view :>> columnView {
            filter hastype SysML::PartDefinition;
        }
        view :>> cellView {
            filter hastype SysML::SatisfyRequirementUsage;
        }
    }
}
