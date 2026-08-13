# Competitive Intel Researcher

Turns a week of battlecard research into an afternoon — without turning it into fiction. The credibility of the output is the product.

## What you get

Three files per run in `outputs/<competitor-slug>/<date>/`:

- **`full-report.md`** — the sourced analysis, organized by five lenses (company scan, voice of market, trajectory, positioning read, delta).
- **`battlecard.md`** — one page, sales-facing: who they are, how we win, **how we lose** (mandatory — a card that says we always win is marketing to ourselves), landmines to set, objection handling, pricing with a fetched-on date.
- **`delta-memo.md`** — when prior intel exists in `intel/<competitor-slug>/`: what changed since last look, with the so-what for sales in one line per change.

## How to run

Ask: "build a battlecard for [company]", "what's new with [competitor]", or "how would we sell against [company]?" Providing your own product context (who we are, which deals we meet them in) transforms the "how we win" section from generic to usable — the skill says so plainly when context is missing.

## How it works

| Lens | Question it answers | Source |
|---|---|---|
| 1. Company scan | What do they *say* they are? | Product pages, pricing, docs, changelog, customer logos |
| 2. Voice of market | What do customers *say* they are? | G2/Capterra/TrustRadius themes, why users switched |
| 3. Trajectory | Where are they going? | Funding, exec hires, press, open job postings (postings telegraph roadmap) |
| 4. Positioning read | Where's the attack surface? | The gap between lens 1 and lens 2 |
| 5. Delta | What changed? | Diff against `intel/<competitor-slug>/` |

## Design decisions

- **Fetch the actual pages** — search results alone rank stale and dead content (verified repeatedly in practice).
- **Every factual claim carries its source URL inline**; anything not directly verifiable is labeled `(inference)` — allowed, but never disguised as fact. Conflicting sources are reported as conflicts, not silently resolved.
- **Pricing gets a fetched-on date** — a battlecard with stale pricing burns sales' trust exactly once.
- **The tracker stays untouched during runs**: promoting a fresh report to the `intel/` baseline is offered afterward, never silent.
