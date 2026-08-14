# Site Auditor — Technical + AEO Crawl

Crawls a site into a structured page corpus, runs deterministic technical and AEO checks over it, and has an analyst subagent turn the findings into a prioritized report. The Screaming Frog job, plus a question Screaming Frog never asks: **can answer engines read this site at all?**

## The design decision that matters

The crawler is a **corpus builder, not an issue finder**. `crawl_site.py` fetches pages and stores one JSON record each — structure, metadata, links, optionally full text. Every audit finding is computed *downstream* by `check_site.py` as a free re-runnable read of that corpus, and interpreted by the `site-audit-analyst` subagent.

Screaming Frog couples crawling to auditing; decoupling them is what makes this dual-use. Pointed at your own site, the corpus answers layer-1 questions (technical health). Pointed at a competitor with `--full-text`, the same corpus is layer-4 raw material — content inventory, gaps, positioning language — for a future analysis agent that reads two corpora and diffs them. One crawler, two layers.

## What the checks cover

**Technical (per page):** broken internal links, redirect chains and redirected links, missing/duplicate/overlong titles and meta descriptions, missing/multiple H1s, thin content, orphan pages, noindex-in-sitemap conflicts, canonical mismatches, images without alt text, pages without structured data.

**AEO readiness (site-level) — the differentiator:**
- **AI-crawler access** — robots.txt verdicts for 13 AI bots (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot, …). A site that blocks ClaudeBot cannot be read, and therefore cannot be cited, by that engine. Sites block these by default more often than their marketing teams know.
- **Server-rendered content** — the crawler doesn't render JS, and neither do most AI crawlers. A JS-heavy site shows up as wholesale thin content: for Google that's a measurement caveat, for AEO it *is* the finding.
- **Structured data** — JSON-LD coverage and whether answer-engine-relevant types (FAQPage, HowTo, Article, Product, Organization) exist anywhere.
- **llms.txt** — presence check, reported as an emerging convention, not a standard.

## Structure

```
agents/ai-brand-auditor/site-auditor/
├── SKILL.md                    # front door — crawl, check, analyze, report
├── scripts/
│   ├── crawl_site.py           # stdlib-only polite crawler → page corpus
│   ├── check_site.py           # deterministic checks → issues.json (no network, free to re-run)
│   └── parse_gsc_links.py      # GSC Links export → own-site backlink summary
└── runs/<domain>/<timestamp>/  # created per crawl (gitignored)
    ├── pages.jsonl             # the corpus: one record per page
    ├── crawl-summary.json      # params, status counts, AI-bot access, llms.txt
    ├── sitemap-urls.json       # what the sitemap claims exists
    ├── robots.txt              # as fetched
    ├── issues.json             # ← check_site.py output
    ├── links-summary.json      # ← parse_gsc_links.py output (optional)
    └── report.md               # ← site-audit-analyst output
```

The analyst subagent lives at the repo root in [`.claude/agents/site-audit-analyst.md`](../../../.claude/agents/site-audit-analyst.md).

## How to run

Just ask, from the repo root: `Audit dw-digital-consulting.com` — [`SKILL.md`](SKILL.md) drives the steps. Install by symlinking:

```bash
ln -s ~/github/marketing-agents/agents/ai-brand-auditor/site-auditor ~/.claude/skills/site-auditor
```

Direct script usage:

```bash
python3 scripts/crawl_site.py example.com                    # crawl (300 pages, 1 req/s)
python3 scripts/crawl_site.py example.com --full-text        # + store text (layer-4 corpus)
python3 scripts/check_site.py                                # checks on the newest run
python3 scripts/parse_gsc_links.py ~/Downloads/links-export/ --run runs/example.com/<ts>
```

No keys, no gateway, no cost: the crawler talks only to the audited site, and analysis runs inside the Claude subscription.

## Politeness

Identifying user agent, robots.txt respected (disallowed URLs are recorded as skipped, and AI-bot rules are *reported* either way), 1 request/second default, 300-page default cap. Crawling a competitor's public marketing site at that rate is ordinary crawler traffic; keep it that way — never crank `--delay` down on a site you don't own.

## Honest boundaries

- **Search volumes: not here.** Google Suggest expansion lives in the SEO monitor; actual volume numbers require paid data. Free approximations: Keyword Planner ranges (free Ads account), Google Trends for relative demand.
- **Competitor backlinks: not here.** Own-site backlinks come free from the GSC Links export (`parse_gsc_links.py` — works on anything you or a client can verify, or a CSV a client emails you). A backlink *index* cannot be self-built.
- **The upgrade trigger for both:** first paid client audit that needs competitor backlink data or precise volumes → DataForSEO pay-as-you-go (~$50 one-time deposit, pennies per audit; verify current rates before depositing — they adjusted ~20% in July 2026). Deliberately not built until then.
- **No JS rendering.** Server HTML only, which doubles as the AEO-relevant view. Trigger for a Playwright fallback: the first client site that's genuinely client-rendered.

## Gotchas learned elsewhere in this repo, applied here

- Cloudflare 403s Python's default urllib user-agent (`error code: 1010`) — the crawler sends an identifying UA of its own.
- Dramatic numbers are the instrument until proven otherwise: "every page is thin" means a JS-rendered site; "no sitemap" usually means a non-standard location. Same rule as the brand auditor's truncation incident.
