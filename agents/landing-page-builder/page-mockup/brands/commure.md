# Brand: Commure (commure.com)

<!-- Confidence tags: [3+] observed 3+ times · [1] observed once · [inf] inferred. -->

## Sources
- Live site, two-pass extraction (CSSOM tokens + computed styles) of commure.com/ambient-ai — 2026-08-13. 168 Webflow custom properties recovered; values below are the authored hex.
- Voice sampled from the ambient-ai page + announcement bar only — below the 2-page rule, tag voice rules [1] unless marked.

## Tokens
```css
:root{
  /* semantic roles (Commure's own names in comments) */
  --bg:#000;                /* graphite — page ground, dark-first brand */
  --surface:#1a1a1a;        /* primary-2-light — cards on black */
  --surface-2:#2f2f2f;      /* charcoal */
  --text:#d9d9d9;           /* stealth-grey — default text on black */
  --text-strong:#fff;       /* h3/emphasis */
  --text-muted:#7b7b7b;     /* grey — eyebrows, secondary */
  --accent:#a8f4ff;         /* velocity — THE brand accent (cyan), CTAs + highlights */
  --accent-light:#dbfaff;   /* accent-1-light */
  --blue:#3351f1;           /* blue-litmus — secondary accent */
  --blue-bright:#2d62ff;    /* brand blue */
  --pink:#dd23bb;           /* brand pink — rare, celebratory */
  --border:#ffffff1a;       /* white-0-1 — 10% white hairlines on black */
}
/* Light-section variants exist (glacier white, cloud-gray #ececec, nexus-4 #ecf3f9)
   but the ambient-ai page runs dark end to end. */
```

**Fonts:** GT America Extended (display; weight 300 only) + Satoshi (body; 400/700/900). **Both custom-licensed webfonts — do not rehost.**
Fallbacks: display `'Helvetica Neue', Arial, sans-serif` weight 300 (GT America Extended is a wide grotesk — add `letter-spacing` per the scale below and it survives); body `-apple-system, 'Helvetica Neue', Arial, sans-serif` (Satoshi is a geometric humanist close to system faces).

**Container:** ~1147px max-width. Nav ~101px tall, transparent over black.

## Type scale (desktop = mobile on this page — sizes don't scale up at 1280)
| Element | Family | Weight | Size | Letter-spacing | Casing |
|---|---|---|---|---|---|
| h1 | GT America Ext | **300** | ~36px | **-0.067em (very tight)** | Title |
| h2 | GT America Ext | 300 | ~32px | +0.01em | Title |
| h3 | Satoshi | **900** | ~25px | normal | Title |
| body | Satoshi | 400 | ~14.3px / 1.3 | normal | Sentence |
| eyebrow | Satoshi | 700 | ~12.5px | normal | UPPERCASE, #7b7b7b |
| CTA | Satoshi | 900 | ~10.8px | +0.04em | UPPERCASE |

Signature moves: light-weight extended-grotesk headlines with tight negative tracking on a black ground; heavy (900) Satoshi for card titles — the 300/900 weight contrast IS the hierarchy; tiny uppercase 900 pill CTAs; stat callouts where the number is huge and cyan/white and the qualifier is small grey text.

## Components

### CTA pill (primary)
```css
.btn{display:inline-block;background:var(--accent);color:#000;font-weight:900;font-size:11px;letter-spacing:.04em;text-transform:uppercase;border-radius:999px;padding:11px 29px;border:0;text-decoration:none}
/* secondary: transparent bg, 1px solid var(--border) or #000 on light, same pill shape */
```

### Card (tier/feature, on black)
```css
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:28px}
/* h3 Satoshi 900 white → feature list in stealth-grey → "BEST FOR" eyebrow + line pinned at bottom */
```
[inf] radius ~12–20px observed visually; hairline borders are the 10% white token.

### Stat callout
Eyebrow (uppercase 700 grey) above a huge number (GT America Ext 300, white or cyan) above a small grey qualifier. Pattern: "REDUCE CLINICIAN BURDEN / **Up to 2 hours** / saved per day…" [3+ on page]

### Eyebrow pattern
Uppercase Satoshi 700 ~12.5px in #7b7b7b above every section h2. [3+]

### Announcement bar
Full-width velocity-cyan strip, black text, pill button right. (Top of every page.)

### Logo
Lowercase "commure" wordmark + ring glyph. For mocks: typographic recreation (lowercase, medium weight, wide) — do not lift the SVG for public concept pages.

## Voice
**Persona:** Enterprise health-IT vendor speaking CMIO/CFO — capability claims grounded in scale numbers.
**Anti-persona:** Never consumer-cute; no exclamation points; no first person.

1. Scale-proof over adjectives: "Live across the largest US health systems, supporting 40 million appointments annually." [1]
2. Alliterative/structured headline patterns: "Listens, Codes, Cues, and Connects." [1]
3. Body = verb-first capability bullets ("Surfaces clinically relevant documentation and coding cues"), 3–7 per card. [3+]
4. Outcome numbers carry units and qualifiers: "Up to 2 hours saved per day … depending on the specialty" — hedged precisely, healthcare-compliance style. [3+]
5. Vocabulary: "clinicians"/"care teams" (not doctors), "documentation burden," "revenue integrity," "encounter," "downstream workflows." EHR/CPT/ICD-10 jargon used verbatim — the audience expects it. [3+]

**Register table:** hero = platform claim + scale proof; cards = capability bullets; stats = eyebrow/number/qualifier; testimonials = long verbatim quotes with full name + title.

## Notes
- Dark-first brand: black is the ground, not a mode. Velocity cyan is used sparingly — CTAs, stat numbers, the announcement bar — never as large surface fills.
- The 300-weight extended headline + 900-weight Satoshi card title contrast is the single most identifying pattern; preserve both in any mock.
- Page content inventory for redesign work captured 2026-08-13: hero, care-environment intro, 4 support tiers (Ambient AI / Assist / Live / +), 7 capability groups, 3 outcome stats, 25-specialty list, 6 enterprise trust points, testimonials (NEMS, HCA/Schlosser, Tenet), lead form.
