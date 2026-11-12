from gsps.cascade.derived import estimates_with_moved_inputs
from gsps.model.records import Anchor
from tests.conftest import make_anchor


def chain(
    lab_change: str = "revision", lab_vv: str = "v2", lab_walked: str = "2026-11-07"
) -> list[Anchor]:
    lab = make_anchor(
        anchor_id="LAB-001", value_version=lab_vv, change_type=lab_change, last_walked=lab_walked
    )
    est = make_anchor(
        anchor_id="EST-001",
        lane="EST",
        anchor_type="estimate",
        series_or_table="LAB-001 * 2",
        last_touch="2026-10-03",
    )
    top = make_anchor(
        anchor_id="EST-002",
        lane="EST",
        anchor_type="estimate",
        series_or_table="EST-001 + 1",
        last_touch="2026-10-03",
    )
    return [lab, est, top]


def test_moved_input_flags_the_whole_chain() -> None:
    assert estimates_with_moved_inputs(chain()) == {"EST-001": ["LAB-001"], "EST-002": ["LAB-001"]}


def test_change_before_computation_is_not_stale() -> None:
    assert estimates_with_moved_inputs(chain(lab_walked="2026-09-01")) == {}


def test_first_versions_and_bookkeeping_do_not_count() -> None:
    assert estimates_with_moved_inputs(chain(lab_vv="v1", lab_change="new_release")) == {}
    assert estimates_with_moved_inputs(chain(lab_change="")) == {}


def test_estimate_without_a_computed_date_is_skipped() -> None:
    lab, est, _ = chain()
    est = est.model_copy(update={"last_touch": "", "last_walked": ""})
    assert estimates_with_moved_inputs([lab, est]) == {}
