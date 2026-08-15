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


class Session(BaseModel):
    session_id: str
    content_id: str
    turns_used: int = 0
    min_turns: int
    max_turns: int
    status: Literal["active", "may_conclude", "complete"] = "active"
    exchanges: list[Exchange] = Field(default_factory=list)
    report: Report | None = None

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
    icon: str | None = None
    generated: bool = False


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


class Template(BaseModel):
    """A starting point a teacher edits before generating. Seeds are read-only."""

    id: str
    name: str
    description: str = ""
    icon: str = "📝"
    trap: str = ""
    subject: str = ""
    chart_kind: Literal["bar", "scatter"] = "bar"
    generation_instructions: str = ""
    offline_draft: dict = Field(default_factory=dict)
    builtin: bool = False


class GenerateRequest(BaseModel):
    template_id: str
    topic: str = Field(min_length=1, max_length=200)
    extra_instructions: str = Field(default="", max_length=2000)
    source_text: str = Field(default="", max_length=6000)
    grade_level: int = Field(default=6, ge=1, le=12)
    generation_instructions: str | None = Field(default=None, max_length=4000)


class GenerateResponse(BaseModel):
    content: dict
    warnings: list[str] = Field(default_factory=list)
    thinking_trap: str = ""
    generated_with_llm: bool = False


class ImportRequest(BaseModel):
    """A content piece authored outside the app — by hand or by a model elsewhere."""

    payload: dict


class ContentPatch(BaseModel):
    """Fields a teacher may edit after generation. Chart geometry is not among them."""

    title: str | None = None
    subject: str | None = None
    blurb: str | None = None
    intro: str | None = None
    body: str | None = None
    opening_prompt: str | None = None
    icon: str | None = None
