package ServerSequenceModel {
    private import ScalarValues::String;

    package SignalDefinitions {
        item def Subscribe {
            attribute topic : String;
            ref part subscriber;
        }
        item def Publish {
            attribute topic : String;
            ref publication;
        }
        item def Deliver {
            ref publication;
        }
    }

    public import SignalDefinitions::*;

    part def PubSubSequence {
        part producer[1] {
            event occurrence publishSourceEvent;
        }

        message publishMessage from producer.publishSourceEvent to server.publishTargetEvent;

        part server[1] {
            event occurrence subscribeTargetEvent;
            then event occurrence publishTargetEvent;
            then event occurrence deliverSourceEvent;
        }

        message subscribeMessage from consumer.subscribeSourceEvent to server.subscribeTargetEvent;
        message deliverMessage from server.deliverSourceEvent to consumer.deliverTargetEvent;

        part consumer {
            event occurrence subscribeSourceEvent;
            then event occurrence deliverTargetEvent;
        }
    }
}
