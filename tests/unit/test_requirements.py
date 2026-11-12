import pytest
from pydantic import ValidationError

from gsps.requirements.brief import load_brief
from gsps.requirements.business_case import Claim, load_claims, validate_routing
from gsps.requirements.shopping import (
    Band,
    ShoppingReport,
    ShoppingRequest,
    ShoppingToken,
    TokenRecord,
    mark_dirty,
    validate_report,
)
from tests.conftest import EXAMPLE


def test_brief_loads() -> None:
    b = load_brief(EXAMPLE / "brief.yaml")
    assert b.blind
    assert [q.id for q in b.questions] == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert b.is_held("unit economics")
    assert b.page_inputs[0].path == "page.md"
    assert b.question("Q4").text.startswith("Is AI")
    with pytest.raises(KeyError):
        b.question("Q9")


def test_example_claims_route_correctly() -> None:
    assert validate_routing(load_claims(EXAMPLE / "claims.csv")) == []


@pytest.mark.parametrize(
    ("kind", "track"),
    [("estimate", "T1"), ("fact", "T2"), ("internal", "T1"), ("legal", "T1"), ("absence", "T2")],
)
def test_misrouting_is_caught(kind: str, track: str) -> None:
    c = Claim(claim_id="X", text="t", kind=kind, track=track)
    assert validate_routing([c])


def test_duplicate_claim_ids() -> None:
    c = Claim(claim_id="X", text="t", kind="fact", track="T1")
    assert "duplicate" in validate_routing([c, c])[0]


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        Claim(claim_id="X", text="t", kind="vibe", track="T1")


def _request() -> ShoppingRequest:
    return ShoppingRequest(
        request_id="SR-1",
        document="page",
        tokens=[
            ShoppingToken(token_id="T1", ask="payrolls"),
            ShoppingToken(token_id="T2", ask="ARR"),
        ],
    )


def _sourced(**kw: object) -> TokenRecord:
    base: dict[str, object] = {
        "token_id": "T1",
        "value": "+165,000",
        "class": "sourced",
        "confidence": "H",
        "source_or_route": "BLS <url>",
        "reason": "owner's release",
    }
    base.update(kw)
    return TokenRecord.model_validate(base)


def _estimate(**kw: object) -> TokenRecord:
    base: dict[str, object] = {
        "token_id": "T2",
        "value": "$2.34B",
        "class": "estimate",
        "confidence": "L",
        "source_or_route": "ASM-001 * PRC-001 * 12",
        "reason": "full-market",
        "range": Band(low="$1.9B", mid="$2.34B", high="$2.8B"),
        "depends_on": ("ASM-001", "PRC-001"),
    }
    base.update(kw)
    return TokenRecord.model_validate(base)


def test_complete_report_releases() -> None:
    assert (
        validate_report(
            _request(), ShoppingReport(request_id="SR-1", records=[_sourced(), _estimate()])
        )
        == []
    )


def test_bare_stray_and_duplicate_tokens() -> None:
    report = ShoppingReport(
        request_id="SR-1", records=[_sourced(), _sourced(), _sourced(token_id="T9")]
    )
    problems = " | ".join(validate_report(_request(), report))
    assert "T2: ships bare" in problems
    assert "T9: stray" in problems
    assert "T1: answered more than once" in problems


def test_estimate_discipline() -> None:
    no_band = _estimate(range=None)
    not_mid = _estimate(value="$2.8B")
    no_route = _estimate(source_or_route=" ")
    for rec, needle in [(no_band, "band"), (not_mid, "mid"), (no_route, "missing route")]:
        problems = validate_report(
            _request(), ShoppingReport(request_id="SR-1", records=[_sourced(), rec])
        )
        assert any(needle in p for p in problems), (needle, problems)


def test_dirty_blocks_release_and_cascades() -> None:
    report = ShoppingReport(request_id="SR-1", records=[_sourced(), _estimate()])
    dirty = mark_dirty(report, {"PRC-001"})
    rec = dirty.record("T2")
    assert rec is not None and rec.dirty and "PRC-001" in rec.dirty_reason
    assert not dirty.record("T1").dirty  # type: ignore[union-attr]
    assert any("dirty" in p for p in validate_report(_request(), dirty))


def test_wrong_request_id() -> None:
    report = ShoppingReport(request_id="SR-2", records=[_sourced(), _estimate()])
    assert "answers SR-2" in validate_report(_request(), report)[0]
