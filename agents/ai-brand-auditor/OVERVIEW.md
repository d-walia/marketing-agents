# The AI Brand Perception Audit: Product Overview

Working draft. This is the skeleton for the overview deck: each section carries the core argument and the evidence behind it. Refine here first, then convert to slides.

---

## 1. What is Agentic Buying

**The shift:** B2B buyers are delegating the early stages of buying to AI assistants. Instead of searching, reading ten tabs, and forming their own shortlist, they describe their problem to ChatGPT, Claude, or Gemini and let the assistant diagnose it, propose a solution category, name vendors, and defend a recommendation.

**What actually happens in an agentic buying conversation:**

1. The buyer describes a business pain in their own words. No category, no vendor names.
2. The AI decides what kind of problem it is hearing, and whether a product category is even the answer.
3. The AI proposes a shortlist, ranks it, and attaches reasons.
4. The buyer pushes back the way real buyers do: price, incumbents, proof. The AI either defends its pick or switches.
5. The buyer walks into demos with a favorite, an objection list, and a set of beliefs about every vendor, none of which any vendor saw happen.

**The trajectory:** today this is a human consulting an AI advisor. The endpoint is Agent-to-Agent Commerce: the buyer's agent evaluating vendors, requesting proof, and negotiating with the seller's agent directly. Every stage of that trajectory runs on the same underlying asset: what the AI believes about your brand.

**The one-line definition:** agentic buying is when the decisive moments of a purchase happen inside an AI conversation the vendor never sees.

---

## 2. Why Marketers and CEOs Should Care

**There is now a funnel above your funnel.** By the time a buyer books a demo, an AI conversation may have already decided which categories were considered, who made the shortlist, and what objections the buyer arrived with. None of it shows up in attribution. Your CRM records the demo request; it does not record that the assistant recommended your competitor first and the buyer overrode it, or that your category was never proposed at all.

**The judge repeats itself at scale.** A human analyst's opinion reaches whoever reads the report. A model's opinion is repeated, nearly verbatim, to every buyer who asks a similar question. One stale belief ("their forecasting is a bolt-on") becomes the opening position in thousands of evaluations.

**The beliefs are unmanaged today.** In every audit we have run, the assistants' verdicts rested on training-data memory and third-party narrative. Zero first-party content shaped any parametric verdict. Models openly admitted their information was "possibly a year or more stale" and told buyers to trust anyone with recent firsthand information over the assistant. Whoever fills that vacuum first, including your competitors, defines you.

**For the CEO specifically:** the existential version of this risk is category routing. If AI does not route your buyer's problem to your category, you are not losing deals to competitors. You are losing them to "fix your process" advice, to incumbent tools the buyer already owns, and to inertia. No sales team can recover a deal that never became a deal.

**Why now:** beliefs compound. Models retrain on a web that AI-influenced buyers are already shaping, and buyer-side agents will inherit these priors. The cost of correcting a wrong belief rises the longer it circulates.

---

## 3. Why GEO/AEO Don't Solve This, and Can Waste Resources

**What GEO/AEO is:** optimizing content so AI answer engines cite and surface it: structured pages, quotable passages, entity markup, tracking whether your brand appears in AI-generated answers. It treats AI as a new search results page to rank in.

**Why that misses the problem:**

**a) Citation is not recommendation.** Being quoted in an answer is not being chosen at the end of a conversation. Our audits repeatedly found brands with perfect visibility and zero conversion: mentioned unprompted in every session, shortlisted in every session, and still not recommended when the buyer forced a final call. Visibility was never the bottleneck. The beliefs were.

**b) It optimizes one moment of the journey, and not the decisive one.** AEO lives where the buyer asks "what tools exist for X": a search-shaped question. But the same buyer, with the same pain, also asks "what do I do about this," "does tooling even solve this," and "what evidence would my CFO need." In our live testing, the same brand won the final call under one phrasing and lost it under another, with the same model, on the same day. Answer-engine placement does not touch three of those four conversations.

**c) The metrics do not connect to decisions, and can point the wrong way.** Share of voice in AI answers, mention counts, and citation rates measure presence, not persuasion. They cannot tell you which objection blocks the recommendation, who the model defects to under pressure, or what evidence would flip the verdict. Worse, they can be actively misleading: a mention where the model describes you *negatively* still registers as positive volume and share of voice. Engagement in a topic is not intent for your product. You can move every AEO metric, including in the wrong direction, and never know it cost you recommendations.

**d) The waste mechanism is specific.** Models discount vendor-published, marketing-shaped content, and they say so unprompted: "those figures are self-reported, not independently confirmed." Content engineered for extraction reads as exactly the kind of material models discount. Budget spent making discounted content more visible is budget spent amplifying the discount.

**What AEO is still good for:** being findable and accurately described is table stakes, and worth basic hygiene. It just does not win the conversation that decides the deal.

---

## 4. What AI Brand Management Is, and How It's Different

**Definition:** AI Brand Management makes what AI models believe and recommend about your brand match your real strengths and proof, across the whole buying conversation: from whether your category gets proposed, to whether you survive pushback, to what evidence the model needs before choosing you.

**The difference in one line:** GEO/AEO asks "does AI see us?" AI Brand Management asks "when a buyer asks, does AI choose us, and if not, what exactly would change its mind?"

| | GEO / AEO | AI Brand Management |
|---|---|---|
| Object of work | Citations and visibility in AI answers | The model's beliefs and buying verdicts |
| Unit of analysis | Pages, snippets, mentions | Full buying conversations, end to end |
| Stage of the journey | The search-shaped moment | Problem framing through final call under pressure |
| Method | Content structuring and tracking | Simulated buyer journeys across models, framings, and scenarios |
| What it measures | Presence (share of answers, citations) | Conversion (shortlist rate, recommendation strength, final calls, dealbreakers) |
| Output | Visibility dashboard | Belief inventory, objection map, flip conditions, venue-level content brief |
| Fails when | You are visible but not chosen | Nothing structural: it measures the choosing itself |

**The measurement layer, in brief:** the audit poses as your real ICP, runs adaptive multi-turn buying conversations against the assistants your buyers use, and never names your category or brand first, so unprompted behavior is what gets measured. It phrases the same pain several ways, pressures every verdict into a final call, and extracts the model's own flip condition: the exact evidence that would reverse its decision, in its words. With retrieval on, it records every source the model actually read, so prescriptions name the venue, not just the proof. (Full mechanics in the [README](README.md) and [BUILD_LOG](BUILD_LOG.md).)

**What the report puts in front of you:**

- **An AI behavior scorecard.** One line per buying conversation: does AI route the problem to your category, does your brand surface inside it, does AI endorse you under pressure. Pass, mixed, or fail. The five-second read for someone who will not open the rest.
- **The evidence graph.** Every belief AI holds about you, traced to what it rests on and who owns that source: your content, an independent source, or stale memory it admits it cannot vouch for. Plus the numbers AI has memorized and repeats, and the specific competitor assets it reaches for as counter-proof. In the first live run against a real brand, only a fifth of the claims traced to the brand's own content, and every first-party source that did appear was flagged by the model as self-reported.
- **Where you fall out of the conversation.** Turn by turn, whether you stay named as the buyer gets specific, or drop out mid-thread while a competitor persists. A loss no first-answer or final-call metric can see.
- **Belief stability.** The same intent, reworded many ways. Claims that survive the rewording are what AI actually believes; claims that appear once are noise a single-prompt tool would have reported as findings. The measured version of the paraphrase-brittleness problem, run on your own brand.
- **The say-versus-believe gap.** Your own positioning, claim by claim, against what AI absorbed, contradicts, or has never heard. That gap is the work.

**The output is a to-do list, not a dashboard:** which beliefs are wrong, which objections actually block deals, what evidence closes each gap, and where to publish it so models encounter it.

---

## 5. Quick Examples: How Recommendations Actually Differ

All examples below are from live audit runs (Gong used as a public demo subject; findings are the models' stated views, not market fact).

**Example 1: same buyer, same pain, four phrasings, different winners.**
A sales leader with slipping forecasts asked the same model about the same problem four ways. "How would you approach this" and "does tooling even solve this" ended in Gong winning the final call. "What tools exist" and "what would my CFO need to see" ended with a competitor winning. An AEO program would count Gong as visible in all four. Only two of the four were wins, and the losing two are invisible to citation tracking.

**Example 2: the real competitor was the tool the buyer already owned.**
When an enablement buyer's installed stack was modeled, the assistant's recommendation became "build this inside the platform you already own, and only buy a specialist if that provably fails." No competitor citation strategy addresses this: the deal was lost to the incumbent-by-default answer. Management work targets the belief that gates the switch ("the incumbent's feature is good enough"), which is only visible when you watch the whole conversation.

**Example 3: the model tells you the exact content to create.**
Pressed on its final call, a model stated its own reversal condition: prove that reps who pass the incumbent's certification still fail on live calls, as a repeating pattern, and it would switch to recommending the specialist. That is a content brief and a pilot design, authored by the judge itself. No visibility metric produces it.

**Example 4: the venue battle.**
With live search enabled, a model researching the category consulted a competitor's published buyer's guide to form its comparison, alongside review sites and independent blogs. Being well-described on your own site did not matter to that conversation; the comparison frame was set by whoever owned the page the model chose to read. Management prescriptions name those venues; visibility metrics do not know they exist.

---

## 6. The Maturity Curve: From AI-Assisted Research to Agent-to-Agent Commerce

Agentic buying is not a single event; it is a curve, and it is moving in one direction. The value of managing AI's beliefs compounds because the same asset (what AI believes about you) gets more decisive at every stage.

**Stage 1, AI-Assisted Research (today).** A human buyer consults an AI advisor to scope the problem, build a shortlist, and pressure-test options, then takes over for demos and the final decision. The AI shapes the frame; the human still closes. This is where most B2B buying already is.

**Stage 2, AI-Led Evaluation (emerging).** The buyer delegates more of the work: the assistant runs the comparison, drafts the RFP questions, filters vendors against stated criteria, and hands the human a near-final recommendation to approve. The human's role shrinks to ratification. The model's beliefs now carry most of the decision.

**Stage 3, Agent-to-Agent Commerce (arriving).** The buyer's agent evaluates vendors, requests proof, and negotiates directly with the seller's agent. Purchases execute with minimal human touch. There is no demo to recover a deal in; the entire evaluation happens agent-to-agent, on the beliefs and proof each side's model holds.

**Why the curve matters for the argument:**

- **The asset is constant, the stakes rise.** At every stage, the deciding input is what AI believes about you. Managing those beliefs is the only work that compounds across all three; visibility optimization was built for a search paradigm that Stage 2 and 3 leave behind entirely.
- **Beliefs set today are inherited forward.** Models retrain on a web that AI-influenced buying is already reshaping, and buyer-side agents will launch with these priors baked in. A wrong belief corrected now is a wrong belief that never propagates into Stage 3.
- **The window is an advantage.** Most competitors are still optimizing for Stage 0 (be findable). Managing beliefs while the curve is early is cheaper and more durable than fighting entrenched priors later.
