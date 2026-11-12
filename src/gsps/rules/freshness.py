"""Freshness and sync.

* ``value_version`` bumps only when the value changes; ``record_version`` bumps on any
  bookkeeping change. Sync is computed on ``value_version`` only, so metadata edits never
  cause a false alarm.
* Stale: the as-of date is on or after ``next_release`` and the anchor was not walked
  again since then. A blank ``next_release`` never auto-stales.
* A citation is In sync, At risk (anchor stale, not re-walked), Behind (the cited value
  version moved) or DANGLING (anchor missing). A deliverable takes its worst citation.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping

from gsps.model.records import Anchor, Citation, parse_date
from gsps.vocab.values import SyncStatus


def is_stale(anchor: Anchor, as_of: dt.date) -> bool:
    nr = parse_date(anchor.next_release)
    lw = parse_date(anchor.last_walked)
    return bool(nr and as_of >= nr and (lw is None or lw < nr))


def sync_status(citation: Citation, anchors: Mapping[str, Anchor], as_of: dt.date) -> SyncStatus:
    current = anchors.get(citation.anchor_id)
    if current is None:
        return SyncStatus.DANGLING
    if current.value_version != citation.anchor_value_version:
        return SyncStatus.BEHIND
    return SyncStatus.AT_RISK if is_stale(current, as_of) else SyncStatus.IN_SYNC


def worst_status(statuses: Iterable[SyncStatus]) -> SyncStatus | None:
    items = list(statuses)
    return max(items, key=lambda s: s.rank) if items else None
