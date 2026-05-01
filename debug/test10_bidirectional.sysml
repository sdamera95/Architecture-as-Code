package TestBidirectional {

    occurrence requestResponse {
        doc /* Minimal test: exactly 2 messages, opposite directions.
               m1: a sends to b (should arrow left → right)
               m2: b sends back to a (should arrow right → left) */

        part a {
            event occurrence sendRequest;
            then event occurrence receiveResponse;
        }

        part b {
            event occurrence receiveRequest;
            then event occurrence sendResponse;
        }

        message request from a.sendRequest to b.receiveRequest;
        message response from b.sendResponse to a.receiveResponse;
    }
}
