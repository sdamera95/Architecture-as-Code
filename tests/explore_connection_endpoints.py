"""Deep exploration of connection endpoint resolution in Syside API.

The previous exploration showed that ConnectionUsage has:
  - owned_elements: Feature(pub), Feature(sub) for TopicConnection
  - attrs: .connector_ends, .end_features, .source, .targets, .related_features

Let's explore these to find how to resolve "connect lidar.sensorPub to nav.localCostmap.mapSub"
"""
import syside
from pathlib import Path

LIB_DIR = Path("projects/ros2-sysmlv2/ros2_sysmlv2")
LIB_FILES = sorted(str(f) for f in LIB_DIR.glob("*.sysml"))
CONSUMER = "tests/consumer_test_robot.sysml"
ALL_FILES = LIB_FILES + [CONSUMER]

model, diag = syside.load_model(ALL_FILES)
assert not diag.contains_errors()

part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}
test_robot = part_defs["TestRobot"]

for elem in test_robot.owned_elements.collect():
    if cu := elem.try_cast(syside.ConnectionUsage):
        print(f"\n{'='*60}")
        print(f"ConnectionUsage: {cu.name}")
        print(f"{'='*60}")

        # Try .connector_ends
        print("\n  .connector_ends:")
        try:
            for ce in cu.connector_ends.collect():
                print(f"    {type(ce).__name__}: {ce.name}")
                # Check chaining features
                if hasattr(ce, 'chaining_features'):
                    try:
                        for cf in ce.chaining_features.collect():
                            print(f"      chaining: {cf.name} ({type(cf).__name__})")
                    except:
                        pass
                # Check referenced_feature
                if hasattr(ce, 'referenced_feature'):
                    rf = ce.referenced_feature
                    if rf:
                        print(f"      referenced_feature: {rf.name} ({type(rf).__name__})")
        except Exception as e:
            print(f"    error: {e}")

        # Try .end_features
        print("\n  .end_features:")
        try:
            for ef in cu.end_features.collect():
                print(f"    {type(ef).__name__}: {ef.name}")
                # Walk its owned elements
                for sub in ef.owned_elements.collect():
                    sub_name = sub.name if sub.name else "(anon)"
                    print(f"      {type(sub).__name__}: {sub_name}")
                    # Check chaining
                    if hasattr(sub, 'chaining_features'):
                        try:
                            for cf in sub.chaining_features.collect():
                                print(f"        chaining: {cf.name} ({type(cf).__name__}, qn: {cf.qualified_name})")
                        except:
                            pass
        except Exception as e:
            print(f"    error: {e}")

        # Try .source_feature / .target_features
        print("\n  .source_feature:")
        try:
            sf = cu.source_feature
            if sf:
                print(f"    {type(sf).__name__}: {sf.name}")
        except Exception as e:
            print(f"    error: {e}")

        print("\n  .target_features:")
        try:
            for tf in cu.target_features.collect():
                print(f"    {type(tf).__name__}: {tf.name}")
        except Exception as e:
            print(f"    error: {e}")

        # Try .related_features
        print("\n  .related_features:")
        try:
            for rf in cu.related_features.collect():
                print(f"    {type(rf).__name__}: {rf.name}")
                if hasattr(rf, 'chaining_features'):
                    try:
                        chains = list(rf.chaining_features.collect())
                        if chains:
                            chain_str = " -> ".join(f"{c.name}({type(c).__name__})" for c in chains)
                            print(f"      chain: {chain_str}")
                    except:
                        pass
        except Exception as e:
            print(f"    error: {e}")

print("\nDone.")
