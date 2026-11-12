from pathlib import Path

from gsps.vocab.registry import Registry, YieldLog
from tests.conftest import FIXTURES


def test_default_registry_knows_the_ladder() -> None:
    reg = Registry.default()
    assert reg.is_registered("grade", "Grounded")
    assert reg.is_registered("gate", "chained")
    assert not reg.is_registered("grade", "Probable")


def test_unregistered_value_yields_and_does_not_raise() -> None:
    item = Registry.default().check("X-001", "nature", "derived")
    assert item is not None
    assert item.kind == "unregistered"
    assert "YIELD" in str(item)


def test_blank_is_listed_not_passed() -> None:
    item = Registry.default().check("X-001", "grade", "")
    assert item is not None
    assert item.kind == "blank"


def test_registered_value_is_routine() -> None:
    assert Registry.default().check("X-001", "grade", "Confirmed") is None


def test_ungoverned_column_is_ignored() -> None:
    assert Registry.default().check("X-001", "metric", "anything") is None


def test_markdown_registry_splits_multi_values() -> None:
    reg = Registry.from_markdown(FIXTURES / "library" / "STATE_FLAGS.md")
    assert {"Confirmed", "Sourced", "Grounded"} <= reg.values("grade")
    assert reg.is_registered("anchor_type", "definition")
    assert not reg.is_registered("nature", "derived")


def test_markdown_registry_column_filter(tmp_path: Path) -> None:
    p = tmp_path / "flags.md"
    p.write_text(
        "| Column | Value | Meaning | Origin |\n|---|---|---|---|\n"
        "| grade | A / B | x | y |\n| tier | t | x | y |\n"
    )
    reg = Registry.from_markdown(p, columns=["grade"])
    assert reg.columns() == {"grade"}


def test_yield_log_collects() -> None:
    log = YieldLog()
    reg = Registry.default()
    log.extend(
        reg.check_record("X-001", {"grade": "Probable", "nature": "derived", "ceiling": "none"})
    )
    assert len(log) == 2
    assert log.by_kind("unregistered")
