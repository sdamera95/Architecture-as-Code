package Test06BlogReplica {
    doc /* Attempting to replicate the exact structure visible in the
           Syside 0.8.5 blog screenshot showing SAML authentication. */

    private import StandardViewDefinitions::*;

    item def SAMLRequest;
    item def SAMLResponse;
    item def AuthRequest;
    item def Credentials;
    item def Token;

    part def SAMLAuthenticationSequence {
        part user {
            event occurrence requestProtectedResource;
            then event occurrence receiveRedirect;
            then event occurrence submitCredentials;
            then event occurrence receiveToken;
        }
        part serviceProvider {
            event occurrence receiveRequest;
            then event occurrence sendRedirect;
            then event occurrence receiveSAMLResponse;
            then event occurrence grantAccess;
        }
        part identityProvider {
            event occurrence receiveSAMLRequest;
            then event occurrence presentLoginPage;
            then event occurrence validateCredentials;
            then event occurrence sendSAMLResponse;
        }

        message initialRequest from user.requestProtectedResource to serviceProvider.receiveRequest;
        message redirectToIdP from serviceProvider.sendRedirect to user.receiveRedirect;
        message samlRequest from user.receiveRedirect to identityProvider.receiveSAMLRequest;
        message loginPage from identityProvider.presentLoginPage to user.submitCredentials;
        message credentials from user.submitCredentials to identityProvider.validateCredentials;
        message samlResponse from identityProvider.sendSAMLResponse to serviceProvider.receiveSAMLResponse;
        message accessGranted from serviceProvider.grantAccess to user.receiveToken;
    }

    view samlSequence : SequenceView {
        expose Test06BlogReplica::SAMLAuthenticationSequence;
    }
}
