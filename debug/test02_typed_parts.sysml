package Test02TypedParts {
    part def Client;
    part def Server;

    part def Seq2 {
        part client : Client {
            event occurrence sendReq;
            then event occurrence recvResp;
        }
        part server : Server {
            event occurrence recvReq;
            then event occurrence sendResp;
        }
        message request from client.sendReq to server.recvReq;
        message response from server.sendResp to client.recvResp;
    }
}
