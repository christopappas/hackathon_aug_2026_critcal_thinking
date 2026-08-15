import type { AccessProfile, ContentSummary } from "../types";
import { AccessSettings } from "./AccessSettings";

interface Props {
  items: ContentSummary[];
  onPick: (id: string) => void;
  profile: AccessProfile;
  onProfileChange: (profile: AccessProfile) => void;
}

const ICONS: Record<string, string> = {
  "screen-time-scores": "📱",
  "energy-drink-ad": "🥤",
  "mars-headline": "🚀",
  "ai-code-review": "🤖",
  "study-music": "🎧",
};

export function ContentPicker({ items, onPick, profile, onProfileChange }: Props) {
  return (
    <div className="picker">
      <header className="picker-head">
        <h1>Think It Through</h1>
        <p>Pick something to question. You will talk it over, then get a thinking report card.</p>
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
