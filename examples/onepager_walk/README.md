# Worked example: grounding a one-pager

A complete walk for **Northwind Careers, a fictional product**. The labor-market figures
(BLS, Challenger) and the research sources in `qualitative.csv` are real and public, with
their URLs. The competitor in claim C04 ("ExampleApply") is **fictional**; its page and
quote are invented for the example.

| File | What it is |
|---|---|
| `brief.yaml` | The requester's brief: questions, inputs, scope |
| `page.md` | The page under review |
| `claims.csv` | Every claim extracted from the page, routed to a track |
| `track1.csv` | Sourced claims: primary, gate, verbatim, grade, verdict |
| `track2.csv` | The assumption register |
| `qualitative.csv` | Q4 sources with method and stance |

```bash
gsps brief examples/onepager_walk/brief.yaml
gsps validate-walk --claims examples/onepager_walk/claims.csv --track1 examples/onepager_walk/track1.csv
gsps ship-check --claims examples/onepager_walk/claims.csv \
  --track1 examples/onepager_walk/track1.csv --track2 examples/onepager_walk/track2.csv \
  --page examples/onepager_walk/page.md
```

Expected: the walk is consistent, and the page is **blocked** by four claims:
C04 (WRONG: a competitor does approve-first), C05 and C06 (UNVERIFIABLE) and C09 (a legal
claim waiting on the ratifier). That is the point: the gate tells you exactly what to
rewrite before the page ships.
