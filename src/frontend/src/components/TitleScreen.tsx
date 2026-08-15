import { useEffect, useRef, useState } from "react";
import { motionIsReduced } from "../motion";
import { SOCK_SKINS } from "../sockSkin";
import type { SockSkin } from "../sockSkin";
import { useCursorEyes } from "../useCursorEyes";
import { Sockrates } from "./Sockrates";
import type { SockratesMood } from "./Sockrates";

interface Props {
  skin: SockSkin;
  onBegin: (mascot: DOMRect) => void;
  onSkinChange: (skin: SockSkin) => void;
  leaving: boolean;
}

/** One is picked per page load, so back-to-back demo runs never open the same way. */
const GREETINGS = [
  "I am Sockrates. I have questions.",
  "Do not believe me either.",
  "A sock? Yes. And yet — questions.",
  "Ah, a thinker. Let us find out.",
  "I know only that I am a sock.",
];

const ENTRANCE_MS = 1050;
const GREETING_MS = 2200;
const POKE_MS = 900;
/** Two pokes inside this window count as consecutive. */
const POKE_WINDOW_MS = 1200;
const RIFFLE_STEP_MS = 110;
const POKES_FOR_RIFFLE = 5;

/** Big, but never wider than the viewport it has to skid across. */
function mascotSizeFor(width: number, height: number) {
  return Math.round(Math.max(150, Math.min(420, width * 0.42, height * 0.46)));
}

export function TitleScreen({ skin, onBegin, onSkinChange, leaving }: Props) {
  const reduceMotion = motionIsReduced();

  // Seeded from the media query: with motion reduced there is no animation, so
  // `animationend` never fires and a `false` seed would hang the entrance forever.
  const [settled, setSettled] = useState(reduceMotion);
  const [greeting, setGreeting] = useState(false);
  const [mood, setMood] = useState<SockratesMood>("idle");
  const [riffleSkin, setRiffleSkin] = useState<SockSkin | null>(null);
  const [size, setSize] = useState(() => mascotSizeFor(window.innerWidth, window.innerHeight));
  const [line] = useState(() => GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);

  const mascotRef = useRef<HTMLDivElement>(null);
  const pokes = useRef(0);
  const pokeAt = useRef(0);
  const timers = useRef<number[]>([]);

  useCursorEyes(mascotRef, !reduceMotion && !leaving);

  /** Every timer goes through here so one cleanup can cancel all of them. */
  function later(fn: () => void, ms: number) {
    const id = window.setTimeout(fn, ms);
    timers.current.push(id);
    return id;
  }

  useEffect(() => {
    const running = timers.current;
    return () => {
      running.forEach(window.clearTimeout);
      running.length = 0;
    };
  }, []);

  useEffect(() => {
    const onResize = () => setSize(mascotSizeFor(window.innerWidth, window.innerHeight));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Two independent paths onto one idempotent boolean. `animationend` alone is not
  // enough: it never fires for a backgrounded tab or a browser that drops the
  // animation, and the entrance would stay un-settled with no way to skip.
  useEffect(() => {
    const timer = later(() => setSettled(true), ENTRANCE_MS + 120);
    const skip = () => setSettled(true);
    window.addEventListener("keydown", skip);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", skip);
    };
  }, []);

  // He speaks once he has stopped moving.
  useEffect(() => {
    if (!settled || greeting) return;
    later(() => setGreeting(true), reduceMotion ? 0 : 180);
  }, [settled, greeting, reduceMotion]);

  useEffect(() => {
    if (!greeting) return;
    setMood("talking");
    const timer = later(() => setMood("idle"), GREETING_MS);
    return () => window.clearTimeout(timer);
  }, [greeting]);

  function poke() {
    setSettled(true); // poking mid-skid should also land him

    const now = Date.now();
    pokes.current = now - pokeAt.current < POKE_WINDOW_MS ? pokes.current + 1 : 1;
    pokeAt.current = now;

    if (pokes.current < POKES_FOR_RIFFLE) {
      setMood("impressed");
      later(() => setMood("idle"), POKE_MS);
      return;
    }

    // Easter egg: riffle the whole drawer and land somewhere random. Held in local
    // state so only the final sock is committed and written to storage.
    pokes.current = 0;
    setMood("impressed");
    const landing = Math.floor(Math.random() * SOCK_SKINS.length);
    SOCK_SKINS.forEach((option, index) => {
      later(() => setRiffleSkin(option), index * RIFFLE_STEP_MS);
    });
    later(() => {
      setRiffleSkin(null);
      onSkinChange(SOCK_SKINS[landing]);
      setMood("idle");
    }, SOCK_SKINS.length * RIFFLE_STEP_MS + 120);
  }

  const className = [
    "title-screen",
    settled ? "is-settled" : "",
    leaving ? "is-leaving" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className} onClick={() => setSettled(true)}>
      <div className="title-stage">
        <div
          className="title-mascot"
          ref={mascotRef}
          onAnimationEnd={(event) => {
            // The mascot's own mood animations are infinite and never emit this,
            // but the guard costs nothing and survives someone adding a finite one.
            if (event.target === event.currentTarget) setSettled(true);
          }}
        >
          <button type="button" className="title-poke" onClick={poke} aria-label="Poke Sockrates">
            <Sockrates skin={riffleSkin ?? skin} mood={mood} size={size} />
          </button>
          {greeting && (
            <p className="title-speech" role="status">
              {line}
            </p>
          )}
        </div>

        <button
          type="button"
          className="title-begin"
          autoFocus
          onClick={() => {
            const box = mascotRef.current?.getBoundingClientRect();
            if (box) onBegin(box);
          }}
        >
          Begin →
        </button>
      </div>

      <h1 className="title-wordmark">Sockrates</h1>
    </div>
  );
}
