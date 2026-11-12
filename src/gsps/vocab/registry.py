"""The vocabulary registry and the yield log.

Rule: values are walked, same as claims. A value that is not registered for its column
is never silently accepted and never silently rejected. It is recorded as a *yield*: an
item a person must rule on (register it, or reject it). Assigning an already-registered
value is routine and does not yield.

A registry can be built from the default enums, or parsed from a markdown table with the
columns ``| Column | Value | Meaning | Origin |`` where one row may list several values
separated by `` / `` (the format used by a ``STATE_FLAGS.md`` file).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from gsps.vocab import values as v

#: Columns governed by the default registry, mapped to their enum.
DEFAULT_COLUMNS: Mapping[str, type[StrEnum]] = {
    "grade": v.Grade,
    "ceiling": v.Ceiling,
    "authority_tier": v.AuthorityTier,
    "anchor_type": v.AnchorType,
    "nature": v.Nature,
    "refresh_basis": v.RefreshBasis,
    "lifecycle_state": v.Lifecycle,
    "stance": v.Stance,
    "gate": v.Gate,
}


@dataclass(frozen=True)
class YieldItem:
    """One decision the engine refuses to make on its own."""

    kind: str  # "unregistered" | "blank" | other rule names
    column: str
    value: str
    record_id: str
    note: str = ""

    def __str__(self) -> str:
        shown = self.value or "(blank)"
        return f"[{self.kind}] {self.record_id}: {self.column}={shown} {self.note}".rstrip()


@dataclass
class YieldLog:
    """Collects yields. The engine yields and keeps going; it does not halt."""

    items: list[YieldItem] = field(default_factory=list)

    def add(self, item: YieldItem) -> None:
        self.items.append(item)

    def extend(self, items: Iterable[YieldItem]) -> None:
        self.items.extend(items)

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)

    def by_kind(self, kind: str) -> list[YieldItem]:
        return [i for i in self.items if i.kind == kind]


class Registry:
    """Registered values per column."""

    def __init__(self, columns: Mapping[str, Iterable[str]]) -> None:
        self._values: dict[str, set[str]] = {c: set(vals) for c, vals in columns.items()}

    @classmethod
    def default(cls) -> Registry:
        return cls({col: [m.value for m in enum] for col, enum in DEFAULT_COLUMNS.items()})

    @classmethod
    def from_markdown(cls, path: str | Path, columns: Iterable[str] | None = None) -> Registry:
        """Parse a ``| Column | Value | Meaning | Origin |`` table.

        Only the columns named in ``columns`` are read (all columns when ``None``).
        Header and separator rows are skipped.
        """
        wanted = set(columns) if columns is not None else None
        found: dict[str, set[str]] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or cells[0] in {"Column", ""} or set(cells[0]) <= {"-", ":"}:
                continue
            col = cells[0]
            if wanted is not None and col not in wanted:
                continue
            for val in cells[1].split(" / "):
                val = val.strip()
                if val:
                    found.setdefault(col, set()).add(val)
        return cls(found)

    def columns(self) -> set[str]:
        return set(self._values)

    def values(self, column: str) -> set[str]:
        return set(self._values.get(column, set()))

    def is_registered(self, column: str, value: str) -> bool:
        return value in self._values.get(column, set())

    def check(
        self, record_id: str, column: str, value: str | None, *, blank_yields: bool = True
    ) -> YieldItem | None:
        """Return a yield if ``value`` is unregistered (or blank), else ``None``."""
        if column not in self._values:
            return None
        if not value:
            if blank_yields:
                return YieldItem(
                    "blank", column, "", record_id, "pending ruling, listed not passed"
                )
            return None
        if not self.is_registered(column, value):
            return YieldItem("unregistered", column, value, record_id, "YIELD: register or reject")
        return None

    def check_record(
        self, record_id: str, record: Mapping[str, object], columns: Iterable[str] | None = None
    ) -> list[YieldItem]:
        cols = list(columns) if columns is not None else sorted(self._values)
        out: list[YieldItem] = []
        for col in cols:
            if col not in record:
                continue
            raw = record[col]
            item = self.check(record_id, col, "" if raw is None else str(raw))
            if item:
                out.append(item)
        return out
