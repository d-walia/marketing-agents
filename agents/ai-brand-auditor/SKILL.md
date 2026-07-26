---
name: ai-brand-auditor
description: Run a full AI brand audit (GEO/AEO) — measure how Claude, ChatGPT, and Gemini perceive and recommend a brand, then produce a scored, graded, decision-ready report. Use whenever Dhruv asks to audit a brand's AI visibility, run a GEO or AEO audit, check whether a brand shows up in AI answers, measure share of voice in LLMs, re-run or re-score an existing audit, or asks "how do models talk about <brand>?" — and also when he names a brand and asks how AI search represents it versus competitors.
---

# AI Brand Auditor

Measure how AI models perceive and recommend a brand: does it surface when buyers ask category questions, at what rank, framed how, and how accurately. This skill is the front door to a four-subagent pipeline — it decides what needs to run, dispatches the subagents in order, and reports the outcome.

**Repo root:** `~/github/marketing-agents`. All paths below are relative to it. Run from the repo root so the `.claude/agents/` subagent definitions load.

## Why the pipeline is split

Four subagents, each owning one step, handing off through files:

| Subagent | Owns | Must not |
|---|---|---|
| `audit-query-runner` | Collecting raw model responses | Interpret anything |
| `audit-perception-scorer` | Routing, rank, share of voice, framing | Judge factual accuracy |
| `audit-rubric-grader` | Rubric grades, blind to the scorer | Read `scores.json` / `scores.md` |
| `audit-reporter` | Synthesis + recommendations | Do new analysis of raw data |

The scorer and grader are independent **on purpose** — one measures visibility, the other measures representation quality, and their disagreements are findings. Never collapse them into one step to save a turn. This separation is what caught a truncation artifact that read as a real (and damning) 0% mention rate; see the README's "Field-tested" section.

## Inputs

- **Brand** (required). If it isn't already the brand in `agents/ai-brand-auditor/config/brand.json`, update that file first — brand, category, `category_short`, `buyer_query_context`, and 3 competitors. Confirm the config in one line before spending API calls.
- **Scope** (optional): which providers (`anthropic,openai,gemini`), or `--smoke` for a cheap pipe-check.
- **Existing runs**: check `agents/ai-brand-auditor/runs/` first. If the request is "re-score" or "re-report," reuse the newest run directory instead of collecting again — collection is the only step that costs money.

## Procedure

1. **Confirm config.** Read `config/brand.json`. State brand, category, competitors, and models in one line. If the brand differs from the request, edit the config before proceeding.
2. **Collect** — dispatch `audit-query-runner`. It returns a run ID, a success/failure count, and the run directory path. That path is the handoff artifact for both analysts.
   - If the runner reports gateway errors (401/`AiGatewayError`), stop and surface it — never bypass the gateway silently.
   - If it reports partial failures, continue, but carry the list of missing provider/query pairs forward.
3. **Analyze — dispatch both analysts on the same run directory.** `audit-perception-scorer` and `audit-rubric-grader` are independent and have no shared state, so launch them in parallel in a single message. Pass each the run directory path and nothing else. Do not relay the scorer's findings to the grader, even in passing.
4. **Report** — once `scores.json`, `scores.md`, and `grades.md` all exist, dispatch `audit-reporter` on the run directory. It writes `report.md`.
5. **Close out** — report the run directory path and the reporter's verdict paragraph verbatim. Then offer, don't silently do: publish the report to `outputs/`, or pull the single most actionable finding into chat.

## Cost discipline

Every call routes through the Cloudflare AI Gateway and is attributable in the dashboard — an audit run has a visible price. So:

- Default to a **smoke run first** (`--smoke`, 1 query, capped tokens) when anything about the setup is new: a new brand, changed config, changed env, or a first run in a fresh shell. Collect the full grid only once the pipe is proven.
- Never re-collect to fix an analysis problem. Re-scoring and re-reporting are free; re-collecting is not.

## Instrument-error rule

Before treating any dramatic number as a finding, rule out measurement artifact. A shocking result — 0% mentions, every response identical, uniformly one-line answers — is more often the harness than the brand. Check raw response lengths and the manifest's failure list first. Report the artifact, fix the harness, re-collect; do not report the number.

If the two analysts independently flag the same anomaly, that is near-conclusive evidence of an instrument problem, not a brand problem.

## Calibration

A good run has responses from all three providers across all four query types, zero ungradeable files, and a report where every quantitative claim traces to `scores.json` or `grades.md`. If a provider drops out entirely (quota, retired model), say so in the handoff and mark that model's column absent rather than reporting a low score that's really a missing score.

## Auditing a different brand

Edit `config/brand.json` only. The query grid uses placeholders (`{brand}`, `{competitor_0}`, …) and adapts automatically; add category-specific queries to `config/query_grid.json` when the category has evaluation questions the generic grid misses.

## Setup

Requires the Cloudflare AI Gateway env (`*_BASE_URL`, provider keys, `CF_AIG_TOKEN`), documented in the [`ai-architecture`](https://github.com/d-walia/ai-architecture/tree/main/cloudflare-ai-gateway) repo. Keys live in `~/.marketing-agents.env`, never in this repo. Full architecture writeup and known gotchas: [`README.md`](README.md).
