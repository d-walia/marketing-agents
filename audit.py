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

from journey import build_journey
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
    },
    "required": [
        "category_proposed", "category_terms_used", "unprompted_brand_mention",
        "shortlist", "brand_recommendation", "qualifiers", "competitor_preferred",
        "competitor_preferred_reason", "sources_cited", "brand_sources_first_party",
        "beliefs_about_brand", "proof_gaps", "final_call", "final_call_vendor",
        "pressure_outcome", "dealbreakers",
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
    if problems:
        sys.exit("Config problems:\n  - " + "\n  - ".join(problems)
                 + "\nSee 'python audit.py --init' for the expected shape.")
    config.setdefault("competitors", [])
    return config


def conduct_session(provider, turns: list) -> list:
    """Run one multi-turn chat with an assistant; return the full transcript."""
    messages = []
    for turn in turns:
        messages.append({"role": "user", "content": turn})
        answer = provider.ask(messages)
        messages.append({"role": "assistant", "content": answer})
    return messages


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
                "Below is a buyer-journey chat with an AI assistant (4 buyer turns: "
                "situation, vendor shortlist, direct question about the target brand, "
                "then pressure on the concerns and a demand for a final call). "
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
        f"Priorities: {'; '.join(icp['priorities'])}.\n\n"
        "Below are structured extractions from buyer-journey chat sessions: each "
        "scenario is a situation where this persona's jobs hit a challenge, run "
        "against each AI assistant.\n\n"
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
        "the pick'. Never use yes/no or 'partially' as the value.\n"
        "4. Recommended positioning and content changes: concrete, prioritized actions "
        "(positioning language, proof points to publish, content to create, where to "
        "place it) that would move these assistants toward recommending the brand.\n"
        "Be specific and evidence-bound: every claim should trace to the session data. "
        "No filler."
    )
    with client.messages.stream(
        model=ANALYSIS_MODEL,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()
    return "".join(b.text for b in response.content if b.type == "text")


def run_audit(config: dict, requested_models) -> dict:
    client = anthropic.Anthropic()
    providers, skipped = active_providers(requested_models)
    if not providers:
        sys.exit("No probe models available. Set ANTHROPIC_API_KEY at minimum.")
    if skipped:
        print(f"  skipping (no API key): {', '.join(skipped)}", file=sys.stderr)

    sessions = []
    for scenario in config["scenarios"]:
        for provider in providers:
            print(f"  session: {scenario['id']} x {provider.name} ...", file=sys.stderr)
            turns = build_journey(config["icp"], scenario, config["brand"])
            messages = conduct_session(provider, turns)
            transcript = transcript_text(messages)
            data = extract_session(client, transcript, config["brand"], config["category"])
            sessions.append({
                "scenario": scenario["id"],
                "assistant": provider.name,
                "assistant_model": provider.model,
                "transcript": transcript,
                **data,
            })

    audit = {
        **{k: config[k] for k in ["brand", "category", "icp", "competitors", "scenarios"]},
        "date": date.today().isoformat(),
        "sessions": sessions,
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
    for i, (label, count, _) in enumerate(stages, start=1):
        node = f"S{i}"
        lines.append(f'    {node}["{label}<br/>{count}/{n}"]')
        lines.append(f'    {prev_node} -->|"{count} continue"| {node}')
        lost = prev_count - count
        if lost > 0:
            drop = f"D{i}"
            lines.append(f'    {drop}["DROP-OFF: {lost} session{"s" if lost != 1 else ""}"]')
            lines.append(f'    {prev_node} -.->|"{lost} lost"| {drop}')
        prev_node, prev_count = node, count

    diverted = sorted({
        s["final_call_vendor"] for s in sessions
        if s["final_call"] == "competitor" and s["final_call_vendor"]
    })
    if diverted:
        lines.append(f'    W["Recommendation diverted to:<br/>{", ".join(diverted)}"]')
        lines.append(f'    D{len(stages)} --> W')

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
        lines += [
            f"### {s['scenario']} x {s['assistant']}",
            "",
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
            "",
        ]

    lines += [audit["analysis"], ""]
    with open(out_path, "w") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a B2B AI brand perception audit.")
    parser.add_argument("config", nargs="?", help="Path to the audit config JSON (see --init)")
    parser.add_argument("--init", action="store_true", help="Write audit-config.json template and exit")
    parser.add_argument("--models", default=None, help="Comma-separated subset of: claude,chatgpt,gemini,perplexity (default: all with keys)")
    parser.add_argument("--out", default=None)
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
    audit = run_audit(config, requested)

    out_path = args.out or f"report-{config['brand'].lower().replace(' ', '-')}-{audit['date']}.md"
    write_report(audit, out_path)

    raw_path = out_path.replace(".md", ".json")
    with open(raw_path, "w") as f:
        json.dump(audit, f, indent=2)
    print(f"\nReport: {out_path}\nRaw data (incl. transcripts): {raw_path}")


if __name__ == "__main__":
    main()
