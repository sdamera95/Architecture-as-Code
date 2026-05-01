package 'API Sequence Views' {
    occurrence 'SAML Authentication Sequence' {
        part User : Human {
            event occurrence sendAccessRequest;
            then event occurrence receiveAuthRedirect;
            then event occurrence revealLoginPage;
            then event occurrence revealSAMLResponse;
            then event occurrence receiveValidation;
        }

        part 'GitLab' : Platform {
            event occurrence receiveAccessRequest;
            then event occurrence sendAuthRedirect;
            then event occurrence receiveSAMLResponse;
            then event occurrence sendValidation;
        }

        part 'Google Workspace' : GP {
            event occurrence receiveAuthRequest;
            then event occurrence sendLoginPage;
            then event occurrence receiveCredentials;
            then event occurrence sendSAMLResponse;
        }

        // Phase 1: Initial request & SSO redirect
        message 'Access protected resource' : Msg
            from User.sendAccessRequest to 'GitLab'.receiveAccessRequest;
        message 'Redirect with SAML AuthnRequest' : Msg
            from 'GitLab'.sendAuthRedirect to User.receiveAuthRedirect;
        message 'Forward AuthnRequest' : Msg
            from User.receiveAuthRedirect to 'Google Workspace'.receiveAuthRequest;

        // Phase 2: IdP authentication
        message 'Present login page' : Msg
            from 'Google Workspace'.sendLoginPage to User.revealLoginPage;
        message 'Submit credentials' : Msg
            from User.revealLoginPage to 'Google Workspace'.receiveCredentials;
        message 'HTTP POST with SAMLResponse' : Msg
            from 'Google Workspace'.sendSAMLResponse to 'GitLab'.receiveSAMLResponse;

        // Phase 3: SP validation & session creation
        message 'POST SAMLResponse to ACS' : Msg from User.revealSAMLResponse to 'GitLab'.receiveSAMLResponse;
        message 'Create session & redirect to resource' : Msg
            from 'GitLab'.sendValidation to User.receiveValidation;
    }
}

part def Platform;
part def Human;
part def GP;
item def Msg;
