import pytest

from gsps.rules.confidence import confidence, weakest_confidence
from gsps.vocab.values import Confidence
from tests.conftest import make_anchor


@pytest.mark.parametrize(
    ("grade", "tier", "expected"),
    [
        ("Confirmed", "government", Confidence.H),
        ("Grounded", "international", Confidence.H),
        ("Confirmed", "company-self", Confidence.H),
        ("Confirmed", "academic", Confidence.M),
        ("Grounded", "company-research", Confidence.M),
        ("Sourced", "government", Confidence.M),
        ("Sourced", "institute", Confidence.M),
        ("Sourced", "company-research", Confidence.L),
        ("Confirmed", "commercial-publisher", Confidence.L),
        ("Reported", "government", Confidence.L),
        ("Hypothesis", "internal", Confidence.L),
        ("Conjecture", "internal", Confidence.NOT_SHIPPABLE),
        ("Confirmed", "3rd-party-unknown", Confidence.L),
    ],
)
def test_confidence_table(grade: str, tier: str, expected: Confidence) -> None:
    assert confidence(make_anchor(grade=grade, authority_tier=tier)) == expected


def test_no_value_cannot_be_cited() -> None:
    assert confidence(make_anchor(value="")) == Confidence.NO_VALUE


def test_weakest_wins() -> None:
    strong = make_anchor(anchor_id="LAB-001")
    weak = make_anchor(anchor_id="LAB-002", grade="Reported")
    assert weakest_confidence([strong, weak]) == Confidence.L
    assert weakest_confidence([]) is None
