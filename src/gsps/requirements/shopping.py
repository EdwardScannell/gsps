"""Shopping Request in, Shopping Report out.

A requester marks the values a document needs as tokens and hands over a Shopping
Request. The keeper returns a Shopping Report: one record per token, so nothing ships
bare. Loop-closure rules enforced by :func:`validate_report`:

1. No token ships bare: every requested token has a record with class, confidence and a
   source (for sourced/reported) or a derivation route (for estimates).
2. Request in, report out: the report answers exactly the request (no missing tokens, no
   strays).
3. Edit-time dirty detection: a value or a dependency that changed after fill marks the
   token dirty, and dirty blocks release.
4. Estimate discipline: every estimate carries its route and a low / mid / high band, and
   the shipped value is the mid.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FillClass(StrEnum):
    SOURCED = "sourced"  # walked to primary
    REPORTED = "reported"  # a secondary figure
    ESTIMATE = "estimate"  # derived by the keeper


class ShoppingToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_id: str
    ask: str
    as_of_needed: str = ""


class ShoppingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    document: str
    tokens: list[ShoppingToken]


class Band(BaseModel):
    model_config = ConfigDict(frozen=True)

    low: str
    mid: str
    high: str


class TokenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    token_id: str
    value: str
    fill_class: FillClass = Field(alias="class")
    confidence: str  # H / M / L
    source_or_route: str
    reason: str
    range: Band | None = None
    as_of: str = ""
    depends_on: tuple[str, ...] = ()
    dirty: bool = False
    dirty_reason: str = ""


class ShoppingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    records: list[TokenRecord]

    def record(self, token_id: str) -> TokenRecord | None:
        return next((r for r in self.records if r.token_id == token_id), None)


def validate_report(request: ShoppingRequest, report: ShoppingReport) -> list[str]:
    """Every reason the report cannot release. Empty means it can."""
    problems: list[str] = []
    if report.request_id != request.request_id:
        problems.append(f"report answers {report.request_id}, not {request.request_id}")
    asked = {t.token_id for t in request.tokens}
    answered = [r.token_id for r in report.records]
    for tid in sorted(asked - set(answered)):
        problems.append(f"{tid}: ships bare (no record)")
    for tid in sorted(set(answered) - asked):
        problems.append(f"{tid}: stray record (not requested)")
    for tid in sorted({t for t in answered if answered.count(t) > 1}):
        problems.append(f"{tid}: answered more than once")
    for r in report.records:
        if r.confidence not in {"H", "M", "L"}:
            problems.append(f"{r.token_id}: confidence must be H, M or L")
        if not r.source_or_route.strip():
            what = "route" if r.fill_class == FillClass.ESTIMATE else "source"
            problems.append(f"{r.token_id}: missing {what}")
        if not r.reason.strip():
            problems.append(f"{r.token_id}: missing reason")
        if r.fill_class == FillClass.ESTIMATE:
            if r.range is None:
                problems.append(f"{r.token_id}: estimate without a low/mid/high band")
            elif r.value != r.range.mid:
                problems.append(
                    f"{r.token_id}: estimate must ship the mid ({r.range.mid}), not {r.value}"
                )
        if r.dirty:
            problems.append(
                f"{r.token_id}: dirty ({r.dirty_reason or 'no reason given'}); "
                "re-walk before release"
            )
    return problems


def mark_dirty(report: ShoppingReport, changed_inputs: set[str]) -> ShoppingReport:
    """Return a copy with every record that depends on a changed input marked dirty."""
    out: list[TokenRecord] = []
    for r in report.records:
        hit = sorted(changed_inputs & set(r.depends_on))
        if hit and not r.dirty:
            r = r.model_copy(
                update={"dirty": True, "dirty_reason": "input changed: " + ", ".join(hit)}
            )
        out.append(r)
    return report.model_copy(update={"records": out})
