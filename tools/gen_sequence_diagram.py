#!/usr/bin/env python3
"""Generate a PlantUML sequence diagram from a SysML v2 occurrence's messages.

The in-house Syside renderer (0.10.x) does not implement sequence-diagram
layout, and the Tom Sawyer renderer (interactive Modeler) has a confirmed
random arrow-direction bug. This generator sidesteps both: message from/to
semantics are extracted from the model itself via the Automator API, so the
arrows are correct by construction.

Extraction uses `syside.pprint(flow)` — Sensmetry's canonical textual printer
(the 0.10.0 changelog fixed `from` keyword emission for exactly this form) —
and parses `message <name> from <chain> to <chain>;`. Message order follows
document order, which matches the `then message` succession ordering in all
project models.

Usage:
    uv run python tools/gen_sequence_diagram.py MODEL.sysml [MORE.sysml ...] \
        --element 'Package::OccurrenceName' -o out.puml
"""
import argparse
import re
import sys
from pathlib import Path

import syside

MESSAGE_RE = re.compile(r"\bfrom\s+(.+?)\s+to\s+(.+?)\s*;", re.DOTALL)


def chain_parts(chain: str) -> list[str]:
    """Split a printed feature chain into segments, respecting 'quoted names'."""
    return [seg.strip().strip("'") for seg in re.findall(r"'[^']*'|[^.\s]+", chain)]


def find_element(model, qualified_name: str):
    for cls in (syside.OccurrenceDefinition, syside.OccurrenceUsage, syside.Package):
        for el in model.nodes(cls):
            if str(el.qualified_name) == qualified_name or el.name == qualified_name:
                return el
    return None


def collect_messages(container) -> list[dict]:
    """All FlowUsages under `container`, in document order, parsed via the printer."""
    messages = []
    for owned in container.owned_elements.collect():
        fu = owned.try_cast(syside.FlowUsage)
        if fu is None:
            continue
        text = syside.pprint(fu)
        m = MESSAGE_RE.search(text)
        if not m:
            continue
        src = chain_parts(m.group(1))
        dst = chain_parts(m.group(2))
        messages.append({
            "name": fu.name or "",
            "from_part": src[0],
            "from_event": src[-1] if len(src) > 1 else "",
            "to_part": dst[0],
            "to_event": dst[-1] if len(dst) > 1 else "",
        })
    return messages


def collect_participants(container) -> list[tuple[str, str]]:
    """(name, type) of owned part usages, in declaration order."""
    parts = []
    for owned in container.owned_elements.collect():
        pu = owned.try_cast(syside.PartUsage)
        if pu is None or pu.name is None:
            continue
        types = list(pu.types.collect())
        parts.append((pu.name, types[0].name if types else ""))
    return parts


def emit_plantuml(participants, messages, title="") -> str:
    lines = ["@startuml"]
    if title:
        lines.append(f"title {title}")
    declared = set()
    alias = {}
    for i, (name, type_name) in enumerate(participants):
        alias[name] = f"P{i}"
        label = f"{name} : {type_name}" if type_name else name
        lines.append(f'participant "{label}" as P{i}')
        declared.add(name)
    # Participants referenced by messages but not declared as parts (defensive)
    for msg in messages:
        for p in (msg["from_part"], msg["to_part"]):
            if p not in declared:
                alias[p] = f"P{len(alias)}"
                lines.append(f'participant "{p}" as {alias[p]}')
                declared.add(p)
    for msg in messages:
        label = msg["name"] or f'{msg["from_event"]} -> {msg["to_event"]}'
        lines.append(f'{alias[msg["from_part"]]} -> {alias[msg["to_part"]]} : {label}')
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("models", nargs="+", help="SysML v2 files to load")
    parser.add_argument("--element", required=True,
                        help="Qualified name of the occurrence/package owning the messages")
    parser.add_argument("-o", "--output", required=True, help="Output .puml path")
    args = parser.parse_args()

    model, _ = syside.load_model(args.models, warnings_as_errors=True)
    container = find_element(model, args.element)
    if container is None:
        print(f"ERROR: element '{args.element}' not found", file=sys.stderr)
        sys.exit(1)

    messages = collect_messages(container)
    if not messages:
        print(f"ERROR: no messages found under '{args.element}'", file=sys.stderr)
        sys.exit(1)
    participants = collect_participants(container)

    puml = emit_plantuml(participants, messages, title=container.name or "")
    Path(args.output).write_text(puml)
    print(f"{args.output}: {len(participants)} participants, {len(messages)} messages")


if __name__ == "__main__":
    main()
