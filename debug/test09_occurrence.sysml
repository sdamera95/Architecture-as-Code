package 'API Sequence Views' {

    part def Platform;
    part def Human;
    part def GP;

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

        message 'Access protected resource' from User.sendAccessRequest to 'GitLab'.receiveAccessRequest;
        message 'Redirect with SAML AuthnRequest' from 'GitLab'.sendAuthRedirect to User.receiveAuthRedirect;
        message 'Forward AuthnRequest' from User.receiveAuthRedirect to 'Google Workspace'.receiveAuthRequest;
        message 'Present login page' from 'Google Workspace'.sendLoginPage to User.revealLoginPage;
        message 'Submit credentials' from User.revealLoginPage to 'Google Workspace'.receiveCredentials;
        message 'HTTP POST with SAMLResponse' from 'Google Workspace'.sendSAMLResponse to 'GitLab'.receiveSAMLResponse;
        message 'POST SAMLResponse to ACS' from User.revealSAMLResponse to 'GitLab'.receiveSAMLResponse;
        message 'Create session & redirect to resource' from 'GitLab'.sendValidation to User.receiveValidation;
    }
}
