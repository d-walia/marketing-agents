# Quality Gates & Asset Rules

Run top to bottom before sharing any mock link. Every item is cheap; skipping any one is the thing a reviewer notices.

## Pre-share checklist

**Responsive**
- [ ] ~375px pass: no horizontal scroll, no overlapping elements, columns stack cleanly, primary CTA visible on the first mobile screen. If you run only one pass, run mobile — stakeholders open links on their phones.
- [ ] ~1280–1440px pass; add ~768px if the brand's CSS has a tablet break.
- [ ] Fold check at ~800px desktop / ~812px mobile: value prop + primary CTA survive above it.

**Accessibility-visible**
- [ ] Contrast AA: 4.5:1 body text, 3:1 large text — especially text over images/gradients (reads as "hard to read" even to reviewers who can't name the rule).
- [ ] Body text ≥16px; tap targets ≥44px.

**Typography**
- [ ] `text-wrap: balance` on headlines; `text-wrap: pretty` (or a strategic `&nbsp;`) on key paragraphs — kill widows/orphans.
- [ ] Copy proofread at production standard. Read it aloud once.

**Interaction honesty**
- [ ] Every visible link/button either works (anchor, toggle) or is visibly inert by design. No `href="#"` that jumps to top.
- [ ] Primary CTA has styled hover state (use the brand file's hover delta).

**No placeholder artifacts**
- [ ] No visible placeholder-service text, no lorem fragments, no default blue underlined links.
- [ ] Explicit width/height or `aspect-ratio` on every image box so nothing collapses if an asset fails.

**Ship test**
- [ ] Open the actual share URL fresh (not the local file): fonts render, layout holds, light/dark both sane (or the mock explicitly commits to one scheme with painted backgrounds).
- [ ] Version stamp present; variant badges present; every stand-in labeled once.

## Asset & rights rules

- **Prefer structured SVG stand-ins over flat gray boxes:** gradient fills in brand-adjacent tones or CSS-drawn abstract compositions preserve the page's visual weight and color balance — and inline SVG survives the Artifact CSP.
- **Match tonal value:** dark placeholder where a dark photo will go, so text-over-image treatments evaluate truthfully.
- **Logos:** the client brand's own logo SVG (from the brand file) is fine. Simple logos may be recreated typographically in the correct font/weight and labeled as approximation. **Never** real third-party logos you haven't cleared — grayscale text wordmarks labeled "representative" for partner/customer walls.
- **People:** CSS initial-circles or abstract generated avatars for testimonials; never real people's photos pulled from the web.
- **Wrong-but-real beats nothing? No —** an obviously-abstract stand-in beats a stock photo you'd never ship, because a real-looking wrong photo anchors reviewers to imagery that won't exist.
- **Label every stand-in once, unobtrusively** ("FPO" corner tag or one annotation line) — one label prevents ten "is this final?" comments.

## Fidelity calibration (decide before building)

- Decision is **"which direction?"** → don't go full polish; hi-fi too early anchors stakeholders and makes structural feedback feel expensive ("it looks done").
- Decision is **"ship this?"** → full fidelity on everything resolved; nitpicks surfacing now instead of after launch is the point.
- Hi-fi implies commitment: if engineering effort is *not* mostly spent, say so next to the mock.
- State the project stage on the page ("Concept · not built") so reviewers calibrate feedback correctly.
