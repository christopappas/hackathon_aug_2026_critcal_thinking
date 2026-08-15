import { useCallback, useEffect, useState } from "react";
import {
  fetchHealth,
  fetchReport,
  listContent,
  requestHint,
  sendExploreMessage,
  sendMessage,
  setSessionLlmMode,
  startExplore,
  startSession,
} from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { CompletionScreen } from "./components/CompletionScreen";
import { ContentPicker } from "./components/ContentPicker";
import { ContentViewer } from "./components/ContentViewer";
import { ExplorePopover } from "./components/ExplorePopover";
import { LlmModeToggle } from "./components/LlmModeToggle";
import { MascotFlight } from "./components/MascotFlight";
import { ReportCard } from "./components/ReportCard";
import { TitleScreen } from "./components/TitleScreen";
import { setDyslexiaMotion } from "./motion";
import { loadSkin, saveSkin } from "./sockSkin";
import type { SockSkin } from "./sockSkin";
import type {
  AccessProfile,
  Anchor,
  ContentSummary,
  ExploreMessage,
  HealthResponse,
  LlmMode,
  Message,
  Report,
  SessionResponse,
} from "./types";

type Phase = "loading" | "picking" | "chatting" | "celebrating" | "report" | "error";

/** "flying" is the window where the title card and the picker are both on screen. */
type SplashStage = "showing" | "flying" | "done";

const PROFILE_KEY = "think-it-through:access-profile";
const LLM_MODE_KEY = "think-it-through:llm-mode";

function loadLlmMode(): LlmMode {
  try {
    const stored = localStorage.getItem(LLM_MODE_KEY);
    if (stored === "live" || stored === "stub") return stored;
  } catch {
    // Ignore unreadable storage; live is the right default when configured.
  }
  return "live";
}

function loadProfile(): AccessProfile {
  let profile: AccessProfile = { dyslexia_support: false };
  try {
    const stored = localStorage.getItem(PROFILE_KEY);
    if (stored) profile = JSON.parse(stored) as AccessProfile;
  } catch {
    // Ignore unreadable storage; the default profile is a safe fallback.
  }
  // Applied here rather than only in the profile effect: a student who set this
  // last session must not see the title screen animate before React's first
  // effect runs. The effect below keeps it in sync after any later toggle.
  setDyslexiaMotion(profile.dyslexia_support);
  return profile;
}

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
  const [profile, setProfile] = useState<AccessProfile>(loadProfile);
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
  const [llmMode, setLlmMode] = useState<LlmMode>(loadLlmMode);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  // Deliberately NOT a Phase member. `Phase` tracks the fetch/session machine, and
  // `loadCatalog` -- which is also the restart path -- resets it. Keeping the title
  // card on its own axis makes replay-on-restart impossible by construction rather
  // than merely avoided. App mounts once per page load, so this means exactly what
  // was asked for: a reload replays the card, nothing inside the app does.
  const [splash, setSplash] = useState<SplashStage>("showing");
  const [flightFrom, setFlightFrom] = useState<DOMRect | null>(null);

  function chooseSkin(next: SockSkin) {
    setSkin(next);
    saveSkin(next);
  }

  async function chooseLlmMode(next: LlmMode) {
    setLlmMode(next);
    try {
      localStorage.setItem(LLM_MODE_KEY, next);
    } catch {
      // A saved preference is a convenience; the session still gets the mode.
    }
    // An in-flight session holds its own mode server-side, so it has to be told.
    if (session) {
      try {
        await setSessionLlmMode(session.session_id, next);
        setSession({ ...session, llm_mode: next });
      } catch (err) {
        setError(String(err));
      }
    }
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

  // Whether a provider is reachable decides if 'Live' is offerable at all, so it
  // is read once from the server rather than guessed in the UI.
  useEffect(() => {
    fetchHealth()
      .then((result) => {
        setHealth(result);
        if (!result.llm_enabled) setLlmMode("stub");
      })
      .catch(() => setHealth(null));
  }, []);

  // Drive styling from one attribute on <html> so every screen -- picker, chat,
  // completion, report -- adapts without each component knowing about the profile.
  useEffect(() => {
    document.documentElement.dataset.access = profile.dyslexia_support ? "dyslexia" : "";
    // Typography and motion are separate concerns with separate triggers, so the
    // accommodation drives the shared motion attribute rather than its own rules.
    setDyslexiaMotion(profile.dyslexia_support);
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
    } catch {
      // A student can still work through the session without a saved preference.
    }
  }, [profile]);

  async function pickContent(contentId: string) {
    setPhase("loading");
    try {
      const created = await startSession(contentId, profile, llmMode);
      setSession(created);
      // The server downgrades to stub when nothing is configured; follow it so the
      // dropdown shows what is actually running, not what was asked for.
      setLlmMode(created.llm_mode);
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

  // One chrome wrapper for every screen: the mode has to be visible and switchable
  // during the conversation, not just before it starts.
  const withChrome = (screen: React.ReactNode) => (
    <>
      <LlmModeToggle
        mode={llmMode}
        onChange={(next) => void chooseLlmMode(next)}
        llmEnabled={health?.llm_enabled ?? false}
        model={health?.model ?? ""}
        busy={busy || hintBusy}
      />
      {screen}
    </>
  );

  // The phase chain is a function purely so the title card can overlay it during
  // the handoff, when the picker and the title card are both on screen. It is only
  // called once the card is on its way out, which is also what keeps the mode
  // toggle off the title screen.
  function renderPhase() {
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
      return withChrome(
        <ContentPicker
          items={catalog}
          onPick={(id) => void pickContent(id)}
          profile={profile}
          onProfileChange={setProfile}
          skin={skin}
          onSkinChange={chooseSkin}
          hideMascot={splash === "flying"}
        />,
      );
    if (phase === "celebrating")
      return withChrome(<CompletionScreen onReveal={() => setPhase("report")} skin={skin} />);
    if (phase === "report" && report)
      return withChrome(
        <ReportCard report={report} onRestart={() => void loadCatalog()} skin={skin} />,
      );
    if (!session) return null;

    return withChrome(
      <div className="layout">
      <ContentViewer
        content={session.content}
        activeAnchor={anchor}
        onAnchor={setAnchor}
        onExplore={(clickedAnchor, position) => void handleExplore(clickedAnchor, position)}
        disabled={busy}
        dyslexiaMode={session.access_profile?.dyslexia_support}
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

  return (
    <>
      {/* Held back until the handoff so the picker never flashes behind the card. */}
      {splash !== "showing" && renderPhase()}
      {splash !== "done" && (
        <TitleScreen
          skin={skin}
          onSkinChange={chooseSkin}
          leaving={splash === "flying"}
          onBegin={(mascot) => {
            setFlightFrom(mascot);
            setSplash("flying");
          }}
        />
      )}
      {splash === "flying" && flightFrom && (
        <MascotFlight from={flightFrom} skin={skin} onDone={() => setSplash("done")} />
      )}
    </>
  );
}
