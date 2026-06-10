package UAVTradeStudy {
    doc
    /* UAV system model with concrete parameter values designed for
       trade studies on flight endurance. Extends the structural
       architecture from demo.sysml with numeric values, power budgets,
       and a parametric endurance calculation.

       The key trade-off: larger batteries increase endurance but also
       increase mass, which increases propulsion power demand, which
       reduces endurance. There is a sweet spot. */

    private import ScalarValues::*;

    // ===============================================================
    // 1. Item definitions (things that flow)
    // ===============================================================

    item def ElectricalPower {
        attribute voltage : Real;
        attribute currentDraw : Real;
    }

    item def CommandSignal;
    item def TelemetryData;
    item def SensorReading;

    // ===============================================================
    // 2. Port definitions
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

    port def SensorPort {
        out item reading : SensorReading;
    }

    // ===============================================================
    // 3. Connection definitions
    // ===============================================================

    connection def PowerConnection {
        end source : PowerPort;
        end target : PowerPort;
    }
    connection def CommandConnection {
        end source : CommandPort;
        end target : CommandPort;
    }
    connection def SensorConnection {
        end source : SensorPort;
        end target : SensorPort;
    }
    connection def TelemetryConnection {
        end source : TelemetryPort;
        end target : TelemetryPort;
    }

    // ===============================================================
    // 4. Part definitions with concrete parameters
    // ===============================================================

    // ---- Battery ---------------------------------------------------
    // Key trade parameter: capacity (Wh) — drives endurance
    // Trade-off: higher capacity = more mass = more power to fly

    part def Battery {
        attribute massKg : Real;
        attribute capacityWh : Real;
        attribute nominalVoltage : Real;
        attribute specificEnergy : Real;   // Wh/kg — technology constant

        port powerOut : PowerPort;
    }

    // ---- Motors (4x for quadrotor) ---------------------------------

    part def Motor {
        attribute massKg : Real;
        attribute maxPowerW : Real;
        attribute efficiencyPct : Real;   // 0-100

        port powerIn : ~PowerPort;
        port cmdIn : ~CommandPort;
    }

    // ---- Propulsion subsystem (4 motors) ---------------------------

    part def PropulsionSubsystem {
        attribute numMotors : Integer;
        attribute massKg : Real;
        attribute hoverPowerW : Real;      // power at hover for given total mass

        port powerIn : ~PowerPort;
        port cmdIn : ~CommandPort;

        part motor : Motor;
    }

    // ---- Sensors ---------------------------------------------------

    part def IMU {
        attribute massKg : Real;
        attribute powerW : Real;
        port sensorOut : SensorPort;
    }

    part def GPS {
        attribute massKg : Real;
        attribute powerW : Real;
        port sensorOut : SensorPort;
    }

    part def Barometer {
        attribute massKg : Real;
        attribute powerW : Real;
        port sensorOut : SensorPort;
    }

    // ---- Flight controller -----------------------------------------

    part def FlightController {
        attribute massKg : Real;
        attribute powerW : Real;

        port powerIn : ~PowerPort;
        port imuIn : ~SensorPort;
        port gpsIn : ~SensorPort;
        port baroIn : ~SensorPort;
        port motorCmdOut : CommandPort;
        port telemetryOut : TelemetryPort;
    }

    // ---- Avionics subsystem ----------------------------------------

    part def AvionicsSubsystem {
        attribute massKg : Real;
        attribute totalPowerW : Real;

        port powerIn : ~PowerPort;
        port motorCmdOut : CommandPort;
        port telemetryOut : TelemetryPort;

        part fcc : FlightController;
        part imu : IMU;
        part gps : GPS;
        part baro : Barometer;
    }

    // ---- Payload ---------------------------------------------------

    part def CameraPayload {
        attribute massKg : Real;
        attribute powerW : Real;

        port powerIn : ~PowerPort;
        port telemetryOut : TelemetryPort;
    }

    // ---- Airframe --------------------------------------------------

    part def Airframe {
        attribute massKg : Real;
        attribute wingspanM : Real;
    }

    // ===============================================================
    // 5. Top-level UAV with parametric endurance model
    // ===============================================================

    part def UAV {
        // ---- Subsystem instances with concrete values ----

        part airframe : Airframe {
            :>> massKg = 0.8;
            :>> wingspanM = 0.5;
        }

        part battery : Battery {
            // ** Trade parameter: capacityWh **
            // massKg is derived from capacity and specific energy
            :>> capacityWh = 100.0;
            :>> specificEnergy = 200.0;  // Wh/kg (typical Li-Po)
            :>> massKg = capacityWh / specificEnergy;
            :>> nominalVoltage = 22.2;   // 6S Li-Po
        }

        part propulsion : PropulsionSubsystem {
            :>> numMotors = 4;

            part :>> motor {
                :>> massKg = 0.065;
                :>> maxPowerW = 250.0;
                :>> efficiencyPct = 85.0;
            }

            :>> massKg = numMotors * motor.massKg;  // 4 * 0.065 = 0.26 kg
        }

        part avionics : AvionicsSubsystem {
            part :>> fcc {
                :>> massKg = 0.05;
                :>> powerW = 5.0;
            }
            part :>> imu {
                :>> massKg = 0.01;
                :>> powerW = 0.5;
            }
            part :>> gps {
                :>> massKg = 0.015;
                :>> powerW = 0.8;
            }
            part :>> baro {
                :>> massKg = 0.005;
                :>> powerW = 0.1;
            }

            :>> massKg = fcc.massKg + imu.massKg + gps.massKg + baro.massKg;
            :>> totalPowerW = fcc.powerW + imu.powerW + gps.powerW + baro.powerW;
        }

        part payload : CameraPayload {
            :>> massKg = 0.15;
            :>> powerW = 8.0;
        }

        // ---- Power distribution topology ----

        connection : PowerConnection connect battery.powerOut to propulsion.powerIn;
        connection : PowerConnection connect battery.powerOut to avionics.powerIn;
        connection : PowerConnection connect battery.powerOut to payload.powerIn;
        connection : CommandConnection connect avionics.motorCmdOut to propulsion.cmdIn;

        // ---- Flows ----

        flow from battery.powerOut.suppliedPower to propulsion.powerIn.suppliedPower;
        flow from battery.powerOut.suppliedPower to avionics.powerIn.suppliedPower;
        flow from battery.powerOut.suppliedPower to payload.powerIn.suppliedPower;
        flow from avionics.motorCmdOut.cmd to propulsion.cmdIn.cmd;

        // ---- Derived system-level attributes ----

        // Total mass: sum of all subsystem masses
        attribute totalMassKg : Real =
            airframe.massKg +
            battery.massKg +
            propulsion.massKg +
            avionics.massKg +
            payload.massKg;

        // Hover power model (simplified):
        //   P_hover = k * totalMass^1.5
        // where k is a propulsive constant (W / kg^1.5)
        // This captures the physics: heavier UAV needs more thrust,
        // thrust power scales as mass^1.5 (momentum theory)
        attribute propulsiveConstant : Real = 50.0;  // W/kg^1.5 (empirical)

        // Approximate: P = k * m * sqrt(m) ~ k * m^1.5
        // Since SysML v2 may not support fractional exponents in expressions,
        // we linearize around the operating point:
        //   P_hover ≈ k * totalMass * 1.0  (linear approximation for sweep)
        // A more accurate version would use the Python side for the nonlinear model
        attribute hoverPowerW : Real = propulsiveConstant * totalMassKg;

        // Total power budget
        attribute avionicsPowerW : Real = avionics.totalPowerW;
        attribute payloadPowerW : Real = payload.powerW;
        attribute totalPowerW : Real = hoverPowerW + avionicsPowerW + payloadPowerW;

        // ** THE KEY OUTPUT: Flight endurance **
        attribute enduranceHrs : Real = battery.capacityWh / totalPowerW;
        attribute enduranceMin : Real = enduranceHrs * 60.0;
    }

    // ===============================================================
    // 6. Mission action model
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
    // 7. Requirements
    // ===============================================================

    requirement def MassBudget {
        doc /* The UAV total mass shall not exceed 5 kg. */
        subject uav : UAV;
        require constraint { uav.totalMassKg <= 5.0 }
    }

    requirement def EnduranceRequirement {
        doc /* The UAV shall sustain flight for at least 30 minutes. */
        subject uav : UAV;
        require constraint { uav.enduranceMin >= 30.0 }
    }

    requirement def PowerBudget {
        doc /* Total system power draw shall not exceed battery discharge capacity. */
        subject uav : UAV;
        require constraint { uav.totalPowerW <= 600.0 }
    }
}
