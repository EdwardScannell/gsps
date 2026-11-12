"""The live walk example, executed: ingest the November 7, 2026 walk of public October
releases into the October 3 library and check the whole ripple."""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

import pytest

from gsps.cascade.derived import estimates_with_moved_inputs
from gsps.deliverable.fill_report import build_fill_report
from gsps.library import Library
from gsps.model.records import Token
from gsps.rules.estimates import recompute
from gsps.rules.freshness import sync_status
from gsps.store.csv_io import load_records
from gsps.walk.ingest import Outcome, ingest, load_walks
from tests.conftest import ROOT

pytestmark = pytest.mark.business_case
LIVE = ROOT / "examples" / "live_walk"
DAY = dt.date(2026, 11, 12)


@pytest.fixture
def lib(tmp_path: Path) -> Path:
    shutil.copytree(LIVE / "library", tmp_path / "library")
    return tmp_path / "library"


def test_live_walk_ripple(lib: Path) -> None:
    before = Library.load(lib)
    result = ingest(
        lib,
        load_walks(LIVE / "walks_20261107.csv"),
        before.anchors,
        on=DAY,
        registry=before.registry,
    )
    outcomes = {ln.anchor_id: ln.outcome for ln in result.lines}
    assert outcomes == {
        "LAB-010": Outcome.REVISED,
        "LAB-012": Outcome.REVISED,
        "LAB-013": Outcome.ADDED,
        "JLT-001": Outcome.ADDED,
        "LAY-002": Outcome.ADDED,
        "AID-001": Outcome.ADDED,
        "APP-001": Outcome.REFUSED,
        "GHO-001": Outcome.REFUSED,
    }
    assert result.yields == []
    assert (lib / "ANCHORS_20261112.csv").exists()  # the old version is untouched

    after = Library.load(lib)
    assert after.sources["anchors"] is not None
    assert after.sources["anchors"].name == "ANCHORS_20261112_v2.csv"
    by_id = after.anchors_by_id
    statuses = {c.anchor_id: sync_status(c, by_id, DAY).value for c in after.citations}
    assert statuses == {"LAB-012": "Behind", "EST-001": "In sync", "FCT-001": "In sync"}
    assert estimates_with_moved_inputs(after.anchors) == {"EST-001": ["LAB-010", "LAB-012"]}

    tokens = load_records(LIVE / "TOKENS.csv", Token)
    page = (LIVE / "page_v1.md").read_text(encoding="utf-8")
    rows = {r.token_id: r for r in build_fill_report(tokens, by_id, page, "v1")}
    assert rows["T01"].dirty and "LAB-012 v1->v2" in rows["T01"].dirty_reason
    assert rows["T02"].dirty and "inputs moved" in rows["T02"].dirty_reason
    assert not rows["T03"].dirty

    check = recompute(
        "(LAB-010 + LAB-012) / 2",
        {"LAB-010": by_id["LAB-010"].value, "LAB-012": by_id["LAB-012"].value},
        "81,000",
    )
    assert not check.ok and check.recomputed == 123_000


def test_wider_net_clears_thin_and_vendor_heavy_flags() -> None:
    from gsps.walk.qualitative import load_sources, summarize_question

    before = load_sources(LIVE / "qualitative_20261107.csv")
    after = load_sources(LIVE / "qualitative_20261112.csv")
    assert set(summarize_question("Q2", before).flags) == {"thin", "vendor-heavy"}
    assert summarize_question("Q5", before).flags == ("thin",)
    q2, q5 = summarize_question("Q2", after), summarize_question("Q5", after)
    assert q2.flags == () and q5.flags == ()
    assert q2.stances.get("complicates") == 3 and q5.stances.get("complicates") == 1
    assert all(len(s.verbatim) < 125 and s.url.startswith("https://") for s in after)
