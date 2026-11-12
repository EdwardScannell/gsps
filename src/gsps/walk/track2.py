"""Track 2: the assumption register.

Estimates, models and narrative are registered, never sourced:
``{claim, basis, estimate-not-fact label, status, drift risk}``. The register makes the
honest floor explicit, so a page never presents an estimate as a fact.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from gsps.store.csv_io import read_rows


class RegisterStatus(StrEnum):
    KEEP = "keep"  # ships as written, labeled
    SOFTEN = "soften"  # ships only with the proposed rewording
    CUT = "cut"  # must not ship
    PENDING = "pending"  # waits on the ratifier
    RULED = "ruled"  # the ratifier ruled; see ruling


class DriftRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssumptionEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    basis: str
    label: str  # how it must be presented: "estimate", "framing", "illustrative", ...
    status: RegisterStatus
    drift_risk: DriftRisk = DriftRisk.LOW
    proposed_wording: str = ""
    ruling: str = ""
    note: str = ""


def load_track2(path: str | Path) -> list[AssumptionEntry]:
    return [AssumptionEntry.model_validate(row) for row in read_rows(path)]
