"""The ship gate: can this page go out?

A page ships only when every claim on it is accounted for:

* T1 / T1-INT: verdict CONFIRMED or ATTESTED, with a consistent Track-1 entry.
  WRONG blocks (cut or rewrite). UNVERIFIABLE blocks (soften or cut).
* T2: a register entry whose status is keep, soften (with wording) or ruled. Pending and
  cut block. A legal claim needs the ratifier's ruling whatever its status.
* Estimates must carry their label in the page text when the page text is supplied.
* Any claim marked contested blocks until the ratifier rules.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from gsps.requirements.business_case import RATIFIER_KINDS, Claim, ClaimKind, Track
from gsps.vocab.values import Verdict
from gsps.walk.track1 import Track1Entry, entry_problems
from gsps.walk.track2 import AssumptionEntry, RegisterStatus


@dataclass(frozen=True)
class ShipLine:
    claim_id: str
    ok: bool
    reason: str


@dataclass
class ShipReport:
    lines: list[ShipLine] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(line.ok for line in self.lines)

    @property
    def blockers(self) -> list[ShipLine]:
        return [line for line in self.lines if not line.ok]

    def render(self) -> str:
        head = (
            "SHIP: PASS"
            if self.ok
            else f"SHIP: BLOCKED ({len(self.blockers)} of {len(self.lines)})"
        )
        rows = ["| Claim | Result | Reason |", "|---|---|---|"]
        for line in sorted(self.lines, key=lambda x: (x.ok, x.claim_id)):
            rows.append(f"| {line.claim_id} | {'ok' if line.ok else 'BLOCK'} | {line.reason} |")
        return head + "\n\n" + "\n".join(rows)


def ship_check(
    claims: Iterable[Claim],
    track1: Iterable[Track1Entry],
    track2: Iterable[AssumptionEntry],
    *,
    contested: Iterable[str] = (),
    page_text: str | None = None,
) -> ShipReport:
    t1 = {e.claim_id: e for e in track1}
    t2 = {e.claim_id: e for e in track2}
    hot = set(contested)
    report = ShipReport()

    for c in claims:
        if not c.on_page:
            continue
        if c.claim_id in hot:
            report.lines.append(ShipLine(c.claim_id, False, "contested: waits on a ruling"))
            continue
        if c.track in {Track.T1, Track.T1_INTERNAL}:
            report.lines.append(_ship_t1(c, t1.get(c.claim_id)))
        else:
            report.lines.append(_ship_t2(c, t2.get(c.claim_id), page_text))
    return report


def _ship_t1(c: Claim, e: Track1Entry | None) -> ShipLine:
    if e is None:
        return ShipLine(c.claim_id, False, "not walked")
    problems = entry_problems(c, e)
    if problems:
        return ShipLine(c.claim_id, False, "; ".join(problems))
    if e.verdict == Verdict.WRONG:
        return ShipLine(c.claim_id, False, "WRONG: cut or rewrite")
    if e.verdict == Verdict.UNVERIFIABLE:
        return ShipLine(c.claim_id, False, "UNVERIFIABLE: soften or cut")
    return ShipLine(c.claim_id, True, e.verdict.value)


def _ship_t2(c: Claim, e: AssumptionEntry | None, page_text: str | None) -> ShipLine:
    if e is None:
        return ShipLine(c.claim_id, False, "not registered")
    try:
        status = RegisterStatus(e.status)  # coerce: copies made with model_copy skip validation
    except ValueError:
        return ShipLine(c.claim_id, False, f"unknown register status '{e.status}'")
    if c.kind in RATIFIER_KINDS and status != RegisterStatus.RULED:
        return ShipLine(c.claim_id, False, f"{c.kind} claim needs the ratifier's ruling")
    if status == RegisterStatus.PENDING:
        return ShipLine(c.claim_id, False, "pending the ratifier")
    if status == RegisterStatus.CUT:
        return ShipLine(c.claim_id, False, "registered as cut but still on the page")
    if status == RegisterStatus.SOFTEN and not e.proposed_wording.strip():
        return ShipLine(c.claim_id, False, "soften without proposed wording")
    if (
        c.kind == ClaimKind.ESTIMATE
        and page_text is not None
        and e.label.lower() not in page_text.lower()
    ):
        return ShipLine(c.claim_id, False, f"estimate not labeled '{e.label}' on the page")
    return ShipLine(c.claim_id, True, f"registered: {status.value} ({e.label})")
