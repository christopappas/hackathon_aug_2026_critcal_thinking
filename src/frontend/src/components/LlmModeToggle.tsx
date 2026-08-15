import type { LlmMode } from "../types";

interface Props {
  mode: LlmMode;
  onChange: (mode: LlmMode) => void;
  llmEnabled: boolean;
  model: string;
  busy?: boolean;
}

/**
 * Switch between the live provider and the scripted stub, mid-session if needed.
 *
 * The live option is disabled outright when no provider is configured, rather
 * than offered and quietly ignored: the whole reason this control exists is that
 * "am I talking to a real model right now?" was previously unanswerable from the
 * screen, and a lying dropdown would be worse than none.
 */
export function LlmModeToggle({ mode, onChange, llmEnabled, model, busy }: Props) {
  const liveLabel = llmEnabled ? `Live - ${model}` : "Live - not configured";

  return (
    <div className="llm-mode-bar">
      <label htmlFor="llm-mode">Brain</label>
      <select
        id="llm-mode"
        value={mode}
        disabled={busy}
        onChange={(event) => onChange(event.target.value as LlmMode)}
      >
        <option value="live" disabled={!llmEnabled}>
          {liveLabel}
        </option>
        <option value="stub">Mock - scripted replies</option>
      </select>
      <span className={`llm-mode-dot ${mode === "live" ? "live" : "stub"}`} aria-hidden="true" />
      <span className="sr-only">
        {mode === "live" ? `Live model ${model}` : "Mock mode, scripted replies"}
      </span>
    </div>
  );
}
