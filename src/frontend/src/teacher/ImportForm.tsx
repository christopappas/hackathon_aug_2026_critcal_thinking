import { useEffect, useState } from "react";
import { fetchImportSchema } from "../api";

interface Props {
  busy: boolean;
  onImport: (payload: unknown) => void;
  onBack: () => void;
}

/**
 * For content written somewhere else -- by hand, or by asking a model in a chat window
 * for a payload in this shape. It goes through the same renderer, validator, and draft
 * gate as anything generated in the app.
 */
export function ImportForm({ busy, onImport, onBack }: Props) {
  const [text, setText] = useState("");
  const [shape, setShape] = useState("");
  const [showShape, setShowShape] = useState(false);
  const [parseError, setParseError] = useState("");

  useEffect(() => {
    fetchImportSchema()
      .then((result) => setShape(result.shape))
      .catch(() => setShape(""));
  }, []);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    try {
      const parsed = JSON.parse(text);
      setParseError("");
      onImport(parsed);
    } catch (err) {
      setParseError(`That is not valid JSON: ${String(err)}`);
    }
  }

  return (
    <form className="teacher-form" onSubmit={submit}>
      <div className="teacher-bar">
        <button type="button" className="link" onClick={onBack}>
          ← All templates
        </button>
      </div>

      <h1>📥 Import a piece</h1>
      <p className="hint">
        Paste a content payload written elsewhere. Give the chart either a{" "}
        <code>chart</code> spec, in which case the click regions are worked out from it, or
        your own <code>chart_svg</code> plus <code>chart_regions</code>, in which case you
        line them up yourself and check them in the preview.
      </p>

      <div className="field">
        <button type="button" className="link" onClick={() => setShowShape((open) => !open)}>
          {showShape ? "Hide" : "Show"} the payload shape
        </button>
        {showShape && <pre className="payload-shape">{shape || "Loading…"}</pre>}
      </div>

      <label className="field">
        <span>Payload JSON</span>
        <textarea
          rows={16}
          className="prompt-editor"
          value={text}
          placeholder='{ "title": "...", "body": "...", "chart": { "kind": "bar", ... } }'
          onChange={(e) => setText(e.target.value)}
        />
      </label>

      {parseError && <p className="notice error">{parseError}</p>}

      <button type="submit" className="primary" disabled={busy || !text.trim()}>
        {busy ? "Importing…" : "Import as a draft"}
      </button>
    </form>
  );
}
