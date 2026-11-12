"""CSV access. Files are only ever read and written through the csv module (no string edits)."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import TypeVar

from gsps.model.records import Record
from gsps.store.versioned import write_new

R = TypeVar("R", bound=Record)


def read_rows(path: str | Path | None) -> list[dict[str, str]]:
    """All rows as dicts; an absent path reads as no rows."""
    if path is None:
        return []
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return [
            {k: (v or "") for k, v in row.items() if k is not None} for row in csv.DictReader(fh)
        ]


def load_records(
    path: str | Path | None,
    model: type[R],
    *,
    rename: Mapping[str, str] | None = None,
) -> list[R]:
    """Load rows into ``model``. ``rename`` maps a library's column names onto field names."""
    ren = dict(rename or {})
    out: list[R] = []
    for row in read_rows(path):
        out.append(model(**{ren.get(k, k): v for k, v in row.items()}))
    return out


def to_csv_text(rows: Iterable[Mapping[str, object]], fieldnames: Sequence[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=list(fieldnames), extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in fieldnames})
    return buf.getvalue()


def write_rows(
    path: str | Path, rows: Iterable[Mapping[str, object]], fieldnames: Sequence[str]
) -> Path:
    """Write a new CSV. Refuses to overwrite (regenerate clean; never edit in place)."""
    return write_new(path, to_csv_text(rows, fieldnames))
