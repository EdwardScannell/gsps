"""Qualitative findings: question -> sources -> supports / contradicts / complicates.

Thin or contrary evidence is a finding, not a failure. :func:`summarize_question` flags:

* ``thin``: fewer than ``min_documentary`` sources at a documentary grade.
* ``contrary``: at least one source contradicts the narrative.
* ``vendor-heavy``: most sources come from parties selling into the market
  (company-research, company-self, commercial-publisher), which must be named on the page.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from gsps.rules.grading import is_documentary
from gsps.vocab.values import AuthorityTier, Stance

_INTERESTED = {
    AuthorityTier.COMPANY_RESEARCH,
    AuthorityTier.COMPANY_SELF,
    AuthorityTier.COMMERCIAL_PUBLISHER,
}


class QualSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    source_id: str
    title: str
    publisher: str
    date: str = ""
    method: str = ""
    verbatim: str = ""
    stance: Stance
    grade: str
    authority_tier: str = ""
    url: str = ""


class QuestionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    sources: int
    stances: dict[str, int]
    documentary: int
    flags: tuple[str, ...]

    @property
    def lean(self) -> str:
        s, c = self.stances.get("supports", 0), self.stances.get("contradicts", 0)
        if s and c:
            return "mixed"
        if c:
            return "contradicts"
        if s:
            return "supports"
        return "complicates" if self.sources else "no evidence"


def summarize_question(
    question_id: str, sources: Iterable[QualSource], *, min_documentary: int = 2
) -> QuestionSummary:
    mine = [s for s in sources if s.question_id == question_id]
    stances = Counter(s.stance.value for s in mine)
    documentary = sum(1 for s in mine if is_documentary(s.grade))
    interested = sum(1 for s in mine if s.authority_tier in _INTERESTED)
    flags: list[str] = []
    if documentary < min_documentary:
        flags.append("thin")
    if stances.get("contradicts"):
        flags.append("contrary")
    if mine and interested * 2 > len(mine):
        flags.append("vendor-heavy")
    return QuestionSummary(
        question_id=question_id,
        sources=len(mine),
        stances=dict(stances),
        documentary=documentary,
        flags=tuple(flags),
    )
