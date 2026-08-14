# AI Brand Audit: Multi-Agent GEO Pipeline

Measures how AI models (Claude, ChatGPT, Gemini) perceive and recommend a brand: does it show up when buyers ask category questions, at what rank, framed how, and how accurately. The workflow runs as four Claude Code subagents, each owning one step and handing off through files.

This folder holds the repo's GEO/AEO practice. The audit pipeline is the main agent; two smaller sibling agents (see [Sibling agents](#sibling-agents)) cover what it doesn't: technical site health and traditional search performance.

## Why four subagents

An audit is only as credible as its separation of concerns:

| Agent | Owns | Tools | Not allowed |
|---|---|---|---|
| `audit-query-runner` | Collecting raw model responses | Bash, Read | Interpretation of any kind. Downstream agents see the data cold |
| `audit-perception-scorer` | Category routing, rank, share of voice, framing | Read, Write | Factual accuracy judgments. No Bash (it never executes anything) |
| `audit-rubric-grader` | Rubric-based quality grades | Read, Write | Reading the scorer's outputs. It grades blind, so the two analyses stay independent |
| `audit-reporter` | Synthesis + recommendations | Read, Write | New analysis of raw data. Every claim must trace to the two upstream artifacts |

The scorer and grader are split because they measure different things: one visibility, one representation quality. Their disagreements ("mentioned everywhere but described inaccurately") are findings in their own right. A single agent doing both tends to smooth those tensions over.

## Field-tested

The first full run (July 2026) proved the design. A harness bug truncated every Gemini response to fragments, which scored as "0% brand mentions on category queries": a dramatic number that was pure instrument error. Both analysts caught it independently. The perception scorer flagged the responses as truncation artifacts, and the rubric grader, which cannot read the scorer's output, hit the same raw files cold and raised the same flag. After the harness fix and a re-collection, the finding reversed: Gemini ranks the audited brand #1 on every category list. Same brand, same queries, opposite conclusion. The agent separation is the only reason the bad number never reached a report.

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

Two smaller agents live in this folder because they belong to the same GEO/AEO practice. They are independent tools, not steps of the pipeline: each has its own `SKILL.md` front door, runs on its own, costs nothing (neither calls an LLM API), and installs as its own symlink in `~/.claude/skills/`.

- [**Site Auditor**](site-auditor/) crawls a site into a page corpus, runs technical checks, and reports AEO readiness: AI-crawler access, server-rendered content, structured data, llms.txt, plus own-site backlinks from a Search Console export. Replaces Screaming Frog. Its `--full-text` corpus is also the input for the planned Competitor Content Analyzer.
- [**SEO Performance Monitor**](seo-performance-monitor/) analyzes Search Console exports, computes position-weighted share of voice, and discovers keywords. Replaces the everyday slice of Ahrefs and Semrush.

They are grouped here because AI visibility rests on them: a site AI crawlers can't read can't be cited, and traditional search performance feeds the same content decisions. The full stack mapping is in the [repo README](../../README.md#how-the-geoaeo-agents-fit-together). They stay out of the pipeline because they run on different cadences with different inputs, and the pipeline's four subagents form a closed system whose boundaries protect audit credibility.

## How to run

Ask, from the repo root:

```
Run an AI brand audit for Hyperbound
```

[`SKILL.md`](SKILL.md) is the front door. It triggers on GEO/AEO audit requests, confirms the config, then dispatches the four subagents in order (collect, then score and grade in parallel, then report) and hands back the run directory and verdict. Install it by symlinking this folder into `~/.claude/skills/`:

```bash
ln -s ~/github/marketing-agents/agents/ai-brand-auditor ~/.claude/skills/ai-brand-auditor
```

The repo stays the source of truth; edits here are live everywhere the skill runs.

The subagents also work standalone. Each one's description tells Claude when it applies, and each hands the next a file path:

```
Run audit-perception-scorer on agents/ai-brand-auditor/runs/<run_id>
```

Full pipeline runs need Claude Code with the repo root as the working directory, since the subagents load from this repo's `.claude/agents/`.

Direct script usage (collection step only):

```bash
python3 scripts/run_queries.py            # full grid
python3 scripts/run_queries.py --smoke    # 1 query, capped tokens: cheap pipe check
python3 scripts/run_queries.py --providers anthropic,gemini
```

Requires the Cloudflare AI Gateway env setup (`*_BASE_URL`, provider keys, `CF_AIG_TOKEN`), documented in the [`ai-architecture`](https://github.com/d-walia/ai-architecture/tree/main/cloudflare-ai-gateway) repo. Every audit call shows up in the gateway dashboard, so a run has a visible, attributable cost.

## Sharing a finished audit

`report.md` is the working deliverable. The shareable one is its HTML render: a single self-contained file (inline CSS, light/dark aware, no external assets) that opens in any browser with nothing installed.

```bash
python3 scripts/render_report.py runs/<run_id>                 # → outputs/<brand>-ai-audit-<run_id>.html
python3 scripts/render_report.py runs/<run_id> --out audit.html
```

The header band (brand, models, calls succeeded/failed) comes from `manifest.json`; the body converts `report.md` faithfully. No new analysis happens at render time, and rendering never touches an API, so it is free to re-run. The agent needs this repo, keys, and Claude Code; the render needs only a browser.

## Auditing a different brand

Start with [`config/client-intake.md`](config/client-intake.md): what to collect from the client, why each piece matters, and where it goes. The short version:

1. **To run at all:** fill `config/brand.json` (brand, category, buyer context, 3 competitors). The file documents each field, and `run_queries.py` refuses to run while any are blank. The query grid uses placeholders (`{brand}`, `{competitor_0}`, ...) and adapts automatically.
2. **To trust the grades:** a `config/ground-truth.md` fact sheet from the client. The rubric's accuracy and freshness criteria need a source of truth; without one, the grader can only catch errors it happens to recognize.
3. **To sharpen the audit:** real buyer language for category-specific queries in `query_grid.json`, battlecards in `intel/`, positioning in `brand-pack/`.

Client material (ground truth, battlecards, positioning) stays out of git history and published outputs, same rule as keys.

## Gotchas

- Cloudflare's bot protection 403s Python's default urllib user-agent (`error code: 1010`); the script sends its own UA.
- `gemini-2.5-flash` is retired for new API accounts; `gemini-flash-latest` is the stable alias.
- An OpenAI 429 "exceeded your current quota" means no API billing on the account. It is unrelated to the gateway.
- Gemini "thinking" models spend `maxOutputTokens` on internal reasoning before the visible answer. At a 700-token cap, every response truncated to ~26-token fragments. The script now adds headroom for Gemini automatically, but the lesson outlasts the fix: truncated data read as "brand mentioned in 0% of category queries," a measurement artifact indistinguishable from a real finding. See "Field-tested" above.
