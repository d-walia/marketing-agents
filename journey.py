"""B2B buyer journey.

Each audit runs ONE ICP persona through a multi-turn chat session, repeated
across every AI assistant you have keys for. One ICP per audit keeps the
comparison clean: differences between sessions are differences between
models, not differences between personas. To audit a different ICP, run the
tool again with --persona.

The default persona is a Head of Sales / Sales Ops leader: hands-on with
process and tooling, but accountable for the number, and the one who will
defend the purchase to the CEO.

The turns mirror how B2B buying conversations with an AI assistant unfold:

  Turn 1 (problem)   - describe the business pain in the buyer's own words.
                       Never names the category or any vendor. Measures
                       whether the assistant proposes the category at all.
  Turn 2 (vendors)   - ask who to shortlist. Measures whether the brand
                       surfaces unprompted and who leads the shortlist.
  Turn 3 (the brand) - raise the brand directly and ask for a candid take.
                       Measures recommendation strength, qualifiers, cited
                       sources, and whether a competitor gets pulled in
                       over you.
"""

DEFAULT_PERSONA = {
    "id": "sales-leader",
    "label": "Head of Sales / Sales Ops leader",
    "voice": (
        "I'm the Head of Sales and I also own sales ops. I'm hands-on with our "
        "process, tooling, and pipeline reviews, but I'm accountable for the "
        "number, and I'll be the one defending this purchase to the CEO."
    ),
}


def make_persona(description: str) -> dict:
    """Build a custom ICP persona from a free-text description."""
    return {"id": "custom", "label": description, "voice": description}


def build_journey(persona: dict, icp: str, problem: str, brand: str) -> list:
    """Return the ordered user turns for the persona's chat session."""
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
