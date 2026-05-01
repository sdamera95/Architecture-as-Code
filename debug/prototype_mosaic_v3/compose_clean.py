"""Hand-built four-pillar SysML v2 architecture mosaic.

The Tom Sawyer auto-renderer ignores filter directives at the compartment level,
so we lose control over visual density. This composition replaces all 4 panels
with hand-drawn SVG that mirrors SysML v2 notation conventions: «part def»,
«part», «state def», «state», «requirement def», «constraint def» stereotypes
with consistent typography. All panel content represents real elements present
in the showcase_agr_full.sysml model.
"""
from pathlib import Path

HERE = Path(__file__).parent
OUT_SVG = HERE / "mosaic_clean.svg"

CANVAS_W = 1700
CANVAS_H = 1180

# ---- Color palette (SysML v2 conventional) ----
PART_HEAD = "#d4e3f5"      # light blue («part def», «part»)
PART_BODY = "#ffffff"
PART_STROKE = "#5b8aab"
STATE_HEAD = "#f3e3e2"     # light pink («state def», «state»)
STATE_BODY = "#ffffff"
STATE_STROKE = "#ce716e"
REQ_HEAD = "#e9e3f4"       # light purple («requirement def»)
REQ_BODY = "#ffffff"
REQ_STROKE = "#7a6aab"
CON_HEAD = "#fff2cd"       # light yellow («constraint def»)
CON_BODY = "#ffffff"
CON_STROKE = "#cea05a"
TEXT_DARK = "#222222"
TEXT_MUTED = "#555555"

# Arrow colors
SATISFY_C = "#0070c0"
TRIGGER_C = "#bf9000"
FRAME_C = "#385723"


def part_box(x, y, w, h, name, body=PART_BODY, head=PART_HEAD, stroke=PART_STROKE,
             stereotype="«part»", header_h=44, ports=None, body_lines=None):
    """Render a SysML part box with stereotype header and optional ports/body."""
    out = []
    # Outer rounded rect
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
               f'fill="{body}" stroke="{stroke}" stroke-width="1.5" rx="6"/>')
    # Header band
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{header_h}" '
               f'fill="{head}" stroke="{stroke}" stroke-width="1.5" rx="6"/>')
    # Mask the bottom corners of header
    out.append(f'<rect x="{x}" y="{y+header_h-8}" width="{w}" height="8" '
               f'fill="{head}" stroke="none"/>')
    out.append(f'<line x1="{x}" y1="{y+header_h}" x2="{x+w}" y2="{y+header_h}" '
               f'stroke="{stroke}" stroke-width="1.5"/>')
    # Stereotype + name (centered)
    cx = x + w / 2
    out.append(f'<text x="{cx}" y="{y+18}" font-family="sans-serif" font-size="11" '
               f'font-style="italic" fill="{TEXT_MUTED}" text-anchor="middle">{stereotype}</text>')
    out.append(f'<text x="{cx}" y="{y+35}" font-family="sans-serif" font-size="13" '
               f'font-weight="bold" fill="{TEXT_DARK}" text-anchor="middle">{name}</text>')
    # Body text lines
    if body_lines:
        for i, line in enumerate(body_lines):
            out.append(f'<text x="{x+12}" y="{y+header_h+22+i*16}" font-family="sans-serif" '
                       f'font-size="11" fill="{TEXT_DARK}">{line}</text>')
    # Ports as small squares with label outside
    if ports:
        for px, py, plabel, side in ports:
            # px, py are relative to box top-left
            ax = x + px
            ay = y + py
            out.append(f'<rect x="{ax-6}" y="{ay-6}" width="12" height="12" '
                       f'fill="white" stroke="{stroke}" stroke-width="1.2"/>')
            # Label position based on side
            if side == "L":
                out.append(f'<text x="{ax-12}" y="{ay+4}" font-family="sans-serif" '
                           f'font-size="10" fill="{TEXT_DARK}" text-anchor="end">{plabel}</text>')
            elif side == "R":
                out.append(f'<text x="{ax+12}" y="{ay+4}" font-family="sans-serif" '
                           f'font-size="10" fill="{TEXT_DARK}" text-anchor="start">{plabel}</text>')
            elif side == "T":
                out.append(f'<text x="{ax}" y="{ay-10}" font-family="sans-serif" '
                           f'font-size="10" fill="{TEXT_DARK}" text-anchor="middle">{plabel}</text>')
            elif side == "B":
                out.append(f'<text x="{ax}" y="{ay+20}" font-family="sans-serif" '
                           f'font-size="10" fill="{TEXT_DARK}" text-anchor="middle">{plabel}</text>')
    return "\n".join(out)


def wire(x1, y1, x2, y2, label=None, label_offset=(0, -8)):
    """Draw a topic wire (thin black line with arrowhead and optional topic name)."""
    out = []
    # Polyline orthogonal route
    if x1 != x2 and y1 != y2:
        midx = (x1 + x2) / 2
        out.append(f'<path d="M {x1} {y1} L {midx} {y1} L {midx} {y2} L {x2} {y2}" '
                   f'fill="none" stroke="#444" stroke-width="1.2" marker-end="url(#wire_arrow)"/>')
        if label:
            out.append(f'<text x="{midx + label_offset[0]}" y="{(y1+y2)/2 + label_offset[1]}" '
                       f'font-family="monospace" font-size="10" fill="#444" text-anchor="middle">{label}</text>')
    else:
        out.append(f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" '
                   f'stroke="#444" stroke-width="1.2" marker-end="url(#wire_arrow)"/>')
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            out.append(f'<text x="{mx + label_offset[0]}" y="{my + label_offset[1]}" '
                       f'font-family="monospace" font-size="10" fill="#444" text-anchor="middle">{label}</text>')
    return "\n".join(out)


# =====================================================================
# Pillar 1 — Structure (IBD-style)
# =====================================================================

def pillar_1_structure(x0, y0, w, h):
    """Safety subsystem topology: 4 parts + 3 typed connections."""
    out = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" '
           f'fill="#fafafa" stroke="#dddddd" stroke-width="1" rx="3"/>']
    # Outer "ibd" header band
    out.append(f'<text x="{x0+12}" y="{y0+22}" font-family="monospace" font-size="11" '
               f'fill="{TEXT_MUTED}">ibd [part def] SafetyChainFocus</text>')

    # Part box positions inside the panel (relative to x0, y0)
    # Layout (4 boxes): lidar (top-left), obstacleDetector (top-right),
    #                   velocitySmoother (bottom-left), collisionGuard (bottom-right).
    LX, LY = x0+30, y0+60      # lidar
    OX, OY = x0+450, y0+60     # obstacleDetector
    VX, VY = x0+30, y0+330     # velocitySmoother
    CX, CY = x0+450, y0+330    # collisionGuard

    # Part dimensions
    PW, PH = 220, 180

    # lidar : LidarDriver  (one out port: sensorPub)
    out.append(part_box(LX, LY, PW, PH, "lidar : LidarDriver",
                        ports=[(PW, PH/2, "sensorPub", "R")],
                        body_lines=["nodeName = \"lidar_driver\"",
                                    "frameId = \"lidar_link\"",
                                    "qos = sensorDataQoS"]))

    # obstacleDetector : ObstacleDetector  (in: rawSub, out: processedPub)
    out.append(part_box(OX, OY, PW, PH, "obstacleDetector : ObstacleDetector",
                        ports=[(0, PH/2, "rawSub", "L"),
                               (PW, PH/2, "processedPub", "R")],
                        body_lines=["nodeName = \"obstacle_detector\"",
                                    "satisfy ObstacleDetectionRangeReq"]))

    # velocitySmoother : AGRVelocitySmoother  (in: cmdVelIn, out: cmdVelOut)
    out.append(part_box(VX, VY, PW, PH, "velocitySmoother : AGRVelocitySmoother",
                        ports=[(0, PH/2, "cmdVelIn", "L"),
                               (PW, PH/2, "cmdVelOut", "R")],
                        body_lines=["nodeName = \"velocity_smoother\"",
                                    "qos = systemDefaultQoS"]))

    # collisionGuard : CollisionGuard  (in: cmdVelIn, scanSub; out: cmdVelOut)
    out.append(part_box(CX, CY, PW, PH, "collisionGuard : CollisionGuard",
                        head=STATE_HEAD, stroke=STATE_STROKE,    # safety-critical, distinct color
                        ports=[(0, PH/2 - 30, "cmdVelIn", "L"),
                               (0, PH/2 + 30, "scanSub", "L"),
                               (PW, PH/2, "cmdVelOut", "R")],
                        body_lines=["nodeName = \"collision_guard\"",
                                    "namespace = \"/safety\"",
                                    "satisfy EmergencyStopReq",
                                    "satisfy CollisionAvoidanceReq"]))

    # Connections (typed wires)
    # scanToDetector: lidar.sensorPub -> obstacleDetector.rawSub
    out.append(wire(LX + PW, LY + PH/2, OX, OY + PH/2, label="/scan"))
    # scanToGuard: lidar.sensorPub -> collisionGuard.scanSub (longer route)
    out.append(f'<path d="M {LX+PW} {LY+PH/2 + 6} '
               f'L {LX+PW + 30} {LY+PH/2 + 6} '
               f'L {LX+PW + 30} {CY+PH/2+30} '
               f'L {CX} {CY+PH/2+30}" '
               f'fill="none" stroke="#444" stroke-width="1.2" marker-end="url(#wire_arrow)"/>')
    out.append(f'<text x="{LX+PW + 35}" y="{(LY+PH/2 + CY+PH/2)/2}" font-family="monospace" '
               f'font-size="10" fill="#444">/scan</text>')
    # smootherToGuard: velocitySmoother.cmdVelOut -> collisionGuard.cmdVelIn
    out.append(wire(VX + PW, VY + PH/2, CX, CY + PH/2 - 30, label="/cmd_vel_smooth"))

    # Caption strip at bottom
    out.append(f'<text x="{x0+12}" y="{y0+h-12}" font-family="sans-serif" font-size="10" '
               f'font-style="italic" fill="{TEXT_MUTED}">'
               f'Y-junction: collisionGuard fuses sensor + commanded-velocity inputs to satisfy safety reqs.'
               f'</text>')
    return "\n".join(out)


# =====================================================================
# Pillar 2 — Behavior (state machine)
# =====================================================================

def pillar_2_behavior(x0, y0, w, h):
    """OperationalModes state machine with safetyPort highlighted."""
    out = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" '
           f'fill="#fafafa" stroke="#dddddd" stroke-width="1" rx="3"/>']
    out.append(f'<text x="{x0+12}" y="{y0+22}" font-family="monospace" font-size="11" '
               f'fill="{TEXT_MUTED}">stm [state def] OperationalModes</text>')

    # Outer state def container
    SX, SY, SW, SH = x0+15, y0+38, w-30, h-70
    out.append(f'<rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" '
               f'fill="white" stroke="{STATE_STROKE}" stroke-width="1.5" rx="4"/>')

    # Title band
    out.append(f'<rect x="{SX}" y="{SY}" width="{SW}" height="36" '
               f'fill="{STATE_HEAD}" stroke="{STATE_STROKE}" stroke-width="1.5" rx="4"/>')
    out.append(f'<rect x="{SX}" y="{SY+28}" width="{SW}" height="8" fill="{STATE_HEAD}" stroke="none"/>')
    out.append(f'<line x1="{SX}" y1="{SY+36}" x2="{SX+SW}" y2="{SY+36}" stroke="{STATE_STROKE}" stroke-width="1.5"/>')
    out.append(f'<text x="{SX+SW/2}" y="{SY+24}" font-family="sans-serif" font-size="13" '
               f'font-weight="bold" fill="{TEXT_DARK}" text-anchor="middle">'
               f'OperationalModes</text>')

    # State positions inside the state def container
    def state(cx, cy, label, sw=110, sh=50, accent=False):
        col = STATE_STROKE
        bg = "#fff5f4" if accent else "white"
        return (f'<rect x="{cx-sw/2}" y="{cy-sh/2}" width="{sw}" height="{sh}" '
                f'fill="{bg}" stroke="{col}" stroke-width="1.5" rx="10"/>'
                f'<text x="{cx}" y="{cy-2}" font-family="sans-serif" font-size="10" '
                f'font-style="italic" fill="{TEXT_MUTED}" text-anchor="middle">«state»</text>'
                f'<text x="{cx}" y="{cy+14}" font-family="sans-serif" font-size="12" '
                f'font-weight="bold" fill="{TEXT_DARK}" text-anchor="middle">{label}</text>')

    # State coordinates inside SX/SY/SW/SH
    s_idle      = (SX+90,  SY+90)
    s_charging  = (SX+90,  SY+200)
    s_autonomous= (SX+260, SY+90)
    s_manual    = (SX+260, SY+200)
    s_emergency = (SX+430, SY+145)

    out.append(state(*s_idle, "idle"))
    out.append(state(*s_charging, "charging"))
    out.append(state(*s_autonomous, "autonomous"))
    out.append(state(*s_manual, "manual"))
    out.append(state(*s_emergency, "emergency", accent=True))

    # Initial-state black dot
    init_x, init_y = SX+30, SY+90
    out.append(f'<circle cx="{init_x}" cy="{init_y}" r="6" fill="{STATE_STROKE}"/>')
    out.append(f'<path d="M {init_x+6} {init_y} L {s_idle[0]-55} {s_idle[1]}" '
               f'fill="none" stroke="{STATE_STROKE}" stroke-width="1.5" marker-end="url(#sm_arrow)"/>')

    # Transitions (annotated)
    def trans(x1, y1, x2, y2, label, label_offset=(0,-6)):
        # Simple straight transition with label
        return (f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" '
                f'stroke="{STATE_STROKE}" stroke-width="1.5" marker-end="url(#sm_arrow)"/>'
                f'<text x="{(x1+x2)/2 + label_offset[0]}" y="{(y1+y2)/2 + label_offset[1]}" '
                f'font-family="sans-serif" font-size="10" fill="{TEXT_DARK}" text-anchor="middle">{label}</text>')

    # idle -> autonomous (startMission)
    out.append(trans(s_idle[0]+55, s_idle[1], s_autonomous[0]-55, s_autonomous[1],
                     "startMission via commandPort"))
    # autonomous -> manual (takeControl)
    out.append(trans(s_autonomous[0], s_autonomous[1]+25, s_manual[0], s_manual[1]-25,
                     "takeControl", label_offset=(50,0)))
    # autonomous -> emergency (triggerEmergency via safetyPort)
    out.append(f'<path d="M {s_autonomous[0]+55} {s_autonomous[1]} L {s_emergency[0]-55} {s_emergency[1]-15}" '
               f'fill="none" stroke="{STATE_STROKE}" stroke-width="1.5" marker-end="url(#sm_arrow)"/>')
    out.append(f'<text x="{(s_autonomous[0]+s_emergency[0])/2 + 10}" y="{(s_autonomous[1]+s_emergency[1])/2 - 30}" '
               f'font-family="sans-serif" font-size="10" font-weight="bold" '
               f'fill="{STATE_STROKE}" text-anchor="middle">triggerEmergency</text>')
    out.append(f'<text x="{(s_autonomous[0]+s_emergency[0])/2 + 10}" y="{(s_autonomous[1]+s_emergency[1])/2 - 16}" '
               f'font-family="monospace" font-size="9" '
               f'fill="{TEXT_MUTED}" text-anchor="middle">accept EmergencyTrigger via safetyPort</text>')
    # idle <-> charging (guards)
    out.append(trans(s_idle[0], s_idle[1]+25, s_charging[0], s_charging[1]-25,
                     "[batteryLevel &lt; 0.2]", label_offset=(-50,0)))
    # emergency -> idle (clearEmergency)
    out.append(f'<path d="M {s_emergency[0]-55} {s_emergency[1]+15} L {s_idle[0]+55} {s_idle[1]+10}" '
               f'fill="none" stroke="{STATE_STROKE}" stroke-width="1.5" '
               f'stroke-dasharray="4,2" marker-end="url(#sm_arrow)"/>')

    # safetyPort label as a port circle on the right edge of the state def container
    sp_x, sp_y = SX+SW, SY+145
    out.append(f'<rect x="{sp_x-6}" y="{sp_y-6}" width="12" height="12" '
               f'fill="white" stroke="{TRIGGER_C}" stroke-width="2"/>')
    out.append(f'<text x="{sp_x+12}" y="{sp_y+5}" font-family="sans-serif" font-size="11" '
               f'font-weight="bold" fill="{TRIGGER_C}">safetyPort</text>')

    # Caption
    out.append(f'<text x="{x0+12}" y="{y0+h-12}" font-family="sans-serif" font-size="10" '
               f'font-style="italic" fill="{TEXT_MUTED}">'
               f'safetyPort is the architectural channel that admits EmergencyTrigger events.'
               f'</text>')
    return "\n".join(out)


# =====================================================================
# Pillar 3 — Requirements
# =====================================================================

def pillar_3_requirements(x0, y0, w, h):
    """Two requirement defs with attributes and require constraints."""
    out = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" '
           f'fill="#fafafa" stroke="#dddddd" stroke-width="1" rx="3"/>']
    out.append(f'<text x="{x0+12}" y="{y0+22}" font-family="monospace" font-size="11" '
               f'fill="{TEXT_MUTED}">req [package] SafetyRequirements</text>')

    def req_box(rx, ry, rw, rh, name, body):
        b = []
        b.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" '
                 f'fill="{REQ_BODY}" stroke="{REQ_STROKE}" stroke-width="1.5" rx="6"/>')
        b.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="44" '
                 f'fill="{REQ_HEAD}" stroke="{REQ_STROKE}" stroke-width="1.5" rx="6"/>')
        b.append(f'<rect x="{rx}" y="{ry+36}" width="{rw}" height="8" fill="{REQ_HEAD}" stroke="none"/>')
        b.append(f'<line x1="{rx}" y1="{ry+44}" x2="{rx+rw}" y2="{ry+44}" stroke="{REQ_STROKE}" stroke-width="1.5"/>')
        b.append(f'<text x="{rx+rw/2}" y="{ry+18}" font-family="sans-serif" font-size="11" '
                 f'font-style="italic" fill="{TEXT_MUTED}" text-anchor="middle">«requirement def»</text>')
        b.append(f'<text x="{rx+rw/2}" y="{ry+35}" font-family="sans-serif" font-size="13" '
                 f'font-weight="bold" fill="{TEXT_DARK}" text-anchor="middle">{name}</text>')
        # Body text
        for i, line in enumerate(body):
            italic = ' font-style="italic"' if line.startswith("doc:") else ""
            mono = ' font-family="monospace"' if line.startswith(("attr:", "req:")) else ' font-family="sans-serif"'
            txt = line.split(":", 1)[1].lstrip() if ":" in line[:6] else line
            b.append(f'<text x="{rx+12}" y="{ry+44+22+i*18}"{mono}{italic} font-size="11" fill="{TEXT_DARK}">{txt}</text>')
        return "\n".join(b)

    # EmergencyStopReq
    out.append(req_box(x0+30, y0+50, w-60, 200, "EmergencyStopReq",
                       ["doc: The robot shall halt all motion within 0.5 s",
                        "doc: of receiving an emergency stop command.",
                        "attr: subject vehicle : Vehicle",
                        "attr: attribute maxResponseMs : Real = 500",
                        "req: require constraint {",
                        "req:   vehicle.responseTimeMs &lt;= maxResponseMs",
                        "req: }"]))

    # CollisionAvoidanceReq
    out.append(req_box(x0+30, y0+280, w-60, 200, "CollisionAvoidanceReq",
                       ["doc: The robot shall maintain a minimum clearance",
                        "doc: of 0.3 m from all detected obstacles.",
                        "attr: subject vehicle : Vehicle",
                        "attr: attribute minClearanceM : Real = 0.3",
                        "req: require constraint {",
                        "req:   vehicle.nearestObstacleM &gt;= minClearanceM",
                        "req: }"]))

    return "\n".join(out)


# =====================================================================
# Pillar 4 — Constraints (parametric)
# =====================================================================

def pillar_4_constraints(x0, y0, w, h):
    """EmergencyStopBudget constraint def: parametric decomposition."""
    out = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" '
           f'fill="#fafafa" stroke="#dddddd" stroke-width="1" rx="3"/>']
    out.append(f'<text x="{x0+12}" y="{y0+22}" font-family="monospace" font-size="11" '
               f'fill="{TEXT_MUTED}">par [constraint def] EmergencyStopBudget</text>')

    # Constraint def container
    cx_, cy_, cw_, ch_ = x0+30, y0+50, w-60, 230
    out.append(f'<rect x="{cx_}" y="{cy_}" width="{cw_}" height="{ch_}" '
               f'fill="{CON_BODY}" stroke="{CON_STROKE}" stroke-width="1.5" rx="6"/>')
    out.append(f'<rect x="{cx_}" y="{cy_}" width="{cw_}" height="44" '
               f'fill="{CON_HEAD}" stroke="{CON_STROKE}" stroke-width="1.5" rx="6"/>')
    out.append(f'<rect x="{cx_}" y="{cy_+36}" width="{cw_}" height="8" fill="{CON_HEAD}" stroke="none"/>')
    out.append(f'<line x1="{cx_}" y1="{cy_+44}" x2="{cx_+cw_}" y2="{cy_+44}" stroke="{CON_STROKE}" stroke-width="1.5"/>')
    out.append(f'<text x="{cx_+cw_/2}" y="{cy_+18}" font-family="sans-serif" font-size="11" '
               f'font-style="italic" fill="{TEXT_MUTED}" text-anchor="middle">«constraint def»</text>')
    out.append(f'<text x="{cx_+cw_/2}" y="{cy_+35}" font-family="sans-serif" font-size="13" '
               f'font-weight="bold" fill="{TEXT_DARK}" text-anchor="middle">EmergencyStopBudget</text>')

    # Attribute parameters as small rounded boxes (parametric-style)
    def param(px, py, plabel, pval=""):
        b = []
        b.append(f'<rect x="{px}" y="{py}" width="190" height="34" '
                 f'fill="#fff7e6" stroke="{CON_STROKE}" stroke-width="1.2" rx="4"/>')
        b.append(f'<text x="{px+10}" y="{py+14}" font-family="sans-serif" font-size="10" '
                 f'font-style="italic" fill="{TEXT_MUTED}">«attribute»</text>')
        b.append(f'<text x="{px+10}" y="{py+28}" font-family="monospace" font-size="11" '
                 f'fill="{TEXT_DARK}">{plabel}</text>')
        if pval:
            b.append(f'<text x="{px+185}" y="{py+28}" font-family="monospace" font-size="10" '
                     f'fill="{TEXT_MUTED}" text-anchor="end">{pval}</text>')
        return "\n".join(b)

    # Three input parameters (latencies)
    out.append(param(cx_+15, cy_+58, "sensingLatencyMs : Real"))
    out.append(param(cx_+15, cy_+98, "decisionLatencyMs : Real"))
    out.append(param(cx_+15, cy_+138, "actuationLatencyMs : Real"))

    # Output parameter
    out.append(param(cx_+220, cy_+98, "totalResponseMs : Real"))

    # Constraint expression box
    eq_y = cy_+185
    out.append(f'<rect x="{cx_+15}" y="{eq_y}" width="{cw_-30}" height="36" '
               f'fill="#f5f5f5" stroke="{CON_STROKE}" stroke-width="1.2" stroke-dasharray="4,2" rx="3"/>')
    out.append(f'<text x="{cx_+25}" y="{eq_y+14}" font-family="sans-serif" font-size="10" '
               f'font-style="italic" fill="{TEXT_MUTED}">constraint expression:</text>')
    out.append(f'<text x="{cx_+25}" y="{eq_y+30}" font-family="monospace" font-size="11" '
               f'fill="{TEXT_DARK}">'
               f'totalResponseMs == sensingLatencyMs + decisionLatencyMs + actuationLatencyMs</text>')

    # Lines connecting input attrs to output attr
    out.append(f'<path d="M {cx_+205} {cy_+75} C {cx_+215} {cy_+75}, {cx_+215} {cy_+115}, {cx_+220} {cy_+115}" '
               f'fill="none" stroke="{CON_STROKE}" stroke-width="1.2"/>')
    out.append(f'<path d="M {cx_+205} {cy_+115} L {cx_+220} {cy_+115}" '
               f'fill="none" stroke="{CON_STROKE}" stroke-width="1.2"/>')
    out.append(f'<path d="M {cx_+205} {cy_+155} C {cx_+215} {cy_+155}, {cx_+215} {cy_+115}, {cx_+220} {cy_+115}" '
               f'fill="none" stroke="{CON_STROKE}" stroke-width="1.2"/>')

    # Caption
    out.append(f'<text x="{x0+12}" y="{y0+h-12}" font-family="sans-serif" font-size="10" '
               f'font-style="italic" fill="{TEXT_MUTED}">'
               f'Parametric decomposition: maxResponseMs in EmergencyStopReq frames totalResponseMs.'
               f'</text>')
    return "\n".join(out)


# =====================================================================
# Cross-pillar arrows
# =====================================================================

def cross_pillar_arrows():
    """Four explicit architectural bindings."""
    # Anchor coordinates (eyeballed from panel layout below)
    # Pillar 1 (Structure):  x: 30..830,    y: 30..620   (panel)
    #   collisionGuard part: roughly at (480, 330)..(700, 510)
    cg_right = (700, 380)        # right edge upper
    cg_right_lo = (700, 460)     # right edge lower
    cg_bottom_l = (490, 510)     # left of collisionGuard's bottom edge
    # Pillar 2 (Behavior):   x: 30..830,    y: 660..1140 (panel)
    #   safetyPort: at the right edge of OperationalModes container (canvas x ~ 815)
    safety_port = (815, 805)
    # Pillar 3 (Requirements): x: 870..1670, y: 30..520 (panel)
    #   EmergencyStopReq: at top of P3, left edge
    estop_left = (900, 130)
    coll_left = (900, 360)
    estop_bottom = (1270, 250)   # bottom-middle of EmergencyStopReq
    # Pillar 4 (Constraints): x: 870..1670, y: 560..1140 (panel)
    con_top_mid = (1270, 610)    # top-middle of EmergencyStopBudget container

    out = ['<g font-family="sans-serif" font-size="13" font-weight="bold">']

    # 1+2. Two «satisfy» arrows (collisionGuard -> two requirements)
    for tgt in [estop_left, coll_left]:
        out.append(
            f'<path d="M {cg_right[0]} {(cg_right[1]+cg_right_lo[1])/2 if tgt is coll_left else cg_right[1]} '
            f'C {(cg_right[0]+tgt[0])/2 + 30} {((cg_right[1]+cg_right_lo[1])/2 if tgt is coll_left else cg_right[1])-30}, '
            f'{(cg_right[0]+tgt[0])/2 + 30} {tgt[1]+20}, '
            f'{tgt[0]-3} {tgt[1]}" '
            f'stroke="{SATISFY_C}" stroke-width="2.5" fill="none" '
            f'marker-end="url(#arrow_satisfy)"/>'
        )
    # Single shared label
    out.append(f'<text x="{(cg_right[0]+estop_left[0])/2 - 30}" y="{cg_right[1] - 35}" fill="{SATISFY_C}">«satisfy»</text>')

    # 3. «triggers» (collisionGuard.scanSub region -> safetyPort on P2)
    midx = max(cg_bottom_l[0] - 60, 90)
    midy = (cg_bottom_l[1] + safety_port[1]) / 2
    out.append(
        f'<path d="M {cg_bottom_l[0]} {cg_bottom_l[1]} '
        f'L {cg_bottom_l[0]} {midy} '
        f'L {safety_port[0]+40} {midy} '
        f'L {safety_port[0]+40} {safety_port[1]} '
        f'L {safety_port[0]+12} {safety_port[1]}" '
        f'stroke="{TRIGGER_C}" stroke-width="2.5" fill="none" '
        f'stroke-dasharray="6,4" '
        f'marker-end="url(#arrow_triggers)"/>'
    )
    out.append(f'<text x="{cg_bottom_l[0] - 40}" y="{midy - 8}" fill="{TRIGGER_C}">«triggers»</text>')

    # 4. «frame» (EmergencyStopReq -> EmergencyStopBudget)
    midy2 = (estop_bottom[1] + con_top_mid[1]) / 2
    out.append(
        f'<path d="M {estop_bottom[0]} {estop_bottom[1]} '
        f'L {estop_bottom[0]} {midy2} '
        f'L {con_top_mid[0]} {midy2} '
        f'L {con_top_mid[0]} {con_top_mid[1]-3}" '
        f'stroke="{FRAME_C}" stroke-width="2.5" fill="none" '
        f'marker-end="url(#arrow_frame)"/>'
    )
    out.append(f'<text x="{con_top_mid[0]+10}" y="{midy2 - 8}" fill="{FRAME_C}">«frame»</text>')

    out.append('</g>')
    return "\n".join(out)


# =====================================================================
# Pillar titles + borders + legend
# =====================================================================

def titles_and_borders(panels):
    out = ['<g font-family="sans-serif">']
    for x, y, w, h, label in panels:
        out.append(f'<text x="{x}" y="{y-12}" font-size="22" font-weight="bold" '
                   f'fill="#c00000">{label}</text>')
    out.append('</g>')
    return "\n".join(out)


def legend(y):
    return f'''
    <g font-family="sans-serif" font-size="13">
        <text x="30" y="{y}" font-weight="bold" fill="{TEXT_DARK}">Cross-pillar bindings:</text>
        <line x1="200" y1="{y-5}" x2="245" y2="{y-5}" stroke="{SATISFY_C}" stroke-width="2.5" marker-end="url(#arrow_satisfy)"/>
        <text x="252" y="{y}" fill="{SATISFY_C}">«satisfy» (part fulfills requirement)</text>
        <text x="600" y="{y}" font-weight="bold" fill="{TEXT_DARK}">|</text>
        <line x1="620" y1="{y-5}" x2="665" y2="{y-5}" stroke="{TRIGGER_C}" stroke-width="2.5" stroke-dasharray="6,4" marker-end="url(#arrow_triggers)"/>
        <text x="672" y="{y}" fill="{TRIGGER_C}">«triggers» (event drives state transition)</text>
        <text x="1010" y="{y}" font-weight="bold" fill="{TEXT_DARK}">|</text>
        <line x1="1030" y1="{y-5}" x2="1075" y2="{y-5}" stroke="{FRAME_C}" stroke-width="2.5" marker-end="url(#arrow_frame)"/>
        <text x="1082" y="{y}" fill="{FRAME_C}">«frame» (requirement frames constraint def)</text>
    </g>
    '''


# =====================================================================
# Main: assemble
# =====================================================================

def main():
    P1 = (30, 60, 800, 590, "1. Structure")
    P2 = (30, 690, 800, 460, "2. Behavior")
    P3 = (870, 60, 800, 480, "3. Requirements")
    P4 = (870, 580, 800, 320, "4. Constraints")
    panels = [P1, P2, P3, P4]

    parts = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}"
     viewBox="0 0 {CANVAS_W} {CANVAS_H}">
<defs>
    <marker id="arrow_satisfy"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{SATISFY_C}"/></marker>
    <marker id="arrow_triggers" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{TRIGGER_C}"/></marker>
    <marker id="arrow_frame"    viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{FRAME_C}"/></marker>
    <marker id="wire_arrow"     viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#444"/></marker>
    <marker id="sm_arrow"       viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{STATE_STROKE}"/></marker>
</defs>
<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="white"/>
''']
    parts.append(pillar_1_structure(*P1[:4]))
    parts.append(pillar_2_behavior(*P2[:4]))
    parts.append(pillar_3_requirements(*P3[:4]))
    parts.append(pillar_4_constraints(*P4[:4]))
    parts.append(titles_and_borders(panels))
    parts.append(cross_pillar_arrows())
    parts.append(legend(CANVAS_H - 30))
    parts.append("</svg>\n")
    OUT_SVG.write_text("\n".join(parts))
    print(f"Wrote {OUT_SVG}")


if __name__ == "__main__":
    main()
