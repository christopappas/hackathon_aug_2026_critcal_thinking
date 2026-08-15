# Prototype — Think It Through

A working prototype of the critical-thinking experience described in [ARCHITECTURE.md](./ARCHITECTURE.md).

A student picks a piece of content, questions it in a 3–5 turn Socratic dialogue,
and receives a Bloom's-Taxonomy report card scoring how they thought.

All five content pieces are written for **6th graders** (ages 11–12), and both the tutor and
the scorer are instructed to read and write at that level.

## Content library

| Piece | Subject | The thinking trap |
|---|---|---|
| Do Phones Hurt Test Scores? | Data and graphs | Correlation treated as cause; truncated axis; self-reported data |
| 9 Out of 10 Students Prefer ZapFuel | Ads and media | Tiny biased sample; funded by the seller; misleading bar scale |
| Scientists Find Life on Mars | Science news | Headline overstates what the study actually claims |
| The AI Wrote This Code. Is It Right? | Computer science | AI states wrong code is correct; off-by-one and a crash case |
| Does Music Make You Study Better? | Science fair | No control; one person, one trial; two things changed at once |

## Run it

Two terminals. **It runs with no API token** — see Offline mode below.

### Backend

```bash
cd src/backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd src/frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` and `/static` to the backend, so there is no CORS setup to do.

### Enable the LLM

```bash
cd src/backend
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
cd src/backend
.venv\Scripts\python smoke_test.py
```

This drives a full session — five anchored messages through to the report card — and asserts
that every content piece loads with a reachable asset, that an unknown content id is rejected,
that every rubric dimension is scored with an evidence quote, and that a sixth message is
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
| `GET` | `/content` | List the content library for the picker |
| `POST` | `/session` | Create session for a `content_id`, return content |
| `POST` | `/chat` | Send message + optional anchor |
| `POST` | `/hint` | Request the next hint for the current turn (up to 3, then 409) |
| `POST` | `/explore/start` | Open an unscored discussion anchored to a clicked spot, replacing any thread already open |
| `POST` | `/explore/message` | Continue the active explore thread (capped at 30 messages as an anti-abuse ceiling, not a turn limit) |
| `GET` | `/report/{id}` | Report card |
| `GET` | `/rubric` | The rubric, for UI display |
| `GET` | `/health` | Status + whether the LLM is live |

Interactive docs at <http://localhost:8000/docs>.

## Layout

```
src/
  backend/
    app/
      main.py         FastAPI routes + turn guard
      dialogue.py     Socratic prompt (adaptive follow-ups)
      evaluator.py    Rubric scoring + report generation
      anchors.py      Anchor -> text excerpt resolver
      config.py       Settings + content library loader
      models.py       Pydantic models
      data/
        rubric.json   Bloom's Taxonomy rubric
        content/      One JSON file per content piece
      static/         Chart and diagram SVGs
    smoke_test.py     End-to-end check
  frontend/
    src/
      App.tsx         Phase machine: pick -> chat -> celebrate -> report
      components/     ContentPicker, ContentViewer, ChatPanel,
                      CompletionScreen, ReportCard
```

## Adding content

Drop a new JSON file into `src/backend/app/data/content/` and it appears in the picker on the
next restart — no code change. Copy an existing file for the shape. Required keys: `id`,
`title`, `body`, `chart` (with `regions`), `video.transcript`, and `opening_prompt`.
Use `order` to place it in the picker and `grade_level` for the badge.

Optionally add `min_turns` / `max_turns` to give this piece its own exchange length instead of
the global default (`MIN_TURNS`/`MAX_TURNS`, 3-5) — a quick single-flaw piece might warrant
fewer turns, a layered one more. See `study-music.json` (2-4) for a worked example. Validated
at session-creation time: `min_turns` must be at least 1, `max_turns` can't be below
`min_turns`, and there's a ceiling of 10 so a typo can't create a marathon session.

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
- **Hints are layered and cost score, not turns.** Up to 3 hints per turn (level 1 = where to
  look, level 3 = close to the issue), tracked on the exchange and folded into scoring: 2+
  hints in a session docks Question Quality and Evidence & Reasoning, enforced deterministically
  in `evaluator.py` so it holds even in offline heuristic mode.
- **Explore threads are a separate, unscored channel.** Clicking a sentence, chart region, or
  transcript line opens an open-ended discussion about just that spot (`app/explore.py`), one
  at a time, replaced whenever a new spot is clicked. It is never turn-guarded and never read by
  `evaluator.py` - going deep on a tangent should never help or hurt the graded report. The
  30-message cap is an anti-abuse ceiling, not a pedagogical limit like `MAX_TURNS`.
