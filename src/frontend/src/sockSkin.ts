/**
 * Sockrates' wardrobe.
 *
 * A skin is chosen once and reused on every screen, so it lives in App state and
 * is persisted per browser. A teacher can pin one sock for a whole class by
 * sharing a `?sock=<skin>` link, which outranks the student's own choice.
 */

export const SOCK_SKINS = [
  "athletic",
  "rugby",
  "argyle",
  "polka",
  "tiedye",
  "rainbow",
  "toga",
] as const;

export type SockSkin = (typeof SOCK_SKINS)[number];

export const SKIN_LABELS: Record<SockSkin, string> = {
  athletic: "Gym sock",
  rugby: "Rugby stripes",
  argyle: "Argyle",
  polka: "Polka dots",
  tiedye: "Tie-dye",
  rainbow: "Rainbow",
  toga: "Marble toga",
};

const KEY = "sockrates.skin";

function isSkin(value: unknown): value is SockSkin {
  return typeof value === "string" && (SOCK_SKINS as readonly string[]).includes(value);
}

function forcedSkin(): string | null {
  return new URLSearchParams(window.location.search).get("sock");
}

/** Precedence: ?sock= (teacher link) > localStorage (student) > default. */
export function loadSkin(): SockSkin {
  const forced = forcedSkin();
  if (isSkin(forced)) return forced;
  try {
    const stored = localStorage.getItem(KEY);
    if (isSkin(stored)) return stored;
  } catch {
    // Safari private browsing throws rather than returning null.
  }
  return "athletic";
}

export function saveSkin(skin: SockSkin) {
  try {
    localStorage.setItem(KEY, skin);
  } catch {
    // Not being able to remember the sock is not worth crashing the picker over.
  }
}

/** True when a `?sock=` link pinned the skin, so the drawer should be read only. */
export function isSkinLocked(): boolean {
  return isSkin(forcedSkin());
}
