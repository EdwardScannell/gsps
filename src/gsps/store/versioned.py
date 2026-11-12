"""Dated, immutable versions.

Naming: ``<STEM>_<YYYYMMDD>.<ext>`` is version 1 of that day; ``<STEM>_<YYYYMMDD>_v<N>.<ext>``
is version N. Rules enforced here:

* The next version is the highest version *ever used* that day plus one. Gaps are never
  filled, and files already marked ``TO_DELETE_`` still count as used.
* A new version is written with exclusive create: an existing file is never overwritten.
* Nothing is deleted. A file proposed for removal is renamed with a ``TO_DELETE_`` prefix
  and a person deletes it.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

TO_DELETE_PREFIX = "TO_DELETE_"
_PATTERN = re.compile(
    r"^(?:TO_DELETE_)?(?P<stem>.+?)_(?P<date>\d{8})(?:_v(?P<ver>\d+))?\.(?P<ext>\w+)$"
)


@dataclass(frozen=True, order=True)
class VersionedName:
    date: str
    version: int
    stem: str
    ext: str
    marked_for_delete: bool = False

    def filename(self) -> str:
        suffix = "" if self.version == 1 else f"_v{self.version}"
        return f"{self.stem}_{self.date}{suffix}.{self.ext}"


def parse_versioned(name: str) -> VersionedName | None:
    m = _PATTERN.match(Path(name).name)
    if not m:
        return None
    return VersionedName(
        date=m["date"],
        version=int(m["ver"] or 1),
        stem=m["stem"],
        ext=m["ext"],
        marked_for_delete=Path(name).name.startswith(TO_DELETE_PREFIX),
    )


def latest(directory: str | Path, stem: str, ext: str = "csv") -> Path | None:
    """The current file for ``stem``: newest date, then highest version. Ignores TO_DELETE_."""
    best: tuple[VersionedName, Path] | None = None
    for p in Path(directory).glob(f"{stem}_*.{ext}"):
        vn = parse_versioned(p.name)
        if vn is None or vn.stem != stem or vn.marked_for_delete:
            continue
        if best is None or (vn.date, vn.version) > (best[0].date, best[0].version):
            best = (vn, p)
    return best[1] if best else None


def next_version_path(
    directory: str | Path, stem: str, ext: str, on: dt.date | None = None
) -> Path:
    """Path for the next version of ``stem`` on date ``on`` (default: today)."""
    day = (on or dt.date.today()).strftime("%Y%m%d")
    used = [0]
    for p in Path(directory).glob(f"*{stem}_{day}*.{ext}"):
        vn = parse_versioned(p.name)
        if vn and vn.stem == stem and vn.date == day:
            used.append(vn.version)
    return Path(directory) / VersionedName(day, max(used) + 1, stem, ext).filename()


def write_new(path: str | Path, text: str) -> Path:
    """Write ``text`` to a file that must not exist yet. Raises ``FileExistsError`` otherwise."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return p


def mark_to_delete(path: str | Path) -> Path:
    """Rename ``path`` with the TO_DELETE_ prefix. The engine never deletes."""
    p = Path(path)
    if p.name.startswith(TO_DELETE_PREFIX):
        return p
    target = p.with_name(TO_DELETE_PREFIX + p.name)
    if target.exists():
        raise FileExistsError(target)
    p.rename(target)
    return target
