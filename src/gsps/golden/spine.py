"""The metric spine: every reported value for one metric, kept distinct."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Basis(StrEnum):
    """Observed values and projections are never blended.

    Hypothesis is ours; Projected is theirs.
    """

    OBSERVED = "observed"
    PROJECTED = "projected"


class SpineEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_key: str
    period: str
    basis: Basis
    anchor_id: str
    value: str
    reporter: str
    authority_tier: str
    grade: str
    anchor_type: str = "metric"
    as_of: str = ""
