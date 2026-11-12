"""Estimates must be reproducible from their inputs (cited by ID) and their method.

An estimate's method is an arithmetic expression over anchor IDs, for example
``"SAM-001 * PRC-001 * 12"``. :func:`recompute` evaluates it with a restricted AST
evaluator (numbers, IDs, + - * / ** and parentheses only; no names, calls or attributes)
and compares the result with the stated value. A mismatch is reported with the ratio,
which makes a slipped decimal or a missing penetration factor obvious.
"""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

_ID = re.compile(r"\b([A-Z]{3})-(\d{3})\b")
_OPS: dict[type[ast.AST], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}


def parse_number(text: str) -> float:
    """Parse ``"$2.34B"``, ``"1,016"``, ``"4.1%"`` or ``"-10,000"`` into a float."""
    t = text.strip().replace(",", "").replace("$", "")
    scale = 1.0
    if t.endswith("%"):
        t, scale = t[:-1], 0.01
    suffixes = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    if t and t[-1].upper() in suffixes:
        scale *= suffixes[t[-1].upper()]
        t = t[:-1]
    return float(t) * scale


def _eval(node: ast.AST, env: Mapping[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise KeyError(f"input {node.id} not provided")
        return env[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left, env), _eval(node.right, env))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand, env)
    raise ValueError(f"unsupported expression element: {ast.dump(node)}")


@dataclass(frozen=True)
class EstimateCheck:
    method: str
    stated: float
    recomputed: float
    tolerance: float

    @property
    def ratio(self) -> float:
        return self.stated / self.recomputed if self.recomputed else float("inf")

    @property
    def ok(self) -> bool:
        if self.recomputed == 0:
            return self.stated == 0
        return abs(self.stated - self.recomputed) <= self.tolerance * abs(self.recomputed)

    def explain(self) -> str:
        if self.ok:
            return f"reproduces: {self.method} = {_fmt(self.recomputed)}"
        return (
            f"DOES NOT REPRODUCE: {self.method} = {_fmt(self.recomputed)}, "
            f"stated {_fmt(self.stated)} (stated/recomputed = {self.ratio:.4g})"
        )


def _fmt(x: float) -> str:
    """Whole numbers with thousands separators; small values with up to 4 decimals."""
    if abs(x) >= 1000 or x == int(x):
        return f"{x:,.0f}"
    return f"{x:,.4f}".rstrip("0").rstrip(".")


def input_ids(method: str) -> list[str]:
    return [f"{a}-{b}" for a, b in _ID.findall(method)]


def recompute(
    method: str,
    inputs: Mapping[str, str | float],
    stated: str | float,
    *,
    tolerance: float = 0.005,
) -> EstimateCheck:
    """Re-run an estimate's method on its inputs and compare with the stated value.

    Inputs are cited by anchor ID only (``LAB-011``); any other name is refused, so an
    estimate can never rest on an input the library cannot trace.
    """
    bad = [k for k in inputs if not _ID.fullmatch(k)]
    if bad:
        raise ValueError(f"inputs must be anchor IDs like LAB-011: {', '.join(bad)}")
    env = {
        aid.replace("-", "_"): (parse_number(v) if isinstance(v, str) else float(v))
        for aid, v in inputs.items()
    }
    expr = _ID.sub(lambda m: f"{m[1]}_{m[2]}", method)
    value = _eval(ast.parse(expr, mode="eval"), env)
    st = parse_number(stated) if isinstance(stated, str) else float(stated)
    return EstimateCheck(method=method, stated=st, recomputed=value, tolerance=tolerance)
