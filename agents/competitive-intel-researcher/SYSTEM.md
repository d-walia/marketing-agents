# Competitive Intel Researcher

*Decision-driven competitive intelligence on 1–5 vendors — evidence-graded dossiers, a weighted comparison matrix, say/do gap analysis, Four Corners response prediction, and Know/Say/Show battlecards.*

## Flow

```mermaid
flowchart LR
  SKILL(["Skill · analyze competitor / battlecard / compare"]):::trigger --> P0["Phase 0 · intake · mode · taxonomy + weights"]:::process
  P0 --> P1["Phase 1 · one dossier per vendor · parallel subagents for 3+"]:::process
  INTEL[("intel/ · competitor baselines")]:::store -->|read| P1
  P1 --> P2["Phase 2 · weighted matrix · say/do gap · Four Corners"]:::process
  P2 --> OUT[/"dossiers · comparison-matrix · battlecards · delta-memo"/]:::output
  OUT -->|write| OUTS[("outputs/run/date/")]:::store
  P2 -.->|offer to promote fresh dossier| INTEL
  classDef trigger fill:#dcfce7,stroke:#15803d,color:#0f172a;
  classDef process fill:#eef2f8,stroke:#64748b,color:#0f172a;
  classDef service fill:#fef3c7,stroke:#b45309,color:#0f172a;
  classDef store fill:#ede9fe,stroke:#6d28d9,color:#0f172a;
  classDef output fill:#ccfbf1,stroke:#0f766e,color:#0f172a;
  classDef ext fill:#f1f5f9,stroke:#94a3b8,color:#334155,stroke-dasharray:4 3;
```

## How it runs

A pure-methodology Claude skill — no scripts. Collection is web research the agent (and parallel general-purpose subagents for 3+ vendors) performs against docs, changelogs, review sites, and pricing pages. Four modes: deal support, landscape, monitoring refresh, positioning/prep. Also served over MCP (it works fully for MCP recipients because there's no code to transfer).

## Services & stores

| Thing | Type | Detail |
|---|---|---|
| Web research | (agent work) | No coded API dependency; method sources are intellectual (SCIP, Porter, Forrester, Clozd, Klue) |
| `intel/<competitor-slug>/` | Store | Prior baselines read at Phase 1 |
| `outputs/<run-slug>/<date>/` | Store | `dossier-*.md`, `comparison-matrix.md`, `battlecard-*.md`, `delta-memo.md` |

## Connects to

- Shares the `intel/` baseline dir with the (planned) Transcript Router; offers to promote fresh dossiers back as new baselines.
- Distributed by the [MCP Server](../../mcp-server/SYSTEM.md) (one of the three included skills).

## Gotchas

- Pure methodology — no external API keys, no Gateway. A full design doc lives outside the repo (in Claude Outputs).

## Sources

`SKILL.md`, `README.md`, `references/dossier-template.md`, `references/battlecard-template.md`
