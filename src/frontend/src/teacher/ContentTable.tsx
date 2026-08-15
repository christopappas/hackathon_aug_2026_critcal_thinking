import type { TeacherContentRow } from "../types";

interface Props {
  rows: TeacherContentRow[];
  busy: boolean;
  onPreview: (id: string) => void;
  onPublish: (id: string) => void;
  onUnpublish: (id: string) => void;
  onDelete: (id: string) => void;
}

export function ContentTable({ rows, busy, onPreview, onPublish, onUnpublish, onDelete }: Props) {
  const mine = rows.filter((row) => row.generated);
  const builtIn = rows.filter((row) => !row.generated);

  return (
    <div className="teacher-table">
      <h2>What you have made</h2>
      {mine.length === 0 ? (
        <p className="hint">Nothing yet. Pick a template to make your first piece.</p>
      ) : (
        <ul className="content-rows">
          {mine.map((row) => (
            <li key={row.id}>
              <span className="row-icon">{row.icon ?? "🆕"}</span>
              <div className="row-main">
                <strong>{row.title}</strong>
                <p>{row.blurb}</p>
                <div className="row-chips">
                  <span className={`chip ${row.review_status === "published" ? "good" : "warn"}`}>
                    {row.review_status === "published" ? "Live for students" : "Draft"}
                  </span>
                  {row.source?.generated_with_llm === false && (
                    <span className="chip">Offline example</span>
                  )}
                  {row.source?.topic && <span className="chip">{row.source.topic}</span>}
                </div>
              </div>
              <div className="row-actions">
                <button type="button" className="link" disabled={busy} onClick={() => onPreview(row.id)}>
                  Preview
                </button>
                {row.review_status === "published" ? (
                  <button type="button" className="link" disabled={busy} onClick={() => onUnpublish(row.id)}>
                    Unpublish
                  </button>
                ) : (
                  <button type="button" className="link" disabled={busy} onClick={() => onPublish(row.id)}>
                    Publish
                  </button>
                )}
                <button type="button" className="link danger" disabled={busy} onClick={() => onDelete(row.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <h2>Built in</h2>
      <p className="hint">
        The original five. They are always available to students and cannot be edited or deleted.
      </p>
      <ul className="content-rows muted">
        {builtIn.map((row) => (
          <li key={row.id}>
            <span className="row-icon">{row.icon ?? "📄"}</span>
            <div className="row-main">
              <strong>{row.title}</strong>
              <p>{row.blurb}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
