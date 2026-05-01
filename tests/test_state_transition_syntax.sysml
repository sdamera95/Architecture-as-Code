package TestStateTransitionSyntax {
    doc /* Minimal test file to discover which state machine transition
           syntaxes Syside 0.8.7 actually supports. Each state def below
           tests a different syntax variant. */

    private import ScalarValues::*;

    // ---- Item defs for triggers ----
    item def ConfigureEvent;
    item def ActivateEvent;
    item def DeactivateEvent;
    item def CleanupEvent;
    item def ShutdownEvent;

    // =================================================================
    // TEST 1: Basic transition keyword with source/target
    // Syntax: transition <name> first <source> then <target>;
    // =================================================================

    state def TestTransitionKeyword {
        state stateA;
        state stateB;
        state stateC;

        transition t1 first stateA then stateB;
        transition t2 first stateB then stateC;
        transition t3 first stateC then stateA;
    }

    // =================================================================
    // TEST 2: Transition with accept (trigger)
    // Syntax: transition first <source> accept <trigger> then <target>;
    // =================================================================

    state def TestTransitionWithAccept {
        state stateA;
        state stateB;
        state stateC;

        transition t1 first stateA accept ConfigureEvent then stateB;
        transition t2 first stateB accept ActivateEvent then stateC;
        transition t3 first stateC accept DeactivateEvent then stateA;
    }

    // =================================================================
    // TEST 3: Transition with guard (if)
    // Syntax: transition first <source> if <guard> then <target>;
    // =================================================================

    state def TestTransitionWithGuard {
        state stateA;
        state stateB;

        attribute ready : Boolean;

        transition t1 first stateA if ready then stateB;
    }

    // =================================================================
    // TEST 4: Transition with do action inside states
    // Syntax: state <name> { entry action <name>; do action <name>; }
    // =================================================================

    action def OnConfigure;
    action def OnActivate;

    state def TestStateWithActions {
        state configuring {
            entry action configure : OnConfigure;
        }
        state active {
            entry action activate : OnActivate;
        }

        transition t1 first configuring then active;
    }

    // =================================================================
    // TEST 5: Plain successions with transition keyword (no trigger)
    // Just to confirm the basic pattern still works
    // =================================================================

    state def TestPlainSuccession {
        state stateA;
        state stateB;
        state stateC;

        first stateA then stateB;
        first stateB then stateC;
    }
}
