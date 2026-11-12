# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-11

First public release.

### Added
- Vocabulary registry with yields: unregistered or blank values are flagged for a person,
  never coined and never silently rejected. Default enums, or a markdown registry file.
- Library records compatible with the 28-column anchor CSV format; extra columns preserved.
- Rules: derived confidence (H/M/L), staleness and sync on value version, extract-twice and
  lead-vs-source grading, effort-ceiling guard, integrity checks, reproducible estimates
  (restricted arithmetic over anchor IDs).
- Storage discipline: dated versions (next = highest + 1, gaps never filled), exclusive
  create, `TO_DELETE_` marking instead of deletion, CSV only through a parser, sha256.
- Requester side: walk briefs (YAML), business-case claims with routing to Track 1 /
  Track 1 internal / Track 2, Shopping Request and Shopping Report with loop-closure rules.
- Walk outputs: Track-1 log with consistency rules, Track-2 assumption register,
  qualitative findings with thin / contrary / vendor-heavy flags, web gates and paste
  blocks, frozen walk-run folders with manifests and verification, the ship gate.
- Deliverables: token registry and fill report (class, grade, confidence, upstream /
  edited / visual dirt), with estimate inputs followed through the full dependency chain.
- Library views, dependency graph with full transitive impact, metric spines and Golden
  Metric resolution (contested on disagreement; approval only by a ratifier).
- `gsps` command line, worked example, regression tests from real incidents, CI.
