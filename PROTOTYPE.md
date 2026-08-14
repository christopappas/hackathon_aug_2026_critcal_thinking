# Prototype — Think It Through

A working prototype of the critical-thinking experience described in [ARCHITECTURE.md](./ARCHITECTURE.md).

A student reads a flawed school-newspaper report, questions it in a 3–5 turn Socratic dialogue,
and receives a Bloom's-Taxonomy report card scoring how they thought.

## Run it

Two terminals. **It runs with no API token** — see Offline mode below.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` and `/static` to the backend, so there is no CORS setup to do.

### Enable the LLM

```bash
cd backend
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Put a GitHub token in `GITHUB_TOKEN` (no scopes required — it is only used for
[GitHub Models](https://github.com/marketplace/models)). Restart the backend.

`GET /health` reports whether the LLM is live:

```json
{ "status": "ok", "llm_enabled": true, "model": "gpt-4o-mini" }
```

### Offline mode

Without a token the app still runs a complete demo: the tutor uses scripted Socratic
follow-ups and scoring falls back to a deterministic heuristic. The report card flags this
with `generated_with_llm: false`. This keeps the demo alive if the token expires or the
provider rate-limits mid-presentation.

## Verify it

With the backend running:

```bash
cd backend
.venv\Scripts\python smoke_test.py
```

This drives a full session — five anchored messages through to the report card — and asserts
that every rubric dimension is scored with an evidence quote and that a sixth message is
rejected with HTTP 409.

## How anchoring works

The student can point a question at a specific part of the content. All three kinds normalize
to a text excerpt server-side (`app/anchors.py`), so the prompts never branch on media type.

| Kind | Student action | Payload |
|---|---|---|
| `text` | Selects a sentence in the report | `{kind, quote, start, end}` |
| `region` | Clicks the chart | `{kind, box: [x, y, 0, 0]}` normalized 0–1 |
| `temporal` | Clicks a transcript line | `{kind, timestamp_s}` |

Chart regions overlap, so the resolver picks the **smallest** region containing the click —
clicking the outlier cluster resolves to the outliers, not the trend line beneath it.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/session` | Create session, return content |
| `POST` | `/chat` | Send message + optional anchor |
| `GET` | `/report/{id}` | Report card |
| `GET` | `/rubric` | The rubric, for UI display |
| `GET` | `/health` | Status + whether the LLM is live |

Interactive docs at <http://localhost:8000/docs>.

## Layout

```
backend/
  app/
    main.py         FastAPI routes + turn guard
    dialogue.py     Socratic prompt (adaptive follow-ups)
    evaluator.py    Rubric scoring + report generation
    anchors.py      Anchor -> text excerpt resolver
    models.py       Pydantic models
    data/           content.json, rubric.json
    static/         chart.svg
  smoke_test.py     End-to-end check
frontend/
  src/
    App.tsx         Phase machine: chat -> celebrate -> report
    components/     ContentViewer, ChatPanel, CompletionScreen, ReportCard
```

## Notes on the design

- **The turn guard is server-side.** The dots in the UI are display only; the backend rejects a
  6th message with 409, so the cap cannot be bypassed from the client.
- **Dialogue and scoring are separate LLM calls.** Sharing one prompt makes the model grade
  while it coaches, which leaks the rubric to the student mid-conversation.
- **Scoring is post-hoc over the full transcript**, because the Depth of Follow-up dimension
  can only be judged by comparing turns to each other.
- **Every dimension score must cite a verbatim student quote.** This is enforced by the JSON
  schema and curbs hallucinated grading, and it doubles as the required score explanation.
- **The conversation can end early.** After 3 turns the model may set `should_conclude` once
  all rubric dimensions have evidence; 5 is the hard stop.
