package UAVModel {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;

    // ===============================================================
    // 1. Attribute definitions (typed scalar quantities)
    // ===============================================================
    attribute def MassValue :> MassValue;
    attribute def LengthValue :> LengthValue;
    attribute def SpeedValue :> SpeedValue;
    attribute def DurationValue :> TimeValue;
    attribute def PowerValue :> PowerValue;
    attribute def EnergyValue :> EnergyValue;
    attribute def VoltageValue :> ElectricPotentialValue;
    attribute def AltitudeValue :> LengthValue;

    // ===============================================================
    // 2. Item definitions (things that flow through the system)
    // ===============================================================
    item def ElectricalPower {
        attribute voltage : VoltageValue;
        attribute power : PowerValue;
    }

    item def CommandSignal;
    item def TelemetryData;
    item def ThrustForce;
    item def SensorReading;

    // ===============================================================
    // 3. Port definitions
    // ===============================================================
    port def PowerPort {
        out item suppliedPower : ElectricalPower;
    }

    port def CommandPort {
        out item cmd : CommandSignal;
        in item ack : TelemetryData;
    }

    port def TelemetryPort {
        out item telemetry : TelemetryData;
    }

    port def ThrustPort {
        out item thrust : ThrustForce;
    }

    port def SensorPort {
        out item reading : SensorReading;
    }

    // ===============================================================
    // 4. Connection definitions
    // ===============================================================
    connection def PowerConnection {
        end powerEnd1 : PowerPort;
        end powerEnd2 : PowerPort;
    }
    connection def CommandConnection {
        end cmdEnd1 : CommandPort;
        end cmdEnd2 : CommandPort;
    }
    connection def ShaftConnection {
        end shaftEnd1 : ThrustPort;
        end shaftEnd2 : ThrustPort;
    }
    connection def ThrustConnection {
        end thrustEnd1 : ThrustPort;
        end thrustEnd2 : ThrustPort;
    }
    connection def SensorConnection {
        end sensorEnd1 : SensorPort;
        end sensorEnd2 : SensorPort;
    }
    connection def TelemetryConnection {
        end telemetryEnd1 : TelemetryPort;
        end telemetryEnd2 : TelemetryPort;
    }

    // ===============================================================
    // 5. Part definitions
    // ===============================================================

    // ---- 5a. Battery ------------------------------------------------
    part def Battery {
        attribute mass : MassValue;
        attribute capacity : EnergyValue;
        attribute nominalVolts : VoltageValue;

        port powerOut : PowerPort;
    }

    // ---- 5b. Motor and propeller -----------------------------------
    part def Motor {
        attribute mass : MassValue;
        attribute maxPower : PowerValue;

        port powerIn : ~PowerPort;
        port cmdIn : ~CommandPort;
        port shaftOut : ThrustPort;
    }

    part def Propeller {
        attribute mass : MassValue;
        attribute diameter : LengthValue;

        port shaftIn : ~ThrustPort;
        port thrustOut : ThrustPort;
    }

    // ---- 5c. Propulsion subsystem ----------------------------------
    part def PropulsionSubsystem {
        attribute mass : MassValue;

        port powerIn : ~PowerPort;
        port cmdIn : ~CommandPort;
        port thrustOut : ThrustPort;

        part motor : Motor;
        part propeller : Propeller;

        connection : PowerConnection connect powerIn to motor.powerIn;
        connection : CommandConnection connect cmdIn to motor.cmdIn;
        connection : ShaftConnection connect motor.shaftOut to propeller.shaftIn;
        connection : ThrustConnection connect propeller.thrustOut to thrustOut;
    }

    // ---- 5d. Sensors -----------------------------------------------
    // Note: 'out' is reserved, so port is named 'sensorOut'
    part def IMU {
        attribute mass : MassValue;
        port sensorOut : SensorPort;
    }

    part def GPS {
        attribute mass : MassValue;
        port sensorOut : SensorPort;
    }

    part def Barometer {
        attribute mass : MassValue;
        port sensorOut : SensorPort;
    }

    // ---- 5e. Flight controller -------------------------------------
    part def FlightController {
        attribute mass : MassValue;

        port powerIn : ~PowerPort;
        port imuIn : ~SensorPort;
        port gpsIn : ~SensorPort;
        port baroIn : ~SensorPort;
        port motorCmdOut : CommandPort;
        port telemetryOut : TelemetryPort;
    }

    // ---- 5f. Avionics subsystem ------------------------------------
    part def AvionicsSubsystem {
        attribute mass : MassValue;

        port powerIn : ~PowerPort;
        port motorCmdOut : CommandPort;
        port telemetryOut : TelemetryPort;

        part fcc : FlightController;
        part imu : IMU;
        part gps : GPS;
        part baro : Barometer;

        connection : PowerConnection connect powerIn to fcc.powerIn;
        connection : SensorConnection connect imu.sensorOut to fcc.imuIn;
        connection : SensorConnection connect gps.sensorOut to fcc.gpsIn;
        connection : SensorConnection connect baro.sensorOut to fcc.baroIn;
        connection : CommandConnection connect fcc.motorCmdOut to motorCmdOut;
        connection : TelemetryConnection connect fcc.telemetryOut to telemetryOut;
    }

    // ---- 5g. Payload (camera) --------------------------------------
    part def CameraPayload {
        attribute mass : MassValue;
        port powerIn : ~PowerPort;
        port telemetryOut : TelemetryPort;
    }

    // ---- 5h. Airframe ----------------------------------------------
    part def Airframe {
        attribute mass : MassValue;
        attribute wingspan : LengthValue;
    }

    // ===============================================================
    // 6. Top-level UAV system
    // ===============================================================
    part def UAV {
        attribute totalMass : MassValue;
        attribute cruiseSpeed : SpeedValue;
        attribute maxAltitude : AltitudeValue;
        attribute endurance : DurationValue;

        part airframe : Airframe;
        part battery : Battery;
        part propulsion : PropulsionSubsystem;
        part avionics : AvionicsSubsystem;
        part payload : CameraPayload;

        // Power distribution
        connection : PowerConnection connect battery.powerOut to propulsion.powerIn;
        connection : PowerConnection connect battery.powerOut to avionics.powerIn;
        connection : PowerConnection connect battery.powerOut to payload.powerIn;

        // Command path
        connection : CommandConnection connect avionics.motorCmdOut to propulsion.cmdIn;

        // Flows
        flow from battery.powerOut.suppliedPower to propulsion.powerIn.suppliedPower;

        flow from battery.powerOut.suppliedPower to avionics.powerIn.suppliedPower;

        flow from battery.powerOut.suppliedPower to payload.powerIn.suppliedPower;

        flow from avionics.motorCmdOut.cmd to propulsion.cmdIn.cmd;
    }

    // ===============================================================
    // 7. Mission action model
    // ===============================================================
    action def Takeoff;
    action def Cruise;
    action def Survey;
    action def ReturnToBase;
    action def Land;

    action def Mission {
        action takeoff : Takeoff;
        action cruise : Cruise;
        action survey : Survey;
        action returnToBase : ReturnToBase;
        action land : Land;

        first takeoff then cruise;
        first cruise then survey;
        first survey then returnToBase;
        first returnToBase then land;
    }

    // ===============================================================
    // 8. Requirements (speculative syntax, not yet parser-validated)
    // ===============================================================
    requirement def MassBudget {
        doc
        /* The UAV total mass shall not exceed 5 kg. */
        subject uav : UAV;
        require constraint { uav.totalMass <= 5 [SI::kg] }
    }

    requirement def EnduranceRequirement {
        doc
        /* The UAV shall sustain flight for at least 30 minutes. */
        subject uav : UAV;
        require constraint { uav.endurance >= 30 [SI::min] }
    }

    requirement def AltitudeRequirement {
        doc
        /* The UAV shall be capable of reaching 400 m AGL. */
        subject uav : UAV;
        require constraint { uav.maxAltitude >= 400 [SI::m] }
    }
}
