import { useEffect } from "react";
import type { RefObject } from "react";

/** Furthest the pupils travel from centre. See the viewBox-units note below. */
const REACH_X = 6;
const REACH_Y = 5;

/** The eyes sit high in the 220-unit viewBox, not at the mascot's centre. */
const EYE_LINE = 0.32;

const clamp = (value: number) => (value < -1 ? -1 : value > 1 ? 1 : value);

/**
 * Makes Sockrates' pupils follow the pointer.
 *
 * The transform is written straight to the node and throttled to one write per
 * frame. Routing this through React state would re-render the whole title card on
 * every pointer move, which is a lot of work to shift two circles.
 *
 * Two things this depends on, both easy to break:
 *
 * - `.sk-pupils` must not be under a running CSS animation. The `idle` mood
 *   animates it with `sk-wander`, and a running animation outranks inline style,
 *   so the pupils would silently ignore the pointer. `styles.css` disables it for
 *   the title card specifically.
 * - `transform-box: view-box` is already set on `.sk-pupils`, so the values below
 *   are viewBox units in a 220-unit space, NOT CSS pixels. That is why the reach
 *   is the same number at 420px as it would be at 44px.
 *
 * The pupils are found with `querySelector` rather than a ref threaded through
 * `<Sockrates>`: adding a prop would change the shared rig's surface for its five
 * other call sites, and the null guard means a future markup change degrades to
 * "no eye tracking" rather than a crash.
 */
export function useCursorEyes(hostRef: RefObject<HTMLElement | null>, enabled: boolean) {
  useEffect(() => {
    if (!enabled) return;

    const host = hostRef.current;
    const pupils = host?.querySelector<SVGGElement>(".sk-pupils");
    if (!host || !pupils) return;

    let frame = 0;
    let pointerX = 0;
    let pointerY = 0;

    const apply = () => {
      frame = 0;
      // Measured every frame rather than cached: during the skid the host is still
      // moving, and a live rect keeps him looking at you the whole way in.
      const box = host.getBoundingClientRect();
      if (!box.width || !box.height) return;
      const x = clamp((pointerX - (box.left + box.width / 2)) / (box.width / 2));
      const y = clamp((pointerY - (box.top + box.height * EYE_LINE)) / (box.height / 2));
      pupils.style.transform = `translate(${(x * REACH_X).toFixed(2)}px, ${(y * REACH_Y).toFixed(2)}px)`;
    };

    // `pointermove` rather than `mousemove` so the eyes also work on a tablet demo.
    const onMove = (event: PointerEvent) => {
      pointerX = event.clientX;
      pointerY = event.clientY;
      if (!frame) frame = requestAnimationFrame(apply);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (frame) cancelAnimationFrame(frame);
      pupils.style.removeProperty("transform"); // hand the pose back to CSS
    };
  }, [hostRef, enabled]);
}
