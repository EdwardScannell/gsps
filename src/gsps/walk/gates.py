"""Web gates and the follow-up list.

Every URL in a walk carries a gate. A failed fetch names its gate type and ends with a
paste-ready block, so the ratifier can clear the gate in one step. A blocked page is
never routed around (no scraping workaround, no mirror, no browser for a refused page):
it becomes a follow-up item for a human walk.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from gsps.vocab.values import Gate


class FailedFetch(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str
    gate: Gate
    detail: str = ""
    corrected_url: str = ""

    @property
    def needs_paste(self) -> bool:
        """A gate the ratifier can clear by pasting the (corrected) URL."""
        return self.gate in {Gate.NOT_FOUND, Gate.SIZE} or not self.gate.cleared

    @property
    def needs_human_walk(self) -> bool:
        return self.gate == Gate.WALL


class FollowupItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    url: str
    gate: Gate
    check_for_human: str


def paste_block(urls: Iterable[str]) -> str:
    """A fenced block of unique URLs, in order, ready to paste back."""
    seen: list[str] = []
    for u in urls:
        u = u.strip()
        if u and u not in seen:
            seen.append(u)
    return "```\n" + "\n".join(seen) + "\n```" if seen else ""


def paste_block_for(failures: Iterable[FailedFetch]) -> str:
    return paste_block(
        f.corrected_url or f.url for f in failures if f.needs_paste and not f.needs_human_walk
    )


def render_followup(items: Iterable[FollowupItem]) -> str:
    lines = ["| Date | URL | Gate | What a human must check |", "|---|---|---|---|"]
    lines += [f"| {i.date} | {i.url} | {i.gate.value} | {i.check_for_human} |" for i in items]
    return "\n".join(lines)
