---
name: brand-extractor-v2
description: Extract a company's brand system (colors, type, spacing, components, voice) from its live website or codebase into a reusable brand file for page mocking. Use whenever Dhruv asks to capture, extract, or build a brand file or brand skill for a company, onboard a new brand for mockups, or asks to mock a page for a brand that has no file yet in the mockup suite. This is half of the Landing Page Builder suite in the marketing-agents repo — its output feeds the page-mockup-v2 skill, which consumes the brand files this skill writes to ../page-mockup/brands/. V2, repo-hosted and research-hardened: prefer it over the v1 brand-extractor when both are installed.
---

# Brand Extractor

Capture a brand once, into one markdown file, so every future mock is a single generation pass instead of a re-derivation of the design system. The core framing (Superposition's): **the production site already contains the design system — extract, don't invent.**

Output goes to `../page-mockup/brands/<brand-slug>.md`, following `../page-mockup/brands/_TEMPLATE.md`. One file per brand; re-running updates the existing file (preserve sections marked `<!-- hand-edited -->` — hand edits win).

## Sources, in order of fidelity

1. **Codebase** — repo is local: read the actual CSS/tokens. Highest fidelity. Still screenshot the live site for the visual ground truth.
2. **Live site** — Browser tools. Run **two complementary passes**, never just one:
   - **Authored pass** (parse stylesheets via CSSOM): recovers `:root` custom properties with their semantic names, hover/focus states, `@media` breakpoints, dark-mode blocks, authored hex/`clamp()` values. Cross-origin sheets throw SecurityError on `.cssRules` — catch it, collect the blocked `sheet.href`s, and fetch those as raw text instead.
   - **Computed pass** (`getComputedStyle` on ~10 role-representative elements): ground truth for what actually renders. Expect resolved values — colors come back as `rgb()`, units as px, shorthands expanded; recover hex, alpha, and `clamp()` fluid type from the authored pass. Never select by class name on CSS-in-JS/utility sites (hashed classes carry no meaning); select by tag, role, or visible text. On Tailwind sites, reverse-map utilities (`bg-indigo-600`, `rounded-xl`) straight to values.
3. **Screenshots only** — last resort; mark every estimated value `(approx)` so mocks built from it aren't mistaken for pixel-true.

Full element sampling list, per-element properties, state-capture tactics (hover/dark/mobile/scroll), and scale-inference method: **read [references/extraction-playbook.md](references/extraction-playbook.md) before extracting.**

## What to capture (the template enforces this)

- **Tokens by semantic role**, not a flat color list — page bg, surface, primary text, muted text, CTA, CTA hover, link, border — with the site's own variable names when it has them. Sanity check: **>15 unique colors means you sampled noise**, not a system.
- **Shadows and gradients verbatim** — record the full `box-shadow`/`linear-gradient(...)` strings; layered shadows are brand signatures and approximations read as off.
- **Scales, not raw values** — cluster spacing to 4px multiples, keep the high-frequency survivors, and state the generative rule ("8px base, doubling above 32"); fit heading sizes to a modular ratio so unobserved levels (an h5 the homepage never used) can be generated consistently.
- **Breakpoints and motion** — the 3–5 real `@media` widths; default transition duration/easing and hover transforms. Duration and easing are first-class tokens (Project Wallace's taxonomy) that ad-hoc extraction always skips.
- **Components as token-referencing CSS recipes** including the **hover delta on its own line** ("hover: bg → #1e40af, translateY(-2px), 150ms") — brand feel lives disproportionately in interaction details a static pass misses.
- **Fonts with license status** — Google-hosted fonts can be linked; commercial fonts cannot be rehosted: record the family plus a metric-matched substitute (matched weight, letter-spacing, similar x-height) so line-breaks survive substitution.
- **Logo** — grab the SVG from the DOM (inline or `<img src>`). Hero photography/illustration: never hotlink; record aspect ratio and treatment (radius, overlay, shadow) for placeholder reconstruction.
- **Voice** — the deepest section; see below.

## Voice extraction

Voice is what makes copy-in-place mocks feel true-to-life, and it's the part screenshots can't give you. Method (playbook has the full checklist):

- **Sample a spread of page types**, not just the homepage: hero, one product/feature page, pricing, a blog post, and one low-stakes surface (404, empty state, footer microcopy). The hero is the most polished and least representative single page; **pricing and error states are the stress tests** — they show how the brand talks about money and what its formality floor is.
- **Promote a pattern to a rule only if it appears on 2+ page types**; seen once → record as a page-specific tone note. This is the anti-overgeneralization mechanism: one clever 404 line does not make a witty brand.
- **Every rule carries a verbatim quote** from real published copy with its source page. First-party, edited copy only — never guest posts or press releases.
- **Capture voice (constant) and tone-by-page-type (contextual) separately** — the register table in the template. An AI given only voice uses hero register on every surface.
- **Write do/don't pairs where the "don't" is the plausible near-miss an AI would produce** ("Unlock the power of seamless…"), not a strawman.
- **Capture absence patterns** — what never appears in the copy (superlatives? competitor names? exclamation points?) becomes the banned list.
- **Tag each rule's confidence**: `[3+]` observed three-plus times, `[1]` observed once, `[inf]` inferred — so the mock builder knows which rules are load-bearing.
- **Flag inconsistencies, don't average them.** If the homepage and blog sound like different companies, surface the conflict and ask Dhruv which surface is canonical.

## Verification (required before calling it done)

1. Screenshot the live site at desktop (~1280px) and mobile (~375px).
2. Have `page-mockup` rebuild one existing section of the site **from the brand file alone** — no peeking at the source.
3. Compare rebuild vs. screenshot; every visible mismatch is a gap in the brand file. Fix the file, not the mock, and iterate until the diff is honest noise (imagery, live data).

## Calibration

- Capture what the site *does*, not what a brand-guideline PDF says it should do — mocks must match the live site.
- Budget: 15–25 minutes with verification. The brand file must be complete enough that `page-mockup` never needs to open the source site.
- Date-stamp everything in the Sources section; voice and tokens drift with rebrands, and staleness must be visible.
