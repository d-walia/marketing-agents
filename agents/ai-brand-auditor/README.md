# AI Brand Audit — Multi-Agent GEO Pipeline

Measures how AI models (Claude, ChatGPT, Gemini) perceive and recommend a brand: does it show up when buyers ask category questions, at what rank, framed how, and how accurately. The workflow is decomposed into four Claude Code subagents, each owning one step and handing off through files.

This folder is the home of the repo's whole GEO/AEO practice: the brand audit pipeline is the flagship, and two smaller sibling agents live alongside it (see [Sibling agents](#sibling-agents) below) covering the layers of the stack the pipeline itself doesn't — technical site health and traditional search performance.

## Why agents, and why these boundaries

The credibility of an audit depends on separation of concerns:

| Agent | Owns | Tools | Deliberately excluded |
|---|---|---|---|
| `audit-query-runner` | Collecting raw model responses | Bash, Read | Any interpretation — downstream agents must see data cold |
| `audit-perception-scorer` | Category routing, rank, share of voice, framing | Read, Write | Factual accuracy judgments; Bash (it never needs to execute anything) |
| `audit-rubric-grader` | Rubric-based quality grades | Read, Write | The scorer's outputs — it grades blind, so the two analyses are independent |
| `audit-reporter` | Synthesis + recommendations | Read, Write | New analysis of raw data — every claim must trace to the two upstream artifacts |

The scorer and grader are separate agents *on purpose*: one measures visibility, the other measures representation quality, and their disagreements (e.g. "mentioned everywhere but described inaccurately") are audit findings in themselves. A single agent doing both tends to smooth those tensions over.

## Field-tested

The first full audit run (2026-07) validated the architecture in a way no demo could. A harness bug truncated every Gemini response to fragments, which scored as "0% brand mentions on category queries" — a shocking headline that was pure instrument error. Both analysts caught it **independently**: the perception scorer flagged the responses as truncation artifacts, and the rubric grader — forbidden from reading the scorer's output — hit the same raw files cold and raised the identical flag. The harness was fixed, the grid re-collected, and the clean run *reversed* the finding: Gemini actually ranks the audited brand #1 on every category list. Same brand, same queries, opposite conclusion — the agent separation is the only reason the bad number never reached a report.

## Structure

```
agents/ai-brand-auditor/
├── SKILL.md              # the front door — orchestrates the four subagents
├── config/
│   ├── brand.json        # brand, category, competitors, models per provider
│   ├── query_grid.json   # 8 queries × 4 types (category, brand, comparison, use-case)
│   ├── rubric.md         # 5-criterion grading rubric (0–2 each)
│   └── client-intake.md  # what to collect from a client, and where each piece goes
├── scripts/
│   ├── run_queries.py    # stdlib-only; routes all calls through Cloudflare AI Gateway
│   └── render_report.py  # stdlib-only; run dir → one shareable self-contained HTML file
├── runs/<run_id>/        # created per run (gitignored)
│   ├── manifest.json     # what ran, what failed
│   ├── raw/<provider>/   # one JSON per query: prompt, response, usage, latency
│   ├── scores.json/.md   # ← audit-perception-scorer output
│   ├── grades.md         # ← audit-rubric-grader output
│   └── report.md         # ← audit-reporter output
├── site-auditor/             # sibling agent (own SKILL.md + README)
└── seo-performance-monitor/  # sibling agent (own SKILL.md + README)
```

Subagent definitions live at the repo root in [`.claude/agents/`](../../.claude/agents/).

## Sibling agents

Two smaller agents live in this folder because they serve the same GEO/AEO practice, but they are **independent tools, not steps of the pipeline** — each has its own `SKILL.md` front door, runs on its own (and for free — neither touches an LLM API), and gets symlinked into `~/.claude/skills/` separately:

- [**Site Auditor**](site-auditor/) — polite stdlib crawler → page corpus → technical checks + AEO readiness (can AI crawlers get in, server-rendered content, structured data, llms.txt; own-site backlinks via GSC export). Replaces Screaming Frog. Its `--full-text` corpus is also the collection half of the planned Competitor Content Analyzer.
- [**SEO Performance Monitor**](seo-performance-monitor/) — Search Console analysis, position-weighted share of voice, keyword discovery. Replaces the everyday slice of Ahrefs/Semrush.

Why they're grouped here rather than top-level: a brand's AI visibility (the pipeline's subject) rests on whether its site can be read and cited at all (Site Auditor) and how it performs in traditional search (SEO Monitor) — the full stack mapping is in the [repo README](../../README.md#how-the-geoaeo-agents-fit-together). Why they're *not* merged into the pipeline: they run on different cadences with different inputs, and the pipeline's four subagents stay a closed system — collection, two blind analysts, reporter — whose boundaries exist for audit credibility, not for grouping convenience.

## How to run

Just ask, from the repo root:

```
Run an AI brand audit for Hyperbound
```

[`SKILL.md`](SKILL.md) is the front door. It triggers on any GEO/AEO audit request, confirms the config, then dispatches the four subagents in order — collect, score and grade in parallel, report — and hands back the run directory and verdict. Install it by symlinking this folder into `~/.claude/skills/`:

```bash
ln -s ~/github/marketing-agents/agents/ai-brand-auditor ~/.claude/skills/ai-brand-auditor
```

The repo stays the source of truth; edits here are live everywhere the skill runs.

The subagents still work standalone if you want to drive a single step — each one's description tells Claude when it applies, and each hands off a file path the next one consumes:

```
Run audit-perception-scorer on agents/ai-brand-auditor/runs/<run_id>
```

Note that the subagents load from this repo's `.claude/agents/`, so full pipeline runs need Claude Code with the repo root as the working directory.

Direct script usage (collection step only):

```bash
python3 scripts/run_queries.py            # full grid
python3 scripts/run_queries.py --smoke    # 1 query, capped tokens — cheap pipe-check
python3 scripts/run_queries.py --providers anthropic,gemini
```

Requires the Cloudflare AI Gateway env setup (`*_BASE_URL`, provider keys, `CF_AIG_TOKEN`) — documented in the [`ai-architecture`](https://github.com/d-walia/ai-architecture/tree/main/cloudflare-ai-gateway) repo. Every audit call is therefore tracked in the gateway dashboard — an audit run has a visible, attributable cost.

## Sharing a finished audit

`report.md` is the pipeline's working deliverable; the *shareable* one is its HTML render — a single self-contained file (inline CSS, light/dark aware, no external assets) that a stakeholder opens in a browser with nothing installed:

```bash
python3 scripts/render_report.py runs/<run_id>                 # → outputs/<brand>-ai-audit-<run_id>.html
python3 scripts/render_report.py runs/<run_id> --out audit.html
```

The header band (brand, models, calls succeeded/failed) comes from `manifest.json`; the body is `report.md` converted faithfully — no new analysis happens at render time, and rendering never touches an API, so it's free to re-run. This closes the shareability gap: the agent needs this repo, keys, and Claude Code, but the render needs only a browser.

## Auditing a different brand

Start with [`config/client-intake.md`](config/client-intake.md) — it lists what to collect from the client (or gather yourself), why each piece matters, and where it goes. The short version:

1. **Required to run:** fill `config/brand.json` (brand, category, buyer context, 3 competitors — the file is a self-documenting template, and `run_queries.py` refuses to run while it's unfilled). The query grid uses placeholders (`{brand}`, `{competitor_0}`, …) so it adapts automatically.
2. **Required before trusting grades:** a `config/ground-truth.md` fact sheet from the client. The rubric's accuracy and freshness criteria are only as good as the source of truth behind them — without one, the grader can only catch errors it happens to recognize.
3. **Better with:** real buyer language for category-specific queries in `query_grid.json`, battlecards in `intel/`, positioning in `brand-pack/`.

Client-provided material (ground truth, battlecards, positioning) stays out of git history and published outputs — same rule as keys.

## Gotchas learned the hard way

- Cloudflare's bot protection 403s Python's default urllib user-agent (`error code: 1010`) — the script sends its own UA.
- `gemini-2.5-flash` is retired for new API accounts; `gemini-flash-latest` is the stable alias.
- An OpenAI 429 "exceeded your current quota" means no API billing on the account — unrelated to the gateway.
- Gemini "thinking" models spend `maxOutputTokens` on internal reasoning *before* the visible answer — at a 700-token cap, every response truncated to ~26-token fragments. The script now adds automatic headroom for Gemini, but the episode matters beyond the fix: truncated data read as "brand mentioned in 0% of category queries," a measurement artifact indistinguishable from a real (and damning) finding. Both analysis agents flagged it independently; see "Field-tested" below.
