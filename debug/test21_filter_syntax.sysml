// Experiment 21: validate Syside filter syntax for stripping docs +
// attribute usage compartments + satisfy compartments from rendered views.
//
// Goal: reduce a topology figure to ONLY: part name boxes + port circles +
// wire arrows. No yellow «usage» boxes, no «satisfy» compartments,
// no «doc» blocks.

private import Views::*;
private import ScalarValues::String;
private import ScalarValues::Real;

item def Message;
item def LaserScan :> Message;

requirement def DummyReq {
    doc /* should be filtered */
    attribute target : Real;
    require constraint { target > 0 }
}

port def Pub {
    attribute topicName : String;
    out item msg : Message;
}
port def Sub {
    attribute topicName : String;
    in item msg : Message;
}
connection def Wire { end pub : Pub; end sub : Sub; }

part def Source {
    doc /* this should also be filtered */
    attribute frameId : String;
    attribute updateRate : Real;
    port out1 : Pub { :>> topicName = "/scan"; out item :>> msg : LaserScan; }
    satisfy requirement : DummyReq;
}

part def Sink {
    doc /* filtered */
    attribute frameId : String;
    port in1 : Sub { :>> topicName = "/scan"; in item :>> msg : LaserScan; }
}

part def MiniSystem {
    part src : Source;
    part dst : Sink;
    connection w : Wire connect src.out1 to dst.in1;
}

// View A: no filter (baseline noise)
view baseline {
    expose MiniSystem;
    expose MiniSystem::*;
    attribute depth = 3;
}

// View B: filter docs only
view filterDocs {
    expose MiniSystem;
    expose MiniSystem::*;
    filter not @SysML::Documentation;
    attribute depth = 3;
}

// View C: filter docs + attribute usages + satisfy usages
view filterAll {
    expose MiniSystem;
    expose MiniSystem::*;
    filter not @SysML::Documentation;
    filter not @SysML::AttributeUsage;
    filter not @SysML::SatisfyRequirementUsage;
    attribute depth = 3;
}
