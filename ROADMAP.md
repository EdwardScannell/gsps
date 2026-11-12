# Roadmap

Work ahead, in priority order. Each item is sized to land as its own pull request with
tests. Status mirrors [`docs/requirements_traceability.md`](docs/requirements_traceability.md).

## Next

1. **Ingest walks into the library** (`gsps ingest`). Record walked values (URL, gate, two
   extractions) as a new dated anchors version; bump `value_version` only when the value
   moves; record `prior_value` and `change_type`; report the downstream impact.
2. **Re-walk queue.** When an anchor passes its `next_release`, write a dated queue of what
   to re-walk before any document that cites it ships. (F04)
3. **Golden Metrics persistence.** Store spines and Golden candidates as versioned files,
   with touch fields (created, updated, last refreshed, reviewed, approved). (L09, L10)
4. **Qualitative summaries from the command line.** `gsps qual-summary` over a sources
   file: stance counts, thin / contrary / vendor-heavy flags per question.
5. **Observed vs projected as a first-class column** (`value_basis`), enforced in views,
   resolution and the ship gate. (W08)

## Later

6. **Intake command.** Fingerprint, version and log every incoming document; archive the
   original. (I01)
7. **Source-candidate workflow.** Every offered source gets a potential band, a decision
   and a reason, returned in the run's report. (I05)
8. **Yield list command.** One place that lists every value awaiting a ruling. (V03)
9. **Tracked-changes redline.** Return page fixes as a Word document with tracked changes
   and comments, never silent edits. (D05)
10. **Fetcher interface.** A typed protocol so a person or an agent can plug in how pages
    are opened, without the engine ever making network calls itself.

## Done

- 0.1.0: vocabulary and yields, grading, confidence, freshness and sync, versioned storage,
  briefs and claim routing, shopping request/report, Track-1 / Track-2 / qualitative
  outputs, ship gate, fill report, dependency cascade, Golden resolution, views, CLI, CI.
