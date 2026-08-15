import type { SockSkin } from "../sockSkin";
import type { Report } from "../types";
import { Sockrates } from "./Sockrates";

const BLOOM = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"];

interface Props {
  report: Report;
  onRestart: () => void;
  skin: SockSkin;
}

export function ReportCard({ report, onRestart, skin }: Props) {
  const reachedIndex = BLOOM.indexOf(report.bloom_level_reached);

  return (
    <div className="report">
      <header className="report-header">
        <div className="score-ring">
          <span className="score">{report.overall_score}</span>
          <span className="out-of">/ 10</span>
        </div>
        <div>
          <h1>Sockrates' Notes</h1>
          <p className="explanation">{report.explanation}</p>
          {!report.generated_with_llm && (
            <p className="stub-note">Offline scoring mode - add a token for LLM scoring.</p>
          )}
          {report.accommodations?.length > 0 && (
            <p className="accommodations">
              Accommodations in effect: {report.accommodations.join(", ")}. These change how the
              content was presented, not what was asked of the student. Spelling and message
              length are never scored.
            </p>
          )}
        </div>
        <Sockrates
          className="report-mascot"
          skin={skin}
          mood={report.overall_score >= 7 ? "impressed" : "idle"}
          size={66}
        />
      </header>

      <section className="bloom">
        <h2>Bloom level reached</h2>
        <div className="bloom-ladder">
          {BLOOM.map((level, index) => (
            <span key={level} className={index <= reachedIndex ? "step reached" : "step"}>
              {level}
            </span>
          ))}
        </div>
      </section>

      <section className="dimensions">
        <h2>Rubric breakdown</h2>
        {report.dimensions.map((dimension) => (
          <article key={dimension.dimension} className="dimension">
            <div className="dimension-head">
              <h3>{dimension.name}</h3>
              <div className="pips">
                {[1, 2, 3, 4].map((n) => (
                  <span key={n} className={n <= dimension.score ? "pip filled" : "pip"} />
                ))}
                <span className="pip-label">{dimension.score}/4</span>
              </div>
            </div>
            <blockquote>"{dimension.evidence_quote}"</blockquote>
            <p>{dimension.feedback}</p>
          </article>
        ))}
      </section>

      <section className="next-step">
        <h2>Try this next time</h2>
        <p>{report.next_step}</p>
      </section>

      <div className="export-row">
        <a className="export-link" href={`/api/report/${report.session_id}/pdf`}>
          Download PDF
        </a>
        <a className="export-link" href={`/api/report/${report.session_id}/xlsx`}>
          Download XLSX
        </a>
      </div>

      <button type="button" className="restart" onClick={onRestart}>
        Try another one
      </button>
    </div>
  );
}
