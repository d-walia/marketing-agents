"""B2B buyer journey.

The buyer persona is constructed entirely from YOUR ICP definition in the
config file: their role, their jobs to be done, and their priorities. Nothing
about the persona is hardcoded to any product category, so the tool applies
to any B2B product.

Each scenario in the config is one journey: a situation where the ICP's jobs
run into a challenge. The journey runs as a multi-turn chat session, repeated
across every AI assistant you have keys for, and unfolds the way B2B buying
conversations actually do:

  Turn 1 (problem)   - the ICP describes the scenario in their own words.
                       Never names the category or any vendor. Measures
                       whether the assistant proposes the category at all.
  Turn 2 (vendors)   - ask who to shortlist. Measures whether the brand
                       surfaces unprompted and who leads the shortlist.
  Turn 3 (the brand) - raise the brand directly and ask for a candid take.
                       Measures recommendation strength, qualifiers, cited
                       sources, and whether a competitor gets pulled in
                       over you.
"""


def persona_intro(icp: dict) -> str:
    """Build the buyer's self-introduction from the ICP definition."""
    jobs = "; ".join(icp["jobs_to_be_done"])
    priorities = "; ".join(icp["priorities"])
    return (
        f"I'm the {icp['role']}. About us: {icp['description']}\n\n"
        f"My job is to: {jobs}.\n"
        f"My top priorities right now: {priorities}."
    )


def build_journey(icp: dict, scenario: dict, brand: str) -> list:
    """Return the ordered user turns for one scenario's chat session."""
    return [
        # Turn 1: persona + situation. No category, no vendors.
        (
            f"{persona_intro(icp)}\n\n"
            f"Here's the situation I'm dealing with: {scenario['situation']}\n\n"
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
