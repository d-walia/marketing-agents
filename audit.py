#!/usr/bin/env python3
"""AI Brand Perception Audit (B2B).

Runs multi-turn buyer-journey chat sessions against the AI assistants your
buyers actually use, posing as your ICP. Measures whether your category gets
proposed for the buyer's problem, whether your brand surfaces and gets
recommended, with what qualifiers and sources, and who beats you. Then
synthesizes positioning and content recommendations: what AI models believe
about you, what drives that opinion, and what proof would change it.

Usage:
    python audit.py \
        --brand "Acme Analytics" \
        --category "product analytics platforms" \
        --icp "Series B B2B SaaS companies, 50-200 employees, PLG motion" \
        --problem "We can't tell which product features drive retention, and churn is creeping up" \
        --competitors "Amplitude,Mixpanel,Heap"

Requires ANTHROPIC_API_KEY (probing + analysis). Optional: OPENAI_API_KEY,
GEMINI_API_KEY, PERPLEXITY_API_KEY to probe those assistants too.
"""

import argparse
import json
import os
import sys
from datetime import date

import anthropic

from journey import DEFAULT_PERSONA, build_journey, make_persona
from providers import active_providers

ANALYSIS_MODEL = "claude-opus-4-8"

SESSION_SCHEMA = {
    "type": "object",
    "properties": {
        "category_proposed": {
            "type": "boolean",
            "description": "In turn 1, did the assistant propose the target product category as a solution to the problem?",
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
    },
    "required": [
        "category_proposed", "category_terms_used", "unprompted_brand_mention",
        "shortlist", "brand_recommendation", "qualifiers", "competitor_preferred",
        "competitor_preferred_reason", "sources_cited", "brand_sources_first_party",
        "beliefs_about_brand", "proof_gaps",
    ],
    "additionalProperties": False,
}


def conduct_session(provider, turns: list[str]) -> list[dict]:
    """Run one multi-turn chat with an assistant; return the full transcript."""
    messages: list[dict] = []
    for turn in turns:
        messages.append({"role": "user", "content": turn})
        answer = provider.ask(messages)
        messages.append({"role": "assistant", "content": answer})
    return messages


def transcript_text(messages: list[dict]) -> str:
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
                "Below is a buyer-journey chat with an AI assistant (3 buyer turns: "
                "problem, vendor shortlist, direct question about the target brand). "
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
    prompt = (
        f"You are analyzing an AI brand perception audit for {audit['brand']} "
        f"(category: {audit['category']}; ICP: {audit['icp']}; "
        f"buyer persona: {audit['persona']}; "
        f"known competitors: {', '.join(audit['competitors']) or 'not specified'}).\n\n"
        "Below are structured extractions from buyer-journey chat sessions, the "
        "same buyer persona run against each AI assistant.\n\n"
        f"{json.dumps(condensed, indent=2)}\n\n"
        "Write the analysis sections of the audit report in markdown (start at "
        "'## How AI models see the brand'). Cover:\n"
        "1. How AI models see the brand versus competitors (consistent beliefs, "
        "where the brand wins and loses, differences between assistants).\n"
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


def run_audit(args) -> dict:
    client = anthropic.Anthropic()
    requested = [p.strip() for p in args.models.split(",")] if args.models else None
    providers, skipped = active_providers(requested)
    if not providers:
        sys.exit("No probe models available. Set ANTHROPIC_API_KEY at minimum.")
    if skipped:
        print(f"  skipping (no API key): {', '.join(skipped)}", file=sys.stderr)

    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]
    persona = make_persona(args.persona) if args.persona else DEFAULT_PERSONA
    sessions = []
    for provider in providers:
        print(f"  session: {provider.name} x {persona['id']} ...", file=sys.stderr)
        turns = build_journey(persona, args.icp, args.problem, args.brand)
        messages = conduct_session(provider, turns)
        transcript = transcript_text(messages)
        data = extract_session(client, transcript, args.brand, args.category)
        sessions.append({
            "assistant": provider.name,
            "assistant_model": provider.model,
            "persona": persona["label"],
            "transcript": transcript,
            **data,
        })

    audit = {
        "brand": args.brand,
        "category": args.category,
        "icp": args.icp,
        "problem": args.problem,
        "persona": persona["label"],
        "competitors": competitors,
        "date": date.today().isoformat(),
        "sessions": sessions,
    }
    print("  synthesizing recommendations ...", file=sys.stderr)
    audit["analysis"] = synthesize(client, audit)
    return audit


def journey_map(audit: dict, stages: list) -> list:
    """Render the buyer journey as a mermaid flowchart with drop-off branches.

    stages: list of (label, count) in funnel order. A drop-off branch is drawn
    at every stage where sessions were lost, annotated with where they went.
    """
    sessions = audit["sessions"]
    n = len(sessions)
    lines = ["## Buyer journey map", "", "```mermaid", "flowchart LR"]
    lines.append(f'    S0(["{audit["persona"]}<br/>states the problem<br/>({n} session{"s" if n != 1 else ""})"])')

    prev_node, prev_count = "S0", n
    for i, (label, count) in enumerate(stages, start=1):
        node = f"S{i}"
        lines.append(f'    {node}["{label}<br/>{count}/{n}"]')
        lines.append(f'    {prev_node} -->|"{count} continue"| {node}')
        lost = prev_count - count
        if lost > 0:
            drop = f"D{i}"
            lines.append(f'    {drop}["DROP-OFF: {lost} session{"s" if lost != 1 else ""}"]')
            lines.append(f'    {prev_node} -.->|"{lost} lost"| {drop}')
        prev_node, prev_count = node, count

    # Where the lost recommendations went, if anywhere
    diverted = sorted({
        s["competitor_preferred"] for s in sessions
        if s["competitor_preferred"] and s["brand_recommendation"] != "strong"
    })
    if diverted:
        lines.append(f'    W["Recommendation diverted to:<br/>{", ".join(diverted)}"]')
        lines.append(f'    D{len(stages)} --> W')

    lines += ["```", ""]
    return lines


def write_report(audit: dict, out_path: str) -> None:
    sessions = audit["sessions"]
    n = len(sessions)
    cat = sum(1 for s in sessions if s["category_proposed"])
    unprompted = sum(1 for s in sessions if s["unprompted_brand_mention"])
    shortlisted = sum(
        1 for s in sessions
        if any(audit["brand"].lower() in v.lower() for v in s["shortlist"])
    )
    strong = sum(1 for s in sessions if s["brand_recommendation"] == "strong")
    stages = [
        ("Category proposed", cat),
        ("Brand mentioned unprompted", unprompted),
        ("Brand shortlisted", shortlisted),
        ("Strong recommendation", strong),
    ]

    lines = [
        f"# AI Brand Perception Audit: {audit['brand']}",
        "",
        f"- **Category:** {audit['category']}",
        f"- **ICP:** {audit['icp']}",
        f"- **Buyer persona:** {audit['persona']}",
        f"- **Buyer problem probed:** {audit['problem']}",
        f"- **Assistants probed:** {', '.join(sorted({s['assistant'] for s in sessions}))}",
        f"- **Sessions:** {n} (one per assistant) | **Date:** {audit['date']}",
        "",
        "## The funnel",
        "",
        "| Stage | Result |",
        "|---|---|",
        f"| Category proposed for the buyer's problem | {cat}/{n} |",
        f"| Brand mentioned unprompted | {unprompted}/{n} |",
        f"| Brand made the vendor shortlist | {shortlisted}/{n} |",
        f"| Strong recommendation when asked directly | {strong}/{n} |",
        "",
        *journey_map(audit, stages),
        "## Session summaries",
        "",
    ]
    for s in sessions:
        comp = (
            f"{s['competitor_preferred']} ({s['competitor_preferred_reason']})"
            if s["competitor_preferred"] else "none"
        )
        lines += [
            f"### {s['assistant']} x {s['persona']}",
            "",
            f"- Category proposed: {s['category_proposed']} (as: {', '.join(s['category_terms_used']) or 'n/a'})",
            f"- Shortlist: {', '.join(s['shortlist']) or 'none given'}",
            f"- Verdict on {audit['brand']}: **{s['brand_recommendation']}**",
            f"- Qualifiers: {'; '.join(s['qualifiers']) or 'none'}",
            f"- Preferred over you: {comp}",
            f"- Sources cited: {', '.join(s['sources_cited']) or 'none stated'}"
            + ("" if s["brand_sources_first_party"] else " (nothing from the brand's own content)"),
            f"- Proof gaps: {'; '.join(s['proof_gaps']) or 'none identified'}",
            "",
        ]

    lines += [audit["analysis"], ""]

    with open(out_path, "w") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a B2B AI brand perception audit.")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--category", required=True, help='Buyer-language category, e.g. "product analytics platforms"')
    parser.add_argument("--icp", required=True, help="Who the buyer is, in one or two sentences")
    parser.add_argument("--problem", required=True, help="The business pain in the buyer's own words (no category or vendor names)")
    parser.add_argument("--competitors", default="", help="Comma-separated rivals (context for the analysis)")
    parser.add_argument("--persona", default=None, help="Override the buyer persona (default: Head of Sales / Sales Ops leader). One audit = one ICP; run again to audit another persona.")
    parser.add_argument("--models", default=None, help="Comma-separated subset of: claude,chatgpt,gemini,perplexity (default: all with keys)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is required (analysis engine). https://platform.claude.com/")

    audit = run_audit(args)
    out_path = args.out or f"report-{args.brand.lower().replace(' ', '-')}-{audit['date']}.md"
    write_report(audit, out_path)

    raw_path = out_path.replace(".md", ".json")
    with open(raw_path, "w") as f:
        json.dump(audit, f, indent=2)
    print(f"\nReport: {out_path}\nRaw data (incl. transcripts): {raw_path}")


if __name__ == "__main__":
    main()
