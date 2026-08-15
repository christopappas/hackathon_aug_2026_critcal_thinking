from __future__ import annotations

from .models import Anchor


def _box_center(box: list[float]) -> tuple[float, float]:
    x, y, w, h = box
    return x + w / 2, y + h / 2


def _point_in_box(px: float, py: float, box: list[float]) -> bool:
    x, y, w, h = box
    return x <= px <= x + w and y <= py <= y + h


def resolve_anchor(anchor: Anchor | None, content: dict) -> str | None:
    """Turn any anchor kind into a short text excerpt for the prompt.

    Keeping every media type on one text path means the dialogue and scoring
    prompts never need to know which format the student pointed at.
    """
    if anchor is None:
        return None

    if anchor.kind == "text":
        return f'the passage "{anchor.quote.strip()}"'

    if anchor.kind == "region":
        regions = content.get("chart", {}).get("regions", [])
        if anchor.region_id:
            for region in regions:
                if region["id"] == anchor.region_id:
                    return f"the chart region showing {region['caption']}"
        if anchor.box:
            px, py = _box_center(anchor.box)
            # Regions overlap, so prefer the smallest containing one; the tightest
            # box is the most specific thing the student could have meant.
            matches = [r for r in regions if _point_in_box(px, py, r["box"])]
            if matches:
                best = min(matches, key=lambda r: r["box"][2] * r["box"][3])
                return f"the chart region showing {best['caption']}"
            return "an unlabeled area of the chart"
        return "a region of the chart"

    if anchor.kind == "temporal":
        transcript = content.get("video", {}).get("transcript", [])
        if not transcript:
            return f"the moment at {anchor.timestamp_s:.0f} seconds"
        chosen = transcript[0]
        for line in transcript:
            if line["t"] <= anchor.timestamp_s:
                chosen = line
            else:
                break
        return f'the moment at {anchor.timestamp_s:.0f}s where the clip says "{chosen["text"]}"'

    return None
