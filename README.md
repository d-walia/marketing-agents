# Marketing Agents

Working agents for real GTM problems, built with Claude. The public face of these lives at [dw-digital-consulting.com](https://dw-digital-consulting.com/#agents).

## The agents

| Agent | Replaces | Status |
|---|---|---|
| AI Brand Auditor | Profound, AthenaHQ | Built. Lives in `agents/ai-brand-auditor/` (35-version build history preserved) |
| Competitive Intel Researcher | Klue, Crayon | Built. `skills/competitive-intel-researcher/` |
| Intelligent Copywriter | Writer, Jasper | Planned |
| Customer Researcher | Wynter, UserTesting | Planned |
| Dashboard Synthesizer | Tableau, Looker Studio | Planned |
| Content Agents | Canva, Gamma, Adobe GenStudio | Planned |

## Layout

| Directory | What lives there |
|---|---|
| `agents/` | Standalone agents with their own code (AI Brand Auditor is a Python engine, not a skill) |
| `skills/` | Agent definitions built as Claude Code skills |
| `brand-pack/` | Positioning, voice rules, ICPs. The input layer for the Copywriter |
| `intel/` | Existing competitive intel; one folder per competitor |
| `sample-data/` | Synthetic datasets for demos |
| `outputs/` | Public demo artifacts produced by the agents |

API keys live in `~/.marketing-agents.env` (never in this repo).

The AI Brand Auditor was developed first, as its own project (originally the `Prototype` repo, now archived). Its full commit history — ten-plus documented versions, each driven by findings from live runs — is preserved here under `agents/ai-brand-auditor/`. See its own `BUILD_LOG.md` for the version story.
