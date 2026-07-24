# Marketing Agents

Working agents for real GTM problems, built with Claude. The public face of these lives at [dw-digital-consulting.com](https://dw-digital-consulting.com/#agents).

## The agents

| Agent | Replaces | Status |
|---|---|---|
| AI Brand Auditor | Profound, AthenaHQ | Built. `agents/ai-brand-auditor/` — a 4-subagent GEO audit pipeline |
| Competitive Intel Researcher | Klue, Crayon | Built. `agents/competitive-intel-researcher/` — a single Claude Code skill |
| Meeting Transcriber | Otter, Fireflies | Built. `agents/meeting-transcriber/` — recordings → structured notes via the free Groq Whisper API |
| Intelligent Copywriter | Writer, Jasper | Planned |
| Customer Researcher | Wynter, UserTesting | Planned |
| Dashboard Synthesizer | Tableau, Looker Studio | Planned |
| Content Agents | Canva, Adobe GenStudio | Planned |

## Layout

| Directory | What lives there |
|---|---|
| `agents/` | Every agent, one folder each — whether it's built as a single Claude Code skill (`competitive-intel-researcher`) or a multi-agent pipeline (`ai-brand-auditor`) |
| `.claude/agents/` | Subagent definitions Claude Code loads when running from this repo (the four `audit-*` agents behind the AI Brand Auditor) |
| `brand-pack/` | Positioning, voice rules, ICPs. The input layer for the Copywriter |
| `intel/` | Existing competitive intel; one folder per competitor |
| `sample-data/` | Synthetic datasets for demos |
| `outputs/` | Public demo artifacts produced by the agents |

API keys live in `~/.marketing-agents.env` (never in this repo).

## AI Brand Auditor

The canonical implementation is a **multi-agent GEO pipeline**: four Claude Code subagents — `audit-query-runner`, `audit-perception-scorer`, `audit-rubric-grader`, `audit-reporter` — each owning one step and handing off through files. The scorer and grader analyze independently (the grader is forbidden from reading the scorer's output) so disagreements between visibility and representation-quality surface as findings instead of getting smoothed over. Full writeup in [`agents/ai-brand-auditor/README.md`](agents/ai-brand-auditor/README.md).

Every audit call routes through the Cloudflare AI Gateway, so runs have visible, attributable cost. An earlier single-script Python prototype of this auditor has been retired in favor of the multi-agent version.
