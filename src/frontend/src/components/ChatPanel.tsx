import { useEffect, useRef, useState } from "react";
import type { SockSkin } from "../sockSkin";
import type { Anchor, Message } from "../types";
import { useSockratesMood } from "../useSockratesMood";
import { SockDrawer } from "./SockDrawer";
import { Sockrates } from "./Sockrates";

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
  skin: SockSkin;
  onSkinChange: (skin: SockSkin) => void;
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
  skin,
  onSkinChange,
}: Props) {
  const [draft, setDraft] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const mood = useSockratesMood(messages, busy, hintBusy, hints.length, draft);

  useEffect(() => {
    // Smooth scrolling is driven by JS, so no media query reaches it.
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    endRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
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
      {/* .chat-header is justify-content: space-between, so the sock and the title
          are wrapped together to keep the row at exactly two children. */}
      <header className="chat-header">
        <div className="chat-title">
          <button
            type="button"
            className="sock-swap"
            aria-label="Change Sockrates' sock"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen((open) => !open)}
          >
            <Sockrates mood={mood} skin={skin} size={76} />
          </button>
          <h2>Sockrates</h2>
        </div>
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

      {drawerOpen && (
        <SockDrawer
          skin={skin}
          popover
          onPick={(next) => {
            onSkinChange(next);
            setDrawerOpen(false);
          }}
        />
      )}

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
