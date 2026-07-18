# AI Brand Perception Audit (B2B)

A CLI that measures **how AI assistants perceive and recommend your brand** when your buyers work through a real evaluation, and tells you **what to change so they recommend you**.

B2B buying decisions increasingly start inside AI conversations. When your ICP describes their problem to ChatGPT, Claude, Gemini, or Perplexity, the assistant decides whether your *category* is even the answer, who makes the shortlist, and who wins, based on what it believes about you.

Works for **any B2B product**: everything brand-specific lives in a config file you write. Define your ICP and their moments of pain; the tool runs adaptive multi-turn buying conversations as that person against Claude, ChatGPT, and Gemini, then reports the funnel (category proposed, mentioned unprompted, shortlisted, recommended, wins the final call under pressure), the beliefs and sources behind every verdict, and the exact evidence, in each model's own words, that would flip the answer. How it was built, and why each design choice exists: [BUILD_LOG.md](BUILD_LOG.md).

## Inputs: what the tool needs from you

The audit is only as good as your ICP definition. The config file needs:

| Input | What good looks like |
|---|---|
| **Brand + category + competitors** | The category in your *buyer's* language, not your marketing language. If buyers say "contract software" and you say "CLM platform," use theirs. |
| **ICP: who the buyer is** | A specific role at a specific kind of company. "VP of Legal Operations at a mid-market fintech, 800 employees, high contract volume", not "legal teams". |
| **ICP: jobs to be done + priorities** | The outcomes this person is on the hook for, and what they care about most right now. These shape how the persona talks and what trade-offs it makes. Bad: "wants efficiency." Good: "turn contracts around in under 5 days; reduce outside counsel spend; look rigorous in front of the audit committee." |
| **ICP: buying moment** | The trigger event that put them in market and the pressure clock they're on. This makes the simulated buyer push like a real one. Good: "third forecast miss just landed; I have one quarter before this becomes a question about me." |
| **ICP: installed stack** | Tools they already run that a purchase must coexist with. This is where the realest objections come from: a buyer with Mindtickle installed asks "what happens to my Mindtickle rollout," and so will the simulated one. |
| **ICP: decision criteria** | What would actually make them buy: proof thresholds, integration constraints, admin capacity, reference requirements. The buyer raises these unprompted, as real buyers do. |
| **Scenarios** | One or more concrete moments where those jobs hit a challenge, written in the buyer's own words, with **no category or vendor names**. Each scenario becomes one buyer-journey session per assistant. Keep each scenario to one dominant pain: multi-pain scenarios measure which pain the model latches onto rather than who wins. Bad: "needs better contract management." Good: "two deals slipped last quarter because redlines sat with us for two weeks and sales is furious." |

Generate a starter template and fill it in:

```bash
python audit.py --init          # writes audit-config.json
```

See [example-config.json](example-config.json) for a fully worked example (Gong is the demo subject; swap in any B2B brand).

## The method: buyer-journey chat sessions

For each scenario, the tool poses as your ICP and runs the same multi-turn chat session against every assistant you have API keys for. Each session unfolds the way B2B buying conversations actually do:

### Framings: the same pain, asked four ways

Real buyers phrase the same problem differently on different days, and AI routes those phrasings to completely different answers. Each scenario can run under up to four **framings** of the opening question, everything else held constant:

| Framing | The buyer opens with | What it measures |
|---|---|---|
| `operational` (default) | "How would you approach solving this?" | Does the category enter at all, or does AI route to process advice? |
| `platform` | "What tools or platforms exist for this?" | Who leads when AI treats it as a vendor evaluation |
| `methodology` | "Is there evidence tooling even solves this, vs process change?" | Whether AI routes to research with no vendor named, and whether your brand is connected to the evidence debate |
| `validation` | "What evidence would I need to justify budget to my CFO?" | Which proof sources AI treats as CFO-grade, and whether yours qualify |

Add `"framings": ["operational", "platform", ...]` to a scenario; omit for operational only. Which framings unlock the category and the brand is a keystone finding; the report compares them directly.

### Retrieval mode: see what AI actually reads

By default probes measure trained-in beliefs. With `--retrieval`, Claude and Gemini probe with live web search, and the tool records **every URL each assistant consulted** per session. Prescriptions upgrade from "publish this proof" to "publish this proof *in this venue*": the report analyzes which domains carried the verdict (your site, competitor buyer's guides, review aggregators, independent blogs) and names the placement for each recommendation. Run both modes to compare what AI believes from memory versus what it finds when it looks.

### Pathways

The journey **branches after stage 1** based on what the assistant does. If the assistant names vendors on its own while answering the problem (a sign the category-to-vendor mapping already works for that framing, typical of established categories like revenue intelligence), the buyer follows that thread: stage 2 becomes a **head-to-head comparison** of the vendors the assistant put on the table. If no vendor surfaces (typical of younger categories), the buyer opens the vendor conversation themselves (**standard pathway**). Both pathways are 4 stages and 8 turns; the report notes each session's pathway, and the pathway distribution is itself a category-mapping finding.

Every stage goes two prompts deep. The stage arc is fixed for comparability; the buyer's words are **adaptive**: a simulated persona built from your full ICP definition (role, jobs, priorities, buying moment, installed stack, decision criteria) reads the assistant's answer and writes the follow-up a real buyer under pressure would, referencing specifics and raising its own constraints unprompted. Only the opening turn is verbatim from your scenario, so the unprimed category measurement stays clean. A guardrail blocks the buyer from naming the brand, competitors, or category before the assistant does; if generation fails, scripted fallbacks keep the run alive.

1. **Problem stage.** The buyer describes the scenario in their own words (no category, no vendor names), then asks which approach gives the most impact fastest. Measures: *does the assistant propose your category, and does the category survive prioritization, not just brainstorming?*
2. **Vendor stage.** The buyer asks who to shortlist, then makes the assistant defend its top pick and name what would change the ranking. Measures: *do you surface unprompted, where do you rank, and what are the real decision criteria?*
3. **Brand stage.** The buyer raises your brand directly for a candid take, then asks what that view is based on and how current it is. Measures: *recommendation strength, the qualifiers attached, whether a competitor gets recommended over you, and the provenance of the assistant's information: your content, third parties, or stale training data it admits it can't vouch for.*
4. **Pressure stage.** The buyer pushes back ("would any of those concerns actually stop you? Commit today: them or someone else?") then demands a three-sentence case to the CEO and the single piece of evidence that would change the assistant's mind. Measures: *which qualifiers dissolve (soft objections) vs harden into dealbreakers (real objections), who wins the final call, the pitch your brand gets made with, and the exact flip condition your content strategy should target.*

## What you get

- **A funnel and a buyer journey map:** category proposed → brand mentioned unprompted → shortlisted → strongly recommended, across every scenario and assistant, with a mermaid map of where sessions drop off and which competitor the recommendation diverted to.
- **The belief inventory:** the concrete claims each assistant made about you, the qualifiers it hedged with, who it prefers over you and why, and whether any of its information came from your own content.
- **The prescription:** an analysis of what information drives AI opinion of your brand, what proof the assistants needed but didn't have (with its impact on each verdict), and prioritized positioning and content changes to close those gaps.
- Full raw transcripts in JSON, for receipts.

## Quick start

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...     # required: probes Claude + runs the analysis
export OPENAI_API_KEY=...               # optional: probe ChatGPT
export GEMINI_API_KEY=...               # optional: probe Gemini

python audit.py --init                  # create the config template
# fill in audit-config.json, then:
python audit.py audit-config.json
```

Any assistant without a key is skipped with a notice. Analysis and extraction always run on Claude. Perplexity is not currently probed.

## Model policy: probe the defaults, at medium effort

Probe sessions always use each vendor's **default-tier model at medium effort**: that's what real buyers are talking to, and it keeps runs fast and cheap. Do not point probes at heavyweight frontier models (Claude Fable/Opus, OpenAI's pro-tier models, Gemini Pro/Ultra).

| Assistant | Probe model | Effort setting |
|---|---|---|
| Claude | `claude-sonnet-5` | `effort: medium` |
| ChatGPT | `gpt-5.5` | `reasoning_effort: medium` |
| Gemini | `gemini-3.5-flash` | default |

Override with `ANTHROPIC_MODEL` / `OPENAI_MODEL` / `GEMINI_MODEL` env vars only when a vendor changes its default model. The analysis/extraction engine (Claude Opus) is separate and intentionally stronger than the probes.

## Pre-flight: usage check and confirmation

Before any session runs, the tool checks every key and reports what each API exposes about remaining usage (rate-limit headroom for Claude and OpenAI; key validity for Gemini; none expose credit balances via API, so it points you at the right dashboard), then shows the planned session count and asks which assistants to include: all, or a subset.

```bash
python audit.py audit-config.json --preflight   # check only, don't run
python audit.py audit-config.json               # check, confirm, run
python audit.py audit-config.json --yes         # skip confirmation (CI)
```

## Reading the results

- **Category never proposed** is the most serious finding: AI doesn't route your ICP's problem to your category. No amount of brand content fixes that until the category-to-problem link exists in public writing.
- **Shortlisted but never recommended:** read the qualifiers and the competitor-preferred reasons. Those are the exact objections your proof points need to answer.
- **No first-party sources cited:** third parties are defining you. The prescription section will tell you what to publish.

## Repository layout

| File | What it is |
|---|---|
| [audit.py](audit.py) | The CLI: config loading, pre-flight, session orchestration, extraction, synthesis, markdown report |
| [journey.py](journey.py) | The buyer: persona construction, framings, the four-stage arc, both pathways, the adaptive-buyer prompt |
| [providers.py](providers.py) | Model providers (Claude, ChatGPT, Gemini): default-tier model policy, retries, retrieval mode, pre-flight checks |
| [report_html.py](report_html.py) | Renders an audit's JSON into a designed, self-contained HTML report |
| [example-config.json](example-config.json) | Fully worked example config (Gong as demo subject; swap in any B2B brand) |
| [audits/gong/](audits/gong/) | Real output from a live run of the example config (`.md`, `.json`, designed `.html`) |
| [audits/hyperbound/v1/](audits/hyperbound/v1/) | First Hyperbound audit: scripted 8-turn journey, thin ICP |
| [audits/hyperbound/v2/](audits/hyperbound/v2/) | Re-run on the adaptive engine: generative buyer, branching pathways, enriched ICP |
| [BUILD_LOG.md](BUILD_LOG.md) | How this tool was built: version history, findings from live runs, design principles |

## Scope and honesty notes

- Built for **B2B**: the persona models an accountable buyer working through a real evaluation, not a consumer impulse purchase.
- One ICP per audit keeps the comparison clean: session differences are model and scenario differences, not persona differences. Another ICP is another config file.
- API models are proxies for the consumer apps (the apps add retrieval and memory). Treat results as a strong signal of the model's beliefs, not a pixel-perfect replay of chatgpt.com.
- A few sessions is a probe, not a census. Re-run monthly; model updates move these answers.

MIT licensed. Built by [Dhruv Walia](https://github.com/d-walia).
