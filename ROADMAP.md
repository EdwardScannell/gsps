# Roadmap

Work ahead, in priority order. Each item is sized to land as its own pull request with
tests. Status mirrors [`docs/requirements_traceability.md`](docs/requirements_traceability.md).

## Next

1. **Re-walk queue.** When an anchor passes its `next_release`, write a dated queue of what
   to re-walk before any document that cites it ships. (F04)
2. **Golden Metrics persistence.** Store spines and Golden candidates as versioned files,
   with touch fields (created, updated, last refreshed, reviewed, approved). (L09, L10)
3. **Observed vs projected as a first-class column** (`value_basis`), enforced in views,
   resolution and the ship gate. (W08)

## Later

4. **Intake command.** Fingerprint, version and log every incoming document; archive the
   original. (I01)
5. **Source-candidate workflow.** Every offered source gets a potential band, a decision
   and a reason, returned in the run's report. (I05)
6. **Yield list command.** One place that lists every value awaiting a ruling. (V03)
7. **Tracked-changes redline.** Return page fixes as a Word document with tracked changes
   and comments, never silent edits. (D05)
8. **Fetcher interface.** A typed protocol so a person or an agent can plug in how pages
   are opened, without the engine ever making network calls itself.

## Done

- `gsps qual-summary`: per-question stance counts, documentary sources, lean and
  thin / contrary / vendor-heavy flags.
- `gsps ingest`: record walks as a new dated anchors version and report the ripple
  ([`docs/ingest.md`](docs/ingest.md)).
- 0.1.0: vocabulary and yields, grading, confidence, freshness and sync, versioned storage,
  briefs and claim routing, shopping request/report, Track-1 / Track-2 / qualitative
  outputs, ship gate, fill report, dependency cascade, Golden resolution, views, CLI, CI.
