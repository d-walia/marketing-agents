---
name: agent-architect
description: Design the architecture for a new agent or automation before building it — decompose the workflow, pick the right tool per layer (Claude Code skill, Claude API script, Agent SDK, GitHub Actions, Zapier, n8n, LangGraph, or an enterprise iPaaS like Tray.ai), and produce a build plan that spends zero dollars wherever zero dollars does the job. Use whenever Dhruv describes an agent or automation he wants to build and asks how to build it, which tool to use, whether he needs n8n / Zapier / LangGraph / Tray, how to make something run on a schedule or unattended, or asks for an architecture or build plan for a workflow.
---

# Agent Architect

Turn "I want an agent that does X" into a concrete architecture with the cheapest tool that actually does the job — and name the trigger that would justify upgrading later. The failure mode this skill exists to prevent: paying platform fees or burning tokens on work a free scheduler and a deterministic script could do.

## The mental model (explain it when it helps)

The tool ladder is not one axis. It is two:

1. **Control over logic** (how much custom behavior you own):
   Zapier → n8n → Claude Agent SDK / LangGraph → raw code
2. **Governance** (who vouches for it in production — patching, compliance certs, SSO, audit trails, an accountable vendor):
   self-hosted anything → managed SaaS (Zapier, n8n cloud) → enterprise iPaaS (Tray.ai, Workato)

Tray-class tools are not "harder LangGraph." They are bought, not built — the cost is procurement and money, not engineering time. They enter the picture only when someone else's security or compliance team is a stakeholder. For solo work they are never the answer; inside a company, they become the answer the moment a pilot touches customer data and must survive review (the "who patches this instance, where are the compliance certificates" test).

## Intake — establish these before recommending

Ask only what the description doesn't already answer:

1. **Trigger** — human-initiated on demand? An event in a SaaS tool? A schedule? Always-on?
2. **Unattended?** — does it run with no human watching, or is Dhruv in the loop each run?
3. **Volume** — runs per month, honestly estimated.
4. **Logic shape** — linear glue (A happened → do B)? Branching/state/loops? Genuine LLM reasoning? Multi-agent handoffs?
5. **Who must trust it** — just Dhruv? A client? An employer's security/compliance team?
6. **Data sensitivity** — public, personal, or regulated (PHI/PII)?
7. **Failure tolerance** — if a run silently fails, is that annoying or damaging?

## The decision ladder (apply top to bottom — stop at the first fit)

**1. Claude Code skill** — human-initiated, Dhruv in the loop, judgment-heavy.
Cost: $0 beyond the Claude subscription. This is the default for research, analysis, and content work. If he'll be at the keyboard anyway, nothing else earns its complexity.

**2. Script + GitHub Actions cron** — scheduled or event-driven, unattended, deterministic or single-LLM-call logic.
Cost: $0 (free minutes dwarf his usage; secrets in Actions; Claude calls via the Cloudflare AI Gateway so spend is visible). This is the free n8n for a solo operator: fetch → transform → write → notify. The dashboard pipeline pattern.

**3. Zapier** — an event in one SaaS tool must trigger an action in another, the connectors exist, volume is low (< ~100 tasks/mo), and building auth by hand is the only alternative.
Cost: free tier is tiny; per-task pricing punishes volume. Use it as glue, never as the brain. If a Zap grows branches, it's outgrown Zapier.

**4. n8n (self-hosted)** — many-step workflows with branching, retries, and state, at volumes where Zapier pricing stings, where a visual editor beats maintaining scripts.
Cost: $0 licence (fair-code) + wherever it runs + **the Tray CEO's tax: you are the one patching it and answering for it.** Self-hosted n8n holding client credentials or regulated data is a liability, not a hack — that's the honest boundary of this rung.

**5. Claude Agent SDK / LangGraph** — the logic itself is agentic: multi-step reasoning, tool use, multi-agent handoffs, custom evals. Agent SDK first (already in the stack, Claude-native); LangGraph when orchestration must span providers or needs graph-state machinery the SDK doesn't give.
Cost: engineering time + tokens. Enters only when a workflow tool would be fighting the problem.

**6. Enterprise iPaaS (Tray.ai, Workato)** — someone else's compliance team is in the room: SSO, audit logs, SOC2/HIPAA, vendor accountability, cross-team ownership.
Cost: enterprise contract. Recommend it inside orgs at production-handoff time; never for personal builds. (Useful framing given the healthcare background: anything touching PHI leans hard toward this rung or the employer's own approved infra.)

## Multi-agent and token optimization (the second budget)

Platform fees are one budget; tokens are the other. For every step in the decomposed workflow, ask:

- **Does this step need an LLM at all?** Fetching, parsing, diffing, formatting, scheduling are deterministic — code, not tokens. The LLM belongs only where judgment lives.
- **Cheapest capable model per step.** Haiku-class for extraction and classification; big models only for synthesis and writing. A pipeline that uses one model for everything is almost always overpaying.
- **Batch, don't drip.** One call over 50 items beats 50 calls.
- **Cache and diff.** Store last run's output; only process what changed (the Visualping → delta pattern).
- **Multi-agent only when isolation pays.** Separate agents earn their overhead when independence is the point (the Brand Auditor's scorer/grader firewall) or contexts must stay clean — not because "multi-agent" sounds better. Default to one agent with good steps.
- **Human-in-the-loop is free QA.** If Dhruv reviews output anyway, drop the verification pass and its tokens.

## Output format

Always produce:

```
## Architecture: <agent name>
**Recommendation:** <tool(s)> — one sentence on why this rung and not the ones below it.

| Step | What happens | LLM? | Runs on | Cost |
|---|---|---|---|---|

**Monthly cost floor:** $X platform + ~$Y tokens (state assumptions)
**Upgrade trigger:** the specific event that justifies the next rung
  (e.g., "volume passes ~500 runs/mo → move Zapier glue to n8n";
   "a client's security team asks who patches it → managed/iPaaS")
**Build order:** first working slice → hardening → automation
```

## Calibration

- Bias to the lowest rung that truly fits; name the upgrade trigger instead of pre-building for it.
- If two rungs genuinely tie, recommend the one already in the stack (skills, Actions, Agent SDK) — familiarity is a real cost advantage.
- Say when something should *not* be an agent at all: a one-off task is a chat session, not a build.
