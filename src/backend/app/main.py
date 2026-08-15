from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, dialogue, evaluator, explore, store, teacher
from .anchors import resolve_anchor
from .models import (
    ChatRequest,
    ChatResponse,
    ContentSummary,
    Exchange,
    ExploreMessage,
    ExploreMessageRequest,
    ExploreMessageResponse,
    ExploreStartRequest,
    ExploreStartResponse,
    ExploreThread,
    HintRequest,
    HintResponse,
    Report,
    SessionRequest,
    SessionResponse,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Sockrates API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

# The teacher surface is a router rather than more routes here, to keep this file readable.
app.include_router(teacher.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_enabled": config.llm_enabled(), "model": config.LLM_MODEL}


@app.get("/rubric")
def get_rubric() -> dict:
    return config.load_rubric()


@app.get("/content", response_model=list[ContentSummary])
def list_content() -> list[ContentSummary]:
    return [ContentSummary(**item) for item in config.list_content()]


@app.post("/session", response_model=SessionResponse)
def create_session(request: SessionRequest | None = None) -> SessionResponse:
    content_id = request.content_id if request else None
    try:
        content = config.load_content(content_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown content id: {content_id}") from None
    min_turns, max_turns = config.content_turn_range(content)
    session = store.create(
        content["id"],
        min_turns,
        max_turns,
        request.access_profile if request else None,
    )
    return SessionResponse(
        session_id=session.session_id,
        content=content,
        min_turns=session.min_turns,
        max_turns=session.max_turns,
        opening_prompt=content["opening_prompt"],
        llm_enabled=config.llm_enabled(),
        access_profile=session.access_profile,
    )


@app.post("/hint", response_model=HintResponse)
def hint(request: HintRequest) -> HintResponse:
    session = store.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    # Same authority rule as the turn guard: server decides what's allowed, UI just displays it.
    if session.status == "complete" or session.turns_used >= session.max_turns:
        raise HTTPException(status_code=409, detail="conversation already complete")
    if session.pending_hints >= config.MAX_HINTS_PER_TURN:
        raise HTTPException(status_code=409, detail="no hints remaining for this turn")

    content = config.load_content(session.content_id)
    excerpt = resolve_anchor(request.anchor, content)
    hint_level = session.pending_hints + 1

    text, _used_llm = dialogue.generate_hint(session, content, excerpt, hint_level)

    session.pending_hints = hint_level
    store.save(session)

    return HintResponse(
        hint=text,
        hint_level=hint_level,
        hints_used_this_turn=session.pending_hints,
        max_hints_per_turn=config.MAX_HINTS_PER_TURN,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session = store.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    # Turn guard is authoritative here; the UI counter is display only.
    if session.status == "complete" or session.turns_used >= session.max_turns:
        raise HTTPException(status_code=409, detail="conversation already complete")

    content = config.load_content(session.content_id)
    excerpt = resolve_anchor(request.anchor, content)

    payload, _used_llm = dialogue.generate_followup(session, content, request.message, excerpt)

    session.exchanges.append(
        Exchange(
            index=session.turns_used + 1,
            student_message=request.message,
            llm_response=payload["reply"],
            anchor=request.anchor,
            anchor_excerpt=excerpt,
            hints_used=session.pending_hints,
        )
    )
    session.turns_used += 1
    session.pending_hints = 0

    hit_max = session.turns_used >= session.max_turns
    may_stop_early = session.can_conclude and payload.get("should_conclude", False)

    if hit_max or may_stop_early:
        session.status = "complete"
    elif session.can_conclude:
        session.status = "may_conclude"
    else:
        session.status = "active"

    if session.status == "complete":
        session.report = evaluator.build_report(session, content)

    store.save(session)

    return ChatResponse(
        reply=payload["reply"],
        turns_used=session.turns_used,
        turns_remaining=session.turns_remaining,
        status=session.status,
        is_complete=session.status == "complete",
        anchor_excerpt=excerpt,
    )


@app.post("/explore/start", response_model=ExploreStartResponse)
def explore_start(request: ExploreStartRequest) -> ExploreStartResponse:
    """Open a fresh, unscored discussion anchored to one clicked spot.

    Deliberately not turn-guarded like /chat: this is outside the graded
    dialogue by design. One thread is active per session; starting a new one
    replaces whatever was there before (the popover UI shows one at a time).
    """
    session = store.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    content = config.load_content(session.content_id)
    excerpt = resolve_anchor(request.anchor, content)

    opening, _used_llm = explore.generate_opening(content, excerpt)

    session.explore = ExploreThread(anchor_excerpt=excerpt, messages=[])
    store.save(session)

    return ExploreStartResponse(
        opening=opening,
        anchor_excerpt=excerpt,
        max_messages=config.MAX_EXPLORE_MESSAGES,
    )


@app.post("/explore/message", response_model=ExploreMessageResponse)
def explore_message(request: ExploreMessageRequest) -> ExploreMessageResponse:
    session = store.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.explore is None:
        raise HTTPException(status_code=409, detail="no explore thread started for this session")
    # A generous anti-abuse ceiling, not a pedagogical limit - see MAX_EXPLORE_MESSAGES.
    if len(session.explore.messages) >= config.MAX_EXPLORE_MESSAGES:
        raise HTTPException(status_code=409, detail="explore thread has reached its message limit")

    content = config.load_content(session.content_id)
    reply, _used_llm = explore.generate_reply(session.explore, content, request.message)

    session.explore.messages.append(
        ExploreMessage(student_message=request.message, llm_response=reply)
    )
    store.save(session)

    return ExploreMessageResponse(
        reply=reply,
        messages_used=len(session.explore.messages),
        max_messages=config.MAX_EXPLORE_MESSAGES,
    )


@app.get("/report/{session_id}", response_model=Report)
def get_report(session_id: str) -> Report:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.report is None:
        raise HTTPException(status_code=409, detail="conversation not complete yet")
    return session.report
