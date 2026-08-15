import { useEffect, useState } from "react";

interface Props {
  onReveal: () => void;
}

const CONFETTI = Array.from({ length: 40 }, (_, i) => i);

export function CompletionScreen({ onReveal }: Props) {
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
        <div className="badge">✦</div>
        <h1>You thought it through!</h1>
        <p>You questioned a claim instead of just accepting it. That is the whole game.</p>
        <button type="button" onClick={onReveal} disabled={!ready}>
          {ready ? "See my report card" : "Scoring your thinking..."}
        </button>
      </div>
    </div>
  );
}
