---
name: page-mockup-v2
description: Build a true-to-life, on-brand HTML mock of a web page (hero variant, pricing page, landing page, homepage section) with real copy in place, using a saved brand file — the "propose web updates with a mock, not a screenshot stitch" workflow. Use whenever Dhruv asks to mock up a page, prototype a web page or section, build a branded landing page draft, show a before/after of a web change, or visualize new positioning copy on a site. This is half of the Landing Page Builder suite in the marketing-agents repo — if the brand he names has no file in brands/, run the brand-extractor-v2 skill first to create one. V2, repo-hosted and research-hardened: prefer it over the v1 page-mockup when both are installed.
---

# Page Mockup

Turn copy + a page intent into a full, on-brand HTML page mock, published as a private Artifact link Dhruv can share when proposing web updates. The audience is stakeholders making a ship/no-ship call: the mock is a **persuasion and evaluation artifact**, and its credibility is the product. "Close" colors and near-miss fonts are the fastest credibility killer for people who look at their own brand daily.

## Inputs

1. **Brand** — a file in `brands/`. If the brand has no file, run `brand-extractor` first; never improvise a brand from memory.
2. **Page intent** — what page/section and what job it does, plus **the decision it's for**: "which direction?" tolerates lower polish; "ship this?" demands full fidelity. One idea per mock — a mock demonstrating three unrelated changes gets three diluted verdicts.
3. **Copy** — write or get the copy **before** laying out. Real, final-intent copy only; lorem ipsum hides layout failures and prevents stakeholders from evaluating the message, which for this audience *is* the change. If Dhruv gives only positioning notes, draft the copy from the brand file's voice section (run its pre-return self-check), and label it DRAFT.

## Process

1. **Read the brand file fully.** It is the single source of truth. Follow its register table for the page type (hero copy ≠ pricing copy ≠ error copy). If the mock needs a component the file lacks, derive it from the file's primitives and note the derivation so the brand file can be extended — don't invent tokens.
2. **Build the full page chrome** — real nav, footer, logo placement — not a floating section. Stakeholders judge "does this look like our site?" in the first seconds. One self-contained HTML file in the scratchpad, CSS inlined from the brand tokens, no external requests (Artifact CSP blocks them anyway).
3. **Mixed fidelity is a steering tool:** anything unresolved gets deliberately reduced fidelity (grayscale block, dashed border) **plus a label** ("placeholder image — final asset from brand team"). Unlabeled rough spots read as forgotten and tank the whole mock; labeled ones steer attention where you want it.
4. **Images and logos you don't own:** structured stand-ins, never lifted assets — full rules in [references/quality-gates.md](references/quality-gates.md). Match the placeholder's tonal value to the intended asset so text-over-image contrast evaluates truthfully. No real third-party logos, no real people's photos: a stakeholder screenshotting the mock into a deck turns your placeholder into a public claim.
5. **Load `artifact-design`**, publish with the Artifact tool. One artifact per page concept; iterations redeploy the same file path so the share URL stays stable.

## Variants (before/after, A/B)

- **Full-page change → Current/Proposed toggle** on one page: both states render at true size in true context (side-by-side at 50% scale misrepresents type sizes and fold position).
- **Section-level change → side-by-side** at desktop width, stacked at mobile.
- **Lead with the "after," anchor with the "before"** — the delta is the argument; never omit the before.
- **Max 2–3 variants.** Beyond that stakeholders satisfice or request a Frankenstein merge.
- **Persistent visible badges** on each variant ("Current — live today" / "Proposed — B"), not just intro text: screenshots travel without their context.
- **Annotate what changed *and why*** ("Moved CTA above fold: most viewing time concentrates there") — stakeholders approve reasoning, not pixels. Keep annotations visually separate (numbered pins or a toggleable rail) so the mock also views clean.
- Show mobile and desktop states of the proposed variant near each other; the responsive story is part of the pitch.

## Quality gates — run the full checklist in [references/quality-gates.md](references/quality-gates.md) before sharing any link

Non-negotiables: responsive pass at ~375px and ~1280px; WCAG AA contrast (4.5:1 body, 3:1 large — low-contrast hero text is the failure non-experts *notice*); `text-wrap:balance` on headlines (one orphaned word makes the whole mock look untuned); no dead-looking links (`href="#"` jumps are worse than none); no visible placeholder artifacts; body ≥16px; copy proofread to production standard — a typo is the one defect every reviewer is qualified to catch, and for a marketing audience it's disqualifying. Verify the actual share URL renders before sending it.

## Iteration

- **One stable URL per mock, redeployed in place** — a new URL per version fragments the discussion and leaves people reviewing stale copies.
- **Visible version stamp on the page** ("v3 · Aug 13" in the footer/rail) so forwarded screenshots self-identify their vintage.
- **Stakeholder-readable changelog** on or linked from the mock, logging the *decision rationale*, not just the diff ("reverted to single CTA: two CTAs split attention") — it proves feedback was incorporated and stops settled points from re-litigating.
- **Batch feedback into rounds** rather than live-editing per comment; close each round by stating what's incorporated vs. still open.
- Snapshot superseded major variants (keep the old variant section, collapsed/linked) so "what did the old B look like?" is answerable.

## Copy rules (Dhruv's, layered on top of any brand file)

- No em dashes in on-page copy.
- Consequence-forward: headlines carry the "so what," not just the feature.
- Never invent stats, customer names, or testimonials — placeholder slots or claims present in source material only. Hallucinated proof points are a brand-safety failure worse than any tone miss.
- Anything Dhruv presents externally: offer `copy-optimizer` (and `ai-detector` if public-facing) before he ships.

## Brand files

Live in `brands/`. `_TEMPLATE.md` defines the format; `brand-extractor` writes new ones; hand edits win over re-extraction.
