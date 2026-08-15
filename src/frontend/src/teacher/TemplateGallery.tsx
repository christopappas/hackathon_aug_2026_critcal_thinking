import type { Template } from "../types";

interface Props {
  templates: Template[];
  onPick: (template: Template) => void;
  onImport: () => void;
}

export function TemplateGallery({ templates, onPick, onImport }: Props) {
  return (
    <div className="picker">
      <header className="picker-head">
        <h1>Make something for your class</h1>
        <p>
          Start from a template, change it to fit what you are teaching, and generate a new
          piece for students to question.
        </p>
      </header>

      <div className="picker-grid">
        {templates.map((template) => (
          <button
            key={template.id}
            type="button"
            className="picker-card"
            onClick={() => onPick(template)}
          >
            <span className="picker-icon">{template.icon}</span>
            <span className="picker-subject">{template.subject}</span>
            <h2>{template.name}</h2>
            <p>{template.description}</p>
            <span className="chip warn">{template.trap}</span>
            <span className="picker-go">Use this →</span>
          </button>
        ))}

        <button type="button" className="picker-card dashed" onClick={onImport}>
          <span className="picker-icon">📥</span>
          <span className="picker-subject">Written elsewhere</span>
          <h2>Import a piece</h2>
          <p>
            Paste a payload you wrote by hand, or had a model write for you. Bring a chart
            spec and the click regions are worked out for you, or bring your own SVG.
          </p>
          <span className="picker-go">Paste it in →</span>
        </button>
      </div>
    </div>
  );
}
