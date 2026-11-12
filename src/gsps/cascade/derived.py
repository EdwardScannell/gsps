"""Derived values whose inputs moved after they were computed.

An estimate keeps its own ``value_version`` until someone recomputes it, so a citation to it
stays In sync even when its inputs were revised. That is correct bookkeeping, but the
estimate is now stale. :func:`estimates_with_moved_inputs` finds every anchor with inputs
where any input, anywhere up the chain, was revised or re-released *after* the anchor was
last computed (its ``last_touch``, else ``last_walked``).
"""

from __future__ import annotations

from collections.abc import Iterable

from gsps.cascade.graph import DependencyGraph
from gsps.model.records import Anchor, parse_date

_MOVES = {"revision", "new_release"}


def estimates_with_moved_inputs(anchors: Iterable[Anchor]) -> dict[str, list[str]]:
    """Map each stale derived anchor to the sorted inputs that moved after it was computed."""
    by_id = {a.anchor_id: a for a in anchors}
    graph = DependencyGraph.build(anchors=by_id.values())
    stale: dict[str, list[str]] = {}
    for a in by_id.values():
        if not a.input_ids:
            continue
        computed = parse_date(a.last_touch) or parse_date(a.last_walked)
        if computed is None:
            continue
        moved = []
        for i in graph.upstream(a.anchor_id):
            x = by_id.get(i)
            if x is None or x.change_type not in _MOVES or x.value_version == "v1":
                continue
            changed = parse_date(x.last_walked) or parse_date(x.last_touch)
            if changed is not None and changed > computed:
                moved.append(i)
        if moved:
            stale[a.anchor_id] = sorted(moved)
    return stale
