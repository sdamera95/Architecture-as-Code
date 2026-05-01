package 'SAML Authentication Sequence' {
    private import StandardViewDefinitions::*;

    part def Platform;
    part def Human;
    part def GP;

    part 'User' : Human {
        event occurrence requestProtectedResource;
        then event occurrence receiveRedirect;
        then event occurrence submitCredentials;
        then event occurrence receiveAccessToken;
    }

    part 'GitLab' : Platform {
        event occurrence receiveInitialRequest;
        then event occurrence redirectToIdP;
        then event occurrence receiveSAMLResponse;
        then event occurrence grantAccess;
    }

    part 'Google Workspace' : GP {
        event occurrence receiveSAMLRequest;
        then event occurrence presentLoginForm;
        then event occurrence validateCredentials;
        then event occurrence sendSAMLResponse;
    }

    // Phase 1: Initial request & SSO redirect
    message 'Request protected resource'
        from 'User'.requestProtectedResource
        to 'GitLab'.receiveInitialRequest;

    message 'Redirect with SAML AuthnRequest'
        from 'GitLab'.redirectToIdP
        to 'User'.receiveRedirect;

    message 'Forward AuthnRequest'
        from 'User'.receiveRedirect
        to 'Google Workspace'.receiveSAMLRequest;

    // Phase 2: IdP authentication
    message 'Present login page'
        from 'Google Workspace'.presentLoginForm
        to 'User'.submitCredentials;

    message 'Submit credentials'
        from 'User'.submitCredentials
        to 'Google Workspace'.validateCredentials;

    // Phase 3: SP validation & session creation
    message 'POST SAMLResponse to ACS'
        from 'Google Workspace'.sendSAMLResponse
        to 'GitLab'.receiveSAMLResponse;

    message 'Create session & redirect to resource'
        from 'GitLab'.grantAccess
        to 'User'.receiveAccessToken;
}

package 'API Sequence Views' {
    private import StandardViewDefinitions::*;
    private import 'SAML Authentication Sequence'::*;

    view 'SAML Authentication Sequence' : SequenceView {
        expose 'SAML Authentication Sequence'::*;
    }
}
