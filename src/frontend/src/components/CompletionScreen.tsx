import { useEffect, useState } from "react";
import type { SockSkin } from "../sockSkin";
import { Sockrates } from "./Sockrates";

interface Props {
  onReveal: () => void;
  skin: SockSkin;
}

const CONFETTI = Array.from({ length: 40 }, (_, i) => i);

export function CompletionScreen({ onReveal, skin }: Props) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setReady(true), 1400);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="completion">
      <div className="confetti">
        {CONFETTI.map((i) => (
          <span
            key={i}
            style={{
              left: `${(i * 37) % 100}%`,
              animationDelay: `${(i % 10) * 0.14}s`,
              background: ["#ffd166", "#06d6a0", "#ef476f", "#118ab2"][i % 4],
            }}
          />
        ))}
      </div>
      <div className="completion-card">
        <Sockrates className="completion-mascot" skin={skin} mood="celebrating" size={132} />
        <h1>Sockrates is impressed!</h1>
        <p>You questioned a claim instead of just accepting it. That is the whole game.</p>
        <button type="button" onClick={onReveal} disabled={!ready}>
          {ready ? "See my report card" : "Sockrates is taking notes..."}
        </button>
      </div>
    </div>
  );
}
