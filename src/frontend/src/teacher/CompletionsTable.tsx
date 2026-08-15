import { useMemo, useState } from "react";
import { SockDrawerScene } from "../components/SockDrawerScene";
import type { CompletionsResponse, StudentCompletion } from "../types";

/**
 * Who finished what, and how they thought while doing it.
 *
 * A real <table> rather than the card list the content manager uses: these rows are
 * meant to be *compared* down a column, which is the one job a table does better than
 * anything else. It also gets column sorting and screen-reader row/column association
 * for free, both of which a grid of divs would have to reimplement.
 *
 * The rows are mock (see the backend's completions.py). The banner says so on the page
 * instead of only in the code, because a table of student names and scores is exactly
 * the thing someone would otherwise screenshot and believe.
 */

type SortKey = "student_name" | "content_title" | "completed_at" | "overall_score" | "hints_used";

const COLUMNS: { key: SortKey | null; label: string; numeric?: boolean }[] = [
  { key: "student_name", label: "Student" },
  { key: "content_title", label: "Piece" },
  { key: "completed_at", label: "Finished" },
  { key: null, label: "Rubric" },
  { key: "hints_used", label: "Hints", numeric: true },
  { key: "overall_score", label: "Score", numeric: true },
];

/** Names are long; the column is narrow. Full text stays in the cell's title. */
function shorten(title: string): string {
  return title.length > 34 ? `${title.slice(0, 33)}…` : title;
}

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function band(score: number): string {
  if (score >= 8) return "high";
  if (score >= 5) return "mid";
  return "low";
}

/** The five dimension scores as pips, so a row shows its shape without five columns. */
function RubricPips({ row }: { row: StudentCompletion }) {
  return (
    <span
      className="rubric-pips"
      title={row.dimensions.map((d) => `${d.name}: ${d.score}/4`).join("\n")}
    >
      {row.dimensions.map((dimension) => (
        <span key={dimension.dimension} className={`rubric-pip rubric-pip-${dimension.score}`}>
          <span className="sr-only">{`${dimension.name}: ${dimension.score} of 4. `}</span>
        </span>
      ))}
    </span>
  );
}

interface Props {
  data: CompletionsResponse;
  onBack: () => void;
}

export function CompletionsTable({ data, onBack }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("completed_at");
  const [ascending, setAscending] = useState(false);

  const rows = useMemo(() => {
    const direction = ascending ? 1 : -1;
    return [...data.rows].sort((a, b) => {
      const left = a[sortKey];
      const right = b[sortKey];
      if (typeof left === "number" && typeof right === "number") return (left - right) * direction;
      return String(left).localeCompare(String(right)) * direction;
    });
  }, [data.rows, sortKey, ascending]);

  function sortBy(key: SortKey) {
    if (key === sortKey) {
      setAscending((previous) => !previous);
      return;
    }
    setSortKey(key);
    // Names read best A-Z; everything else is most interesting at its high end.
    setAscending(key === "student_name" || key === "content_title");
  }

  return (
    <section className="completions">
      <header className="completions-head">
        <div>
          <h1>Student completions</h1>
          <p className="hint">
            Every finished dialogue, with the report card score it earned. Scores are 1–10;
            the five pips are the rubric dimensions, 1–4 each.
          </p>
          {data.mock && (
            <p className="notice warn-notice">
              <strong>Demo data.</strong> These students are invented and no real completion is
              recorded anywhere — sessions are anonymous and in memory. Nothing here is a
              student record.
            </p>
          )}
        </div>
        <SockDrawerScene width={260} />
      </header>

      <div className="completions-stats">
        <div>
          <strong>{data.rows.length}</strong>
          <span>completions</span>
        </div>
        <div>
          <strong>{data.student_count}</strong>
          <span>students</span>
        </div>
        <div>
          <strong>{data.average_score}</strong>
          <span>class average</span>
        </div>
      </div>

      <div className="completions-scroll">
        <table className="completions-table">
          <caption className="sr-only">
            Student completions, sortable by student, piece, date, hints, or score.
          </caption>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.label}
                  scope="col"
                  className={column.numeric ? "numeric" : undefined}
                  aria-sort={
                    column.key === sortKey ? (ascending ? "ascending" : "descending") : undefined
                  }
                >
                  {column.key ? (
                    <button type="button" className="sort" onClick={() => sortBy(column.key!)}>
                      {column.label}
                      <span aria-hidden="true">
                        {column.key === sortKey ? (ascending ? " ↑" : " ↓") : " ↕"}
                      </span>
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <th scope="row">{row.student_name}</th>
                <td title={row.content_title}>{shorten(row.content_title)}</td>
                <td>
                  {formatDate(row.completed_at)}
                  <span className="turns"> · {row.turns_used} turns</span>
                </td>
                <td>
                  <RubricPips row={row} />
                </td>
                <td className="numeric">{row.hints_used}</td>
                <td className="numeric">
                  <span className={`score-pill ${band(row.overall_score)}`}>
                    {row.overall_score}
                  </span>
                  <span className="bloom-tag">{row.bloom_level_reached}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="teacher-actions">
        <button type="button" className="link" onClick={onBack}>
          ← Back to content
        </button>
      </div>
    </section>
  );
}
