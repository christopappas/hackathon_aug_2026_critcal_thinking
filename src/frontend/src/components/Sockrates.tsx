import { useId } from "react";
import type { CSSProperties } from "react";
import type { SockSkin } from "../sockSkin";

/**
 * Sockrates: a sock puppet who is convinced he is a great Greek philosopher.
 *
 * Everything is hand-authored SVG in a fixed `viewBox`, so one set of CSS rules
 * drives every instance regardless of rendered size. Two rules keep the rig from
 * breaking, and both are load-bearing:
 *
 *   1. Positional transforms live on a wrapper <g>; animated rotation lives on the
 *      element itself. CSS `transform` replaces the `transform` presentation
 *      attribute wholesale, so an element that carries both teleports on frame one.
 *   2. No animation uses `animation-fill-mode`. Moods are expressed by swapping a
 *      class, and with no fill mode the element always reverts to its base pose —
 *      so there is no state a mood can get stuck in.
 */

export type SockratesMood =
  | "idle"
  | "listening"
  | "thinking"
  | "talking"
  | "impressed"
  | "hinting"
  | "celebrating";

// --- Geometry. All coordinates are viewBox units; the mouth hinge is (104, 104).

/**
 * The leg of the sock, trailing down and back from the head. Angled rather than
 * vertical: a straight tube under the head reads as a separate box, and the whole
 * point is one continuous sock silhouette.
 */
const LEG_D = "M130 116 C128 154 113 180 88 194 L58 176 C82 163 93 140 96 110 Z";

const CUFF_D = "M88 194 L58 176 L70 155 L100 173 Z";

/**
 * The two jaws share their lip edge exactly — (96,108) to (208,96) — so a closed
 * mouth tiles with no seam and the throat behind it is fully covered.
 */
const JAW_UPPER_D =
  "M96 108 C86 68 110 38 150 36 C190 34 210 56 210 82 L208 96 L96 108 Z";

const JAW_LOWER_D =
  "M96 108 L208 96 C216 102 213 128 198 140 C174 156 128 156 110 143 C98 134 93 120 96 108 Z";

/**
 * The throat. Deliberately larger than the closed mouth and clipped to the union
 * of the two jaws in their resting position: whatever a jaw swings away from is
 * revealed, and the wedge can never poke outside the silhouette. Sizing this
 * shape by hand to hide when closed is the fiddly way to get the same result.
 */
const MOUTH_D = "M92 108 L220 40 L220 160 Z";

const POLKA: [number, number][] = [
  [40, 44], [82, 30], [124, 46], [166, 32], [200, 50],
  [58, 82], [100, 68], [142, 84], [184, 70],
  [40, 120], [82, 106], [124, 122], [166, 108], [200, 126],
  [58, 158], [100, 144], [142, 160], [184, 146],
  [76, 194], [130, 194],
];

const ARGYLE: [number, number][] = [];
for (let row = -1; row < 5; row++) {
  for (let col = -1; col < 5; col++) {
    ARGYLE.push([col * 52 + (row % 2 ? 26 : 0), row * 52]);
  }
}

/**
 * csstype has no index signature for custom properties and the project builds with
 * `strict`, so the cast is required rather than stylistic.
 */
const SKIN_VARS: Record<SockSkin, CSSProperties> = {
  athletic: { "--sock-base": "#fbfcfe", "--sock-ink": "#2f6feb", "--sock-alt": "#c9d6ee" },
  rugby: { "--sock-base": "#fdfdfd", "--sock-ink": "#ef476f", "--sock-alt": "#118ab2" },
  argyle: { "--sock-base": "#f3e8d2", "--sock-ink": "#8b5e34", "--sock-alt": "#c8a165" },
  polka: { "--sock-base": "#fff3d6", "--sock-ink": "#ef476f", "--sock-alt": "#ffd166" },
  tiedye: { "--sock-base": "#e8f7ff", "--sock-ink": "#6f42c1", "--sock-alt": "#06d6a0" },
  rainbow: { "--sock-base": "#ffffff", "--sock-ink": "#ef476f", "--sock-alt": "#118ab2" },
  toga: { "--sock-base": "#f6f4ef", "--sock-ink": "#b9b3a6", "--sock-alt": "#d8d2c4" },
} as Record<SockSkin, CSSProperties>;

/**
 * Decoration for one skin, authored in plain viewBox coordinates.
 *
 * This is why the rig clips layered shapes instead of using <pattern>: a pattern's
 * default `objectBoundingBox` units would force every stripe to be expressed as a
 * fraction of a bounding box you cannot see, and tiling is the wrong primitive for
 * placing a knee stripe in a specific spot.
 */
function SkinLayer({ skin }: { skin: SockSkin }) {
  switch (skin) {
    case "rainbow":
      return (
        <>
          {["#ef476f", "#ff9f1c", "#ffd166", "#06d6a0", "#118ab2", "#6f42c1"].map((color, i) => (
            <rect key={color} x="0" y={i * 37} width="220" height="37" fill={color} opacity="0.85" />
          ))}
        </>
      );
    case "rugby":
      return (
        <>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <rect
              key={i}
              x="0"
              y={14 + i * 34}
              width="220"
              height="17"
              fill={i % 2 ? "var(--sock-alt)" : "var(--sock-ink)"}
            />
          ))}
        </>
      );
    case "polka":
      return (
        <>
          {POLKA.map(([cx, cy], i) => (
            <circle key={i} cx={cx} cy={cy} r="7" fill="var(--sock-ink)" opacity="0.8" />
          ))}
        </>
      );
    case "argyle":
      return (
        <g transform="rotate(45 110 110)">
          {ARGYLE.map(([x, y], i) => (
            <rect
              key={i}
              x={x}
              y={y}
              width="34"
              height="34"
              opacity="0.7"
              fill={i % 2 ? "var(--sock-alt)" : "var(--sock-ink)"}
            />
          ))}
        </g>
      );
    case "tiedye":
      // Translucent circles rather than a blur filter: a filter would need another
      // id, and every extra id is another cross-instance collision surface.
      return (
        <>
          <circle cx="66" cy="62" r="76" fill="var(--sock-ink)" opacity="0.4" />
          <circle cx="158" cy="126" r="86" fill="var(--sock-alt)" opacity="0.4" />
          <circle cx="120" cy="188" r="60" fill="var(--sock-ink)" opacity="0.3" />
        </>
      );
    case "toga":
      return (
        <>
          <path d="M0 58 Q110 28 220 68 L220 92 Q110 54 0 86 Z" fill="var(--sock-alt)" opacity="0.7" />
          <path d="M0 124 Q110 94 220 134 L220 156 Q110 118 0 150 Z" fill="var(--sock-alt)" opacity="0.5" />
        </>
      );
    case "athletic":
    default:
      return (
        <>
          <rect x="0" y="150" width="220" height="13" fill="var(--sock-ink)" />
          <rect x="0" y="169" width="220" height="13" fill="var(--sock-ink)" />
        </>
      );
  }
}

/** One sock-coloured piece: the skin, clipped to the piece, plus its outline. */
function SockPiece({ d, clipId, skin }: { d: string; clipId: string; skin: SockSkin }) {
  return (
    <>
      <g clipPath={`url(#${clipId})`}>
        <rect x="0" y="0" width="220" height="220" fill="var(--sock-base)" />
        <SkinLayer skin={skin} />
      </g>
      {/* Heavier than it looks like it needs to be: the chat header renders this at
          44px, where a 4-unit stroke in a 220 viewBox lands under one device pixel. */}
      <path d={d} fill="none" stroke="#12263a" strokeWidth="5" strokeLinejoin="round" />
    </>
  );
}

interface Props {
  mood?: SockratesMood;
  skin?: SockSkin;
  size?: number;
  /** Supplying a title makes the mascot a labelled image; omitting it hides it from AT. */
  title?: string;
  className?: string;
}

export function Sockrates({ mood = "idle", skin = "athletic", size = 96, title, className }: Props) {
  // React emits ids of the form ":r0:". Those happen to resolve inside url(#…) but
  // are invalid in a CSS selector and trip SVG sanitisers, so strip the colons.
  const uid = useId().replace(/:/g, "");
  const legClip = `sk-leg-${uid}`;
  const upperClip = `sk-upper-${uid}`;
  const lowerClip = `sk-lower-${uid}`;
  const mouthClip = `sk-mouth-${uid}`;

  return (
    <svg
      className={`sockrates mood-${mood}${className ? ` ${className}` : ""}`}
      style={{ ...SKIN_VARS[skin], width: size, height: size }}
      viewBox="0 0 220 220"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      {title && <title>{title}</title>}

      <defs>
        <clipPath id={legClip}>
          <path d={LEG_D} />
        </clipPath>
        <clipPath id={upperClip}>
          <path d={JAW_UPPER_D} />
        </clipPath>
        <clipPath id={lowerClip}>
          <path d={JAW_LOWER_D} />
        </clipPath>
        <clipPath id={mouthClip}>
          {/* Two paths in one clipPath give their union: the closed silhouette. */}
          <path d={JAW_UPPER_D} />
          <path d={JAW_LOWER_D} />
        </clipPath>
      </defs>

      <g className="sk-body">
        <g className="sk-leg">
          <SockPiece d={LEG_D} clipId={legClip} skin={skin} />
          <path d={CUFF_D} fill="#12263a" opacity="0.1" clipPath={`url(#${legClip})`} />
        </g>

        {/* Throat and tongue both live inside the closed silhouette, straddling the
            lip line, so they are covered by the jaws until one of them swings. */}
        <g clipPath={`url(#${mouthClip})`}>
          <path d={MOUTH_D} fill="#7c2b45" />
          <ellipse className="sk-tongue" cx="168" cy="100" rx="27" ry="11" fill="#e8607f" />
        </g>

        <g className="sk-jaw sk-jaw-lower">
          <SockPiece d={JAW_LOWER_D} clipId={lowerClip} skin={skin} />
          <g className="sk-beard">
            <path
              d="M140 148 C132 172 146 194 168 196 C188 192 196 168 190 140 C176 152 154 154 140 148 Z"
              fill="#f4f6fa"
              stroke="#b9c4d4"
              strokeWidth="3"
              strokeLinejoin="round"
            />
            <g fill="none" stroke="#cdd6e2" strokeWidth="2.5" strokeLinecap="round">
              <path d="M154 158 q-3 18 2 30" />
              <path d="M170 160 q1 18 -1 30" />
            </g>
          </g>
        </g>

        <g className="sk-jaw sk-jaw-upper">
          <SockPiece d={JAW_UPPER_D} clipId={upperClip} skin={skin} />

          {/* A laurel wreath around the back of the crown. Together with the beard
              this is what makes him read as Sockrates rather than as a sock. */}
          <g className="sk-crown" fill="#3f9d6a" stroke="#2c7a50" strokeWidth="1.5">
            <path d="M99 88 C82 84 72 90 72 99 C85 106 96 99 99 88 Z" />
            <path d="M99 64 C83 57 71 63 70 72 C83 81 95 75 99 64 Z" />
            <path d="M108 44 C95 32 82 33 78 41 C88 53 102 53 108 44 Z" />
            <path d="M126 32 C119 18 106 13 100 19 C105 33 117 39 126 32 Z" />
          </g>

          <g className="sk-brow" fill="#12263a">
            <rect x="132" y="27" width="27" height="7" rx="3.5" transform="rotate(-16 145 30)" />
            <rect x="178" y="42" width="23" height="6" rx="3" transform="rotate(-8 189 45)" />
          </g>

          <g className="sk-eyes">
            <circle cx="146" cy="62" r="19" fill="#ffffff" stroke="#12263a" strokeWidth="4" />
            <circle cx="186" cy="70" r="16" fill="#ffffff" stroke="#12263a" strokeWidth="4" />
            <g className="sk-pupils" fill="#12263a">
              <circle cx="152" cy="65" r="9" />
              <circle cx="191" cy="73" r="7.5" />
            </g>
            <g fill="#ffffff" opacity="0.9">
              <circle cx="147" cy="58" r="3.5" />
              <circle cx="187" cy="67" r="3" />
            </g>
            {/* Half-lid over the right eye. A true one-eyed squint would mean
                grouping every eye part twice; dropping a lid on top is one node. */}
            <path
              className="sk-lid"
              d="M170 70 a16 16 0 0 1 32 0 Z"
              fill="var(--sock-base)"
              stroke="#12263a"
              strokeWidth="3"
              opacity="0"
            />
          </g>
        </g>
      </g>

      {/* Shown for impressed and celebrating; also the reduced-motion stand-in. */}
      <g className="sk-spark" fill="#ffd166" stroke="#e0a800" strokeWidth="1.5" opacity="0">
        <path className="sk-spark-a" d="M28 44 l5 12 12 5 -12 5 -5 12 -5 -12 -12 -5 12 -5 Z" />
        <path className="sk-spark-b" d="M196 22 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 Z" />
        <path className="sk-spark-c" d="M40 158 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 Z" />
      </g>

      {/* Static "…" so `thinking` still reads when motion is reduced. */}
      <g className="sk-thought" fill="#5b6b7c" opacity="0">
        <circle cx="182" cy="16" r="4" />
        <circle cx="196" cy="16" r="4" />
        <circle cx="210" cy="16" r="4" />
      </g>
    </svg>
  );
}
