import { useId } from "react";
import { Sockrates } from "./Sockrates";
import type { SockSkin } from "../sockSkin";

/**
 * Sockrates in his natural habitat: a dresser drawer full of rolled socks.
 *
 * Three stacked layers rather than one drawing, because the depth is the whole joke —
 * socks behind him, socks in front of him, and his sock leg disappearing behind the
 * drawer front. Stacking order does that for free.
 *
 * The mascot is the real `<Sockrates>` rig, so his skins, moods, and reduced-motion
 * poses keep working here with no second copy of the artwork to maintain. He sits
 * between the layers as a sibling and *not* as a nested `<svg>`: a nested one takes
 * its width and height in CSS pixels, which are not the parent's viewBox units, so it
 * lands at the wrong size and the wrong place. Absolute percentages of the frame are
 * the same in both coordinate systems.
 *
 * The two SVG layers share the 320x240 viewBox, and every percentage below is read
 * off it. The line that holds the illusion together is the drawer front at y=148:
 * the mascot is placed so his cuff falls below it.
 */

const FRAME_W = 320;
const FRAME_H = 240;
const PANEL_TOP = 148;

/** The mascot's box within the frame, in viewBox units. */
const SOCKRATES = { x: 84, y: 32, size: 118 };

/** Wood, dark to light. The cavity is the darkest, so socks read as being inside it. */
const CAVITY = "#5b3d25";
const RIM = "#b3824c";
const PANEL = "#cb9c66";
const GROOVE = "#a67c4a";
const OUTLINE = "#12263a";

const percent = (value: number, of: number) => `${(value / of) * 100}%`;

interface SockProps {
  x: number;
  y: number;
  r: number;
  base: string;
  ink: string;
  tilt?: number;
}

/**
 * A sock rolled into a ball, the way socks are actually put away.
 *
 * Stripes are full-width bars clipped to the ball rather than shapes cut to fit it,
 * so one clip path does the work at every radius and the outline is drawn last over
 * a clean edge. The tuck line across the middle is what stops it reading as a
 * beach ball.
 */
function RolledSock({ x, y, r, base, ink, tilt = 0 }: SockProps) {
  // Same reason as the mascot rig: React ids contain colons, which are invalid in a
  // CSS selector and trip SVG sanitisers.
  const clipId = `roll-${useId().replace(/:/g, "")}`;

  return (
    <g transform={`translate(${x} ${y}) rotate(${tilt})`}>
      <defs>
        <clipPath id={clipId}>
          <circle r={r} />
        </clipPath>
      </defs>

      <circle r={r} fill={base} />
      <g clipPath={`url(#${clipId})`}>
        <rect x={-r} y={-r * 0.62} width={r * 2} height={r * 0.3} fill={ink} opacity="0.9" />
        <rect x={-r} y={r * 0.34} width={r * 2} height={r * 0.3} fill={ink} opacity="0.9" />
      </g>

      <path
        d={`M ${-r * 0.78} ${-r * 0.12} q ${r * 0.78} ${r * 0.5} ${r * 1.56} 0`}
        fill="none"
        stroke={OUTLINE}
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.5"
      />
      <ellipse
        cx={-r * 0.3}
        cy={-r * 0.52}
        rx={r * 0.26}
        ry={r * 0.13}
        fill="#ffffff"
        opacity="0.55"
        transform={`rotate(-25 ${-r * 0.3} ${-r * 0.52})`}
      />
      <circle r={r} fill="none" stroke={OUTLINE} strokeWidth="2.5" />
    </g>
  );
}

interface Props {
  skin?: SockSkin;
  /** Rendered width in px. The frame is 4:3, so the height follows. */
  width?: number;
  className?: string;
}

export function SockDrawerScene({ skin = "athletic", width = 320, className }: Props) {
  return (
    <div
      className={`sock-drawer-scene${className ? ` ${className}` : ""}`}
      style={{ width, height: (width * FRAME_H) / FRAME_W }}
      role="img"
      aria-label="Sockrates popping out of a drawer full of rolled-up socks"
    >
      {/* Layer 1: the drawer's inside, and the socks at the back of it. */}
      <svg className="drawer-layer" viewBox={`0 0 ${FRAME_W} ${FRAME_H}`} aria-hidden="true">
        {/* The drawer has to sit on something or it floats. */}
        <ellipse cx="160" cy="228" rx="126" ry="11" fill={OUTLINE} opacity="0.13" />

        {/* Looking slightly down into an open drawer: the top edge of the four walls
            is the outer quad, and the cavity is that quad inset by the wall thickness. */}
        <path
          d="M32 152 L288 152 L258 62 L62 62 Z"
          fill={RIM}
          stroke={OUTLINE}
          strokeWidth="3"
          strokeLinejoin="round"
        />
        <path d="M48 146 L272 146 L248 72 L72 72 Z" fill={CAVITY} />

        <RolledSock x={96} y={104} r={17} base="#f4f6fa" ink="#118ab2" tilt={-12} />
        <RolledSock x={140} y={90} r={14} base="#ffd166" ink="#ef476f" tilt={18} />
        <RolledSock x={212} y={92} r={15} base="#e8f7ff" ink="#6f42c1" tilt={-6} />
        <RolledSock x={244} y={110} r={18} base="#f4f6fa" ink="#06d6a0" tilt={10} />
      </svg>

      {/* Layer 2: the resident philosopher, mid-rummage. Positioned in percentages of
          the frame, so the whole scene still scales from the one `width` prop. */}
      <div
        className="drawer-mascot"
        style={{ left: percent(SOCKRATES.x, FRAME_W), top: percent(SOCKRATES.y, FRAME_H) }}
      >
        <Sockrates skin={skin} mood="idle" size={(width * SOCKRATES.size) / FRAME_W} />
      </div>

      {/* Layer 3: the socks in front of him, then the drawer front over all of it. */}
      <svg className="drawer-layer" viewBox={`0 0 ${FRAME_W} ${FRAME_H}`} aria-hidden="true">
        <RolledSock x={74} y={134} r={19} base="#fff3d6" ink="#ef476f" tilt={22} />
        <RolledSock x={188} y={140} r={16} base="#f3e8d2" ink="#8b5e34" tilt={-14} />
        <RolledSock x={250} y={134} r={18} base="#f4f6fa" ink="#2f6feb" tilt={6} />

        <rect
          x="30"
          y={PANEL_TOP}
          width="260"
          height="74"
          rx="10"
          fill={PANEL}
          stroke={OUTLINE}
          strokeWidth="3"
        />
        <rect
          x="46"
          y={PANEL_TOP + 13}
          width="228"
          height="48"
          rx="7"
          fill="none"
          stroke={GROOVE}
          strokeWidth="2.5"
        />
        <g fill="none" stroke={GROOVE} strokeWidth="2" opacity="0.45" strokeLinecap="round">
          <path d="M64 206 q 48 -6 96 0 t 92 0" />
          <path d="M64 214 q 60 -5 120 0" />
        </g>
        {[110, 210].map((cx) => (
          <g key={cx}>
            <circle
              cx={cx}
              cy={PANEL_TOP + 37}
              r="10"
              fill="#8a5f34"
              stroke={OUTLINE}
              strokeWidth="3"
            />
            <circle cx={cx - 3} cy={PANEL_TOP + 34} r="3" fill="#ffffff" opacity="0.4" />
          </g>
        ))}

        {/* One sock perched on the front edge, half out of the drawer. Drawn last so
            it straddles the panel, which is what makes the drawer read as overstuffed
            rather than tidily packed. */}
        <RolledSock x={62} y={150} r={15} base="#ef476f" ink="#ffd166" tilt={-24} />
      </svg>
    </div>
  );
}
