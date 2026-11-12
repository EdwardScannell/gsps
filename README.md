# GSPS

**A provenance engine for external facts.** Every figure a document uses walks to its
owner's primary source, is graded on an explicit confidence ladder, and ships with its
receipts.

GSPS is for anyone who publishes numbers they did not produce: pitch decks, research
notes, policy briefs, market sizing, data rooms. It turns the discipline of a careful
fact-checker into rules a machine enforces.

[![CI](https://github.com/EdwardScannell/gsps/actions/workflows/ci.yml/badge.svg)](https://github.com/EdwardScannell/gsps/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

## Why

Most wrong numbers in published documents are not invented. They are copied: from a
search summary, from a blog that misread the source, from last month's release that has
since been revised, from a competitor's comparison page. GSPS exists to make each of those
failures loud.

| Failure | What GSPS does |
|---|---|
| A search summary is quoted as if it were the source | A **lead** cannot set or grade a value. Only the owner's own page can. |
| An extractor invents a table row that is not on the page | **Extract twice.** A value enters only when two independent extractions match. |
| Last month's figure has been revised | Citations go **Behind** when a value version moves; the document takes its worst citation. |
| "We're the only one that does X" | An **absence claim** can be disproved by a walk, never confirmed. |
| An estimate is presented as a fact | Estimates live in an **assumption register**, must reproduce from their inputs, and must carry their label on the page. |
| A new category is quietly invented to make data fit | Unregistered values **yield** to a person. The engine never coins a value. |
| One input changes and nobody knows what it touches | A **dependency graph** reports every estimate, token and document downstream. |
| A file is edited in place and history is lost | **Dated versions**, exclusive create, never overwrite, never delete. |

## What it is (and is not)

GSPS is the **engine**: models, rules, storage discipline and reports. It does **not**
fetch, search or browse. Walking a page is done by a person or an agent; the engine
receives what was walked (URL, gate, two verbatim extractions) and enforces every rule
from there. That boundary is deliberate: it keeps the engine deterministic, testable and
safe to run anywhere.

## Install

```bash
pip install -e ".[dev]"          # from a clone
pip install -e ".[dev,docx]"     # also read .docx pages
```

Python 3.11+.

## Quick start

```bash
# Is the walk internally consistent? (routing + every Track-1 entry against the rules)
gsps validate-walk --claims examples/onepager_walk/claims.csv \
                   --track1 examples/onepager_walk/track1.csv

# Can the page ship?
gsps ship-check --claims examples/onepager_walk/claims.csv \
                --track1 examples/onepager_walk/track1.csv \
                --track2 examples/onepager_walk/track2.csv \
                --page   examples/onepager_walk/page.md

# Views over a library (status, staleness, punch list, integrity, vocabulary yields)
gsps views --library tests/fixtures/library --as-of 2026-11-15 --dry

# What moves when one input moves?
gsps impact --library tests/fixtures/library --anchor PRC-001

# Does an estimate reproduce from its inputs?
gsps recompute --method "SAM-001 * PRC-001 * 12" --stated '$2.34B' \
               --input SAM-001=5000000 --input PRC-001=39
```

`ship-check`, `validate-walk`, `vocab-check`, `fill-report` and `recompute` exit non-zero
when something blocks, so they drop straight into CI.

## The model in one page

**Roles.** A *requester* hands over requirements (questions, documents, scope), not
sources. A *keeper* finds the evidence and maintains the library. A *ratifier* (a person)
rules on anything the engine refuses to decide.

**Library.** Every external value is an **anchor**: owner, URL, as-of, grade, ceiling,
authority tier, verbatim receipt, walk date, value version and record version.

**Grades** (strongest to weakest): Confirmed, Sourced, Grounded, Potential, Reported,
Unverified, Hypothesis, Conjecture. Only a walked primary earns the first three.

**Ceilings** record why a walk stopped: none, effort, access, structural. `effort` is a
to-do, never a resting state, and never ships.

**Confidence** (H / M / L) is derived from grade and authority tier. It is never typed.

**Two tracks** for every claim on a page:

* **Track 1** (sourced facts): claim, primary source, verdict
  (CONFIRMED / WRONG / UNVERIFIABLE; ATTESTED for internal facts).
* **Track 2** (assumptions, estimates, narrative): `{basis, label, status, drift risk}`.
  Registered, never sourced.

**Qualitative questions** are answered as question, sources, stance
(supports / contradicts / complicates). Thin, contrary and vendor-heavy evidence is
flagged as a finding, not hidden.

**Ship gate.** A page ships only when every claim on it is CONFIRMED, ATTESTED, or
registered and labeled. WRONG, UNVERIFIABLE, pending and contested all block.

See [`docs/architecture.md`](docs/architecture.md) and
[`docs/rules_to_code.md`](docs/rules_to_code.md).

## Layout

```
src/gsps/
  vocab/         registered values and the yield log
  model/         library records (CSV-compatible)
  rules/         confidence, freshness, grading, integrity, estimate recompute
  store/         dated versions, CSV through a parser, fingerprints
  requirements/  briefs, business-case claims, shopping requests and reports
  walk/          Track-1 log, Track-2 register, qualitative, gates, runs, ship gate
  deliverable/   token registry, fill report
  views/         derived library views
  cascade/       dependency graph
  golden/        metric spines and Golden Metric resolution
  cli.py
tests/
  unit/          one file per rule
  regression/    real incidents, each a permanent test
  business_cases/ a requester's brief as an executable ship gate
examples/onepager_walk/   a complete worked walk
```

## Development

```bash
make check      # ruff, mypy --strict, pytest with coverage
```

Contributions: see [`CONTRIBUTING.md`](CONTRIBUTING.md). Every bug fixed gets a
regression test named after the incident.

## License

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
