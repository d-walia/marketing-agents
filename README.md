# AI Brand Perception Audit (B2B)

A CLI that measures **how AI assistants perceive and recommend your brand** when your actual buyers work through a real evaluation, and tells you **what to change so they recommend you**.

B2B buying decisions increasingly start inside AI conversations. When your ICP describes their problem to ChatGPT, Claude, Gemini, or Perplexity, the assistant decides whether your *category* is even the answer, who makes the shortlist, and who wins, based on what it believes about you. This tool captures those beliefs and turns them into positioning and content recommendations.

## The method: buyer-journey chat sessions

The tool poses as **one ICP persona per audit** (default: a Head of Sales / Sales Ops leader — hands-on with process and tooling, but accountable for the number) and runs the same multi-turn chat session against every assistant you have API keys for. One ICP per audit keeps the comparison clean: differences between sessions are differences between models, not personas. Auditing another ICP is another run with `--persona`.

Each session follows how B2B buying conversations actually unfold:

1. **Problem turn.** The buyer describes their business pain in their own words. No category, no vendor names. Measures: *does the assistant propose your category as a solution at all?*
2. **Vendor turn.** The buyer asks who to shortlist. Measures: *do you surface unprompted, and where do you rank?*
3. **Brand turn.** The buyer raises your brand directly and asks for a candid take. Measures: *recommendation strength, the qualifiers attached ("good, but...")*, *whether a competitor gets recommended over you, and which sources the view rests on — your content or third parties'.*

## What you get

- **A funnel and a buyer journey map:** category proposed → brand mentioned unprompted → shortlisted → strongly recommended, across every assistant, with a visual (mermaid) map of exactly where sessions drop off and which competitor the recommendation diverted to.
- **The belief inventory:** the concrete claims each assistant made about you, the qualifiers it hedged with, who it prefers over you and why, and whether any of its information came from your own content.
- **The prescription:** an analysis of what information drives AI opinion of your brand, what proof the assistants needed but didn't have, and prioritized positioning and content changes to close those gaps.
- Full raw transcripts in JSON, for receipts.

## Quick start

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...     # required: probes Claude + runs the analysis
export OPENAI_API_KEY=...               # optional: probe ChatGPT
export GEMINI_API_KEY=...               # optional: probe Gemini
export PERPLEXITY_API_KEY=...           # optional: probe Perplexity

python audit.py \
  --brand "Acme Analytics" \
  --category "product analytics platforms" \
  --icp "Series B B2B SaaS companies, 50-200 employees, product-led growth motion" \
  --problem "We can't tell which product features drive retention, and churn is creeping up" \
  --competitors "Amplitude,Mixpanel,Heap"
```

Any assistant without a key is skipped with a notice. Analysis and extraction always run on Claude.

## Reading the results

- **Category never proposed** is the most serious finding: AI doesn't route your ICP's problem to your category. No amount of brand content fixes that until the category-to-problem link exists in public writing.
- **Shortlisted but never recommended:** read the qualifiers and the competitor-preferred reasons. Those are the exact objections your proof points need to answer.
- **No first-party sources cited:** third parties are defining you. The prescription section will tell you what to publish.

## Scope and honesty notes

- Built for **B2B** evaluations. The personas and journey model a buying committee, not a consumer impulse purchase.
- API models are proxies for the consumer apps (the apps add retrieval and memory). Treat results as a strong signal of the model's beliefs, not a pixel-perfect replay of chatgpt.com.
- A few sessions is a probe, not a census. Re-run monthly; model updates move these answers.

MIT licensed. Built by [Dhruv Walia](https://github.com/d-walia).
