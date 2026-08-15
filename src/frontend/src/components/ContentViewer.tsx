import { useRef } from "react";
import { POPOVER_WIDTH } from "./ExplorePopover";
import type { Anchor, Content } from "../types";

type Position = { x: number; y: number };

interface Props {
  content: Content;
  activeAnchor: Anchor | null;
  onAnchor: (anchor: Anchor | null) => void;
  onExplore: (anchor: Anchor, position: Position) => void;
  disabled: boolean;
  dyslexiaMode?: boolean;
}

/**
 * Break the body into short paragraphs at sentence boundaries.
 *
 * Each chunk stays a contiguous substring of `content.body`, so text anchoring
 * still resolves by `indexOf` against the original text.
 */
function chunkSentences(body: string, perChunk: number): string[] {
  const sentences = body.split(/(?<=[.!?])\s+/).filter(Boolean);
  const chunks: string[] = [];
  for (let i = 0; i < sentences.length; i += perChunk) {
    chunks.push(sentences.slice(i, i + perChunk).join(" "));
  }
  return chunks.length > 0 ? chunks : [body];
}

export function ContentViewer({
  content,
  activeAnchor,
  onAnchor,
  onExplore,
  disabled,
  dyslexiaMode,
}: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<HTMLElement>(null);
  const paragraphs = dyslexiaMode ? chunkSentences(content.body, 2) : [content.body];

  // The popover is viewport-fixed, so on a wide screen a click near the right
  // edge of this column can still leave room to drift into the chat panel.
  // Clamp against this column's own right edge, not just the window's.
  function popoverPosition(x: number, y: number): Position {
    const bounds = viewerRef.current?.getBoundingClientRect();
    const maxX = bounds ? bounds.right - POPOVER_WIDTH - 12 : x;
    return { x: Math.min(x, maxX), y };
  }

  function handleTextSelect() {
    if (disabled) return;
    const selection = window.getSelection();
    const quote = selection?.toString().trim() ?? "";
    if (quote.length < 3) return;
    const start = content.body.indexOf(quote);
    const anchor: Anchor = { kind: "text", quote, start, end: start + quote.length };
    onAnchor(anchor);
    const rect = selection!.getRangeAt(0).getBoundingClientRect();
    onExplore(anchor, popoverPosition(rect.left, rect.bottom + 8));
  }

  function handleChartClick(event: React.MouseEvent<HTMLDivElement>) {
    if (disabled || !chartRef.current) return;
    const rect = chartRef.current.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    // Zero-size box: the backend resolves an anchor by its center point.
    const anchor: Anchor = { kind: "region", box: [x, y, 0, 0] };
    onAnchor(anchor);
    onExplore(anchor, popoverPosition(event.clientX, event.clientY + 12));
  }

  return (
    <section className="content-viewer" ref={viewerRef}>
      <p className="eyebrow">{content.intro}</p>
      <h1>{content.title}</h1>
      <div className="viewer-meta">
        {content.subject && <span className="chip">{content.subject}</span>}
        {content.grade_level && <span className="chip grade">Grade {content.grade_level}</span>}
      </div>

      <div className="body-text" onMouseUp={handleTextSelect}>
        {paragraphs.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>
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
                onClick={(event) => {
                  const anchor: Anchor = { kind: "temporal", timestamp_s: line.t };
                  onAnchor(anchor);
                  onExplore(anchor, popoverPosition(event.clientX, event.clientY + 12));
                }}
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
