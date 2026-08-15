import type { SockSkin } from "../sockSkin";
import type { AccessProfile, ContentSummary } from "../types";
import { AccessSettings } from "./AccessSettings";
import { SockDrawer } from "./SockDrawer";
import { Sockrates } from "./Sockrates";

interface Props {
  items: ContentSummary[];
  onPick: (id: string) => void;
  profile: AccessProfile;
  onProfileChange: (profile: AccessProfile) => void;
  skin: SockSkin;
  onSkinChange: (skin: SockSkin) => void;
}

const ICONS: Record<string, string> = {
  "screen-time-scores": "📱",
  "energy-drink-ad": "🥤",
  "mars-headline": "🚀",
  "ai-code-review": "🤖",
  "study-music": "🎧",
};

export function ContentPicker({ items, onPick, profile, onProfileChange, skin, onSkinChange }: Props) {
  return (
    <div className="picker">
      <header className="picker-head">
        <Sockrates
          className="picker-mascot"
          skin={skin}
          mood="idle"
          size={150}
          title="Sockrates, a sock puppet philosopher"
        />
        <h1>Sockrates</h1>
        <p>
          A sock with questions. Pick something to question — he will ask you why, then hand you a
          thinking report card.
        </p>
        <SockDrawer skin={skin} onPick={onSkinChange} />
      </header>

      <div className="picker-grid">
        {items.map((item) => (
          <button key={item.id} type="button" className="picker-card" onClick={() => onPick(item.id)}>
            <span className="picker-icon">{ICONS[item.id] ?? "❓"}</span>
            <span className="picker-subject">{item.subject}</span>
            <h2>{item.title}</h2>
            <p>{item.blurb}</p>
            <span className="picker-go">Start →</span>
          </button>
        ))}
      </div>

      <AccessSettings profile={profile} onChange={onProfileChange} />
    </div>
  );
}
