import { useState } from "react";
import type { GenerateRequest, Template } from "../types";

interface Props {
  template: Template;
  busy: boolean;
  onGenerate: (request: GenerateRequest) => void;
  onBack: () => void;
}

export function GenerateForm({ template, busy, onGenerate, onBack }: Props) {
  const [topic, setTopic] = useState("");
  const [gradeLevel, setGradeLevel] = useState(6);
  const [instructions, setInstructions] = useState(template.generation_instructions);
  const [extra, setExtra] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [showInstructions, setShowInstructions] = useState(false);

  const dirty = instructions !== template.generation_instructions;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!topic.trim() || busy) return;
    onGenerate({
      template_id: template.id,
      topic: topic.trim(),
      grade_level: gradeLevel,
      generation_instructions: instructions,
      extra_instructions: extra.trim(),
      source_text: sourceText.trim(),
    });
  }

  return (
    <form className="teacher-form" onSubmit={submit}>
      <div className="teacher-bar">
        <button type="button" className="link" onClick={onBack}>
          ← All templates
        </button>
        <span className="chip warn">{template.trap}</span>
      </div>

      <h1>
        {template.icon} {template.name}
      </h1>
      <p className="hint">{template.description}</p>

      <label className="field">
        <span>What should it be about?</span>
        <input
          type="text"
          value={topic}
          maxLength={200}
          placeholder="e.g. a new energy bar sold in the cafeteria"
          onChange={(e) => setTopic(e.target.value)}
          autoFocus
        />
      </label>

      <label className="field">
        <span>Reading level</span>
        <select value={gradeLevel} onChange={(e) => setGradeLevel(Number(e.target.value))}>
          {[4, 5, 6, 7, 8].map((grade) => (
            <option key={grade} value={grade}>
              Grade {grade}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Anything else to include?</span>
        <textarea
          rows={2}
          value={extra}
          maxLength={2000}
          placeholder="Optional. e.g. tie it to our unit on averages"
          onChange={(e) => setExtra(e.target.value)}
        />
      </label>

      <label className="field">
        <span>Paste source material</span>
        <textarea
          rows={4}
          value={sourceText}
          maxLength={6000}
          placeholder="Optional. Paste a passage from your textbook or a news story to draw facts from."
          onChange={(e) => setSourceText(e.target.value)}
        />
        <small className="hint">
          Do not paste student work, names, or anything else that identifies a person.
        </small>
      </label>

      <div className="field">
        <button
          type="button"
          className="link"
          onClick={() => setShowInstructions((open) => !open)}
        >
          {showInstructions ? "Hide" : "Edit"} the prompt this template uses
          {dirty ? " (edited)" : ""}
        </button>
        {showInstructions && (
          <>
            <textarea
              rows={12}
              className="prompt-editor"
              value={instructions}
              maxLength={4000}
              onChange={(e) => setInstructions(e.target.value)}
            />
            <div className="teacher-bar">
              <button
                type="button"
                className="link"
                disabled={!dirty}
                onClick={() => setInstructions(template.generation_instructions)}
              >
                Reset to the original
              </button>
              <small className="hint">
                Changes apply to this generation. Safety and reading-level rules always apply.
              </small>
            </div>
          </>
        )}
      </div>

      <button type="submit" className="primary" disabled={busy || !topic.trim()}>
        {busy ? "Generating…" : "Generate a draft"}
      </button>
    </form>
  );
}
