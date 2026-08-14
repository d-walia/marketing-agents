# Account Intelligence Agent

Builds a clean, enriched total-addressable-market table in [Clay](https://clay.com): companies, firmographics no B2B database sells, decision-maker contacts, and verified work emails, with Claude driving the Clay UI through the browser. First implementation: US health systems for revenue-cycle-management (RCM) sales.

This is the workflow a GTM engineer or Clay consultant builds first for every client, automated end to end: seed list → provider enrichment → AI research columns → contact sourcing → email waterfall.

## What it produced (first run, Aug 2026)

Two linked Clay tables in the workspace:

| Table | Contents |
|---|---|
| `health-system-seed-list` | 185 US health systems (name, domain, state, type) imported from the seed CSV in `seed-data/`, enriched on a 10-row test slice |
| `Revenue Cycle VPs Directors` | 71 revenue-cycle decision-makers sourced from those companies, email waterfall run on a 10-row test slice |

Test-slice results:

- **Enrich Company** (1 credit/row): 10/10 hit rate. Normalized name, website, employee count.
- **Claygent bed count** (~2 credits/row): 9/10. Kaiser 13,098; HCA 50,550. The one miss returned `not found` rather than a guess, by prompt design.
- **Claygent EHR vendor** (~3 credits/row): 10/10, spot-check accurate. HCA→MEDITECH, Ascension/Tenet/CHS→Oracle Health (Cerner), nonprofits→Epic.
- **Work Email waterfall** (11 providers, ~3 credits/row): 8/10 verified-format emails on first pass.

Total spend: ~90 credits of a 200-credit free plan, ~80 held in reserve.

## Why it's built this way

**Identifiers in, attributes enriched.** The seed CSV has two real columns (name and domain; state and type ride along free). Everything else is an enrichment column. Hand-researching CSV columns is the beginner mistake this workflow removes.

**Domain, not name, as the join key.** "Ascension" mismatches; `ascension.org` doesn't. The CSV ships domains so no credits are spent resolving them.

**Filters before waterfalls.** Credits burn per provider call, not per completed row. The expensive columns (Claygent, email waterfall) only run on rows that pass the cheap filters. On a 200-credit plan that's the difference between a working pipeline and an empty balance: running both Claygent columns across all 185 rows would have cost ~925 credits.

**Auto-run off, everywhere.** Table-level and column-level. Every credit spend is an explicit "run N rows" action. This is also the right client posture: prove the pipeline on a 10-row slice, then buy credits to scale the same columns.

**Claygent for what databases can't sell.** Staffed beds and EHR vendor aren't in any B2B data product, but they are in the AHA directory, press releases, and job postings. AI research columns with a strict output contract (`integer, no commas`, `vendor name only`, `not found` when unknown) turn the open web into a structured column. A confident wrong number is worse than a miss, so the prompts forbid guessing.

**Companies and people in separate linked tables.** One row per contact, joined back to the company table. This is the standard consultant pattern, and it makes the next layer (signal plays) cheap to add.

## The Claygent prompts

Bed count (model: Clay Neon):

> Find the number of staffed beds operated by the health system {{company_name}} (website: {{domain}}). Search the American Hospital Association directory, the system's own website, and recent press releases or fact sheets. Return only the total staffed or licensed bed count across the whole system as an integer with no commas. If sources conflict, use the most recent figure. If you cannot find a number, return exactly: not found

EHR vendor (model: Clay Neon):

> Identify the primary enterprise EHR (electronic health record) vendor used by the health system {{company_name}} (website: {{domain}}). Determine which enterprise EHR platform the system runs hospital-wide: Epic, Oracle Health (Cerner), MEDITECH, Altera, TruBridge, or another vendor. Check the system's press releases, news coverage of EHR implementations or go-lives, and the system's own job postings that name the EHR. Return only the vendor name. If the system is mid-migration, return the vendor it is migrating to. If you cannot determine it, return exactly: not found

Contact sourcing filter (Find People, scoped to the company table): job title similar to `VP Revenue Cycle`, `Director of Revenue Cycle`, `VP Patient Financial Services`. 72 matches across 10 systems.

## Structure

```
agents/account-intelligence-agent/
├── SKILL.md      # front door — how Claude drives Clay to run or extend this workflow
├── README.md     # this file
└── seed-data/
    └── health-system-seed-list.csv   # 185 US health systems: company_name, domain, state, type
```

## How to run

Ask from any Claude Code session with Chrome access, logged into Clay:

```
Extend the Clay TAM table — run the enrichments on the next 25 rows
```

[`SKILL.md`](SKILL.md) carries the operating rules (credit discipline, auto-run policy, prompt contracts) so any session can pick the workflow up cold. To install as an auto-triggering skill:

```bash
ln -s ~/github/marketing-agents/agents/account-intelligence-agent ~/.claude/skills/account-intelligence-agent
```

## Next layers (designed, not yet built)

1. **ICP-fit formula column** (free): beds ≥ 300 AND type ≠ critical access; gates the expensive columns
2. **Signal play**: Clay job-postings integration watching these domains for titles like "denials," "prior authorization," "underpayment analyst." A health system hiring denials analysts is signaling RCM pain; new match → enrich → AI first-line referencing the posting
3. **Export views**: "Ready for outreach" (valid email + ICP pass) and "Needs manual research"
