#!/usr/bin/env python3
"""AI Brand Perception Audit (B2B).

Runs multi-turn buyer-journey chat sessions against the AI assistants your
buyers actually use, posing as your ICP. Measures whether your category gets
proposed for the buyer's problem, whether your brand surfaces and gets
recommended, with what qualifiers and sources, and who beats you. Then
synthesizes positioning and content recommendations: what AI models believe
about you, what drives that opinion, and what proof would change it.

Works for any B2B product. All audit inputs live in a JSON config file:

    python audit.py --init            # writes audit-config.json template
    # edit the template with your brand, ICP, and scenarios, then:
    python audit.py audit-config.json

Requires ANTHROPIC_API_KEY (probing + analysis). Optional: OPENAI_API_KEY,
GEMINI_API_KEY, PERPLEXITY_API_KEY to probe those assistants too.
"""

import argparse
import json
import os
import sys
from datetime import date

import anthropic

from journey import (
    BUYER_MODEL, FRAMINGS, buyer_prompt, comparison_continuation, opening_turn,
    problem_stage, standard_continuation,
)
from providers import active_providers

ANALYSIS_MODEL = "claude-opus-4-8"

CONFIG_TEMPLATE = {
    "brand": "YourBrand",
    "category": "the product category in your buyer's language, e.g. 'contract lifecycle management platforms'",
    "competitors": ["Rival A", "Rival B"],
    "icp": {
        "role": "the buyer's job title, e.g. 'VP of Legal Operations'",
        "description": "firmographics in one or two sentences: industry, size, motion, e.g. 'mid-market fintech, 800 employees, high contract volume with banks'",
        "jobs_to_be_done": [
            "the outcomes this person is on the hook for, e.g. 'turn contracts around in under 5 days'",
            "e.g. 'keep the company out of compliance trouble'",
        ],
        "priorities": [
            "what they care about most right now, e.g. 'reduce outside counsel spend'",
            "e.g. 'look rigorous in front of the audit committee'",
        ],
        "buying_moment": "optional but strongly recommended: the trigger event that put them in market and the pressure they're under, e.g. 'two deals slipped last quarter because of contract turnaround; the CRO escalated to the CEO and I have one quarter to show improvement'",
        "installed_stack": [
            "optional but strongly recommended: tools they already run that a purchase must coexist with, e.g. 'Salesforce'",
            "e.g. 'Ironclad (legacy contracts only)'",
        ],
        "decision_criteria": [
            "optional but strongly recommended: what would actually make them buy, e.g. 'provable ROI within two quarters'",
            "e.g. 'works with our existing Salesforce workflow, no rip-and-replace'",
        ],
    },
    "scenarios": [
        {
            "id": "short-slug-for-this-scenario",
            "situation": "a concrete moment where the jobs above hit a challenge, in the buyer's own words. No category or vendor names. e.g. 'Our sales team is furious because contract review is the slowest step in every deal, and last quarter two deals slipped because redlines sat with us for two weeks.'",
        }
    ],
}

REQUIRED_ICP_FIELDS = ["role", "description", "jobs_to_be_done", "priorities"]

SESSION_SCHEMA = {
    "type": "object",
    "properties": {
        "category_proposed": {
            "type": "boolean",
            "description": "In turn 1, did the assistant propose the target product category as a solution to the situation?",
        },
        "category_terms_used": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The words the assistant used for the category/solution space",
        },
        "unprompted_brand_mention": {
            "type": "boolean",
            "description": "Was the target brand named before the buyer raised it in turn 3?",
        },
        "shortlist": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Vendors the assistant shortlisted in turn 2, in ranked order",
        },
        "brand_recommendation": {
            "type": "string",
            "enum": ["strong", "qualified", "lukewarm", "negative", "not_assessed"],
            "description": "Strength of the assistant's turn-3 verdict on the target brand",
        },
        "qualifiers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Hedges or caveats attached to the brand (e.g. 'good for smaller teams, but...')",
        },
        "competitor_preferred": {
            "type": ["string", "null"],
            "description": "Competitor the assistant would pick over the brand, or null",
        },
        "competitor_preferred_reason": {"type": ["string", "null"]},
        "sources_cited": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sources the assistant said its view is based on (sites, reviews, docs, general knowledge)",
        },
        "brand_sources_first_party": {
            "type": "boolean",
            "description": "Did any cited information about the brand come from the brand's own content, vs third parties only?",
        },
        "beliefs_about_brand": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete claims the assistant made about the brand, right or wrong",
        },
        "proof_gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Evidence that, had the assistant known it, would plausibly have strengthened the recommendation",
        },
        "final_call": {
            "type": "string",
            "enum": ["target_brand", "competitor", "neither_or_defer"],
            "description": "In turn 4, when forced to commit today, who did the assistant pick?",
        },
        "final_call_vendor": {
            "type": ["string", "null"],
            "description": "The vendor named in the final call, or null if it deferred",
        },
        "pressure_outcome": {
            "type": "string",
            "enum": ["objections_dissolved", "caveats_stand", "hardened_to_dealbreaker", "switched_to_competitor", "no_objections_raised"],
            "description": "What happened to the turn-3 qualifiers under turn-4 pressure: the assistant talked the buyer back in (dissolved), kept them as conditions (stand), turned them into blockers (dealbreaker), or moved to a rival (switched)",
        },
        "dealbreakers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concerns that the assistant said would actually stop the purchase, if any",
        },
        "ceo_pitch": {
            "type": ["string", "null"],
            "description": "The assistant's three-sentence case to the CEO for its final choice, verbatim or near-verbatim",
        },
        "flip_condition": {
            "type": ["string", "null"],
            "description": "The single piece of evidence the assistant said would change its mind about the final call",
        },
        "information_confidence": {
            "type": ["string", "null"],
            "description": "What the assistant admitted about how current/reliable its information on the target brand is, and what it told the buyer to verify",
        },
    },
    "required": [
        "category_proposed", "category_terms_used", "unprompted_brand_mention",
        "shortlist", "brand_recommendation", "qualifiers", "competitor_preferred",
        "competitor_preferred_reason", "sources_cited", "brand_sources_first_party",
        "beliefs_about_brand", "proof_gaps", "final_call", "final_call_vendor",
        "pressure_outcome", "dealbreakers", "ceo_pitch", "flip_condition",
        "information_confidence",
    ],
    "additionalProperties": False,
}


def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            config = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Config file not found: {path}\nRun 'python audit.py --init' to create a template.")
    except json.JSONDecodeError as e:
        sys.exit(f"Config file is not valid JSON: {e}")

    problems = []
    for field in ["brand", "category", "icp", "scenarios"]:
        if not config.get(field):
            problems.append(f"missing '{field}'")
    if isinstance(config.get("icp"), dict):
        for field in REQUIRED_ICP_FIELDS:
            if not config["icp"].get(field):
                problems.append(f"missing 'icp.{field}'")
    for i, scenario in enumerate(config.get("scenarios") or []):
        if not scenario.get("id") or not scenario.get("situation"):
            problems.append(f"scenario {i} needs both 'id' and 'situation'")
        for framing in scenario.get("framings", []):
            if framing not in FRAMINGS:
                problems.append(
                    f"scenario {i}: unknown framing '{framing}' (valid: {', '.join(FRAMINGS)})"
                )
    if problems:
        sys.exit("Config problems:\n  - " + "\n  - ".join(problems)
                 + "\nSee 'python audit.py --init' for the expected shape.")
    config.setdefault("competitors", [])
    return config


def generate_buyer_turn(client, config, scenario, goal, conversation, before_brand_stage) -> str:
    """Have the simulated buyer write its next message, reacting to the chat so far."""
    convo = "\n\n".join(
        f"[{'YOU (the buyer)' if m['role'] == 'user' else 'ASSISTANT'}]\n{m['content']}"
        for m in conversation
    )
    response = client.messages.create(
        model=BUYER_MODEL,
        max_tokens=400,
        output_config={"effort": "low"},
        system=buyer_prompt(config["icp"], scenario, goal, before_brand_stage),
        messages=[{
            "role": "user",
            "content": f"The conversation so far:\n\n{convo}\n\nWrite the buyer's next message.",
        }],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


def assistant_named(messages: list, config: dict) -> list:
    """Config-known vendor names the assistant has said so far, in config order."""
    said = " ".join(m["content"].lower() for m in messages if m["role"] == "assistant")
    return [n for n in [config["brand"], *config["competitors"]] if n.lower() in said]


def leaks_names(text: str, config: dict, allowed: list) -> bool:
    """True if a buyer turn introduces a config-known vendor the assistant hasn't named."""
    lowered = text.lower()
    allowed_lower = {a.lower() for a in allowed}
    return any(
        name.lower() in lowered and name.lower() not in allowed_lower
        for name in [config["brand"], *config["competitors"]]
    )


def conduct_session(provider, client, config, scenario, framing="operational"):
    """Run one stage-driven chat with an adaptive buyer.

    After stage 1, the journey branches: if the assistant named vendors on its
    own (category mapping works), the buyer follows that thread into a
    head-to-head comparison; otherwise the buyer opens the vendor conversation
    (standard pathway). Both pathways are 4 stages / 8 turns.
    Returns (messages, pathway, unprompted_vendor_names).
    """
    messages = []
    retrieved = []

    def run_stage(stage, guard_new_names):
        for slot in stage["turns"]:
            if slot["goal"] == "OPENING":
                turn = opening_turn(config["icp"], scenario, framing)
            else:
                allowed = assistant_named(messages, config) if guard_new_names else (
                    [config["brand"], *config["competitors"]]
                )
                try:
                    turn = generate_buyer_turn(client, config, scenario, slot["goal"], messages, guard_new_names)
                    if guard_new_names and leaks_names(turn, config, allowed):
                        turn = generate_buyer_turn(client, config, scenario, slot["goal"], messages, guard_new_names)
                    if not turn or (guard_new_names and leaks_names(turn, config, allowed)):
                        turn = slot["fallback"]
                except Exception as e:
                    print(f"    buyer generation failed ({e}); using scripted fallback", file=sys.stderr)
                    turn = slot["fallback"]
            messages.append({"role": "user", "content": turn})
            answer, urls = provider.ask(messages)
            for url in urls:
                if url not in retrieved:
                    retrieved.append(url)
            messages.append({"role": "assistant", "content": answer})

    run_stage(problem_stage(), guard_new_names=True)

    unprompted = assistant_named(messages, config)
    if unprompted:
        pathway = "vendor_comparison"
        continuation = comparison_continuation(
            config["brand"], unprompted, brand_named=config["brand"] in unprompted
        )
    else:
        pathway = "standard"
        continuation = standard_continuation(config["brand"])

    for stage in continuation:
        # Buyer may discuss vendors the assistant has named; may not introduce
        # new config-known names until the brand stage.
        run_stage(stage, guard_new_names=(stage["id"] in ("vendors", "head-to-head")))
    return messages, pathway, unprompted, retrieved


def transcript_text(messages: list) -> str:
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)


def extract_session(client: anthropic.Anthropic, transcript: str, brand: str, category: str) -> dict:
    response = client.messages.create(
        model=ANALYSIS_MODEL,
        max_tokens=4096,
        output_config={"format": {"type": "json_schema", "schema": SESSION_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                f"Target brand: {brand}\nTarget category: {category}\n\n"
                "Below is a buyer-journey chat with an AI assistant (8 buyer turns "
                "across 4 stages: situation and prioritization; vendor shortlist "
                "and top-pick defense; direct question about the target brand and "
                "the basis/currency of that view; then pressure on the concerns, a "
                "final call, a CEO pitch, and the evidence that would change its "
                "mind). The buyer's follow-ups are adaptive, written in character "
                "from the ICP definition, so wording varies between sessions. "
                "Extract the data per the schema, judging only from what the assistant "
                f"actually said.\n\n<transcript>\n{transcript}\n</transcript>"
            ),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def synthesize(client: anthropic.Anthropic, audit: dict) -> str:
    """Turn all session extractions into positioning and content recommendations."""
    condensed = [
        {k: v for k, v in s.items() if k != "transcript"}
        for s in audit["sessions"]
    ]
    icp = audit["icp"]
    prompt = (
        f"You are analyzing an AI brand perception audit for {audit['brand']} "
        f"(category: {audit['category']}; "
        f"known competitors: {', '.join(audit['competitors']) or 'not specified'}).\n\n"
        f"The buyer persona: {icp['role']} at {icp['description']} "
        f"Jobs to be done: {'; '.join(icp['jobs_to_be_done'])}. "
        f"Priorities: {'; '.join(icp['priorities'])}."
        + (f" Buying moment: {icp['buying_moment']}" if icp.get("buying_moment") else "")
        + (f" Installed stack: {', '.join(icp['installed_stack'])}." if icp.get("installed_stack") else "")
        + (f" Decision criteria: {'; '.join(icp['decision_criteria'])}." if icp.get("decision_criteria") else "")
        + "\n\n"
        "Below are structured extractions from buyer-journey chat sessions: each "
        "scenario is a situation where this persona's jobs hit a challenge, run "
        "against each AI assistant. Each session's 'pathway' field matters: "
        "'vendor_comparison' means the assistant named vendors unprompted in "
        "stage 1 (the category-to-vendor mapping already works for that problem "
        "framing) and the session became a head-to-head; 'standard' means the "
        "buyer had to open the vendor conversation themselves (a category "
        "mapping gap for that framing). Read pathway distribution as a finding "
        "in itself. Each session's 'framing' field is the question shape the "
        "buyer opened with (operational, platform, methodology, validation): "
        "compare framings explicitly, since which framings unlock the category "
        "and the brand is a core finding. If sessions include "
        "'retrieved_sources' (URLs the assistant actually consulted live), "
        "analyze them: which domains carried the verdict, first-party vs "
        "third-party, and make every content recommendation name the specific "
        "venue it should live in, based on what was actually retrieved.\n\n"
        f"{json.dumps(condensed, indent=2)}\n\n"
        "Write the analysis sections of the audit report in markdown (start at "
        "'## How AI models see the brand'). Cover:\n"
        "1. How AI models see the brand versus competitors (consistent beliefs, "
        "where the brand wins and loses, differences between assistants and scenarios). "
        "Include what happened under pressure: which qualifiers dissolved when the "
        "buyer pushed back (soft objections), which stood as conditions, and which "
        "hardened into dealbreakers or a switch to a competitor (real objections).\n"
        "2. What information drives AI opinion (which claims and sources the verdicts "
        "rest on, whether the brand's own content is shaping them or third parties are).\n"
        "3. What proof AI models need to see to choose the brand. Present this as a "
        "markdown table with exactly these columns: "
        "'Rank | Proof gap | Sessions flagging it | Impact on recommendation'. "
        "In the 'Impact on recommendation' column, write one plain-English sentence "
        "describing what the missing proof actually did to the verdict, for example "
        "'Main reason the assistant recommended a competitor instead' or 'Softened "
        "the verdict from strong to qualified' or 'Added hedging but did not change "
        "the pick'. Never use yes/no or 'partially' as the value. Give special "
        "weight to each session's flip_condition: that is the evidence the "
        "assistant itself named as what would change its final call.\n"
        "4. Recommended positioning and content changes: concrete, prioritized actions "
        "(positioning language, proof points to publish, content to create, where to "
        "place it) that would move these assistants toward recommending the brand.\n"
        "Be specific and evidence-bound: every claim should trace to the session data. "
        "No filler.\n"
        "Style: write like a senior consultant, in plain professional prose. Never use "
        "em dashes; use commas, colons, or separate sentences. Use bold sparingly, only "
        "for verdict-level takeaways. No exclamation marks, no rhetorical questions, no "
        "'delve', 'landscape', 'leverage' or similar filler vocabulary."
    )
    with client.messages.stream(
        model=ANALYSIS_MODEL,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()
    return "".join(b.text for b in response.content if b.type == "text")


def preflight(providers, skipped, config) -> None:
    """Check every key, report what usage info each API exposes."""
    print("\nPre-flight check", file=sys.stderr)
    print("----------------", file=sys.stderr)
    for p in providers:
        result = p.preflight()
        status = "OK " if result["ok"] else "FAIL"
        print(f"  [{status}] {p.name} ({p.model}): {result['detail']}", file=sys.stderr)
    for name in skipped:
        print(f"  [SKIP] {name}: no API key set", file=sys.stderr)
    n_cells = sum(len(s.get("framings") or ["operational"]) for s in config["scenarios"])
    n_sessions = n_cells * len(providers)
    print(
        f"\nPlanned run: {n_cells} scenario-framing cell(s) x {len(providers)} assistant(s) "
        f"= {n_sessions} sessions of 8 turns each, plus {n_sessions} extraction call(s) "
        "and 1 synthesis call on Claude.",
        file=sys.stderr,
    )


def confirm_selection(providers):
    """Ask which assistants to include; return the filtered provider list."""
    names = [p.name for p in providers]
    answer = input(
        f"\nRun across which assistants? [{', '.join(names)}] "
        "(Enter for all, or a comma-separated subset, or 'q' to abort): "
    ).strip().lower()
    if answer == "q":
        sys.exit("Aborted.")
    if not answer:
        return providers
    chosen = {a.strip() for a in answer.split(",")}
    unknown = chosen - set(names)
    if unknown:
        sys.exit(f"Unknown assistant(s): {', '.join(sorted(unknown))}. Available: {', '.join(names)}")
    return [p for p in providers if p.name in chosen]


def run_audit(config: dict, providers: list) -> dict:
    client = anthropic.Anthropic()
    sessions, failed = [], []
    for scenario in config["scenarios"]:
        for framing in scenario.get("framings") or ["operational"]:
            for provider in providers:
                label = f"{scenario['id']} [{framing}] x {provider.name}"
                print(f"  session: {label} ...", file=sys.stderr)
                try:
                    messages, pathway, unprompted, retrieved = conduct_session(
                        provider, client, config, scenario, framing
                    )
                    transcript = transcript_text(messages)
                    data = extract_session(client, transcript, config["brand"], config["category"])
                except Exception as e:
                    print(f"    FAILED ({e}); continuing with remaining sessions", file=sys.stderr)
                    failed.append({
                        "scenario": scenario["id"], "framing": framing,
                        "assistant": provider.name, "error": str(e),
                    })
                    continue
                sessions.append({
                    "scenario": scenario["id"],
                    "framing": framing,
                    "assistant": provider.name,
                    "assistant_model": provider.model,
                    "retrieval_enabled": getattr(provider, "retrieval", False),
                    "retrieved_sources": retrieved,
                    "pathway": pathway,
                    "unprompted_vendors_stage1": unprompted,
                    "transcript": transcript,
                    **data,
                })

    if not sessions:
        sys.exit("Every session failed; nothing to analyze.")
    audit = {
        **{k: config[k] for k in ["brand", "category", "icp", "competitors", "scenarios"]},
        "date": date.today().isoformat(),
        "sessions": sessions,
        "failed_sessions": failed,
    }
    print("  synthesizing recommendations ...", file=sys.stderr)
    audit["analysis"] = synthesize(client, audit)
    return audit


def funnel_counts(brand: str, sessions: list) -> list:
    n = len(sessions)
    return [
        ("Category proposed", sum(1 for s in sessions if s["category_proposed"]), n),
        ("Brand mentioned unprompted", sum(1 for s in sessions if s["unprompted_brand_mention"]), n),
        ("Brand shortlisted", sum(
            1 for s in sessions
            if any(brand.lower() in v.lower() for v in s["shortlist"])
        ), n),
        ("Strong recommendation", sum(1 for s in sessions if s["brand_recommendation"] == "strong"), n),
        ("Final call under pressure", sum(1 for s in sessions if s["final_call"] == "target_brand"), n),
    ]


def journey_map(audit: dict) -> list:
    """Render the buyer journey as a mermaid flowchart with drop-off branches."""
    sessions = audit["sessions"]
    n = len(sessions)
    stages = funnel_counts(audit["brand"], sessions)
    lines = ["## Buyer journey map", "", "```mermaid", "flowchart LR"]
    lines.append(f'    S0(["{audit["icp"]["role"]}<br/>states the problem<br/>({n} session{"s" if n != 1 else ""})"])')

    prev_node, prev_count = "S0", n
    last_drop = None
    for i, (label, count, _) in enumerate(stages, start=1):
        node = f"S{i}"
        lines.append(f'    {node}["{label}<br/>{count}/{n}"]')
        lines.append(f'    {prev_node} -->|"{count} continue"| {node}')
        lost = prev_count - count
        if lost > 0:
            last_drop = f"D{i}"
            lines.append(f'    {last_drop}["DROP-OFF: {lost} session{"s" if lost != 1 else ""}"]')
            lines.append(f'    {prev_node} -.->|"{lost} lost"| {last_drop}')
        prev_node, prev_count = node, count

    lost_final = [
        s for s in sessions
        if s["final_call"] == "competitor" and s["final_call_vendor"]
    ]
    if lost_final:
        diverted = sorted({s["final_call_vendor"] for s in lost_final})
        lines.append(f'    W["Final call diverted to:<br/>{", ".join(diverted)}"]')
        # Attach to the last drop-off if one exists, else to the final stage
        origin = last_drop or f"S{len(stages)}"
        lines.append(f'    {origin} -.->|"{len(lost_final)} session{"s" if len(lost_final) != 1 else ""}"| W')

    lines += ["```", ""]
    return lines


def write_report(audit: dict, out_path: str) -> None:
    sessions = audit["sessions"]
    n = len(sessions)
    icp = audit["icp"]
    stages = funnel_counts(audit["brand"], sessions)

    lines = [
        f"# AI Brand Perception Audit: {audit['brand']}",
        "",
        f"- **Category:** {audit['category']}",
        f"- **Buyer persona:** {icp['role']} — {icp['description']}",
        f"- **Jobs to be done:** {'; '.join(icp['jobs_to_be_done'])}",
        f"- **Priorities:** {'; '.join(icp['priorities'])}",
        f"- **Scenarios:** {', '.join(s['id'] for s in audit['scenarios'])}",
        f"- **Assistants probed:** {', '.join(sorted({s['assistant'] for s in sessions}))}",
        f"- **Sessions:** {n} (scenarios x assistants) | **Date:** {audit['date']}",
        *(
            [f"- **Failed sessions (excluded):** " + ", ".join(
                f"{f['scenario']} [{f.get('framing', 'operational')}] x {f['assistant']}" for f in audit.get("failed_sessions", [])
            )] if audit.get("failed_sessions") else []
        ),
        "",
        "## The funnel",
        "",
        "| Stage | Result |",
        "|---|---|",
    ]
    lines += [f"| {label} | {count}/{total} |" for label, count, total in stages]
    lines += ["", *journey_map(audit), "## Session summaries", ""]

    for s in sessions:
        comp = (
            f"{s['competitor_preferred']} ({s['competitor_preferred_reason']})"
            if s["competitor_preferred"] else "none"
        )
        pathway_note = (
            f"vendor comparison (assistant named {', '.join(s['unprompted_vendors_stage1'])} unprompted in stage 1)"
            if s.get("pathway") == "vendor_comparison" else "standard (buyer had to open the vendor conversation)"
        )
        lines += [
            f"### {s['scenario']} [{s.get('framing', 'operational')}] x {s['assistant']}",
            "",
            f"- Pathway: {pathway_note}",
            f"- Sources retrieved live: {', '.join(s['retrieved_sources']) if s.get('retrieved_sources') else ('none (retrieval on, answered from memory)' if s.get('retrieval_enabled') else 'n/a (parametric probe, no retrieval)')}",
            f"- Category proposed: {s['category_proposed']} (as: {', '.join(s['category_terms_used']) or 'n/a'})",
            f"- Shortlist: {', '.join(s['shortlist']) or 'none given'}",
            f"- Verdict on {audit['brand']}: **{s['brand_recommendation']}**",
            f"- Qualifiers: {'; '.join(s['qualifiers']) or 'none'}",
            f"- Preferred over you: {comp}",
            f"- Sources cited: {', '.join(s['sources_cited']) or 'none stated'}"
            + ("" if s["brand_sources_first_party"] else " (nothing from the brand's own content)"),
            f"- Proof gaps: {'; '.join(s['proof_gaps']) or 'none identified'}",
            f"- Under pressure: **{s['pressure_outcome'].replace('_', ' ')}** | final call: "
            + (f"**{s['final_call_vendor'] or audit['brand']}**" if s["final_call"] != "neither_or_defer" else "**deferred**"),
            f"- Dealbreakers: {'; '.join(s['dealbreakers']) or 'none'}",
            f"- Own-information confidence: {s['information_confidence'] or 'not stated'}",
            f"- CEO pitch for the final call: {s['ceo_pitch'] or 'none given'}",
            f"- Would change its mind if: {s['flip_condition'] or 'nothing named'}",
            "",
        ]

    lines += [audit["analysis"], ""]
    with open(out_path, "w") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a B2B AI brand perception audit.")
    parser.add_argument("config", nargs="?", help="Path to the audit config JSON (see --init)")
    parser.add_argument("--init", action="store_true", help="Write audit-config.json template and exit")
    parser.add_argument("--models", default=None, help="Comma-separated subset of: claude,chatgpt,gemini (default: all with keys)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--retrieval", action="store_true", help="Probe with live web search enabled (Claude, Gemini); captures which URLs each assistant consults")
    parser.add_argument("--preflight", action="store_true", help="Check keys and available usage info, then exit without running")
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation and run across all available assistants")
    args = parser.parse_args()

    if args.init:
        path = "audit-config.json"
        if os.path.exists(path):
            sys.exit(f"{path} already exists; not overwriting.")
        with open(path, "w") as f:
            json.dump(CONFIG_TEMPLATE, f, indent=2)
        print(f"Template written to {path}. Fill it in, then run: python audit.py {path}")
        return

    if not args.config:
        parser.error("provide a config file, or --init to create one")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is required (analysis engine). https://platform.claude.com/")

    config = load_config(args.config)
    requested = [m.strip() for m in args.models.split(",")] if args.models else None
    providers, skipped = active_providers(requested, retrieval=args.retrieval)
    if not providers:
        sys.exit("No probe models available. Set ANTHROPIC_API_KEY at minimum.")

    preflight(providers, skipped, config)
    if args.preflight:
        return
    if not args.yes and sys.stdin.isatty():
        providers = confirm_selection(providers)

    audit = run_audit(config, providers)

    out_path = args.out or f"report-{config['brand'].lower().replace(' ', '-')}-{audit['date']}.md"
    write_report(audit, out_path)

    raw_path = out_path.replace(".md", ".json")
    with open(raw_path, "w") as f:
        json.dump(audit, f, indent=2)
    print(f"\nReport: {out_path}\nRaw data (incl. transcripts): {raw_path}")


if __name__ == "__main__":
    main()
