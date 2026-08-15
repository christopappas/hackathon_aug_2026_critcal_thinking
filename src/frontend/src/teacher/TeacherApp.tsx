import { useCallback, useEffect, useState } from "react";
import {
  deleteContent,
  generateContent,
  getTeacherContent,
  importContent,
  listCompletions,
  listTeacherContent,
  listTemplates,
  publishContent,
  unpublishContent,
} from "../api";
import type {
  CompletionsResponse,
  GeneratedContent,
  GenerateRequest,
  TeacherContentRow,
  Template,
} from "../types";
import { CompletionsTable } from "./CompletionsTable";
import { ContentTable } from "./ContentTable";
import { DraftPreview } from "./DraftPreview";
import { GenerateForm } from "./GenerateForm";
import { ImportForm } from "./ImportForm";
import { TemplateGallery } from "./TemplateGallery";

// Same shape as App.tsx: a phase union with sequential early returns, no router.
type Phase =
  | "loading"
  | "home"
  | "editing"
  | "importing"
  | "previewing"
  | "completions"
  | "error";

export default function TeacherApp() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [templates, setTemplates] = useState<Template[]>([]);
  const [rows, setRows] = useState<TeacherContentRow[]>([]);
  const [template, setTemplate] = useState<Template | null>(null);
  const [draft, setDraft] = useState<GeneratedContent | null>(null);
  const [completions, setCompletions] = useState<CompletionsResponse | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [trap, setTrap] = useState("");
  const [usedLlm, setUsedLlm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [loadedTemplates, loadedRows] = await Promise.all([
        listTemplates(),
        listTeacherContent(),
      ]);
      setTemplates(loadedTemplates);
      setRows(loadedRows);
      setPhase("home");
    } catch (err) {
      setError(String(err));
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleGenerate(request: GenerateRequest) {
    setBusy(true);
    setError("");
    try {
      const result = await generateContent(request);
      setDraft(result.content);
      setWarnings(result.warnings);
      setTrap(result.thinking_trap);
      setUsedLlm(result.generated_with_llm);
      setPhase("previewing");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleImport(payload: unknown) {
    setBusy(true);
    setError("");
    try {
      const result = await importContent(payload);
      setDraft(result.content);
      setWarnings(result.warnings);
      setTrap(result.thinking_trap);
      setUsedLlm(false);
      setTemplate(null);
      setPhase("previewing");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function act(work: () => Promise<unknown>) {
    setBusy(true);
    try {
      await work();
      await refresh();
    } catch (err) {
      setError(String(err));
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }

  async function handleShowCompletions() {
    setBusy(true);
    setError("");
    try {
      // Fetched on entry rather than with the rest of the portal: the dashboard is a
      // side trip, and the content manager should not wait on it to render.
      setCompletions(await listCompletions());
      setPhase("completions");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handlePreviewExisting(id: string) {
    setBusy(true);
    try {
      const content = await getTeacherContent(id);
      setDraft(content);
      setWarnings([]);
      setTrap(content.thinking_trap ?? "");
      setUsedLlm(content.source?.generated_with_llm ?? false);
      setPhase("previewing");
    } catch (err) {
      setError(String(err));
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }

  const nav = (
    <TeacherNav
      active={phase === "completions" ? "completions" : "content"}
      busy={busy}
      onHome={() => setPhase("home")}
      onCompletions={() => void handleShowCompletions()}
    />
  );

  if (phase === "loading") return <div className="center">Loading…</div>;
  if (phase === "error")
    return (
      <div className="center error">
        <p>{error}</p>
        <button type="button" onClick={() => void refresh()}>
          Retry
        </button>
      </div>
    );

  if (phase === "editing" && template)
    return (
      <div className="teacher">
        {nav}
        {error && <p className="notice error">{error}</p>}
        <GenerateForm
          template={template}
          busy={busy}
          onGenerate={(request) => void handleGenerate(request)}
          onBack={() => setPhase("home")}
        />
      </div>
    );

  if (phase === "importing")
    return (
      <div className="teacher">
        {nav}
        {error && <p className="notice error">{error}</p>}
        <ImportForm
          busy={busy}
          onImport={(payload) => void handleImport(payload)}
          onBack={() => setPhase("home")}
        />
      </div>
    );

  if (phase === "completions" && completions)
    return (
      <div className="teacher">
        {nav}
        {error && <p className="notice error">{error}</p>}
        <CompletionsTable data={completions} onBack={() => setPhase("home")} />
      </div>
    );

  if (phase === "previewing" && draft)
    return (
      <div className="teacher">
        {nav}
        <DraftPreview
          content={draft}
          warnings={warnings}
          thinkingTrap={trap}
          generatedWithLlm={usedLlm}
          busy={busy}
          onPublish={() =>
            void act(async () => {
              await publishContent(draft.id);
              setPhase("home");
            })
          }
          onDiscard={() =>
            void act(async () => {
              await deleteContent(draft.id);
              setDraft(null);
              setPhase("home");
            })
          }
          onBack={() => setPhase(template ? "editing" : "home")}
        />
      </div>
    );

  return (
    <div className="teacher">
      {nav}
      {error && <p className="notice error">{error}</p>}
      <TemplateGallery
        templates={templates}
        onPick={(picked) => {
          setTemplate(picked);
          setError("");
          setPhase("editing");
        }}
        onImport={() => {
          setError("");
          setPhase("importing");
        }}
      />
      <ContentTable
        rows={rows}
        busy={busy}
        onPreview={(id) => void handlePreviewExisting(id)}
        onPublish={(id) => void act(() => publishContent(id))}
        onUnpublish={(id) => void act(() => unpublishContent(id))}
        onDelete={(id) => void act(() => deleteContent(id))}
      />
    </div>
  );
}

function TeacherNav({
  active,
  busy,
  onHome,
  onCompletions,
}: {
  active: "content" | "completions";
  busy: boolean;
  onHome: () => void;
  onCompletions: () => void;
}) {
  return (
    <nav className="teacher-nav">
      <strong>Sockrates — teacher portal</strong>
      <div className="teacher-nav-links">
        <button
          type="button"
          className={`nav-link${active === "content" ? " current" : ""}`}
          aria-current={active === "content" ? "page" : undefined}
          onClick={onHome}
        >
          Content
        </button>
        <button
          type="button"
          className={`nav-link${active === "completions" ? " current" : ""}`}
          aria-current={active === "completions" ? "page" : undefined}
          disabled={busy}
          onClick={onCompletions}
        >
          Completions
        </button>
        <a href="/">Open the student view →</a>
      </div>
    </nav>
  );
}
