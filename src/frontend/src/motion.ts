/**
 * Motion preference, resolved to one attribute on <html>.
 *
 * Two independent things ask for calmer motion: the OS `prefers-reduced-motion`
 * setting, and the dyslexia reading accommodation (issue #6), where animation
 * competes for attention while decoding text. Rather than let each grow its own
 * set of CSS overrides -- which is how dyslexia mode ended up with a blanket
 * `animation-duration: 0.001s`, turning every animation into a ~1000fps vibration
 * -- both feed this one `data-motion` attribute, and styles.css defines the
 * behaviour exactly once.
 *
 * That shared block does not simply kill animation: Sockrates' mood is the app's
 * only channel for thinking/listening/talking, so each mood is pinned to a static
 * pose instead. See the "Reduced motion" section of styles.css.
 */

const query = window.matchMedia("(prefers-reduced-motion: reduce)");

let dyslexia = false;

function apply() {
  document.documentElement.dataset.motion = dyslexia || query.matches ? "reduced" : "full";
}

/**
 * Mirror the educator's dyslexia toggle into the motion preference.
 * Safe to call on every render of the profile effect -- it only writes an attribute.
 */
export function setDyslexiaMotion(on: boolean) {
  dyslexia = on;
  apply();
}

/**
 * The same answer the CSS gets, for the motion that only JavaScript controls --
 * smooth scrolling and the title screen's timed sequence. Read this instead of
 * calling matchMedia directly, or the dyslexia accommodation gets silently skipped.
 */
export function motionIsReduced() {
  return dyslexia || query.matches;
}

/**
 * Call once from main.tsx *before* the first render, so a user who has asked their
 * OS for reduced motion never sees a frame of animation while React mounts.
 */
export function initMotionPreference() {
  query.addEventListener("change", apply);
  apply();
}
