"""The walk brief: what the requester needs grounded, expressed as requirements.

A brief is YAML::

    id: BRIEF-2026-11-07
    requester: requester
    date: 2026-11-07
    supersedes: [BRIEF-2026-11-05]
    blind: true            # prior hand-offs' named claims are not leads
    inputs:
      - path: page.md
        role: page          # page | superset | context | walklist
    questions:
      - id: Q1
        text: Overall employment environment now (direction, momentum).
    scope:
      in:   [page claims, qualitative questions]
      held: [unit economics]
    output: [track1_log, track2_register, qualitative_findings]
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

InputRole = Literal["page", "superset", "context", "walklist"]


class BriefInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    role: InputRole = "context"


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    text: str


class Scope(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    in_: list[str] = Field(default_factory=list, alias="in")
    held: list[str] = Field(default_factory=list)


class WalkBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    requester: str = "requester"
    date: dt.date
    supersedes: list[str] = Field(default_factory=list)
    blind: bool = True
    inputs: list[BriefInput] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    scope: Scope = Field(default_factory=Scope)
    output: list[str] = Field(
        default_factory=lambda: ["track1_log", "track2_register", "qualitative_findings"]
    )

    @property
    def page_inputs(self) -> list[BriefInput]:
        return [i for i in self.inputs if i.role == "page"]

    def question(self, qid: str) -> Question:
        for q in self.questions:
            if q.id == qid:
                return q
        raise KeyError(qid)

    def is_held(self, topic: str) -> bool:
        return topic in self.scope.held


def load_brief(path: str | Path) -> WalkBrief:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return WalkBrief.model_validate(data)
