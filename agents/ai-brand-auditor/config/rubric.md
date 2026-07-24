# Response Grading Rubric

Grade each model response on the five criteria below, 0–2 each (max 10 per response). Grade what the model actually said — not what you know to be true from other responses.

| # | Criterion | 0 | 1 | 2 |
|---|-----------|---|---|---|
| 1 | **Factual accuracy about the brand** | Materially wrong (wrong product, wrong market, hallucinated features) | Mostly right with minor errors or stale details | Accurate description of what the brand does |
| 2 | **Category placement** | Brand absent from its own category, or placed in the wrong category | Present but buried, hedged, or miscategorized | Correctly and confidently placed in its category |
| 3 | **Competitive framing** | Recommends only competitors, or frames brand as inferior without basis | Neutral mention alongside competitors | Differentiated: articulates what the brand is uniquely good at |
| 4 | **Freshness** | Clearly outdated (old positioning, dead features, stale funding/team facts) | Mixed vintage | Reflects current positioning |
| 5 | **Recommendation strength** | Model would steer a buyer away | Model is neutral / "depends" | Model would plausibly steer a buyer toward the brand |

## Notes for the grader

- For **category_discovery** and **use_case** queries where the brand isn't mentioned at all: criteria 1, 3, 4 are N/A — score only 2 and 5 (max 4), and flag the absence prominently. Absence from category queries is the single most important finding in a GEO audit.
- Quote the model's exact words as evidence for any 0 score.
- One grade table per response; one summary row per model at the end.
