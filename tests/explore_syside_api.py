"""Explore Syside API for connection endpoints, port items, and attribute values.

This script loads consumer_test_robot.sysml with the library and investigates:
1. How ConnectionUsage exposes source/target endpoints
2. How PortUsage exposes its typed items (msg, goal, feedback, result)
3. How :>> redefinitions are traversed for attribute values
4. How to classify ports against port defs (TopicPublisher, etc.)
"""
import syside
from pathlib import Path

LIB_DIR = Path("projects/ros2-sysmlv2/ros2_sysmlv2")
LIB_FILES = sorted(str(f) for f in LIB_DIR.glob("*.sysml"))
CONSUMER = "tests/consumer_test_robot.sysml"
ALL_FILES = LIB_FILES + [CONSUMER]

model, diag = syside.load_model(ALL_FILES)
assert not diag.contains_errors(), "Parse errors!"

# Build lookups
part_defs = {n.name: n for n in model.nodes(syside.PartDefinition)}
port_defs = {n.name: n for n in model.nodes(syside.PortDefinition)}
node_def = part_defs["Node"]
lcn_def = part_defs["LifecycleNode"]

print("=" * 60)
print("1. CONNECTION ENDPOINT EXPLORATION")
print("=" * 60)

# Find TestRobot and its connections
test_robot = part_defs["TestRobot"]
for elem in test_robot.owned_elements.collect():
    if cu := elem.try_cast(syside.ConnectionUsage):
        print(f"\nConnectionUsage: {cu.name}")
        print(f"  qualified_name: {cu.qualified_name}")

        # Check connection type
        conn_types = list(cu.types.collect())
        for ct in conn_types:
            print(f"  type: {ct.name} ({type(ct).__name__})")

        # Walk ALL owned elements
        print(f"  owned_elements:")
        for sub in cu.owned_elements.collect():
            sub_type = type(sub).__name__
            sub_name = sub.name if sub.name else "(anon)"
            print(f"    {sub_type}: {sub_name}")

            # Go one level deeper
            for sub2 in sub.owned_elements.collect():
                s2_type = type(sub2).__name__
                s2_name = sub2.name if sub2.name else "(anon)"
                print(f"      {s2_type}: {s2_name}")
                # Check for feature_value_expression
                if hasattr(sub2, 'feature_value_expression'):
                    expr = sub2.feature_value_expression
                    if expr:
                        print(f"        has value expression")

        # Check for source/target/end related attrs
        print(f"  available attrs (connection-related):")
        for attr in sorted(dir(cu)):
            if any(k in attr.lower() for k in
                   ['source', 'target', 'end', 'connect', 'relat', 'assoc', 'feat']):
                if not attr.startswith('_'):
                    print(f"    .{attr}")

print("\n" + "=" * 60)
print("2. PORT USAGE EXPLORATION (MyLidarDriver.sensorPub)")
print("=" * 60)

lidar_def = part_defs["MyLidarDriver"]
for elem in lidar_def.owned_elements.collect():
    if pu := elem.try_cast(syside.PortUsage):
        print(f"\nPortUsage: {pu.name}")

        # Check port type
        port_types = list(pu.types.collect())
        for pt in port_types:
            print(f"  type: {pt.name} ({type(pt).__name__})")

        # Walk owned elements (should include :>> overrides and item usages)
        print(f"  owned_elements:")
        for sub in pu.owned_elements.collect():
            sub_type = type(sub).__name__
            sub_name = sub.name if sub.name else "(anon)"
            print(f"    {sub_type}: {sub_name}")

            # Check for value
            if hasattr(sub, 'feature_value_expression'):
                expr = sub.feature_value_expression
                if expr:
                    try:
                        result, report = syside.Compiler().evaluate(expr)
                        if not report.fatal:
                            print(f"      value = {result}")
                    except Exception as e:
                        print(f"      eval error: {e}")

            # Check for item usages (message types)
            if sub.try_cast(syside.ItemUsage):
                item_types = list(sub.types.collect())
                for it in item_types:
                    print(f"      item type: {it.name} (qn: {it.qualified_name})")

print("\n" + "=" * 60)
print("3. ATTRIBUTE VALUE EXTRACTION (MyLidarDriver :>> attrs)")
print("=" * 60)

for elem in lidar_def.owned_elements.collect():
    elem_type = type(elem).__name__
    elem_name = elem.name if elem.name else "(anon)"

    # Check both AttributeUsage and ReferenceUsage
    if au := elem.try_cast(syside.AttributeUsage):
        print(f"\n  AttributeUsage: {au.name}")
        if au.feature_value_expression:
            try:
                result, report = syside.Compiler().evaluate(au.feature_value_expression)
                if not report.fatal:
                    print(f"    value = {result}")
            except:
                print(f"    (eval failed)")

    elif ru := elem.try_cast(syside.ReferenceUsage):
        print(f"\n  ReferenceUsage: {ru.name}")
        if ru.feature_value_expression:
            try:
                result, report = syside.Compiler().evaluate(ru.feature_value_expression)
                if not report.fatal:
                    print(f"    value = {result}")
            except:
                print(f"    (eval failed)")

print("\n" + "=" * 60)
print("4. PORT DEF CLASSIFICATION")
print("=" * 60)

print(f"\nAvailable port defs: {list(port_defs.keys())}")

# For MyLidarDriver.sensorPub, check which port def it matches
for elem in lidar_def.owned_elements.collect():
    if pu := elem.try_cast(syside.PortUsage):
        port_types = list(pu.types.collect())
        for pt in port_types:
            for pd_name, pd in port_defs.items():
                if pt.specializes(pd) or pt == pd:
                    print(f"  {pu.name} matches port def: {pd_name}")
                    break
            else:
                print(f"  {pu.name} type {pt.name} — checking by name")
                if pt.name in port_defs:
                    print(f"    -> matched by name: {pt.name}")

print("\nDone.")
