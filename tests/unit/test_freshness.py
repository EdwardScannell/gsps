import datetime as dt

from gsps.model.records import Citation
from gsps.rules.freshness import is_stale, sync_status, worst_status
from gsps.vocab.values import SyncStatus
from tests.conftest import make_anchor

DAY = dt.date(2026, 11, 15)


def test_stale_after_next_release_without_rewalk() -> None:
    a = make_anchor(next_release="2026-11-06", last_walked="2026-10-03")
    assert is_stale(a, DAY)


def test_rewalk_after_release_is_fresh() -> None:
    a = make_anchor(next_release="2026-11-06", last_walked="2026-11-07")
    assert not is_stale(a, DAY)


def test_before_release_is_fresh() -> None:
    a = make_anchor(next_release="2026-12-04", last_walked="2026-11-07")
    assert not is_stale(a, DAY)


def test_blank_next_release_never_auto_stales() -> None:
    assert not is_stale(make_anchor(next_release="", last_walked="2020-01-01"), DAY)


def test_unparseable_dates_are_absent_not_errors() -> None:
    assert not is_stale(make_anchor(next_release="Q1 2027"), DAY)


def test_sync_states() -> None:
    anchors = {
        "LAB-001": make_anchor(anchor_id="LAB-001", value_version="v2"),
        "LAB-002": make_anchor(
            anchor_id="LAB-002", next_release="2026-11-06", last_walked="2026-10-01"
        ),
        "LAB-003": make_anchor(anchor_id="LAB-003"),
    }

    def cite(aid: str, vv: str = "v1") -> Citation:
        return Citation(
            deliverable_id="D", deliverable_version="v1", anchor_id=aid, anchor_value_version=vv
        )

    assert sync_status(cite("LAB-001"), anchors, DAY) == SyncStatus.BEHIND
    assert sync_status(cite("LAB-002"), anchors, DAY) == SyncStatus.AT_RISK
    assert sync_status(cite("LAB-003"), anchors, DAY) == SyncStatus.IN_SYNC
    assert sync_status(cite("LAB-999"), anchors, DAY) == SyncStatus.DANGLING


def test_worst_status_rolls_up() -> None:
    assert (
        worst_status([SyncStatus.IN_SYNC, SyncStatus.BEHIND, SyncStatus.AT_RISK])
        == SyncStatus.BEHIND
    )
    assert worst_status([]) is None
