import pytest

from gsps.rules.grading import (
    ExtractionMismatch,
    LeadIsNotASource,
    accept_value,
    can_ship_with_ceiling,
    normalize_text,
    weakest_grade,
)
from gsps.vocab.values import Grade


def test_matching_extractions_enter() -> None:
    assert (
        accept_value("rose by 165,000", "rose  by 165,000", is_owner_primary=True)
        == "rose by 165,000"
    )


def test_typography_is_normalized_but_not_numbers() -> None:
    assert normalize_text("\u201cup 2\u2013%\u201d") == '"up 2-%"'
    with pytest.raises(ExtractionMismatch):
        accept_value("165,000", "165,500", is_owner_primary=True)


def test_missing_extraction_rejected() -> None:
    with pytest.raises(ExtractionMismatch):
        accept_value("165,000", "", is_owner_primary=True)


def test_lead_rejected() -> None:
    with pytest.raises(LeadIsNotASource):
        accept_value("165,000", "165,000", is_owner_primary=False)


def test_effort_ceiling_never_ships() -> None:
    assert not can_ship_with_ceiling("effort")
    for c in ("none", "access", "structural"):
        assert can_ship_with_ceiling(c)


def test_weakest_grade() -> None:
    assert weakest_grade(["Confirmed", "Reported", "Sourced"]) == Grade.REPORTED
    assert weakest_grade(["not-a-grade"]) is None
