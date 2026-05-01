"""Test which state machine transition syntaxes Syside 0.8.7 supports.

Loads the test_state_transition_syntax.sysml file and reports:
  - Which state defs parse without errors
  - What transition-related elements are accessible via the API
  - What types/classes are available for state machine constructs
"""
import syside
import sys

TEST_FILE = "tests/test_state_transition_syntax.sysml"

print("=" * 60)
print("State Machine Transition Syntax Test")
print(f"Syside version: {syside.__version__}")
print("=" * 60)

# Load the test file
model, diagnostics = syside.load_model([TEST_FILE])

# Check for parse errors
has_errors = diagnostics.contains_errors()
print(f"\nOverall parse result: {'ERRORS' if has_errors else 'CLEAN'}")

# Print diagnostics if any
if has_errors:
    print("\nDiagnostics present (check Syside Editor for details)")

# Enumerate all state defs found
print("\n" + "-" * 60)
print("State definitions found:")
print("-" * 60)

for sd in model.nodes(syside.StateDefinition):
    print(f"\n  state def {sd.name}")

    # Walk owned elements to find transitions, states, etc.
    for elem in sd.owned_elements.collect():
        elem_type = type(elem).__name__
        name = elem.name if elem.name else "(anonymous)"

        # Check for various transition-related types
        if hasattr(syside, 'TransitionUsage'):
            if trans := elem.try_cast(syside.TransitionUsage):
                print(f"    TransitionUsage: {name}")
                # Try to get source/target
                for sub in trans.owned_elements.collect():
                    sub_type = type(sub).__name__
                    sub_name = sub.name if sub.name else "(anon)"
                    print(f"      -> {sub_type}: {sub_name}")
                continue

        if hasattr(syside, 'StateUsage'):
            if state := elem.try_cast(syside.StateUsage):
                print(f"    StateUsage: {name}")
                # Check for entry/do/exit actions
                for sub in state.owned_elements.collect():
                    sub_type = type(sub).__name__
                    sub_name = sub.name if sub.name else "(anon)"
                    print(f"      -> {sub_type}: {sub_name}")
                continue

        if hasattr(syside, 'SuccessionAsUsage'):
            if succ := elem.try_cast(syside.SuccessionAsUsage):
                print(f"    SuccessionAsUsage: {name}")
                continue

        # Generic fallback
        print(f"    {elem_type}: {name}")

# Also check what transition-related types exist in syside
print("\n" + "-" * 60)
print("Available transition-related types in syside module:")
print("-" * 60)

transition_types = [
    'TransitionUsage', 'TransitionDefinition',
    'TransitionFeatureMembership',
    'SuccessionAsUsage', 'Succession',
    'SuccessionFlowConnectionUsage',
    'AcceptActionUsage', 'TriggerInvocationExpression',
    'GuardExpression', 'EffectBehaviorUsage',
    'StateUsage', 'StateDefinition',
    'StateSubactionMembership',
    'EntryTransitionUsage', 'ExitTransitionUsage',
    'TransitionFeatureKind',
]

for tname in sorted(transition_types):
    exists = hasattr(syside, tname)
    print(f"  syside.{tname}: {'EXISTS' if exists else 'not found'}")

# Also do a broader search for anything with "Transition" or "State" in the name
print("\n" + "-" * 60)
print("All syside attributes containing 'Transition' or 'Succession':")
print("-" * 60)
for attr in sorted(dir(syside)):
    if 'Transition' in attr or 'Succession' in attr or 'Accept' in attr:
        print(f"  syside.{attr}")

print("\nDone.")
