"""Library record types.

Records are deliberately permissive: every controlled column is a plain string, so a
record carrying an unregistered value still loads. Validation against the vocabulary is
a separate step (:class:`gsps.vocab.Registry`) that yields instead of rejecting.
Unknown extra columns are preserved, so a round trip never drops data.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

#: Anchor columns in canonical order (the 28-column library format).
ANCHOR_COLUMNS: tuple[str, ...] = (
    "anchor_id",
    "value_version",
    "record_version",
    "lane",
    "anchor_type",
    "metric",
    "value",
    "as_of",
    "owner",
    "url",
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
    "last_walked",
    "last_touch",
    "lifecycle_state",
    "change_type",
    "prior_value",
    "notes",
)

_ID_RANGE = re.compile(r"([A-Z]{3})-(\d{3})(?:\.\.(\d{3}))?")


def parse_date(text: str | None) -> dt.date | None:
    """ISO date or ``None``. Never raises: an unparseable date is treated as absent."""
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text.strip())
    except ValueError:
        return None


def expand_ids(text: str) -> list[str]:
    """Anchor IDs mentioned in free text, expanding ranges like ``PRC-001..004``."""
    out: list[str] = []
    for lane, start, end in _ID_RANGE.findall(text or ""):
        if end:
            out.extend(f"{lane}-{i:03d}" for i in range(int(start), int(end) + 1))
        else:
            out.append(f"{lane}-{start}")
    return out


class Record(BaseModel):
    """Base: string fields, extra columns kept, immutable once built."""

    model_config = ConfigDict(extra="allow", frozen=True, str_strip_whitespace=True)

    key_field: ClassVar[str] = ""

    @property
    def key(self) -> str:
        return str(getattr(self, self.key_field, ""))

    def as_row(self) -> dict[str, str]:
        return {k: "" if v is None else str(v) for k, v in self.model_dump().items()}


class Anchor(Record):
    """One walked value (or a logged attempt) in the library."""

    key_field: ClassVar[str] = "anchor_id"

    anchor_id: str
    value_version: str = "v1"
    record_version: str = "v1"
    lane: str = ""
    anchor_type: str = ""
    metric: str = ""
    value: str = ""
    as_of: str = ""
    owner: str = ""
    url: str = ""
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
    last_walked: str = ""
    last_touch: str = ""
    lifecycle_state: str = "active"
    change_type: str = ""
    prior_value: str = ""
    notes: str = ""

    @property
    def id_lane(self) -> str:
        return self.anchor_id.split("-", 1)[0]

    @property
    def input_ids(self) -> list[str]:
        """IDs this anchor is computed from (estimates cite their inputs by ID)."""
        return [i for i in expand_ids(self.series_or_table) if i != self.anchor_id]


class Finding(Record):
    """An authority's conclusion, keyed by the anchor that holds it."""

    key_field: ClassVar[str] = "anchor_id"

    anchor_id: str
    institution: str = ""
    claim: str = ""
    verbatim: str = ""
    question: str = ""
    stance: str = ""
    stance_on: str = ""
    counterweight: str = ""
    counterweight_status: str = ""


class Tension(Record):
    key_field: ClassVar[str] = "flag_id"

    flag_id: str
    token: str = ""
    anchors: str = ""
    flag_type: str = ""
    status: str = ""
    phrasing_rule: str = ""


class Deliverable(Record):
    key_field: ClassVar[str] = "deliverable_id"

    deliverable_id: str
    name: str = ""
    code: str = ""
    lane: str = ""
    audience: str = ""
    current_version: str = ""
    status_stage: str = ""
    shipped_date: str = ""
    shipped_to: str = ""


class Citation(Record):
    """Deliverable version x anchor value version x location. Rows are immutable."""

    key_field: ClassVar[str] = "anchor_id"

    deliverable_id: str
    deliverable_version: str
    anchor_id: str
    anchor_value_version: str = ""
    location: str = ""
    token: str = ""
    value_shown: str = ""


class Token(Record):
    """One stable ID per value or checked claim on a deliverable."""

    key_field: ClassVar[str] = "token_id"

    token_id: str
    section: str = ""
    value: str = ""
    depends_on: str = ""  # "LAB-011@v2; ASM-003"
    class_override: str = ""
    check: str = "text"  # "text" | "visual"
    expected_text: str = ""
    locator: str = ""  # regex that finds the token on the page
    route: str = ""  # derivation route, for estimates
    reason: str = ""
    range: str = ""
    as_of_override: str = ""
    visual_status: str = ""
    status: str = "active"
    note: str = ""

    def references(self) -> list[tuple[str, str]]:
        """``(anchor_id, cited_value_version)`` pairs; version is ``""`` when not pinned."""
        out: list[tuple[str, str]] = []
        for part in self.depends_on.split(";"):
            part = part.strip()
            if re.match(r"^[A-Z]{3}-\d{3}", part):
                aid, _, vv = part.partition("@")
                out.append((aid.strip(), vv.strip()))
        return out


class Intake(Record):
    key_field: ClassVar[str] = "intake_id"

    intake_id: str
    received_utc: str = ""
    sender: str = ""
    via: str = ""
    sha256: str = ""
    assigned_version: str = ""
    stored_as: str = ""
    archived_to: str = ""
    status: str = ""
    run_id: str = ""


class SourceCandidate(Record):
    """A source someone offered. Each gets a decision with a reason."""

    key_field: ClassVar[str] = "candidate_id"

    candidate_id: str
    name: str = ""
    url: str = ""
    offered_by: str = ""
    potential_band: str = ""
    access: str = ""
    decision: str = ""
    reason: str = ""
    becomes: str = ""
    run_id: str = ""
