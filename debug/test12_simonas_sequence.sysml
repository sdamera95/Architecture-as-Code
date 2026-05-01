// Experiment 12: Simonas' exact sequence diagram pattern from forum #447
// Key differences from our current approach:
//   1. occurrence def (definition, not usage)
//   2. then message (temporal ordering between messages)
//   3. typed parts (: Lamp, : User)
//   4. untyped messages (no : Msg)

part def Lamp;
part def User;

occurrence def TurnLampOnSequence {
    part lamp : Lamp {
        event occurrence commandReceived;
        then event occurrence lampTurnedOn;
    }

    part user : User {
        event occurrence pressesButton;
        then event occurrence observesLampOn;
    }

    message from user.pressesButton to lamp.commandReceived;
    then message from lamp.lampTurnedOn to user.observesLampOn;
}
