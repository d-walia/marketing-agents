"""B2B buyer journey.

The buyer persona is constructed entirely from YOUR ICP definition in the
config file: their role, their jobs to be done, and their priorities. Nothing
about the persona is hardcoded to any product category, so the tool applies
to any B2B product.

Each scenario in the config is one journey: a situation where the ICP's jobs
run into a challenge. The journey runs as a multi-turn chat session, repeated
across every AI assistant you have keys for.

The journey has four stages, and every stage goes two prompts deep: the main
question, then a scripted follow-up that pushes past the first-pass answer
before transitioning to the next stage. All prompts are fixed scripts so
sessions stay comparable across models and scenarios.

  Stage 1 (problem)   Q:  the ICP describes the situation in their own words.
                          Never names the category or any vendor.
                      FU: which approach gives the most impact fastest?
                          Measures whether the category survives
                          prioritization, not just brainstorming.
  Stage 2 (vendors)   Q:  who should be on the shortlist, ranked?
                      FU: defend the top pick; what would change the ranking?
                          Measures conviction and the real decision criteria.
  Stage 3 (the brand) Q:  candid take on the target brand.
                      FU: what is that view based on, how current is it, and
                          what should the buyer verify? Measures provenance:
                          whose information is defining the brand.
  Stage 4 (pressure)  Q:  would any concern actually stop you? Commit today:
                          them or someone else?
                      FU: make the case to the CEO in three sentences, and
                          name the single piece of evidence that would change
                          your mind. Extracts the pitch and the flip
                          condition.
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
    """Return the ordered user turns (8: four stages x question + follow-up)."""
    return [
        # Stage 1: problem. No category, no vendors.
        (
            f"{persona_intro(icp)}\n\n"
            f"Here's the situation I'm dealing with: {scenario['situation']}\n\n"
            "How would you approach solving this?"
        ),
        (
            "There's a lot there. If I can only focus on one or two of those, "
            "which would give us the most impact fastest, and what would that "
            "actually look like in practice for a team like ours?"
        ),
        # Stage 2: vendors. Still without naming anyone.
        (
            "That's helpful. If we decided to buy something rather than build or "
            "change process, which specific vendors or products should be on our "
            "shortlist? Rank them for a company like ours and say why."
        ),
        (
            "Tell me more about your top pick. Why them over the next one down, "
            "specifically for our situation? And what would have to be true for "
            "you to change that ranking?"
        ),
        # Stage 3: the target brand.
        (
            f"We've come across {brand}. Be candid: would you recommend them for "
            "our situation? What are they actually good at, what would you flag, "
            "and is there anyone you'd pick over them?"
        ),
        (
            "What is that assessment actually based on? How current and reliable "
            "is your information about them, and what should I go verify myself "
            "before trusting it?"
        ),
        # Stage 4: pressure and final call.
        (
            "You raised some concerns along the way. Be honest with me: would any "
            f"of those actually stop you from recommending {brand} for us? If you "
            "were in my seat and had to commit today, what would you do: go with "
            "them, or someone else? Give me your final call and why."
        ),
        (
            "Last thing. Make the case for that choice to my CEO in three "
            "sentences. Then tell me: what single piece of evidence, if you saw "
            "it, would change your mind?"
        ),
    ]
