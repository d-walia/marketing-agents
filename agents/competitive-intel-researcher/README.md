# Competitive Intel Researcher

Decision-driven competitive intelligence on 1–5 vendors — evidence-graded dossiers, a weighted comparison matrix, and battlecards sales can read verbatim. The credibility of the output is the product.

## What you get

Depends on the mode (every run starts by confirming which decision it serves):

| Mode | Outputs |
|---|---|
| Deal support | Know/Say/Show battlecard + head-to-head delta |
| Landscape (2–5 vendors) | Per-vendor dossiers + weighted comparison matrix + landscape report |
| Monitoring refresh | Delta memo against the `intel/` baseline |
| Positioning/prep | Landscape report + say/do gap analysis |

## How to run

Ask: "build a battlecard for [company]", "compare [A] vs [B] vs [C]", "what's new with [competitor]", or "how would we sell against [company]?" The skill confirms mode, vendor list, capability taxonomy, and scoring weights before researching — collection starts from the decision, not from data.

## How it works

1. **Intake** — mode, vendors, product context, and a capability taxonomy defined *before* profiling any vendor (prevents anchoring on one vendor's feature sheet).
2. **Collection** — one dossier per vendor against a fixed 8-section schema ([references/dossier-template.md](references/dossier-template.md)): identity, ICP, capabilities, pricing, GTM motion, voice of market, trajectory, and a Porter Four Corners strategy read. Parallel subagents for 3+ vendors so depth doesn't shrink with vendor count.
3. **Analysis** — Forrester-Wave-style weighted matrix (published, reweightable scores + deal-breaker vetoes), say/do gap per vendor, predicted moves, head-to-head deltas.
4. **Outputs** — dossiers, matrix, landscape report, battlecards, delta memo.

## Design decisions

- **Hard evidence gates**: ≥15 reviews per vendor across ≥2 sources with frequency-counted themes; capabilities verified against docs/changelogs, never marketing pages; pricing dated. A run that can't meet a gate says so in the output — depth failures are visible, never silent.
- **Every claim graded** — Verified / Corroborated / Reported / Inference — with conflicts reported as conflicts.
- **Analysis is separated from collection**: dossiers are the evidence base; the matrix, report, and battlecard consume them and add no new research.
- **Four Corners is what makes it intelligence**: drivers, assumptions, strategy, capabilities → predicted moves and likely response to our play, labeled as inference.
- **"How we lose" is mandatory** — a battlecard that says we always win is marketing to ourselves.

Method sources: SCIP's KIT/collection-plan discipline, Porter's Four Corners, Forrester Wave scoring structure, Clozd's win/loss discipline, Klue's Know/Say/Show framework. Full rationale: `~/Desktop/Claude Outputs/competitive-intel-v2-design.md`.
