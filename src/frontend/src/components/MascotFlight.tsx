import { useLayoutEffect, useRef } from "react";
import type { SockSkin } from "../sockSkin";
import { Sockrates } from "./Sockrates";

interface Props {
  /** Where the mascot sat on the title card, measured at the moment Begin was hit. */
  from: DOMRect;
  skin: SockSkin;
  onDone: () => void;
}

const FLIGHT_MS = 520;

/**
 * Carries the giant title-card mascot into its slot in the picker header.
 *
 * This exists to solve a real problem rather than for decoration: the picker header
 * already renders the same mascot and the same "Sockrates" wordmark, so cutting
 * straight from the title card shows near-identical branding twice in a row and
 * reads as a stutter.
 *
 * Only `transform` is animated -- a translate plus a uniform scale about the
 * top-left corner, which maps one rect onto another exactly. Interpolating the
 * mascot's width/height instead would not work: `Sockrates` sets those inline from
 * its `size` prop, so they cannot be transitioned by a class swap.
 */
export function MascotFlight({ from, skin, onDone }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const finished = useRef(false);
  const launched = useRef(false);
  // Read through a ref so an unstable `onDone` from the parent cannot re-run the
  // effect and relaunch a flight that is already under way.
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useLayoutEffect(() => {
    const node = ref.current;
    // The picker renders in the same commit as this layer, and useLayoutEffect runs
    // after the DOM is mutated, so the destination is already measurable.
    const target = document.querySelector<HTMLElement>(".picker-mascot");

    const settle = () => {
      if (finished.current) return;
      finished.current = true;
      onDoneRef.current();
    };

    // transitionend BUBBLES, and the mascot's own parts (.sk-jaw, .sk-eyes,
    // .sk-pupils ...) each carry `transition: transform`. Without this guard a
    // child settling on mount ends the flight after a single frame, which looks
    // like a hard cut rather than a broken listener.
    const onEnd = (event: TransitionEvent) => {
      if (event.target === node && event.propertyName === "transform") settle();
    };

    // No destination, or motion is reduced: hand over immediately rather than
    // leaving a mascot parked mid-air.
    if (!node || !target || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      settle();
      return;
    }

    // Listeners are re-registered on every run, but the launch happens exactly once.
    // StrictMode invokes this effect twice in dev, and re-applying the start pose
    // mid-flight interrupts the running transition -- which fires `transitionend`
    // immediately and ends the flight after a single frame.
    if (!launched.current) {
      launched.current = true;
      const to = target.getBoundingClientRect();
      const scale = to.width / from.width;

      node.style.transform = `translate(${from.left}px, ${from.top}px) scale(1)`;
      void node.offsetWidth; // flush the start pose so the transition has a from-value
      node.style.transition = `transform ${FLIGHT_MS}ms cubic-bezier(0.5, 0, 0.2, 1)`;
      node.style.transform = `translate(${to.left}px, ${to.top}px) scale(${scale})`;
    }

    // transitionend does not fire if the transition is interrupted or never starts,
    // so the timer is what guarantees the picker's own mascot comes back.
    node.addEventListener("transitionend", onEnd);
    const backstop = window.setTimeout(settle, FLIGHT_MS + 160);
    return () => {
      node.removeEventListener("transitionend", onEnd);
      window.clearTimeout(backstop);
    };
    // Deliberately runs once: the flight is a one-shot launched at mount.
  }, [from]);

  return (
    <div
      className="mascot-flight"
      ref={ref}
      style={{ width: from.width, height: from.height }}
      aria-hidden="true"
    >
      <Sockrates skin={skin} mood="idle" size={from.width} />
    </div>
  );
}
