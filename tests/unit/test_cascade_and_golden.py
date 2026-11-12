import pytest

from gsps.cascade.graph import CycleError, DependencyGraph
from gsps.golden.resolution import GoldenStatus, ResolutionOrder, approve, resolve, resolve_spine
from gsps.golden.spine import Basis, SpineEntry
from gsps.model.records import Citation, Token
from tests.conftest import make_anchor

ORDER = ResolutionOrder(
    name="owner-first", tiers=("government", "international", "academic", "company-research")
)


def test_full_transitive_impact() -> None:
    anchors = [
        make_anchor(anchor_id="ASM-001", lane="ASM"),
        make_anchor(
            anchor_id="EST-001", lane="EST", anchor_type="estimate", series_or_table="ASM-001 * 12"
        ),
        make_anchor(
            anchor_id="EST-002", lane="EST", anchor_type="estimate", series_or_table="EST-001 * 0.1"
        ),
    ]
    tokens = [Token(token_id="T9", depends_on="EST-002@v1")]
    cites = [Citation(deliverable_id="DEL-1", deliverable_version="v1", anchor_id="EST-002")]
    imp = DependencyGraph.build(anchors, tokens, cites).impact("ASM-001")
    assert imp.anchors == {"EST-001", "EST-002"}
    assert imp.tokens == {"T9"} and imp.deliverables == {"DEL-1"}
    assert DependencyGraph.build(anchors).upstream("EST-002") == {"EST-001", "ASM-001"}
    assert DependencyGraph.build(anchors).impact("EST-002").empty


def test_cycles_are_refused() -> None:
    a = make_anchor(anchor_id="EST-001", lane="EST", series_or_table="EST-002")
    b = make_anchor(anchor_id="EST-002", lane="EST", series_or_table="EST-001")
    with pytest.raises(CycleError):
        DependencyGraph.build([a, b])


def spine(
    aid: str,
    value: str,
    tier: str,
    grade: str = "Confirmed",
    basis: Basis = Basis.OBSERVED,
    kind: str = "metric",
) -> SpineEntry:
    return SpineEntry(
        metric_key="payrolls",
        period="2026-10",
        basis=basis,
        anchor_id=aid,
        value=value,
        reporter="r",
        authority_tier=tier,
        grade=grade,
        anchor_type=kind,
    )


def test_highest_tier_proposed() -> None:
    g = resolve(
        [spine("LAB-1", "+165,000", "government"), spine("NEWS-1", "+150,000", "company-research")],
        ORDER,
    )
    assert g.status == GoldenStatus.PROPOSED and g.anchor_id == "LAB-1"


def test_best_ranked_disagreement_is_contested() -> None:
    g = resolve([spine("A", "1", "government"), spine("B", "2", "government")], ORDER)
    assert g.status == GoldenStatus.CONTESTED and len(g.competing) == 2


def test_unknown_and_unranked_never_win() -> None:
    g = resolve(
        [spine("U", "1", "3rd-party-unknown"), spine("C", "2", "commercial-publisher")], ORDER
    )
    assert g.status == GoldenStatus.CONTESTED


def test_non_documentary_not_eligible() -> None:
    assert (
        resolve([spine("A", "1", "government", grade="Reported")], ORDER).status
        == GoldenStatus.CONTESTED
    )


def test_findings_need_a_ratifier() -> None:
    assert (
        resolve([spine("F", "x", "academic", kind="finding")], ORDER).status
        == GoldenStatus.CONTESTED
    )


def test_observed_and_projected_never_mix() -> None:
    with pytest.raises(ValueError):
        resolve(
            [spine("A", "1", "government"), spine("B", "2", "government", basis=Basis.PROJECTED)],
            ORDER,
        )
    out = resolve_spine(
        [spine("A", "1", "government"), spine("B", "2", "government", basis=Basis.PROJECTED)], ORDER
    )
    assert {g.basis for g in out} == {"observed", "projected"}


def test_approval_is_the_only_door() -> None:
    proposed = resolve([spine("A", "1", "government")], ORDER)
    approved = approve(proposed, "ratifier")
    assert approved.status == GoldenStatus.APPROVED and approved.approved_by == "ratifier"
    contested = resolve([spine("A", "1", "government"), spine("B", "2", "government")], ORDER)
    with pytest.raises(ValueError):
        approve(contested, "ratifier")
    assert approve(contested, "ratifier", value="1", anchor_id="A").value == "1"
    with pytest.raises(ValueError):
        approve(proposed, " ")
