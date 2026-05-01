package 'Emergency Stop Sequence' {
    private import StandardViewDefinitions::*;

    part operator {
        event occurrence triggerEstop;
    }

    part baseStation {
        event occurrence receiveEstop;
        then event occurrence relayEstop;
        then event occurrence receiveAck;
    }

    part coordinator {
        event occurrence receiveEstopCmd;
        then event occurrence sendCancel;
        then event occurrence receiveCancelAck;
        then event occurrence sendZeroVel;
        then event occurrence sendAck;
    }

    part tracker {
        event occurrence receiveCancelCmd;
        then event occurrence confirmCancel;
    }

    part guard {
        event occurrence receiveZeroVel;
    }

    message estopTrigger from operator.triggerEstop to baseStation.receiveEstop;
    message estopRelay from baseStation.relayEstop to coordinator.receiveEstopCmd;
    message cancelRequest from coordinator.sendCancel to tracker.receiveCancelCmd;
    message cancelConfirm from tracker.confirmCancel to coordinator.receiveCancelAck;
    message zeroVelocity from coordinator.sendZeroVel to guard.receiveZeroVel;
    message haltReport from coordinator.sendAck to baseStation.receiveAck;

    view estopSequence : SequenceView {
        expose 'Emergency Stop Sequence'::*;
    }
}
