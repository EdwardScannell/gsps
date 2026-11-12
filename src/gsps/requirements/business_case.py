"""Business-case claims and their routing.

Every claim extracted from a page is routed to exactly one track:

* ``T1``: a sourced fact about the world. Walk it to the owner's primary.
* ``T1_INTERNAL``: a fact about our own system or case. Its primary is our own record,
  or a first-hand attestation.
* ``T2``: an assumption, model, estimate or narrative. Register it; never source it.

Routing is a judgment the keeper makes; :func:`validate_routing` checks that the judgment
is consistent with the claim's kind (an estimate is never routed to T1, for example).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from gsps.store.csv_io import read_rows


class Track(StrEnum):
    T1 = "T1"
    T1_INTERNAL = "T1-INT"
    T2 = "T2"


class ClaimKind(StrEnum):
    FACT = "fact"  # a statement about the world
    COUNT = "count"  # a number about the world ("a dozen tools")
    ABSENCE = "absence"  # "the only one", "no one else": can be disproved, never confirmed
    UNIVERSAL = "universal"  # "everyone else does X"
    INTERNAL = "internal"  # about our own system, case or record
    ESTIMATE = "estimate"  # a modeled number
    NARRATIVE = "narrative"  # framing, rhetoric, a model of the market
    ILLUSTRATIVE = "illustrative"  # persona voice; not a claim of fact
    LEGAL = "legal"  # an assertion about what is lawful or safe


_ROUTES: dict[ClaimKind, set[Track]] = {
    ClaimKind.FACT: {Track.T1},
    ClaimKind.COUNT: {Track.T1},
    ClaimKind.ABSENCE: {Track.T1},
    ClaimKind.UNIVERSAL: {Track.T1},
    ClaimKind.INTERNAL: {Track.T1_INTERNAL},
    ClaimKind.ESTIMATE: {Track.T2},
    ClaimKind.NARRATIVE: {Track.T2},
    ClaimKind.ILLUSTRATIVE: {Track.T2},
    ClaimKind.LEGAL: {Track.T2},
}

#: Kinds a walk can disprove but can never confirm.
UNCONFIRMABLE_KINDS = frozenset({ClaimKind.ABSENCE, ClaimKind.UNIVERSAL})

#: Kinds that need a decision from the ratifier before they ship, whatever the walk finds.
RATIFIER_KINDS = frozenset({ClaimKind.LEGAL})


class Claim(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    text: str
    kind: ClaimKind
    track: Track
    on_page: bool = True
    location: str = ""
    question_ids: tuple[str, ...] = ()
    anchors: tuple[str, ...] = ()

    @field_validator("question_ids", "anchors", mode="before")
    @classmethod
    def _split(cls, v: object) -> object:
        if isinstance(v, str):
            return tuple(x.strip() for x in v.replace(";", ",").split(",") if x.strip())
        return v

    @field_validator("on_page", mode="before")
    @classmethod
    def _bool(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y", "p"}
        return v


def validate_routing(claims: list[Claim]) -> list[str]:
    """Problems with routing: wrong track for the kind, or duplicate IDs."""
    problems: list[str] = []
    seen: set[str] = set()
    for c in claims:
        if c.claim_id in seen:
            problems.append(f"{c.claim_id}: duplicate claim id")
        seen.add(c.claim_id)
        allowed = _ROUTES[c.kind]
        if c.track not in allowed:
            want = ", ".join(sorted(t.value for t in allowed))
            problems.append(f"{c.claim_id}: kind '{c.kind}' must route to {want}, not {c.track}")
    return problems


def load_claims(path: str | Path) -> list[Claim]:
    return [Claim.model_validate(row) for row in read_rows(path)]
