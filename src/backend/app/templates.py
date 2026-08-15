"""The template library: starting points a teacher edits before generating.

Templates are data, for the same reason the rubric is data -- the portal, the generator,
and the offline fallback all read one definition rather than three copies drifting apart.

Seeded templates ship with the repo and are read-only. Editing one and saving writes a
copy into ``templates/custom/``, which is gitignored, so a teacher can never leave the
team without the starting points they began from.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from . import config

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "template") -> str:
    # Strip again after truncating: cutting at 48 can land mid-word and leave a trailing dash.
    slug = SLUG_RE.sub("-", text.lower()).strip("-")[:48].strip("-")
    return slug or fallback


@lru_cache(maxsize=1)
def load_templates() -> dict[str, dict]:
    """Every template keyed by id, seeds first, then custom ones."""
    templates: dict[str, dict] = {}
    for directory, builtin in ((config.TEMPLATE_DIR, True), (config.CUSTOM_TEMPLATE_DIR, False)):
        for path in sorted(directory.glob("*.json")):
            template = json.loads(path.read_text(encoding="utf-8"))
            template["builtin"] = builtin
            templates[template["id"]] = template
    return templates


def reload_templates() -> None:
    load_templates.cache_clear()


def get(template_id: str) -> dict:
    templates = load_templates()
    if template_id not in templates:
        raise KeyError(template_id)
    return templates[template_id]


def save(template: dict) -> dict:
    """Write a custom template. Saving over a seed id forks it instead of overwriting."""
    template = dict(template)
    template_id = slugify(template.get("id") or template.get("name", ""))
    existing = load_templates().get(template_id)
    if existing is not None and existing.get("builtin"):
        template_id = _unique_id(f"{template_id}-custom")
    template["id"] = template_id
    template["builtin"] = False

    path = config.CUSTOM_TEMPLATE_DIR / f"{template_id}.json"
    path.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")
    reload_templates()
    return load_templates()[template_id]


def delete(template_id: str) -> None:
    """Remove a custom template. Seeds are not deletable -- they are the fallback floor."""
    template = get(template_id)
    if template.get("builtin"):
        raise PermissionError("built-in templates cannot be deleted")
    (config.CUSTOM_TEMPLATE_DIR / f"{template_id}.json").unlink(missing_ok=True)
    reload_templates()


def _unique_id(base: str) -> str:
    taken = load_templates()
    if base not in taken:
        return base
    for suffix in range(2, 100):
        candidate = f"{base}-{suffix}"
        if candidate not in taken:
            return candidate
    raise RuntimeError("could not allocate a template id")
