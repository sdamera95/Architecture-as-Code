package ros2_sysmlv2_nav_msgs {
    doc
    /* Navigation message types for ROS2.

       Maps to: nav_msgs package from ros2/common_interfaces (Jazzy).
       8 message types for maps, odometry, paths, and trajectories.

       Dependencies: ros2_sysmlv2_foundation (Header, Time),
                     ros2_sysmlv2_geometry_msgs (Pose, PoseStamped,
                     PoseWithCovariance, TwistWithCovariance, etc.). */

    private import ScalarValues::*;
    private import ros2_sysmlv2_foundation::*;
    private import ros2_sysmlv2_geometry_msgs::*;

    // ===============================================================
    // Map types
    // ===============================================================

    item def MapMetaData {
        doc /* Metadata for an OccupancyGrid map.
               Maps to nav_msgs/msg/MapMetaData. */
        attribute mapLoadTime : Time;
        attribute resolution : Real;
        attribute width : Integer;
        attribute height : Integer;
        attribute origin : Pose;
    }

    item def OccupancyGrid {
        doc /* 2D occupancy grid map. Cell values: 0=free, 100=occupied, -1=unknown.
               Maps to nav_msgs/msg/OccupancyGrid. */
        attribute header : Header;
        attribute info : MapMetaData;
        attribute data : Integer[0..*];
    }

    item def GridCells {
        doc /* Collection of cells in a grid, used for visualization.
               Maps to nav_msgs/msg/GridCells. */
        attribute header : Header;
        attribute cellWidth : Real;
        attribute cellHeight : Real;
        attribute cells : Point[0..*];
    }

    // ===============================================================
    // Odometry
    // ===============================================================

    item def Odometry {
        doc /* Estimated position and velocity in free space.
               Maps to nav_msgs/msg/Odometry.
               Pose is in header.frame_id frame (typically "odom").
               Twist is in child_frame_id frame (typically "base_link"). */
        attribute header : Header;
        attribute childFrameId : String;
        attribute pose : PoseWithCovariance;
        attribute twist : TwistWithCovariance;
    }

    // ===============================================================
    // Paths and trajectories
    // ===============================================================

    item def Path {
        doc /* Ordered list of poses representing a planned path.
               Maps to nav_msgs/msg/Path.
               Used by Nav2 planner server output. */
        attribute header : Header;
        attribute poses : PoseStamped[0..*];
    }

    item def Goals {
        doc /* Ordered list of goal poses.
               Maps to nav_msgs/msg/Goals. */
        attribute header : Header;
        attribute goals : PoseStamped[0..*];
    }

    item def TrajectoryPoint {
        doc /* Single point in a trajectory with full dynamics.
               Maps to nav_msgs/msg/TrajectoryPoint. */
        attribute header : Header;
        attribute pose : Pose;
        attribute velocity : Twist;
        attribute acceleration : Accel;
        attribute effort : Wrench;
    }

    item def Trajectory {
        doc /* Ordered list of trajectory points with full dynamics.
               Maps to nav_msgs/msg/Trajectory. */
        attribute header : Header;
        attribute points : TrajectoryPoint[0..*];
    }
}
