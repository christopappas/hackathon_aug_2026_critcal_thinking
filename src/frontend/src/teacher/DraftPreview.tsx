import { useState } from "react";
import type { GeneratedContent } from "../types";

interface Props {
  content: GeneratedContent;
  warnings: string[];
  thinkingTrap: string;
  generatedWithLlm: boolean;
  busy: boolean;
  onPublish: () => void;
  onDiscard: () => void;
  onBack: () => void;
}

/**
 * Resolves a click the same way the backend does: the smallest region containing the
 * point wins. Mirroring anchors.py here means the teacher is testing the real behaviour,
 * not a lookalike -- if a box is wrong, it is wrong the same way for a student.
 */
function resolveRegion(content: GeneratedContent, px: number, py: number) {
  const hits = content.chart.regions.filter(
    ({ box: [x, y, w, h] }) => px >= x && px <= x + w && py >= y && py <= y + h
  );
  if (hits.length === 0) return null;
  return hits.reduce((best, r) => (r.box[2] * r.box[3] < best.box[2] * best.box[3] ? r : best));
}

export function DraftPreview({
  content,
  warnings,
  thinkingTrap,
  generatedWithLlm,
  busy,
  onPublish,
  onDiscard,
  onBack,
}: Props) {
  const [showRegions, setShowRegions] = useState(true);
  const [lastHit, setLastHit] = useState<string | null>(null);

  function handleChartClick(event: React.MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    const region = resolveRegion(content, px, py);
    setLastHit(region ? region.caption : "an unlabeled area of the chart");
  }

  return (
    <div className="teacher-preview">
      <div className="teacher-bar">
        <button type="button" className="link" onClick={onBack}>
          ← Back to the form
        </button>
        <span className={`chip ${generatedWithLlm ? "good" : "warn"}`}>
          {generatedWithLlm ? "Written by the model" : "Offline example — no API token set"}
        </span>
      </div>

      {!generatedWithLlm && (
        <p className="notice">
          No <code>GITHUB_TOKEN</code> is configured, so the writing came from the template's
          built-in example. The chart and its clickable regions are still generated fresh.
        </p>
      )}

      {warnings.length > 0 && (
        <ul className="warnings">
          {warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      <div className="teacher-trap">
        <h3>The trap — teacher only</h3>
        <p>{thinkingTrap || content.thinking_trap}</p>
        <p className="hint">Students never see this. It is not in the text or the prompt they read.</p>
      </div>

      <section className="content-viewer">
        <p className="eyebrow">{content.intro}</p>
        <h1>{content.title}</h1>
        <div className="viewer-meta">
          {content.subject && <span className="chip">{content.subject}</span>}
          {content.grade_level && <span className="chip grade">Grade {content.grade_level}</span>}
        </div>

        <p className="body-text">{content.body}</p>

        <div className="teacher-bar">
          <label className="toggle">
            <input
              type="checkbox"
              checked={showRegions}
              onChange={(e) => setShowRegions(e.target.checked)}
            />
            Show the clickable regions
          </label>
          <span className="hint">Click the chart to test what a student would point at.</span>
        </div>

        <div className="chart-wrap" onClick={handleChartClick}>
          <img src={content.chart.asset_url} alt={content.chart.alt} draggable={false} />
          {showRegions &&
            content.chart.regions.map((region) => (
              <span
                key={region.id}
                className="region-box"
                title={region.caption}
                style={{
                  left: `${region.box[0] * 100}%`,
                  top: `${region.box[1] * 100}%`,
                  width: `${region.box[2] * 100}%`,
                  height: `${region.box[3] * 100}%`,
                }}
              >
                <span className="region-label">{region.id}</span>
              </span>
            ))}
        </div>

        {lastHit && (
          <p className="region-hit">
            A student clicking there points at <strong>{lastHit}</strong>
          </p>
        )}

        <p className="opening-prompt">{content.opening_prompt}</p>

        <details className="transcript" open>
          <summary>Interview clip transcript</summary>
          <ul>
            {content.video.transcript.map((line) => (
              <li key={line.t}>
                <span className="ts">{line.t.toFixed(0)}s</span> {line.text}
              </li>
            ))}
          </ul>
        </details>
      </section>

      <div className="teacher-actions">
        <button type="button" className="primary" disabled={busy} onClick={onPublish}>
          Publish to students
        </button>
        <button type="button" className="danger" disabled={busy} onClick={onDiscard}>
          Discard
        </button>
        <p className="hint">
          Saved as a draft. Students cannot see it until you publish.
        </p>
      </div>
    </div>
  );
}
