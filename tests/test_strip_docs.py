"""Round-trip tests for bridge/strip_docs.py.

Validates that stripping `doc /* ... */` blocks:
  1. Removes every doc block (zero matches in output)
  2. Preserves all structural element counts (part def, state def, action def,
     attribute def, item def, connection def, interface def, port def,
     requirement def, allocation def, verification def)
  3. Preserves line-comment content (`//`) and non-doc block comments

Follows the project's hand-rolled test convention (see test_bridge_pipeline.py):
manual `check(label, condition)` calls with passed/failed counters.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

from strip_docs import DOC_BLOCK, strip_docs

REPO = Path(__file__).parent.parent
CANONICAL_FILES = [
    REPO / "syside-demos" / "showcase_agr_full.sysml",
    REPO / "syside-demos" / "showcase_agr_nav2_full.sysml",
]

STRUCTURAL_KEYWORDS = [
    "part def",
    "state def",
    "action def",
    "attribute def",
    "item def",
    "connection def",
    "interface def",
    "port def",
    "requirement def",
    "allocation def",
    "verification def",
    "occurrence",
]

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}  {detail}")


def count_keyword(text: str, keyword: str) -> int:
    # Anchor to line start + optional whitespace so we only count structural
    # definitions, not prose mentions inside line comments or (unstripped) docs.
    pattern = (
        r"^\s*" + re.escape(keyword).replace(r"\ ", r"\s+") + r"\s+\w+"
    )
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def test_file(path: Path) -> None:
    print(f"\n=== {path.name} ===")
    src = path.read_text()
    stripped = strip_docs(src)

    src_docs = len(DOC_BLOCK.findall(src))
    dst_docs = len(DOC_BLOCK.findall(stripped))
    check(
        f"source has >0 doc blocks ({src_docs})",
        src_docs > 0,
        "expected rich model docs",
    )
    check(
        f"stripped output has 0 doc blocks (found {dst_docs})",
        dst_docs == 0,
    )

    for kw in STRUCTURAL_KEYWORDS:
        src_n = count_keyword(src, kw)
        dst_n = count_keyword(stripped, kw)
        check(
            f"'{kw}' count preserved ({src_n} -> {dst_n})",
            src_n == dst_n,
            f"src={src_n} dst={dst_n}",
        )

    check(
        "stripped output is smaller than source",
        len(stripped) < len(src),
        f"src={len(src)} dst={len(stripped)}",
    )


def test_synthetic_cases() -> None:
    print("\n=== synthetic cases ===")

    simple = 'doc /* hello */\npart p;'
    check("simple doc stripped", strip_docs(simple).strip() == "part p;")

    multiline = 'doc /* line1\nline2\nline3 */\npart p;'
    check(
        "multi-line doc stripped",
        strip_docs(multiline).strip() == "part p;",
    )

    versioned = "doc <'v1.2'> /* versioned doc */\npart p;"
    check(
        "versioned doc stripped",
        strip_docs(versioned).strip() == "part p;",
    )

    preserved = "// line comment\n/* non-doc block */\npart p;"
    check(
        "non-doc comments preserved",
        strip_docs(preserved) == preserved,
    )

    # 'doc' as substring of another identifier must not be stripped
    not_doc = "attribute document : String;"
    check(
        "'document' identifier not stripped",
        strip_docs(not_doc) == not_doc,
    )


def main() -> int:
    test_synthetic_cases()
    for path in CANONICAL_FILES:
        if path.exists():
            test_file(path)
        else:
            print(f"\n=== SKIP: {path.name} not found ===")

    print(f"\n{'='*50}\n{passed} passed, {failed} failed\n{'='*50}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
