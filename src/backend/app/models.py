from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

AnchorKind = Literal["text", "region", "temporal"]


class Anchor(BaseModel):
    """A pointer from a student message to a specific part of the content."""

    kind: AnchorKind
    quote: str | None = None
    start: int | None = None
    end: int | None = None
    region_id: str | None = None
    box: list[float] | None = Field(default=None, description="Normalized x, y, w, h")
    timestamp_s: float | None = None

    @model_validator(mode="after")
    def check_payload(self) -> "Anchor":
        if self.kind == "text" and not self.quote:
            raise ValueError("text anchor requires a quote")
        if self.kind == "region" and not (self.region_id or self.box):
            raise ValueError("region anchor requires region_id or box")
        if self.kind == "temporal" and self.timestamp_s is None:
            raise ValueError("temporal anchor requires timestamp_s")
        return self


class Exchange(BaseModel):
    index: int
    student_message: str
    llm_response: str
    anchor: Anchor | None = None
    anchor_excerpt: str | None = None
    hints_used: int = 0


class DimensionScore(BaseModel):
    dimension: str
    name: str
    score: int = Field(ge=1, le=4)
    evidence_quote: str
    feedback: str


class Report(BaseModel):
    session_id: str
    overall_score: int = Field(ge=1, le=10)
    bloom_level_reached: str
    explanation: str
    dimensions: list[DimensionScore]
    next_step: str
    generated_with_llm: bool


class ExploreMessage(BaseModel):
    student_message: str
    llm_response: str


class ExploreThread(BaseModel):
    """An open-ended, unscored discussion anchored to one spot in the content.

    Deliberately outside the graded Session.exchanges / rubric transcript: this
    is where a student can go deep on something that caught their eye without
    it counting toward, or being capped by, the 3-5 turn graded dialogue.
    """

    anchor_excerpt: str | None = None
    messages: list[ExploreMessage] = Field(default_factory=list)


class Session(BaseModel):
    session_id: str
    content_id: str
    turns_used: int = 0
    min_turns: int
    max_turns: int
    status: Literal["active", "may_conclude", "complete"] = "active"
    exchanges: list[Exchange] = Field(default_factory=list)
    report: Report | None = None
    pending_hints: int = 0
    """Hints requested for the in-progress turn; folded into the next Exchange, then reset."""
    explore: ExploreThread | None = None
    """The one active explore popover, if any. Starting a new one replaces this outright."""

    @property
    def turns_remaining(self) -> int:
        return max(0, self.max_turns - self.turns_used)

    @property
    def can_conclude(self) -> bool:
        return self.turns_used >= self.min_turns


class ContentSummary(BaseModel):
    id: str
    title: str
    subject: str = ""
    blurb: str = ""
    grade_level: int | None = None


class SessionRequest(BaseModel):
    content_id: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    content: dict
    min_turns: int
    max_turns: int
    opening_prompt: str
    llm_enabled: bool


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=2000)
    anchor: Anchor | None = None


class ChatResponse(BaseModel):
    reply: str
    turns_used: int
    turns_remaining: int
    status: str
    is_complete: bool
    anchor_excerpt: str | None = None


class HintRequest(BaseModel):
    session_id: str
    anchor: Anchor | None = None


class HintResponse(BaseModel):
    hint: str
    hint_level: int
    hints_used_this_turn: int
    max_hints_per_turn: int


class ExploreStartRequest(BaseModel):
    session_id: str
    anchor: Anchor


class ExploreStartResponse(BaseModel):
    opening: str
    anchor_excerpt: str | None = None
    max_messages: int


class ExploreMessageRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=2000)


class ExploreMessageResponse(BaseModel):
    reply: str
    messages_used: int
    max_messages: int
