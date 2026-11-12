# Live walk: a real revision, rippling through the engine

The October 2026 jobs report revised August and September payrolls upward. A brief written
after the September release now cites a number that has changed underneath it. This
example shows GSPS catching that, from the walk to the page, using only public figures.

```bash
bash examples/live_walk/run.sh      # from the repository root; works on a scratch copy
```

Recorded output: [`RUN_LOG.md`](RUN_LOG.md). CI runs the script on every push.

## The data (all public, with sources)

| Anchor | Value before | Value after the walk | Source |
|---|---|---|---|
| LAB-010 Aug 2026 payrolls | +133,000 | **+186,000** (revised) | BLS Employment Situation, Oct 2026 release |
| LAB-012 Sep 2026 payrolls | +29,000 | **+60,000** (revised) | same |
| LAB-013 Oct 2026 payrolls | (none) | +165,000 | same |
| JLT-001 Sep 2026 hires rate | (none) | 3.4% | BLS JOLTS, Sep 2026 |
| LAY-002 Oct 2026 announced cuts | (none) | 43,994 | Challenger Report, Oct 2026 |
| AID-001 cuts citing AI, Jan-Oct 2026 | (none) | 121,401 | same (employer-attributed) |
| FCT-001 consensus, Sep 2026 | +90,000 | unchanged | FactSet (a projection, kept distinct) |
| EST-001 Aug-Sep average (ours) | +81,000 | **stale: recomputes to 123,000** | `(LAB-010 + LAB-012) / 2` |

Two walks are refused on purpose: a vendor CEO's interview figure entered as a lead, and a
page that refused automated reading with no human walk recorded.

## What you see in the run

1. **Before:** LAB-010 and LAB-012 are STALE (their next release date has passed) and the
   brief is At risk.
2. **Ingest:** two revisions, four additions, two refusals; a new dated anchors version and
   a walk log; the ripple from each revision to the estimate, the tokens and the brief.
3. **After:** the brief's citation to September payrolls is **Behind**; the punch list says
   to recompute EST-001.
4. **Impact** of the September revision: EST-001, tokens T01 and T02, the brief.
5. **Fill report:** T01 dirty (its value moved) and T02 dirty (its inputs moved).
6. **Recompute:** the stated 81,000 no longer reproduces; the inputs now give 123,000.
7. **Integrity and vocabulary** on the new version: clean.
8. **Qualitative, before:** Q2 (job seekers) rested on 5 sources, 4 from hiring-software
   vendors, only 1 at a documentary grade: flagged *thin* and *vendor-heavy*. Q5 (trust
   and safety) had 2 sources: *thin*.
9. **Qualitative, after** widening the net to the NY Fed, Burning Glass Institute, Pew,
   Indeed Hiring Lab, the FBI's IC3 and the FTC: both flags clear, and the wider net
   surfaces findings that *complicate* the story (job-finding expectations up, postings
   above their pre-pandemic level, employment scams about 2% of all complaints). Sources
   pointing two ways are recorded as two rows, never folded into one stance.

Nothing on the page was edited. Noticing a change never edits a document; the person who
owns the brief decides whether to re-render it.

## Files

| File | What it is |
|---|---|
| `library/` | The library as of the October 3 walk |
| `walks_20261107.csv` | The November 7 walk: URL, gate, two extractions, verbatim |
| `TOKENS.csv`, `page_v1.md` | The brief and the values on it |
| `qualitative_20261107.csv` | Q2 and Q5 sources from the November 7 walk |
| `qualitative_20261112.csv` | The same plus 12 findings from the wider net |
| `run.sh` | The reproducible run |
| `RUN_LOG.md` | Its recorded output |
