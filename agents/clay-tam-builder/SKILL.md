---
name: clay-tam-builder
description: Build or extend a TAM (total addressable market) table in Clay — seed list import, enrichment waterfalls, Claygent research columns, contact sourcing, and email waterfalls — with Claude driving the Clay web UI through the browser. Use whenever Dhruv asks to build an account list in Clay, extend or re-run the health-system TAM table, add enrichment columns, source contacts, or run email waterfalls in Clay. Also trigger on "run the Clay workflow", "enrich more rows", or requests to adapt this workflow to a new vertical.
---

# Clay TAM Builder

Drive Clay's web UI (app.clay.com, Chrome, Dhruv's logged-in session) to build or extend an enriched TAM table. The first build (Aug 2026) lives in the workspace as `health-system-seed-list` (185 US health systems) + `Revenue Cycle VPs Directors` (71 contacts); `seed-data/health-system-seed-list.csv` is the seed. Full design rationale in [README.md](README.md).

## Operating rules (non-negotiable)

1. **Check the credit balance first** (top bar) and state it to Dhruv before any run. Free plan = 200/month. Announce projected spend before each run ("this costs ~N credits, leaving ~M").
2. **Auto-run stays OFF** — table-level (toolbar toggle → "Manual") and column-level (Run settings in every new column). If a new table or column defaults it on, turn it off before saving.
3. **Test slice before scale.** New columns run on 10 rows first via the column header ▶ → "Run first 10 rows". Report hit rate to Dhruv before running more.
4. **Filters before waterfalls.** Never run Claygent or email waterfalls on rows that haven't passed the cheap gates (provider enrichment hit, ICP formula). Formula columns are free — use them as gates.
5. **Import is free; enrichment isn't.** Never accept the wizard's offer to attach enrichments (Work Email etc.) at import time — that runs on every row. Add columns in-table and run slices.
6. **Claygent prompts must have an output contract**: exact format ("integer with no commas", "vendor name only"), named sources to check, and a literal `not found` fallback. No guessing allowed. Insert table columns into prompts with `/` (company_name, domain).
7. **Waterfall order cheapest-first**, validation last, stop-at-first-valid on.

## The build sequence (for a new vertical or list)

1. Seed CSV: `company_name, domain` (+ optional `state`, `type`). Claude compiles it from public sources — never hand-research attributes that enrichment can fill. Dhruv must drag the CSV into Clay's import dialog himself (browser sandbox can't upload files).
2. Import → new table → auto-run off.
3. Enrich Company (Clay, 1/row) keyed on domain → 10-row test.
4. Claygent research columns for the attributes no database sells (for healthcare: staffed beds, EHR vendor — prompts in README.md) → 10-row test each.
5. ICP-fit formula column (free) gating on the enriched fields.
6. Find People scoped to the company table, title filters for the buyer persona, save to a new linked table (one row per contact), no import-time enrichments.
7. Work Email waterfall (Clay, ~3/row) → 10-row test → report hit rate.
8. Export views: "Ready for outreach" (valid email + ICP pass), "Needs manual research".

## UI mechanics that aren't obvious

- The post-import "More control over when cells run" modal's toggle is an illustration — the real auto-run switch is the toolbar "Auto-run" button.
- Claygent building: Tools panel → "Use AI" → describe the research task → Clay generates the optimized prompt and picks a model (Neon is right for structured web extraction; don't let it upsell to a deeper model for simple lookups).
- Find People: filters left, live preview right; the companies scope chip must say it's reading from the table, not all of LinkedIn. "Save to new table" (not "in this table") for one-row-per-contact.
- Column runs: header ▶ gives "Run first 10 rows" / "Run empty or out-of-date rows". The Save button on new columns has the same dropdown — "Save and don't run" is the safe default.
