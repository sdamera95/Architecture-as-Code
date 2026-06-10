"""
csv_to_latex.py — convert a CSV exported from Syside Grid Views to a LaTeX
tabular block suitable for inclusion in the manuscript.

Authored as part of Stage D of the v9 re-base. The Grid Views pane in
Syside Modeler 0.9.0 exports matrices to CSV; this utility wraps the CSV
in a publication-friendly `tabular` environment with proper escaping.

Usage:
    uv run python bridge/csv_to_latex.py input.csv                              # to stdout
    uv run python bridge/csv_to_latex.py input.csv -o output.tex                # to file
    uv run python bridge/csv_to_latex.py input.csv --standalone -o doc.tex      # wrap in document
    uv run python bridge/csv_to_latex.py input.csv --rotate-headers -o out.tex  # 90deg column headers
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# LaTeX special characters that need escaping in cell text
_LATEX_ESCAPE = str.maketrans({
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
})


def latex_escape(s: str) -> str:
    """Escape LaTeX special characters in a cell value."""
    return s.translate(_LATEX_ESCAPE)


def csv_to_tabular(rows: list[list[str]], rotate_headers: bool = False) -> str:
    """Render a list of rows as a `tabular` block. First row is the header."""
    if not rows:
        return "% empty matrix — no rows in CSV\n"

    header, *body = rows
    n_cols = len(header)
    # Use `l` for the first column (row labels) and `c` for the rest
    col_spec = "l" + "c" * (n_cols - 1)

    lines = [
        r"\begin{tabular}{" + col_spec + "}",
        r"\toprule",
    ]

    if rotate_headers:
        # Wrap each non-first header in \rotatebox{90}{...}
        # Requires `\usepackage{rotating}` (or `graphicx`) in the document preamble.
        first, *rest = header
        wrapped = [latex_escape(first)] + [
            r"\rotatebox{90}{" + latex_escape(h) + "}" for h in rest
        ]
        lines.append(" & ".join(wrapped) + r" \\")
    else:
        lines.append(" & ".join(latex_escape(c) for c in header) + r" \\")

    lines.append(r"\midrule")

    for row in body:
        # Pad / truncate to header width
        padded = (row + [""] * n_cols)[:n_cols]
        lines.append(" & ".join(latex_escape(c) for c in padded) + r" \\")

    lines.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(lines) + "\n"


def wrap_standalone(tabular: str, title: str = "", rotate_headers: bool = False) -> str:
    """Wrap a tabular block in a minimal LaTeX document for compile-check."""
    pkgs = [r"\usepackage{booktabs}"]
    if rotate_headers:
        pkgs.append(r"\usepackage{rotating}")
    return (
        "\\documentclass[border=4pt]{standalone}\n"
        + "\n".join(pkgs)
        + "\n\\begin{document}\n"
        + (f"% {title}\n" if title else "")
        + tabular
        + "\\end{document}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    parser.add_argument("csv_path", type=Path, help="Path to the CSV file")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output .tex path (default: stdout)")
    parser.add_argument("--standalone", action="store_true",
                        help="Wrap in a complete LaTeX document for compile-check")
    parser.add_argument("--rotate-headers", action="store_true",
                        help="Rotate column headers 90 degrees (useful for many narrow columns)")
    parser.add_argument("--title", default="",
                        help="Optional title comment when --standalone is set")

    args = parser.parse_args(argv)

    if not args.csv_path.exists():
        print(f"error: file not found: {args.csv_path}", file=sys.stderr)
        return 1

    with args.csv_path.open(newline="") as f:
        rows = list(csv.reader(f))

    tabular = csv_to_tabular(rows, rotate_headers=args.rotate_headers)
    output = (
        wrap_standalone(tabular, title=args.title, rotate_headers=args.rotate_headers)
        if args.standalone
        else tabular
    )

    if args.output:
        args.output.write_text(output)
        print(f"wrote {len(output)} chars to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
