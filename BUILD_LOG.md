# Build Log: AI Brand Perception Audit

How this tool went from a one-shot prompt script to a branching, multi-model buyer-journey instrument, in one day of iterations. Each version shipped, ran live, and the findings from real runs drove the next design change. This file is the story; the [README](README.md) is the manual.

## The idea

B2B buying research increasingly happens inside AI conversations. When an ICP describes their problem to ChatGPT, Claude, or Gemini, the assistant decides whether the product's category is even the answer, who makes the shortlist, and who wins. Those verdicts rest on what the model believes about a brand, and no one measures it. The tool poses as the buyer, runs the conversation, and extracts the beliefs, the objections, and the proof that would change the answer.

## Version history

### v1: One-shot probes
Five single-question buyer scenarios (cold start, budget buyer, enterprise, switcher, head-to-head), asked flat, with a structured extraction pass per answer. Worked, but shallow: real buying conversations are multi-turn, and one-shot answers over-reward name recognition.

### v2: The buyer journey
Rebuilt around a multi-turn arc that mirrors how B2B evaluations actually unfold: the buyer describes the pain (no category or vendor names), asks who to shortlist, raises the target brand for a candid take. Three buying-committee personas per assistant. Added the synthesis layer: how AI sees the brand vs competitors, what information drives the opinion, what proof is missing, and prescriptive positioning/content changes.

### v3: One ICP per audit
Running three personas in one audit muddied the comparison: differences between sessions could be persona or model. Switched to a single ICP per audit, run identically across models. Different ICP, different audit.

### v4: The pressure stage
Turn-3 verdicts were uniformly hedged ("qualified"), which hid the real signal. Added a scripted final stage: "would any of those concerns actually stop you? Commit today: them or someone else?" This separates soft objections (dissolve under pushback) from real ones (harden into dealbreakers), and forces a final call. Test runs showed identical "qualified" verdicts splitting into a win and a loss under pressure.

### v5: Config-driven inputs
Moved everything brand-specific into a JSON config with a demanded structure: ICP as role + firmographics + jobs-to-be-done + priorities, and scenarios as concrete moments where those jobs hit a wall, written in the buyer's words. Killed the last category-specific defaults so the tool applies to any B2B product. `--init` writes a guided template.

### v6: Depth per stage
Each stage became question + follow-up (8 turns): prioritization pressure after the problem, top-pick defense after the shortlist, a provenance interrogation after the brand verdict ("what is that assessment based on, how current is it?"), and after the final call, a three-sentence CEO pitch plus the flip condition: the single piece of evidence that would change the assistant's mind. The flip conditions turned out to be the sharpest output in every subsequent run: models state their own decision boundaries, often as falsifiable pilot designs.

### v7: Multi-model, defaults-only, pre-flight
Provider layer for Claude, ChatGPT, and Gemini with a hard model policy: probe each vendor's default-tier model at medium effort, because that's what real buyers talk to (analysis stays on a stronger Claude model, deliberately). Added `--preflight`: key checks, whatever usage data each API exposes, planned session count, and an interactive confirm of which assistants to spend on. Plus resilience learned from real failures: retry with long cool-downs on rate limits, and per-session failure tolerance so one provider outage can't sink a run (failed cells are listed in the report, never silently dropped).

### v8: The adaptive buyer
Replaced scripted follow-ups with a generative buyer: a simulated persona (built from the ICP) reads the assistant's actual answer and writes the follow-up a real person under pressure would, under 90 words, grounded in specifics. The stage arc stays fixed for comparability; the words become natural. Guardrails: the buyer cannot introduce vendor names the assistant hasn't said, and scripted fallbacks keep every run alive. Alongside it, the ICP model got the fields that make a buyer real: **buying moment** (the trigger event and pressure clock), **installed stack** (where coexistence objections come from), and **decision criteria** (proof thresholds the buyer raises unprompted). First run with the enriched model immediately surfaced incumbent-coexistence logic ("build it in the tool we already own first") that thinner configs had never produced.

### v9: Branching pathways
An early unprompted vendor mention isn't noise, it's a finding: the category-to-vendor mapping works for that problem framing. The journey now branches after stage 1. If the assistant names vendors on its own, the buyer follows that thread into a head-to-head comparison of the vendors the assistant put on the table; if not, the buyer opens the vendor conversation (standard pathway). Both are 4 stages / 8 turns, and each session records its pathway. Young categories mostly run standard; established categories mostly branch. Pathway distribution per framing is itself a category-mapping metric.

### v10: Framings and retrieval
Two dimensions that measure the upstream battle:

- **Framings.** The same buyer phrases the same pain four ways: operational ("what do I do?"), platform ("what tools exist?"), methodology ("does tooling even solve this?"), validation ("what evidence justifies budget?"). AI routes these to completely different answers, and which framings unlock the category, and the brand, is a keystone finding. Scenarios opt in per framing; everything else holds constant.
- **Retrieval mode (`--retrieval`).** Default probes measure trained-in beliefs. With retrieval on, Claude and Gemini probe with live web search and the tool records every URL each assistant actually consulted. Prescriptions upgrade from "publish this proof" to "publish this proof in this venue," based on the domains that actually carried the verdict. First live test surfaced a competitor's buyer's guide among the pages consulted to form category opinions: the venue battle is real and measurable.

### The report layer
Reports render three ways: markdown (funnel, mermaid buyer-journey map with drop-off and divert branches, session summaries, synthesis), raw JSON with full transcripts, and a designed self-contained HTML report (`report_html.py`).

## Design principles that emerged

1. **Fixed skeleton, natural flesh.** Hold the stage arc, the ICP, and the extraction schema constant; let the conversation words be generated. Comparability without scripted stiffness.
2. **Measure the judge, not the market.** The output is what AI believes and how it decides, which is decision-relevant precisely because buyers ask these models. Perception data, not market fact, and the reports say so.
3. **Force commitment.** Hedged verdicts hide the signal. The pressure stage, final call, and flip condition exist because "qualified" means nothing until you know what survives pushback.
4. **Unprompted behavior is the gold.** What the assistant does before being steered (proposing the category, naming vendors, choosing sources) is the most valuable measurement; the design protects it (verbatim openings, name-leak guardrails).
5. **One variable at a time.** One ICP per audit, one dominant pain per scenario, framings varied while everything holds. Multi-pain scenarios taught this the hard way: models flip verdicts based on which pain they latch onto.
6. **Single sessions are leads, not verdicts.** Final calls at the margin flip between runs. Durable signal is what repeats across scenarios, framings, and models. (Repeat-runs with rate reporting is the top item on the roadmap.)
7. **Runs must survive reality.** Rate limits, provider outages, and quota exhaustion all happened; retries with real cool-downs and per-session failure tolerance came from those failures.

## What a finished audit answers

- Does AI route my buyer's problem to my category at all, and under which question framings?
- Do I surface unprompted? Where do I rank, and who beats me, for what stated reason?
- What does AI believe about me, whose information is that (mine, third parties', stale memory), and which venues does it actually consult when it can look?
- Which objections dissolve under pushback and which harden into dealbreakers?
- What is the exact evidence, in the model's own words, that would flip the verdict, and where should it be published?

## Roadmap

- Repeat runs per cell (`--runs N`) with final-call rates instead of single calls
- ChatGPT retrieval once wired (and funded); Perplexity as a fourth surface
- Longitudinal diffing: same config re-run monthly, report deltas
- Finish the de-templated HTML report restyle
