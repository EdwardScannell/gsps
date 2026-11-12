# Ingesting walks

`gsps ingest` records walked values into a library as a new dated anchors version, logs
every walk (refusals included), and reports what the change ripples into.

```bash
gsps ingest --library path/to/library --walks walks.csv [--on YYYY-MM-DD] [--tokens TOKENS.csv]
```

Exit code 0 when every walk was accepted, 1 when any was refused.

## The walks file

One row per walked value.

| Column | Required | Meaning |
|---|---|---|
| `anchor_id` | yes | e.g. `LAB-012`. The prefix is the lane. |
| `value_1`, `value_2` | yes | Two independent extractions of the value. They must match. |
| `verbatim` | yes | The owner's sentence or table cell the value came from. |
| `url` | yes | The owner's own page (never a summary or a search result). |
| `gate` | yes | `paste`, `click`, `chained`; or `wall` with `human_walk=true`. |
| `walked_on` | yes | ISO date of the walk. |
| `as_of` | recommended | The period the value describes. A new period is a new release. |
| `walked_by`, `human_walk`, `is_owner_primary` | no | Who walked it; a person's walk past a wall; `false` marks a lead (refused). |
| `lane`, `anchor_type`, `metric`, `owner`, `grade`, `authority_tier`, `nature` | for new anchors | Required the first time an anchor is recorded. |
| `series_or_table`, `cadence`, `last_release`, `next_release`, `refresh_basis`, `next_release_label`, `ceiling`, `ceiling_note`, `public_citation` | no | Updated when present. |

## What each walk does

| Outcome | When | Effect |
|---|---|---|
| `added` | new anchor | `v1`, `change_type=new_release` |
| `rewalked` | same value, same period | `record_version` bumps only. Bookkeeping never ripples. |
| `revised` | same period, new value | `value_version` bumps, `prior_value` kept, `change_type=revision` |
| `new_release` | new period | `value_version` bumps, `change_type=new_release` |
| `refused` | lead, mismatch, uncleared gate, missing fields, wrong lane, duplicate | Logged; the library is unchanged |

## Files written

- `ANCHORS_<date>[_vN].csv`: the whole library at its new state. The previous version is
  untouched. Unknown extra columns are preserved.
- `WALKS/WALK_LOG_<date>[_vN].csv`: every walk with its outcome, gate, URL and verbatim.

Nothing is overwritten. Running the same ingest twice on one day writes `_v2`.

## The ripple

For every value that moved on an existing anchor, ingest reports the estimates, tokens and
deliverables downstream (the full chain, not one level), and each citation's new status.
A citation that cited the old value version is now **Behind**. Re-rendering a document is
never automatic: noticing a change never edits a page.
