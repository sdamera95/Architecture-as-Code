package Test04OccurrenceDef {
    occurrence def RequestEvent;
    occurrence def ResponseEvent;

    part def Seq4 {
        part client {
            event occurrence sendReq : RequestEvent;
            then event occurrence recvResp : ResponseEvent;
        }
        part server {
            event occurrence recvReq : RequestEvent;
            then event occurrence sendResp : ResponseEvent;
        }
        message request from client.sendReq to server.recvReq;
        message response from server.sendResp to client.recvResp;
    }
}
