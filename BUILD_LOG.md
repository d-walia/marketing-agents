# Build Log: AI Brand Perception Audit

How this tool went from a one-shot prompt script to a branching, multi-model buyer-journey instrument, in one day of iterations. Each version shipped and ran live; findings from real runs drove the next change. This file is the story; the [README](README.md) is the manual.

## The idea

B2B buying research increasingly happens inside AI conversations. When an ICP describes their problem to ChatGPT, Claude, or Gemini, the assistant decides whether the product's category is even the answer, who makes the shortlist, and who wins. Those verdicts rest on what the model believes about a brand, which no one measures. The tool poses as the buyer, runs the conversation, and extracts the beliefs, the objections, and the proof that would change the answer.

## Version history

### v1: One-shot probes
Five single-question buyer scenarios (cold start, budget buyer, enterprise, switcher, head-to-head), asked flat, with a structured extraction pass per answer. Shallow: real buying conversations are multi-turn, and one-shot answers over-reward name recognition.

### v2: The buyer journey
Rebuilt around a multi-turn arc that mirrors how B2B evaluations actually unfold: the buyer describes the pain (no category or vendor names), asks who to shortlist, raises the target brand for a candid take. Three buying-committee personas per assistant. Added the synthesis layer: how AI sees the brand vs competitors, what information drives the opinion, what proof is missing, and prescriptive positioning/content changes.

### v3: One ICP per audit
Three personas per audit muddied the comparison: session differences could be persona or model. Switched to one ICP per audit, run identically across models; another ICP is another audit.

### v4: The pressure stage
Turn-3 verdicts were uniformly hedged ("qualified"), hiding the signal. Added a scripted final stage: "would any of those concerns actually stop you? Commit today: them or someone else?" This separates soft objections (dissolve under pushback) from real ones (harden into dealbreakers), and forces a final call. In test runs, identical "qualified" verdicts split into a win and a loss under pressure.

### v5: Config-driven inputs
Moved everything brand-specific into a JSON config with a demanded structure: ICP as role + firmographics + jobs-to-be-done + priorities, and scenarios as concrete moments where those jobs hit a wall, written in the buyer's words. Killed the last category-specific defaults so the tool applies to any B2B product. `--init` writes a guided template.

### v6: Depth per stage
Each stage became question + follow-up (8 turns): prioritization pressure after the problem, top-pick defense after the shortlist, a provenance interrogation after the brand verdict ("what is that assessment based on, how current is it?"), and after the final call, a three-sentence CEO pitch plus the flip condition: the single piece of evidence that would change the assistant's mind. Flip conditions proved the sharpest output in every later run: models state their own decision boundaries, often as falsifiable pilot designs.

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

### v10.5: Output hygiene and house style
Smaller work, but it changed every artifact the tool produces.

**The designed HTML report** (`report_html.py`) renders an audit's JSON as a self-contained page: masthead with the ICP and coverage, the funnel as horizontal bars with the failed stage in red, one card per session with colour-coded verdict chips, then the synthesis as designed prose and tables. No dependencies, no external assets; open it, print it to PDF, or email it.

**Restyled to stop looking machine-made.** The first version used a teal accent with green/amber/red status chips throughout, which reads as generic dashboard. Replaced with a near-monochrome treatment: a cool near-white ground, a single restrained red reserved for outright failures, square-edged bordered chips instead of pills, and monospace for every number and label so data reads as instrumentation. Serif headlines, adaptive to dark mode and mobile.

**Em dashes scrubbed at render time.** House style forbids them, but the synthesis and extracted fields are model-written and the model uses them freely. Rather than fight the prompt, both renderers normalize on the way out: `report_html.py` scrubs during escaping, `audit.py` scrubs the assembled markdown before writing. Generated reports match the house style regardless of what the model produced.

**Reports organized by subject.** Output moved from flat filenames at the repo root into `audits/<brand>/`, with versioned subfolders where a brand was audited more than once (`audits/hyperbound/v1/`, `/v2/`). Each folder is self-contained: the config that produced the run sits beside its report and raw data, so any result can be reproduced or diffed against a later run.

### v11: The scorecard and the evidence graph
Comparing the tool's output against a boutique agency's hand-built read of the same brand exposed what a rigorous funnel still fails to deliver: a verdict a busy executive can absorb, and source-level accountability for every belief. Six additions, in three groups.

**Compression.** An **AI behavior scorecard** sits above the funnel: one row per session, three verdicts (category, visibility, recommendation), PASS / MIXED / FAIL. Computed from data already collected, so it costs nothing. Rendered per scenario-framing cell rather than collapsed into one row for the whole audit, which preserves the finding that a brand can score CATEGORY FAIL under one framing and PASS under another.

**Source-level accountability.** The extraction schema grew an **evidence chain**: every substantive claim traced to what it rests on and who owns that source (first-party, third-party, training memory, unstated), plus whether the assistant caveated it. Alongside it, **quantified claims** (the specific numbers AI has memorized and repeats), **citation depth** (deep product pages vs homepage-only vs no URLs), and a **competitor counter-evidence map** (named rival assets AI reached for, and the criterion each one won). The first live retrieval run made the case: only 19% of claims about the brand traced to its own content, every first-party source that did appear was flagged by the assistant as self-reported, and five specific competitor assets were named as counter-proof, including a rival's Forrester study and a competitor blog's TCO comparison.

**Where the conversation narrows.** A **presence trace** records, turn by turn, whether the brand is named and how many rivals appear alongside it. A brand can lead turn 1 and vanish by turn 2 while competitors persist: a mid-conversation loss invisible to both first-answer and final-call metrics. Deliberately not extracted by a model but measured locally from the completed transcript, so it is deterministic and free. Computed once after each session and stored in the session record, which makes it diffable month over month; a transcript-scan fallback keeps it working on reports generated before the field existed.

### The report layer
Reports render three ways: markdown (scorecard, funnel, mermaid buyer-journey map with drop-off and divert branches, presence trace, evidence graph, session summaries, synthesis), raw JSON with full transcripts, and a designed self-contained HTML report (`report_html.py`).

## Design principles that emerged

1. **Fixed skeleton, natural flesh.** Hold the stage arc, the ICP, and the extraction schema constant; let the conversation words be generated. Comparability without scripted stiffness.
2. **Measure the judge, not the market.** The output is what AI believes and how it decides, which is decision-relevant precisely because buyers ask these models. Perception data, not market fact, and the reports say so.
3. **Force commitment.** Hedged verdicts hide the signal. The pressure stage, final call, and flip condition exist because "qualified" means nothing until you know what survives pushback.
4. **Unprompted behavior is the gold.** What the assistant does before being steered (proposing the category, naming vendors, choosing sources) is the most valuable measurement; the design protects it (verbatim openings, name-leak guardrails).
5. **One variable at a time.** One ICP per audit, one dominant pain per scenario, framings varied while everything holds. Multi-pain scenarios taught this the hard way: models flip verdicts based on which pain they latch onto.
6. **Single sessions are leads, not verdicts.** Final calls at the margin flip between runs. Durable signal is what repeats across scenarios, framings, and models. (Repeat-runs with rate reporting is the top item on the roadmap.)
7. **Runs must survive reality.** Rate limits, provider outages, and quota exhaustion all happened; retries with real cool-downs and per-session failure tolerance came from those failures.
8. **Measure locally when you can.** The presence trace is computed by scanning the completed transcript, not by asking a model. Deterministic, free, and retroactive: it produced findings on data collected days before the feature existed. Prefer local computation over extraction whenever the signal is mechanically detectable.
9. **Compress for the reader who will not read.** A rigorous funnel is not a verdict. The scorecard exists because the person who decides whether to act on an audit will give it five seconds, and the analysis underneath is worthless if that read never happens.
10. **Trace beliefs to their owners.** "AI thinks X" is an observation. "AI thinks X because of a competitor's blog post, and flagged your own case study as self-reported" is an instruction. Provenance is what turns perception data into a content brief.

## What a finished audit answers

- Does AI route my buyer's problem to my category at all, and under which question framings?
- Do I surface unprompted? Where do I rank, and who beats me, for what stated reason?
- What does AI believe about me, whose information is that (mine, third parties', stale memory), and which venues does it actually consult when it can look?
- Which objections dissolve under pushback and which harden into dealbreakers?
- What is the exact evidence, in the model's own words, that would flip the verdict, and where should it be published?
- Do I hold the conversation as the buyer gets specific, or get dropped mid-thread while rivals persist?
- Which of my own claims has AI memorized and repeats verbatim, and which of them does it caveat as self-reported?
- Which named competitor assets does AI reach for as counter-proof, and on what criterion do they win?

## Roadmap

- Repeat runs per cell (`--runs N`) with final-call rates instead of single calls
- ChatGPT retrieval once wired (and funded); Perplexity as a fourth surface
- Longitudinal diffing: same config re-run monthly, report deltas. The stored presence records and evidence chains are built for this
- Surface run metadata (retrieval on/off, failed cells) in the HTML report
- Verify extracted figures against source: the tool captures what AI says, including claims that may be wrong
