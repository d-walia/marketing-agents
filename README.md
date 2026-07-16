# AI Brand Perception Audit (B2B)

A CLI that measures **how AI assistants perceive and recommend your brand** when your actual buyers work through a real evaluation, and tells you **what to change so they recommend you**.

B2B buying decisions increasingly start inside AI conversations. When your ICP describes their problem to ChatGPT, Claude, Gemini, or Perplexity, the assistant decides whether your *category* is even the answer, who makes the shortlist, and who wins, based on what it believes about you. This tool captures those beliefs and turns them into positioning and content recommendations.

Works for **any B2B product**. Everything specific to your brand and buyer lives in a config file you write; nothing about a particular category is baked into the tool.

## Inputs: what the tool needs from you

The audit is only as good as your ICP definition. The config file requires four things:

| Input | What good looks like |
|---|---|
| **Brand + category + competitors** | The category in your *buyer's* language, not your marketing language. If buyers say "contract software" and you say "CLM platform," use theirs. |
| **ICP: who the buyer is** | A specific role at a specific kind of company. "VP of Legal Operations at a mid-market fintech, 800 employees, high contract volume" — not "legal teams." |
| **ICP: jobs to be done + priorities** | The outcomes this person is on the hook for, and what they care about most right now. These shape how the persona talks and what trade-offs it makes. Bad: "wants efficiency." Good: "turn contracts around in under 5 days; reduce outside counsel spend; look rigorous in front of the audit committee." |
| **Scenarios** | One or more concrete moments where those jobs hit a challenge, written in the buyer's own words, with **no category or vendor names**. Each scenario becomes one buyer-journey session per assistant. Bad: "needs better contract management." Good: "two deals slipped last quarter because redlines sat with us for two weeks and sales is furious." |

Generate a starter template and fill it in:

```bash
python audit.py --init          # writes audit-config.json
```

See [example-config.json](example-config.json) for a fully worked example (Gong is the demo subject; swap in any B2B brand).

## The method: buyer-journey chat sessions

For each scenario, the tool poses as your ICP and runs the same multi-turn chat session against every assistant you have API keys for. The persona is built entirely from your ICP definition: role, jobs to be done, priorities. Each session unfolds the way B2B buying conversations actually do:

1. **Problem turn.** The buyer describes the scenario in their own words. No category, no vendor names. Measures: *does the assistant propose your category as a solution at all?*
2. **Vendor turn.** The buyer asks who to shortlist. Measures: *do you surface unprompted, and where do you rank?*
3. **Brand turn.** The buyer raises your brand directly and asks for a candid take. Measures: *recommendation strength, the qualifiers attached ("good, but...")*, *whether a competitor gets recommended over you, and which sources the view rests on — your content or third parties'.*

## What you get

- **A funnel and a buyer journey map:** category proposed → brand mentioned unprompted → shortlisted → strongly recommended, across every scenario and assistant, with a visual (mermaid) map of exactly where sessions drop off and which competitor the recommendation diverted to.
- **The belief inventory:** the concrete claims each assistant made about you, the qualifiers it hedged with, who it prefers over you and why, and whether any of its information came from your own content.
- **The prescription:** an analysis of what information drives AI opinion of your brand, what proof the assistants needed but didn't have (with its impact on each verdict), and prioritized positioning and content changes to close those gaps.
- Full raw transcripts in JSON, for receipts.

## Quick start

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...     # required: probes Claude + runs the analysis
export OPENAI_API_KEY=...               # optional: probe ChatGPT
export GEMINI_API_KEY=...               # optional: probe Gemini
export PERPLEXITY_API_KEY=...           # optional: probe Perplexity

python audit.py --init                  # create the config template
# fill in audit-config.json, then:
python audit.py audit-config.json
```

Any assistant without a key is skipped with a notice. Analysis and extraction always run on Claude.

## Reading the results

- **Category never proposed** is the most serious finding: AI doesn't route your ICP's problem to your category. No amount of brand content fixes that until the category-to-problem link exists in public writing.
- **Shortlisted but never recommended:** read the qualifiers and the competitor-preferred reasons. Those are the exact objections your proof points need to answer.
- **No first-party sources cited:** third parties are defining you. The prescription section will tell you what to publish.

## Scope and honesty notes

- Built for **B2B** evaluations. The persona models an accountable buyer working through a real evaluation, not a consumer impulse purchase.
- One ICP per audit keeps the comparison clean: differences between sessions are differences between models and scenarios, not personas. Auditing another ICP is another config file.
- API models are proxies for the consumer apps (the apps add retrieval and memory). Treat results as a strong signal of the model's beliefs, not a pixel-perfect replay of chatgpt.com.
- A few sessions is a probe, not a census. Re-run monthly; model updates move these answers.

MIT licensed. Built by [Dhruv Walia](https://github.com/d-walia).
