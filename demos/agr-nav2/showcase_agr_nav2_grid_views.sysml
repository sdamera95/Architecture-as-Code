package ShowcaseAGRNav2GridViews {
    doc
    /* Grid Views (Syside 0.9.0) for the AGR_nav2 hybrid showcase.

       Authored from
       docs/cowork/v9_candidates/grid_views/agr_nav2_allocation_design.md.
       The satisfy matrix is deferred (per agr_nav2_satisfy_design.md, the
       current model has only 1 nested satisfy declaration, yielding a too-
       sparse 7x2 matrix). To unblock, add 5 satisfy declarations as the
       design doc describes.

       Companion to syside-demos/showcase_agr_nav2_full.sysml. */

    private import SysideViews::*;
    private import ShowcaseAGRNav2Full::*;

    // ==================================================================
    // Allocation matrix — software components × subsystems
    // ==================================================================
    //
    // Rows: 5 custom rclpy nodes + the Nav2Stack composite = 6 rows.
    // Columns: 6 top-level subsystems of GroundRobotWithNav2.
    // Cells: auto-populated from `AllocationUsage` (the 6 `allocate ... to ...`
    //        declarations at showcase_agr_nav2_full.sysml:956-961). Currently
    //        single-column (all to compute); the design doc proposes adding
    //        LifecycleManagementContainer parts to surface the two-lifecycle-
    //        manager pattern as a 2-column split.

    view agrNav2AllocationMatrix : SV::MVD::AllocationMatrixView {
        doc
        /* Software-to-hardware execution allocation for the AGR_nav2 hybrid
           stack. 6 software→compute allocations, including the whole-stack
           `allocate autonomyStack.nav2 to compute.computer` that collapses
           11 Nav2 servers into a single row. */
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2;
        expose ShowcaseAGRNav2Full::GroundRobotWithNav2::*;

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
}
