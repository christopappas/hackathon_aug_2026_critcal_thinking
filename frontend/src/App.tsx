import { useCallback, useEffect, useState } from "react";
import { fetchReport, sendMessage, startSession } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { CompletionScreen } from "./components/CompletionScreen";
import { ContentViewer } from "./components/ContentViewer";
import { ReportCard } from "./components/ReportCard";
import type { Anchor, Message, Report, SessionResponse } from "./types";

type Phase = "loading" | "chatting" | "celebrating" | "report" | "error";

export default function App() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [turnsUsed, setTurnsUsed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>("");

  const boot = useCallback(async () => {
    setPhase("loading");
    setMessages([]);
    setAnchor(null);
    setTurnsUsed(0);
    setReport(null);
    try {
      setSession(await startSession());
      setPhase("chatting");
    } catch (err) {
      setError(String(err));
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    void boot();
  }, [boot]);

  async function handleSend(text: string) {
    if (!session) return;
    const sent = anchor;
    setMessages((prev) => [...prev, { role: "student", text }]);
    setAnchor(null);
    setBusy(true);
    try {
      const response = await sendMessage(session.session_id, text, sent);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "student", text, anchorExcerpt: response.anchor_excerpt },
        { role: "tutor", text: response.reply },
      ]);
      setTurnsUsed(response.turns_used);
      if (response.is_complete) {
        const card = await fetchReport(session.session_id);
        setReport(card);
        setPhase("celebrating");
      }
    } catch (err) {
      setError(String(err));
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }

  if (phase === "loading") return <div className="center">Loading...</div>;
  if (phase === "error")
    return (
      <div className="center error">
        <p>{error}</p>
        <button type="button" onClick={() => void boot()}>
          Retry
        </button>
      </div>
    );
  if (phase === "celebrating")
    return <CompletionScreen onReveal={() => setPhase("report")} />;
  if (phase === "report" && report)
    return <ReportCard report={report} onRestart={() => void boot()} />;
  if (!session) return null;

  return (
    <div className="layout">
      <ContentViewer
        content={session.content}
        activeAnchor={anchor}
        onAnchor={setAnchor}
        disabled={busy}
      />
      <ChatPanel
        messages={messages}
        openingPrompt={session.opening_prompt}
        anchor={anchor}
        onClearAnchor={() => setAnchor(null)}
        onSend={(text) => void handleSend(text)}
        turnsUsed={turnsUsed}
        minTurns={session.min_turns}
        maxTurns={session.max_turns}
        busy={busy}
        disabled={false}
      />
    </div>
  );
}
