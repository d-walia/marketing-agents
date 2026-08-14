# Brand: DW Digital (dw-digital-consulting.com)

<!-- Confidence tags: [3+] observed 3+ times · [1] observed once · [inf] inferred. -->

## Sources
- Repo: `~/github/portfolio-website` (`app/globals.css`, `app/page.tsx`, `app/layout.tsx`) — extracted 2026-08-13, method: codebase (pixel-true).
- Reference screenshots: not yet captured — take live-site shots at 1280px/375px before the first verification rebuild.

## Tokens
```css
:root{
  /* semantic roles */
  --ink:#1c1c1c;      /* headings, CTA, strongest text */
  --body:#2b2b2b;     /* body text */
  --mid:#6a6a6a;      /* secondary text, nav links, taglines */
  --faint:#9a9a9a;    /* tertiary/colophon text */
  --rule:#c7cbd1;     /* borders, dividers */
  --bg:#e8eaee;       /* page background */
  --bg-alt:#dcdfe4;   /* alternating section background */
  --card:#fafbfc;     /* card/surface background */
  --accent:#111111;   /* darkest accent (btn.solid hover → #000) */

  /* shadows & gradients — verbatim */
  /* card hover: box-shadow:0 10px 28px rgba(30,35,40,.09) */
  /* hero bg:    linear-gradient(180deg,#f0f1f4 0%,#dfe2e7 100%) */
  /* footer bg:  linear-gradient(180deg,#dfe2e7 0%,#e8eaee 100%)  (hero inverted) */
  /* nav bg:     rgba(232,234,238,.92) + backdrop-filter:blur(8px) */

  /* motion */
  /* links/buttons/chips: .15s (all or color); cards: .2s on border-color, box-shadow, transform */
  /* hover transform pattern: translateY(-2px) on cards only */
}
/* Layout: .wrap{max-width:880px;padding:0 28px} · section{padding:76px 0} · body 17px/1.65 */
```

**Fonts:** Lato 100/300/400/700 (display + body), Raleway 500/600 (labels/nav/buttons) · License: both on Google Fonts (site loads via jsdelivr Fontsource) — linkable, but Artifact CSP blocks external hosts.
Fallback stack for CSP-restricted mocks: `'Lato',-apple-system,'Helvetica Neue',Arial,sans-serif` and `'Raleway','Lato',Arial,sans-serif`. The identity survives fallback because it lives in the thin/light weights, wide tracking, and uppercase casing, not the exact face.

**Breakpoints:** 640px (nav, stack rows) and 700px (grids → 1 col). Two real breaks only.

## Scales
- **Spacing:** no strict 4/8 grid — hand-tuned values clustering at 14/18/26–30 (component gaps/padding) and 58/76/96 (chrome/section rhythm). Rule of thumb: gaps ≈ 26px, card padding ≈ 28–30px, section padding 76px, hero 96px top. Evidence: gap 26/22/24, padding 28–30, sections 76, header 96/72.
- **Type:** 17px base; body sizes step 12 → 12.5 → 13.5 → 14 → 15 → 15.5 → 17 → 18 (dense, ~1.08 micro-steps — this brand differentiates with many small sizes, not a big ratio); display jumps to 26 (h2) and clamp(44px,8vw,72px) (h1). [3+]

## Type scale
| Element | Family | Weight | Size | Letter-spacing | Casing |
|---|---|---|---|---|---|
| h1 | Lato | **100 (thin)** | clamp(44px,8vw,72px), color #000 | .02em | Title |
| h2 | Lato | 300 | 26px | .26em | UPPERCASE |
| h3 | Raleway | 600 | 17px | normal | Title |
| body | Lato | 300 | 17px / 1.65 | normal | Sentence |
| label/meta/nav | Raleway | 500–600 | 12–13.5px | .06–.14em | UPPERCASE |

Signature moves: hairline h1; wide-tracked uppercase h2 with 46×2px ink underline (`h2::after{content:'';display:block;width:46px;height:2px;background:var(--ink);margin:16px 0 18px}`); fully monochrome — hierarchy from weight and gray steps, never color.

## Components

### Nav (sticky, blurred)
```css
nav{position:sticky;top:0;background:rgba(232,234,238,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--rule);z-index:10}
nav .wrap{display:flex;justify-content:space-between;align-items:center;height:58px}
.nav-name{font-family:'Raleway';font-weight:600;font-size:14px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);text-decoration:none}
nav a{font-family:'Raleway';font-weight:500;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--mid);text-decoration:none;padding-bottom:4px;border-bottom:1px solid transparent}
/* hover: color → var(--ink), border-bottom-color → var(--ink), .15s */
```
No scroll-state change (always translucent + blur).

### Hero composition
```css
header{padding:96px 0 72px;text-align:center;border-bottom:1px solid var(--rule);background:linear-gradient(180deg,#f0f1f4 0%,#dfe2e7 100%)}
.tagline{font-family:'Raleway';font-weight:500;font-size:15px;letter-spacing:.22em;text-transform:uppercase;color:var(--mid);margin-top:18px}
.hero-sub{max-width:620px;margin:26px auto 0;font-size:18px;color:var(--body)}
.hero-cta{margin-top:34px;display:flex;gap:14px;justify-content:center;flex-wrap:wrap}
```
Centered, text-only hero — no media split, no imagery.

### Buttons (primary = .solid, secondary = outlined)
```css
.btn{font-family:'Raleway';font-weight:600;font-size:12px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none;padding:13px 26px;border:1px solid var(--ink);color:var(--ink);transition:all .15s}
.btn.solid{background:var(--ink);color:#fff}
/* hover: outline → filled ink/white text; solid → #000. NO border-radius — squares are the look. */
```

### Card (2-col grid)
```css
.grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.card{border:1px solid var(--rule);background:var(--card);padding:30px 28px;display:flex;flex-direction:column;transition:border-color .2s,box-shadow .2s,transform .2s}
.card .result{margin-top:auto;padding-top:14px;border-top:1px solid var(--rule);font-size:14px;color:var(--mid)}
/* hover: border-color → #a9b0b8, box-shadow → 0 10px 28px rgba(30,35,40,.09), translateY(-2px), .2s */
```
Bottom rows (`.result`, `.chips`) pin with `margin-top:auto` so paired cards align — keep in any new variant.

### Section header pattern
Uppercase tracked h2 + ink underline (::after above) + `.lede{max-width:660px;font-size:17.5px;margin-bottom:40px}`. Alternate sections use `section.alt{background:var(--bg-alt)}`.

### Footer
```css
footer{padding:80px 0 60px;text-align:center;border-top:1px solid var(--rule);background:linear-gradient(180deg,#dfe2e7 0%,#e8eaee 100%)}
.colophon{font-size:13px;color:var(--faint);max-width:520px;margin:0 auto;line-height:1.7}
```

## Voice

**Persona:** A practitioner showing receipts — explains what he built and what it did, plainly, like a colleague walking you through his work.
**Anti-persona:** Never a personal-brand LinkedIn bio — no "results-driven leader," no third-person self-narration, no hype adjectives.

**Tone sliders:** serious (dry, occasional understatement) · casual-professional (contractions yes, slang no) · respectful · matter-of-fact (enthusiasm shown through specifics, never exclamation points).

**Traits:**
1. **Evidence-anchored** — means: claims end in an outcome, number, or mechanism · doesn't mean: stat-stuffing every line · "using AI to move faster than the team size would suggest" (about lede) [3+]
2. **Plain first person** — means: "I built," "my agents" · doesn't mean: falsely modest; he states scope directly · "Custom agents I've built with Claude to solve real GTM challenges" (agents lede) [3+]
3. **Structurally clever, verbally literal** — means: wit lives in structure (the × mark, the h2 underline, terse titles); sentences stay literal · doesn't mean: wordplay or puns in copy · "Product Marketing × AI × Marketing Engineering" (tagline) [3+]

**Mechanics:** First person "I"; reader rarely addressed directly (portfolio register). Section titles 1–3 words, uppercase via CSS not copy ("Experience", "My AI Stack"). Contractions yes ("I've"). Sentence rhythm: mid-length with concrete nouns; ledes are one or two sentences max. Hedging: asserts, with qualified precision ("skeptical, regulated buyers"). No exclamation points [3+]. No em dashes (house rule — commas and periods instead).

**Vocabulary:**
- Always (≤1/page): the × separator; "agents" (not "automations" or "bots"); "GTM"
- Sometimes: healthcare jargon (RCM, EHR, payer) — kept verbatim, it signals domain competence
- Never: house + AI-slop bans — leverage, seamless, robust, unlock, unleash, empower, elevate, game-changing, "passionate about," "results-driven," superlatives without numbers

**Do / don't pairs:**
- Do: "Custom agents I've built with Claude to solve real GTM challenges." / Don't: "Cutting-edge AI solutions that supercharge your go-to-market motion."
- Do: "Seven years of product marketing in healthcare and B2B SaaS." / Don't: "A seasoned marketing leader with a proven track record of driving growth."

**Register table:**
| Page type | Tone adjustment | Example line |
|---|---|---|
| Hero | Tersest; identity as fragments, not sentences | "Product Marketing × AI × Marketing Engineering" [3+] |
| Section lede | One-sentence scope statement, matter-of-fact | "How I build my agents, and the tools I run across the funnel." [3+] |
| Card body | Compressed evidence; outcome pinned at bottom (.result) | — [inf from structure] |
| Contact/footer | Warmer but still plain; direct ask | — [1] |

**Exemplars:**
> "Seven years of product marketing in healthcare and B2B SaaS, launching AI products to skeptical, regulated buyers, and using AI to move faster than the team size would suggest." — about lede, 2026-08-13
> "Custom agents I've built with Claude to solve real GTM challenges." — agents lede, 2026-08-13
> "Dhruv Walia is a San Francisco–based product marketer specializing in healthcare and B2B SaaS, with hands-on experience launching AI products and building AI-powered marketing workflows." — meta description (third-person register is metadata-only, never on-page), 2026-08-13

**Pre-return self-check for generated copy:** banned-word scan → register matches page type → every claim traceable or placeholder → would it pass blind-mixing with the exemplars?

## Notes
- **Monochrome discipline is the brand.** Adding a color is a redesign proposal, not a mock.
- Card bodies are dense and small (14–15.5px) relative to the 17px page base — don't "fix" this, it's the look.
- Voice sample is thin outside ledes/taglines (few full paragraphs on the site by design) — exemplar count below the 5–15 target; expand from card bodies if richer generation is needed.
- Copy tone: confident but literal; cleverness goes in structure, not adjectives.
