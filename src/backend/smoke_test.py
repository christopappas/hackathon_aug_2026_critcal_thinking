"""End-to-end smoke test.

Two flows:
  student -- session -> anchored chat turns -> report card
  teacher -- template -> generate -> preview -> publish -> student session -> delete

Run the server first, then: python smoke_test.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code} on {method} {path}: {exc.read().decode()}")
        raise


MESSAGES = [
    (
        "How were the 200 students picked for this survey?",
        {"kind": "text", "quote": "Our survey of 200 students", "start": 0, "end": 25},
    ),
    (
        "The screen time was self-reported, so students might be guessing. Could that make the 71 percent number wrong?",
        {"kind": "temporal", "timestamp_s": 9.0},
    ),
    (
        "I think something else could cause both, maybe students who study less use phones more. That would mean phones are not the real cause.",
        {"kind": "region", "region_id": "trend-line"},
    ),
    (
        "Those students with high screen time who still got above 85 do not fit the trend, so the conclusion assumes every student follows the line.",
        {"kind": "region", "box": [0.7, 0.2, 0.05, 0.05]},
    ),
    (
        "I would tell the newspaper their data shows a link but not a cause, and they should compare students with similar study habits before banning phones.",
        None,
    ),
]


def expect_status(method: str, path: str, payload: dict | None, want: int, label: str) -> None:
    got = None
    try:
        call(method, path, payload)
    except urllib.error.HTTPError as exc:
        got = exc.code
    assert got == want, f"{label}: expected {want}, got {got}"
    print(f"  ok: {label} -> {want}")


def teacher_flow() -> str | None:
    """Generate a piece, prove its regions are clickable, publish it, then clean up.

    Returns the generated content id if it is still on disk, so the caller can remove it
    even when an assertion fails partway through -- otherwise a failed run leaves junk in
    the library that slows every later run.
    """
    print("\n=== TEACHER FLOW ===")

    templates = call("GET", "/teacher/templates")
    assert templates, "expected at least one template"
    print(f"templates ({len(templates)}): {[t['id'] for t in templates]}")

    template = templates[0]
    result = call(
        "POST",
        "/teacher/generate",
        {"template_id": template["id"], "topic": "a new snack sold at the school store"},
    )
    content = result["content"]
    cid = content["id"]
    print(f"generated '{cid}' from {template['id']} | llm={result['generated_with_llm']}")
    if result["warnings"]:
        print(f"  warnings: {result['warnings']}")

    assert content["review_status"] == "draft", "a fresh generation must start as a draft"
    assert result["thinking_trap"], "the teacher needs the trap explained"
    assert result["thinking_trap"] not in content["body"], "the trap leaked into student-facing text"

    # The review gate: a draft exists but students cannot see it.
    assert cid not in [c["id"] for c in call("GET", "/content")], "draft leaked into the catalog"
    print("  ok: draft is hidden from the student catalog")

    asset = content["chart"]["asset_url"]
    with urllib.request.urlopen(f"{BASE}{asset}", timeout=20) as resp:
        body = resp.read().decode()
    assert resp.status == 200 and body.lstrip().startswith("<svg"), f"bad asset at {asset}"
    print(f"  ok: chart rendered and served at {asset}")

    # The assertion this whole design exists to satisfy. Every region derived by the
    # renderer must resolve, through the real anchor path, back to its own caption. If a
    # box drifts from the drawing, this is what catches it.
    regions = content["chart"]["regions"]
    assert regions, "generated content has no clickable regions"
    session = call("POST", "/session", {"content_id": cid})
    assert session["content"]["id"] == cid, "drafts must stay previewable as a student"
    sid = session["session_id"]

    # Cap by the server's own turn limit, not len(MESSAGES), so a lowered MAX_TURNS
    # produces a shorter check rather than a spurious 409.
    for region in regions[: session["max_turns"]]:
        x, y, w, h = region["box"]
        reply = call(
            "POST",
            "/chat",
            {
                "session_id": sid,
                "message": "What does this part actually show?",
                "anchor": {"kind": "region", "box": [x + w / 2, y + h / 2, 0, 0]},
            },
        )
        excerpt = reply["anchor_excerpt"] or ""
        assert region["caption"] in excerpt, (
            f"region '{region['id']}' is not clickable: a click at its center resolved "
            f"to {excerpt!r} instead of its caption"
        )
        print(f"  ok: clicking '{region['id']}' -> {excerpt}")

    call("POST", f"/teacher/content/{cid}/publish")
    assert cid in [c["id"] for c in call("GET", "/content")], "publish did not reach the catalog"
    print("  ok: published and visible to students without a restart")

    call("POST", f"/teacher/content/{cid}/unpublish")
    assert cid not in [c["id"] for c in call("GET", "/content")], "unpublish did not take effect"
    print("  ok: unpublish pulls it back out of the catalog")

    # The built-in five are not the teacher's to break.
    seed = next(c["id"] for c in call("GET", "/content") if c["id"] != cid)
    expect_status("DELETE", f"/teacher/content/{seed}", None, 403, "delete a built-in piece")
    expect_status("PUT", f"/teacher/content/{seed}", {"title": "x"}, 403, "edit a built-in piece")

    return cid


def main() -> int:
    health = call("GET", "/health")
    print(f"health: {health}")

    rubric = call("GET", "/rubric")
    print(f"rubric dimensions: {[d['id'] for d in rubric['dimensions']]}")

    catalog = call("GET", "/content")
    print(f"content library ({len(catalog)}):")
    for item in catalog:
        print(f"  - {item['id']} | grade {item['grade_level']} | {item['title']}")
    assert len(catalog) >= 2, "expected a content library"

    # Every piece must start a session and serve its asset.
    for item in catalog:
        probe = call("POST", "/session", {"content_id": item["id"]})
        content = probe["content"]
        assert content["id"] == item["id"], "server returned the wrong content"
        asset = content["chart"]["asset_url"]
        with urllib.request.urlopen(f"{BASE}{asset}", timeout=20) as resp:
            assert resp.status == 200, f"missing asset {asset}"
        assert content["chart"]["regions"], f"{item['id']} has no clickable regions"
        print(f"  ok: {item['id']} -> {asset}")

    bad = None
    try:
        call("POST", "/session", {"content_id": "does-not-exist"})
    except urllib.error.HTTPError as exc:
        bad = exc.code
    assert bad == 404, f"expected 404 for unknown content, got {bad}"
    print("unknown content id correctly rejected (404)")

    session = call("POST", "/session", {"content_id": catalog[0]["id"]})
    sid = session["session_id"]
    print(f"\nsession {sid} | turns {session['min_turns']}-{session['max_turns']} | llm={session['llm_enabled']}")

    completed = False
    for message, anchor in MESSAGES:
        if completed:
            break
        body = {"session_id": sid, "message": message, "anchor": anchor}
        reply = call("POST", "/chat", body)
        print(f"\n--- turn {reply['turns_used']} (status={reply['status']}) ---")
        print(f"anchor -> {reply['anchor_excerpt']}")
        print(f"student: {message[:70]}...")
        print(f"tutor  : {reply['reply'][:110]}...")
        completed = reply["is_complete"]

    assert completed, "conversation never reached completion"

    report = call("GET", f"/report/{sid}")
    print("\n=== REPORT CARD ===")
    print(f"overall {report['overall_score']}/10 | bloom: {report['bloom_level_reached']} | llm={report['generated_with_llm']}")
    print(f"explanation: {report['explanation']}")
    for dim in report["dimensions"]:
        print(f"  {dim['name']}: {dim['score']}/4 - {dim['feedback'][:70]}")
    print(f"next step: {report['next_step']}")

    assert len(report["dimensions"]) == len(rubric["dimensions"]), "missing rubric dimensions"
    assert all(d["evidence_quote"] for d in report["dimensions"]), "a dimension lacks evidence"

    # Turn guard must reject extra messages after completion.
    try:
        call("POST", "/chat", {"session_id": sid, "message": "one more"})
        print("\nFAIL: turn guard allowed an extra message")
        return 1
    except urllib.error.HTTPError as exc:
        assert exc.code == 409, f"expected 409, got {exc.code}"
        print("\nturn guard correctly rejected a 6th message (409)")

    generated_id = None
    try:
        generated_id = teacher_flow()
    finally:
        # Always clean up, including after a failed assertion, so the test stays
        # re-runnable and the library does not grow with every run.
        if generated_id:
            call("DELETE", f"/teacher/content/{generated_id}")
            remaining = [c["id"] for c in call("GET", "/content")]
            assert generated_id not in remaining, "delete left the piece in the catalog"
            print(f"  ok: cleaned up '{generated_id}'")

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
