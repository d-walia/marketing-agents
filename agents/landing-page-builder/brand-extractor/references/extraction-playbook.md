# Extraction Playbook

Operational detail for the two-pass extraction. SKILL.md holds the principles; this holds the checklists.

## Pass 1 — Authored CSS (CSSOM / raw stylesheets)

Run in the Browser pane via `javascript_tool`:

1. **Enumerate custom properties by iterating rules, not by guessing names:**
   ```js
   const tokens = {};
   for (const sheet of document.styleSheets) {
     let rules; try { rules = sheet.cssRules } catch (e) { console.log('BLOCKED:', sheet.href); continue }
     for (const r of rules) {
       if (r.selectorText && /:root|^html|^body|\[data-theme|\.dark/.test(r.selectorText)) {
         for (const p of r.style) if (p.startsWith('--')) tokens[r.selectorText] ??= {}, tokens[r.selectorText][p] = r.style.getPropertyValue(p).trim();
       }
     }
   }
   ```
   `getComputedStyle(...).getPropertyValue('--x')` only works if you already know the name; rule iteration *discovers* names. Capture `[data-theme]`/`.dark` blocks in the same pass for theme variants.
2. **Blocked cross-origin sheets:** fetch each logged `href` as raw text (curl or WebFetch) and grep it for `--` declarations, `:hover` rules, `@media` blocks, `clamp(`, `box-shadow`, `linear-gradient`.
3. **From the authored CSS also pull:** every `@media (min|max-width)` value (cluster to the 3–5 real breakpoints), `@font-face` sources, `:hover`/`:focus` rules for buttons and links, `transition` declarations, `prefers-color-scheme` blocks.

## Pass 2 — Computed styles on a role-representative sample

Sample these ~10 elements (select by tag, ARIA role, or visible text — **never** by hashed/utility class name):

| Element | Why |
|---|---|
| `body` | base font, size, line-height, text color, page bg |
| `h1`, `h2`, `h3` | type scale, weights, letter-spacing, casing |
| body-copy `a` | link color/decoration |
| primary CTA button (find by its text) | bg, color, radius, padding, border, shadow, weight |
| secondary/ghost button | the variant delta |
| header/nav | height, bg, blur/shadow, link styling |
| one card | bg, radius, border, shadow, padding |
| one form input (if any) | border, radius, focus ring |
| main container | max-width, horizontal padding |
| footer | bg, text color |

Per element record: `font-family, font-size, font-weight, line-height, letter-spacing, color, background-color, border, border-radius, box-shadow, padding, margin, gap, max-width, transition`. Query **longhands** explicitly — shorthands come back expanded.

**Known lies of computed style (recover from Pass 1):**
- Colors resolve to `rgb()`/flat — authored hex, `oklch`, and alpha (`rgb(x/0.6)`) live in the stylesheet.
- Units resolve to px — a heading may actually be `clamp(2.5rem, 8vw, 4.5rem)`; check for `clamp()` before recording a fixed size.
- `var()` indirection is flattened — the semantic token name is lost.
- Hover/focus/active never appear — grep Pass 1 for `:hover` (the `getComputedStyle(el, ':hover')` form is NOT reliable for state pseudo-classes).
- Visited-link styles are deliberately falsified by browsers — ignore.

**States to capture beyond default:**
- **Mobile:** resize viewport to ~375px, re-sample nav/hero/container — don't extrapolate from desktop numbers.
- **Dark mode:** read the `prefers-color-scheme`/`[data-theme=dark]` blocks from Pass 1, or re-sample with dark emulation (`resize_window` colorScheme).
- **Scroll state:** sticky headers often change on scroll (transparent → solid + shadow); screenshot and sample both states.

## Scale inference

**Spacing:** collect all padding/margin/gap values from the sample → round each to the nearest 4px → count frequency → keep the top ~8, discard singletons (13px and 22px are usually artifacts, not tokens) → state the generative rule (most common shape: 4, 8, 12, 16, 24, 32, 48, 64 — linear then doubling). Record rule + raw evidence.

**Type:** compute the ratio between consecutive observed heading sizes; a modular ratio (~1.2–1.333 from a 16–18px base) lets you generate unobserved levels consistently. Weight by frequency so a one-off 15px caption doesn't pollute the scale.

**Colors:** map to semantic roles with rough usage counts (frequency = importance). >15 unique colors = sampled noise; re-cluster.

## Fonts

- On Google Fonts → record the embed link; usable directly in mocks served normally. Artifact mocks block external hosts — inline as data URI only if small, else use the fallback stack.
- Commercial/licensed (Klim, Commercial Type, foundry-hosted) → do not rehost. Record: exact family, closest free/system substitute, and matched metrics (weight, letter-spacing, comparable x-height/width) so line-breaks survive substitution. Note in the brand file which one any mock actually used.

## Screenshot ground truth

Take live-site screenshots at ~1280px and ~375px (plus a scrolled-state shot if the nav changes) and save them next to the brand file (`brands/<slug>-desktop.png` etc.). They are the reference for the verification rebuild and for future drift checks.

## Voice sampling checklist

Pages to read (skip what doesn't exist): homepage, one product/feature page, pricing, one blog post, 404 or empty state, footer/microcopy, one transactional surface if reachable.

Look for, per page: headline structure (verb-first? benefit-first? fragment?), CTA verbs, capitalization scheme (sentence case vs Title Case — a highly visible fingerprint), self-reference ("we" vs product name; "the" before the product name or not), reader naming ("you", "your team", a named persona), how numbers/claims appear (specific stats vs superlatives), hedging posture (asserts vs qualifies — regulated brands hedge deliberately; don't erase it), punctuation habits (em dashes, exclamations-per-page, oxford comma, ampersands, periods in headlines), contractions, sentence-length rhythm, and **what never appears**.

Fill the template's voice section: persona + anti-persona sentence, 3–5 traits each with means/doesn't-mean + quote, four tone sliders (funny↔serious, formal↔casual, respectful↔irreverent, enthusiastic↔matter-of-fact) with stated positions, mechanics block, three-tier vocabulary (always / sometimes-with-context / never — including the standing AI-slop bans), do/don't pairs, register table per page type, 5–15 dated exemplars including 1–2 **full paragraphs** (rhythm and transitions are invisible in one-liners), each tagged `[3+]`/`[1]`/`[inf]`.
