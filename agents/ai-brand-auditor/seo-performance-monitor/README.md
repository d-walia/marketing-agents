# SEO Performance Monitor

Three questions every SEO program has to answer, each with its own data source:

| Question | Source | Key needed | Cost |
|---|---|---|---|
| How are my existing pages doing? | Search Console CSV export | **No** | Free |
| Am I winning or losing against competitors? | SearchAPI.io *or* SerpApi | Free tier | 100 one-time / 250 per month |
| What should I publish next? | Google Suggest | **No** | Free |

Two of the three need no credentials, so a useful run is always possible — and
the whole thing stays inside free tiers indefinitely.

## Why CSV instead of the Search Console API

The API needs OAuth, a Google Cloud project, and a consent screen. A CSV export
needs three clicks and works on **any property you or a client can open** —
including one where a client just emails you the export. Same data, no setup.
The analyzer also reads API JSON if automation is ever worth building.

## What it actually computes

Search Console tells you what happened; it doesn't tell you what to do. The
analyzer does the arithmetic that turns one into the other:

- **Striking distance (positions 8-20)** — usually the cheapest traffic
  available. The page already ranks; rank 11 → 8 crosses onto page one. Each
  row is priced by clicks gained if it reached position 3.
- **CTR shortfalls** — ranking well but under-clicked for that position. That's
  a title/meta problem, not a ranking problem: the fix is a rewrite, not a
  backlink. Measured against an industry-average CTR-by-position curve.
- **Cannibalization** — two of your pages competing for one query, splitting
  signals so neither wins. Needs a query+page export.
- **Decay** — with a second export, what's quietly declining, what dropped out
  entirely, and what's growing. A position drop and a click drop at stable
  position are different diagnoses, and the report separates them.

Share of voice is **position-weighted**, not presence-based: appearing at #9 is
worth a fraction of #1, and the arithmetic reflects that. The report also names
domains ranking across your keyword set that you never listed as competitors —
usually the most uncomfortable and useful part of the output.

Keyword expansion buckets by **audience before intent**. Job-seeker queries
("consultant salary", "GTM engineer course") and off-market geographies get
their own sections rather than padding the buyer-intent count. A high-volume
phrase read by the wrong audience is worth less than nothing, because it looks
like an opportunity.

## Setup

Nothing to install — standard library only.

For share of voice, add whichever provider key you have to
`~/.marketing-agents.env` — the script auto-detects which one is present:

```
SEARCHAPI_KEY=...    # searchapi.io — 100 searches free, one-time
SERPAPI_KEY=...      # serpapi.com  — 250 searches/month, recurring
```

Then point `config/site.json` at whichever domain you're analyzing.

## How to run

From the repo root in Claude Code, just ask — the `seo-performance-monitor`
skill triggers on requests like "how is the site doing in search" or "what
should I write about next."

Direct script use:

```bash
# Performance — no key needed
python3 scripts/analyze_gsc.py current.csv --previous last-quarter.csv --site example.com --out runs/latest

# Keyword discovery — no key needed
python3 scripts/expand_keywords.py --config config/site.json --out runs/latest
python3 scripts/expand_keywords.py --seeds "ambient ai scribe" --depth 2   # wider sweep

# Share of voice — SerpApi key; always price it first
python3 scripts/fetch_serp.py --config config/site.json --dry-run
python3 scripts/fetch_serp.py --config config/site.json --out runs/latest
```

To get the export: Search Console → Performance → set the date range → Export →
Download CSV. That yields a ZIP; `Queries.csv` inside it is the input.

`templates/` holds a copy-paste email for requesting this from a client (no
account access required) and `Queries-EXAMPLE.csv`, a realistic sample showing
the exact five columns Google produces. Note that the standard UI export gives
queries and pages as *separate* files, so cannibalization detection needs either
Search Console API access or a page-by-page export — the analyzer says so rather
than skipping silently.

## Notes and limits

- **No search volume, anywhere.** This toolchain has demonstrated demand
  (Suggest) and actual impressions (Search Console), which are better signals
  than a third-party volume estimate. It never estimates volume, and neither
  should the report.
- **Estimated click gains are relative priorities, not forecasts.** They come
  from an average CTR curve; a real curve varies by SERP features, brand
  strength, and intent.
- **Ambiguous seeds pull in the wrong category.** "GTM engineering" surfaces
  Google Tag Manager and SAP Global Trade Management queries. Check the first
  run's output and tighten seeds accordingly — that's a feature of Suggest
  being honest about what people search, not a bug.
- **SERP credits are finite.** One per keyword per run, on either provider.
  `--dry-run` prices a set and names the detected provider before spending.
- Run outputs are gitignored — SEO data for client sites shouldn't land in the repo.
