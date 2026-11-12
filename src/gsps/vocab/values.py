"""Default registered values.

These enums are the vocabulary as ratified at release. A deployment may extend the
vocabulary through its own registry file (see :mod:`gsps.vocab.registry`); records are
never rejected for carrying an unknown value. They are flagged as a yield instead, so a
person rules on the new value (the engine never coins one).
"""

from __future__ import annotations

from enum import StrEnum


class Grade(StrEnum):
    """The confidence ladder, strongest to weakest."""

    CONFIRMED = "Confirmed"
    SOURCED = "Sourced"
    GROUNDED = "Grounded"
    POTENTIAL = "Potential"
    REPORTED = "Reported"
    UNVERIFIED = "Unverified"
    HYPOTHESIS = "Hypothesis"
    CONJECTURE = "Conjecture"


#: Strongest to weakest. Index order is meaningful: a higher index is a weaker grade.
LADDER: tuple[Grade, ...] = tuple(Grade)

#: Grades that only a walked owner's primary can earn.
DOCUMENTARY_GRADES: frozenset[Grade] = frozenset({Grade.CONFIRMED, Grade.SOURCED, Grade.GROUNDED})


class Ceiling(StrEnum):
    """Why a walk stopped. ``effort`` is a to-do, never a resting state."""

    NONE = "none"
    EFFORT = "effort"
    ACCESS = "access"
    STRUCTURAL = "structural"


class AuthorityTier(StrEnum):
    """The kind of source. Distinct kinds are never folded together."""

    GOVERNMENT = "government"
    INTERNATIONAL = "international"
    ACADEMIC = "academic"
    INSTITUTE = "institute"
    COMPANY_RESEARCH = "company-research"
    COMMERCIAL_PUBLISHER = "commercial-publisher"
    COMPANY_SELF = "company-self"
    INTERNAL = "internal"
    OFFICIAL_STATEMENT = "official-statement"
    MEDIA_RESEARCH = "media-research"
    THIRD_PARTY_UNKNOWN = "3rd-party-unknown"


class AnchorType(StrEnum):
    METRIC = "metric"
    PRICE = "price"
    ESTIMATE = "estimate"
    FINDING = "finding"
    DEFINITION = "definition"


class Nature(StrEnum):
    """Whose value it is and how it was produced."""

    EXTERNAL_PRIMARY = "external-primary"
    INTERNAL_CONFIRM = "internal-confirm"
    DERIVED_ESTIMATE = "derived-estimate"
    ASSUMPTION = "assumption"


class RefreshBasis(StrEnum):
    PUBLISHED_SCHEDULE = "published-schedule"
    OUR_POLICY = "our-policy"
    IRREGULAR = "irregular"
    NONE = "none"


class Lifecycle(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class Stance(StrEnum):
    """A finding's relation to one of our claims."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    COMPLICATES = "complicates"


class ClaimStatus(StrEnum):
    """A claim status, not a grade. ``contested`` blocks shipping until a ratifier rules."""

    OPEN = "open"
    CONTESTED = "contested"
    RESOLVED = "resolved"


class Gate(StrEnum):
    """How a URL was cleared for fetching, or why it failed."""

    PASTE = "paste"  # the ratifier pasted it to the walking agent
    CLICK = "click"  # the ratifier approved the fetch
    CHAINED = "chained"  # linked from a page fetched in the same session
    NOT_FOUND = "404"  # wrong or moved URL; our error
    WALL = "wall"  # robots, login or blocklist: needs a human walk
    SIZE = "size"  # too long or rendered empty

    @property
    def cleared(self) -> bool:
        """True when the gate permitted the fetch."""
        return self in {Gate.PASTE, Gate.CLICK, Gate.CHAINED}


class Confidence(StrEnum):
    """Derived from grade and tier; never typed by hand."""

    H = "H"
    M = "M"
    L = "L"
    NO_VALUE = "NO-VALUE"
    NOT_SHIPPABLE = "NOT-SHIPPABLE"


class SyncStatus(StrEnum):
    """A citation's state against the library. Ordered best to worst."""

    IN_SYNC = "In sync"
    AT_RISK = "At risk"
    BEHIND = "Behind"
    DANGLING = "DANGLING"

    @property
    def rank(self) -> int:
        return list(SyncStatus).index(self)


class Verdict(StrEnum):
    """Track-1 verdict on a claim, set after the walk."""

    CONFIRMED = "CONFIRMED"
    WRONG = "WRONG"
    UNVERIFIABLE = "UNVERIFIABLE"
    ATTESTED = "ATTESTED"  # internal fact confirmed by the ratifier's first-hand attestation
