# Architecture — Critical Thinking POC

## Requirements

| # | Requirement |
|---|-------------|
| R1 | A user can go to a web page |
| R2 | The web page displays some information (image or otherwise) |
| R3 | A chatbox is available for the user to interact with the LLM |
| R4 | The user can interact up to **X** times with the LLM (POC: `X = 3`) |
| R5 | A fun screen is shown when they finish interacting |
| R6 | For the POC, the evaluation score, description, and recommendation are displayed to the user |

## System Context

```mermaid
graph LR
    User([Student]) -->|browser| Web[Web App]
    Web -->|REST / JSON| API[Backend API]
    API -->|prompt + context| LLM[(LLM Provider)]
    API --> Store[(Session Store)]
    API --> Content[(Stimulus Content<br/>image / text)]
```

## Component Architecture

```mermaid
graph TB
    subgraph Frontend
        SP[Stimulus Panel<br/>R2]
        CB[Chat Box<br/>R3]
        TC[Turn Counter<br/>R4]
        FS[Fun / Celebration Screen<br/>R5]
        EV[Evaluation Panel<br/>R6]
    end

    subgraph Backend
        SM[Session Manager]
        TG[Turn Guard<br/>enforces max X]
        PB[Prompt Builder]
        EE[Evaluation Engine]
    end

    subgraph External
        LLM[(LLM API)]
        CT[(Content Repo)]
        DB[(Session Store)]
    end

    SP --> SM
    CB --> TG
    TG --> PB
    PB --> LLM
    LLM --> PB
    TG --> TC
    TG -->|turns exhausted| EE
    EE --> LLM
    EE --> EV
    EE --> FS
    SM --> DB
    SM --> CT
```

## Interaction Flow

```mermaid
sequenceDiagram
    actor U as Student
    participant W as Web App
    participant A as Backend API
    participant L as LLM

    U->>W: Open page (R1)
    W->>A: GET /session
    A->>W: session_id + stimulus (R2)
    W->>U: Render stimulus + chatbox (R3)

    loop up to X = 3 turns (R4)
        U->>W: Types message
        W->>A: POST /chat {session_id, message}
        A->>A: Turn guard: turns_used < X?
        A->>L: Prompt (stimulus + history + message)
        L->>A: Response
        A->>W: reply + turns_remaining
        W->>U: Show reply + remaining turns
    end

    A->>L: Evaluate transcript (rubric)
    L->>A: score + description + recommendation
    A->>W: Evaluation payload
    W->>U: Fun screen (R5) + evaluation (R6)
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> Loading
    Loading --> Ready: stimulus fetched
    Ready --> AwaitingLLM: user sends message
    AwaitingLLM --> Ready: reply, turns_used < X
    AwaitingLLM --> Evaluating: turns_used == X
    Evaluating --> Complete: score ready
    Complete --> [*]
```

## Data Model

```mermaid
erDiagram
    SESSION ||--o{ TURN : contains
    SESSION ||--|| STIMULUS : presents
    SESSION ||--o| EVALUATION : produces

    SESSION {
        string session_id PK
        int turns_used
        int max_turns
        string status
    }
    TURN {
        int index PK
        string user_message
        string llm_response
    }
    STIMULUS {
        string id PK
        string type
        string content_url
    }
    EVALUATION {
        int score
        string description
        string recommendation
    }
```

## API Surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/session` | Create session, return `session_id` + stimulus (R1, R2) |
| `POST` | `/chat` | Send a message, return reply + `turns_remaining` (R3, R4) |
| `GET` | `/evaluation/{session_id}` | Return score, description, recommendation (R6) |

## Key Design Decisions

- **Turn limit enforced server-side.** The Turn Guard is authoritative; the frontend counter is display only, so the cap can't be bypassed.
- **Two LLM roles.** One prompt drives the Socratic conversation; a separate rubric prompt scores the transcript. This keeps coaching and grading concerns separate.
- **Evaluation is post-hoc.** Scoring runs only after the final turn, so it can assess the whole arc of reasoning rather than a single message.
- **Stateless frontend.** All session state lives server-side, keyed by `session_id`, so a refresh doesn't reset progress.
- **`X` is configurable.** Set to 3 for the POC, stored as `max_turns` per session.

## Evaluation Output (R6)

The evaluation engine returns three fields, rendered on the completion screen alongside the fun screen:

```json
{
  "score": 7,
  "description": "You questioned the source of the claim and asked what evidence supported it.",
  "recommendation": "Next time, try asking what information is missing before accepting a conclusion."
}
```
