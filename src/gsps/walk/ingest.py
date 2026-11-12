"""Ingest walked values into the library.

A walk produces, for each value: the owner's URL, the gate that cleared it, two independent
extractions of the value and the verbatim sentence it came from. :func:`apply_walks` decides
what each walk does to the library (a pure function); :func:`ingest` writes the result as a
new dated anchors version plus a walk log, and never overwrites anything.

Outcomes per walk:

* ``refused``: a lead, mismatched extractions, an uncleared gate (a wall needs a human walk),
  a new anchor missing required fields or whose ID prefix does not match its lane, or a
  duplicate in the same batch. Refusals are logged, never dropped.
* ``added``: a new anchor at ``v1``.
* ``rewalked``: same value, same period. Only ``record_version`` bumps: bookkeeping never
  ripples.
* ``revised``: same period, new value. ``value_version`` bumps, ``prior_value`` is kept and
  ``change_type`` is ``revision``.
* ``new_release``: a new period. ``value_version`` bumps and ``change_type`` is
  ``new_release``.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from gsps.cascade.graph import DependencyGraph, Impact
from gsps.model.records import ANCHOR_COLUMNS, Anchor, Citation, Token
from gsps.rules.grading import ExtractionMismatch, LeadIsNotASource, accept_value, normalize_text
from gsps.store.csv_io import read_rows, write_rows
from gsps.store.versioned import next_version_path
from gsps.vocab.registry import Registry, YieldItem
from gsps.vocab.values import Gate

#: Fields a brand-new anchor must carry.
REQUIRED_FOR_NEW = ("lane", "anchor_type", "metric", "owner", "grade", "authority_tier", "nature")

#: Anchor fields a walk may set or update (others are left as they are).
UPDATABLE = (
    "lane",
    "anchor_type",
    "metric",
    "owner",
    "series_or_table",
    "cadence",
    "last_release",
    "next_release",
    "refresh_basis",
    "next_release_label",
    "nature",
    "grade",
    "ceiling",
    "ceiling_note",
    "authority_tier",
    "public_citation",
)

WALK_LOG_COLUMNS = (
    "anchor_id",
    "outcome",
    "detail",
    "value",
    "as_of",
    "url",
    "gate",
    "human_walk",
    "walked_by",
    "walked_on",
    "verbatim",
)

_VERSION = re.compile(r"^v(\d+)$")


def bump(version: str) -> str:
    """``v3`` -> ``v4``. An unparseable version is treated as ``v1``."""
    m = _VERSION.match(version.strip())
    return f"v{(int(m[1]) if m else 1) + 1}"


class WalkedValue(BaseModel):
    """One value as walked: where it came from and both extractions of it."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    anchor_id: str
    value_1: str
    value_2: str
    verbatim: str
    url: str
    gate: Gate
    walked_on: str
    walked_by: str = "keeper"
    human_walk: bool = False
    is_owner_primary: bool = True
    as_of: str = ""
    # Optional anchor fields (required only for a new anchor; see REQUIRED_FOR_NEW).
    lane: str = ""
    anchor_type: str = ""
    metric: str = ""
    owner: str = ""
    series_or_table: str = ""
    cadence: str = ""
    last_release: str = ""
    next_release: str = ""
    refresh_basis: str = ""
    next_release_label: str = ""
    nature: str = ""
    grade: str = ""
    ceiling: str = ""
    ceiling_note: str = ""
    authority_tier: str = ""
    public_citation: str = ""

    @field_validator("human_walk", "is_owner_primary", mode="before")
    @classmethod
    def _bool(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y"}
        return v


class Outcome(StrEnum):
    ADDED = "added"
    REWALKED = "rewalked"
    REVISED = "revised"
    NEW_RELEASE = "new_release"
    REFUSED = "refused"

    @property
    def moves_value(self) -> bool:
        return self in {Outcome.ADDED, Outcome.REVISED, Outcome.NEW_RELEASE}


@dataclass(frozen=True)
class IngestLine:
    walk: WalkedValue
    outcome: Outcome
    detail: str

    @property
    def anchor_id(self) -> str:
        return self.walk.anchor_id


@dataclass
class IngestResult:
    lines: list[IngestLine]
    anchors: list[Anchor]
    yields: list[YieldItem] = field(default_factory=list)
    anchors_path: Path | None = None
    walk_log_path: Path | None = None

    @property
    def refused(self) -> list[IngestLine]:
        return [ln for ln in self.lines if ln.outcome == Outcome.REFUSED]

    @property
    def value_changes(self) -> list[IngestLine]:
        """Lines whose value moved for an anchor that already existed (these ripple)."""
        return [ln for ln in self.lines if ln.outcome in {Outcome.REVISED, Outcome.NEW_RELEASE}]

    def impacts(
        self, citations: Iterable[Citation] = (), tokens: Iterable[Token] = ()
    ) -> list[Impact]:
        graph = DependencyGraph.build(self.anchors, tokens, citations)
        return [graph.impact(ln.anchor_id) for ln in self.value_changes]


def _gate_problem(w: WalkedValue) -> str:
    if w.gate.cleared:
        return ""
    if w.gate == Gate.WALL and w.human_walk:
        return ""
    if w.gate == Gate.WALL:
        return "gate 'wall' needs a human walk (human_walk=true); never route around it"
    return f"gate '{w.gate.value}' did not clear the page; walk again with a corrected URL"


def _fields(w: WalkedValue) -> dict[str, str]:
    return {f: getattr(w, f) for f in UPDATABLE if getattr(w, f)}


def apply_walks(
    anchors: Sequence[Anchor],
    walks: Iterable[WalkedValue],
    *,
    on: dt.date,
    registry: Registry | None = None,
) -> IngestResult:
    """Decide what each walk does. Pure: returns the new anchor list, writes nothing."""
    current: dict[str, Anchor] = {a.anchor_id: a for a in anchors}
    order = [a.anchor_id for a in anchors]
    lines: list[IngestLine] = []
    seen: set[str] = set()
    touch = on.isoformat()

    for w in walks:
        if w.anchor_id in seen:
            lines.append(IngestLine(w, Outcome.REFUSED, "duplicate anchor in this batch"))
            continue
        seen.add(w.anchor_id)

        problem = _gate_problem(w)
        if problem:
            lines.append(IngestLine(w, Outcome.REFUSED, problem))
            continue
        try:
            value = accept_value(w.value_1, w.value_2, is_owner_primary=w.is_owner_primary)
        except (LeadIsNotASource, ExtractionMismatch) as exc:
            lines.append(IngestLine(w, Outcome.REFUSED, str(exc)))
            continue

        old = current.get(w.anchor_id)
        if old is None:
            missing = [f for f in REQUIRED_FOR_NEW if not getattr(w, f)]
            if missing:
                lines.append(
                    IngestLine(w, Outcome.REFUSED, "new anchor missing: " + ", ".join(missing))
                )
                continue
            if w.anchor_id.split("-", 1)[0] != w.lane:
                lines.append(
                    IngestLine(w, Outcome.REFUSED, f"ID prefix does not match lane '{w.lane}'")
                )
                continue
            current[w.anchor_id] = Anchor(
                anchor_id=w.anchor_id,
                value=value,
                as_of=w.as_of,
                url=w.url,
                last_walked=w.walked_on,
                last_touch=touch,
                ceiling=w.ceiling or "none",
                change_type="new_release",
                **{k: v for k, v in _fields(w).items() if k != "ceiling"},
            )
            order.append(w.anchor_id)
            lines.append(IngestLine(w, Outcome.ADDED, f"{w.anchor_id} v1 = {value}"))
            continue

        same_value = normalize_text(old.value) == value
        same_period = not w.as_of or w.as_of == old.as_of
        update: dict[str, str] = {
            **_fields(w),
            "url": w.url,
            "last_walked": w.walked_on,
            "last_touch": touch,
            "record_version": bump(old.record_version),
        }
        if same_value and same_period:
            outcome, detail = Outcome.REWALKED, f"{w.anchor_id} unchanged at {old.value_version}"
        else:
            outcome = Outcome.REVISED if same_period else Outcome.NEW_RELEASE
            new_vv = bump(old.value_version)
            update |= {
                "value": value,
                "as_of": w.as_of or old.as_of,
                "value_version": new_vv,
                "prior_value": old.value,
                "change_type": "revision" if same_period else "new_release",
            }
            detail = f"{w.anchor_id} {old.value_version}->{new_vv}: {old.value} -> {value}"
        current[w.anchor_id] = old.model_copy(update=update)
        lines.append(IngestLine(w, outcome, detail))

    result = IngestResult(lines=lines, anchors=[current[i] for i in order])
    if registry is not None:
        touched = {ln.anchor_id for ln in lines if ln.outcome != Outcome.REFUSED}
        for a in result.anchors:
            if a.anchor_id in touched:
                result.yields.extend(registry.check_record(a.anchor_id, a.model_dump()))
    return result


def load_walks(path: str | Path) -> list[WalkedValue]:
    return [WalkedValue.model_validate(row) for row in read_rows(path)]


def ingest(
    library_root: str | Path,
    walks: Iterable[WalkedValue],
    anchors: Sequence[Anchor],
    *,
    on: dt.date | None = None,
    registry: Registry | None = None,
) -> IngestResult:
    """Apply walks and write a new anchors version and a walk log. Nothing is overwritten."""
    day = on or dt.date.today()
    root = Path(library_root)
    result = apply_walks(anchors, walks, on=day, registry=registry)

    if any(ln.outcome != Outcome.REFUSED for ln in result.lines):
        extras = sorted({k for a in result.anchors for k in (a.model_extra or {})})
        cols = [*ANCHOR_COLUMNS, *[e for e in extras if e not in ANCHOR_COLUMNS]]
        result.anchors_path = write_rows(
            next_version_path(root, "ANCHORS", "csv", day),
            (a.as_row() for a in result.anchors),
            cols,
        )

    log_dir = root / "WALKS"
    log_dir.mkdir(parents=True, exist_ok=True)
    result.walk_log_path = write_rows(
        next_version_path(log_dir, "WALK_LOG", "csv", day),
        (
            {
                "anchor_id": ln.anchor_id,
                "outcome": ln.outcome.value,
                "detail": ln.detail,
                "value": ln.walk.value_1,
                "as_of": ln.walk.as_of,
                "url": ln.walk.url,
                "gate": ln.walk.gate.value,
                "human_walk": str(ln.walk.human_walk).lower(),
                "walked_by": ln.walk.walked_by,
                "walked_on": ln.walk.walked_on,
                "verbatim": ln.walk.verbatim,
            }
            for ln in result.lines
        ),
        WALK_LOG_COLUMNS,
    )
    return result
