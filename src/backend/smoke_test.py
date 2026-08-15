"""End-to-end smoke test: session -> anchored chat turns -> report card.

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

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
