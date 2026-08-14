---
name: blooms-taxonomy-evaluator
description: Classifies a student's question about a piece of source material (a paragraph, passage, image, or other stimulus) against Bloom's revised taxonomy (Remember, Understand, Apply, Analyze, Evaluate, Create). Use this whenever a teacher or instructional designer shares source content plus one or more student questions and wants to know what level of thinking the question(s) demand, wants a rationale for that level, wants to check whether classroom questions are pitched at the right challenge level, or shares a batch of questions (from a discussion, worksheet, or quiz) and wants a profile of the class's overall cognitive-demand distribution. Trigger this even if the user doesn't say "Bloom's" explicitly — phrases like "is this a good question", "what level of thinking does this require", "are my students asking higher-order questions", or "review these discussion questions" are all a match.
---

# Bloom's Taxonomy Question Evaluator

Teachers use this to check whether a student's question — asked in response to something they read, watched, or looked at — is pitched at rote recall or genuine higher-order thinking. The judgment call is never about the question in isolation; it's about the relationship between the question and the source material. The exact same words ("What causes the seasons?") can be a Remember question if the source states the cause directly, or an Analyze question if the student has to connect several facts the source never puts together itself.

## The six levels

Use Anderson & Krathwohl's revised taxonomy, from lowest to highest cognitive demand:

1. **Remember** — retrieve a fact, term, or detail that is stated directly in the source. The student doesn't need to do anything with the information, just locate or recall it.
2. **Understand** — grasp and restate meaning: explain in their own words, summarize, give an example, or translate an idea from the source into a different form.
3. **Apply** — use information or a procedure from the source in a new, concrete situation the source doesn't already cover.
4. **Analyze** — break the source down into parts and examine how they relate: compare, contrast, find causes, identify assumptions, or spot patterns the source doesn't state outright.
5. **Evaluate** — make and defend a judgment: which is better, is this argument convincing, do you agree, what's the strongest weakness.
6. **Create** — generate something new by combining ideas from the source in an original way: propose, design, hypothesize, or reimagine.

Don't classify by surface verb alone. "What do you think will happen if...?" can sound like Apply but is really Evaluate if it's asking for a judgment, or Create if it's asking the student to invent a scenario. Read the question against what the source actually says, and ask: what does the student actually have to *do* to answer this — find it, restate it, use it, take it apart, judge it, or build something new?

See `references/level_details.md` for cue verbs, worked examples, and edge cases (compound questions, ambiguous phrasing, questions unrelated to the source).

## Workflow

**Single question:**
1. Read the source material (and look at any image directly — don't skip this to save time, since the level often hinges on whether the answer is already sitting in the source).
2. Determine what cognitive operation the question demands relative to that source.
3. Report: the level (bold), one or two sentences of rationale tied to the specific source content, and — only if genuinely ambiguous — the second-closest level.

Keep this to a short paragraph. Don't produce a file or a table for a single question.

**Batch of questions** (a discussion's worth, a worksheet, a quiz):
1. Classify each question the same way.
2. Present a simple list: question → level → one-line rationale.
3. Add a short profile: the count/percentage at each level, and one or two sentences of interpretation — e.g. whether the set skews toward recall, whether any level is completely absent, whether that's appropriate for the context described (a quick comprehension check vs. a discussion meant to build argumentation).

Don't inflate this into a formal report or create a document unless the user asks for one — this is a conversational check, not a deliverable.

## A few things worth remembering

Real student questions are often compound or messy — "What's photosynthesis and why does it matter for climate change?" packs Remember and Analyze into one sentence. When that happens, say so and classify at the higher level the question is really driving toward, rather than forcing a single clean label onto something that doesn't have one.

A question can also be completely unrelated to the source, or unanswerable from it (a student going off on a tangent). That's fine and worth naming plainly rather than stretching a classification to fit.

Resist the pull to always find something at every level when profiling a batch — an honest, slightly uneven distribution is more useful to a teacher than a tidy one that isn't true.