import { useEffect, useRef, useState } from "react";
import type { Anchor, Message } from "../types";

interface Props {
  messages: Message[];
  openingPrompt: string;
  anchor: Anchor | null;
  onClearAnchor: () => void;
  onSend: (message: string) => void;
  turnsUsed: number;
  minTurns: number;
  maxTurns: number;
  busy: boolean;
  disabled: boolean;
  hints: string[];
  onHint: () => void;
  hintBusy: boolean;
  maxHintsPerTurn: number;
}

function anchorLabel(anchor: Anchor): string {
  if (anchor.kind === "text") return `"${anchor.quote?.slice(0, 60)}..."`;
  if (anchor.kind === "region") return "a spot on the chart";
  return `the clip at ${anchor.timestamp_s?.toFixed(0)}s`;
}

export function ChatPanel({
  messages,
  openingPrompt,
  anchor,
  onClearAnchor,
  onSend,
  turnsUsed,
  minTurns,
  maxTurns,
  busy,
  disabled,
  hints,
  onHint,
  hintBusy,
  maxHintsPerTurn,
}: Props) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, busy]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy || disabled) return;
    onSend(text);
    setDraft("");
  }

  return (
    <section className="chat-panel">
      <header className="chat-header">
        <h2>Think it through</h2>
        <div className="turn-track" title={`${minTurns}-${maxTurns} exchanges`}>
          {Array.from({ length: maxTurns }, (_, i) => (
            <span
              key={i}
              className={`dot ${i < turnsUsed ? "filled" : ""} ${i >= minTurns ? "optional" : ""}`}
            />
          ))}
          <span className="turn-label">
            {turnsUsed} of {maxTurns}
          </span>
        </div>
      </header>

      <div className="messages">
        <div className="bubble tutor opening">{openingPrompt}</div>
        {messages.map((message, index) => (
          <div key={index} className={`bubble ${message.role}`}>
            {message.anchorExcerpt && (
              <div className="anchor-tag">pointing at {message.anchorExcerpt}</div>
            )}
            {message.text}
          </div>
        ))}
        {hints.map((text, index) => (
          <div key={`hint-${index}`} className="bubble hint-bubble">
            <div className="hint-label">Hint {index + 1}</div>
            {text}
          </div>
        ))}
        {busy && (
          <div className="bubble tutor thinking">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="composer">
        {anchor && (
          <div className="anchor-chip">
            Pointing at {anchorLabel(anchor)}
            <button type="button" onClick={onClearAnchor} aria-label="Clear anchor">
              x
            </button>
          </div>
        )}
        <div className="composer-row">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) submit(event);
            }}
            placeholder={disabled ? "This conversation is complete." : "Ask a question about the report..."}
            disabled={busy || disabled}
            rows={2}
          />
          <button type="submit" disabled={busy || disabled || !draft.trim()}>
            Send
          </button>
        </div>
        <div className="hint-row">
          <button
            type="button"
            className="hint-button"
            onClick={onHint}
            disabled={busy || disabled || hintBusy || hints.length >= maxHintsPerTurn}
          >
            {hints.length === 0 ? "Need a hint?" : `Another hint (${hints.length}/${maxHintsPerTurn} used)`}
          </button>
          <span className="hint-cost">Hints can lower your score for this turn.</span>
        </div>
      </form>
    </section>
  );
}
