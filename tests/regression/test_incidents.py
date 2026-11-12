"""Real incidents, each turned into a permanent test.

Every test names the failure it guards against. When a new failure is caught in a live
walk, it gets a test here before the fix is merged.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from gsps.model.records import Citation
from gsps.requirements.business_case import Claim
from gsps.rules.estimates import recompute
from gsps.rules.freshness import sync_status
from gsps.rules.grading import ExtractionMismatch, LeadIsNotASource, accept_value
from gsps.rules.integrity import run_integrity_checks
from gsps.vocab.registry import Registry
from gsps.vocab.values import SyncStatus
from gsps.walk.ship import ship_check
from gsps.walk.track1 import Track1Entry, validate_track1
from gsps.walk.track2 import AssumptionEntry
from tests.conftest import make_anchor

pytestmark = pytest.mark.regression


def test_summarizer_invented_a_table_row() -> None:
    """A fetch summary reported an age-band row the agency's table does not have.
    The second, verbatim extraction did not contain it, so the value must not enter."""
    summary = "Unemployment duration, 55 and over: 26.2 weeks"
    verbatim = "Unemployment duration, 55 to 64: 26.2 weeks"
    with pytest.raises(ExtractionMismatch):
        accept_value(summary, verbatim, is_owner_primary=True)


def test_seasonally_adjusted_vs_not_adjusted_are_different_values() -> None:
    """4.2% (seasonally adjusted) and 4.0% (not adjusted) for the same month are two
    distinct series. They never reconcile into one value."""
    with pytest.raises(ExtractionMismatch):
        accept_value("4.2 percent", "4.0 percent", is_owner_primary=True)
    sa = make_anchor(anchor_id="LAB-001", series_or_table="CPS, seasonally adjusted", value="4.2%")
    nsa = make_anchor(
        anchor_id="LAB-002", series_or_table="CPS, not seasonally adjusted", value="4.0%"
    )
    assert sa.series_or_table != nsa.series_or_table


def test_keeper_coined_a_vocabulary_value() -> None:
    """The keeper once wrote an owner/nature value nobody had registered. It must yield."""
    a = make_anchor(anchor_id="EST-001", lane="EST", nature="derived")
    results = {r.name: r for r in run_integrity_checks([a], [], [], {}, Registry.default())}
    assert results["nature: unregistered value (YIELD)"].offenders == ("EST-001=derived",)


def test_lead_tried_to_grade_a_claim() -> None:
    """A search synthesis 'confirmed' a figure. A lead points to the page; it never grades."""
    with pytest.raises(LeadIsNotASource):
        accept_value("+165,000", "+165,000", is_owner_primary=False)
    claim = Claim(claim_id="C1", text="payrolls rose", kind="fact", track="T1")
    lead = Track1Entry.model_validate(
        {
            "claim_id": "C1",
            "verdict": "CONFIRMED",
            "url": "https://search.example",
            "gate": "click",
            "verbatim": "payrolls rose 165,000",
            "grade": "Confirmed",
            "is_lead": True,
        }
    )
    assert any("a lead cannot" in p for p in validate_track1([claim], [lead]))


def test_market_size_was_one_tenth_of_its_own_math() -> None:
    """A page stated $234M-$374M as 5M-8M people x $39/mo x 12. The math gives $2.34B-$3.74B:
    the stated range was exactly one-tenth (an unstated 10% penetration)."""
    for people, stated in [(5_000_000, "$234M"), (8_000_000, "$374M")]:
        check = recompute("SAM-001 * PRC-001 * 12", {"SAM-001": people, "PRC-001": 39}, stated)
        assert not check.ok
        assert check.ratio == pytest.approx(0.1, rel=0.01)


def test_only_one_claim_cannot_be_confirmed() -> None:
    """'We're the only one that submits only what you approved' was disproved by competitors'
    own pages. An absence claim can be shown WRONG; it can never be CONFIRMED."""
    claim = Claim(claim_id="C4", text="the only one", kind="absence", track="T1")
    confirmed = Track1Entry.model_validate(
        {
            "claim_id": "C4",
            "verdict": "CONFIRMED",
            "url": "https://owner.example",
            "gate": "paste",
            "verbatim": "we review",
            "grade": "Confirmed",
        }
    )
    assert any("never confirmed" in p for p in validate_track1([claim], [confirmed]))


def test_prior_month_revised_puts_citation_behind() -> None:
    """September payrolls were cited at +29,000; the October release revised them to +60,000.
    The page citing v1 must go Behind; a metadata-only edit must not."""
    revised = make_anchor(
        anchor_id="LAB-012", value="+60,000", value_version="v2", record_version="v2"
    )
    cite = Citation(
        deliverable_id="D", deliverable_version="v3", anchor_id="LAB-012", anchor_value_version="v1"
    )
    assert sync_status(cite, {"LAB-012": revised}, dt.date(2026, 11, 8)) == SyncStatus.BEHIND
    relabeled = make_anchor(anchor_id="LAB-012", value_version="v1", record_version="v7")
    assert sync_status(cite, {"LAB-012": relabeled}, dt.date(2026, 11, 8)) == SyncStatus.IN_SYNC


def test_internal_proof_case_without_a_receipt_blocks_ship() -> None:
    """A page's proof case said a credential was 'banked, now deploys forever'; the records
    showed it was not banked yet and the count was not reachable. No receipt, no ship."""
    claim = Claim(claim_id="C6", text="banked, deploys forever", kind="internal", track="T1-INT")
    no_receipt = Track1Entry.model_validate(
        {
            "claim_id": "C6",
            "verdict": "UNVERIFIABLE",
            "ceiling": "access",
            "note": "tracker not reachable",
        }
    )
    report = ship_check([claim], [no_receipt], [])
    assert not report.ok and "UNVERIFIABLE" in report.blockers[0].reason


def test_legal_assertion_waits_for_the_ratifier() -> None:
    """'We can safely sell this data' is a legal assertion. Registered is not enough."""
    claim = Claim(claim_id="C9", text="safely sell", kind="legal", track="T2")
    kept = AssumptionEntry.model_validate(
        {"claim_id": "C9", "basis": "none", "label": "legal assertion", "status": "keep"}
    )
    assert not ship_check([claim], [], [kept]).ok
    ruled = kept.model_copy(update={"status": "ruled", "ruling": "say 'with consent'"})
    assert ship_check([claim], [], [ruled]).ok


def test_unvalidated_copy_with_bad_status_blocks_instead_of_crashing() -> None:
    """model_copy(update=...) skips validation; a typo'd status once crashed the gate.
    The gate must coerce, and block on an unknown status rather than pass or raise."""
    claim = Claim(claim_id="C8", text="x", kind="narrative", track="T2")
    entry = AssumptionEntry.model_validate(
        {"claim_id": "C8", "basis": "b", "label": "framing", "status": "keep"}
    )
    typo = entry.model_copy(update={"status": "kept"})
    report = ship_check([claim], [], [typo])
    assert not report.ok and "unknown register status" in report.blockers[0].reason


def test_effort_ceiling_is_not_a_resting_state() -> None:
    """A walk parked at 'effort' looked finished in a report. It is a to-do and blocks."""
    claim = Claim(claim_id="C1", text="x", kind="fact", track="T1")
    parked = Track1Entry.model_validate(
        {
            "claim_id": "C1",
            "verdict": "UNVERIFIABLE",
            "ceiling": "effort",
            "note": "ran out of time",
        }
    )
    assert any("effort ceiling" in p for p in validate_track1([claim], [parked]))


def test_offer_reported_as_cut() -> None:
    """A voluntary exit offer to tens of thousands was headlined like a layoff. Offers and
    cuts are distinct kinds; the engine keeps them as distinct metrics (never fold)."""
    offer = make_anchor(
        anchor_id="LAY-010", lane="LAY", metric="Employees eligible for a voluntary exit offer"
    )
    cuts = make_anchor(anchor_id="LAY-002", lane="LAY", metric="Announced job cuts")
    assert offer.metric != cuts.metric and offer.anchor_id != cuts.anchor_id


def test_september_revision_ripples_through_ingest(tmp_path: Path) -> None:
    """September payrolls were cited at +29,000; October's release revised them to +60,000.
    Ingesting the walk must bump the value version, put the page's citation Behind and flag
    the estimate built on it, end to end through the command line."""
    from typer.testing import CliRunner

    from gsps.cli import app
    from gsps.model.records import ANCHOR_COLUMNS
    from gsps.store.csv_io import write_rows

    lib = tmp_path / "lib"
    (lib / "CITATION_MAP").mkdir(parents=True)
    sep = make_anchor(anchor_id="LAB-012", value="+29,000", as_of="2026-09").as_row()
    avg = make_anchor(
        anchor_id="EST-001",
        lane="EST",
        anchor_type="estimate",
        value="+81,000",
        series_or_table="(LAB-010 + LAB-012) / 2",
        grade="Hypothesis",
        authority_tier="internal",
        nature="derived-estimate",
    ).as_row()
    aug = make_anchor(anchor_id="LAB-010", value="+133,000", as_of="2026-08").as_row()
    write_rows(lib / "ANCHORS_20261003.csv", [aug, sep, avg], ANCHOR_COLUMNS)
    write_rows(
        lib / "CITATION_MAP" / "CITATION_MAP_20261003.csv",
        [
            {
                "deliverable_id": "DEL-1",
                "deliverable_version": "v1",
                "anchor_id": "LAB-012",
                "anchor_value_version": "v1",
                "location": "P1",
            }
        ],
        ["deliverable_id", "deliverable_version", "anchor_id", "anchor_value_version", "location"],
    )
    walks = tmp_path / "walks.csv"
    write_rows(
        walks,
        [
            {
                "anchor_id": "LAB-012",
                "value_1": "+60,000",
                "value_2": "+60,000",
                "as_of": "2026-09",
                "verbatim": "from +29,000 to +60,000",
                "url": "https://www.bls.gov/news.release/empsit.nr0.htm",
                "gate": "paste",
                "walked_on": "2026-11-07",
            }
        ],
        ["anchor_id", "value_1", "value_2", "as_of", "verbatim", "url", "gate", "walked_on"],
    )
    result = CliRunner().invoke(
        app, ["ingest", "-l", str(lib), "--walks", str(walks), "--on", "2026-11-12"]
    )
    assert result.exit_code == 0, result.output
    assert "revised      LAB-012   LAB-012 v1->v2: +29,000 -> +60,000" in result.output
    assert "estimates/anchors: EST-001" in result.output
    assert "citation DEL-1 v1 P1: cites v1, now Behind" in result.output
    assert (lib / "ANCHORS_20261112.csv").exists() and (lib / "ANCHORS_20261003.csv").exists()


def test_blank_csv_cell_turned_every_walk_into_a_lead() -> None:
    """The first live ingest refused every walk as 'a lead': a blank is_owner_primary cell was
    parsed as false. A blank cell means the default; only an explicit 'false' marks a lead."""
    from gsps.walk.ingest import WalkedValue

    base = {
        "anchor_id": "LAB-001",
        "value_1": "1",
        "value_2": "1",
        "verbatim": "v",
        "url": "https://owner.example",
        "gate": "paste",
        "walked_on": "2026-11-07",
    }
    blank = WalkedValue.model_validate({**base, "is_owner_primary": "", "human_walk": ""})
    assert blank.is_owner_primary is True and blank.human_walk is False
    lead = WalkedValue.model_validate({**base, "is_owner_primary": "false"})
    assert lead.is_owner_primary is False
    with pytest.raises(ValueError):
        WalkedValue.model_validate({**base, "is_owner_primary": "maybe"})
