from pathlib import Path

import pytest
from typer.testing import CliRunner

from gsps.cli import app
from gsps.requirements.business_case import Claim
from gsps.walk.ship import ship_check
from gsps.walk.track2 import AssumptionEntry
from tests.conftest import EXAMPLE, FIXTURES

runner = CliRunner()
LIB = str(FIXTURES / "library")
EX = {k: str(EXAMPLE / f"{k}.csv") for k in ("claims", "track1", "track2")}


def run(*args: str) -> tuple[int, str]:
    r = runner.invoke(app, list(args))
    return r.exit_code, r.output


def test_version() -> None:
    assert run("version") == (0, "0.2.0\n")


def test_views_dry_and_write(tmp_path: Path) -> None:
    code, out = run("views", "-l", LIB, "--as-of", "2026-11-15", "--dry")
    assert code == 0 and "SIMULATED DATE" in out
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "ANCHORS_20261107.csv").write_text(
        (FIXTURES / "library" / "ANCHORS_20261107.csv").read_text()
    )
    code, out = run("views", "-l", str(lib))
    assert code == 0 and "wrote" in out and list((lib / "VIEWS").glob("VIEWS_*.md"))


def test_vocab_check_flags_and_exits_1() -> None:
    code, out = run("vocab-check", "-l", LIB)
    assert code == 1 and "FLAG  nature: unregistered value (YIELD): TRU-001=derived" in out


def test_fill_report_exits_1_when_dirty() -> None:
    code, out = run(
        "fill-report",
        "-l",
        LIB,
        "--tokens",
        str(FIXTURES / "deliverable" / "TOKENS.csv"),
        "--page",
        str(FIXTURES / "deliverable" / "page_v3.md"),
        "--doc-version",
        "v3",
    )
    assert code == 1 and "dirty 2" in out


def test_validate_walk_ok() -> None:
    code, out = run("validate-walk", "--claims", EX["claims"], "--track1", EX["track1"])
    assert code == 0 and "walk is consistent" in out


def test_validate_walk_problems(tmp_path: Path) -> None:
    claims = tmp_path / "c.csv"
    claims.write_text("claim_id,text,kind,track\nC1,x,estimate,T1\n")
    track1 = tmp_path / "t.csv"
    track1.write_text("claim_id,verdict\n")
    code, out = run("validate-walk", "--claims", str(claims), "--track1", str(track1))
    assert code == 1 and "must route to T2" in out


def test_ship_check_blocks_and_contested() -> None:
    code, out = run(
        "ship-check",
        "--claims",
        EX["claims"],
        "--track1",
        EX["track1"],
        "--track2",
        EX["track2"],
        "--page",
        str(EXAMPLE / "page.md"),
        "--contested",
        "C01",
    )
    assert code == 1 and "SHIP: BLOCKED (5 of 11)" in out and "contested" in out


def test_impact() -> None:
    code, out = run(
        "impact",
        "-l",
        LIB,
        "--anchor",
        "ASM-001",
        "--tokens",
        str(FIXTURES / "deliverable" / "TOKENS.csv"),
    )
    assert code == 0 and "EST-001" in out and "T04" in out and "DEL-001" in out


def test_recompute_exit_codes() -> None:
    refused = run(
        "recompute", "--method", "A-B", "--stated", "1", "--input", "A=3", "--input", "B=2"
    )
    assert refused[0] == 2  # inputs must be anchor IDs; "A" and "B" are refused
    wrong = run(
        "recompute", "--method", "SAM-001 * 12", "--stated", "$234M", "--input", "SAM-001=195000000"
    )
    assert wrong[0] == 1 and "DOES NOT REPRODUCE" in wrong[1]
    code, out = run(
        "recompute",
        "--method",
        "SAM-001 * PRC-001 * 12",
        "--stated",
        "$2.34B",
        "--input",
        "SAM-001=5,000,000",
        "--input",
        "PRC-001=39",
    )
    assert code == 0 and "reproduces" in out and "2,340,000,000" in out


def test_paste_block_and_new_run(tmp_path: Path) -> None:
    code, out = run("paste-block", "https://a", "https://a", "https://b")
    assert code == 0 and out.count("https://a") == 1
    code, out = run("new-run", "--runs-dir", str(tmp_path), "--doc-version", "v3")
    assert code == 0 and "WR-001_v3_" in out


def test_brief() -> None:
    code, out = run("brief", str(EXAMPLE / "brief.yaml"))
    assert code == 0 and "Q4: Is AI" in out and "held:     unit economics" in out


def test_ship_render_and_t2_branches() -> None:
    def claim(cid: str, kind: str) -> Claim:
        return Claim(claim_id=cid, text="t", kind=kind, track="T2")

    def reg(cid: str, status: str, **kw: str) -> AssumptionEntry:
        return AssumptionEntry.model_validate(
            {"claim_id": cid, "basis": "b", "label": "estimate", "status": status, **kw}
        )

    claims = [
        claim("A", "narrative"),
        claim("B", "narrative"),
        claim("C", "narrative"),
        claim("D", "estimate"),
        claim("E", "narrative"),
        claim("F", "narrative"),
    ]
    entries = [
        reg("A", "pending"),
        reg("B", "cut"),
        reg("C", "soften"),
        reg("D", "keep"),
        reg("E", "soften", proposed_wording="softer"),
    ]
    report = ship_check(claims, [], entries, page_text="no label here")
    reasons = {line.claim_id: line.reason for line in report.lines}
    assert reasons["A"] == "pending the ratifier"
    assert reasons["B"].startswith("registered as cut")
    assert reasons["C"].startswith("soften without")
    assert reasons["D"].startswith("estimate not labeled")
    assert reasons["F"] == "not registered"
    assert report.render().startswith("SHIP: BLOCKED (5 of 6)")
    assert ship_check([], [], []).render().startswith("SHIP: PASS")


def test_library_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GSPS_LIBRARY", LIB)
    code, out = run("views", "--as-of", "2026-11-15", "--dry")
    assert code == 0 and "SIMULATED DATE" in out


def test_qual_summary() -> None:
    code, out = run("qual-summary", "--sources", str(EXAMPLE / "qualitative.csv"))
    assert code == 0 and "| Q4 | 5 | 1 | 3 | 1 | 4 | mixed | contrary |" in out
    code, out = run(
        "qual-summary", "--sources", str(EXAMPLE / "qualitative.csv"), "--question", "Q9"
    )
    assert code == 0 and "| Q4 |" not in out
