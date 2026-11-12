"""The fill report: one row per active token, saying how each value on the page was decided.

Class and confidence are computed, never typed:

* ``class``: the token's override if set; else ``estimate`` when any direct anchor is our
  own (owner is the keeper, or nature is derived-estimate / assumption); else ``primary``
  when every direct anchor is Confirmed/Grounded and external-primary; else ``secondary``;
  ``no-receipt`` when nothing backs it.
* ``grade``: the weakest grade among direct anchors.
* ``confidence``: the weakest H/M/L among direct anchors (attestations are pending).

Dirty is detected from both sides:

* upstream: a pinned anchor's value_version moved, or the anchor is missing;
* edited: the approved wording is no longer on the page;
* visual: an image claim was checked by eye and marked dirty.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from pydantic import BaseModel, ConfigDict

from gsps.cascade.derived import estimates_with_moved_inputs
from gsps.cascade.graph import DependencyGraph
from gsps.deliverable.text import normalize_page
from gsps.model.records import Anchor, Token
from gsps.rules.confidence import weakest_confidence
from gsps.rules.grading import weakest_grade
from gsps.vocab.values import Grade, Nature

_OURS = {Nature.DERIVED_ESTIMATE, Nature.ASSUMPTION}


class FillRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_id: str
    section: str
    value: str
    fill_class: str
    grade: str
    confidence: str
    source_or_route: str
    reason: str
    range: str
    as_of: str
    depends_on: str
    owner: str
    doc_version: str
    doc_text: str
    dirty_flag: str
    dirty_reason: str
    note: str

    @property
    def dirty(self) -> bool:
        return self.dirty_flag == "dirty"


def _classify(token: Token, direct: list[Anchor], keeper: str) -> str:
    if token.class_override:
        return token.class_override
    if any(a.owner == keeper or a.nature in _OURS for a in direct):
        return "estimate"
    if direct and all(
        a.grade in {Grade.CONFIRMED, Grade.GROUNDED} and a.nature == Nature.EXTERNAL_PRIMARY
        for a in direct
    ):
        return "primary"
    return "secondary" if direct else "no-receipt"


def build_fill_report(
    tokens: Iterable[Token],
    anchors: Mapping[str, Anchor],
    page_text: str,
    doc_version: str,
    *,
    keeper: str = "keeper",
    ratifier: str = "ratifier",
) -> list[FillRow]:
    text = normalize_page(page_text)
    stale = estimates_with_moved_inputs(anchors.values())
    rows: list[FillRow] = []
    for t in tokens:
        if t.status == "retired":
            continue
        upstream: list[str] = []
        direct: list[Anchor] = []
        for aid, pinned in t.references():
            a = anchors.get(aid)
            if a is None:
                upstream.append(f"{aid} missing")
                continue
            direct.append(a)
            if pinned and a.value_version != pinned:
                upstream.append(f"{aid} {pinned}->{a.value_version}")
            if aid in stale:
                upstream.append(f"{aid} inputs moved ({', '.join(stale[aid])}); recompute")

        cls = _classify(t, direct, keeper)
        g = weakest_grade(a.grade for a in direct)
        if cls == "attested":
            conf = "PENDING (attestation)"
        elif cls == "no-receipt":
            conf = "NONE (no receipt)"
        else:
            c = weakest_confidence(direct)
            conf = c.value if c else ""

        if cls == "estimate":
            route = t.route
        else:
            route = " | ".join(f"{a.public_citation} <{a.url}> as of {a.as_of}" for a in direct)
            route = route or t.depends_on
        as_of = t.as_of_override or min((a.as_of for a in direct if a.as_of), default="")
        owner = "; ".join(sorted({a.owner for a in direct})) or (
            ratifier if cls == "attested" else "unassigned"
        )

        if t.check == "visual":
            doc_text = "(image; checked by eye)"
            edited = t.visual_status == "dirty"
            edited_reason = "visual: image claim has no receipt or overstates the approved text"
        else:
            m = re.search(t.locator, text) if t.locator else None
            doc_text = m.group(0) if m else "(not found on page)"
            edited = normalize_page(t.expected_text) not in text
            edited_reason = f"edited: expected '{t.expected_text}'"

        reasons = []
        if upstream:
            reasons.append("upstream: " + ", ".join(upstream))
        if edited:
            reasons.append(edited_reason)

        rows.append(
            FillRow(
                token_id=t.token_id,
                section=t.section,
                value=t.value,
                fill_class=cls,
                grade=g.value if g else "",
                confidence=conf,
                source_or_route=route,
                reason=t.reason,
                range=t.range,
                as_of=as_of,
                depends_on=t.depends_on,
                owner=owner,
                doc_version=doc_version,
                doc_text=doc_text,
                dirty_flag="dirty" if reasons else "clean",
                dirty_reason="; ".join(reasons),
                note=t.note,
            )
        )
    return rows


def anchors_used(tokens: Iterable[Token], anchors: Mapping[str, Anchor]) -> list[Anchor]:
    """Every anchor the page rests on, following estimate inputs all the way down."""
    graph = DependencyGraph.build(anchors=anchors.values())
    used: set[str] = set()
    for t in tokens:
        if t.status == "retired":
            continue
        for aid, _ in t.references():
            used.add(aid)
            used |= graph.upstream(aid)
    return [anchors[a] for a in sorted(used) if a in anchors]


def render_fill_report(rows: list[FillRow], title: str) -> str:
    dirty = [r for r in rows if r.dirty]
    attested = sum(r.fill_class == "attested" for r in rows)
    out = [
        f"# FILL REPORT: {title}",
        "",
        f"Tokens: {len(rows)} · clean {len(rows) - len(dirty)} · dirty {len(dirty)} · "
        f"attestations pending {attested}",
        "",
        "## Dirty first",
        "| Token | Value | Class | Conf. | Why dirty |",
        "|---|---|---|---|---|",
    ]
    out += [
        f"| {r.token_id} | {r.value} | {r.fill_class} | {r.confidence} | {r.dirty_reason} |"
        for r in dirty
    ]
    out += [
        "",
        "## All tokens",
        "| Token | Value | Class | Grade | Conf. | Source or route | As of | Dirty |",
        "|---|---|---|---|---|---|---|---|",
    ]
    out += [
        f"| {r.token_id} | {r.value} | {r.fill_class} | {r.grade} | {r.confidence} | "
        f"{r.source_or_route} | {r.as_of} | {r.dirty_flag} |"
        for r in rows
    ]
    return "\n".join(out) + "\n"
