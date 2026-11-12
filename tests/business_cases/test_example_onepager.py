"""A requester's brief, executed: the example one-pager's ship gate.

This is the pattern for every real deliverable: put the claims, the Track-1 log and the
Track-2 register next to the page, and this test fails until the page can ship.
"""

from __future__ import annotations

import pytest

from gsps.requirements.business_case import load_claims, validate_routing
from gsps.store.csv_io import read_rows
from gsps.walk.qualitative import QualSource, summarize_question
from gsps.walk.ship import ship_check
from gsps.walk.track1 import load_track1, validate_track1
from gsps.walk.track2 import load_track2
from tests.conftest import EXAMPLE

pytestmark = pytest.mark.business_case


@pytest.fixture
def walk() -> tuple[list, list, list, str]:  # type: ignore[type-arg]
    return (
        load_claims(EXAMPLE / "claims.csv"),
        load_track1(EXAMPLE / "track1.csv"),
        load_track2(EXAMPLE / "track2.csv"),
        (EXAMPLE / "page.md").read_text(encoding="utf-8"),
    )


def test_walk_is_consistent(walk: tuple[list, list, list, str]) -> None:  # type: ignore[type-arg]
    claims, t1, _, _ = walk
    assert validate_routing(claims) == []
    assert validate_track1(claims, t1) == []


def test_page_is_blocked_by_exactly_these_claims(walk: tuple[list, list, list, str]) -> None:  # type: ignore[type-arg]
    claims, t1, t2, page = walk
    report = ship_check(claims, t1, t2, page_text=page)
    assert not report.ok
    assert {b.claim_id for b in report.blockers} == {"C04", "C05", "C06", "C09"}


def test_page_ships_after_the_rewrites(walk: tuple[list, list, list, str]) -> None:  # type: ignore[type-arg]
    """Apply the fixes the gate asked for: cut C04-C06 from the page, get a ruling on C09."""
    claims, t1, t2, page = walk
    cut = {"C04", "C05", "C06"}
    claims = [c.model_copy(update={"on_page": False}) if c.claim_id in cut else c for c in claims]
    t2 = [
        e.model_copy(update={"status": "ruled", "ruling": "license with consent"})
        if e.claim_id == "C09"
        else e
        for e in t2
    ]
    assert ship_check(claims, t1, t2, page_text=page).ok


def test_contested_claim_blocks(walk: tuple[list, list, list, str]) -> None:  # type: ignore[type-arg]
    claims, t1, t2, page = walk
    report = ship_check(claims, t1, t2, contested=["C01"], page_text=page)
    assert "C01" in {b.claim_id for b in report.blockers}


def test_q4_evidence_is_mixed_and_flagged() -> None:
    sources = [QualSource.model_validate(r) for r in read_rows(EXAMPLE / "qualitative.csv")]
    s = summarize_question("Q4", sources)
    assert s.lean == "mixed"
    assert "contrary" in s.flags
    assert "thin" not in s.flags
