package SeqTest {

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

        message query from client.sendQuery to server.receiveQuery;
        then message dbQuery from server.forwardToDb to database.receiveDbQuery;
        then message dbResult from database.returnDbResult to server.receiveDbResult;
        then message result from server.sendResult to client.receiveResult;
    }
}
