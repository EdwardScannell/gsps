"""Metric spines and Golden Metrics (ratified design; first implementation).

Each metric keeps a spine: every reported value, who reported it, when, for what period,
observed or projected, grade and source kind. A Golden Metric is the one sanctioned value
per metric, period and basis, promoted uncontested, by a named rule, or by a ratifier.
"""

from gsps.golden.resolution import (
    GoldenCandidate,
    GoldenStatus,
    ResolutionOrder,
    approve,
    resolve,
)
from gsps.golden.spine import Basis, SpineEntry

__all__ = [
    "Basis",
    "GoldenCandidate",
    "GoldenStatus",
    "ResolutionOrder",
    "SpineEntry",
    "approve",
    "resolve",
]
