import pytest

from gsps.rules.estimates import input_ids, parse_number, recompute


@pytest.mark.parametrize(
    ("text", "value"),
    [("1,016", 1016), ("$2.34B", 2.34e9), ("4.1%", 0.041), ("-10,000", -10000), ("$300K", 3e5)],
)
def test_parse_number(text: str, value: float) -> None:
    assert parse_number(text) == pytest.approx(value)


def test_reproduces() -> None:
    check = recompute("SAM-001 * PRC-001 * 12", {"SAM-001": "5,000,000", "PRC-001": "39"}, "$2.34B")
    assert check.ok
    assert "reproduces" in check.explain()


def test_does_not_reproduce_reports_ratio() -> None:
    check = recompute("SAM-001 * PRC-001 * 12", {"SAM-001": 5e6, "PRC-001": 39}, "$234M")
    assert not check.ok
    assert check.ratio == pytest.approx(0.1)


def test_missing_input_is_an_error() -> None:
    with pytest.raises(KeyError):
        recompute("SAM-001 * PRC-001", {"SAM-001": 1}, 1)


@pytest.mark.parametrize("method", ["__import__('os')", "SAM-001.real", "abs(SAM-001)"])
def test_only_arithmetic_is_evaluated(method: str) -> None:
    with pytest.raises((ValueError, KeyError, SyntaxError)):
        recompute(method, {"SAM-001": 1}, 1)


def test_inputs_must_be_anchor_ids() -> None:
    with pytest.raises(ValueError, match="anchor IDs"):
        recompute("A - B", {"A": 3, "B": 2}, 1)


def test_input_ids() -> None:
    assert input_ids("(ASM-001 + ASM-002) * PRC-003") == ["ASM-001", "ASM-002", "PRC-003"]
