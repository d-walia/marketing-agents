# Marketing Agents

Working agents for real GTM problems, built with Claude. The public face of these lives at [dw-digital-consulting.com](https://dw-digital-consulting.com/#agents).

## The agents

| Agent | Replaces | Status |
|---|---|---|
| AI Brand Auditor | Profound, AthenaHQ | Built. `agents/ai-brand-auditor/` — a skill front door over a 4-subagent GEO audit pipeline |
| Competitive Intel Researcher | Klue, Crayon | Built. `agents/competitive-intel-researcher/` — a single Claude Code skill |
| Meeting Transcriber | Otter, Fireflies | Built. `agents/meeting-transcriber/` — recordings and video files → structured notes via the free Groq Whisper API. Portable: no hardware dependency |
| Live Meeting Transcriber | Otter, Fireflies | Built. `agents/live-meeting-transcriber/` — **live** calls, near-real-time, from the Mac's mic (+ BlackHole for the far side). Mic-bound, Claude Code-only; feeds the Meeting Transcriber notes step |
| SEO Performance Monitor | Ahrefs, Semrush | Built. `agents/seo-performance-monitor/` — page performance from a Search Console export, position-weighted share of voice, and keyword discovery via Google Suggest. Two of three data sources need no API key |
| Account Intelligence Agent | A GTM engineer / Clay consultant | Built. `agents/account-intelligence-agent/` — Claude drives the Clay web UI to build enriched account + contact tables: seed CSV → enrichment waterfalls → Claygent research columns → contact sourcing → email waterfall. First build: 185 US health systems for RCM sales |
| Intelligent Copywriter | Writer, Jasper | Planned |
| Customer Researcher | Wynter, UserTesting | Planned |
| Content Agents | Canva, Adobe GenStudio | Planned |

## Layout

| Directory | What lives there |
|---|---|
| `agents/` | Every agent, one folder each. Each has a `SKILL.md` — the front door that makes it auto-trigger — whether the work behind it is one skill (`competitive-intel-researcher`) or a multi-agent pipeline (`ai-brand-auditor`) |
| `.claude/agents/` | Subagent definitions Claude Code loads when running from this repo (the four `audit-*` agents behind the AI Brand Auditor) |
| `brand-pack/` | Positioning, voice rules, ICPs. The input layer for the Copywriter |
| `intel/` | Existing competitive intel; one folder per competitor |
| `sample-data/` | Synthetic datasets for demos |
| `outputs/` | Public demo artifacts produced by the agents |

API keys live in `~/.marketing-agents.env` (never in this repo).

## AI Brand Auditor

The canonical implementation is a **multi-agent GEO pipeline**: four Claude Code subagents — `audit-query-runner`, `audit-perception-scorer`, `audit-rubric-grader`, `audit-reporter` — each owning one step and handing off through files. The scorer and grader analyze independently (the grader is forbidden from reading the scorer's output) so disagreements between visibility and representation-quality surface as findings instead of getting smoothed over. Full writeup in [`agents/ai-brand-auditor/README.md`](agents/ai-brand-auditor/README.md).

You don't orchestrate that by hand. [`agents/ai-brand-auditor/SKILL.md`](agents/ai-brand-auditor/SKILL.md) is the front door: ask for a brand audit in plain language and it confirms the config, dispatches the four subagents in order, and returns the run directory and verdict. Symlink the folder into `~/.claude/skills/` to install it — the repo stays the source of truth.

Every audit call routes through the Cloudflare AI Gateway, so runs have visible, attributable cost. An earlier single-script Python prototype of this auditor has been retired in favor of the multi-agent version.

A finished audit is shareable beyond this repo: `scripts/render_report.py` turns a run into a single self-contained HTML file in `outputs/` — no Claude Code, keys, or markdown viewer needed on the receiving end, just a browser.
