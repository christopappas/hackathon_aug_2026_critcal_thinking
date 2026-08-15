import { useCallback, useEffect, useState } from "react";
import {
  fetchReport,
  listContent,
  requestHint,
  sendExploreMessage,
  sendMessage,
  startExplore,
  startSession,
} from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { CompletionScreen } from "./components/CompletionScreen";
import { ContentPicker } from "./components/ContentPicker";
import { ContentViewer } from "./components/ContentViewer";
import { ExplorePopover } from "./components/ExplorePopover";
import { ReportCard } from "./components/ReportCard";
import { loadSkin, saveSkin } from "./sockSkin";
import type { SockSkin } from "./sockSkin";
import type { Anchor, ContentSummary, ExploreMessage, Message, Report, SessionResponse } from "./types";

type Phase = "loading" | "picking" | "chatting" | "celebrating" | "report" | "error";

interface ExplorePopupState {
  position: { x: number; y: number };
  anchorLabel: string;
  messages: ExploreMessage[];
  starting: boolean;
  busy: boolean;
  messagesUsed: number;
  maxMessages: number;
}

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
  const [hints, setHints] = useState<string[]>([]);
  const [maxHintsPerTurn, setMaxHintsPerTurn] = useState(3);
  const [hintBusy, setHintBusy] = useState(false);
  const [explore, setExplore] = useState<ExplorePopupState | null>(null);
  // Mood stays inside ChatPanel — lifting it would drag `draft` up here and
  // re-render ContentViewer on every keystroke. Only the skin is shared.
  const [skin, setSkin] = useState<SockSkin>(loadSkin);

  function chooseSkin(next: SockSkin) {
    setSkin(next);
    saveSkin(next);
  }

  const loadCatalog = useCallback(async () => {
    setPhase("loading");
    setSession(null);
    setMessages([]);
    setAnchor(null);
    setTurnsUsed(0);
    setReport(null);
    setHints([]);
    setExplore(null);
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
      setHints([]);
      setExplore(null);
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
      setHints([]);
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

  async function handleHint() {
    if (!session || hintBusy || busy) return;
    setHintBusy(true);
    try {
      const response = await requestHint(session.session_id, anchor);
      setHints((prev) => [...prev, response.hint]);
      setMaxHintsPerTurn(response.max_hints_per_turn);
    } catch (err) {
      setError(String(err));
      setPhase("error");
    } finally {
      setHintBusy(false);
    }
  }

  async function handleExplore(clickedAnchor: Anchor, position: { x: number; y: number }) {
    if (!session) return;
    // One popover at a time: opening a new spot replaces whatever was open.
    setExplore({
      position,
      anchorLabel: "",
      messages: [],
      starting: true,
      busy: false,
      messagesUsed: 0,
      maxMessages: 30,
    });
    try {
      const response = await startExplore(session.session_id, clickedAnchor);
      setExplore({
        position,
        anchorLabel: response.anchor_excerpt ?? "this part of the content",
        messages: [{ role: "tutor", text: response.opening }],
        starting: false,
        busy: false,
        messagesUsed: 0,
        maxMessages: response.max_messages,
      });
    } catch (err) {
      setError(String(err));
      setPhase("error");
    }
  }

  async function handleExploreSend(text: string) {
    if (!session || !explore) return;
    setExplore((prev) => (prev ? { ...prev, messages: [...prev.messages, { role: "student", text }], busy: true } : prev));
    try {
      const response = await sendExploreMessage(session.session_id, text);
      setExplore((prev) =>
        prev
          ? {
              ...prev,
              messages: [...prev.messages, { role: "tutor", text: response.reply }],
              messagesUsed: response.messages_used,
              maxMessages: response.max_messages,
              busy: false,
            }
          : prev,
      );
    } catch (err) {
      setError(String(err));
      setPhase("error");
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
    return (
      <ContentPicker
        items={catalog}
        onPick={(id) => void pickContent(id)}
        skin={skin}
        onSkinChange={chooseSkin}
      />
    );
  if (phase === "celebrating")
    return <CompletionScreen onReveal={() => setPhase("report")} skin={skin} />;
  if (phase === "report" && report)
    return <ReportCard report={report} onRestart={() => void loadCatalog()} skin={skin} />;
  if (!session) return null;

  return (
    <div className="layout">
      <ContentViewer
        content={session.content}
        activeAnchor={anchor}
        onAnchor={setAnchor}
        onExplore={(clickedAnchor, position) => void handleExplore(clickedAnchor, position)}
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
        hints={hints}
        onHint={() => void handleHint()}
        hintBusy={hintBusy}
        maxHintsPerTurn={maxHintsPerTurn}
        skin={skin}
        onSkinChange={chooseSkin}
      />
      {explore && (
        <ExplorePopover
          position={explore.position}
          anchorLabel={explore.anchorLabel}
          messages={explore.messages}
          busy={explore.busy}
          starting={explore.starting}
          messagesUsed={explore.messagesUsed}
          maxMessages={explore.maxMessages}
          onSend={(text) => void handleExploreSend(text)}
          onClose={() => setExplore(null)}
        />
      )}
    </div>
  );
}
