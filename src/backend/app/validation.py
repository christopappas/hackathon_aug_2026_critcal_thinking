"""Checks a generated piece must pass before a teacher can publish it.

Errors block publishing because they break the student experience outright -- a chart that
renders off-canvas, a click region that can never be hit, an image that 404s. Warnings are
judgement calls about whether the writing suits the grade, which is the teacher's call to
make, so they are shown and not enforced.
"""

from __future__ import annotations

from . import config

REQUIRED_KEYS = ("id", "title", "intro", "body", "opening_prompt", "chart", "video")

MIN_BARS, MAX_BARS = 2, 5
MIN_POINTS = 6
BODY_MIN, BODY_MAX = 300, 1400
MAX_AVG_SENTENCE_WORDS = 18


def _check_spec_bounds(spec: dict, errors: list[str]) -> None:
    y_min, y_max = spec.get("y_min"), spec.get("y_max")
    if y_min is None or y_max is None:
        errors.append("Chart is missing its axis range.")
        return
    if y_max <= y_min:
        errors.append(f"Chart axis is inverted or flat (y_min {y_min}, y_max {y_max}).")
        return

    if spec.get("kind") == "bar":
        bars = spec.get("bars") or []
        if not MIN_BARS <= len(bars) <= MAX_BARS:
            errors.append(f"A bar chart needs {MIN_BARS}-{MAX_BARS} bars, got {len(bars)}.")
        for bar in bars:
            value = bar.get("value")
            if value is None:
                errors.append(f"Bar '{bar.get('label', '?')}' has no value.")
            elif not y_min <= value <= y_max:
                # Outside the axis range the bar renders with negative or overflowing
                # height, which is a broken image rather than a debatable one.
                errors.append(
                    f"Bar '{bar.get('label', '?')}' is {value}, outside the axis "
                    f"range {y_min}-{y_max}, so it would render off the chart."
                )
    else:
        points = spec.get("points") or []
        if len(points) < MIN_POINTS:
            errors.append(f"A scatter chart needs at least {MIN_POINTS} points, got {len(points)}.")


def _check_regions(content: dict, errors: list[str]) -> None:
    regions = (content.get("chart") or {}).get("regions") or []
    if not regions:
        errors.append("The chart has no clickable regions, so students could not point at it.")
        return
    for region in regions:
        box = region.get("box") or []
        if len(box) != 4:
            errors.append(f"Region '{region.get('id')}' has a malformed box.")
            continue
        x, y, w, h = box
        if w <= 0 or h <= 0:
            errors.append(f"Region '{region.get('id')}' has no area, so it can never be clicked.")
        if not (0 <= x <= 1 and 0 <= y <= 1 and x + w <= 1.001 and y + h <= 1.001):
            errors.append(f"Region '{region.get('id')}' falls outside the chart.")
        if not region.get("caption"):
            errors.append(f"Region '{region.get('id')}' has no caption for the tutor to quote.")


def _readability_warnings(body: str, warnings: list[str]) -> None:
    sentences = [s for s in body.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if not sentences:
        return
    avg = sum(len(s.split()) for s in sentences) / len(sentences)
    if avg > MAX_AVG_SENTENCE_WORDS:
        warnings.append(
            f"Sentences average {avg:.0f} words, which reads long for grade 6. "
            "Consider shortening before publishing."
        )


def validate(content: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Publishing is blocked only by errors."""
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_KEYS:
        value = content.get(key)
        if value is None or (isinstance(value, (str, dict, list)) and not value):
            errors.append(f"Missing required field: {key}.")

    chart = content.get("chart") or {}
    if chart:
        if not chart.get("alt"):
            errors.append("The chart has no alt text, which students using a screen reader need.")
        spec = chart.get("spec") or {}
        if spec:
            _check_spec_bounds(spec, errors)
        _check_regions(content, errors)

        asset_url = chart.get("asset_url", "")
        if asset_url.startswith("/static/generated/"):
            asset_path = config.GENERATED_STATIC_DIR / asset_url.rsplit("/", 1)[-1]
            if not asset_path.exists():
                errors.append("The chart image was not written to disk.")

    body = content.get("body") or ""
    if body:
        if len(body) < BODY_MIN:
            warnings.append(f"The body is {len(body)} characters, which is short for a full session.")
        elif len(body) > BODY_MAX:
            warnings.append(f"The body is {len(body)} characters, which is long for grade 6.")
        _readability_warnings(body, warnings)

    if not (content.get("video") or {}).get("transcript"):
        warnings.append("No interview transcript, so students cannot anchor to a spoken moment.")

    if not any(bar.get("highlight") for bar in ((chart.get("spec") or {}).get("bars") or [])):
        if (chart.get("spec") or {}).get("kind") == "bar":
            warnings.append("No bar is highlighted, so the chart does not push a claim visually.")

    return errors, warnings
