"""Rasterize the composite SVG to PNG via subprocess to rsvg-convert."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
src = HERE / "mosaic_final.svg"
dst = HERE / "mosaic_final.png"

result = subprocess.run(
    ["rsvg-convert", "-w", "2000", str(src), "-o", str(dst)],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("STDERR:", result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
print(f"Wrote {dst}")
