package Flashlight_StarterModel {
    // ran on release 2025-06 on 2025-07-21
    /* The following is a simple flashlight model that is intended to introduce modelers to SysML v2.
     * The scope includes some basic language features used to model system requirements, behavior, structure, analysis and verification.
     * This model contains usage elements with limited use of definition elements to simplify the example.
     * It is anticipated that a user will review and modify this model in their modeling environment.
     * As an example, a modification could include updating the flashlight requirments and design to add a flashing state.
     *
     * Refer to the following URL for instructional material on SysML v2 textual and graphical syntax: 
     * https://github.com/Systems-Modeling/SysML-v2-Release/tree/master/doc
     *
     * /* Updates
     * 2024-07-28 updates for rev a:
     * - Changed lines 38,39 from USCustomaryUnits to ISQ
     * - Changed import to private import in anticipation of spec update for next release 2024-06
     * 2025-05-09 updates for rev b:
     * - Added packages for Analysis and Verification
     * - Modified package structure
     * - Added simple definition and usage example under General Concepts package
     * 2025-05-09 Added context package for class exercise
     * 2025-07-21 Added ISQ to poweer in calc, updated views, added first to state transition 
     */
    private import ScalarValues::*;
    private import SI::*;
    private import USCustomaryUnits::*;
    
    private import Definitions::*;
    package Definitions{
        item def OnOffCmd;
        item def DCPwr;
        item def Light;
    }
    package FlashlightSpecificationAndDesign {
        package Requirements {
            requirement flashlightSpecification {
                requirement userInterface;
                requirement illumination {
                    requirement fieldOfView {
                        doc /* The flashlight field of view shall be 0 - 20 degrees.*/
                    }
                    requirement lightPower {
                        doc /* The light power shall be a minumum of TBD lumens.*/
                    }
                }
                requirement physical {
                    requirement portability;
                    requirement size {
                        doc /* The flashlight shall be less than 6 inches in length.*/
                    }
                    requirement weight {
                        doc /* The weight shall be less than 0.25 lbs.*/
                        attribute actualWeight :> mass;
                        require constraint {
                            actualWeight <= 0.25 [lb]
                        }
                    }
                }
                requirement reliability;
                requirement cost;
                requirement newRequirement;
            }
        }
        package Actions {
            action produceDirectedLight {
                in item onOffCmd;
                out item lightOut = directLight.lightOut;
                action provideDCPwr { out item dcPwr; }
                action connectDCPwr {
                    in item onOffCmd;
                    in item dcPwrIn;
                    out item dcPwrOut;
                }
                action generateLight {
                    in item dcPwrIn;
                    out item light;
                }
                action directLight {
                    in item lightIn;
                    out item lightOut;
                }
                fork fork1;
                    then provideDCPwr;
                    then connectDCPwr;
                first start then fork1;
                bind onOffCmd = connectDCPwr.onOffCmd;
                bind lightOut = directLight.lightOut;
                flow provideDCPwr.dcPwr to connectDCPwr.dcPwrIn;
                flow connectDCPwr.dcPwrOut to generateLight.dcPwrIn;
                flow generateLight.light to directLight.lightIn;
            }
        }
        package Parts {
            part flashlight {
                attribute mass :> ISQBase::mass;
                attribute fov : Real;
                attribute illuminationLevel : Real;
                port cmdPort;
                port lightOutPort;
                port handPort;
                perform Actions::produceDirectedLight;
                exhibit state flashlightStates {
                    state off;
                    state on {
                        do produceDirectedLight;
                    }
                    transition first start then off;
                    transition off_To_on first off accept onOffCmd : OnOffCmd via cmdPort then on;
                    transition on_To_off first on accept onOffCmd : OnOffCmd via cmdPort then off;
                }
                ref part battery [2] {
                    attribute power :> ISQMechanics::power = Analysis::BatteryPower(v, i);
                    attribute v :> voltage default 1.5 [V];
                    attribute i :> electricCurrent default 2.1 / 30 [A];
                    port dcPwrOutPort {
                        out item dcPwr;
                    }
                    perform produceDirectedLight.provideDCPwr;
                }
                part switch {
                    port cmdPort;
                    port inPort {
                        in item dcPwrIn : DCPwr;
                    }
                    port outPort {
                        out item dcPwrOut : DCPwr;
                    }
                    perform produceDirectedLight.connectDCPwr;
                }
                part lamp {
                    attribute efficiency : Real;
                    port dcPwrInPort {
                        in item dcPwrIn : DCPwr;
                    }
                    port lightOutPort {
                        out item light : Light;
                    }
                    perform produceDirectedLight.generateLight;
                }
                part optics {
                    port lightInPort {
                        in item light : Light;
                    }
                    port lightOutPort {
                        out item directedLight : Light;
                    }
                    perform produceDirectedLight.directLight;
                    part reflector {
                        attribute radius :> length;
                    }
                    part lens;
                }
                part structure {
                    port handPort;
                    part frontHousing;
                    part middleHousing;
                    part backHousing;
                }
                bind cmdPort = switch.cmdPort;
                bind lightOutPort = optics.lightOutPort;
                bind handPort = structure.handPort;
                connect battery.dcPwrOutPort to switch.inPort {
                    flow of DCPwr from source.dcPwr to target.dcPwrIn;
                }
                connect switch.outPort to lamp.dcPwrInPort {
                    flow of DCPwr from source.dcPwrOut to target.dcPwrIn;
                }
                connect lamp.lightOutPort to optics.lightInPort {
                    flow of Light from source.light to target.light;
                }
            }
        }
        package RequirementsAllocation {
            private import Requirements::*;
            private import Parts::*;
            allocate flashlightSpecification to flashlight {
                allocate flashlightSpecification.physical.weight to flashlight.mass;
                allocate flashlightSpecification.illumination to flashlight.produceDirectedLight;
                allocate flashlightSpecification.illumination.fieldOfView to flashlight.fov;
                allocate flashlightSpecification.illumination.lightPower to flashlight.illuminationLevel;
            }
        }
    }
    package Analysis {
        calc def BatteryPower {
            in attribute voltage :> ISQ::voltage;
            in attribute current :> ISQ::electricCurrent;
            attribute numberBatteriesInSeries : Integer default 2;
            return power :> ISQ::power = numberBatteriesInSeries * voltage * current;
        }
        attribute batteryPower :> ISQ::power = BatteryPower(1.5 [V], 2.1 / 30 [A]);
        /* Note: current = currrent time (2.1 *3600 [A * s])/ battery life (30 *3600 [s])*/
    }
    package Verification {
        private import FlashlightSpecificationAndDesign::Requirements::*;
        private import FlashlightSpecificationAndDesign::Parts::*;
        public import VerificationCases::*;
        verification massTest {
            subject systemUnderTest :> flashlight;
            objective {
                doc /* Verify system under test satisfies its weight requirement*/
                verify flashlightSpecification.physical.weight;
            }
            @VerificationMethod { kind = (kind::test, kind::analyze); }
            action placeSystemOnScale;
            action weighSystem;
            action evaluateResult;
            action removeSystemFromScale;
        }
    }
    package Views1{
        //private import Views::*;
        view flashlightPartsTree{
            expose FlashlightSpecificationAndDesign::Parts::**;
            filter @SysML::PartUsage;
            render Views::asTreeDiagram;
        }
    }
}
package GeneralConcepts {
    private import ScalarValues::*;
    private import SI::*;
    private import USCustomaryUnits::*;
    package AttributeDeclarationExamples {
        attribute x1 : Integer = 1;
        attribute x2 : Real = 3.3;
        attribute x3 : Boolean = true;
        attribute x4 : String = "This is a String";
        attribute y1 :> length = 3.0 [m];
        attribute y2 :> mass = 100 [kg];
        attribute z1 :> length = 3.0 [ft];
        attribute z2 :> mass = 100 [lb];
    }
    package DefinitionAndUsageExample {
        part def Part1 {
            attribute mass :> ISQBase::mass;
        }
        part part1 : Part1;
    }
}

%viz

%viz --view tree --style showinherited --style comptree Flashlight_StarterModel::ContextPkg::Parts::context

%viz --view action --style showinherited --style comptree Flashlight_StarterModel::ContextPkg::Parts::context


