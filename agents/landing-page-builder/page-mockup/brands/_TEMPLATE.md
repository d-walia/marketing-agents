# Brand: <Name>

<!-- One file per brand. brand-extractor writes it; hand edits win — mark
     hand-edited sections with <!-- hand-edited --> so re-extraction preserves them.
     Confidence tags used throughout: [3+] observed 3+ times · [1] observed once · [inf] inferred. -->

## Sources
- <repo path / URL / screenshot> — extracted <YYYY-MM-DD>, method: <codebase | two-pass live | screenshots (approx)>
- Reference screenshots: `<slug>-desktop.png`, `<slug>-mobile.png` (ground truth for rebuild verification)

## Tokens
```css
:root {
  /* Colors BY SEMANTIC ROLE, using the site's own variable names when it has them:
     page bg, surface/card, primary text, muted text, CTA, CTA hover, link, border.
     >15 unique colors = extraction sampled noise; re-cluster. */

  /* Shadows & gradients VERBATIM — full box-shadow / linear-gradient() strings. */

  /* Motion: default transition duration + easing; hover transform pattern. */
}
/* Layout: container max-width + gutter, section vertical padding, base size/line-height. */
```

**Fonts:** <family + weights actually used> · License: <Google-linkable | commercial, do-not-rehost>
Fallback stack for CSP-restricted mocks: <metric-matched substitute + what carries the identity (weights/tracking/casing)>

**Breakpoints:** <the 3–5 real @media widths>

## Scales
- **Spacing:** <generative rule, e.g. "8px base, doubling above 32"> — evidence: <observed values>
- **Type:** <base size + modular ratio, e.g. "17px base, ~1.25 ratio"> — evidence: <observed sizes>

## Type scale
| Element | Family | Weight | Size | Letter-spacing | Casing |
|---|---|---|---|---|---|
| h1 | | | | | |
| h2 | | | | | |
| h3 | | | | | |
| body | | | | | |
| label/meta | | | | | |

## Components
<!-- One paste-ready CSS recipe per recurring pattern, written against the tokens above.
     Each recipe ends with its hover/focus delta on its own line — interaction details
     carry brand feel and are what static extraction misses. -->

### Nav
```css
```
<!-- Note scroll-state change if any (transparent → solid + shadow). -->

### Hero composition
```css
```
<!-- Text/media split ratio, background treatment, eyebrow pattern. -->

### Buttons (primary / secondary)
```css
/* hover: ... */
```

### Card
```css
/* hover: ... */
```

### Section header pattern
```css
```

### Footer
```css
```

## Voice

**Persona:** <one sentence — "writes like…">
**Anti-persona:** <one sentence — "never like…">

**Tone sliders:** funny <pos> serious · formal <pos> casual · respectful <pos> irreverent · enthusiastic <pos> matter-of-fact

**Traits (3–5, each with means / doesn't-mean + verbatim quote):**
1. <trait> — means: … · doesn't mean: … · "<quote>" (<page>) [3+]

**Mechanics:** POV/self-naming (we vs product name; "the" before product?), reader naming, contractions y/n, capitalization scheme, punctuation habits (em dashes, exclamations/page, oxford comma, ampersands, periods in headlines), sentence rhythm, hedging posture (asserts vs qualifies), CTA verb style.

**Vocabulary:**
- Always (signature terms, ≤1 use per page): …
- Sometimes (term — context rule): …
- Never (brand bans + standing AI-slop bans: delve, leverage, unleash, unlock, seamless, robust, elevate, empower, game-changing, "in today's fast-paced world"): …

**Do / don't pairs (don'ts = the plausible AI near-miss, not a strawman):**
- Do: "<real-copy-shaped line>" / Don't: "<the slop the model would write>"

**Register table:**
| Page type | Tone adjustment | Example line |
|---|---|---|
| Hero | | |
| Feature | | |
| Pricing | | |
| Error/empty | | |

**Exemplars (5–15, dated + sourced, incl. 1–2 FULL paragraphs for rhythm):**
> "<paragraph>" — <page>, <date>

**Pre-return self-check for generated copy:** banned-word scan → register matches page type → every claim traceable or placeholder → would it pass blind-mixing with the exemplars?

## Notes
<!-- Anything a mock builder would otherwise get wrong; flagged inconsistencies
     (surfaces that sound like different companies) and which surface is canonical. -->
