"""Confidence (H / M / L) is derived from grade and authority tier. It is never typed.

* H: Confirmed or Grounded, from a government, international or company-self source.
* M: Confirmed or Grounded from an academic, institute or company-research source;
  or Sourced from a government, international, academic or institute source.
* NOT-SHIPPABLE: Conjecture.
* NO-VALUE: the anchor has no value (a blocked walk was logged). It cannot be cited.
* L: everything else.
"""

from __future__ import annotations

from collections.abc import Iterable

from gsps.model.records import Anchor
from gsps.vocab.values import AuthorityTier as T
from gsps.vocab.values import Confidence
from gsps.vocab.values import Grade as G

_STRONG = {G.CONFIRMED, G.GROUNDED}
_H_TIERS = {T.GOVERNMENT, T.INTERNATIONAL, T.COMPANY_SELF}
_M_TIERS_STRONG = {T.ACADEMIC, T.INSTITUTE, T.COMPANY_RESEARCH}
_M_TIERS_SOURCED = {T.GOVERNMENT, T.INTERNATIONAL, T.ACADEMIC, T.INSTITUTE}

#: Higher is more confident. Used to take the weakest of several.
_RANK = {
    Confidence.H: 3,
    Confidence.M: 2,
    Confidence.L: 1,
    Confidence.NO_VALUE: 0,
    Confidence.NOT_SHIPPABLE: 0,
}


def confidence(anchor: Anchor) -> Confidence:
    if not anchor.value:
        return Confidence.NO_VALUE
    grade, tier = anchor.grade, anchor.authority_tier
    if grade in _STRONG and tier in _H_TIERS:
        return Confidence.H
    if grade in _STRONG and tier in _M_TIERS_STRONG:
        return Confidence.M
    if grade == G.SOURCED and tier in _M_TIERS_SOURCED:
        return Confidence.M
    if grade == G.CONJECTURE:
        return Confidence.NOT_SHIPPABLE
    return Confidence.L


def weakest_confidence(anchors: Iterable[Anchor]) -> Confidence | None:
    """A value is only as confident as its weakest input."""
    levels = [confidence(a) for a in anchors]
    return min(levels, key=_RANK.__getitem__) if levels else None
