# Making the evaluator measure development, not just presence

Notes on reshaping `src/backend/app/evaluator.py` so the report card scores *how a
student's thinking moved across the conversation*, rather than what showed up in it
at least once.

Status: design notes, nothing implemented. Written against `evaluator.py` as of the
title-screen merge (`6642abf`).

## The problem in one line

The evaluator treats a 5-turn transcript as a bag of words, and the one dimension
that is defined cross-turn is scored by counting messages.

## Where that shows up in the code

**The heuristic flattens the conversation before it looks at it.** `_heuristic_scores`
opens with:

```python
joined = " ".join(messages).lower()   # evaluator.py:142
```

Every signal after that line — `has_doubt`, `has_reasoning`, `has_probe`,
`has_synthesis` — is a membership test against that one string. The result is
order-independent: the same five messages shuffled into any sequence produce an
identical score. A student who opens with the sharpest possible question and then
coasts scores the same as one who starts flat and arrives there by turn 5. Those are
very different pieces of thinking and the current model cannot tell them apart.

**Depth of Follow-up is a turn counter.** The rubric defines it as *"Does each turn
build on the previous exchange rather than restart?"* (`rubric.json`, levels running
from "Each message is unrelated to the last" up to "Revises an earlier position in
light of new reasoning"). The heuristic implements it as:

```python
"depth_of_followup": clamp(1 + int(builds) + int(len(messages) >= 4)),   # evaluator.py:166
```

where `builds = len(messages) >= 3`. Nothing compares turn N to turn N−1. Paste the
same sentence four times and this dimension returns 3 out of 4. This is the single
clearest gap between what the rubric claims to measure and what the code measures.

**One quote is reused for all five dimensions.** Inside the scoring loop:

```python
quote = _best_quote(messages)   # evaluator.py:173 — same value every iteration
```

`_best_quote` picks the single most reasoning-dense message in the whole session. So
the evidence offered for "Depth of Follow-up" is one sentence from one turn — which
is structurally incapable of showing follow-up. Demonstrating movement needs at least
two quotes from different turns, held next to each other.

**The schema can't express a trajectory even when the model sees one.** `evidence_quote`
is a single string in `_scoring_schema` and in `DimensionScore`. The LLM path *does*
receive turn numbers — `_transcript_block` labels every line `Student (turn N)` — and
the system prompt already asks that *"the explanation must describe how the student's
thinking moved across the conversation"* (`evaluator.py:62`). So the intent is there
and the ordering information is there. What's missing is anywhere in the output shape
to put it: `explanation` is free prose that no score depends on, and every scored
field is a scalar.

That's the encouraging read of all this. The gap is mostly in the **output contract**,
not in what the model can see.

## The reframe

Score the **delta between turns**, not the union of them. Concretely: for a dimension
to earn a high mark for development, the transcript has to show a *later* turn doing
something an *earlier* turn did not.

## Changes worth making, cheapest first

### 1. Evidence becomes a list of turn-tagged quotes

The highest-leverage change, and the one everything else builds on. Replace the single
`evidence_quote` string with:

```python
"evidence": {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "turn": {"type": "integer"},
            "quote": {"type": "string"},
        },
        "required": ["turn", "quote"],
        "additionalProperties": False,
    },
},
```

For the cross-turn dimensions (Depth of Follow-up, and arguably Synthesis) require two
entries with *different* `turn` values. The scoring prompt then has to point at the
before and the after, which is most of the work of making it reason about development
rather than presence.

This preserves the "every score cites a verbatim quote" invariant from `CLAUDE.md` —
it strengthens it. It does mean touching `DimensionScore` in `models.py` and the report
card component, so it isn't free.

### 2. Make the Depth heuristic actually compare adjacent turns

Replace the message count with a pairwise comparison. A crude version that is still far
better than counting:

```python
def _builds_on_previous(prev: str, curr: str) -> bool:
    """Curr engages prev's content while adding something prev didn't have."""
    prev_words = set(re.findall(r"\w+", prev.lower())) - _STOPWORDS
    curr_words = set(re.findall(r"\w+", curr.lower())) - _STOPWORDS
    if not prev_words or not curr_words:
        return False
    shared = prev_words & curr_words
    fresh = curr_words - prev_words
    # Continuity without repetition: some overlap, but genuinely new content too.
    return len(shared) >= 2 and len(fresh) >= 3

steps = sum(
    _builds_on_previous(a, b) for a, b in zip(messages, messages[1:])
)
raw["depth_of_followup"] = clamp(1 + steps)
```

Both halves matter. Overlap alone rewards restating; novelty alone rewards changing the
subject. Requiring both is what distinguishes "extends the previous idea" from "repeats
it" and from "restarts".

This is lexical and therefore shallow — it can't see a student who paraphrases an idea
in entirely new words. That's an acceptable floor for a deterministic fallback whose job
is to keep the demo alive, and the LLM path is where the real judgment should live.

### 3. Give the report a start and an end, not just an end

`bloom_level_reached` is a single terminal level, and the heuristic derives it from
`total // 4` — an aggregate that discards sequence entirely. Development is a movement,
so report it as one:

```python
"bloom_level_start": {"type": "string", "enum": BLOOM_LEVELS},
"bloom_level_reached": {"type": "string", "enum": BLOOM_LEVELS},
"turning_point_turn": {"type": "integer"},   # where the shift happened, 0 if none
```

`turning_point_turn` is the field to watch. It forces the model to commit to *where*
the thinking changed, which is much harder to confabulate than a vague closing
paragraph, and it gives the UI something concrete to show — "your thinking shifted at
turn 3" is a far better artifact for a student than a number out of 10.

### 4. Consider a distinct Movement dimension

The rubric is data, not prompt text (`app/data/rubric.json`), so adding a sixth
dimension is a JSON edit and needs no code change — the picker, evaluator, and report
generator all read from it. That's a deliberate design invariant and it makes this
cheap to try.

Worth weighing against just fixing Depth of Follow-up, though. Six dimensions on a
report card for an 11-year-old is a lot of surface, and two dimensions that both
measure cross-turn behaviour will correlate heavily. My instinct is to fix Depth of
Follow-up first and only split it out if the single dimension turns out to be carrying
two distinguishable ideas — continuity between adjacent turns, versus overall arc from
first message to last.

### 5. Prompt changes for the LLM path

Additions to `SYSTEM_PROMPT` that follow from the above:

- Score Depth of Follow-up by comparing each turn to the one before it. A transcript
  where every message could be reordered without loss scores 1, however good the
  individual messages are.
- Cite the earlier turn and the later turn when awarding a development score. If the
  same turn is the best evidence for both, the score is at most 2.
- A student who reasons well from turn 1 and sustains it is not penalised. Consistent
  strength is not the same as a flat line — say so in the explanation and score the
  dimension on the quality of the sustained reasoning.

That last one is not optional; see the traps below.

## Traps

**The ceiling problem.** A student who arrives at turn 1 with the sharpest question in
the transcript has nowhere to develop *to*. A naive delta metric scores them low, which
is both wrong and demoralising, and it would punish exactly the strongest thinkers.
Whatever gets built needs an explicit floor: sustained high performance scores as well
as improvement. This is the main reason I'd rather reshape Depth of Follow-up than add
a raw "improvement" score.

**Don't let length back in.** The current file is deliberately anti-length-bias —
`_best_quote` was changed away from "longest message" precisely because it *"surfaced
rambling over insight"*, and the system prompt says message length is not evidence of
thinking, with dyslexic students named as the reason. A cross-turn metric is an easy
place to smuggle that bias back in, because "added new content" and "wrote more" look
similar to a keyword counter. The `fresh` check in the sketch above is a token-set
difference, not a length comparison, for exactly this reason. Any future version should
be checked against a transcript of short, sharp messages to confirm it doesn't sag.

**Turn count is not development.** Worth stating plainly since the current code makes
this mistake: the conversation can legitimately end at turn 3 when `should_conclude`
fires. A 3-turn transcript that moves is better than a 5-turn one that doesn't, and the
scoring must not reward simply continuing.

**Hints complicate the story.** `_apply_hint_penalty` already docks Question Quality and
Evidence and Reasoning when a student leaned on hints, and `_transcript_block` marks the
turns with `[hints used: N]`. Development that happens immediately after a hint is real
learning but it is not *independent* thinking, and the two shouldn't score identically.
I don't have a clean answer here. The honest options are to dock hint-adjacent movement
the way question quality is docked, or to report it separately as "moved after a nudge"
rather than folding it into one number. Worth a conversation with whoever owns the hint
feature before picking.

## What this does not touch

Deliberately out of scope, because each is load-bearing for a stated reason in
`CLAUDE.md`:

- **Dialogue and scoring stay separate LLM calls.** Merging them to give the tutor
  visibility into the developing score would leak the rubric to the student mid-session.
- **Scoring stays post-hoc over the full transcript.** Incremental per-turn scoring
  would make the cross-turn comparison harder, not easier — you need the whole arc to
  judge the arc.
- **The rubric stays data.** Any new dimension or level descriptor belongs in
  `rubric.json`, not in the prompt string.

## Open question for the team

`fenichel/skill.md` classifies a *single* question against Bloom's; `rubric.json` scores
a *whole transcript* on five dimensions. `CLAUDE.md` flags that these two encodings of
the same six levels coexist without talking to each other.

Cross-turn development is where they'd naturally meet: per-turn Bloom classification
(the skill's unit of work) is precisely the input a trajectory needs — classify each
turn, then read the sequence. If we build the turn-level track in section 3, that track
is the skill's output, and converging the two definitions stops being a tidiness
argument and starts being a shared requirement.
