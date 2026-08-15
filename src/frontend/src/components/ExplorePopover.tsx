import { useEffect, useRef, useState } from "react";
import type { ExploreMessage } from "../types";

interface Props {
  position: { x: number; y: number };
  anchorLabel: string;
  messages: ExploreMessage[];
  busy: boolean;
  starting: boolean;
  messagesUsed: number;
  maxMessages: number;
  onSend: (message: string) => void;
  onClose: () => void;
}

const WIDTH = 340;
const MAX_HEIGHT = 420;

function clampedStyle(position: { x: number; y: number }): React.CSSProperties {
  const left = Math.min(Math.max(12, position.x), window.innerWidth - WIDTH - 12);
  const top = Math.min(Math.max(12, position.y), window.innerHeight - 160 - 12);
  return { left, top };
}

export function ExplorePopover({
  position,
  anchorLabel,
  messages,
  busy,
  starting,
  messagesUsed,
  maxMessages,
  onSend,
  onClose,
}: Props) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const atCap = messagesUsed >= maxMessages;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, busy]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy || starting || atCap) return;
    onSend(text);
    setDraft("");
  }

  return (
    <div className="explore-popover" style={{ width: WIDTH, maxHeight: MAX_HEIGHT, ...clampedStyle(position) }}>
      <header className="explore-header">
        <div>
          <div className="explore-eyebrow">Let's talk about this</div>
          <div className="explore-anchor">{anchorLabel}</div>
        </div>
        <button type="button" className="explore-close" onClick={onClose} aria-label="Close discussion">
          x
        </button>
      </header>

      <div className="explore-messages">
        {starting && (
          <div className="bubble tutor thinking">
            <span />
            <span />
            <span />
          </div>
        )}
        {messages.map((message, index) => (
          <div key={index} className={`bubble ${message.role}`}>
            {message.text}
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

      <form onSubmit={submit} className="explore-composer">
        {atCap ? (
          <p className="explore-cap-note">You've reached the discussion limit for this spot.</p>
        ) : (
          <div className="composer-row">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) submit(event);
              }}
              placeholder="Say what you're thinking..."
              disabled={busy || starting}
              rows={2}
            />
            <button type="submit" disabled={busy || starting || !draft.trim()}>
              Send
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
