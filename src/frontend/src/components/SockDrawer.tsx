import { SKIN_LABELS, SOCK_SKINS, isSkinLocked } from "../sockSkin";
import type { SockSkin } from "../sockSkin";
import { Sockrates } from "./Sockrates";

interface Props {
  skin: SockSkin;
  onPick: (skin: SockSkin) => void;
  /** Renders as a card floating under the chat header rather than inline. */
  popover?: boolean;
}

export function SockDrawer({ skin, onPick, popover = false }: Props) {
  const locked = isSkinLocked();

  return (
    <div
      role="group"
      aria-label="Pick Sockrates' sock"
      className={`sock-drawer${popover ? " popover" : ""}${locked ? " locked" : ""}`}
    >
      <span className="sock-drawer-label">{locked ? "Your class sock" : "Pick his sock"}</span>

      {SOCK_SKINS.map((option) => (
        <button
          key={option}
          type="button"
          className="sock-swatch"
          aria-pressed={option === skin}
          aria-label={SKIN_LABELS[option]}
          title={SKIN_LABELS[option]}
          disabled={locked}
          onClick={() => onPick(option)}
        >
          <Sockrates skin={option} mood="idle" size={38} />
        </button>
      ))}

      {locked && (
        <p className="sock-drawer-locked-note">Your teacher picked this one for the whole class.</p>
      )}
    </div>
  );
}
