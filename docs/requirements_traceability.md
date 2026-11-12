# Requirements traceability

The business requirements GSPS implements, where each lives, and its status in 0.1.0.
Status: **Done** (implemented and tested), **Partial**, **Planned**.

## Library

| ID | Requirement | Where | Status |
|---|---|---|---|
| L01 | Every external figure is an anchor with owner, URL, as-of, grade, tier, receipt and walk date | `model.records.Anchor` | Done |
| L02 | Anchors are grouped in lanes; ID prefix equals lane | `rules.integrity` | Done |
| L03 | Our own assumptions are a separate kind; estimates cite inputs by ID | `vocab` (`nature`), `rules.estimates` | Done |
| L04 | Internal facts are attestations, never graded as walked | `Verdict.ATTESTED`, fill-report class `attested` | Done |
| L05 | Versioned by date; next = highest + 1 | `store.versioned` | Done |
| L06 | Nothing deleted; TO_DELETE_ prefix | `store.versioned.mark_to_delete` | Done |
| L07 | One place tells consumers which file is current | `store.versioned.latest`, `Library.load` | Done |
| L08 | Findings stored with the question they answer and their stance | `model.records.Finding.question` | Done |
| L09 | Every metric has a stored spine and its own resolution order | `golden.spine`, `golden.resolution` | Partial (in memory; persistence planned) |
| L10 | Golden Metrics with status, rule, approval | `golden.resolution` | Partial (no touch fields yet) |

## Walks and grading

| ID | Requirement | Where | Status |
|---|---|---|---|
| W01 | A value enters only from the owner's page; a lead is never a source | `rules.grading`, `walk.track1` | Done |
| W02 | Extract twice; enter only on match | `rules.grading.accept_value` | Done |
| W03 | Ladder + ceiling on every row; effort is a to-do | `vocab`, `walk.track1` | Done |
| W04 | Blocks are logged, never routed around | `walk.gates` (FollowupItem) | Done |
| W05 | Paste-ready list whenever a gate blocks | `walk.gates.paste_block_for` | Done |
| W06 | Human walks recorded | `Track1Entry.human_walk`, `walked_by` | Done |
| W07 | Confidence computed, never typed | `rules.confidence` | Done |
| W08 | Observed and projected never blended | `golden.spine.Basis`, integrity check | Partial (needs a `value_basis` column in libraries) |
| W09 | Images reviewed as claims | token `check = visual` | Done |

## Vocabulary, freshness, deliverables, runs

| ID | Requirement | Where | Status |
|---|---|---|---|
| V01-V02 | Registered values; unregistered values yield | `vocab.registry` | Done |
| V03 | Proposed values visible in one list | `YieldLog` | Partial (CLI listing planned) |
| F01-F03 | Refresh fields; value vs record version; citation states and rollup | `rules.freshness`, `views` | Done |
| F04 | Re-walk queue when next_release passes | views section 5 (STALE) | Partial (queue file planned) |
| F05 | Noticing never ripples; re-render only on request | engine never edits deliverables | Done |
| F06 | Full dependency cascade, including estimates whose inputs moved | `cascade.graph`, `cascade.derived` | Done |
| D01-D04 | Token registry; wording tokens; fill report; dirty detection | `deliverable` | Done |
| D05 | Fixes returned as a tracked-changes redline | out of scope for 0.1 | Planned |
| D06-D08 | Provenance stamp as a token; attestations held; estimates labeled | tokens, `walk.ship` | Done |
| R01-R02 | One frozen folder per review with manifest | `walk.run` | Done |
| I01 | Intake fingerprinted and logged | `model.Intake`, `store.fingerprint` | Partial (intake command planned) |
| I05 | Offered sources each get a decision and reason | `model.SourceCandidate` | Partial (decision workflow planned) |
| G01 | Views derived on every run | `views.build` | Done |
