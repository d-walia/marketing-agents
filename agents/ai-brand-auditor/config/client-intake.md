# Client Intake Guide

What to collect from a client before auditing their brand, why each piece matters, and where it goes. Work top to bottom: each section is labeled **required** (the audit can't run or can't be trusted without it) or **better-with** (sharpens the audit but doesn't block it).

The one-line test for everything below: *does this change what we ask the models, or how we judge what they said back?* If it does neither, don't collect it.

---

## 1. The basics — required, fills `brand.json`

| Ask the client | Goes in |
|---|---|
| Brand name exactly as a buyer would type it | `brand` |
| Product category *in the buyer's words*, not the vendor's | `category`, `category_short` |
| Who is asking and why (role + trigger), as an "I'm a..." sentence | `buyer_query_context` |
| 3 direct competitors a buyer would shortlist | `competitors` |

**How to ask about competitors:** don't ask "who are your competitors" — ask **"who did you lose your last five deals to, and why?"** Marketing's competitor list and sales' loss list are different lists; the loss list is the one buyers are actually comparing against. Also ask whether the real alternative is "do nothing" or "build in-house" — if so, note it, because category queries will surface it.

## 2. Buyer reality — better-with, shapes `query_grid.json`

The default grid works, but its biggest failure mode is queries written in vendor vocabulary. Buyers don't ask "best {category} tools" — they describe a problem. Collect:

- **2–4 distinct asker personas** (economic buyer, end user, procurement). Each becomes a `buyer_query_context` variant worth its own query.
- **Real buyer language**: questions pulled from sales-call transcripts, SDR objection docs, support tickets, and the client's G2/review phrasing. Add the best 2–3 as category-specific queries in the grid.
- **The money queries**: which 3–5 questions map to actual deals. Weight these in the report — a #1 rank on a query nobody commercially asks is a vanity finding.

## 3. Ground truth — required before trusting accuracy grades

The rubric grades **factual accuracy** (criterion 1) and **freshness** (criterion 4). Without a source of truth from the client, the grader can only catch errors it happens to recognize. Collect a one-page fact sheet and save it as `config/ground-truth.md`:

```markdown
# Ground Truth — {brand}
## What it is / does        (2-3 sentences, and what it explicitly does NOT do)
## Pricing model            (structure, not necessarily numbers)
## Integrations             (the ones buyers ask about)
## Security / compliance    (SOC 2, HIPAA, etc. — only what's certified today)
## Notable customers        (publicly referenceable only)
## Company facts            (founded, HQ, funding stage, rough headcount)
## Stale-history list       (see below)
## Claims constraints       (see below)
```

- **Stale-history list**: old names, rebrands, acquisitions, killed products, old pricing. Models carry stale training data — the most common audit finding is a model confidently describing the client as of two years ago. You can only flag "stale" if the client tells you what changed, and when.
- **Claims constraints**: what the client can and cannot legally or contractually say (critical in regulated categories like healthcare). A model paraphrasing the brand into an unapproved claim is a risk finding, not a good mention.

## 4. Competitive context — better-with, fills `intel/`

Existing battlecards, win/loss notes, and objection-handling docs, dropped into `intel/<competitor-slug>/` at the repo root (one folder per competitor). The perception scorer doesn't read these, but the reporter's recommendations get much sharper when "the models frame you as X" can be checked against "and your battlecard says you win on Y."

## 5. Positioning and voice — better-with, fills `brand-pack/`

The client's positioning doc, messaging hierarchy, and ICP definitions → `brand-pack/` at the repo root (`positioning.md`, `icps/`). This is the baseline the audit measures drift against: the interesting finding is rarely "the model described you wrong," it's "the model described you accurately *as of your old positioning*."

## 6. Outcomes and scope — better-with, shapes the report

- **The decision this audit informs.** Content investment? Competitive response? Rebrand validation? The reporter's recommendation section should be written toward that decision, so get it before the run, not after.
- **Measurement access**, if the engagement goes beyond a one-shot audit: Google Search Console, analytics that can segment AI referral traffic (chatgpt.com, perplexity.ai referrers), and CRM "how did you hear about us" data. This connects "you rank #3" to "and here's whether it shows up in pipeline."
- **Markets, languages, segments.** An English/US-only grid for a client doing 40% of revenue in EMEA is an instrument error, not an audit.

---

## Minimum viable intake

| Engagement | Need |
|---|---|
| Smoke run / pipe check | Section 1 only |
| First full audit | Sections 1 + 3 (never report accuracy or freshness grades without ground truth) |
| Paid engagement / repeat audits | All six |

## Where everything lands

```
agents/ai-brand-auditor/config/
├── brand.json          ← section 1
├── query_grid.json     ← section 2 (add category-specific queries)
├── ground-truth.md     ← section 3 (per client; gitignore if confidential)
└── rubric.md           (unchanged — but grader should be pointed at ground-truth.md)

repo root:
├── brand-pack/         ← section 5
└── intel/<competitor>/ ← section 4
```

**Confidentiality rule:** client-provided material (ground truth, battlecards, positioning) never gets committed to a public repo and never feeds any published sample output. Same rule as keys: it lives on the machine, not in git history.
