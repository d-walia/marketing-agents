---
name: seo-performance-monitor
description: Measure SEO performance and find where to grow — analyze existing pages from a Search Console export (striking distance, CTR shortfalls, content decay, cannibalization), track position-weighted share of voice against competitors, and discover new keyword and content territory via Google Suggest. Use whenever Dhruv asks about SEO, organic traffic, search rankings, keyword research, what content to write next, why traffic dropped, how a site is performing in search, or share of voice in Google — and also when he names a domain and asks how it's doing organically.
---

# SEO Performance Monitor

Three questions, three data sources, one report:

| Question | Source | Needs a key? |
|---|---|---|
| How are my existing pages doing? | Search Console CSV export | **No** |
| Am I winning or losing share against competitors? | SearchAPI.io or SerpApi | Yes, free tier |
| What should I publish next? | Google Suggest autocomplete | **No** |

Two of the three need no credentials at all, so a useful run is always possible.

## Inputs

- **Domain** (required). Read `config/site.json` for the default; any domain can be passed instead — this works on client and prospect sites, not just Dhruv's.
- **Search Console export** (optional but the highest-value input). Ask for it if the site is one he controls; if he doesn't have it handy, tell him exactly how: Search Console → Performance → set the date range → Export → CSV. **Ask for the export with both Queries and Pages dimensions** — cannibalization analysis is impossible without page-level data, and that is often the most actionable finding.
- **A second, older export** (optional) — unlocks decay analysis, which is usually where the urgent problems are.
- **No export available?** Say so plainly and run the opportunity half. Never fabricate performance data for a site you have no data for.

## Pipeline

### 1. Performance — what you already have

```bash
python3 scripts/analyze_gsc.py <current.csv> [--previous <older.csv>] --site <domain> --out <run-dir>
```

Produces four analyses. Read `performance.md`, and interpret rather than restate it:

- **Striking distance (positions 8-20)** — almost always the highest-ROI work. The page already ranks; it needs strengthening, not creating. Lead with this when it's non-empty.
- **CTR shortfalls** — ranks well, under-clicked. This is a *title and meta description* problem. Do not recommend backlinks or new content for these; recommend a rewrite, and draft the replacement title where it's obvious.
- **Cannibalization** — two pages splitting one query. The fix is consolidate-and-redirect or deliberately differentiate; say which, and why, per case.
- **Decay** (needs two periods) — treat a large position drop differently from a click drop at stable position. The first is a ranking loss; the second usually means the SERP changed around you (an AI overview appeared, a competitor took the snippet).

### 2. Share of voice — where you stand

```bash
python3 scripts/fetch_serp.py --config config/site.json --out <run-dir>
python3 scripts/fetch_serp.py --config config/site.json --dry-run   # price it first
```

Costs one credit per keyword on whichever provider is configured (SearchAPI.io's free tier is 100 one-time; SerpApi's is 250/month). **Always `--dry-run` first if the set is over ~30 keywords or the credit balance is unknown**, and tell him the cost before spending. Share of voice is position-weighted, not presence-based: appearing at #9 is worth a fraction of #1, and the report reflects that.

Two parts of this output matter most:
- **"Who actually owns these SERPs"** — domains ranking that aren't in the tracked competitor list. These are real competitors he hasn't accounted for; call them out explicitly.
- **SERP features** — where an AI overview or featured snippet appears, organic CTR is suppressed. A #1 ranking under an AI overview is worth less than it looks, and that reframes what "winning" that keyword means.

### 3. Opportunity — where to go next

```bash
python3 scripts/expand_keywords.py --config config/site.json --out <run-dir>
python3 scripts/expand_keywords.py --seeds "topic one" "topic two" --depth 2   # wider sweep
```

Free, no key. Every phrase returned is one Google's autocomplete actually serves, so demand is demonstrated rather than estimated. Phrases flagged 🆕 introduce vocabulary the seeds didn't contain — that's where genuinely new territory hides.

Cross-reference against the Search Console export when one exists: a phrase with demand that appears nowhere in his impressions is a true gap. **That intersection is the single most valuable output of this skill** — it is the difference between "here are some keywords" and "here is demand you are invisible for."

## The discipline that makes this useful

Keep the two halves separate until the very end. **Analyze what exists before looking at what's missing**, and weigh them independently.

SEO advice defaults to "publish more content" because it is the easiest recommendation to make and the hardest to hold anyone to. It is usually wrong: fixing a title on a page ranking #4 with 4,000 impressions beats publishing a new post that will take six months to rank. When both a fix and a new-content recommendation compete for the top slot, **the fix wins unless the opportunity is materially larger** — and say why in one line.

## Verification rules

- Estimated click gains come from an industry-average CTR curve. Present them as **relative priorities, never forecasts**, and say so once in the report.
- Never invent search volume. This toolchain has no volume data — it has demonstrated demand (Suggest) and actual impressions (Search Console). If volume is genuinely needed, say it isn't available rather than estimating.
- Distinguish measured from inferred. Impressions, clicks, and positions are measured. "This dropped because Google rolled out an update" is inference — label it.
- If a SERP call fails, report it as a gap. A share-of-voice number computed from a partial keyword set, presented as complete, is a wrong number.
- Small sample sizes lie. Under ~100 impressions on a row, note it rather than building a recommendation on it.

## Outputs

Write to `<repo>/outputs/seo/<domain>/<YYYY-MM-DD>/`, where `<repo>` is `$MARKETING_AGENTS_ROOT` if set, otherwise `~/github/marketing-agents`:

- `performance.md` — from analyze_gsc.py
- `share-of-voice.md` — from fetch_serp.py
- `keywords.md` — from expand_keywords.py
- `action-plan.md` — **the deliverable you write**, synthesizing all three

`action-plan.md` is the point of the run. Everything else is evidence. Structure:

```
# SEO action plan — <domain>, <date>
## The one thing            ← single highest-value action, with the number behind it
## Fix first (existing pages)  ← ranked, each with: page, problem, specific fix, est. gain
## Defend                   ← what's decaying and what to do before it's gone
## Build next (new content)  ← only what beats the fixes above on expected value
## Watch                    ← share-of-voice shifts, new SERP competitors, feature encroachment
```

Every item carries the evidence — impressions, position, delta — inline. A recommendation without its number is an opinion.

## After the run

Offer, don't silently do:
- Save this run as the baseline for next time (the run directory is already dated, so comparison is automatic next run).
- Draft the actual title/meta rewrites for the top CTR shortfalls — that's a 20-minute job with immediate payoff.
- Add newly-discovered competitor domains to `config/site.json`.

## Calibration

- **Brand-new site, almost no data** (dw-digital-consulting.com's current state): say so directly. Skip performance analysis, run opportunity discovery, and frame the output as a content plan rather than an optimization plan.
- **Client or prospect site, no Search Console access**: share of voice and keyword discovery still work fully. This is the standard pre-sales configuration and it produces a genuinely useful pitch artifact.
- **Established site with history**: the full pipeline, and decay analysis is usually where the urgency is.
