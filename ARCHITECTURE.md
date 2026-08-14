# Architecture — Critical Thinking MVP

## Requirements

### Infrastructure

| # | Requirement |
|---|-------------|
| I1 | A critical-thinking rubric for evaluating a student's level of critical thinking, based on Bloom's Taxonomy |
| I2 | A piece of content to present to the student as the basis for the interaction |
| I3 | A chatbot supporting a 3–5 turn conversational exchange, each message shown as ongoing dialogue |
| I4 | An evaluator that assesses the student's questions and responses against the rubric |
| I5 | A report generator that produces a critical-thinking report card |

### Student Experience

| # | Requirement |
|---|-------------|
| S1 | Student accesses the experience through a web page |
| S2 | Page displays content: text, images, diagrams, charts, animations, videos, or a combination |
| S3 | MVP ships exactly one piece of content |
| S4 | Interface prompts the student to ask a follow-up question or comment |
| S5 | Student can optionally **anchor** a question to part of the content — a text passage, an image/chart region, or a point in an animation/video |
| S6 | System responds with a personalized follow-up designed to deepen thinking |
| S7 | Back-and-forth of ~3–5 exchanges, each follow-up adapting to the previous response |
| S8 | Engaging completion screen at the end |
| S9 | Student receives a score, an explanation of the score, and rubric-tied feedback |

## System Context

```mermaid
graph LR
    Student([Student]) -->|browser| Web[Web App]
    Web -->|REST / JSON| API[Backend API]
    API -->|dialogue + scoring prompts| LLM[(LLM Provider)]
    API --> Sessions[(Session Store)]
    API --> Content[(Content Repo)]
    API --> Rubric[(Bloom Rubric)]
```

## Component Architecture

```mermaid
graph TB
    subgraph Frontend
        CV[Content Viewer<br/>S2 S3]
        AS[Anchor Selector<br/>text / region / timestamp<br/>S5]
        CP[Chat Panel<br/>S4 I3]
        TI[Turn Indicator<br/>S7]
        CS[Completion Screen<br/>S8]
        RC[Report Card View<br/>S9]
    end

    subgraph Backend
        SM[Session Manager]
        CSvc[Content Service<br/>I2]
        AR[Anchor Resolver<br/>maps anchor to excerpt]
        TG[Turn Guard<br/>min 3 max 5]
        DO[Dialogue Orchestrator<br/>adaptive Socratic prompt<br/>S6 S7]
        EV[Evaluator<br/>I4]
        RG[Report Generator<br/>I5]
    end

    subgraph Data
        RB[(Rubric<br/>Bloom levels<br/>I1)]
        DB[(Session Store)]
        CT[(Content Repo)]
    end

    CV --> AS
    AS --> CP
    CP --> TG
    TG --> AR
    AR --> DO
    DO --> CP
    TG --> TI
    TG -->|turns complete| EV
    EV --> RG
    RG --> CS
    RG --> RC

    CSvc --> CT
    CV --> CSvc
    AR --> CSvc
    EV --> RB
    RG --> RB
    SM --> DB
```

## Interaction Flow

```mermaid
sequenceDiagram
    actor U as Student
    participant W as Web App
    participant A as Backend API
    participant D as Dialogue Orchestrator
    participant E as Evaluator
    participant R as Report Generator
    participant L as LLM

    U->>W: Open page
    W->>A: POST /session
    A->>W: session_id + content
    W->>U: Render content + prompt to ask

    loop 3 to 5 exchanges
        U->>W: Select anchor then type question
        W->>A: POST /chat with message and anchor
        A->>A: Turn guard checks limit
        A->>A: Anchor resolver extracts excerpt
        A->>D: history + anchor excerpt + message
        D->>L: Socratic follow-up prompt
        L->>D: Personalized follow-up
        D->>W: reply + turn state
        W->>U: Show reply in dialogue
    end

    A->>E: Full transcript
    E->>L: Rubric scoring prompt
    L->>E: Per-dimension scores + evidence
    E->>R: Scored dimensions
    R->>W: Report card
    W->>U: Completion screen then report card
```

## Turn Policy

The exchange is a **range**, not a fixed count.

```mermaid
stateDiagram-v2
    [*] --> Loading
    Loading --> Ready: content fetched
    Ready --> AwaitingLLM: student sends message
    AwaitingLLM --> Ready: turns < 3
    AwaitingLLM --> MayConclude: turns >= 3 and < 5
    MayConclude --> AwaitingLLM: more evidence needed
    MayConclude --> Evaluating: rubric coverage sufficient
    AwaitingLLM --> Evaluating: turns == 5
    Evaluating --> Reporting: scores ready
    Reporting --> Complete: report card built
    Complete --> [*]
```

- **Minimum 3** exchanges guarantee enough transcript to score fairly.
- **Maximum 5** is a hard server-side stop.
- Between 3 and 5, the orchestrator ends early once every rubric dimension has observable evidence.

## Rubric (I1)

Bloom's Taxonomy provides the level ladder; each dimension is scored 1–4 with a required evidence quote from the transcript.

```mermaid
graph LR
    R1[Remember] --> R2[Understand] --> R3[Apply] --> R4[Analyze] --> R5[Evaluate] --> R6[Create]

    style R1 fill:#eee
    style R2 fill:#e6f0ff
    style R3 fill:#cce0ff
    style R4 fill:#99c2ff
    style R5 fill:#66a3ff
    style R6 fill:#3385ff
```

| Dimension | What it measures | Bloom anchor |
|---|---|---|
| Question Quality | Do questions move beyond recall toward analysis? | Remember → Analyze |
| Evidence & Reasoning | Are claims tied to the content? | Understand → Evaluate |
| Assumption Awareness | Does the student surface unstated assumptions? | Analyze |
| Depth of Follow-up | Does each turn build on the last rather than restart? | Analyze → Evaluate |
| Synthesis | Does the student form a new position or connection? | Evaluate → Create |

## Data Model

```mermaid
erDiagram
    SESSION ||--o{ EXCHANGE : contains
    SESSION ||--|| CONTENT : presents
    SESSION ||--o| REPORT : produces
    EXCHANGE ||--o| ANCHOR : references
    REPORT ||--|{ DIMENSION_SCORE : includes

    SESSION {
        string session_id PK
        int turns_used
        int min_turns
        int max_turns
        string status
    }
    CONTENT {
        string id PK
        string media_type
        string body
        string asset_url
    }
    EXCHANGE {
        int index PK
        string student_message
        string llm_response
    }
    ANCHOR {
        string kind
        string quote
        string region_box
        float timestamp_s
    }
    REPORT {
        int overall_score
        string explanation
        string next_step
    }
    DIMENSION_SCORE {
        string dimension PK
        int score
        string evidence_quote
        string feedback
    }
```

## Anchoring Model (S5)

One polymorphic `anchor` object, optional on every student message:

| Kind | Applies to | Payload |
|---|---|---|
| `text` | text, transcripts | `{ "kind": "text", "start": 120, "end": 168, "quote": "..." }` |
| `region` | image, diagram, chart | `{ "kind": "region", "box": [x, y, w, h] }` normalized 0–1 |
| `temporal` | animation, video | `{ "kind": "temporal", "timestamp_s": 42.5 }` |

The **Anchor Resolver** converts any anchor into a short text excerpt (quoted passage, region caption, or transcript slice) that is injected into the prompt, so the orchestrator stays media-agnostic.

## API Surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/session` | Create session, return `session_id` + content (S1, S2, S3) |
| `POST` | `/chat` | Send message + optional anchor, return follow-up + turn state (S4–S7) |
| `GET` | `/report/{session_id}` | Return report card: score, explanation, rubric feedback (S9) |
| `GET` | `/rubric` | Expose rubric for UI display and transparency (I1) |

## Key Design Decisions

- **Turn limit enforced server-side.** The Turn Guard is authoritative; the frontend indicator is display-only, so the 5-turn cap can't be bypassed.
- **Three LLM roles, separate prompts.** Socratic dialogue, rubric scoring, and report-card prose are distinct calls. Mixing them causes the model to grade while it coaches, which leaks the rubric to the student mid-conversation.
- **Evaluation is post-hoc.** Scoring runs over the whole transcript so it can judge the arc of reasoning — specifically whether later turns built on earlier ones (the Depth of Follow-up dimension), which no single-message scoring can see.
- **Anchors normalize to text.** Resolving every anchor kind to an excerpt keeps one prompt path for all media types and makes new formats additive.
- **Evidence-bound scoring.** Every dimension score must cite a transcript quote, which both curbs hallucinated grading and supplies the explanation required by S9.
- **Rubric is data, not prompt text.** Stored as a structured artifact so the UI, evaluator, and report generator share one source of truth.
- **Stateless frontend.** All session state lives server-side keyed by `session_id`, so a refresh doesn't reset progress.

## Report Card Output (S9)

```json
{
  "overall_score": 7,
  "bloom_level_reached": "Analyze",
  "explanation": "Your questions moved from asking what the chart showed to asking why two variables diverged after 2019.",
  "dimensions": [
    {
      "dimension": "Question Quality",
      "score": 3,
      "evidence_quote": "Why did the two lines diverge after 2019?",
      "feedback": "You moved past recall into causal analysis."
    },
    {
      "dimension": "Assumption Awareness",
      "score": 2,
      "evidence_quote": "So the policy caused the drop.",
      "feedback": "You assumed causation from timing alone. Try asking what else changed that year."
    }
  ],
  "next_step": "Next time, ask what evidence would prove your explanation wrong."
}
```

## MVP Scope

**In:** one hardcoded piece of content (S3), all three anchor kinds, 3–5 turn dialogue, full rubric scoring, report card.

**Out:** authentication, multi-content library, teacher dashboard, persistent database (in-memory sessions are sufficient), longitudinal progress tracking.
