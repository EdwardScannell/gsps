# Architecture

GSPS separates **walking** (finding and reading the owner's page) from **enforcing**
(everything that happens to what was read). The package is only the second half.

```
           requester                         keeper (person or agent)                 ratifier
               |                                      |                                   |
  brief.yaml   |  questions, inputs, scope            |                                   |
  claims.csv   +------------------------------------->|  walks pages (outside GSPS)       |
                                                      |  -> URL, gate, 2 extractions      |
                                                      v                                   |
   +-------------------------------- gsps (this package) --------------------------+      |
   |  requirements/  brief, claims + routing, shopping request/report              |      |
   |  rules/         grading (lead vs source, extract twice), confidence,          |      |
   |                 freshness/sync, integrity, estimate recompute                 |      |
   |  vocab/         registry -> yields  ---------------------------------------------------> rules on new values
   |  store/         dated versions, exclusive create, CSV via parser, sha256      |      |
   |  walk/          Track-1 log, Track-2 register, qualitative, gates, runs       |      |
   |  deliverable/   tokens, fill report (dirty upstream / edited / visual)        |      |
   |  cascade/       dependency graph, transitive impact                           |      |
   |  golden/        spines, resolution order, Proposed / Contested  -----------------------> approves Golden
   |  views/         derived views of the whole library                            |      |
   |  walk/ship.py   the ship gate  -------------------------------------------------------> rulings unblock
   +-------------------------------------------------------------------------------+
```

## Layers

| Layer | Depends on | Holds |
|---|---|---|
| `vocab` | nothing | registered values, the yield log |
| `model` | nothing | permissive records (strings), CSV-compatible |
| `rules` | vocab, model | pure functions: every derived field |
| `store` | model | versioned files, CSV, fingerprints |
| `requirements` | store | briefs, claims, shopping contract |
| `walk` | requirements, rules, vocab | walk outputs and the ship gate |
| `deliverable` | rules, cascade, model | token checks and the fill report |
| `cascade` | model | dependency graph |
| `golden` | rules, vocab | spines and resolution |
| `views` | everything above | derived markdown |
| `cli` | everything | commands |

Dependencies point downward only. `rules` never touches the filesystem.

## Two design decisions worth knowing

**Records are permissive; validation yields.** A library may contain a value nobody has
registered yet. Rejecting the record would hide it; accepting it silently would let a new
category creep in. So records load as strings, and the registry produces a *yield*: a
visible item a person rules on.

**Derived fields are functions.** Confidence, staleness, sync and deliverable status are
never stored. Storing them is how a figure stays "H" after its source was revised.

## Library file layout

```
<library>/
  ANCHORS_<YYYYMMDD>[_vN].csv
  FINDINGS_<YYYYMMDD>[_vN].csv
  DELIVERABLES_<YYYYMMDD>[_vN].csv
  TENSIONS_<YYYYMMDD>[_vN].csv
  CITATION_MAP/CITATION_MAP_<YYYYMMDD>[_vN].csv
  STATE_FLAGS.md              optional registry; defaults apply when absent
  VIEWS/VIEWS_<YYYYMMDD>[_vN].md   written by `gsps views`
runs/WR-###_<docversion>_<YYYYMMDD>/   one frozen folder per review
```

If your library's column names differ, `Library.load(root, rename={"tensions": {...}})`
maps them onto field names without touching the files.
