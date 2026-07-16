#!/usr/bin/env python3
"""AI Brand Perception Audit.

Asks an AI model realistic buyer questions about a product category,
then measures which brands get mentioned and recommended. The probe
question never names the brand you are auditing, so the answers reflect
what the model actually believes, not what you primed it with.

Usage:
    python audit.py --brand "Notion" --category "team knowledge base tools" \
        --competitors "Coda,Confluence,Slite" --runs 2

Requires: pip install anthropic, and ANTHROPIC_API_KEY set in your environment.
"""

import argparse
import json
import os
import sys
from datetime import date

import anthropic

from scenarios import build_scenarios

MODEL = "claude-opus-4-8"

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "brands_mentioned": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Every product or company brand named in the answer, in order of appearance",
        },
        "top_recommendation": {
            "type": ["string", "null"],
            "description": "The single brand the answer most strongly recommends, or null if none",
        },
        "target_brand_mentioned": {"type": "boolean"},
        "target_brand_sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "negative", "not_mentioned"],
        },
        "reason_for_top_pick": {
            "type": ["string", "null"],
            "description": "One sentence on why the top recommendation won, or null",
        },
    },
    "required": [
        "brands_mentioned",
        "top_recommendation",
        "target_brand_mentioned",
        "target_brand_sentiment",
        "reason_for_top_pick",
    ],
    "additionalProperties": False,
}


def probe(client: anthropic.Anthropic, question: str) -> str:
    """Ask the buyer question with no brand priming and return the answer text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": question}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


def extract(client: anthropic.Anthropic, answer: str, target_brand: str) -> dict:
    """Parse a probe answer into structured mention/recommendation data."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    f"The target brand being audited is: {target_brand}\n\n"
                    "Analyze this AI-generated buying advice and extract the data "
                    f"per the schema.\n\n<answer>\n{answer}\n</answer>"
                ),
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def run_audit(brand: str, category: str, competitors: list[str], runs: int) -> dict:
    client = anthropic.Anthropic()
    scenarios = build_scenarios(category)
    results = []

    for scenario in scenarios:
        for run_index in range(runs):
            label = f"{scenario['id']} (run {run_index + 1}/{runs})"
            print(f"  probing: {label} ...", file=sys.stderr)
            answer = probe(client, scenario["question"])
            data = extract(client, answer, brand)
            results.append(
                {
                    "scenario_id": scenario["id"],
                    "persona": scenario["persona"],
                    "question": scenario["question"],
                    "answer": answer,
                    **data,
                }
            )

    return {
        "brand": brand,
        "category": category,
        "competitors": competitors,
        "model": MODEL,
        "date": date.today().isoformat(),
        "runs_per_scenario": runs,
        "results": results,
    }


def write_report(audit: dict, out_path: str) -> None:
    results = audit["results"]
    total = len(results)
    mentioned = sum(1 for r in results if r["target_brand_mentioned"])
    recommended = sum(
        1
        for r in results
        if r["top_recommendation"]
        and r["top_recommendation"].lower() == audit["brand"].lower()
    )

    # How often each brand (yours + rivals) wins the recommendation
    win_counts: dict[str, int] = {}
    for r in results:
        pick = r["top_recommendation"]
        if pick:
            win_counts[pick] = win_counts.get(pick, 0) + 1

    lines = [
        f"# AI Brand Perception Audit: {audit['brand']}",
        "",
        f"- **Category:** {audit['category']}",
        f"- **Model probed:** {audit['model']}",
        f"- **Date:** {audit['date']}",
        f"- **Probes:** {total} ({audit['runs_per_scenario']} run(s) x {total // audit['runs_per_scenario']} scenarios)",
        "",
        "## Headline numbers",
        "",
        f"- Mention rate: **{mentioned}/{total}** probes named {audit['brand']} at all",
        f"- Recommendation rate: **{recommended}/{total}** probes picked {audit['brand']} as the top choice",
        "",
        "## Who wins the recommendation",
        "",
        "| Brand | Top-pick count |",
        "|---|---|",
    ]
    for name, count in sorted(win_counts.items(), key=lambda kv: -kv[1]):
        marker = " **(you)**" if name.lower() == audit["brand"].lower() else ""
        lines.append(f"| {name}{marker} | {count} |")

    lines += ["", "## Probe-by-probe detail", ""]
    for r in results:
        lines += [
            f"### {r['scenario_id']} — {r['persona']}",
            "",
            f"**Question:** {r['question']}",
            "",
            f"- Target mentioned: {r['target_brand_mentioned']} ({r['target_brand_sentiment']})",
            f"- Top recommendation: {r['top_recommendation']}",
            f"- Why: {r['reason_for_top_pick']}",
            f"- All brands named: {', '.join(r['brands_mentioned']) or 'none'}",
            "",
        ]

    with open(out_path, "w") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an AI brand perception audit.")
    parser.add_argument("--brand", required=True, help="The brand you are auditing")
    parser.add_argument("--category", required=True, help='Buyer-language category, e.g. "team knowledge base tools"')
    parser.add_argument("--competitors", default="", help="Comma-separated rival brands (used in the report only)")
    parser.add_argument("--runs", type=int, default=1, help="Runs per scenario (more runs = more stable numbers)")
    parser.add_argument("--out", default=None, help="Report path (default: report-<brand>-<date>.md)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first: https://platform.claude.com/")

    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]
    audit = run_audit(args.brand, args.category, competitors, args.runs)

    out_path = args.out or f"report-{args.brand.lower().replace(' ', '-')}-{audit['date']}.md"
    write_report(audit, out_path)

    raw_path = out_path.replace(".md", ".json")
    with open(raw_path, "w") as f:
        json.dump(audit, f, indent=2)

    print(f"\nReport: {out_path}\nRaw data: {raw_path}")


if __name__ == "__main__":
    main()
