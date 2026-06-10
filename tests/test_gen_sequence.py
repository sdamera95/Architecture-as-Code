"""Tests for tools/gen_sequence_diagram.py.

Asserts that message from/to extraction (via the canonical syside.pprint
printer) reproduces the model's semantics exactly, including right-to-left
response messages — the case the Tom Sawyer renderer randomized.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import syside  # noqa: E402
from gen_sequence_diagram import (  # noqa: E402
    chain_parts,
    collect_messages,
    collect_participants,
    emit_plantuml,
    find_element,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "seq_three_party.sysml"

passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


# ------------------------------------------------------------------
# chain parsing
# ------------------------------------------------------------------
check("plain chain", chain_parts("client.sendQuery") == ["client", "sendQuery"])
check("quoted chain", chain_parts("'Google Workspace'.receiveSAMLRequest")
      == ["Google Workspace", "receiveSAMLRequest"])

# ------------------------------------------------------------------
# end-to-end on the three-party fixture
# ------------------------------------------------------------------
model, _ = syside.load_model([str(FIXTURE)], warnings_as_errors=True)
container = find_element(model, "SeqTest::ThreePartyProtocol")
check("container found", container is not None)

messages = collect_messages(container)
check("4 messages extracted", len(messages) == 4, f"got {len(messages)}")

expected = [
    ("query", "client", "server"),
    ("dbQuery", "server", "database"),
    ("dbResult", "database", "server"),   # right-to-left response
    ("result", "server", "client"),       # right-to-left response
]
for (name, src, dst), msg in zip(expected, messages):
    check(f"message {name}: {src} -> {dst}",
          msg["name"] == name and msg["from_part"] == src and msg["to_part"] == dst,
          f"got {msg['from_part']} -> {msg['to_part']}")

participants = collect_participants(container)
check("3 participants in declaration order",
      [p[0] for p in participants] == ["client", "server", "database"])
check("participant types resolved",
      [p[1] for p in participants] == ["ClientNode", "ServerNode", "DatabaseNode"])

puml = emit_plantuml(participants, messages, title="ThreePartyProtocol")
check("puml has both R-to-L arrows",
      "P2 -> P1 : dbResult" in puml and "P1 -> P0 : result" in puml)
check("puml well-formed", puml.startswith("@startuml") and puml.rstrip().endswith("@enduml"))

print()
print("=" * 60)
print(f"  {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
