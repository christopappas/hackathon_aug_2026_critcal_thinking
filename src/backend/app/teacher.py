"""Teacher portal API.

Generation and publishing are deliberately two steps. Generating writes a draft, and
config.list_content() filters drafts out of the student catalog, so nothing an LLM wrote
can reach a student until a teacher has looked at it and said yes. The gate is structural
rather than a checkbox someone can forget.

Seeded content is read-only through this router. A teacher can generate, edit, publish,
and delete their own pieces; the five hand-authored originals are the floor the demo
always falls back to.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from . import config, generator, importer, templates, validation
from .models import ContentPatch, GenerateRequest, GenerateResponse, ImportRequest, Template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teacher", tags=["teacher"])


def _require_generated(content_id: str) -> dict:
    library = config.load_library()
    content = library.get(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"unknown content id: {content_id}")
    if not content.get("generated"):
        raise HTTPException(
            status_code=403,
            detail="the built-in content pieces cannot be edited or deleted",
        )
    return content


@router.get("/templates", response_model=list[Template])
def list_templates() -> list[Template]:
    return [Template(**item) for item in templates.load_templates().values()]


@router.post("/templates", response_model=Template)
def save_template(template: Template) -> Template:
    return Template(**templates.save(template.model_dump()))


@router.delete("/templates/{template_id}")
def delete_template(template_id: str) -> dict:
    try:
        templates.delete(template_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown template: {template_id}") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    return {"deleted": template_id}


@router.post("/generate", response_model=GenerateResponse)
def generate_content(request: GenerateRequest) -> GenerateResponse:
    try:
        template = templates.get(request.template_id)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"unknown template: {request.template_id}"
        ) from None

    # Checked here rather than inside the prompt, because the offline path never sees a
    # prompt and would otherwise echo the topic straight into student-facing text.
    refusal = generator.check_topic(request.topic)
    if refusal:
        raise HTTPException(status_code=422, detail=refusal)

    payload, used_llm = generator.generate(template, request.model_dump())
    try:
        content = generator.assemble(payload, template, request.model_dump(), used_llm)
    except (ValueError, KeyError) as exc:
        # A malformed spec means the model returned something the renderer cannot draw.
        # Surface it rather than writing a half-built piece.
        logger.warning("generation produced an unrenderable chart: %s", exc)
        raise HTTPException(status_code=422, detail=f"could not render the chart: {exc}") from None

    errors, warnings = validation.validate(content)
    if errors:
        # Nothing publishable came out, so do not leave a broken draft behind.
        generator.delete(content["id"])
        raise HTTPException(status_code=422, detail="; ".join(errors))

    return GenerateResponse(
        content=content,
        warnings=warnings,
        thinking_trap=content.get("thinking_trap", ""),
        generated_with_llm=used_llm,
    )


@router.get("/import/schema")
def import_schema() -> dict:
    """The payload shape, so it can be shown in the UI or handed to a model to fill in."""
    return {"shape": importer.PAYLOAD_SHAPE}


@router.post("/import", response_model=GenerateResponse)
def import_content(request: ImportRequest) -> GenerateResponse:
    """Take a payload written elsewhere -- by hand, or by a model in a chat window.

    Lands as a draft like anything else, so imported content still passes under a
    teacher's eye before a student sees it.
    """
    try:
        content, notes = importer.build(request.payload)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return GenerateResponse(
        content=content,
        warnings=notes,
        thinking_trap=content.get("thinking_trap", ""),
        generated_with_llm=False,
    )


@router.get("/content")
def list_all_content() -> list[dict]:
    """Everything the teacher can see, drafts included, newest last."""
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "subject": item.get("subject", ""),
            "blurb": item.get("blurb", ""),
            "icon": item.get("icon"),
            "grade_level": item.get("grade_level"),
            "generated": item.get("generated", False),
            "review_status": item.get("review_status", "published"),
            "thinking_trap": item.get("thinking_trap", ""),
            "source": item.get("source", {}),
        }
        for item in config.load_library().values()
    ]


@router.get("/content/{content_id}")
def get_content(content_id: str) -> dict:
    content = config.load_library().get(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"unknown content id: {content_id}")
    return content


@router.post("/content/{content_id}/publish")
def publish(content_id: str) -> dict:
    content = dict(_require_generated(content_id))
    errors, warnings = validation.validate(content)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    content["review_status"] = "published"
    generator.write(content)
    return {"id": content_id, "review_status": "published", "warnings": warnings}


@router.post("/content/{content_id}/unpublish")
def unpublish(content_id: str) -> dict:
    content = dict(_require_generated(content_id))
    content["review_status"] = "draft"
    generator.write(content)
    return {"id": content_id, "review_status": "draft"}


@router.put("/content/{content_id}")
def update_content(content_id: str, patch: ContentPatch) -> dict:
    """Edit the words. Chart geometry is not editable, because regions are derived from it."""
    content = dict(_require_generated(content_id))
    for field, value in patch.model_dump(exclude_none=True).items():
        content[field] = value

    errors, _ = validation.validate(content)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    generator.write(content)
    return content


@router.delete("/content/{content_id}")
def delete_content(content_id: str) -> dict:
    _require_generated(content_id)
    generator.delete(content_id)
    return {"deleted": content_id}
