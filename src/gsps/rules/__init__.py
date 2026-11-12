"""The rules, as pure functions. Every derived field is computed here, never typed."""

from gsps.rules.confidence import confidence, weakest_confidence
from gsps.rules.estimates import EstimateCheck, recompute
from gsps.rules.freshness import is_stale, sync_status, worst_status
from gsps.rules.grading import (
    ExtractionMismatch,
    LeadIsNotASource,
    accept_value,
    can_ship_with_ceiling,
    normalize_text,
    weakest_grade,
)
from gsps.rules.integrity import IntegrityResult, run_integrity_checks

__all__ = [
    "EstimateCheck",
    "ExtractionMismatch",
    "IntegrityResult",
    "LeadIsNotASource",
    "accept_value",
    "can_ship_with_ceiling",
    "confidence",
    "is_stale",
    "normalize_text",
    "recompute",
    "run_integrity_checks",
    "sync_status",
    "weakest_confidence",
    "weakest_grade",
    "worst_status",
]
