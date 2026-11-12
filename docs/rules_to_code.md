# Rules to code

Each operating rule, the code that enforces it, and the test that proves it.

| # | Rule | Enforced in | Proven by |
|---|---|---|---|
| 1 | Read before you assert: a value enters only from the owner's own page | `rules.grading.accept_value` | `test_lead_tried_to_grade_a_claim` |
| 2 | Extract twice; a value enters only when both extractions match | `rules.grading.accept_value` | `test_summarizer_invented_a_table_row` |
| 3 | A lead never grades, confirms or contradicts | `walk.track1.entry_problems` | `test_walk.py::test_confirmed_needs_documentary_grade_and_cleared_gate` |
| 4 | Yield before coining: unregistered or blank values go to a person | `vocab.registry.Registry.check`, `rules.integrity` | `test_keeper_coined_a_vocabulary_value`, `test_registry.py` |
| 5 | Regenerate clean; never edit in place; never overwrite | `store.versioned.write_new`, `store.csv_io.write_rows` | `test_write_new_never_overwrites` |
| 6 | Next version = highest used + 1; gaps never filled; TO_DELETE_ counts | `store.versioned.next_version_path` | `test_store.py`, `test_write_views_versions` |
| 7 | Nothing is deleted; removal is a TO_DELETE_ rename | `store.versioned.mark_to_delete` | `test_mark_to_delete_renames_never_deletes` |
| 8 | Derived fields are computed, never typed | `rules.confidence`, `rules.freshness`; integrity check "typed columns that must be computed" | `test_confidence.py`, `test_freshness.py` |
| 9 | Sync is computed on value_version; metadata edits never ripple | `rules.freshness.sync_status` | `test_prior_month_revised_puts_citation_behind` |
| 10 | Blank next_release never auto-stales; blanks are listed | `rules.freshness.is_stale`, views section 5 | `test_blank_next_release_never_auto_stales` |
| 11 | A deliverable takes its worst citation, current version only | `views.build` section 0 | `test_views_sections` |
| 12 | Walk every claim to a ceiling; `effort` is a to-do, never a verdict | `rules.grading.can_ship_with_ceiling`, `walk.track1` | `test_effort_ceiling_is_not_a_resting_state` |
| 13 | Never fold distinct kinds (SA vs NSA, offer vs cut, observed vs projected) | registry values, `golden.resolution.resolve` | `test_seasonally_adjusted_vs_not_adjusted_are_different_values`, `test_observed_and_projected_never_mix` |
| 14 | Name the gate; hand back a paste-ready block; never route around a wall | `walk.gates` | `test_paste_block_for_failures_skips_walls` |
| 15 | Absence and universal claims can be disproved, never confirmed | `walk.track1.entry_problems` | `test_only_one_claim_cannot_be_confirmed` |
| 16 | Estimates reproduce from inputs cited by ID | `rules.estimates.recompute` | `test_market_size_was_one_tenth_of_its_own_math` |
| 17 | Estimates ship labeled; legal claims wait for the ratifier | `walk.ship._ship_t2` | `test_legal_assertion_waits_for_the_ratifier`, `test_ship_render_and_t2_branches` |
| 18 | Internal facts need a record or a named attestation | `walk.track1.entry_problems`, `walk.ship` | `test_internal_proof_case_without_a_receipt_blocks_ship` |
| 19 | Contested blocks shipping until a ruling | `walk.ship.ship_check(contested=...)` | `test_contested_claim_blocks` |
| 20 | Change ripples through every dependent, not one level | `cascade.graph.DependencyGraph.impact` | `test_full_transitive_impact` |
| 21 | Golden values: rule proposes, ratifier approves; unknown sources never win | `golden.resolution` | `test_cascade_and_golden.py` |
| 22 | A frozen run cannot change silently | `walk.run.WalkRun.freeze/verify` | `test_run_numbering_freeze_and_verify` |
| 23 | No token ships bare; estimates carry route and band; dirty blocks release | `requirements.shopping.validate_report` | `test_requirements.py` |
| 24 | A walk enters only cleared, twice-extracted and from the owner; a moved value bumps value_version and ripples | `walk.ingest.apply_walks` | `test_ingest.py`, `test_september_revision_ripples_through_ingest` |
