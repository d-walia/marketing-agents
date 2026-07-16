"""B2B buyer journeys.

Each journey is a multi-turn chat session where we play a member of the
brand's ICP working through a real evaluation. The turns mirror how B2B
buying conversations with an AI assistant actually unfold:

  Turn 1 (problem)   - describe the business pain in the buyer's own words.
                       Never names the category or any vendor. Measures
                       whether the assistant proposes the category at all.
  Turn 2 (vendors)   - ask who to shortlist. Measures whether the brand
                       surfaces unprompted and who leads the shortlist.
  Turn 3 (the brand) - raise the brand directly and ask for a candid take.
                       Measures recommendation strength, qualifiers, cited
                       sources, and whether a competitor gets pulled in
                       over you.

Personas are variations on the ICP so the audit sees the brand through
the eyes of the different people in a B2B buying committee.
"""

PERSONAS = [
    {
        "id": "practitioner",
        "label": "Hands-on practitioner (will use the product daily)",
        "voice": "I'm the person who would actually use this day to day.",
    },
    {
        "id": "economic-buyer",
        "label": "Economic buyer (owns the budget, cares about ROI)",
        "voice": "I own the budget for this and need to justify the spend to leadership.",
    },
    {
        "id": "skeptical-exec",
        "label": "Skeptical executive (risk-averse, needs proof)",
        "voice": "I'm a senior leader who has been burned by tool purchases before. I need evidence, not marketing.",
    },
]


def build_journey(persona: dict, icp: str, problem: str, brand: str) -> list[str]:
    """Return the ordered user turns for one persona's chat session."""
    return [
        # Turn 1: pure problem statement. No category, no vendors.
        (
            f"{persona['voice']} Some context on us: {icp}\n\n"
            f"Here's what we're struggling with: {problem}\n\n"
            "How would you approach solving this?"
        ),
        # Turn 2: move to vendors, still without naming anyone.
        (
            "That's helpful. If we decided to buy something rather than build or "
            "change process, which specific vendors or products should be on our "
            "shortlist? Rank them for a company like ours and say why."
        ),
        # Turn 3: raise the target brand directly.
        (
            f"We've come across {brand}. Be candid: would you recommend them for "
            "our situation? What are they actually good at, what would you flag, "
            "and is there anyone you'd pick over them? Mention any sources your "
            "view is based on."
        ),
    ]
