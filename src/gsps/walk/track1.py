"""Track 1: claim -> primary source -> verdict.

Consistency rules enforced by :func:`validate_track1`:

* Every T1 and T1-INT claim has exactly one entry.
* A lead never carries a verdict other than UNVERIFIABLE: it cannot confirm or contradict.
* CONFIRMED needs a documentary grade (Confirmed / Sourced / Grounded), a verbatim quote,
  and a cleared gate (paste, click, chained) or a human walk past a wall.
* WRONG needs a walked contradiction: verbatim from a cleared primary.
* An absence or universal claim ("the only one", "everyone else") can never be CONFIRMED.
* UNVERIFIABLE needs a recorded reason: an access or structural ceiling, or an
  unconfirmable kind. An ``effort`` ceiling is an unfinished walk, not a verdict.
* ATTESTED is only for internal claims and names who attested.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from gsps.requirements.business_case import UNCONFIRMABLE_KINDS, Claim, Track
from gsps.rules.grading import is_documentary
from gsps.store.csv_io import read_rows
from gsps.vocab.values import Ceiling, Gate, Verdict


class Track1Entry(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    verdict: Verdict
    url: str = ""
    gate: Gate | None = None
    walked_by: str = ""  # "agent" or a person's role; a human walk past a wall names them
    human_walk: bool = False
    verbatim: str = ""
    grade: str = ""
    ceiling: str = Ceiling.NONE.value
    is_lead: bool = False
    attested_by: str = ""
    note: str = ""

    @field_validator("gate", mode="before")
    @classmethod
    def _blank_gate(cls, v: object) -> object:
        return None if v in ("", None) else v

    @field_validator("human_walk", "is_lead", mode="before")
    @classmethod
    def _bool(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y"}
        return v

    @property
    def walked_primary(self) -> bool:
        if self.is_lead or not self.verbatim.strip():
            return False
        if self.gate is not None and self.gate.cleared:
            return True
        return self.gate == Gate.WALL and self.human_walk


def validate_track1(claims: list[Claim], entries: list[Track1Entry]) -> list[str]:
    problems: list[str] = []
    by_claim: dict[str, list[Track1Entry]] = {}
    for e in entries:
        by_claim.setdefault(e.claim_id, []).append(e)
    known = {c.claim_id for c in claims}
    for cid in sorted(set(by_claim) - known):
        problems.append(f"{cid}: entry for an unknown claim")

    for c in claims:
        if c.track not in {Track.T1, Track.T1_INTERNAL}:
            continue
        found = by_claim.get(c.claim_id, [])
        if not found:
            problems.append(f"{c.claim_id}: no Track-1 entry")
            continue
        if len(found) > 1:
            problems.append(f"{c.claim_id}: more than one Track-1 entry")
        e = found[0]
        problems.extend(f"{c.claim_id}: {p}" for p in entry_problems(c, e))
    return problems


def entry_problems(c: Claim, e: Track1Entry) -> list[str]:
    out: list[str] = []
    if e.is_lead and e.verdict != Verdict.UNVERIFIABLE:
        out.append("a lead cannot confirm or contradict; walk the owner's page")
    if e.ceiling == Ceiling.EFFORT:
        out.append("effort ceiling: the walk is unfinished (a to-do, not a verdict)")

    if e.verdict == Verdict.CONFIRMED:
        if c.kind in UNCONFIRMABLE_KINDS:
            out.append(f"a '{c.kind}' claim can be disproved but never confirmed")
        if not is_documentary(e.grade):
            out.append(f"CONFIRMED needs a documentary grade, got '{e.grade or 'blank'}'")
        if not e.walked_primary:
            out.append("CONFIRMED needs verbatim from a cleared primary (or a human walk)")
    elif e.verdict == Verdict.WRONG:
        if not e.walked_primary:
            out.append("WRONG needs a walked contradiction (verbatim from a cleared primary)")
    elif e.verdict == Verdict.UNVERIFIABLE:
        has_ceiling = e.ceiling in {Ceiling.ACCESS, Ceiling.STRUCTURAL}
        if not (has_ceiling or c.kind in UNCONFIRMABLE_KINDS or e.note.strip()):
            out.append("UNVERIFIABLE needs a ceiling (access/structural) or a recorded reason")
    elif e.verdict == Verdict.ATTESTED:
        if c.track != Track.T1_INTERNAL:
            out.append("ATTESTED is only for internal claims")
        if not e.attested_by.strip():
            out.append("ATTESTED must name who attested")
    return out


def load_track1(path: str | Path) -> list[Track1Entry]:
    return [Track1Entry.model_validate(row) for row in read_rows(path)]
