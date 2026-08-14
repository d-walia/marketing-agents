---
name: site-auditor
description: Crawl a website into a structured corpus and audit it — technical SEO health (broken links, metas, titles, redirects, orphans, thin content) plus AEO readiness (can AI crawlers get in, is content server-rendered, structured data, llms.txt). Use whenever Dhruv asks to audit a site, run a technical SEO audit or site health check, crawl a site, check AEO or AI-crawler readiness of a domain, check whether AI bots are blocked, or asks "what's wrong with [some site]" — his own, a client's, or (crawl politely) a competitor's.
---

# Site Auditor

Crawl a site into a page corpus, run deterministic checks over it, and have an analyst turn the findings into a prioritized report. Collection and checks are stdlib scripts (zero tokens, zero cost); judgment is one subagent at the end.

**Repo root:** `$MARKETING_AGENTS_ROOT` if set, otherwise `~/github/marketing-agents`. Paths below are relative to `agents/ai-brand-auditor/site-auditor/`. Run from the repo root so `.claude/agents/site-audit-analyst.md` loads.

## Design rule

The crawler builds a corpus; it finds nothing. Checks are downstream reads of the corpus; the analyst interprets but never re-counts. Keep those layers separate — the corpus is what makes the same crawl reusable for competitor content analysis later (`--full-text`).

## Procedure

1. **Confirm target and scope.** State domain and page cap in one line. Defaults: 300 pages, 1s delay. For a site that isn't Dhruv's or a client's, keep the default delay or slower — the crawler identifies itself and respects robots.txt, and we stay polite on other people's servers.
2. **Crawl:**
   ```bash
   python3 agents/ai-brand-auditor/site-auditor/scripts/crawl_site.py DOMAIN --max-pages 300
   ```
   Add `--full-text` when the corpus will also feed content analysis (competitor crawls: always). Watch the closing lines: blocked AI bots and a hit page cap are worth relaying immediately.
3. **Check:**
   ```bash
   python3 agents/ai-brand-auditor/site-auditor/scripts/check_site.py agents/ai-brand-auditor/site-auditor/runs/DOMAIN/TIMESTAMP
   ```
   Free to re-run forever; never re-crawl to fix a checks problem.
4. **Backlinks (optional, own/client sites only):** if Dhruv has a GSC Links export for the property, parse it into the run so the analyst can use it:
   ```bash
   python3 agents/ai-brand-auditor/site-auditor/scripts/parse_gsc_links.py EXPORT_DIR --run agents/ai-brand-auditor/site-auditor/runs/DOMAIN/TIMESTAMP
   ```
   If he doesn't, skip silently — offer it only when the audited site is one he or a client controls.
5. **Analyze** — dispatch `site-audit-analyst` with the run directory path and nothing else. It writes `report.md`.
6. **Close out** — relay the report path, the verdict paragraph verbatim, and the top fix.

## Calibration

- A dramatic number is the harness until proven otherwise (same instrument-error rule as the brand auditor): every page thin usually means a JS-rendered site, not a content crisis — though for AEO that *is* the finding, since AI crawlers mostly don't render JS either. Zero sitemap URLs usually means a non-standard sitemap location, not a missing sitemap.
- `corpus_partial: true` in issues.json → all counts are floors; the report must say so.
- Search volumes and competitor backlinks are out of scope by design — own-site backlinks come from the GSC export, and the paid upgrade path is documented in the README. Don't improvise a replacement with web searches.

## Setup

None. No keys, no gateway — the crawler talks only to the audited site.
