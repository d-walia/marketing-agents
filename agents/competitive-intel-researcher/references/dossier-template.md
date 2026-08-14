# Vendor Dossier Schema

One dossier per vendor. Every field is **filled**, **`not found`** (looked, absent), or **`out of scope`** (mode didn't require it). Never silently missing — an empty field is a visible finding.

Every material claim carries a confidence grade and a date:

| Grade | Meaning |
|---|---|
| **Verified** | Primary source: their docs, pricing page, changelog, filing |
| **Corroborated** | 2+ independent secondary sources agree |
| **Reported** | Single secondary source |
| **Inference** | Our reasoning — labeled, never disguised as fact |

---

## D1. Identity & vitals

- Founded / HQ / geography
- Headcount now + 6-month trend (LinkedIn)
- Ownership: funding history, investors, last round + date, implied runway; or parent company / public
- Key executives with backgrounds (feeds D8: a sales-bred CEO runs a different playbook than a research founder)

## D2. Market & ICP

- Segments actually served: named customers with size/segment (from logos, case studies, reviews)
- Case-study mix (which segment do they showcase — that's who they want more of)
- Geographic focus
- The category label *they* use for themselves (verbatim)

## D3. Product & capabilities

- Score against the run's capability taxonomy (defined before any vendor research — see SKILL.md Phase 1), 0–5 per dimension, evidence cited
- **Hard rule: capability claims verify against docs/changelogs/product screenshots, never marketing pages alone**
- Integrations (count + the strategically important ones)
- Security/compliance certs (SOC 2, HIPAA/BAA, FedRAMP...) — only as relevant to the category
- Architecture notes (deployment model, API surface, extensibility)

## D4. Pricing & packaging

- Model: per-seat / usage / platform fee / hybrid
- Tiers and what gates them
- List prices where published; review/community leaks where not (graded Reported)
- Discounting behavior signals; contract structure (annual minimums, implementation fees)
- **Every number carries a fetched-on date**

## D5. GTM motion

- Motion: sales-led / PLG / channel mix; partner ecosystem
- Marketing channels observed: ad libraries (Meta + Google, both free), SEO footprint, sponsored events, content themes
- Current messaging themes with verbatim quotes (input to say/do gap)

## D6. Voice of market — HARD GATES

- **≥15 reviews read per vendor across ≥2 sources** (G2, Capterra, TrustRadius, Reddit/communities), recency-weighted. If fewer exist, the dossier states the actual count — that scarcity is itself a finding.
- Themes as **frequency counts** ("support latency in 7 of 20 negative reviews"), never vibes
- Switching patterns: switched-from and switched-to, with stated reasons — the free proxy for win/loss data. In-house win/loss data, when it exists, outranks reviews.
- Analyst placements (noted as lagging indicators)

## D7. Trajectory

- Open roles by function (postings telegraph roadmap: "PMM, Payer Segment" = market-entry announcement)
- Changelog velocity (releases/quarter, and what kind)
- Funding events, exec arrivals/departures, layoffs, press
- Public companies: 10-K risk factors + earnings-call language about this segment
- Patents where category-relevant

## D8. Strategy & likely response — Porter Four Corners

- **Drivers**: what leadership says it wants (earnings calls, founder interviews, hiring level)
- **Assumptions**: what they appear to believe about the market — including blind spots
- **Current strategy**: what they're visibly doing (D5 + D7)
- **Capabilities**: what they can actually execute (D1 + D3)
- → **Predicted moves** next 2–4 quarters, and **likely response to our play** — every prediction labeled Inference with its supporting evidence named
