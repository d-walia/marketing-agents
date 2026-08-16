# Site Auditor: Technical + AI-Readability Crawl

Crawls a site into a structured page corpus, runs technical and AI-readability checks over it, and has an analyst subagent turn the findings into a prioritized report. It does the Screaming Frog job, plus a question Screaming Frog doesn't ask: can answer engines read this site at all?

## Design

The crawler builds a corpus; it finds nothing. `crawl_site.py` fetches pages and stores one JSON record each: structure, metadata, links, optionally full text. Every finding is computed downstream by `check_site.py` as a free, re-runnable read of that corpus, then interpreted by the `site-audit-analyst` subagent.

Decoupling crawl from audit is what makes the corpus reusable. Pointed at your own site, it answers technical-health questions. Pointed at a competitor with `--full-text`, the same corpus becomes raw material for the planned Competitor Content Analyzer: content inventory, gaps, positioning language. One crawler, two layers of the stack.

## What the checks cover

**Technical, per page:** broken internal links, redirect chains and redirected links, missing/duplicate/overlong titles and meta descriptions, missing or multiple H1s, thin content, orphan pages, noindex-in-sitemap conflicts, canonical mismatches, images without alt text, pages without structured data.

**Whether AI models can reach and read the site:**

- **AI-crawler access.** robots.txt verdicts for 13 AI bots (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot, and more). A site that blocks ClaudeBot can't be read by that engine, so it can't be cited by it either. Sites block these more often than their marketing teams know.
- **Server-rendered content.** The crawler doesn't render JavaScript, and neither do most AI crawlers. A JS-heavy site shows up as wholesale thin content. For Google that's a measurement caveat; for AI models it is the finding.
- **Structured data.** JSON-LD coverage, and whether the types answer engines use (FAQPage, HowTo, Article, Product, Organization) exist anywhere on the site.
- **llms.txt.** Presence check, reported as an emerging convention rather than a standard.

## Structure

```
agents/site-auditor/
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

The analyst subagent lives at the repo root in [`.claude/agents/site-audit-analyst.md`](../../.claude/agents/site-audit-analyst.md).

## How to run

Ask from the repo root: `Audit dw-digital-consulting.com`. [`SKILL.md`](SKILL.md) drives the steps. Install by symlinking:

```bash
ln -s ~/github/marketing-agents/agents/site-auditor ~/.claude/skills/site-auditor
```

Direct script usage:

```bash
python3 scripts/crawl_site.py example.com                    # crawl (300 pages, 1 req/s)
python3 scripts/crawl_site.py example.com --full-text        # + store text (layer-4 corpus)
python3 scripts/check_site.py                                # checks on the newest run
python3 scripts/parse_gsc_links.py ~/Downloads/links-export/ --run runs/example.com/<ts>
```

No keys, no gateway, no cost. The crawler talks only to the audited site, and analysis runs inside the Claude subscription.

## Politeness

Identifying user agent, robots.txt respected (disallowed URLs are recorded as skipped; AI-bot rules are reported either way), 1 request per second, 300-page cap by default. Crawling a competitor's public marketing site at that rate is ordinary crawler traffic. Keep it that way: never lower `--delay` on a site you don't own.

## Limits

- **No search volumes.** Google Suggest expansion lives in the SEO monitor; real volume numbers require paid data. Free approximations: Keyword Planner ranges (free Ads account) and Google Trends for relative demand.
- **No competitor backlinks.** Own-site backlinks come free from the GSC Links export (`parse_gsc_links.py` works on any property you or a client can verify, including a CSV a client emails you). A backlink index can't be self-built.
- **The upgrade trigger for both:** the first paid client audit that needs competitor backlinks or precise volumes. At that point, DataForSEO pay-as-you-go (about a $50 one-time deposit, pennies per audit; verify current rates first, since they moved ~20% in July 2026). Not built until then.
- **No JS rendering.** Server HTML only, which is also what AI crawlers see. The trigger for a Playwright fallback: the first client site that's genuinely client-rendered.

## Gotchas

- Cloudflare 403s Python's default urllib user-agent (`error code: 1010`); the crawler sends an identifying UA of its own.
- Dramatic numbers are the instrument until proven otherwise. "Every page is thin" means a JS-rendered site; "no sitemap" usually means a non-standard location. Same rule as the brand auditor's truncation incident.
