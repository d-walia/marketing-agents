# AI Brand Perception Audit

A small CLI that measures **how AI assistants perceive your brand** when real buyers ask for advice.

Buying decisions increasingly happen inside AI conversations, not on search results pages. When someone asks an assistant "what should I buy for X," the answer is a snapshot of what the model believes about your category: who exists, who is credible, who wins. This tool captures that snapshot so you can act on it. If SEO asks "do we rank," an AI brand perception audit asks "do we get recommended."

## How it works

1. **Probe.** The tool asks Claude a set of realistic buyer questions about your category: a first-time buyer, a price-sensitive SMB, a security-focused enterprise, a switcher, and a head-to-head ask. Your brand is never named in the question, so nothing primes the answer.
2. **Extract.** A second, structured pass parses each answer: every brand mentioned, the top recommendation, sentiment toward your brand, and the stated reason the winner won.
3. **Report.** You get a markdown report with a mention rate, a recommendation rate, a table of who wins each scenario, and probe-by-probe detail, plus the raw JSON.

The interesting output is usually not the score. It's the **reasons column**: the specific claims and gaps that drive the model's picks. Those are the facts your content and proof points need to address.

## Quick start

```bash
git clone https://github.com/d-walia/ai-brand-perception-audit.git
cd ai-brand-perception-audit
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...   # get one at platform.claude.com

python audit.py \
  --brand "YourBrand" \
  --category "team knowledge base tools" \
  --competitors "Rival1,Rival2" \
  --runs 2
```

Output: `report-yourbrand-<date>.md` and a raw `.json` alongside it.

## What to do with the results

- **Low mention rate** means the model doesn't route your category's problems to you at all. That is a positioning and evidence problem, not an ad problem.
- **Mentioned but never recommended** means the model knows you exist but believes something that keeps you out of the top spot. Read the "why" column to find out what.
- **Run it monthly.** Model updates shift these answers. Track your numbers over time the way you'd track rankings.

## Notes and limits

- Currently probes Claude (`claude-opus-4-8`). The same method applies to any assistant; multi-model support is the obvious next step.
- A handful of scenarios is a probe, not a census. More scenarios and more `--runs` give more stable numbers.
- Answers reflect model training and vary run to run. That variance is itself signal: brands with strong evidence get recommended consistently.
- Edit `scenarios.py` to match how your buyers actually phrase things. That file is where most of the value lives.

## Roadmap

- Multi-model probes (compare how different assistants see the same brand)
- Multi-turn scenarios (real buying conversations have follow-ups)
- Trend tracking across monthly runs

MIT licensed. Built by [Dhruv Walia](https://github.com/d-walia).
