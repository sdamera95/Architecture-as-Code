// Experiment 19: Depth thresholds for topology figures with ports + connections
//
// Question: Is depth=3 nested rendering publication-quality for a Nav2-style
// topology figure (Figure 6, Figure 8)? At what depth do ports become visible?
// Are connection wires drawn?
//
// Setup: 3 nodes wired by 2 topic connections — minimal but representative.

private import Views::*;
private import ScalarValues::String;

// --- Mimic ROS2 port + connection types (no library import for isolation) ---

item def Message;
item def LaserScan :> Message;
item def Twist :> Message;

port def TopicPublisher {
    attribute topicName : String;
    out item msg : Message;
}

port def TopicSubscriber {
    attribute topicName : String;
    in item msg : Message;
}

connection def TopicConnection {
    end pub : TopicPublisher;
    end sub : TopicSubscriber;
}

// --- 3 node defs with typed ports ---

part def LidarNode {
    port scanPub : TopicPublisher {
        :>> topicName = "/scan";
        out item :>> msg : LaserScan;
    }
}

part def Planner {
    port scanSub : TopicSubscriber {
        :>> topicName = "/scan";
        in item :>> msg : LaserScan;
    }
    port cmdPub : TopicPublisher {
        :>> topicName = "/cmd_vel";
        out item :>> msg : Twist;
    }
}

part def Driver {
    port cmdSub : TopicSubscriber {
        :>> topicName = "/cmd_vel";
        in item :>> msg : Twist;
    }
}

// --- Topology system ---

part def Robot {
    part lidar : LidarNode;
    part planner : Planner;
    part driver : Driver;

    connection scanWire : TopicConnection
        connect pub ::> lidar.scanPub to sub ::> planner.scanSub;
    connection cmdWire : TopicConnection
        connect pub ::> planner.cmdPub to sub ::> driver.cmdSub;
}

// --- Views at varying depths ---

view depth1Tree {
    expose Robot;
    expose Robot::*;
    render asTreeDiagram;
    attribute depth = 1;
}

view depth1Nested {
    expose Robot;
    expose Robot::*;
    attribute depth = 1;
}

view depth2Nested {
    expose Robot;
    expose Robot::*;
    attribute depth = 2;
}

view depth3Nested {
    expose Robot;
    expose Robot::*;
    attribute depth = 3;
}

view depth4Nested {
    expose Robot;
    expose Robot::*;
    attribute depth = 4;
}
