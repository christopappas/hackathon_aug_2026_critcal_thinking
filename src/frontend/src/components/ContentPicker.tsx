import type { ContentSummary } from "../types";

interface Props {
  items: ContentSummary[];
  onPick: (id: string) => void;
}

// Icons for the five built-in pieces. Generated content carries its own icon field,
// which takes precedence, so new pieces do not all show up as a question mark.
const ICONS: Record<string, string> = {
  "screen-time-scores": "📱",
  "energy-drink-ad": "🥤",
  "mars-headline": "🚀",
  "ai-code-review": "🤖",
  "study-music": "🎧",
};

export function ContentPicker({ items, onPick }: Props) {
  return (
    <div className="picker">
      <header className="picker-head">
        <h1>Think It Through</h1>
        <p>Pick something to question. You will talk it over, then get a thinking report card.</p>
      </header>

      <div className="picker-grid">
        {items.map((item) => (
          <button key={item.id} type="button" className="picker-card" onClick={() => onPick(item.id)}>
            <span className="picker-icon">{item.icon ?? ICONS[item.id] ?? "❓"}</span>
            <span className="picker-subject">{item.subject}</span>
            <h2>{item.title}</h2>
            <p>{item.blurb}</p>
            <span className="picker-go">Start →</span>
          </button>
        ))}
      </div>
    </div>
  );
}
