"""The dependency graph.

Nodes are anchors (``LAB-011``), tokens (``token:T05``) and deliverables
(``deliverable:OPG-001``). Edges run from an input to what depends on it:

* an estimate anchor depends on the anchors its ``series_or_table`` cites by ID;
* a token depends on the anchors in its ``depends_on``;
* a deliverable depends on the anchors its citations name.

:meth:`DependencyGraph.impact` returns the full transitive closure, so when one input
moves, every estimate, token and deliverable downstream is flagged, not only the first
level. Noticing never ripples by itself: the impact is a report, not an edit.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field

from gsps.model.records import Anchor, Citation, Token

TOKEN = "token:"
DELIVERABLE = "deliverable:"


class CycleError(ValueError):
    pass


@dataclass(frozen=True)
class Impact:
    source: str
    anchors: frozenset[str] = field(default_factory=frozenset)
    tokens: frozenset[str] = field(default_factory=frozenset)
    deliverables: frozenset[str] = field(default_factory=frozenset)

    @property
    def empty(self) -> bool:
        return not (self.anchors or self.tokens or self.deliverables)


class DependencyGraph:
    def __init__(self) -> None:
        self._down: dict[str, set[str]] = defaultdict(set)
        self._up: dict[str, set[str]] = defaultdict(set)

    def add_edge(self, upstream: str, downstream: str) -> None:
        if upstream == downstream:
            raise CycleError(f"{upstream} depends on itself")
        self._down[upstream].add(downstream)
        self._up[downstream].add(upstream)

    @classmethod
    def build(
        cls,
        anchors: Iterable[Anchor] = (),
        tokens: Iterable[Token] = (),
        citations: Iterable[Citation] = (),
    ) -> DependencyGraph:
        g = cls()
        for a in anchors:
            for i in a.input_ids:
                g.add_edge(i, a.anchor_id)
        for t in tokens:
            for aid, _ in t.references():
                g.add_edge(aid, TOKEN + t.token_id)
        for c in citations:
            g.add_edge(c.anchor_id, DELIVERABLE + c.deliverable_id)
        g.assert_acyclic()
        return g

    def downstream(self, node: str) -> set[str]:
        seen: set[str] = set()
        queue = deque(self._down.get(node, ()))
        while queue:
            n = queue.popleft()
            if n not in seen:
                seen.add(n)
                queue.extend(self._down.get(n, ()))
        return seen

    def upstream(self, node: str) -> set[str]:
        seen: set[str] = set()
        queue = deque(self._up.get(node, ()))
        while queue:
            n = queue.popleft()
            if n not in seen:
                seen.add(n)
                queue.extend(self._up.get(n, ()))
        return seen

    def impact(self, anchor_id: str) -> Impact:
        down = self.downstream(anchor_id)
        return Impact(
            source=anchor_id,
            anchors=frozenset(n for n in down if ":" not in n),
            tokens=frozenset(n.removeprefix(TOKEN) for n in down if n.startswith(TOKEN)),
            deliverables=frozenset(
                n.removeprefix(DELIVERABLE) for n in down if n.startswith(DELIVERABLE)
            ),
        )

    def assert_acyclic(self) -> None:
        indegree: dict[str, int] = defaultdict(int)
        nodes = set(self._down) | set(self._up)
        for n in nodes:
            for d in self._down.get(n, ()):
                indegree[d] += 1
        queue = deque(n for n in nodes if indegree[n] == 0)
        visited = 0
        while queue:
            n = queue.popleft()
            visited += 1
            for d in self._down.get(n, ()):
                indegree[d] -= 1
                if indegree[d] == 0:
                    queue.append(d)
        if visited != len(nodes):
            stuck = sorted(n for n in nodes if indegree[n] > 0)
            raise CycleError("dependency cycle among: " + ", ".join(stuck))
