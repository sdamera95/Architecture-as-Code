package ShowcaseAGRNav2Sim {
    doc
    /* Simulation deployment configuration for the Nav2 hybrid robot.

       The simulation environment and workstation are PLAIN SysML v2 parts,
       deliberately NOT typed against the ros2-sysmlv2 library: the bridge
       extractor therefore ignores them (library-harness projection), exactly
       as it ignores mechanical and electrical structure. The software
       architecture is reused unchanged from ShowcaseAGRNav2Full; what this
       package adds is the deployment story: who hosts the stack, and where
       the sensor data comes from in simulation.

       At runtime, Isaac Sim's ROS2 bridge stands in for the modeled sensor
       drivers (publishing /scan, /camera/depth/points, /imu/data; subscribing
       /cmd_vel; serving /clock). Launch with use_sim_time:=true and list the
       simulator's nodes in the conformance monitor's ignored_node_patterns
       parameter; the monitor then reports them as tolerated out-of-model
       nodes instead of drift. See demos/RUNBOOK.md. */

    private import ScalarValues::*;
    private import ShowcaseAGRNav2Full::*;

    part def IsaacSimEnvironment {
        doc /* NVIDIA Isaac Sim instance. Its ROS2 bridge provides the
               simulated sensor topics and consumes velocity commands.
               Out of extractor scope by design. */
        attribute sceneUsd : String = "warehouse_agr.usd";
        attribute physicsRateHz : Real = 60.0;
        attribute headless : Boolean = false;
    }

    part def RTXWorkstation {
        doc /* Ubuntu 24.04 / ROS2 Jazzy workstation with NVIDIA RTX PRO 6000
               GPUs; runs Isaac Sim and the generated stack side by side. */
        attribute gpuModel : String = "RTX PRO 6000";
        attribute os : String = "Ubuntu 24.04";
        attribute ros2Distro : String = "jazzy";
    }

    part def SimulatedAGRNav2Deployment {
        doc /* Sim-in-the-loop configuration: the same architecture model that
               drives code generation, hosted entirely on the workstation with
               Isaac Sim as the sensor/actuation source. */
        part robot : GroundRobotWithNav2;
        part simulator : IsaacSimEnvironment;
        part workstation : RTXWorkstation;

        allocate simulator to workstation;
        allocate robot to workstation;
    }
}
