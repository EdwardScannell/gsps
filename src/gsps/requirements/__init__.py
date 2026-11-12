"""The requester's side: briefs, business-case claims and shopping requests.

A requester hands over *requirements, not sources*: the questions to answer, the
documents whose claims must be grounded, and what is out of scope. The keeper finds the
evidence. These modules give that hand-off a typed, testable shape.
"""

from gsps.requirements.brief import Question, WalkBrief, load_brief
from gsps.requirements.business_case import (
    Claim,
    ClaimKind,
    Track,
    load_claims,
    validate_routing,
)
from gsps.requirements.shopping import (
    FillClass,
    ShoppingReport,
    ShoppingRequest,
    ShoppingToken,
    TokenRecord,
    validate_report,
)

__all__ = [
    "Claim",
    "ClaimKind",
    "FillClass",
    "Question",
    "ShoppingReport",
    "ShoppingRequest",
    "ShoppingToken",
    "TokenRecord",
    "Track",
    "WalkBrief",
    "load_brief",
    "load_claims",
    "validate_report",
    "validate_routing",
]
