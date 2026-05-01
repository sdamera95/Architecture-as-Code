"""Strip `doc /* ... */` blocks from a SysML v2 text file.

Produces a `<basename>_viz.sysml` sibling whose content is identical to the
source except that every `doc /* ... */` block (optionally with a version
identifier like `doc <'1.1'> /* ... */`) has been removed. This is the
companion to the Tom Sawyer renderer's inability to suppress the «doc»
compartment when filtering exposed elements (Sensmetry forum #447).

Canonical `.sysml` files remain fully documented for human readers and the
bridge pipeline. Only figure-rendering scripts should consume `_viz.sysml`
outputs.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOC_BLOCK = re.compile(
    r"\bdoc\b"
    r"(?:\s*<'[^']*'>)?"
    r"\s*"
    r"/\*.*?\*/",
    re.DOTALL,
)


def strip_docs(text: str) -> str:
    return DOC_BLOCK.sub("", text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a _viz.sysml sibling with all doc /* ... */ blocks stripped.",
    )
    parser.add_argument("source", type=Path, help="Input .sysml file")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing _viz.sysml output",
    )
    args = parser.parse_args()

    src: Path = args.source
    if not src.is_file():
        print(f"error: {src} is not a file", file=sys.stderr)
        return 2

    dst = src.with_name(f"{src.stem}_viz{src.suffix}")
    if dst.exists() and not args.force:
        print(
            f"error: {dst} exists; pass --force to overwrite",
            file=sys.stderr,
        )
        return 1

    stripped = strip_docs(src.read_text())
    dst.write_text(stripped)
    print(f"Wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
