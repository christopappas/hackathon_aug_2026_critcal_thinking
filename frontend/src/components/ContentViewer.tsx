import { useRef } from "react";
import type { Anchor, Content } from "../types";

interface Props {
  content: Content;
  activeAnchor: Anchor | null;
  onAnchor: (anchor: Anchor | null) => void;
  disabled: boolean;
}

export function ContentViewer({ content, activeAnchor, onAnchor, disabled }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);

  function handleTextSelect() {
    if (disabled) return;
    const selection = window.getSelection();
    const quote = selection?.toString().trim() ?? "";
    if (quote.length < 3) return;
    const start = content.body.indexOf(quote);
    onAnchor({ kind: "text", quote, start, end: start + quote.length });
  }

  function handleChartClick(event: React.MouseEvent<HTMLDivElement>) {
    if (disabled || !chartRef.current) return;
    const rect = chartRef.current.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    // Zero-size box: the backend resolves an anchor by its center point.
    onAnchor({ kind: "region", box: [x, y, 0, 0] });
  }

  return (
    <section className="content-viewer">
      <p className="eyebrow">{content.intro}</p>
      <h1>{content.title}</h1>

      <p className="body-text" onMouseUp={handleTextSelect}>
        {content.body}
      </p>
      <p className="hint">Select any sentence above to point your question at it.</p>

      <div className="chart-wrap" ref={chartRef} onClick={handleChartClick}>
        <img src={content.chart.asset_url} alt={content.chart.alt} draggable={false} />
        {activeAnchor?.kind === "region" && activeAnchor.box && (
          <span
            className="pin"
            style={{ left: `${activeAnchor.box[0] * 100}%`, top: `${activeAnchor.box[1] * 100}%` }}
          />
        )}
      </div>
      <p className="hint">Click anywhere on the chart to point at it.</p>

      <details className="transcript">
        <summary>Interview clip transcript</summary>
        <ul>
          {content.video.transcript.map((line) => (
            <li key={line.t}>
              <button
                type="button"
                disabled={disabled}
                className={activeAnchor?.timestamp_s === line.t ? "selected" : ""}
                onClick={() => onAnchor({ kind: "temporal", timestamp_s: line.t })}
              >
                <span className="ts">{line.t.toFixed(0)}s</span> {line.text}
              </button>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
