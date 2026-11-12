import datetime as dt
from pathlib import Path

import pytest

from gsps.store.csv_io import read_rows, write_rows
from gsps.store.fingerprint import sha256_bytes, sha256_file
from gsps.store.versioned import (
    latest,
    mark_to_delete,
    next_version_path,
    parse_versioned,
    write_new,
)

DAY = dt.date(2026, 11, 7)


def test_parse_versioned() -> None:
    vn = parse_versioned("ANCHORS_20261107_v3.csv")
    assert vn is not None and (vn.stem, vn.date, vn.version) == ("ANCHORS", "20261107", 3)
    first = parse_versioned("ANCHORS_20261107.csv")
    assert first is not None and first.version == 1
    marked = parse_versioned("TO_DELETE_ANCHORS_20261107_v2.csv")
    assert marked is not None and marked.marked_for_delete
    assert parse_versioned("README.md") is None


def test_first_version_has_no_suffix(tmp_path: Path) -> None:
    assert next_version_path(tmp_path, "ANCHORS", "csv", DAY).name == "ANCHORS_20261107.csv"


def test_latest_picks_newest_date_then_version(tmp_path: Path) -> None:
    for n in [
        "ANCHORS_20261101_v9.csv",
        "ANCHORS_20261107.csv",
        "ANCHORS_20261107_v2.csv",
        "TO_DELETE_ANCHORS_20261107_v5.csv",
    ]:
        (tmp_path / n).write_text("x")
    found = latest(tmp_path, "ANCHORS")
    assert found is not None and found.name == "ANCHORS_20261107_v2.csv"


def test_latest_ignores_other_stems(tmp_path: Path) -> None:
    (tmp_path / "ANCHORS_USED_20261107.csv").write_text("x")
    assert latest(tmp_path, "ANCHORS") is None


def test_write_new_never_overwrites(tmp_path: Path) -> None:
    p = write_new(tmp_path / "a.md", "one")
    with pytest.raises(FileExistsError):
        write_new(p, "two")
    assert p.read_text() == "one"


def test_mark_to_delete_renames_never_deletes(tmp_path: Path) -> None:
    p = tmp_path / "VIEWS_20261107.md"
    p.write_text("x")
    target = mark_to_delete(p)
    assert target.name == "TO_DELETE_VIEWS_20261107.md" and target.exists() and not p.exists()
    assert mark_to_delete(target) == target


def test_csv_round_trip_refuses_overwrite(tmp_path: Path) -> None:
    p = write_rows(tmp_path / "t.csv", [{"a": "1, with comma", "b": 'quote "x"'}], ["a", "b"])
    assert read_rows(p) == [{"a": "1, with comma", "b": 'quote "x"'}]
    with pytest.raises(FileExistsError):
        write_rows(p, [], ["a"])
    assert read_rows(None) == []


def test_fingerprints(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == sha256_bytes(b"abc")
