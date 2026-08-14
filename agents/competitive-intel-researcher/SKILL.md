---
name: competitive-intel-researcher
description: Run decision-driven competitive intelligence on 1-5 vendors — evidence-graded dossiers, a weighted comparison matrix, say/do gap analysis, Four Corners response prediction, and Know/Say/Show battlecards. Use whenever Dhruv asks to analyze a competitor or a competitive landscape, build or refresh a battlecard, compare vendors, run competitive intel, prep a competitive case study or interview, or asks "what's new with <competitor>" — and also when he names a company and asks how we'd sell against them.
---

# Competitive Intel Researcher (v2)

Decision-driven competitive intelligence with a defined information model. The credibility of the output is the product: every claim graded and dated, every depth failure visible, analysis separated from collection.

## Phase 0 — Intake (ALWAYS confirm before researching)

Intelligence starts from the decision it serves, not from data. Before any research, confirm with Dhruv (AskUserQuestion when available, otherwise in chat):

1. **Mode** — which decision is this run serving?

| Mode | The decision | Outputs |
|---|---|---|
| Deal support | "How do we beat X in live deals?" | Battlecard + head-to-head delta |
| Landscape | "Who wins this category, where do we fit?" (2–5 vendors) | Dossiers + comparison matrix + landscape report |
| Monitoring refresh | "What changed since last look?" | Delta memo vs. baseline |
| Positioning/prep | Case study, interview, messaging work | Landscape report + say/do gaps |

2. **Vendor list** — and which one is "us" / the client, if any.
3. **Our product context** — who we are, which deals we meet them in. Without it, "how we win" is generic; say so.
4. **Capability taxonomy draft + weights** (landscape/deal modes) — propose 6–10 category capability dimensions drawn from buyer decision criteria, and pillar weights for the run's ICP ("for a 200-bed hospital buyer, integration depth weighs 3×"). Dhruv approves or edits before scoring begins. Defining the taxonomy BEFORE profiling any vendor prevents anchoring on one vendor's feature sheet.

Also at intake: check `<repo>/intel/<competitor-slug>/` for prior baselines (`<repo>` = `$MARKETING_AGENTS_ROOT` or `~/github/marketing-agents`). Prior intel makes the delta memo the highest-value output.

## Phase 1 — Collection: one dossier per vendor

Follow [references/dossier-template.md](references/dossier-template.md) exactly: eight sections (identity, ICP, capabilities, pricing, GTM, voice of market, trajectory, Four Corners), every field filled / `not found` / `out of scope`. Empty is visible, never silent.

**Hard gates — a run that can't meet one states the miss in the output rather than passing silently:**
- Voice of market: ≥15 reviews per vendor across ≥2 sources, themes as frequency counts, switching patterns captured.
- Capabilities verified against docs/changelogs, never marketing pages alone.
- Pricing carries fetched-on dates; fetch the actual pages — search snippets rank stale content.
- Every material claim graded: Verified / Corroborated / Reported / Inference. Conflicts reported as conflicts.

**Execution note:** for 3+ vendors, spawn one general-purpose subagent per dossier (parallel, each returning the completed dossier file path) — depth per vendor shouldn't shrink as vendor count grows.

## Phase 2 — Analysis (consumes dossiers; adds no new collection)

1. **Comparison matrix** — Wave-style: score each vendor 0–5 per capability dimension (evidence-cited), roll up under three weighted pillars: **Current offering** (D3), **Strategy** (D7/D8), **Market presence** (D2/D6/D7). Publish the weights and per-cell scores so the ranking is reproducible and reweightable. Deal-breaker row sits outside the weighting — a vendor missing a veto requirement can't score past it.
2. **Say/do gap per vendor** — messaging themes (D5) vs. market voice (D6): where positioning writes checks the reviews say the product doesn't cash. This is the attack surface.
3. **Four Corners synthesis** — predicted moves per vendor (2–4 quarters) and likely response to our play, all labeled Inference with evidence.
4. **Head-to-head deltas** — for each pairing that matters: win / lose / tie per dimension with the evidence line.

## Phase 3 — Outputs

Write to `<repo>/outputs/<run-slug>/<YYYY-MM-DD>/`:

```
dossier-<vendor>.md        # evidence base, one per vendor
comparison-matrix.md       # scores, weights, deal-breakers, reweighting note
landscape-report.md        # synthesis: market map, say/do gaps, predicted moves, so-whats
battlecard-<vendor>.md     # deal-support mode — per references/battlecard-template.md
delta-memo.md              # when a baseline exists: what changed, so-what per change
```

Report discipline: every section leads with the so-what; dossiers are appendix-grade but the landscape report reads standalone; every recommendation traces to a graded claim; strengths and gaps both named — an analysis where one vendor wins everything is a red flag for anchoring.

## Phase 4 — Freshness and follow-up

Decay rates: **fast** (pricing, changelog, jobs, headcount — recheck every run), **medium** (messaging, ads, review inflow — monthly), **slow** (ICP, strategy, Four Corners — quarterly). Delta memos diff fast-decay fields first.

After the run, offer — don't silently do: promote the fresh dossiers to `intel/<competitor-slug>/` as the new baseline; pull the single most decision-relevant insight into chat if this connects to an active process.

## Calibration

- Landscape runs with hard gates are long; say so up front and estimate scope at intake.
- Fewer than 15 reviews existing for a niche vendor is a finding (young/small market presence), not a gate failure — report the real count and proceed.
- "How we lose" and honest deal-breakers are what make sales trust the card. Never produce a card where we always win.
