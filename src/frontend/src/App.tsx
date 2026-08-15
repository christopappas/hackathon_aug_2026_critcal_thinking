import { useCallback, useEffect, useState } from "react";
import { fetchReport, listContent, sendMessage, startSession } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { CompletionScreen } from "./components/CompletionScreen";
import { ContentPicker } from "./components/ContentPicker";
import { ContentViewer } from "./components/ContentViewer";
import { ReportCard } from "./components/ReportCard";
import type { Anchor, ContentSummary, Message, Report, SessionResponse } from "./types";

type Phase = "loading" | "picking" | "chatting" | "celebrating" | "report" | "error";

export default function App() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [catalog, setCatalog] = useState<ContentSummary[]>([]);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [turnsUsed, setTurnsUsed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>("");

  const loadCatalog = useCallback(async () => {
    setPhase("loading");
    setSession(null);
    setMessages([]);
    setAnchor(null);
    setTurnsUsed(0);
    setReport(null);
    try {
      setCatalog(await listContent());
      setPhase("picking");
    } catch (err) {
      setError(String(err));
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  async function pickContent(contentId: string) {
    setPhase("loading");
    try {
      setSession(await startSession(contentId));
      setMessages([]);
      setAnchor(null);
      setTurnsUsed(0);
      setPhase("chatting");
    } catch (err) {
      setError(String(err));
      setPhase("error");
    }
  }

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
        <button type="button" onClick={() => void loadCatalog()}>
          Retry
        </button>
      </div>
    );
  if (phase === "picking")
    return <ContentPicker items={catalog} onPick={(id) => void pickContent(id)} />;
  if (phase === "celebrating")
    return <CompletionScreen onReveal={() => setPhase("report")} />;
  if (phase === "report" && report)
    return <ReportCard report={report} onRestart={() => void loadCatalog()} />;
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
