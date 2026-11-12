"""Resolving a spine to a Golden candidate.

Rules:

* Resolution happens within one metric, one period and one basis. Observed and projected
  never compete with each other.
* The resolution order ranks authority tiers. A tier missing from the order never wins,
  and ``3rd-party-unknown`` can never win until it is classified.
* Only documentary grades (Confirmed / Sourced / Grounded) are eligible.
* Findings are never promoted by rule; only a ratifier can approve one.
* If the best-ranked eligible entries disagree, the result is Contested, never a pick.
* A rule produces at most a Proposed candidate. Approved comes only from :func:`approve`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from gsps.golden.spine import SpineEntry
from gsps.rules.grading import is_documentary, normalize_text
from gsps.vocab.values import AnchorType, AuthorityTier


class GoldenStatus(StrEnum):
    PROPOSED = "Proposed"
    CONTESTED = "Contested"
    APPROVED = "Approved"
    SUPERSEDED = "Superseded"
    RETIRED = "Retired"


class ResolutionOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    tiers: tuple[str, ...]

    def rank(self, tier: str) -> int | None:
        if tier == AuthorityTier.THIRD_PARTY_UNKNOWN:
            return None
        return self.tiers.index(tier) if tier in self.tiers else None


class GoldenCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_key: str
    period: str
    basis: str
    status: GoldenStatus
    value: str = ""
    anchor_id: str = ""
    rule: str = ""
    reason: str = ""
    competing: tuple[str, ...] = ()
    approved_by: str = ""
    considered: tuple[str, ...] = Field(default_factory=tuple)


def resolve(entries: Iterable[SpineEntry], order: ResolutionOrder) -> GoldenCandidate:
    items = list(entries)
    keys = {(e.metric_key, e.period, e.basis) for e in items}
    if len(keys) != 1:
        raise ValueError(
            "resolve one metric, period and basis at a time; got "
            + ", ".join(map(str, sorted(keys)))
        )
    metric, period, basis = keys.pop()
    considered = tuple(e.anchor_id for e in items)

    def result(status: GoldenStatus, **kw: object) -> GoldenCandidate:
        return GoldenCandidate(
            metric_key=metric,
            period=period,
            basis=basis,
            status=status,
            rule=order.name,
            considered=considered,
            **kw,
        )

    if any(e.anchor_type == AnchorType.FINDING for e in items):
        return result(GoldenStatus.CONTESTED, reason="findings are promoted only by a ratifier")

    eligible = [
        (r, e)
        for e in items
        if is_documentary(e.grade) and (r := order.rank(e.authority_tier)) is not None
    ]
    if not eligible:
        return result(GoldenStatus.CONTESTED, reason="no eligible entry under this order")

    best = min(r for r, _ in eligible)
    top = [e for r, e in eligible if r == best]
    values = {normalize_text(e.value) for e in top}
    if len(values) > 1:
        return result(
            GoldenStatus.CONTESTED,
            reason="best-ranked sources disagree",
            competing=tuple(f"{e.anchor_id}={e.value}" for e in top),
        )
    winner = top[0]
    return result(
        GoldenStatus.PROPOSED,
        value=winner.value,
        anchor_id=winner.anchor_id,
        reason=f"highest-ranked tier: {winner.authority_tier}",
    )


def approve(
    candidate: GoldenCandidate,
    ratifier: str,
    *,
    value: str | None = None,
    anchor_id: str | None = None,
) -> GoldenCandidate:
    """The only door to Approved. A contested candidate needs the ratifier to name the value."""
    if not ratifier.strip():
        raise ValueError("approval must name the ratifier")
    if candidate.status == GoldenStatus.CONTESTED and (value is None or anchor_id is None):
        raise ValueError("a contested metric is approved only with an explicit value and anchor")
    return candidate.model_copy(
        update={
            "status": GoldenStatus.APPROVED,
            "approved_by": ratifier,
            "value": value if value is not None else candidate.value,
            "anchor_id": anchor_id if anchor_id is not None else candidate.anchor_id,
        }
    )


def resolve_spine(entries: Sequence[SpineEntry], order: ResolutionOrder) -> list[GoldenCandidate]:
    """Resolve every (metric, period, basis) group in a spine."""
    groups: dict[tuple[str, str, str], list[SpineEntry]] = {}
    for e in entries:
        groups.setdefault((e.metric_key, e.period, e.basis), []).append(e)
    return [resolve(g, order) for _, g in sorted(groups.items())]
