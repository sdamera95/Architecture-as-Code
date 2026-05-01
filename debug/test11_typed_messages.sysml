package TestTypedMessages {

    item def Msg;

    occurrence requestResponse {
        part a {
            event occurrence sendRequest;
            then event occurrence receiveResponse;
        }

        part b {
            event occurrence receiveRequest;
            then event occurrence sendResponse;
        }

        message request : Msg from a.sendRequest to b.receiveRequest;
        message response : Msg from b.sendResponse to a.receiveResponse;
    }
}
