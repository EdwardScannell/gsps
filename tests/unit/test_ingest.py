from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from gsps.model.records import Anchor, Citation
from gsps.store.csv_io import load_records, read_rows
from gsps.vocab.registry import Registry
from gsps.walk.ingest import Outcome, WalkedValue, apply_walks, bump, ingest
from tests.conftest import make_anchor

DAY = dt.date(2026, 11, 12)
BLS = "https://www.bls.gov/news.release/empsit.nr0.htm"


def walk(**kw: object) -> WalkedValue:
    base: dict[str, object] = {
        "anchor_id": "LAB-001",
        "value_1": "+60,000",
        "value_2": "+60,000",
        "verbatim": "the change for September was revised up by 31,000, from +29,000 to +60,000",
        "url": BLS,
        "gate": "paste",
        "walked_on": "2026-11-07",
        "as_of": "2026-09",
    }
    base.update(kw)
    return WalkedValue.model_validate(base)


NEW = {
    "lane": "LAB",
    "anchor_type": "metric",
    "metric": "Payroll change",
    "owner": "BLS",
    "grade": "Confirmed",
    "authority_tier": "government",
    "nature": "external-primary",
}


def existing(**kw: str) -> Anchor:
    base = {"value": "+29,000", "as_of": "2026-09", "value_version": "v1", "record_version": "v1"}
    base.update(kw)
    return make_anchor(**base)


@pytest.mark.parametrize(("old", "new"), [("v1", "v2"), ("v9", "v10"), ("junk", "v2")])
def test_bump(old: str, new: str) -> None:
    assert bump(old) == new


def test_revision_bumps_value_version_and_keeps_prior() -> None:
    r = apply_walks([existing()], [walk()], on=DAY)
    (line,) = r.lines
    a = r.anchors[0]
    assert line.outcome == Outcome.REVISED
    assert (a.value, a.value_version, a.record_version) == ("+60,000", "v2", "v2")
    assert (a.prior_value, a.change_type, a.last_walked) == ("+29,000", "revision", "2026-11-07")
    assert r.value_changes == [line]


def test_new_period_is_a_new_release() -> None:
    r = apply_walks(
        [existing()], [walk(value_1="+165,000", value_2="+165,000", as_of="2026-10")], on=DAY
    )
    a = r.anchors[0]
    assert r.lines[0].outcome == Outcome.NEW_RELEASE
    assert (a.as_of, a.value_version, a.change_type) == ("2026-10", "v2", "new_release")


def test_rewalk_same_value_is_bookkeeping_only() -> None:
    r = apply_walks([existing()], [walk(value_1="+29,000", value_2="+29,000")], on=DAY)
    a = r.anchors[0]
    assert r.lines[0].outcome == Outcome.REWALKED
    assert (a.value_version, a.record_version) == ("v1", "v2")
    assert r.value_changes == []


def test_new_anchor_added_with_required_fields() -> None:
    r = apply_walks([], [walk(anchor_id="LAB-002", **NEW)], on=DAY)
    assert r.lines[0].outcome == Outcome.ADDED
    a = r.anchors[0]
    assert (a.value_version, a.change_type, a.ceiling, a.grade) == (
        "v1",
        "new_release",
        "none",
        "Confirmed",
    )


@pytest.mark.parametrize(
    ("kw", "needle"),
    [
        ({"value_2": "+59,000"}, "extractions disagree"),
        ({"is_owner_primary": "false"}, "a lead points to the page"),
        ({"gate": "404"}, "did not clear"),
        ({"gate": "wall"}, "needs a human walk"),
    ],
)
def test_refusals(kw: dict[str, object], needle: str) -> None:
    r = apply_walks([existing()], [walk(**kw)], on=DAY)
    assert r.lines[0].outcome == Outcome.REFUSED and needle in r.lines[0].detail
    assert r.anchors[0].value == "+29,000"  # untouched


def test_wall_with_human_walk_is_accepted() -> None:
    r = apply_walks([existing()], [walk(gate="wall", human_walk="true")], on=DAY)
    assert r.lines[0].outcome == Outcome.REVISED


def test_new_anchor_refusals() -> None:
    missing = apply_walks([], [walk(anchor_id="LAB-002", lane="LAB")], on=DAY)
    assert "new anchor missing" in missing.lines[0].detail
    wrong_lane = apply_walks([], [walk(anchor_id="LAY-002", **NEW)], on=DAY)
    assert "does not match lane" in wrong_lane.lines[0].detail


def test_duplicate_in_batch_refused() -> None:
    r = apply_walks([existing()], [walk(), walk()], on=DAY)
    assert [ln.outcome for ln in r.lines] == [Outcome.REVISED, Outcome.REFUSED]


def test_yields_reported_for_touched_anchors() -> None:
    r = apply_walks(
        [],
        [walk(anchor_id="LAB-002", **{**NEW, "nature": "derived"})],
        on=DAY,
        registry=Registry.default(),
    )
    assert any(y.column == "nature" and y.value == "derived" for y in r.yields)


def test_ingest_writes_new_versions_and_never_overwrites(tmp_path: Path) -> None:
    anchors = [existing(), existing(anchor_id="LAB-009", custom_col="kept")]
    r1 = ingest(tmp_path, [walk()], anchors, on=DAY)
    assert r1.anchors_path is not None and r1.anchors_path.name == "ANCHORS_20261112.csv"
    assert r1.walk_log_path is not None and r1.walk_log_path.parent.name == "WALKS"
    reloaded = {a.anchor_id: a for a in load_records(r1.anchors_path, Anchor)}
    assert reloaded["LAB-001"].value_version == "v2"
    assert (reloaded["LAB-009"].model_extra or {}).get("custom_col") == "kept"
    r2 = ingest(tmp_path, [walk(value_1="+61,000", value_2="+61,000")], r1.anchors, on=DAY)
    assert r2.anchors_path is not None and r2.anchors_path.name == "ANCHORS_20261112_v2.csv"
    log = read_rows(r2.walk_log_path)
    assert (
        log[0]["outcome"] == "revised"
        and log[0]["gate"] == "paste"
        and "revised up" in log[0]["verbatim"]
    )


def test_all_refused_writes_log_but_no_anchors(tmp_path: Path) -> None:
    r = ingest(tmp_path, [walk(gate="404")], [existing()], on=DAY)
    assert r.anchors_path is None and r.walk_log_path is not None
    assert r.refused and read_rows(r.walk_log_path)[0]["outcome"] == "refused"


def test_impacts_follow_estimates_to_documents() -> None:
    est = make_anchor(
        anchor_id="EST-001", lane="EST", anchor_type="estimate", series_or_table="LAB-001 * 3"
    )
    cite = Citation(deliverable_id="DEL-1", deliverable_version="v1", anchor_id="EST-001")
    r = apply_walks([existing(), est], [walk()], on=DAY)
    (imp,) = r.impacts([cite])
    assert imp.source == "LAB-001" and imp.anchors == {"EST-001"} and imp.deliverables == {"DEL-1"}
