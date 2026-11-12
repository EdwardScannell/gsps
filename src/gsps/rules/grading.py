"""Grading discipline at the moment a value enters the library.

* A lead (a search summary, an AI answer, another agent's note) points to a page. It never
  sets a value and never grades. Only the owner's own page, opened in the session, does.
* Extract twice: a value enters only when two independent verbatim extractions agree.
  This is the guard that caught a fetch summarizer inventing a table row.
* A walk ends at a documentary grade or a recorded ceiling. An ``effort`` ceiling is a
  to-do, never a resting state, and it cannot ship.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from gsps.vocab.values import DOCUMENTARY_GRADES, LADDER, Ceiling, Grade

_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")
_QUOTES = {ord("\u2018"): "'", ord("\u2019"): "'", ord("\u201c"): '"', ord("\u201d"): '"'}


class LeadIsNotASource(ValueError):
    """Raised when something that is only a lead is used to set or grade a value."""


class ExtractionMismatch(ValueError):
    """Raised when the two extractions of a value disagree."""


def normalize_text(text: str) -> str:
    """Normalize typography and whitespace only; never digits, signs or words."""
    t = unicodedata.normalize("NFKC", text).translate(_DASHES).translate(_QUOTES)
    return re.sub(r"\s+", " ", t).strip()


def accept_value(
    first: str,
    second: str,
    *,
    is_owner_primary: bool,
) -> str:
    """Return the value if it may enter the library, else raise.

    ``is_owner_primary`` must be True: the text came from the owner's own page opened in
    this session, not from a summary of it.
    """
    if not is_owner_primary:
        raise LeadIsNotASource("a lead points to the page; it cannot set a value")
    a, b = normalize_text(first), normalize_text(second)
    if not a or not b:
        raise ExtractionMismatch("both extractions must be present")
    if a != b:
        raise ExtractionMismatch(f"extractions disagree: {a!r} vs {b!r}")
    return a


def can_ship_with_ceiling(ceiling: str) -> bool:
    """``effort`` means the walk is unfinished; it never ships."""
    return ceiling != Ceiling.EFFORT


def is_documentary(grade: str) -> bool:
    return grade in DOCUMENTARY_GRADES


def weakest_grade(grades: Iterable[str]) -> Grade | None:
    """A value is only as strong as its weakest supporting grade."""
    known = [Grade(g) for g in grades if g in {x.value for x in LADDER}]
    return max(known, key=LADDER.index) if known else None
