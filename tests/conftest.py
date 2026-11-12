from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from gsps.library import Library
from gsps.model.records import Anchor

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLE = ROOT / "examples" / "onepager_walk"


@pytest.fixture
def library() -> Library:
    return Library.load(FIXTURES / "library")


@pytest.fixture
def as_of() -> dt.date:
    return dt.date(2026, 11, 15)


def make_anchor(**kw: str) -> Anchor:
    """An anchor with sensible defaults; override any field."""
    base = {
        "anchor_id": "LAB-001",
        "lane": "LAB",
        "anchor_type": "metric",
        "value": "100",
        "grade": "Confirmed",
        "authority_tier": "government",
        "nature": "external-primary",
        "ceiling": "none",
    }
    base.update(kw)
    return Anchor(**base)
