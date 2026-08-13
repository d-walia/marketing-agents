# Marketing Agents

Working agents for real GTM problems, built with Claude — each replacing a paid SaaS tool. The public face of these lives at [dw-digital-consulting.com](https://dw-digital-consulting.com/#agents).

> **TL;DR** — Six built agents (GEO audits, competitive intel, meeting transcription ×2, SEO, account intelligence), three planned. Each agent folder has a `SKILL.md` front door (auto-triggers in Claude Code) and a `README.md` explaining the design. Install by symlinking into `~/.claude/skills/`.

## What's inside

| Agent | What it does | Replaces | Status | Where |
|---|---|---|---|---|
| AI Brand Auditor | 4-subagent GEO pipeline measuring how AI models perceive and recommend a brand | Profound, AthenaHQ | Built | [`agents/ai-brand-auditor/`](agents/ai-brand-auditor/) |
| Competitive Intel Researcher | Competitor analysis → sourced report, sales battlecard, delta memo | Klue, Crayon | Built | [`agents/competitive-intel-researcher/`](agents/competitive-intel-researcher/) |
| Meeting Transcriber | Recordings and video files → structured notes via the free Groq Whisper API | Otter, Fireflies | Built | [`agents/meeting-transcriber/`](agents/meeting-transcriber/) |
| Live Meeting Transcriber | Live calls, near-real-time, from the Mac's mic (+ BlackHole for the far side); feeds the Meeting Transcriber notes step | Otter, Fireflies | Built | [`agents/live-meeting-transcriber/`](agents/live-meeting-transcriber/) |
| SEO Performance Monitor | Page performance from a Search Console export, position-weighted share of voice, keyword discovery via Google Suggest | Ahrefs, Semrush | Built | [`agents/seo-performance-monitor/`](agents/seo-performance-monitor/) |
| Account Intelligence Agent | Claude drives the Clay web UI: seed CSV → enrichment waterfalls → research columns → contacts → email waterfall | A GTM engineer / Clay consultant | Built | [`agents/account-intelligence-agent/`](agents/account-intelligence-agent/) |
| Intelligent Copywriter | On-brand copy from the brand-pack input layer | Writer, Jasper | Planned | — |
| Customer Researcher | — | Wynter, UserTesting | Planned | — |
| Content Agents | — | Canva, Adobe GenStudio | Planned | — |

## Quickstart

Symlink an agent into the skills directory, then ask for the job in plain language ("run an AI brand audit for Hyperbound", "build a battlecard for Klue"):

```bash
ln -s ~/github/marketing-agents/agents/ai-brand-auditor ~/.claude/skills/ai-brand-auditor
```

The repo stays the source of truth — edits here are live everywhere the skill runs. Multi-agent pipelines (the Brand Auditor's four `audit-*` subagents) load from this repo's `.claude/agents/`, so run those with the repo root as the working directory.

## Layout

| Directory | What lives there |
|---|---|
| `agents/` | Every agent, one folder each: `SKILL.md` (the auto-trigger front door) + `README.md` (the design writeup), whether the work behind it is one skill or a multi-agent pipeline |
| `.claude/agents/` | Subagent definitions Claude Code loads when running from this repo (the four `audit-*` agents) |
| `brand-pack/` | Positioning, voice rules, ICPs — the input layer for the Copywriter |
| `intel/` | Existing competitive intel; one folder per competitor |
| `sample-data/` | Synthetic datasets for demos |
| `outputs/` | Public demo artifacts produced by the agents |

## Conventions

- API keys live in `~/.marketing-agents.env` — never in this repo. Client-site run data is gitignored.
- Every AI API call routes through the Cloudflare AI Gateway (setup documented in [`ai-architecture`](https://github.com/d-walia/ai-architecture/tree/main/cloudflare-ai-gateway)), so every run has a visible, attributable cost.
- Deliverables are shareable beyond the repo: `agents/ai-brand-auditor/scripts/render_report.py` turns an audit run into one self-contained HTML file — the recipient needs only a browser.
- Retired work is deleted, not kept as dead weight: an earlier single-script Python prototype of the Brand Auditor gave way to the multi-agent version (the "why" is in [its README](agents/ai-brand-auditor/README.md)).
