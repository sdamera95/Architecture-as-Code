"""Compose the four-pillar MBSE architecture figure (direct XML approach).

We embed the Tom Sawyer panel SVGs as nested <svg> elements with explicit
x/y/width/height (SVG 1.1 supports this for absolute positioning), then
overlay our hand-built panel and cross-pillar arrows.
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
PILLAR1 = HERE / "diagram-prototype_safetyTopology.svg"
PILLAR2 = HERE.parent / "prototype_mosaic" / "diagram-prototype_safetyStateMachine.svg"
PILLAR3 = HERE.parent / "prototype_mosaic" / "diagram-prototype_safetyRequirements.svg"

CANVAS_W = 1600
CANVAS_H = 1300

# Each entry: panel id, source SVG, target_x, target_y, target_w, target_h, label
PANELS = [
    ("p1", PILLAR1, 30, 60, 760, 700, "1. Structure"),
    ("p2", PILLAR2, 30, 790, 540, 480, "2. Behavior"),
    ("p3", PILLAR3, 1010, 60, 540, 380, "3. Requirements"),
]
P4 = (1010, 480, 540, 320, "4. Constraints")


def get_native_dims(svg_text):
    """Extract width and height attributes from SVG root element."""
    w = re.search(r'<svg[^>]*\swidth="([\d.]+)(?:px)?"', svg_text).group(1)
    h = re.search(r'<svg[^>]*\sheight="([\d.]+)(?:px)?"', svg_text).group(1)
    return float(w), float(h)


def build_nested_svg(svg_text, x, y, target_w, target_h):
    """Wrap an existing SVG document inside a positioned <svg> element.

    Uses SVG nesting + viewBox to scale-and-position. The inner content's
    coordinate system is preserved via the original viewBox, so all
    transforms inside the source SVG continue to work."""
    src_w, src_h = get_native_dims(svg_text)
    # Pick the uniform scale that fits inside (target_w, target_h)
    scale = min(target_w / src_w, target_h / src_h)
    eff_w = src_w * scale
    eff_h = src_h * scale
    # Strip the XML/DOCTYPE prologue from the source SVG; keep only the <svg>...</svg>
    inner = re.sub(r"^<\?xml[^>]*\?>\s*", "", svg_text)
    inner = re.sub(r"<!DOCTYPE[^>]*>\s*", "", inner)
    # Modify the root <svg> tag: add x/y/width/height that position it on the parent canvas
    inner = re.sub(
        r'<svg([^>]*?)\swidth="[\d.]+(?:px)?"',
        rf'<svg\1 x="{x}" y="{y}" width="{eff_w}"',
        inner, count=1
    )
    inner = re.sub(
        r'(<svg[^>]*?)\sheight="[\d.]+(?:px)?"',
        rf'\1 height="{eff_h}"',
        inner, count=1
    )
    # Add viewBox if not present so the inner content scales correctly
    if "viewBox" not in inner.split(">", 1)[0]:
        inner = re.sub(
            r'<svg([^>]*?)>',
            rf'<svg\1 viewBox="0 0 {src_w} {src_h}" preserveAspectRatio="xMidYMid meet">',
            inner, count=1
        )
    return inner, eff_w, eff_h


def build_constraints_panel(x, y, w, h):
    """Hand-built Pillar 4 panel. All coords absolute on the parent canvas."""
    # Internal layout offsets relative to (x, y)
    s = lambda dx, dy: (x + dx, y + dy)
    rb = (x + 20, y + 80, 240, 100)   # reqdef box
    cm = (x + 320, y + 80, 200, 100)  # conformance monitor box
    return f'''
    <g id="constraints_panel" font-family="sans-serif">
        <rect x="{x}" y="{y}" width="{w}" height="{h}"
              fill="#fafafa" stroke="#cccccc" stroke-width="1.5" rx="4"/>
        <text x="{x+20}" y="{y+30}" font-size="14" font-weight="bold" fill="#222">Runtime Constraint Predicates</text>
        <text x="{x+20}" y="{y+50}" font-size="11" font-style="italic" fill="#555">Auto-generated from <tspan font-family="monospace" font-style="normal">require constraint</tspan> blocks</text>

        <!-- Source: requirement def excerpt -->
        <rect x="{rb[0]}" y="{rb[1]}" width="{rb[2]}" height="{rb[3]}" fill="#fff7e6" stroke="#d99000" rx="3"/>
        <text x="{rb[0]+10}" y="{rb[1]+18}" font-size="10" font-weight="bold" fill="#222">&#171;requirement def&#187; EmergencyStopReq</text>
        <text x="{rb[0]+10}" y="{rb[1]+36}" font-family="monospace" font-size="9.5" fill="#222">attribute maxResponseMs : Real;</text>
        <text x="{rb[0]+10}" y="{rb[1]+53}" font-family="monospace" font-size="9.5" fill="#222">require constraint {{</text>
        <text x="{rb[0]+10}" y="{rb[1]+68}" font-family="monospace" font-size="9.5" fill="#222">  responseTimeMs &lt;= maxResponseMs</text>
        <text x="{rb[0]+10}" y="{rb[1]+83}" font-family="monospace" font-size="9.5" fill="#222">}}</text>

        <!-- Compile arrow -->
        <path d="M {rb[0]+rb[2]+10} {rb[1]+50} L {cm[0]-10} {cm[1]+50}" stroke="#444" stroke-width="2" fill="none" marker-end="url(#arrow_compile)"/>
        <text x="{rb[0]+rb[2]+12}" y="{rb[1]+42}" font-size="9" font-style="italic" fill="#444">compile</text>

        <!-- Target: conformance monitor code -->
        <rect x="{cm[0]}" y="{cm[1]}" width="{cm[2]}" height="{cm[3]}" fill="#e8f4ff" stroke="#0070c0" rx="3"/>
        <text x="{cm[0]+10}" y="{cm[1]+18}" font-size="10" font-weight="bold" fill="#222">conformance_monitor.py</text>
        <text x="{cm[0]+10}" y="{cm[1]+36}" font-family="monospace" font-size="9.5" fill="#222">if response_ms &gt; spec.maxResponseMs:</text>
        <text x="{cm[0]+10}" y="{cm[1]+53}" font-family="monospace" font-size="9.5" fill="#222">  diag.level = ERROR</text>
        <text x="{cm[0]+10}" y="{cm[1]+68}" font-family="monospace" font-size="9.5" fill="#222">  diag.message = (</text>
        <text x="{cm[0]+10}" y="{cm[1]+83}" font-family="monospace" font-size="9.5" fill="#222">    f"e-stop {{response_ms}}ms")</text>

        <!-- Caption -->
        <text x="{x+20}" y="{y+210}" font-size="10" fill="#444">
            <tspan x="{x+20}" dy="0">Approach A: predicate text is extracted at code-generation time</tspan>
            <tspan x="{x+20}" dy="14">and embedded in the runtime monitor as a Python lambda.</tspan>
            <tspan x="{x+20}" dy="14">Drift between spec and runtime is detected within one cycle.</tspan>
        </text>

        <!-- Digital thread strip -->
        <rect x="{x+20}" y="{y+270}" width="{w-40}" height="36" fill="#f0f7ee" stroke="#5a8a3a" rx="3"/>
        <text x="{x+32}" y="{y+293}" font-size="11" font-weight="bold" fill="#2d5016">Digital thread:</text>
        <text x="{x+118}" y="{y+293}" font-size="10" fill="#2d5016">spec &#8594; generated code &#8594; runtime check &#8594; /conformance_report (DiagnosticArray @ 0.2 Hz)</text>
    </g>
    '''


def build_arrows():
    """Cross-pillar arrows. Anchors extracted from inner SVG text/rect coords
    then transformed by panel scale + offset onto the canvas."""
    # ---- P1 anchors (Structure topology) ----
    # Source SVG: 692x834. Panel target: P1 at (30,60), W=760, H=700.
    # Scale = min(760/692, 700/834) = 0.839
    p1_x, p1_y, p1_scale = 30, 60, min(760/692, 700/834)
    def p1(sx, sy): return (p1_x + sx * p1_scale, p1_y + sy * p1_scale)
    # CollisionGuard part box in source: x=365-596, y=482-660 (from SVG line 380, 384).
    # Right-middle edge = (596, 571). Right edge anchor for satisfy arrows (going right).
    cg_right = p1(596, 540)            # right side, just above mid
    cg_right_lo = p1(596, 570)         # right side, just below mid (for second satisfy)
    cg_bottom_left = p1(365, 660)      # bottom-left corner — natural exit for triggers (going down/left)

    # ---- P2 anchors (State Machine) ----
    # Source: 604x545. Panel: P2 at (30,790), W=540, H=480.
    p2_x, p2_y, p2_scale = 30, 790, min(540/604, 480/545)
    def p2(sx, sy): return (p2_x + sx * p2_scale, p2_y + sy * p2_scale)
    # safetyPort port circle: rect at (510, 172), 12×12, center ≈ (516, 178). Right edge of OperationalModes box.
    safety_port = p2(516, 178)

    # ---- P3 anchors (Requirements) ----
    # Source: 477x356. Panel: P3 at (1010,60), W=540, H=380.
    p3_x, p3_y, p3_scale = 1010, 60, min(540/477, 380/356)
    def p3(sx, sy): return (p3_x + sx * p3_scale, p3_y + sy * p3_scale)
    # Source SVG inspection: requirement def boxes are stacked vertically.
    # EmergencyStopReq title at top (~y=11), CollisionAvoidanceReq below (~y=170 source).
    # Left edges of the requirement boxes are at source x ≈ 20.
    estop_left = p3(20, 50)            # left edge, EmergencyStopReq (top)
    coll_left = p3(20, 200)            # left edge, CollisionAvoidanceReq (lower)
    estop_bottom = p3(150, 130)        # bottom-middle of EmergencyStopReq, source for «frame»

    # ---- P4 anchor (Constraints panel) ----
    # Target the top-edge of the «requirement def» EmergencyStopReq subbox
    # (which is at P4[0]+20 .. P4[0]+260 horizontally, P4[1]+80 vertically).
    con_top = (P4[0] + 140, P4[1] + 80)

    arrows = '<g font-family="sans-serif" font-size="13" font-weight="bold">'

    # 1. Satisfy: collisionGuard right edge -> EmergencyStopReq left edge (curved blue)
    arrows += (
        f'<path d="M {cg_right[0]} {cg_right[1]} '
        f'C {(cg_right[0]+estop_left[0])/2} {cg_right[1]-30}, '
        f'{(cg_right[0]+estop_left[0])/2} {estop_left[1]}, '
        f'{estop_left[0]-3} {estop_left[1]}" '
        f'stroke="#0070c0" stroke-width="2.5" fill="none" '
        f'marker-end="url(#arrow_satisfy)"/>'
    )

    # 2. Satisfy: collisionGuard right edge (lower) -> CollisionAvoidanceReq (curved blue)
    arrows += (
        f'<path d="M {cg_right_lo[0]} {cg_right_lo[1]} '
        f'C {(cg_right_lo[0]+coll_left[0])/2} {cg_right_lo[1]+10}, '
        f'{(cg_right_lo[0]+coll_left[0])/2 - 50} {coll_left[1]+10}, '
        f'{coll_left[0]-3} {coll_left[1]}" '
        f'stroke="#0070c0" stroke-width="2.5" fill="none" '
        f'marker-end="url(#arrow_satisfy)"/>'
    )
    # Single shared label for both satisfy arrows
    arrows += (f'<text x="{(cg_right[0]+estop_left[0])/2 - 30}" '
               f'y="{cg_right[1] - 35}" fill="#0070c0">«satisfy»</text>')

    # 3. Triggers: collisionGuard bottom-left -> safetyPort (yellow dashed, L-shaped)
    # Route: down from cg_bottom_left, then right-and-down to safetyPort right side.
    midx = max(cg_bottom_left[0] + 80, safety_port[0] + 60)
    midy = (cg_bottom_left[1] + safety_port[1]) / 2 + 20
    arrows += (
        f'<path d="M {cg_bottom_left[0]} {cg_bottom_left[1]} '
        f'L {cg_bottom_left[0]} {midy} '
        f'L {midx} {midy} '
        f'L {midx} {safety_port[1]} '
        f'L {safety_port[0]+12} {safety_port[1]}" '
        f'stroke="#bf9000" stroke-width="2.5" fill="none" '
        f'stroke-dasharray="6,4" '
        f'marker-end="url(#arrow_triggers)"/>'
    )
    arrows += (f'<text x="{midx + 8}" y="{midy - 5}" fill="#bf9000">«triggers»</text>')

    # 4. Frame: EmergencyStopReq bottom -> top of «requirement def» subbox in Constraints
    # Route around the right side of P3 to avoid crossing other content.
    midy = (estop_bottom[1] + con_top[1]) / 2
    arrows += (
        f'<path d="M {estop_bottom[0]} {estop_bottom[1]} '
        f'L {estop_bottom[0]} {midy} '
        f'L {con_top[0]} {midy} '
        f'L {con_top[0]} {con_top[1]-3}" '
        f'stroke="#385723" stroke-width="2.5" fill="none" '
        f'marker-end="url(#arrow_frame)"/>'
    )
    # Label sits in the gap between P3 and P4, to the right of the vertical segment
    arrows += (f'<text x="{con_top[0]+8}" '
               f'y="{midy - 6}" '
               f'fill="#385723">«frame»</text>')

    arrows += "</g>"
    return arrows


def build_titles_and_borders(panels):
    """Titles above each panel and a thin border around each."""
    out = '<g font-family="sans-serif">'
    for x, y, w, h, label in panels:
        out += (f'<rect x="{x-8}" y="{y-30}" width="{w+16}" height="{h+38}" '
                f'fill="none" stroke="#dddddd" stroke-width="1" rx="3"/>')
        out += (f'<text x="{x}" y="{y-10}" font-size="22" font-weight="bold" '
                f'fill="#c00000">{label}</text>')
    out += "</g>"
    return out


def build_legend():
    y = 1280
    return f'''
    <g font-family="sans-serif" font-size="13">
        <text x="30" y="{y}" font-weight="bold" fill="#222">Cross-pillar bindings:</text>
        <line x1="200" y1="{y-4}" x2="240" y2="{y-4}" stroke="#0070c0" stroke-width="2.5" marker-end="url(#arrow_satisfy)"/>
        <text x="246" y="{y}" fill="#0070c0">«satisfy» (part fulfills requirement)</text>
        <line x1="560" y1="{y-4}" x2="600" y2="{y-4}" stroke="#bf9000" stroke-width="2.5" stroke-dasharray="6,4" marker-end="url(#arrow_triggers)"/>
        <text x="606" y="{y}" fill="#bf9000">«triggers» (event drives state transition)</text>
        <line x1="950" y1="{y-4}" x2="990" y2="{y-4}" stroke="#385723" stroke-width="2.5" marker-end="url(#arrow_frame)"/>
        <text x="996" y="{y}" fill="#385723">«frame» (constraint compiled to runtime check)</text>
    </g>
    '''


def main():
    parts = []
    parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">
<defs>
    <marker id="arrow_satisfy"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#0070c0"/></marker>
    <marker id="arrow_exhibit"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#ed7d31"/></marker>
    <marker id="arrow_triggers" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#bf9000"/></marker>
    <marker id="arrow_frame"    viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#385723"/></marker>
    <marker id="arrow_compile"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#444"/></marker>
</defs>
<rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" fill="white"/>
''')

    placed = []
    for pid, src, x, y, w, h, label in PANELS:
        svg_text = src.read_text()
        nested, eff_w, eff_h = build_nested_svg(svg_text, x, y, w, h)
        parts.append(nested)
        placed.append((x, y, eff_w, eff_h, label))

    parts.append(build_constraints_panel(P4[0], P4[1], P4[2], P4[3]))
    placed.append((P4[0], P4[1], P4[2], P4[3], P4[4]))

    parts.append(build_titles_and_borders(placed))
    parts.append(build_arrows())
    parts.append(build_legend())
    parts.append("</svg>\n")

    out = HERE / "mosaic_final.svg"
    out.write_text("\n".join(parts))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
