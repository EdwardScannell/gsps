"""Integrity checks run on every view build. Each returns the offending IDs; empty means OK."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from gsps.model.records import Anchor, Citation, Deliverable, Finding
from gsps.vocab.registry import Registry
from gsps.vocab.values import AnchorType

#: Columns that must be computed by the engine and therefore must not exist as typed columns.
COMPUTED_COLUMNS = ("refresh_state", "hml", "sync_status", "confidence")


@dataclass(frozen=True)
class IntegrityResult:
    name: str
    offenders: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.offenders


def run_integrity_checks(
    anchors: Sequence[Anchor],
    citations: Sequence[Citation],
    deliverables: Sequence[Deliverable],
    findings: Mapping[str, Finding],
    registry: Registry | None = None,
    registry_columns: Sequence[str] = (
        "anchor_type",
        "authority_tier",
        "grade",
        "nature",
        "ceiling",
        "refresh_basis",
    ),
) -> list[IntegrityResult]:
    by_id = {a.anchor_id: a for a in anchors}
    ids = [a.anchor_id for a in anchors]
    extra_cols = set().union(*(set(a.model_extra or {}) for a in anchors)) if anchors else set()

    checks: list[tuple[str, list[str]]] = [
        ("duplicate anchor IDs", [i for i, c in Counter(ids).items() if c > 1]),
        ("ID prefix != lane", [a.anchor_id for a in anchors if a.id_lane != a.lane]),
        (
            "citation -> missing anchor",
            [c.anchor_id for c in citations if c.anchor_id not in by_id],
        ),
        (
            "citation -> missing deliverable",
            sorted(
                {c.deliverable_id for c in citations} - {d.deliverable_id for d in deliverables}
            ),
        ),
        (
            "finding without a FINDINGS row",
            [
                a.anchor_id
                for a in anchors
                if a.anchor_type == AnchorType.FINDING and a.anchor_id not in findings
            ],
        ),
        ("typed columns that must be computed", [c for c in COMPUTED_COLUMNS if c in extra_cols]),
        (
            "value_version v1 with a change_type other than new_release",
            [
                a.anchor_id
                for a in anchors
                if a.value_version == "v1" and a.change_type not in {"new_release", ""}
            ],
        ),
        (
            "next_release on/before last_release",
            [
                a.anchor_id
                for a in anchors
                if a.next_release and a.last_release and a.next_release <= a.last_release
            ],
        ),
        (
            "estimate input missing from library",
            [
                f"{a.anchor_id}->{i}"
                for a in anchors
                if a.anchor_type == AnchorType.ESTIMATE
                for i in a.input_ids
                if i not in by_id
            ],
        ),
        (
            "projected value cited as observed",
            [
                a.anchor_id
                for a in anchors
                if str((a.model_extra or {}).get("value_basis", "")) == "projected"
                and a.anchor_type == AnchorType.METRIC
                and "projected" not in a.metric.lower()
            ],
        ),
    ]

    if registry is not None:
        governed = registry.columns()
        for col in registry_columns:
            if col not in governed:
                continue  # this registry does not govern the column; nothing to check against
            unreg, blank = [], []
            for a in anchors:
                val = getattr(a, col, "")
                if not val:
                    blank.append(a.anchor_id)
                elif not registry.is_registered(col, val):
                    unreg.append(f"{a.anchor_id}={val}")
            checks.append((f"{col}: unregistered value (YIELD)", unreg))
            checks.append((f"{col}: blank (pending ruling, listed not passed)", blank))

    return [IntegrityResult(name, tuple(bad)) for name, bad in checks]
