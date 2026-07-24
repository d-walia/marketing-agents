---
name: competitive-intel-researcher
description: Run a full competitive analysis of a named company and turn it into a sourced report, a one-page sales battlecard, and a "what changed" delta memo against existing intel. Use whenever Dhruv asks to analyze a competitor, build or refresh a battlecard, run competitive intel, prep a competitive landscape for a case study or interview, or asks "what's new with <competitor>" — and also when he names a company and asks how we'd sell against them.
---

# Competitive Intel Researcher

Turn a week of battlecard research into an afternoon — without turning it into fiction. The credibility of the output is the product: a battlecard sales can't trust is worse than no battlecard.

## Inputs

- **Competitor name** (required). If ambiguous, resolve the company first (domain, category) and confirm in one line before deep research.
- **Our product context** (optional but transformative): who we are, what we sell, which deals we meet this competitor in. Without it, produce the analysis but say plainly that "how we win" is generic until context is supplied.
- **Existing intel**: check `~/github/marketing-agents/intel/<competitor-slug>/` before researching. If it exists, the delta memo is the most valuable output. If not, this run becomes the baseline.

## Pipeline

Work through five lenses. For each, fetch the actual pages — search results alone go stale and rank dead content (verified repeatedly in practice).

1. **Company scan** — their site: product pages, pricing page, docs, changelog, customer logos. What do they *say* they are?
2. **Voice of market** — G2/Capterra/TrustRadius review themes: recurring strengths, recurring complaints, and *why users switched* (in or out). What do customers *say* they are?
3. **Trajectory** — funding, acquisitions, exec hires, press, and **open job postings** (postings telegraph roadmap: a company hiring "PMM, Payer Segment" is telling you their next market).
4. **Positioning read** — the gap between lens 1 and lens 2 is the attack surface. Where does their marketing write checks their reviews say the product doesn't cash?
5. **Delta** — diff everything above against `intel/<competitor-slug>/`. What's new, what's gone, what shifted. No prior intel → skip, and say the run establishes the baseline.

## Verification rules

These are what make the output usable in front of a sales team:

- Every factual claim carries its source URL inline.
- Anything not directly verifiable is labeled `(inference)` — inferences are allowed and often valuable, but never disguised as fact.
- Pricing gets a fetched-on date; competitor pricing changes silently and a battlecard with stale pricing burns trust exactly once.
- If two sources conflict, report the conflict rather than picking silently.

## Outputs

Write three files to `~/github/marketing-agents/outputs/<competitor-slug>/<YYYY-MM-DD>/`:

**`full-report.md`** — the sourced analysis, organized by the five lenses.

**`battlecard.md`** — one page, sales-facing, in their language not analyst language:
```
# Selling against <Competitor>
## Who they are (2 sentences)
## How we win (3 bullets, each tied to a verified weakness or gap)
## How we lose (honest — the deals where they beat us and why)
## Landmines to set (questions a rep asks that expose their gaps)
## Objection handling (what to say when the prospect quotes their pitch)
## Pricing intel (with fetched-on date)
```
The "How we lose" section is mandatory. A battlecard that says we always win is marketing to ourselves; reps trust the card *because* it names the deals to qualify out of.

**`delta-memo.md`** (when prior intel exists) — what changed since last look, and the so-what for sales in one line per change.

## After the run

Offer — don't silently do — two follow-ups: copy the fresh report into `intel/<competitor-slug>/` as the new baseline, and (if the competitor relates to an active interview process or client) pull the one insight worth leading with into chat.

## Calibration

A good run cites 10+ distinct sources across at least three lens types. If research turns up thin coverage (young company, private, no reviews), say so and mark the whole card lower-confidence rather than padding with inference dressed as fact.
