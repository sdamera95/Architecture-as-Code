// Experiment 14: then message ordering vs no ordering
// Tests whether temporal ordering between messages affects rendering.
// Also tests 3+ messages with a response arrow (right-to-left).

part def ClientNode;
part def ServerNode;
part def DatabaseNode;

occurrence def ThreePartyProtocol {
    part client : ClientNode {
        event occurrence sendQuery;
        then event occurrence receiveResult;
    }

    part server : ServerNode {
        event occurrence receiveQuery;
        then event occurrence forwardToDb;
        then event occurrence receiveDbResult;
        then event occurrence sendResult;
    }

    part database : DatabaseNode {
        event occurrence receiveDbQuery;
        then event occurrence returnDbResult;
    }

    // All messages temporally ordered with 'then'
    message query from client.sendQuery to server.receiveQuery;
    then message dbQuery from server.forwardToDb to database.receiveDbQuery;
    then message dbResult from database.returnDbResult to server.receiveDbResult;
    then message result from server.sendResult to client.receiveResult;
}
