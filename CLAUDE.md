# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

## What this is

**Sockrates** — a hackathon prototype exploring how AI can foster students' critical
thinking. A student picks one of five grade-6 content pieces, questions it in a 3–5 turn
Socratic dialogue, and receives a Bloom's-Taxonomy report card scoring *how they thought*.

The tutor is a sock puppet convinced he is a great Greek philosopher. His persona lives in
`dialogue.py` (`SYSTEM_PROMPT`, `HINT_SYSTEM_PROMPT`, and both stub lists) and in the
`opening_prompt` of each content file. **`evaluator.py` is deliberately not in character** —
see the design invariant on dialogue and scoring being separate calls.

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system design, requirement IDs (I1–I5, S1–S9), key decisions
- [PROTOTYPE.md](./PROTOTYPE.md) — how to run it, API surface, how anchoring works

This is **not** a Drupal project. No lando, composer, drush, or phpcs applies here.

## Branch

Work off **`main`**. The `sat` prototype branch was merged in via PR #2 and is fully
absorbed — do not start new work on `sat`.

Repo convention: per-person top-level scratch directories (`christopappas/`, `fenichel/`)
alongside the shared `src/`.

## The punchlist lives in GitHub issues

Open issues are the team's working punchlist for the day — not a long-term backlog. Check it
before starting work, and treat it as the source of truth for what's in scope:

```bash
gh issue list --state open
```

Close issues via the PR that fixes them (`Closes #N` in the PR description) rather than
resolving them by hand. If you finish something that wasn't filed, file it and close it, so
the list stays an accurate record of the day.

Because the list moves fast, confirm an issue is still live before acting on it — and read
the relevant code before assuming a request isn't already implemented.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI + Pydantic v2 (`src/backend`) |
| Frontend | React + Vite + TypeScript (`src/frontend`) |
| LLM | GitHub Models `gpt-4o-mini` via the OpenAI-compatible SDK |
| Sessions | In-memory dict — no database by design |
| Content + rubric | Static JSON under `src/backend/app/data/` |

## Running it

Two terminals. It runs with **no API token** — see Offline mode below.

```bash
cd src/backend && .venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd src/frontend && npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` and `/static` to the backend, so there is
no CORS setup to do. Interactive API docs at <http://localhost:8000/docs>.

Verify end-to-end — drives a full session through to the report card and asserts the turn
guard rejects a 6th message with 409:

```bash
cd src/backend && .venv/bin/python smoke_test.py
```

## CI

`.github/workflows/ci.yml` runs on every push to `main` and every PR: `pytest` + `smoke_test.py`
for the backend (Python 3.12, no token needed — tests force offline mode), `tsc -b && vite
build` for the frontend. No deploy step yet — nothing is hosted anywhere, so there's no target
to wire up. When one exists, add a `deploy` job gated on the existing checks passing.

## Setup traps

**Use Python 3.12+, never the macOS system `python3`.** System Python is 3.9.6 and *will*
fail: the Pydantic models use `str | None` field annotations (`src/backend/app/models.py`).
`from __future__ import annotations` defers those to strings, but Pydantic resolves them
anyway when building the schema, raising `TypeError` on 3.9. To (re)create the venv:

```bash
cd src/backend && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

**Don't commit `libc` churn in `src/frontend/package-lock.json`.** Depending on the npm
version, `npm install` adds or strips `libc` metadata on optional platform-specific Rollup
binaries. That is not a dependency change. If the only diff is `libc`/`glibc`/`musl` lines,
revert it:

```bash
git checkout -- src/frontend/package-lock.json
```

## Offline mode and the LLM

Without a token the app still runs a complete demo: the tutor uses scripted Socratic
follow-ups and scoring falls back to a deterministic heuristic. The report card flags this
with `generated_with_llm: false`. This keeps the demo alive if a token expires or the
provider rate-limits mid-presentation.

To enable the LLM, `cp .env.example .env` in `src/backend` and set `GITHUB_TOKEN` (no scopes
needed — it is only used for [GitHub Models](https://github.com/marketplace/models)).
Restart the backend; `GET /health` reports `llm_enabled`.

**Caveat worth checking before a demo:** `requirements.txt` pins `openai>=1.109`, but that
currently resolves to **openai 3.x**, a major version ahead of what this was written
against. `app/llm.py` catches *every* provider failure and falls back to the stub, so a
break in the live path shows up as silently-scripted replies rather than an error. Confirm
`llm_enabled: true` and that replies actually vary before relying on it.

## Design invariants

Preserve these when changing things — each exists for a stated reason:

- **The turn guard is server-side.** The dots in the UI are display only; the backend
  rejects a 6th message with 409, so the cap cannot be bypassed from the client.
- **Dialogue and scoring are separate LLM calls.** Sharing one prompt makes the model grade
  while it coaches, which leaks the rubric to the student mid-conversation.
- **Scoring is post-hoc over the full transcript**, because the Depth of Follow-up dimension
  can only be judged by comparing turns to each other.
- **Every dimension score must cite a verbatim student quote**, enforced by the JSON schema.
  This curbs hallucinated grading and doubles as the required score explanation.
- **Anchors normalize to a text excerpt** server-side (`app/anchors.py`), so prompts never
  branch on media type. Overlapping chart regions resolve to the *smallest* box containing
  the click.
- **The rubric is data, not prompt text** (`app/data/rubric.json`), so the UI, evaluator, and
  report generator share one source of truth.
- **Hints cost score, not turns.** Up to 3 per turn, tracked on the exchange and docked against
  Question Quality and Evidence & Reasoning deterministically in `evaluator.py` (not just
  prompted for), so it holds in offline heuristic mode too.
- **Explore threads (`app/explore.py`) are a separate, unscored channel.** Opened by clicking a
  spot in the content, one active at a time, never turn-guarded and never read by
  `evaluator.py`. Going deep on a tangent must never help or hurt the graded report — if you
  touch scoring, double check `session.explore` still isn't referenced anywhere in it.
- **Sockrates' moods are derived, not stored.** `useSockratesMood` keeps state only for the two
  transient reactions (`talking`, `hinting`); `thinking`/`listening`/`idle` are computed at
  render from props. Storing them lets a mood drift out of sync with `busy`.
- **No mascot animation uses `animation-fill-mode`**, and rotation is animated on the element
  while positional transforms stay on a wrapper `<g>`. The first rule means dropping a mood
  class always restores the base pose; the second avoids CSS `transform` clobbering the
  `transform` attribute, which teleports a jaw to the origin on frame one.
- **Every mood has a static pose** under `prefers-reduced-motion`, because motion is the
  mascot's only state channel. A blanket `animation: none` would mute it.

## Adding content

Drop a new JSON file into `src/backend/app/data/content/` and it appears in the picker on the
next restart — no code change. Copy an existing file for the shape. Required keys: `id`,
`title`, `body`, `chart` (with `regions`), `video.transcript`, and `opening_prompt`. Use
`order` to place it in the picker and `grade_level` for the badge.

## Two Bloom's implementations now coexist

The merge brought together two independent encodings of the same six revised-taxonomy levels
(Remember → Understand → Apply → Analyze → Evaluate → Create):

| | `fenichel/skill.md` | `src/backend/app/data/rubric.json` |
|---|---|---|
| Form | A Claude skill (draft) | Static JSON consumed by the evaluator |
| Unit | One student question at a time | The whole transcript, post-hoc |
| Output | One of 6 levels + rationale | 5 dimensions scored 1–4, each with an evidence quote, plus a `bloom_level_reached` |

They are not wired together, and neither imports the other. Before extending either, check
whether the change belongs in both — and consider whether they should converge on one shared
definition of the levels rather than drifting apart.
