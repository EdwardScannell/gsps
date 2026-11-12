import datetime as dt
from pathlib import Path

from gsps.deliverable.fill_report import anchors_used, build_fill_report, render_fill_report
from gsps.library import Library
from gsps.model.records import Token
from gsps.rules.integrity import run_integrity_checks
from gsps.store.csv_io import load_records
from gsps.views.build import build_views, write_views
from tests.conftest import FIXTURES


def test_library_loads_latest_versions(library: Library) -> None:
    assert library.sources["anchors"] is not None
    assert library.sources["anchors"].name == "ANCHORS_20261107.csv"
    assert library.anchors_by_id["LAB-012"].value == "+60,000"
    assert "AID-004" in library.findings


def test_views_sections(library: Library, as_of: dt.date) -> None:
    text = build_views(library, as_of, simulated=True)
    assert "SIMULATED DATE" in text
    assert "| DEL-001 | Example one-pager | review | 4 | 3 | 0 | 1 | **Behind** |" in text
    assert "UNK-001 | [effort] walk-TODO" in text
    assert "classify the source kind" in text
    assert "| EST-001 | L | ship only labeled 'estimate'" in text
    assert (
        "| LAY-002 | H | name the source in the copy" not in text
    )  # company-research is M, flagged below
    assert "LAY-002 |" in text
    assert "nature: unregistered value (YIELD) | FLAG: TRU-001=derived" in text
    assert (
        "say 'employers cited AI'" not in text
    )  # phrasing rules live in the tension row, not views
    assert "| TN-001 | T03 |" in text


def test_write_views_versions(tmp_path: Path, library: Library) -> None:
    lib = Library(root=tmp_path, anchors=library.anchors)
    p1 = write_views(lib)
    p2 = write_views(lib)
    assert p1 != p2 and p2.name.endswith("_v2.md")


def test_integrity_on_fixture(library: Library) -> None:
    flags = {
        r.name: r.offenders
        for r in run_integrity_checks(
            library.anchors,
            library.citations,
            library.deliverables,
            library.findings,
            library.registry,
        )
        if not r.ok
    }
    assert flags == {
        "citation -> missing anchor": ("OLD-001",),
        "nature: unregistered value (YIELD)": ("TRU-001=derived",),
    }


def test_fill_report_classes_and_dirt(library: Library) -> None:
    tokens = load_records(FIXTURES / "deliverable" / "TOKENS.csv", Token)
    page = (FIXTURES / "deliverable" / "page_v3.md").read_text()
    rows = {r.token_id: r for r in build_fill_report(tokens, library.anchors_by_id, page, "v3")}
    assert "T07" not in rows  # retired
    assert (
        rows["T01"].fill_class == "primary"
        and rows["T01"].confidence == "H"
        and not rows["T01"].dirty
    )
    assert rows["T02"].dirty and "LAB-012 v1->v2" in rows["T02"].dirty_reason
    assert rows["T03"].fill_class == "primary" and rows["T03"].confidence == "M"
    assert (
        rows["T04"].fill_class == "estimate"
        and rows["T04"].source_or_route == "ASM-001 * PRC-001 * 12"
    )
    assert rows["T05"].fill_class == "attested" and rows["T05"].confidence.startswith("PENDING")
    assert rows["T05"].owner == "ratifier"
    assert rows["T06"].dirty and rows["T06"].dirty_reason.startswith("visual")
    md = render_fill_report(list(rows.values()), "page_v3 (v3)")
    assert "dirty 2" in md


def test_fill_report_edit_detection(library: Library) -> None:
    t = Token(
        token_id="T01",
        depends_on="LAB-011@v1",
        expected_text="165,000 new jobs",
        locator="new jobs",
    )
    rows = build_fill_report([t], library.anchors_by_id, "October printed 150,000 new jobs", "v4")
    assert rows[0].dirty and rows[0].dirty_reason.startswith("edited")


def test_anchors_used_follows_inputs_all_the_way(library: Library) -> None:
    tokens = load_records(FIXTURES / "deliverable" / "TOKENS.csv", Token)
    used = {a.anchor_id for a in anchors_used(tokens, library.anchors_by_id)}
    assert {"EST-001", "ASM-001", "PRC-001"} <= used
    assert "LAB-012" in used
