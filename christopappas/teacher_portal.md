# Teacher Portal — dynamic content generation (issue #11)

## Context

"Think It Through" ships with five hand-authored content pieces. Adding a sixth means a developer
hand-writing a JSON file *and* hand-drawing an SVG chart with matching normalized region boxes.
That is the bottleneck [issue #11](https://github.com/christopappas/hackathon_aug_2026_critcal_thinking/issues/11)
is about: teachers should be able to generate their own content from a library of templates they
can modify, through a separate page built for them.

Outcome: a `/teacher` portal where a teacher starts from a template ("misleading bar chart ad"),
edits the prompt and fields for their class, generates a draft, **previews it with the clickable
regions overlaid**, and publishes it into the student picker — plus edit/delete for pieces they
made. Auth is deliberately out of scope (tracked separately as issue #10).

### Decisions taken
- Chart = structured spec → deterministic Python SVG renderer. The LLM supplies *captions and
  numbers*; the renderer supplies *geometry and region boxes*. Boxes can never drift from the drawing.
- Generated content is written to disk (`data/content/generated/`), gitignored, and the `lru_cache`
  is cleared so it appears in the picker without a restart.
- Teacher edits **generation templates** and **manages generated pieces**. The Socratic tutor and
  scoring system prompts stay hardcoded — out of scope for this change.
- `/teacher` is an open route.

### The geometry is not a guess — it is verified
A deterministic renderer reproduces the hand-authored files *exactly*, so the renderer is the house
style expressed as code rather than an approximation of it:

| Check | Renderer | Authored file |
|---|---|---|
| ZapFuel bar rect | `x=160 y=200 w=110 h=140` | `static/chart-zapfuel.svg:14` — identical |
| ZapFuel bar region | `[0.267, 0.5, 0.183, 0.35]` | `energy-drink-ad.json:22` — identical |
| y-tick label positions | `345, 275, 205, 135, 65` | `chart-zapfuel.svg:8-12` — identical |
| Derived y-axis region | `[0.04, 0.13, 0.13, 0.73]` | `energy-drink-ad.json:17` — identical |
| Scatter y-axis region | `[0.02, 0.1, 0.16, 0.75]` | `screen-time-scores.json:22` — identical |

The truncated-axis trap falls out of `y_min=80` with no special casing: `y_of(90)=200`, `y_of(85)=270`
— exactly the authored bars. **Build `charts.py` first and diff its ZapFuel output against
`chart-zapfuel.svg`**; once that matches, the riskiest part of the feature is de-risked and the rest
is CRUD.

### Draft state lives on disk, not in memory
Generation writes the piece immediately with `review_status: "draft"`; publishing flips it to
`"published"`. Only `list_content()` filters on it — `load_content()` still resolves drafts. This is
one persistence path instead of two, it survives `--reload`, and it makes **preview-as-student free**:
`POST /session {content_id: <draft>}` just works with no preview-specific code path. The review gate
is then enforced by `list_content()` rather than by discipline.

### The constraint that governs the design
`ContentViewer.tsx:23-30` normalizes a chart click against the `.chart-wrap` rect and sends
`{kind:"region", box:[x,y,0,0]}`. `styles.css:110-114` sets `.chart-wrap img { display:block;
width:100%; height:auto }`, so the wrap is exactly the image box and **normalized click coords equal
normalized SVG viewBox coords**. `anchors.py:34-42` then picks the smallest region containing the
point. So clickability survives iff the renderer emits a **600×400 viewBox** (matching all five
existing SVGs) and emits region boxes as `[x/600, y/400, w/600, h/400]` from the same numbers it drew.
This is the single invariant the whole feature rests on.

---

## Backend

### New: `src/backend/app/chart_render.py`
Deterministic `chart_spec -> (svg_text, regions)`. No LLM involvement in geometry.

Canonical constants, reverse-engineered from and verified against the authored files:

```python
W, H = 600, 400
BAR     = dict(L=100, R=560, T=60, B=340)   # matches chart-zapfuel.svg
SCATTER = dict(L=100, R=560, T=40, B=320)   # matches chart.svg

y_of(v)  = B - (v - y_min)/(y_max - y_min) * (B - T)
slot     = 460 / n;  bar_w = round(slot * 0.48)        # n=2 -> 110, the authored width
bar_x(i) = L + i*slot + (slot - bar_w)/2               # i=0 -> 160, the authored x
```

Escape every text node with `xml.sax.saxutils.escape`. This is the whole reason to prefer a renderer
over LLM-authored SVG: the model never emits markup, so there is no `<script>` to serve to a browser.

```python
def render(spec: dict) -> tuple[str, list[dict]]:
    """Return SVG markup and the normalized regions that match it."""
```

- `kind: "bar"` — n bars evenly spaced across the plot; bar top =
  `340 - (value - y.min)/(y.max - y.min) * 280`. Emits `<rect>` + value label + x label per bar.
- `kind: "scatter"` — points mapped through the same x/y scales, `outlier: true` points styled apart.
- Axis ticks from `y.min`/`y.max`/`tick_step`; `annotation` drawn as a two-line callout; `footnote`
  as the bottom-left small grey text.

Regions are emitted from the same pixel rects, normalized — one per series/point-cluster, plus
`y-axis` (the label gutter, `[30,50,75,300]`px), `annotation`, and `footnote`. Each region's
`caption` comes from the spec (LLM-authored prose); each region's `box` comes from the renderer.
Order matters: emit larger boxes first, smaller last is irrelevant — `anchors.py` already picks the
*smallest* containing box, so overlapping is safe by design.

A truncated y-axis — the classic trap — is just `y.min: 80`, expressible as data.

### New: `src/backend/app/generator.py`
The third LLM role, mirroring `dialogue.py` / `evaluator.py` structure exactly (schema constant +
`SYSTEM_PROMPT` + `build_user_prompt` + stub fallback + `generate_*() -> tuple[dict, bool]`). It is a
separate prompt from dialogue and scoring, preserving the "one prompt per LLM role" invariant.

- `GENERATION_SCHEMA` — must satisfy OpenAI `strict: true` (every property in `required`,
  `additionalProperties: false` at every level). Produces: `title`, `subject`, `blurb`, `icon`
  (emoji), `intro`, `body`, `opening_prompt`, `chart_spec` (incl. per-element `caption` strings),
  `chart_alt`, `transcript[{t, text}]`.
- `SYSTEM_PROMPT` — writes deliberately flawed grade-appropriate content whose flaw is a *reasoning*
  trap. Explicit rails: fictional people/brands/schools only; no real statistics stated as fact;
  avoid health, politics, religion, race, and tragedy as topics; plain 6th-grade language.
- `_stub_content(template)` — offline path returns the template's own `stub` payload, so
  "Generate" still yields a valid, clickable piece with no `GITHUB_TOKEN`. This keeps the existing
  offline-demo invariant intact (`llm.py` swallows *every* provider failure, so generation must
  degrade the same way dialogue and scoring already do).

The generator returns a **draft**, never writes files.

### New: `src/backend/app/content_store.py`
Assembly, validation, and persistence.

- `assemble(draft, template_id) -> content` — renders the chart via `chart_render`, slots
  `chart.asset_url`, `regions`, `video.transcript`, assigns a unique slug id (append `-2`… on
  collision), `order = max(existing) + 1`, and provenance fields `generated: true`,
  `generated_at`, `template_id`, `generated_with_llm`.
- `validate(content)` — rejects on: any missing required key (`id`, `title`, `body`, `intro`,
  `opening_prompt`, `chart`, `video`), empty `regions`, any box outside `[0,1]` or with `w<=0`/`h<=0`,
  empty transcript. Returns a list of problems the portal shows inline.
- `save/update/delete` — writes `data/content/generated/{id}.json` and
  `static/generated/{id}.svg`; delete removes both. Every mutation calls
  `config.load_library.cache_clear()`.

### New: `src/backend/app/data/templates/*.json` + `src/backend/app/templates.py`
Templates are data, consistent with "the rubric is data, not prompt text".

Template shape: `{id, name, description, icon, thinking_trap, chart_kind, fields{topic, subject,
grade_level}, instructions, stub}` where `instructions` is the editable prompt body with `{topic}`,
`{subject}`, `{grade_level}` placeholders, and `stub` is the offline fallback piece.

Seed set (3), each mirroring a piece that already demos well: **`misleading-bar-ad`** (truncated axis
→ `energy-drink-ad`) · **`tiny-sample-experiment`** (→ `study-music`) · **`correlation-news`**
(scatter → `screen-time-scores`, deferred with scatter to Phase B).

Each template also carries a complete, schema-shaped `offline_draft`, which is what makes the demo
safe: with no token, generation substitutes the teacher's topic into that draft and then **runs the
same renderer and the same validator**. Offline still produces a genuinely new SVG, genuinely derived
regions, and a real clickable chart — only the prose is canned. Unlike the dialogue stub this is
honest, because the response carries `generated_with_llm: false`.

`templates.py` mirrors `config.py`: `@lru_cache load_templates()` over
`data/templates/**/*.json`, plus `save_template()` / `delete_template()` writing to
`data/templates/custom/` with `cache_clear()`. Seeded templates are read-only; "Save as new"
writes a custom copy.

### Modified: `src/backend/app/config.py`
`load_library()` uses `CONTENT_DIR.glob("*.json")` (`config.py:31`), which is **depth-1 only** — a
`generated/` subdirectory is silently skipped and `cache_clear()` would be a no-op. Read the two
directories explicitly rather than switching to `rglob`, because being explicit tags provenance at
load time so the writer never has to remember to:

```python
seeds = [(p, False) for p in sorted(CONTENT_DIR.glob("*.json"))]
gen   = [(p, True)  for p in sorted(GENERATED_CONTENT_DIR.glob("*.json"))]
# item["generated"] = is_gen; item.setdefault("review_status", "published")
```

Seeds have no `review_status` key, so defaulting to `"published"` keeps all five visible with zero
edits to the existing JSON files.
- `list_content()` — filter to `review_status == "published"`; add `icon` and `generated` to the projection.
- Add `GENERATED_CONTENT_DIR`, `GENERATED_STATIC_DIR` (created on import), and `reload_library()`.
- `load_content()` unchanged — still resolves drafts, which is what gives preview-as-student.

### Modified: `src/backend/app/main.py`
Seven flat routes in the existing style (no `APIRouter` — the file has none today):

| Route | Purpose |
|---|---|
| `GET /teacher/templates` | template library |
| `POST /teacher/templates` | create/update a custom template |
| `DELETE /teacher/templates/{id}` | delete custom (409 on seeded) |
| `POST /teacher/generate` | generate → writes a **draft** → `{content, warnings[], generated_with_llm, thinking_trap}` |
| `GET /teacher/content` | all pieces including drafts |
| `POST /teacher/content/{id}/publish` · `/unpublish` | flip `review_status` |
| `PUT`/`DELETE /teacher/content/{id}` | edit / remove; **403 on a seed id** |

Generate and publish are **separate calls on purpose** — nothing reaches students without a teacher
looking at it first. That review gate is also what CA policy expects of student-facing content.

These are enough routes to swamp `main.py`, so put them in an `APIRouter` in a new
`src/backend/app/teacher.py` and `app.include_router(...)` — a one-line change to `main.py`, which
keeps its own flat-route convention intact.

**Write ordering matters:** SVG first, JSON second, then `reload_library()`. That guarantees the
picker never lists a piece whose image 404s — exactly what `smoke_test.py:72-73` asserts.

### Modified: `src/backend/app/models.py`
Add `icon: str | None` to `ContentSummary`; add `Template`, `GenerateRequest`,
`GeneratedDraft`, `PublishRequest`.

---

## Frontend

### Modified: `src/frontend/src/main.tsx`
```tsx
const isTeacher = window.location.pathname.startsWith("/teacher");
root.render(<StrictMode>{isTeacher ? <TeacherPortal /> : <App />}</StrictMode>);
```
Zero new dependencies; Vite's default SPA fallback already serves `index.html` at `/teacher`, and
`/api` + `/static` stay proxied per `vite.config.ts`.

### New: `src/frontend/src/teacher/`
`TeacherPortal.tsx` follows the `App.tsx` pattern — a `Phase` union
(`"templates" | "editing" | "preview" | "manage"`) with sequential early returns, no router.

- **`TemplateGallery.tsx`** — reuses `.picker-grid` / `.picker-card` / `.picker-icon`.
- **`GenerateForm.tsx`** — fields (topic, subject, grade level) plus a textarea holding the
  template's `instructions`, editable before generating. "Save as new template" persists the edit.
- **`DraftPreview.tsx`** — the important one. Renders the draft the way `ContentViewer` does
  (same markup and classes so what the teacher sees is what the student gets), and adds a
  **region overlay**: each `chart.regions[i].box` drawn as a labeled translucent rect over the
  SVG, plus live click-testing — clicking the chart resolves the hit locally with the same
  smallest-box rule as `anchors.py:34-42` and shows which caption fired. Any validation problem
  from the backend renders inline. Publish is disabled until validation is clean.
- **`GeneratedList.tsx`** — published pieces with edit (title/body/opening prompt/captions) and
  delete.

### Modified: `src/frontend/src/api.ts`, `types.ts`, `styles.css`
Add teacher functions via the existing `request<T>()` helper; add `Template`, `ChartSpec`,
`GeneratedDraft` types; append a `.teacher-*` block to `styles.css` reusing
`--bg --card --ink --muted --accent --accent-soft --good --line`.

### Modified: `src/frontend/src/components/ContentPicker.tsx`
`ICONS` is hardcoded by content id (`ContentPicker.tsx:8-14`), so generated pieces render `❓`.
Change to `item.icon ?? ICONS[item.id] ?? "❓"`.

---

## Verification

1. **Automated** — extend `src/backend/smoke_test.py` (same plain-urllib + assert style, no new test
   dep) with a teacher flow, run via `.venv/bin/python smoke_test.py` against a live server:
   - `GET /teacher/templates` returns the 4 seeds
   - `POST /teacher/generate` returns a draft with non-empty `chart.regions`, every box inside
     `[0,1]`, and no validation problems
   - `POST /teacher/content` publishes; the new id appears in `GET /content` **without a restart**
     (this is the `lru_cache` regression)
   - `GET` the new `chart.asset_url` → 200
   - **The clickability assertion:** open a session on the generated piece, `POST /chat` with
     `{kind:"region", box:[cx, cy, 0, 0]}` at the center of each returned region, and assert
     `anchor_excerpt` contains that region's caption. This is the direct regression test for
     "regions are still clickable".
   - the draft is **absent** from `GET /content` before publish — proves the review gate
   - the fetched SVG body starts with `<svg` — proves the SVG-before-JSON ordering
   - **Cleanup is mandatory:** `DELETE /teacher/content/{id}` at the end, plus assert `DELETE` on a
     seed id returns 403. Without cleanup the test isn't re-runnable and every run permanently grows
     the library — which then slows the *existing* per-item session loop at `smoke_test.py:66-75`.
2. **Manual** — backend + `npm run dev`, open <http://localhost:5173/teacher>: pick a template, edit
   the prompt, generate, confirm the overlay boxes sit on the right chart elements, publish, then
   open <http://localhost:5173> as a student and run a full session on the new piece through to the
   report card.
3. **Both modes** — run the above once with no `GITHUB_TOKEN` (stub path must still produce a valid
   clickable piece) and once with a token, confirming `GET /health` reports `llm_enabled: true` and
   that generated bodies actually vary between runs. Per `CLAUDE.md`, `llm.py` swallows all provider
   errors, so silent stub fallback is the failure mode to watch for.

## Deliberately out of scope
- **Scatter charts** → Phase B. Bar-only covers the best-demoing trap (truncated axis) and 2 of the 5
  existing pieces. The spec is designed so scatter is purely additive.
- **URL / textbook ingestion.** The issue asks "where to source from? textbook etc?" — answered with
  an optional *paste-your-source-text* textarea. One field, one prompt block, most of the demo value,
  none of the scraping/parsing/licensing surface.
- **Tutor and scoring prompt overrides.** `dialogue.py` and `evaluator.py` keep their hardcoded
  prompts. (Cheap to add later — it's two call sites, `dialogue.py:117` and `evaluator.py:153` — and
  it would want a server-owned, non-editable guardrail suffix so the CLAUDE.md invariants survive
  whatever a teacher types.)
- **Region editing UI.** Regions are derived; a teacher editing them can only break anchoring.

## Notes
- Add `src/backend/app/data/content/generated/` and `src/backend/app/static/generated/` to
  `.gitignore` — LLM-authored content shouldn't land in the repo by accident, and without this every
  generation dirties `git status` mid-hackathon.
- The paste-source-text field is the one place this feature invites PII. It needs inline copy telling
  teachers not to paste student work, and a guardrail forbidding the model from echoing names out of
  source text — worth flagging to the team given there's no auth in front of it yet (issue #10).
- Unrelated but worth 5 minutes before a demo: `evaluator._scoring_schema` uses `minItems`/`maxItems`/
  `minimum`/`maximum` under `strict: true` (`evaluator.py:17-22,35`). Against GitHub Models those may
  400, and `llm.py:56` would swallow it — so scoring silently runs on the heuristic *even with a valid
  token*. The new generation schema deliberately uses none of those keywords.
- Generated pieces carry `generated: true` + `generated_at` + `template_id`; the picker card and
  viewer should show an "AI-generated" badge so provenance is visible to students and teachers.
- Sessions remain in-memory (`store.py`); generated *content* persists, generated *sessions* do not.
  Unchanged behavior, worth knowing during a demo since `--reload` wipes sessions on every save.
- Close via a PR with `Closes #11`, per `CLAUDE.md`.
