// Experiment 13: occurrence def vs bare occurrence (side-by-side)
// Tests whether Tom Sawyer's auto-detection differs between the two.

part def Server;
part def Client;

// ---- Pattern A: occurrence def (Simonas' recommendation) ----

occurrence def RequestResponseDef {
    part client : Client {
        event occurrence sendRequest;
        then event occurrence receiveResponse;
    }

    part server : Server {
        event occurrence receiveRequest;
        then event occurrence sendResponse;
    }

    message request from client.sendRequest to server.receiveRequest;
    then message response from server.sendResponse to client.receiveResponse;
}

// ---- Pattern B: bare occurrence (our current approach) ----

occurrence requestResponseUsage {
    part client : Client {
        event occurrence sendRequest;
        then event occurrence receiveResponse;
    }

    part server : Server {
        event occurrence receiveRequest;
        then event occurrence sendResponse;
    }

    message request from client.sendRequest to server.receiveRequest;
    then message response from server.sendResponse to client.receiveResponse;
}
