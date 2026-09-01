# Landing Page Builder

*A two-skill pipeline: capture a brand's design system + voice once (brand-extractor-v2), then generate unlimited true-to-life on-brand HTML page mocks with real copy (page-mockup-v2).*

## Flow

```mermaid
flowchart LR
  EX(["brand-extractor-v2 · capture a brand"]):::trigger --> PASS["two-pass extraction · authored CSS + computed styles"]:::process
  BROWSER[["browser tools · live site + screenshots"]]:::service -->|extract| PASS
  PASS --> BF[("brands/slug.md")]:::store
  PASS --> VER["verify · rebuild a section · diff vs screenshot"]:::process
  MK(["page-mockup-v2 · mock a page"]):::trigger --> READ["read brand file + real copy"]:::process
  BF -->|read| READ
  READ --> BUILD["build full-chrome HTML · quality gates"]:::process
  BUILD --> ART[["publish as Artifact · stable URL"]]:::service
  ART --> OUT[/"versioned page mock"/]:::output
  classDef trigger fill:#dcfce7,stroke:#15803d,color:#0f172a;
  classDef process fill:#eef2f8,stroke:#64748b,color:#0f172a;
  classDef service fill:#fef3c7,stroke:#b45309,color:#0f172a;
  classDef store fill:#ede9fe,stroke:#6d28d9,color:#0f172a;
  classDef output fill:#ccfbf1,stroke:#0f766e,color:#0f172a;
  classDef ext fill:#f1f5f9,stroke:#94a3b8,color:#334155,stroke-dasharray:4 3;
```

## How it runs

Two local Claude skills (methodology only, no Python). The extractor captures a brand once via browser tools into a single brand file; the mockup skill consumes that file + copy to build a self-contained HTML page, published as a Claude Artifact (iterations redeploy the same URL). No paid APIs, no Gateway. Note: the folders are named `brand-extractor`/`page-mockup` but install as the **`-v2`** skill names.

## Services & stores

| Thing | Type | Detail |
|---|---|---|
| Browser tools | Service | Live-site extraction + screenshots |
| Artifact publishing | Service | Stable shareable URL, versioned in place |
| `page-mockup/brands/<slug>.md` | Store | Per-company design system (`commure.md`, `dw-digital.md` ship) |

## Connects to

- Internal pipeline: brand-extractor-v2 → page-mockup-v2 (extractor writes the brand file the mockup consumes).
- Distinct from `../../brand-pack/` — that holds Dhruv's own positioning for the planned Copywriter; these are per-target-company design systems (a different layer).
- Optionally offers the `copy-optimizer` / `ai-detector` skills before shipping.

## Gotchas

- Prefer these **v2** repo-hosted variants over any installed v1 `brand-extractor`/`page-mockup` skills when both exist.
- Not included in the MCP server.

## Sources

`brand-extractor/SKILL.md`, `page-mockup/SKILL.md`, `page-mockup/brands/*`, `references/`
