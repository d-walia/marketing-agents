"""B2B buyer journey: fixed stage arc, adaptive buyer.

The journey holds FOUR STAGES constant so sessions stay comparable, but the
buyer's actual words are generated live by a simulated persona built from
your ICP definition. The buyer reads the assistant's last answer and asks
the follow-up a real person under pressure would ask, grounded in their
jobs, priorities, constraints, and installed stack. Only the opening turn
is constructed verbatim from your scenario, so the unprimed measurement
(does the assistant propose your category?) stays clean.

  Stage 1  problem   Open with the scenario in the buyer's words (verbatim
                     from config, never names category or vendors), then
                     push the assistant to prioritize.
  Stage 2  vendors   Move to buying: who should be shortlisted, then press
                     on the top pick and what would change the ranking.
  Stage 3  brand     Raise the target brand by name for the first time,
                     then interrogate the basis and currency of the
                     assistant's assessment.
  Stage 4  pressure  Push back on concerns and demand a final call, then
                     the three-sentence CEO case and the single piece of
                     evidence that would change its mind.

If turn generation fails or leaks the brand early, the scripted fallback
for that slot is used instead, so a run always completes.
"""

BUYER_MODEL = "claude-sonnet-5"


def persona_intro(icp: dict) -> str:
    """Build the buyer's self-introduction from the ICP definition."""
    parts = [
        f"I'm the {icp['role']}. About us: {icp['description']}",
        f"My job is to: {'; '.join(icp['jobs_to_be_done'])}.",
        f"My top priorities right now: {'; '.join(icp['priorities'])}.",
    ]
    if icp.get("buying_moment"):
        parts.append(f"What's going on: {icp['buying_moment']}")
    if icp.get("installed_stack"):
        parts.append(f"Tools we already run: {', '.join(icp['installed_stack'])}.")
    return "\n".join(parts)


def opening_turn(icp: dict, scenario: dict) -> str:
    return (
        f"{persona_intro(icp)}\n\n"
        f"Here's the situation I'm dealing with: {scenario['situation']}\n\n"
        "How would you approach solving this?"
    )


def stages(brand: str) -> list:
    """Stage arc: each turn slot has a goal (for the buyer generator) and a
    scripted fallback. Slot 0 of stage 1 is always the constructed opening."""
    return [
        {
            "id": "problem",
            "turns": [
                {"goal": "OPENING", "fallback": None},
                {
                    "goal": (
                        "React to something specific the assistant just said, then push it to "
                        "commit: which one or two of those approaches would give you the most "
                        "impact fastest, and what would that look like in practice for a team "
                        "like yours?"
                    ),
                    "fallback": (
                        "There's a lot there. If I can only focus on one or two of those, "
                        "which would give us the most impact fastest, and what would that "
                        "actually look like in practice for a team like ours?"
                    ),
                },
            ],
        },
        {
            "id": "vendors",
            "turns": [
                {
                    "goal": (
                        "Move the conversation to buying: if you bought something instead of "
                        "building or changing process, which specific vendors or products "
                        "should be on your shortlist, ranked for a company like yours? Do not "
                        "name any vendor or product yourself."
                    ),
                    "fallback": (
                        "That's helpful. If we decided to buy something rather than build or "
                        "change process, which specific vendors or products should be on our "
                        "shortlist? Rank them for a company like ours and say why."
                    ),
                },
                {
                    "goal": (
                        "Press on its top pick: why them over the next one down for your "
                        "specific situation? Bring in whichever of your real constraints is "
                        "most relevant to what it just said (your installed stack, team "
                        "capacity, timeline, or budget pressure), and ask what would have to "
                        "be true for the ranking to change."
                    ),
                    "fallback": (
                        "Tell me more about your top pick. Why them over the next one down, "
                        "specifically for our situation? And what would have to be true for "
                        "you to change that ranking?"
                    ),
                },
            ],
        },
        {
            "id": "brand",
            "turns": [
                {
                    "goal": (
                        f"Raise {brand} by name for the first time. Say you've come across "
                        f"them and ask for a candid assessment for your situation: what "
                        f"they're actually good at, what to flag, and whether the assistant "
                        f"would pick anyone over them."
                    ),
                    "fallback": (
                        f"We've come across {brand}. Be candid: would you recommend them for "
                        "our situation? What are they actually good at, what would you flag, "
                        "and is there anyone you'd pick over them?"
                    ),
                },
                {
                    "goal": (
                        "Interrogate the basis of that assessment: what is it actually based "
                        "on, how current and reliable is the information, and what should "
                        "you verify yourself before trusting it? If anything it said sounded "
                        "like vendor marketing, call that out and ask for the source."
                    ),
                    "fallback": (
                        "What is that assessment actually based on? How current and reliable "
                        "is your information about them, and what should I go verify myself "
                        "before trusting it?"
                    ),
                },
            ],
        },
        {
            "id": "pressure",
            "turns": [
                {
                    "goal": (
                        f"Push back on the concerns raised so far: would any of them actually "
                        f"stop you from buying {brand}? Then demand a commitment: if the "
                        f"assistant were in your seat and had to commit today, {brand} or "
                        f"someone else, and why? Ask for a straight final call."
                    ),
                    "fallback": (
                        "You raised some concerns along the way. Be honest with me: would any "
                        f"of those actually stop you from recommending {brand} for us? If you "
                        "were in my seat and had to commit today, what would you do: go with "
                        "them, or someone else? Give me your final call and why."
                    ),
                },
                {
                    "goal": (
                        "Ask for the case for that choice to your CEO in three sentences, "
                        "then ask: what single piece of evidence, if the assistant saw it, "
                        "would change its mind about that final call?"
                    ),
                    "fallback": (
                        "Last thing. Make the case for that choice to my CEO in three "
                        "sentences. Then tell me: what single piece of evidence, if you saw "
                        "it, would change your mind?"
                    ),
                },
            ],
        },
    ]


BUYER_RULES = """You are playing a real B2B buyer in a live chat with an AI assistant. Stay
completely in character. Rules:
- Write the buyer's next message only: plain conversational prose, one message, under 90 words.
- No bullet points, no headers, no signoffs, never mention being an AI or a simulation.
- Ground your message in something specific the assistant actually said in its last answer.
- Speak from this buyer's real jobs, priorities, constraints, and existing tools when relevant.
- {naming_rule}
- Pursue this goal with your message: {goal}"""

NAMING_BEFORE_BRAND = (
    "Do NOT name any vendor, product, or software category the assistant has not "
    "already named itself. Never mention the brand being evaluated."
)
NAMING_FROM_BRAND = "You may discuss any vendor freely now."


def buyer_prompt(icp: dict, scenario: dict, goal: str, before_brand_stage: bool) -> str:
    rules = BUYER_RULES.format(
        naming_rule=NAMING_BEFORE_BRAND if before_brand_stage else NAMING_FROM_BRAND,
        goal=goal,
    )
    return (
        f"THE BUYER YOU ARE PLAYING:\n{persona_intro(icp)}\n"
        + (f"Decision criteria: {'; '.join(icp['decision_criteria'])}.\n" if icp.get("decision_criteria") else "")
        + f"The situation that started this conversation: {scenario['situation']}\n\n{rules}"
    )
