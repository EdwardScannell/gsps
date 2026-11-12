from pathlib import Path

import pytest

from gsps.requirements.business_case import Claim, load_claims
from gsps.vocab.values import Gate, Stance
from gsps.walk.gates import FailedFetch, FollowupItem, paste_block, paste_block_for, render_followup
from gsps.walk.qualitative import QualSource, summarize_question
from gsps.walk.run import RunFrozenError, WalkRun
from gsps.walk.track1 import Track1Entry, load_track1, validate_track1
from tests.conftest import EXAMPLE


def fact(cid: str = "C1", kind: str = "fact", track: str = "T1") -> Claim:
    return Claim(claim_id=cid, text="t", kind=kind, track=track)


def entry(**kw: object) -> Track1Entry:
    base: dict[str, object] = {
        "claim_id": "C1",
        "verdict": "CONFIRMED",
        "url": "https://owner.example/x",
        "gate": "paste",
        "verbatim": "the words",
        "grade": "Confirmed",
    }
    base.update(kw)
    return Track1Entry.model_validate(base)


def test_example_walk_is_consistent() -> None:
    assert (
        validate_track1(load_claims(EXAMPLE / "claims.csv"), load_track1(EXAMPLE / "track1.csv"))
        == []
    )


def test_confirmed_needs_documentary_grade_and_cleared_gate() -> None:
    assert validate_track1([fact()], [entry()]) == []
    assert validate_track1([fact()], [entry(grade="Reported")])
    assert validate_track1([fact()], [entry(gate="404")])
    assert validate_track1([fact()], [entry(verbatim="")])


def test_human_walk_past_a_wall_counts() -> None:
    assert validate_track1([fact()], [entry(gate="wall", human_walk=True)]) == []
    assert validate_track1([fact()], [entry(gate="wall", human_walk=False)])


def test_missing_and_duplicate_and_unknown_entries() -> None:
    assert "no Track-1 entry" in validate_track1([fact()], [])[0]
    assert any("more than one" in p for p in validate_track1([fact()], [entry(), entry()]))
    assert any(
        "unknown claim" in p for p in validate_track1([fact()], [entry(), entry(claim_id="ZZ")])
    )


def test_t2_claims_need_no_track1_entry() -> None:
    assert validate_track1([fact(kind="narrative", track="T2")], []) == []


def test_attested_only_internal_and_named() -> None:
    internal = fact(kind="internal", track="T1-INT")
    assert validate_track1([internal], [entry(verdict="ATTESTED", attested_by="ratifier")]) == []
    assert validate_track1([internal], [entry(verdict="ATTESTED")])
    assert validate_track1([fact()], [entry(verdict="ATTESTED", attested_by="ratifier")])


def test_unverifiable_needs_a_reason() -> None:
    bare = entry(verdict="UNVERIFIABLE", verbatim="", grade="", gate="")
    assert validate_track1([fact()], [bare])
    assert validate_track1([fact()], [entry(verdict="UNVERIFIABLE", ceiling="access")]) == []


def test_paste_block_dedupes_in_order() -> None:
    assert paste_block(["b", "a", "b", " "]) == "```\nb\na\n```"
    assert paste_block([]) == ""


def test_paste_block_for_failures_skips_walls() -> None:
    fails = [
        FailedFetch(url="https://x/old", gate=Gate.NOT_FOUND, corrected_url="https://x/new"),
        FailedFetch(url="https://blocked", gate=Gate.WALL),
    ]
    assert paste_block_for(fails) == "```\nhttps://x/new\n```"
    assert fails[1].needs_human_walk


def test_followup_renders() -> None:
    out = render_followup(
        [FollowupItem(date="2026-11-07", url="u", gate=Gate.WALL, check_for_human="open and paste")]
    )
    assert "| 2026-11-07 | u | wall | open and paste |" in out


def test_gate_cleared() -> None:
    assert Gate.CHAINED.cleared and not Gate.WALL.cleared


def _src(sid: str, stance: Stance, grade: str = "Sourced", tier: str = "government") -> QualSource:
    return QualSource(
        question_id="Q4",
        source_id=sid,
        title="t",
        publisher="p",
        stance=stance,
        grade=grade,
        authority_tier=tier,
    )


def test_question_summary_flags() -> None:
    s = summarize_question("Q4", [_src("1", Stance.SUPPORTS), _src("2", Stance.CONTRADICTS)])
    assert s.lean == "mixed" and "contrary" in s.flags and "thin" not in s.flags
    thin = summarize_question(
        "Q4", [_src("1", Stance.SUPPORTS, grade="Reported", tier="company-research")]
    )
    assert {"thin", "vendor-heavy"} <= set(thin.flags) and thin.lean == "supports"
    assert summarize_question("Q9", []).lean == "no evidence"


def test_run_numbering_freeze_and_verify(tmp_path: Path) -> None:
    r1 = WalkRun.create(tmp_path, "v3 draft")
    r2 = WalkRun.create(tmp_path, "v3")
    assert r1.run_id == "WR-001" and r2.run_id == "WR-002"
    assert "v3-draft" in r1.path.name
    r1.add_file("LOG.md", "walked")
    r1.freeze("first review")
    assert r1.frozen and r1.verify() == []
    with pytest.raises(RunFrozenError):
        r1.add_file("MORE.md", "x")
    with pytest.raises(RunFrozenError):
        r1.freeze()
    (r1.path / "LOG.md").write_text("tampered")
    (r1.path / "SNEAK.md").write_text("x")
    problems = r1.verify()
    assert "changed: LOG.md" in problems and "added after freeze: SNEAK.md" in problems
    assert r2.verify() == ["not frozen"]


def test_render_summaries_and_load_sources(tmp_path: Path) -> None:
    from gsps.store.csv_io import write_rows
    from gsps.walk.qualitative import load_sources, render_summaries

    p = write_rows(
        tmp_path / "q.csv",
        [
            {
                "question_id": "Q1",
                "source_id": "a",
                "title": "t",
                "publisher": "p",
                "stance": "supports",
                "grade": "Confirmed",
                "authority_tier": "government",
            }
        ],
        ["question_id", "source_id", "title", "publisher", "stance", "grade", "authority_tier"],
    )
    table = render_summaries(load_sources(p))
    assert "| Q1 | 1 | 1 | 0 | 0 | 1 | supports | thin |" in table
