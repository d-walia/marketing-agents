"""Buyer scenario templates.

Each scenario is a realistic question a real buyer would ask an AI
assistant. None of them name the brand being audited. Edit or add
personas freely; the audit runs every scenario listed here.
"""


def build_scenarios(category: str) -> list[dict]:
    return [
        {
            "id": "cold-start",
            "persona": "First-time buyer, no prior knowledge",
            "question": (
                f"I'm looking for {category}. I don't know this space at all. "
                "What are the best options and which one would you pick for me?"
            ),
        },
        {
            "id": "smb-budget",
            "persona": "Small business owner, price sensitive",
            "question": (
                f"I run a 12-person company and need {category}. Budget matters. "
                "Give me your top 3 with rough pricing and tell me which one to buy."
            ),
        },
        {
            "id": "enterprise-eval",
            "persona": "Enterprise buyer with security requirements",
            "question": (
                f"We're a 2,000-person company evaluating {category}. "
                "SSO, admin controls, and vendor stability are non-negotiable. "
                "Which vendors should make our shortlist, and who's the safest choice?"
            ),
        },
        {
            "id": "switcher",
            "persona": "Unhappy customer of an incumbent",
            "question": (
                f"We use a well-known tool for {category} but it's gotten bloated "
                "and expensive. What should we switch to and why?"
            ),
        },
        {
            "id": "comparison-ask",
            "persona": "Buyer asking for a head-to-head",
            "question": (
                f"Compare the two leading options for {category} head to head. "
                "Which one wins, and for whom?"
            ),
        },
    ]
