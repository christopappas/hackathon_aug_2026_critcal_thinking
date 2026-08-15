"""Mock student completions for the teacher dashboard.

Sessions live in a process-local dict and carry no student identity (`store.py`,
`models.Session`), so there is no completion history to read and no roster to read
it against. This module invents both.

**Every name here is fictional and every score is generated.** No real student data
enters the prototype, and nothing in this module reads a session. `CompletionsResponse`
carries `mock: true` so the dashboard can say so on the page rather than leaving a
reviewer to guess.

Two properties make it demo-safe:

- **Stable.** A row's numbers are seeded from its own identity, so refreshing the
  dashboard, restarting the backend, or pointing two laptops at it shows the same
  class. Only the dates move, and only by the day (`_completed_on`).
- **Consistent with real reports.** Dimension scores run 1-4 and are folded into the
  overall and the Bloom level by `evaluator.overall_score` / `evaluator.bloom_level`
  -- the same functions a real report card uses, so the mock rows cannot drift into
  numbers the scorer could never produce.

Replacing this with real data means persisting sessions with a student identity and
building the same `StudentCompletion` rows from `Session.report`. The table above it
does not change.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from random import Random

from . import config
from .evaluator import bloom_level, overall_score
from .models import CompletionDimension, CompletionsResponse, StudentCompletion

# First name plus last initial, the way a class roster is usually shown. The trailing
# number is how the student tends to score on the 1-4 dimension scale, which is what
# gives the dashboard a spread worth looking at instead of noise around the middle.
MOCK_ROSTER: list[tuple[str, int]] = [
    ("Amara O.", 4),
    ("Bex T.", 2),
    ("Cleo M.", 3),
    ("Dev R.", 3),
    ("Esi A.", 4),
    ("Finn K.", 1),
    ("Goldie W.", 2),
    ("Hana S.", 3),
    ("Ira L.", 2),
    ("Jules N.", 3),
    ("Kwame B.", 4),
    ("Lupe V.", 1),
]

MAX_PIECES_PER_STUDENT = 3

# Class periods, so timestamps read like a school day rather than 3am.
PERIODS = (time(9, 15), time(10, 40), time(13, 5), time(14, 30))


def _rng(*parts: str) -> Random:
    """A generator seeded from a row's identity, so a row's numbers never move.

    Hashed rather than seeding `Random` with the tuple directly: `hash()` of a str
    is salted per process, which would reshuffle the whole class on every restart.
    """
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return Random(int(digest[:16], 16))


def _dimension_scores(rng: Random, strength: int) -> list[CompletionDimension]:
    """Score every rubric dimension around the student's usual level.

    Read from the rubric rather than a local list, for the same reason the evaluator
    does: the rubric is the one definition of what gets scored.
    """
    scores = []
    for dim in config.load_rubric()["dimensions"]:
        drift = rng.choice((-1, 0, 0, 0, 1))
        scores.append(
            CompletionDimension(
                dimension=dim["id"],
                name=dim["name"],
                score=max(1, min(4, strength + drift)),
            )
        )
    return scores


def _completed_on(rng: Random, days_back: int) -> str:
    """A timestamp inside the last two weeks.

    Anchored to today rather than a fixed date so the dashboard never shows a class
    that finished months ago. This is the one thing about a row that changes, and it
    changes only by the day.
    """
    when = datetime.combine(date.today() - timedelta(days=days_back), rng.choice(PERIODS))
    return when.isoformat(timespec="minutes")


def build() -> CompletionsResponse:
    """The whole mock class, newest completion first."""
    pieces = config.list_content()
    rows: list[StudentCompletion] = []

    for student, strength in MOCK_ROSTER:
        picker = _rng("roster", student)
        # A weaker student has usually finished fewer pieces, which is itself a thing
        # a teacher would want to spot in the table.
        count = min(len(pieces), picker.randint(1, min(MAX_PIECES_PER_STUDENT, strength + 1)))
        for piece in picker.sample(pieces, count):
            rng = _rng(student, piece["id"])
            content = config.load_content(piece["id"])
            min_turns, max_turns = config.content_turn_range(content)
            dimensions = _dimension_scores(rng, strength)
            scores = [d.score for d in dimensions]

            rows.append(
                StudentCompletion(
                    id=f"{piece['id']}--{student.replace(' ', '-').replace('.', '').lower()}",
                    student_name=student,
                    content_id=piece["id"],
                    content_title=piece["title"],
                    completed_at=_completed_on(rng, rng.randrange(0, 14)),
                    # Stronger students tend to conclude early; the guard allows it
                    # once min_turns is met, so the range starts there either way.
                    turns_used=rng.randint(min_turns, max_turns),
                    hints_used=max(0, rng.randint(0, config.MAX_HINTS_PER_TURN) - strength // 2),
                    overall_score=overall_score(scores),
                    bloom_level_reached=bloom_level(scores),
                    dimensions=dimensions,
                )
            )

    rows.sort(key=lambda row: row.completed_at, reverse=True)
    average = sum(row.overall_score for row in rows) / len(rows) if rows else 0.0

    return CompletionsResponse(
        rows=rows,
        student_count=len({row.student_name for row in rows}),
        average_score=round(average, 1),
    )
