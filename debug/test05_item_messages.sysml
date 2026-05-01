package Test05ItemMessages {
    item def Request;
    item def Response;

    part def Seq5 {
        part client {
            event occurrence sendReq;
            then event occurrence recvResp;
        }
        part server {
            event occurrence recvReq;
            then event occurrence sendResp;
        }
        message request : Request from client.sendReq to server.recvReq;
        message response : Response from server.sendResp to client.recvResp;
    }
}
