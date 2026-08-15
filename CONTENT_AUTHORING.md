# Authoring content

How to add a new piece for students to question — by hand, or by asking a model for it.

Three ways in, in rough order of how often you will want them:

| | Use it when |
|---|---|
| **Teacher portal** — <http://localhost:5173/teacher> | You want something quickly from a template. No JSON. |
| **Import a payload** — this document | You wrote it, or a model wrote it for you. Full control. |
| **Hand-authored JSON** in `src/backend/app/data/content/` | It is a permanent part of the library and belongs in git. |

## The command

```bash
cd src/backend && .venv/bin/python -m app.importer examples/bar-chart-piece.json
```

That lands it as a **draft**. Add `--publish` to make it live for students immediately:

```bash
cd src/backend && .venv/bin/python -m app.importer examples/bar-chart-piece.json --publish
```

Or skip the terminal: **Import a piece** in the teacher portal takes the same JSON pasted into a box.

Print the payload shape any time:

```bash
cd src/backend && .venv/bin/python -m app.importer --schema
```

Working examples live in [`src/backend/examples/`](src/backend/examples/) — copy one and edit it:

- `bar-chart-piece.json` — bar chart, truncated axis
- `scatter-chart-piece.json` — scatter plot, correlation-as-cause
- `custom-svg-piece.json` — a pie chart the built-in renderer cannot draw, so it brings its own SVG

## The JSON

Every field below is required unless marked optional.

```jsonc
{
  "title":          "The Reading App That Made Us Winners",
  "subject":        "Data and graphs",   // Data and graphs | Ads and media | Science news
                                         // | Computer science | Everyday claims
  "blurb":          "One sentence for the picker card.",
  "icon":           "📚",                 // single emoji, shown on the card
  "grade_level":    6,                    // optional, defaults to 6
  "intro":          "One line saying where this came from.",

  // The flawed text the student questions. 4-8 sentences, grade-6 words.
  // Write it in the confident voice of whoever made it. It must never hedge
  // or hint that anything is wrong.
  "body":           "The new reading app is working. Last year, 41 out of 100 ...",

  "opening_prompt": "Read the newsletter and look at the chart. What is one question you
                     would ask before you believe it? You can highlight a sentence or click
                     a part of the chart to show what you mean.",

  // TEACHER ONLY. Never rendered to students. Put the explanation of the flaw
  // here and nowhere else -- if it leaks into body, the exercise is ruined.
  "thinking_trap":  "The axis starts at 35, so a 17-point rise is drawn as a bar more than
                     twice as tall ...",

  "chart_alt":      "Alt text describing the chart for screen readers.",

  // Four short lines. Students can click one to anchor a question to it.
  // Good place to let someone let slip the thing the body hides.
  "transcript": [
    { "t": 0.0, "text": "Reporter: Did any classes not use the app?" },
    { "t": 9.0, "text": "Coordinator: No, we rolled it out to everyone at once." }
  ],

  // Then EXACTLY ONE of the two chart modes below.
  "chart": { ... }
}
```

### Chart mode A — a spec (use this one)

You give numbers and words; the renderer draws the picture **and works out the click regions
from the same numbers**, so they can never drift apart.

```jsonc
"chart": {
  "kind":         "bar",              // "bar" or "scatter"
  "title":        "Sixth graders who hit their reading goal",
  "y_label":      "the counts",       // plain words, used in the y-axis click caption
  "y_min":        35,                 // <-- start above 0 and you have a truncated-axis trap
  "y_max":        65,
  "value_suffix": "",                 // "%" or ""
  "x_label":      "",                 // scatter only
  "x_min":        0,                  // scatter only
  "x_max":        1,                  // scatter only
  "annotation":   "Axis starts at 35, not 0.",   // optional, null to omit
  "footnote":     "Two different groups of students, and a different test each year.",

  // BAR: 2-5 bars. Every value must sit between y_min and y_max.
  "bars": [
    { "label": "Last year", "sublabel": "no app",   "value": 41, "value_label": "41", "highlight": false },
    { "label": "This year", "sublabel": "with app", "value": 58, "value_label": "58", "highlight": true }
  ],

  // SCATTER: 6+ points, a few marked outlier so students can find cases
  // that break the pattern. Mark 3-4 of 14-22 for a good spread.
  "points": []
}
```

**Both `bars` and `points` must be present.** A bar chart sends `"points": []`, a scatter sends
`"bars": []`. Regions come out as `y-axis`, one per bar (or `trend-line` and `outliers` for
scatter), plus `annotation` and `footnote`.

### Chart mode B — your own SVG

For pictures the renderer cannot draw: pie charts, diagrams, annotated screenshots. Replace
`"chart"` with these two keys.

```jsonc
"chart_svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 600 400\">...</svg>",

"chart_regions": [
  { "id": "design-b-slice", "box": [0.42, 0.22, 0.34, 0.44], "caption": "the big slice for Design B" },
  { "id": "vote-count",     "box": [0.04, 0.90, 0.76, 0.08], "caption": "the note saying only 34 students voted" }
]
```

`box` is `[x, y, width, height]` as fractions of the image, `0`–`1` from the top-left. The
caption is what the tutor says the student pointed at, so write it as a phrase that reads
naturally after "the chart region showing ___".

Three rules the importer enforces:

- **`viewBox` must be `0 0 600 400`.** A different aspect ratio is rejected, because clicks are
  normalized against the image box — change the ratio and every region silently misses.
- **`chart_regions` cannot be empty.** Otherwise students have nothing to click.
- **The SVG is sanitized.** `<script>`, `on*=` handlers, `<image>`, and any external `href` are
  stripped, and the importer tells you what it removed.

Overlapping boxes are fine and useful: a click resolves to the **smallest** region containing
it, so a small `outliers` box inside a big `trend-line` box gives the more specific answer.

**You own the alignment in this mode.** Open the draft in the teacher portal, turn on *Show the
clickable regions*, and click around — it reports exactly what a student would point at.

## After importing

Everything arrives as a **draft**. Drafts are invisible to students until someone publishes
them, which is the review step for anything a model wrote. In the portal you can preview it as a
student, check the regions, edit the words, then publish or delete.

Generated and imported files land in `src/backend/app/data/content/generated/` and
`app/static/generated/`. Both are gitignored — if a piece should be permanent, move its JSON
into `app/data/content/` and its SVG into `app/static/`, and commit them.

## Writing good ones

The flaw is the whole point. A piece works when a curious 11-year-old can find the problem by
asking questions, and fails when the problem is either invisible or announced.

- **Confident voice, no hedging.** It should read like a real newsletter, ad, or poster.
- **Bury the tell in the footnote and the transcript.** Sample size, who paid, what else
  changed. Never in the body.
- **Traps that work:** truncated axis · sample of one · correlation read as cause · a survey the
  seller paid for · a comparison where two things changed at once · a percentage with no
  denominator · cherry-picked date range.
- **Keep it invented.** Made-up brands, schools, and studies. Never a real company, person, or
  organisation, and never a real statistic presented as fact.
- **Keep it classroom-safe.** School, sports, snacks, games, gadgets, hobbies, pets. Not health,
  politics, religion, race, crime, disasters, or anything frightening. Portal generation
  rejects these topics outright; the importer does not check your prose, so this one is on you.

## Asking a model to write one

This works well — hand it the shape and the constraints:

> Write a content piece for our critical-thinking app as JSON matching the structure in
> `CONTENT_AUTHORING.md`. Topic: `<your topic>`. The trap should be `<the flaw>`. Grade 6
> reading level, invented brands and schools only, everyday classroom subject matter. Put the
> explanation of the flaw in `thinking_trap` only — it must not appear anywhere the student can
> read. Use chart mode A with a `bar` chart.

Then save what it gives you and run the importer. Preview before you publish — that step exists
because a model will occasionally explain its own trick inside `body`.
