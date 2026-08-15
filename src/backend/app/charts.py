"""Deterministic chart rendering: a spec in, an SVG and its click regions out.

Why a renderer instead of letting the model draw the SVG:

1. Region boxes and the drawing come from the same numbers, in the same function, so a
   click target can never drift from the thing it is supposed to be pointing at. The model
   supplies captions and values; geometry is ours.
2. The model never emits markup, so nothing it writes can reach a browser as anything but
   escaped text.

The layout constants are lifted from the hand-authored charts in ``static/`` rather than
invented, so generated charts sit next to the originals without looking out of place.
``verify_house_style()`` at the bottom of this module is the check that keeps it that way.

The viewBox must stay 600x400. ``ContentViewer`` normalizes a click against the wrapper
element and ``.chart-wrap img`` is ``width: 100%; height: auto``, so normalized click
coordinates equal normalized viewBox coordinates only while the aspect ratio matches the
seeds. Change the viewBox and every generated chart's anchoring silently skews.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

VIEW_W = 600
VIEW_H = 400

# Plot rectangles, matching static/chart-zapfuel.svg and static/chart.svg respectively.
BAR_PLOT = {"left": 100, "right": 560, "top": 60, "bottom": 340}
SCATTER_PLOT = {"left": 100, "right": 560, "top": 40, "bottom": 320}

INK = "#12263a"
AXIS = "#33475b"
MUTED = "#5b6b7c"
HIGHLIGHT = "#ef476f"
NEUTRAL = "#9aa7b5"
WARN = "#d64545"
DOT = "#2f6feb"
FONT = "Segoe UI, Arial, sans-serif"


def _norm(x: float, y: float, w: float, h: float) -> list[float]:
    """Pixel box to a normalized box, clamped so a click test can never miss the canvas."""
    box = [x / VIEW_W, y / VIEW_H, w / VIEW_W, h / VIEW_H]
    return [round(min(max(value, 0.0), 1.0), 4) for value in box]


def _scale(value: float, lo: float, hi: float, pixel_lo: float, pixel_hi: float) -> float:
    if hi == lo:
        return pixel_lo
    return pixel_lo + (value - lo) / (hi - lo) * (pixel_hi - pixel_lo)


def _ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    step = (hi - lo) / (count - 1)
    return [lo + step * i for i in range(count)]


def _tick_label(value: float, suffix: str) -> str:
    text = f"{value:.0f}" if abs(value - round(value)) < 0.05 else f"{value:.1f}"
    return f"{text}{suffix}"


def _text(x: float, y: float, body: str, **attrs: object) -> str:
    parts = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<text x="{x:.0f}" y="{y:.0f}" {parts}>{escape(body)}</text>'


def _slug(label: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in label]
    return "".join(keep).strip("-").replace("--", "-")[:24] or "series"


def _axis_caption(y_min: float, label: str) -> str:
    """The truncated-axis trap is worth naming in the caption, because that caption is what
    the tutor sees when a student clicks the axis."""
    where = label or "the numbers"
    if y_min > 0:
        return f"the side of the graph, where {where} start at {y_min:.0f} instead of 0"
    return f"the side of the graph, where {where} start at 0"


def _render_bar(spec: dict) -> tuple[list[str], list[dict]]:
    plot = BAR_PLOT
    left, right = plot["left"], plot["right"]
    top, bottom = plot["top"], plot["bottom"]
    y_min, y_max = float(spec["y_min"]), float(spec["y_max"])
    suffix = spec.get("value_suffix", "")
    bars = spec.get("bars") or []

    svg: list[str] = []
    regions: list[dict] = []

    svg.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{AXIS}" stroke-width="2"/>')
    svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="{AXIS}" stroke-width="2"/>')

    for tick in _ticks(y_min, y_max):
        ty = _scale(tick, y_min, y_max, bottom, top)
        label = _tick_label(tick, suffix)
        # Nudge wider labels left so they stay clear of the axis, as the authored files do.
        tx = 62 if len(label) <= 3 else 58
        svg.append(_text(tx, ty + 5, label, font_size=11, fill=AXIS))

    regions.append(
        {
            "id": "y-axis",
            "box": _norm(left - 76, top - 8, 78, (bottom - top) + 12),
            "caption": _axis_caption(y_min, spec.get("y_label", "")),
        }
    )

    slot = (right - left) / max(len(bars), 1)
    bar_w = round(slot * 0.48)
    ranked = sorted(range(len(bars)), key=lambda i: float(bars[i]["value"]), reverse=True)
    tallest = ranked[0] if ranked else -1

    for i, bar in enumerate(bars):
        value = float(bar["value"])
        bx = left + i * slot + (slot - bar_w) / 2
        by = _scale(value, y_min, y_max, bottom, top)
        bh = bottom - by
        fill = HIGHLIGHT if bar.get("highlight") else NEUTRAL
        label_fill = HIGHLIGHT if bar.get("highlight") else MUTED
        value_label = bar.get("value_label") or _tick_label(value, suffix)

        svg.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{fill}"/>')
        svg.append(
            _text(bx + bar_w / 2, by - 10, value_label, text_anchor="middle", font_size=14,
                  font_weight=700, fill=label_fill)
        )
        svg.append(
            _text(bx + bar_w / 2, bottom + 22, bar["label"], text_anchor="middle", font_size=13, fill=INK)
        )
        if bar.get("sublabel"):
            # Sits between the bar label and the footnote; both offsets are tuned
            # together in FOOTNOTE_Y so the two rows never touch.
            svg.append(
                _text(bx + bar_w / 2, bottom + 36, bar["sublabel"], text_anchor="middle",
                      font_size=11, fill=MUTED)
            )

        size_word = "tall" if i == tallest and len(bars) > 1 else "short"
        regions.append(
            {
                "id": f"bar-{_slug(bar['label'])}",
                "box": _norm(bx, by, bar_w, bh),
                "caption": f"the {size_word} {bar['label']} bar showing {value_label}",
            }
        )

    return svg, regions


def _render_scatter(spec: dict) -> tuple[list[str], list[dict]]:
    plot = SCATTER_PLOT
    left, right = plot["left"], plot["right"]
    top, bottom = plot["top"], plot["bottom"]
    y_min, y_max = float(spec["y_min"]), float(spec["y_max"])
    x_min, x_max = float(spec.get("x_min", 0)), float(spec.get("x_max", 1))
    suffix = spec.get("value_suffix", "")
    points = spec.get("points") or []

    svg: list[str] = []
    regions: list[dict] = []

    svg.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{AXIS}" stroke-width="2"/>')
    svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="{AXIS}" stroke-width="2"/>')

    for tick in _ticks(y_min, y_max):
        ty = _scale(tick, y_min, y_max, bottom, top)
        svg.append(_text(58, ty + 5, _tick_label(tick, suffix), font_size=11, fill=AXIS))
    for tick in _ticks(x_min, x_max, 4):
        tx = _scale(tick, x_min, x_max, left, right)
        svg.append(_text(tx, bottom + 20, _tick_label(tick, ""), text_anchor="middle", font_size=11, fill=AXIS))

    regions.append(
        {
            "id": "y-axis",
            "box": _norm(left - 88, top, 96, (bottom - top) + 20),
            "caption": _axis_caption(y_min, spec.get("y_label", "")),
        }
    )

    plotted = []
    for point in points:
        px = _scale(float(point["x"]), x_min, x_max, left, right)
        py = _scale(float(point["y"]), y_min, y_max, bottom, top)
        outlier = bool(point.get("outlier"))
        plotted.append((px, py, outlier))
        fill = WARN if outlier else DOT
        svg.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="5" fill="{fill}" opacity="0.8"/>')

    ordinary = [(px, py) for px, py, outlier in plotted if not outlier]
    if len(ordinary) >= 2:
        n = len(ordinary)
        mean_x = sum(px for px, _ in ordinary) / n
        mean_y = sum(py for _, py in ordinary) / n
        denominator = sum((px - mean_x) ** 2 for px, _ in ordinary)
        slope = (
            sum((px - mean_x) * (py - mean_y) for px, py in ordinary) / denominator
            if denominator
            else 0.0
        )
        y1 = mean_y + slope * (left - mean_x)
        y2 = mean_y + slope * (right - mean_x)
        svg.append(
            f'<line x1="{left}" y1="{y1:.0f}" x2="{right}" y2="{y2:.0f}" stroke="{WARN}" '
            f'stroke-width="2" stroke-dasharray="6 5"/>'
        )
        ty, by = min(y1, y2), max(y1, y2)
        regions.append(
            {
                "id": "trend-line",
                "box": _norm(left - 12, ty - 12, (right - left) + 24, (by - ty) + 24),
                "caption": spec.get("trend_caption") or "the dotted line drawn through the dots",
            }
        )

    outliers = [(px, py) for px, py, outlier in plotted if outlier]
    if outliers:
        xs = [px for px, _ in outliers]
        ys = [py for _, py in outliers]
        # Emitted after trend-line and smaller than it, which is what makes anchors.py
        # resolve a click inside both to the outliers -- the more specific answer.
        regions.append(
            {
                "id": "outliers",
                "box": _norm(min(xs) - 24, min(ys) - 24, (max(xs) - min(xs)) + 48, (max(ys) - min(ys)) + 48),
                "caption": spec.get("outlier_caption") or "the dots that do not follow the pattern",
            }
        )

    return svg, regions


ANN_W = 148

# Low enough to clear a bar's sublabel row at bottom + 36, high enough that
# descenders still fit inside the 400pt canvas.
FOOTNOTE_Y = VIEW_H - 8


def _annotation_anchor(spec: dict, kind: str) -> tuple[float, float]:
    """Find somewhere the callout will not land on top of the data.

    A fixed position collides the moment the chart has a tall bar on that side --
    the value label and the callout end up on the same pixels. So place it over
    whatever is shortest, which is by definition where the headroom is.
    """
    y_min, y_max = float(spec["y_min"]), float(spec["y_max"])

    if kind == "bar":
        plot = BAR_PLOT
        bars = spec.get("bars") or []
        if not bars:
            return plot["left"] + 12, plot["top"] + 20
        slot = (plot["right"] - plot["left"]) / len(bars)
        # The shortest bar leaves the most room above it.
        i = min(range(len(bars)), key=lambda j: float(bars[j]["value"]))
        centre = plot["left"] + i * slot + slot / 2
        x = centre - ANN_W / 2
        # Sit just under the title, clear of the shortest bar's own value label.
        y = plot["top"] - 4
    else:
        plot = SCATTER_PLOT
        x_min, x_max = float(spec.get("x_min", 0)), float(spec.get("x_max", 1))
        points = spec.get("points") or []
        mid_x = (x_min + x_max) / 2
        mid_y = (y_min + y_max) / 2
        # Count what sits in each top corner and take the emptier one.
        top_left = sum(1 for p in points if p["x"] < mid_x and p["y"] > mid_y)
        top_right = sum(1 for p in points if p["x"] >= mid_x and p["y"] > mid_y)
        x = plot["left"] + 16 if top_left <= top_right else plot["right"] - ANN_W - 4
        y = plot["top"] + 14

    return max(24, min(x, VIEW_W - ANN_W - 12)), y


def render(spec: dict) -> tuple[str, list[dict]]:
    """Return the SVG markup and the normalized regions that match it exactly."""
    kind = spec.get("kind", "bar")
    if kind not in ("bar", "scatter"):
        raise ValueError(f"unsupported chart kind: {kind}")

    body, regions = (_render_bar if kind == "bar" else _render_scatter)(spec)
    bottom = (BAR_PLOT if kind == "bar" else SCATTER_PLOT)["bottom"]
    ann_x, ann_y = _annotation_anchor(spec, kind)

    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}" '
        f'width="{VIEW_W}" height="{VIEW_H}" font-family="{FONT}">',
        f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="#ffffff"/>',
    ]
    if spec.get("title"):
        head.append(
            _text(VIEW_W / 2, 28, spec["title"], text_anchor="middle", font_size=16,
                  font_weight=600, fill=INK)
        )

    tail: list[str] = []
    annotation = spec.get("annotation")
    if annotation:
        # Wrap by hand: SVG text does not, and an unwrapped callout runs off the canvas.
        words, lines, current = annotation.split(), [], ""
        for word in words:
            if len(current) + len(word) + 1 > 22:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            lines.append(current)
        for offset, line in enumerate(lines):
            tail.append(_text(ann_x, ann_y + offset * 16, line, font_size=11, fill=WARN))
        regions.append(
            {
                "id": "annotation",
                "box": _norm(ann_x - 8, ann_y - 14, 148, len(lines) * 16 + 8),
                "caption": spec.get("annotation_caption") or f"the note reading \"{annotation}\"",
            }
        )

    footnote = spec.get("footnote")
    if footnote:
        tail.append(_text(30, FOOTNOTE_Y, footnote, font_size=11, fill=MUTED))
        regions.append(
            {
                "id": "footnote",
                "box": _norm(24, FOOTNOTE_Y - 18, 460, 26),
                "caption": spec.get("footnote_caption") or f"the small note saying {footnote}",
            }
        )

    return "\n  ".join(head + body + tail) + "\n</svg>\n", regions


# The five authored charts define the house style. This reproduces two of them from specs
# so a change to the constants above fails loudly instead of quietly producing charts that
# no longer match -- and, more importantly, region boxes that no longer match the drawing.
def verify_house_style() -> list[str]:
    """Return a list of mismatches against the hand-authored files. Empty means correct."""
    problems: list[str] = []

    _, regions = render(
        {
            "kind": "bar",
            "y_min": 80,
            "y_max": 100,
            "value_suffix": "%",
            "bars": [
                {"label": "ZapFuel", "value": 90, "highlight": True},
                {"label": "Leading brand", "value": 85, "highlight": False},
            ],
        }
    )
    by_id = {region["id"]: region["box"] for region in regions}
    expected = {
        "y-axis": [0.04, 0.13, 0.13, 0.73],
        "bar-zapfuel": [0.2667, 0.5, 0.1833, 0.35],
    }
    for region_id, want in expected.items():
        got = by_id.get(region_id)
        if got is None:
            problems.append(f"bar chart: missing region {region_id}")
        elif any(abs(a - b) > 0.005 for a, b in zip(got, want)):
            problems.append(f"bar chart region {region_id}: got {got}, authored {want}")

    _, scatter_regions = render(
        {
            "kind": "scatter",
            "y_min": 60,
            "y_max": 100,
            "x_min": 0,
            "x_max": 6,
            "points": [{"x": 1, "y": 88, "outlier": False}, {"x": 5, "y": 71, "outlier": False}],
        }
    )
    scatter_axis = {r["id"]: r["box"] for r in scatter_regions}.get("y-axis")
    want_axis = [0.02, 0.1, 0.16, 0.75]
    if scatter_axis is None:
        problems.append("scatter chart: missing y-axis region")
    elif any(abs(a - b) > 0.005 for a, b in zip(scatter_axis, want_axis)):
        problems.append(f"scatter y-axis region: got {scatter_axis}, authored {want_axis}")

    return problems
