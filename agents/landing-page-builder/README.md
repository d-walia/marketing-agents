# Landing Page Builder

Propose web updates with a true-to-life, on-brand HTML mock instead of stitched screenshots. Two skills work as a pipeline: capture a brand once, then generate unlimited page mocks from the cached brand file.

**Replaces:** the screenshot-stitching workflow for proposing web changes, plus most of what a Figma comp or a Claude Design credit burn would buy for marketing page proposals.

## How it works

```
brand-extractor-v2                          page-mockup-v2
──────────────────                          ──────────────
site or codebase                            brand file + copy + page intent
  → two-pass extraction                       → full-chrome HTML mock
    (authored CSS + computed styles)          → quality gates (responsive, AA
  → tokens, scales, components                  contrast, no placeholder tells)
    with hover deltas, voice rules           → published as a stable Artifact URL
  → one brand file in                         → iterate in place, versioned,
    page-mockup/brands/<slug>.md                with a stakeholder changelog
```

Extraction happens once per brand (15-25 min, verification included). Every mock after that is a single generation pass, with no re-derivation of the design system.

## Design decisions

- **Two-pass extraction, never one.** Computed styles alone mislead (colors resolve to rgb, hover states are invisible, `var()` names flatten away); authored CSS alone includes dead code. Parsing both is what makes the brand file pixel-true. Full method in [brand-extractor/references/extraction-playbook.md](brand-extractor/references/extraction-playbook.md).
- **Voice is extracted with evidence rules.** Patterns promote to rules only when seen on 2+ page types, every rule carries a verbatim quote, and do/don't pairs are written against the actual near-miss an AI would produce. This is why copy-in-place mocks read as the real brand.
- **Verification is mandatory.** The extractor's output is accepted only after `page-mockup-v2` rebuilds a section of the live site from the brand file alone and the diff against a screenshot is nothing but noise.
- **The mock is built to persuade.** Quality gates ([page-mockup/references/quality-gates.md](page-mockup/references/quality-gates.md)) target what stakeholder credibility hinges on: exact tokens, real copy, mobile correctness, no dead links, no placeholder artifacts, rights-safe imagery.
- **Stable share URLs, versioned in place.** One artifact per page concept, a visible version stamp, and a changelog that records the rationale for each revision.

## Install

```bash
ln -s ~/github/marketing-agents/agents/landing-page-builder/brand-extractor ~/.claude/skills/brand-extractor-v2
ln -s ~/github/marketing-agents/agents/landing-page-builder/page-mockup ~/.claude/skills/page-mockup-v2
```

Then ask in plain language: "build a brand file for acme.com", "mock up a hero variant for my portfolio with this copy".

## Layout

| Path | What lives there |
|---|---|
| `brand-extractor/` | The capture skill + extraction playbook |
| `page-mockup/` | The generation skill + quality gates |
| `page-mockup/brands/` | One file per captured brand (`_TEMPLATE.md` = format; hand edits win over re-extraction). Ships with `dw-digital.md`, extracted from the portfolio repo |

Related: `../../brand-pack/` holds Dhruv's own positioning and voice inputs for the planned Intelligent Copywriter. Brand files here are per-target-company design systems, a different layer.
