"""Import an authored content piece — written by hand, or by a model in a chat window.

This is the path for content that did not come from the in-app generator: you write the
prose and the chart, and this turns it into a real library entry, through the same
renderer, the same validator, and the same draft gate as everything else.

A payload picks one of two chart modes:

  "chart": {...spec...}                     rendered by charts.py, regions derived.
                                            Boxes cannot drift from the drawing.

  "chart_svg": "<svg .../>",                your own drawing, used as-is after
  "chart_regions": [{id, box, caption}]     sanitizing. You own the alignment between
                                            the boxes and the picture, so check it in
                                            the portal preview before publishing.

Prefer the spec mode. Reach for raw SVG when you need a picture the renderer cannot
draw — a diagram, an annotated screenshot, a chart shape with no spec support yet.

Usage:
    python -m app.importer piece.json            # import as a draft
    python -m app.importer piece.json --publish   # import and make it live
    python -m app.importer --schema               # print the payload shape
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from . import charts, config, generator, validation

SVG_NS = "http://www.w3.org/2000/svg"

# Drawing elements only. Anything that can fetch, script, or embed arbitrary content is
# dropped rather than escaped, because an imported SVG is served to a browser verbatim.
ALLOWED_TAGS = {
    "svg", "g", "defs", "title", "desc", "rect", "circle", "ellipse", "line",
    "polyline", "polygon", "path", "text", "tspan", "linearGradient",
    "radialGradient", "stop", "marker", "clipPath", "use",
}
DROPPED_TAGS = {"script", "foreignObject", "image", "iframe", "animate", "set", "a"}


def sanitize_svg(markup: str) -> tuple[str, list[str]]:
    """Strip anything that is not drawing. Returns (clean_markup, what_was_removed)."""
    removed: list[str] = []

    try:
        root = ET.fromstring(markup.strip())
    except ET.ParseError as exc:
        raise ValueError(f"chart_svg is not well-formed XML: {exc}") from None

    if root.tag not in (f"{{{SVG_NS}}}svg", "svg"):
        raise ValueError("chart_svg must have <svg> as its root element")

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def clean(element: ET.Element) -> None:
        for child in list(element):
            name = local(child.tag)
            if name in DROPPED_TAGS or name not in ALLOWED_TAGS:
                removed.append(f"<{name}>")
                element.remove(child)
                continue
            clean(child)

        for attr in list(element.attrib):
            attr_local = local(attr).lower()
            value = element.attrib[attr]
            # Event handlers, and any reference that could leave the page.
            if attr_local.startswith("on"):
                removed.append(f"{attr_local}=")
                del element.attrib[attr]
            elif attr_local in ("href", "xlink:href") and not value.startswith("#"):
                removed.append(f"{attr_local}={value[:24]}")
                del element.attrib[attr]
            elif "javascript:" in value.lower() or "url(http" in value.lower():
                removed.append(f"{attr_local}(external)")
                del element.attrib[attr]

    clean(root)

    # The viewBox is the contract with the click handler: normalized click coordinates
    # only equal normalized viewBox coordinates while the aspect ratio matches the seeds.
    want = f"0 0 {charts.VIEW_W} {charts.VIEW_H}"
    if root.get("viewBox", "").strip() != want:
        raise ValueError(
            f'chart_svg must use viewBox="{want}" so click regions line up with the '
            f'drawing (got {root.get("viewBox") or "none"!r})'
        )
    root.set("width", str(charts.VIEW_W))
    root.set("height", str(charts.VIEW_H))

    ET.register_namespace("", SVG_NS)
    return ET.tostring(root, encoding="unicode"), removed


def _normalize_regions(regions: list[dict]) -> list[dict]:
    cleaned = []
    for i, region in enumerate(regions):
        box = [float(v) for v in region["box"]]
        if len(box) != 4:
            raise ValueError(f"region {region.get('id', i)} needs a box of [x, y, w, h]")
        cleaned.append(
            {
                "id": region.get("id") or f"region-{i + 1}",
                "box": [round(min(max(v, 0.0), 1.0), 4) for v in box],
                "caption": region["caption"],
            }
        )
    return cleaned


def build(payload: dict) -> tuple[dict, list[str]]:
    """Turn an authored payload into a content piece on disk. Returns (content, notes)."""
    notes: list[str] = []
    has_spec = isinstance(payload.get("chart"), dict)
    has_svg = bool(payload.get("chart_svg"))

    if has_spec == has_svg:
        raise ValueError("provide exactly one of 'chart' (a spec) or 'chart_svg' (raw markup)")

    if has_spec:
        spec = payload["chart"]
        svg, regions = charts.render(spec)
    else:
        spec = None
        svg, removed = sanitize_svg(payload["chart_svg"])
        if removed:
            notes.append(f"Removed from the SVG: {', '.join(sorted(set(removed)))}")
        raw_regions = payload.get("chart_regions") or []
        if not raw_regions:
            raise ValueError("chart_svg needs chart_regions, or students cannot click the picture")
        regions = _normalize_regions(raw_regions)
        notes.append(
            "Regions were supplied rather than derived. Check them against the drawing "
            "in the portal preview before publishing."
        )

    slug = generator._unique_slug(payload.get("id") or payload.get("title", "lesson"))

    config.GENERATED_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (config.GENERATED_STATIC_DIR / f"{slug}.svg").write_text(svg, encoding="utf-8")

    chart: dict = {
        "asset_url": f"/static/generated/{slug}.svg",
        "alt": payload.get("chart_alt", ""),
        "regions": regions,
    }
    if spec is not None:
        chart["spec"] = spec

    content = {
        "id": slug,
        "order": generator._next_order(),
        "grade_level": payload.get("grade_level", 6),
        "title": payload.get("title", "Untitled"),
        "subject": payload.get("subject", ""),
        "blurb": payload.get("blurb", ""),
        "icon": payload.get("icon", "🆕"),
        "media_type": "mixed",
        "intro": payload.get("intro", ""),
        "body": payload.get("body", ""),
        "chart": chart,
        "video": {"asset_url": None, "transcript": payload.get("transcript") or []},
        "opening_prompt": payload.get("opening_prompt", ""),
        "review_status": "draft",
        "thinking_trap": payload.get("thinking_trap", ""),
        "source": {
            "template_id": None,
            "topic": payload.get("topic", ""),
            "generated_with_llm": False,
            "imported": True,
            "chart_mode": "spec" if spec is not None else "svg",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }

    errors, warnings = validation.validate(content)
    if errors:
        # Do not leave a broken piece and its orphan image behind.
        generator.delete(slug)
        raise ValueError("; ".join(errors))

    generator.write(content)
    return content, notes + warnings


PAYLOAD_SHAPE = """{
  "title":          "Short, in the voice of whoever made it",
  "subject":        "Data and graphs | Ads and media | Science news | Computer science | Everyday claims",
  "blurb":          "One sentence for the picker card",
  "icon":           "single emoji",
  "grade_level":    6,
  "intro":          "One line framing where this came from",
  "body":           "The flawed text the student questions, 4-8 sentences",
  "opening_prompt": "What is one question you would ask before you believe it? ...",
  "thinking_trap":  "Teacher-only explanation of the flaw. Never shown to students.",
  "chart_alt":      "Alt text for the chart",
  "transcript":     [{"t": 0.0, "text": "Reporter: ..."}],

  // ONE of the following two chart modes:

  "chart": {                                  // MODE A - rendered, regions derived
    "kind": "bar",                            //   "bar" or "scatter"
    "title": "Chart title",
    "y_label": "the percents", "y_min": 80, "y_max": 100, "value_suffix": "%",
    "x_label": "", "x_min": 0, "x_max": 1,
    "annotation": "Axis starts at 80%, not 0%.",
    "footnote": "Based on 10 students at the tent.",
    "bars":   [{"label": "Brand", "sublabel": null, "value": 90,
                "value_label": "90%", "highlight": true}],
    "points": [{"x": 1.0, "y": 88, "outlier": false}]
  },

  "chart_svg":     "<svg viewBox=\\"0 0 600 400\\">...</svg>",   // MODE B - your drawing
  "chart_regions": [{"id": "y-axis", "box": [0.04, 0.13, 0.13, 0.73],
                     "caption": "the side of the graph, where ..."}]
}"""


def main(argv: list[str]) -> int:
    if "--schema" in argv:
        print(PAYLOAD_SHAPE)
        return 0

    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        print(__doc__)
        return 2

    publish = "--publish" in argv
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"not found: {path}")
            return 1
        try:
            content, notes = build(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, KeyError) as exc:
            print(f"FAILED {path.name}: {exc}")
            return 1

        if publish:
            content["review_status"] = "published"
            generator.write(content)

        state = "published" if publish else "draft (publish it in the teacher portal)"
        print(f"imported '{content['id']}' as {state}")
        print(f"  chart  : {content['chart']['asset_url']}")
        print(f"  regions: {', '.join(r['id'] for r in content['chart']['regions'])}")
        for note in notes:
            print(f"  note   : {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
