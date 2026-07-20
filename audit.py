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
import re
import sys
from datetime import date

import anthropic

from journey import (
    BUYER_MODEL, FRAMINGS, PARAPHRASE_VENDOR_TURN, buyer_prompt,
    comparison_continuation, opening_turn, paraphrase_prompt, persona_intro,
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
    "positioning": [
        "optional, high value: how YOU describe the product, one claim per line. The audit compares these against what AI actually believes, which is the alignment gap.",
        "e.g. 'fastest contract turnaround in mid-market, days not weeks'",
        "e.g. 'works alongside your existing CLM rather than replacing it'",
    ],
    "verified_facts": [
        "optional, provided by the brand: your real, true, current facts and numbers, one per line. The audit grades every number AI stated about you against these, labelling each accurate, distorted, or fabricated. Give specifics with values.",
        "e.g. 'Starting price is 15,000 USD per year for up to 50 users'",
        "e.g. 'Median implementation time is 6 weeks, not 3 to 6 months'",
        "e.g. 'We integrate natively with Salesforce, HubSpot, and Slack'",
    ],
    "icp_variants": [
        {
            "_note": "optional: other seats at the buying table to sweep. Same shape as icp. Each one multiplies the run, so add deliberately.",
            "role": "e.g. 'Chief Financial Officer'",
            "description": "same company, different seat",
            "jobs_to_be_done": ["what this person is on the hook for"],
            "priorities": ["what this person cares about"],
        }
    ],
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
        "evidence_chain": {
            "type": "array",
            "description": "The evidence graph: for each substantive claim about the target brand, what that claim rests on. Shows whose information is doing the persuading.",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim about the brand, in the assistant's terms"},
                    "source": {"type": "string", "description": "What it rests on: a named URL or site, a source type (analyst, review site, case study), or 'training memory' if nothing was cited"},
                    "provenance": {
                        "type": "string",
                        "enum": ["first_party", "third_party", "training_memory", "unstated"],
                        "description": "first_party = the brand's own site or content; third_party = independent source; training_memory = the assistant said it was recalling rather than reading; unstated = no basis given",
                    },
                    "assistant_flagged_weakness": {
                        "type": "boolean",
                        "description": "Did the assistant itself caveat this source as self-reported, unverified, or stale?",
                    },
                },
                "required": ["claim", "source", "provenance", "assistant_flagged_weakness"],
                "additionalProperties": False,
            },
        },
        "quantified_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific numbers or metrics the assistant repeated about the brand, verbatim where possible (e.g. 'cut ramp from 210 to 75 days'). These claims are memorized and doing work.",
        },
        "citation_depth": {
            "type": "string",
            "enum": ["deep_pages", "homepage_only", "no_urls", "not_applicable"],
            "description": "Retrieval runs only: did the assistant cite specific product/use-case pages (deep_pages), only the homepage or bare brand name (homepage_only), or no URLs (no_urls)? Use not_applicable when no sources were retrieved.",
        },
        "competitor_counter_evidence": {
            "type": "array",
            "description": "Specific competitor assets the assistant reached for as counter-proof: named case studies, customers, analyst placements",
            "items": {
                "type": "object",
                "properties": {
                    "competitor": {"type": "string"},
                    "asset": {"type": "string", "description": "The named case study, customer, or report doing the damage"},
                    "criterion": {"type": "string", "description": "The buying criterion where this asset beat the target brand"},
                },
                "required": ["competitor", "asset", "criterion"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "category_proposed", "category_terms_used", "unprompted_brand_mention",
        "shortlist", "brand_recommendation", "qualifiers", "competitor_preferred",
        "competitor_preferred_reason", "sources_cited", "brand_sources_first_party",
        "beliefs_about_brand", "proof_gaps", "final_call", "final_call_vendor",
        "pressure_outcome", "dealbreakers", "ceo_pitch", "flip_condition",
        "information_confidence", "evidence_chain", "quantified_claims",
        "citation_depth", "competitor_counter_evidence",
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
        "venue it should live in, based on what was actually retrieved. "
        "Use 'evidence_chain' as the backbone of section 2: trace each belief to "
        "its source and provenance, and say plainly whether the brand's own "
        "content or third parties are doing the persuading. Call out any claim "
        "the assistant itself flagged as self-reported or unverified, since a "
        "proof base that traces entirely to vendor-published material is a "
        "structural weakness, not just a gap. Read 'quantified_claims' as the "
        "numbers already memorized and working, 'competitor_counter_evidence' as "
        "the named assets to out-publish, and 'citation_depth' as whether AI "
        "understands the product or merely knows the brand exists. If the "
        "presence trace shows the brand dropping out mid-conversation while rivals persist, treat that as a distinct finding from losing the final "
        "call: it means the brand fails as the buyer gets specific, and name which criterion the conversation had narrowed to.\n\n"
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


def preflight(providers, skipped, config, paraphrase: int = 0) -> None:
    """Check every key, report what usage info each API exposes."""
    print("\nPre-flight check", file=sys.stderr)
    print("----------------", file=sys.stderr)
    for p in providers:
        result = p.preflight()
        status = "OK " if result["ok"] else "FAIL"
        print(f"  [{status}] {p.name} ({p.model}): {result['detail']}", file=sys.stderr)
    for name in skipped:
        print(f"  [SKIP] {name}: no API key set", file=sys.stderr)
    n_personas = len(personas_for(config))
    n_cells = sum(len(s.get("framings") or ["operational"]) for s in config["scenarios"])
    n_sessions = n_cells * len(providers) * n_personas
    persona_note = f" x {n_personas} persona(s)" if n_personas > 1 else ""
    print(
        f"\nPlanned run: {n_cells} scenario-framing cell(s) x {len(providers)} assistant(s)"
        f"{persona_note} = {n_sessions} sessions of 8 turns each, plus {n_sessions} extraction "
        "call(s) and 1 synthesis call on Claude.",
        file=sys.stderr,
    )
    if n_personas > 1:
        print("  Personas: " + ", ".join(p["_label"] for p in personas_for(config)), file=sys.stderr)
    if paraphrase:
        n_probe = len(config["scenarios"]) * len(providers)
        print(
            f"  Paraphrase probes: {n_probe} probe(s) x {paraphrase} wordings = "
            f"{n_probe * paraphrase * 2} extra turns, plus {n_probe} stability call(s).",
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



STABILITY_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "description": "Every distinct claim made about the target brand across the variant answers",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "variants_appeared_in": {"type": "integer"},
                },
                "required": ["claim", "variants_appeared_in"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}

CONFIG_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "description": "Which config field, e.g. 'icp.jobs_to_be_done' or 'scenarios[0].situation'"},
                    "severity": {"type": "string", "enum": ["blocker", "weakens_results", "polish"]},
                    "problem": {"type": "string"},
                    "fix": {"type": "string", "description": "Concrete rewrite or addition, specific to this config"},
                },
                "required": ["field", "severity", "problem", "fix"],
                "additionalProperties": False,
            },
        },
        "readiness": {"type": "string", "enum": ["ready", "usable_with_gaps", "not_ready"]},
        "summary": {"type": "string"},
    },
    "required": ["findings", "readiness", "summary"],
    "additionalProperties": False,
}


def generate_paraphrases(client, scenario: dict, n: int) -> list:
    """Reword the situation n ways, holding intent constant."""
    resp = client.messages.create(
        model=BUYER_MODEL,
        max_tokens=1500,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": paraphrase_prompt(scenario, n)}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return [l.strip(" -*\t") for l in text.splitlines() if len(l.strip()) > 40][:n]


def brands_in(text: str, names: list) -> set:
    low = text.lower()
    return {nm for nm in names if nm.lower() in low}


def jaccard(a: set, b: set) -> float:
    if not (a | b):
        return 1.0
    return len(a & b) / len(a | b)


def run_paraphrase_probe(provider, client, config: dict, scenario: dict, n: int) -> dict:
    """Same intent, n wordings. Two turns each, so wording is the only variable."""
    names = [config["brand"], *config.get("competitors", [])]
    variants = generate_paraphrases(client, scenario, n)
    if not variants:
        return {}

    runs = []
    for wording in variants:
        msgs = [{"role": "user", "content": (
            f"{persona_intro(config['icp'])}\n\nHere's the situation I'm dealing with: "
            f"{wording}\n\nHow would you approach solving this?"
        )}]
        a1, _ = provider.ask(msgs)
        msgs += [{"role": "assistant", "content": a1},
                 {"role": "user", "content": PARAPHRASE_VENDOR_TURN}]
        a2, _ = provider.ask(msgs)
        answer = a1 + "\n" + a2
        runs.append({"wording": wording, "answer": answer,
                     "brands": sorted(brands_in(answer, names))})

    sets = [set(r["brands"]) for r in runs]
    pairs = [jaccard(sets[i], sets[j]) for i in range(len(sets)) for j in range(i + 1, len(sets))]
    hits = sum(1 for s in sets if config["brand"] in s)

    claims = []
    try:
        joined = "\n\n".join(
            f"=== VARIANT {i + 1} ===\n{r['answer'][:4000]}" for i, r in enumerate(runs)
        )
        resp = client.messages.create(
            model=ANALYSIS_MODEL, max_tokens=3000,
            output_config={"format": {"type": "json_schema", "schema": STABILITY_SCHEMA}},
            messages=[{"role": "user", "content": (
                f"Target brand: {config['brand']}. Below are {len(runs)} answers to the SAME "
                "question asked in different words. For every distinct claim made about the "
                "target brand, count how many numbered variants contained it. A claim in most "
                "variants is a stable belief; one appearing once is conversational noise."
                f"\n\n{joined}"
            )}],
        )
        claims = json.loads(next(b.text for b in resp.content if b.type == "text"))["claims"]
    except Exception as e:
        print(f"    stability extraction failed ({e})", file=sys.stderr)

    return {
        "scenario": scenario["id"], "assistant": provider.name,
        "variant_count": len(runs), "runs": runs,
        "mean_overlap": round(sum(pairs) / len(pairs), 3) if pairs else None,
        "brand_appearance_rate": f"{hits}/{len(runs)}",
        "brand_appearance_pct": round(100 * hits / len(runs)),
        "claims": claims,
    }


def review_config(client, config: dict) -> dict:
    """Critique the inputs before spending money on a run."""
    resp = client.messages.create(
        model=ANALYSIS_MODEL, max_tokens=4000,
        output_config={"format": {"type": "json_schema", "schema": CONFIG_REVIEW_SCHEMA}},
        messages=[{"role": "user", "content": (
            "You are reviewing the input config for an AI brand perception audit. The audit "
            "simulates a B2B buyer talking to AI assistants, so the quality of the buyer "
            "definition determines the quality of every finding.\n\n"
            "Judge against these standards:\n"
            "- category: must be the buyer's words, not marketing language.\n"
            "- icp.role and description: a specific person at a specific kind of company, not a segment.\n"
            "- jobs_to_be_done and priorities: outcomes this person is accountable for, concrete "
            "enough to drive trade-offs. 'Wants efficiency' is useless.\n"
            "- buying_moment: a trigger event and a pressure clock. Without it the simulated buyer "
            "does not push like a real one.\n"
            "- installed_stack: what a purchase must coexist with. This is where the strongest "
            "objections come from, and its absence is a common silent gap.\n"
            "- decision_criteria: proof thresholds and constraints the buyer raises unprompted.\n"
            "- positioning: the brand's own claims. Without it the audit cannot measure the gap "
            "between what the brand says and what AI believes.\n"
            "- verified_facts: the brand's real, checkable numbers and facts. Optional but valuable: "
            "with it the audit grades whether the numbers AI repeats are true. Flag any listed fact "
            "that is vague or lacks a value, since a fact with no number cannot verify a claim.\n"
            "- scenarios[].situation: one dominant pain in the buyer's own words, with NO category "
            "or vendor names. Multi-pain scenarios measure which pain the model latches onto "
            "rather than who wins. Category or vendor leakage invalidates the unprompted measurement.\n"
            "- competitors: the rivals AI would plausibly name, used for detection.\n\n"
            "Flag placeholder text left from the template as a blocker. Be specific: every fix "
            "should be a concrete rewrite for THIS config, not general advice.\n\n"
            f"CONFIG:\n{json.dumps(config, indent=2)}"
        )}],
    )
    return json.loads(next(b.text for b in resp.content if b.type == "text"))



VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ai_claim": {"type": "string", "description": "The claim or number AI stated about the brand"},
                    "verdict": {
                        "type": "string",
                        "enum": ["accurate", "distorted", "fabricated", "unverifiable"],
                        "description": "accurate = matches a provided fact; distorted = same topic as a provided fact but the value is wrong; fabricated = a specific claim that a provided fact directly contradicts or that no fact supports and would be knowable if true; unverifiable = the provided facts do not cover this topic",
                    },
                    "matched_fact": {"type": ["string", "null"], "description": "The provided fact this was checked against, or null"},
                    "note": {"type": "string", "description": "One sentence: how AI's claim compares to the fact"},
                },
                "required": ["ai_claim", "verdict", "matched_fact", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["checks"],
    "additionalProperties": False,
}


def verify_claims(client, audit: dict, verified_facts: list) -> list:
    """Grade every number/claim AI stated about the brand against brand-provided ground truth."""
    facts = [f for f in verified_facts if not str(f).startswith(("optional", "e.g."))]
    if not facts:
        return []
    claims = sorted({q for s in audit["sessions"] for q in (s.get("quantified_claims") or [])})
    for s in audit["sessions"]:
        for e in (s.get("evidence_chain") or []):
            c = e.get("claim", "")
            if any(ch.isdigit() for ch in c):
                claims.append(c)
    claims = sorted(set(claims))
    if not claims:
        return []
    try:
        resp = client.messages.create(
            model=ANALYSIS_MODEL, max_tokens=4000,
            output_config={"format": {"type": "json_schema", "schema": VERIFY_SCHEMA}},
            messages=[{"role": "user", "content": (
                f"The brand is {audit['brand']}. Below are TRUE FACTS the brand provided, then "
                "CLAIMS an AI assistant made about the brand. Grade each claim against the facts. "
                "A claim is accurate only if a fact supports its value; distorted if it is about a "
                "fact's topic but the number or detail is wrong; fabricated if a fact contradicts it "
                "or it is a specific checkable claim no fact supports; unverifiable if the facts do "
                "not cover its topic. Do not grade a claim accurate just because it sounds plausible."
                "\n\nTRUE FACTS:\n" + "\n".join(f"- {f}" for f in facts)
                + "\n\nAI CLAIMS:\n" + "\n".join(f"- {c}" for c in claims)
            )}],
        )
        return json.loads(next(b.text for b in resp.content if b.type == "text"))["checks"]
    except Exception as e:
        print(f"    fact verification failed ({e})", file=sys.stderr)
        return []


VERIFY_LABEL = {
    "accurate": "accurate", "distorted": "distorted",
    "fabricated": "fabricated", "unverifiable": "not covered",
}


def verification_report(audit: dict) -> list:
    checks = audit.get("fact_checks") or []
    if not checks:
        return []
    order = {"fabricated": 0, "distorted": 1, "accurate": 2, "unverifiable": 3}
    checks = sorted(checks, key=lambda c: order.get(c["verdict"], 4))
    counts = {}
    for c in checks:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    wrong = counts.get("fabricated", 0) + counts.get("distorted", 0)
    summary = ", ".join(f"{counts[k]} {VERIFY_LABEL[k]}" for k in ["accurate", "distorted", "fabricated", "unverifiable"] if counts.get(k))
    lines = [
        "## Fact check: is what AI says about you true",
        "",
        f"Every number and specific claim AI stated about {audit['brand']}, graded against the "
        f"facts the brand provided. {summary}.",
        "",
    ]
    if wrong:
        lines += [
            f"**{wrong} claim(s) AI repeats to buyers are wrong.** A confidently false number in "
            "circulation is more urgent than a missing one: it is actively costing or misleading "
            "deals, and correcting the public record is the fix.", "",
        ]
    lines += ["| Verdict | AI's claim | Checked against | Note |", "|---|---|---|---|"]
    for c in checks:
        lines.append(
            f"| {VERIFY_LABEL[c['verdict']]} | {c['ai_claim']} | {c['matched_fact'] or 'no matching fact'} | {c['note']} |"
        )
    lines.append("")
    return lines


def paraphrase_report(audit: dict) -> list:
    probes = audit.get("paraphrase_probes") or []
    if not probes:
        return []
    lines = [
        "## Paraphrase sensitivity and belief stability",
        "",
        "The same buyer intent, reworded. Only the opening wording changes, so any difference in "
        "which vendors appear is caused by phrasing alone.",
        "",
        "| Scenario | Assistant | Wordings | Brand appeared | Vendor-set overlap |",
        "|---|---|---|---|---|",
    ]
    for p in probes:
        ov = "n/a" if p.get("mean_overlap") is None else f"{round(100 * p['mean_overlap'])}%"
        lines.append(
            f"| {p['scenario']} | {p['assistant']} | {p['variant_count']} "
            f"| {p['brand_appearance_rate']} ({p['brand_appearance_pct']}%) | {ov} |"
        )
    lines += [
        "",
        "Vendor-set overlap is the mean pairwise similarity of shortlists across wordings. High "
        "overlap means the model holds a stable view of the category. Low overlap means shortlists "
        "are an artifact of phrasing, and any single-prompt visibility metric is measuring noise.",
        "",
    ]

    stable = [(p, c) for p in probes for c in p.get("claims", []) if c["variants_appeared_in"] > 1]
    noise = [(p, c) for p in probes for c in p.get("claims", []) if c["variants_appeared_in"] == 1]
    if stable:
        lines += [
            "### Stable beliefs", "",
            "Claims that survived rewording. This is what the model actually believes, and what "
            "content strategy should target.", "",
            "| Claim | Appeared in |", "|---|---|",
        ] + [
            f"| {c['claim']} | {c['variants_appeared_in']}/{p['variant_count']} wordings |"
            for p, c in sorted(stable, key=lambda x: -x[1]["variants_appeared_in"])
        ] + [""]
    if noise:
        lines += [
            f"{len(noise)} claim(s) appeared in only one wording. Treat as noise, not belief: a "
            "single-prompt audit would have reported them as findings.", "",
        ]
    return lines


def personas_for(config: dict) -> list:
    """The primary ICP, plus any variants worth sweeping, each labelled."""
    out = [dict(config["icp"], _label=config["icp"]["role"])]
    for v in config.get("icp_variants") or []:
        role = str(v.get("role", ""))
        if role and not role.startswith("e.g."):
            out.append(dict(v, _label=role))
    return out


def run_cell(provider, client, cfg, scenario, framing, persona_label):
    """One session. Returns the session record, or None if it failed."""
    messages, pathway, unprompted, retrieved = conduct_session(
        provider, client, cfg, scenario, framing
    )
    transcript = transcript_text(messages)
    data = extract_session(client, transcript, cfg["brand"], cfg["category"])
    return {
        "scenario": scenario["id"],
        "persona": persona_label,
        "framing": framing,
        "assistant": provider.name,
        "assistant_model": provider.model,
        "retrieval_enabled": getattr(provider, "retrieval", False),
        "retrieved_sources": retrieved,
        "pathway": pathway,
        "unprompted_vendors_stage1": unprompted,
        "presence": compute_presence(
            transcript, cfg["brand"], cfg.get("competitors", [])
        ),
        "transcript": transcript,
        **data,
    }


def run_audit(config: dict, providers: list, paraphrase: int = 0) -> dict:
    client = anthropic.Anthropic()
    sessions, failed = [], []
    personas = personas_for(config)

    for persona in personas:
        cfg = dict(config, icp=persona)
        for scenario in cfg["scenarios"]:
            for framing in scenario.get("framings") or ["operational"]:
                for provider in providers:
                    label = (
                        f"{scenario['id']} [{framing}] x {provider.name}"
                        + (f" ({persona['_label']})" if len(personas) > 1 else "")
                    )
                    print(f"  session: {label} ...", file=sys.stderr)
                    try:
                        sessions.append(
                            run_cell(provider, client, cfg, scenario, framing, persona["_label"])
                        )
                    except Exception as e:
                        print(f"    FAILED ({e}); continuing with remaining sessions", file=sys.stderr)
                        failed.append({
                            "scenario": scenario["id"], "framing": framing,
                            "persona": persona["_label"], "assistant": provider.name,
                            "error": str(e),
                        })

    if not sessions:
        sys.exit("Every session failed; nothing to analyze.")

    probes = []
    if paraphrase:
        for scenario in config["scenarios"]:
            for provider in providers:
                print(f"  paraphrase probe: {scenario['id']} x {provider.name} "
                      f"({paraphrase} wordings) ...", file=sys.stderr)
                try:
                    p = run_paraphrase_probe(provider, client, config, scenario, paraphrase)
                    if p:
                        probes.append(p)
                except Exception as e:
                    print(f"    FAILED ({e})", file=sys.stderr)

    audit = {
        **{k: config[k] for k in ["brand", "category", "icp", "competitors", "scenarios"]},
        "positioning": [
            p for p in (config.get("positioning") or [])
            if not str(p).startswith(("optional", "e.g."))
        ],
        "personas_run": [p["_label"] for p in personas],
        "date": date.today().isoformat(),
        "sessions": sessions,
        "failed_sessions": failed,
        "paraphrase_probes": probes,
    }
    if config.get("verified_facts"):
        print("  fact-checking AI claims against provided facts ...", file=sys.stderr)
        audit["fact_checks"] = verify_claims(client, audit, config["verified_facts"])
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


def behavior_marks(brand: str, s: dict) -> tuple:
    """Compress one session into three AI-behavior verdicts.

    CATEGORY       does AI route this pain to the category at all?
    VISIBILITY     does the brand surface, and how prominently?
    RECOMMENDATION does AI endorse it, hedge, or send the buyer elsewhere?
    """
    category = "PASS" if s["category_proposed"] else "FAIL"

    shortlisted = any(brand.lower() in v.lower() for v in s["shortlist"])
    if s["unprompted_brand_mention"] and shortlisted:
        visibility = "PASS"
    elif shortlisted or s["unprompted_brand_mention"]:
        visibility = "MIXED"
    else:
        visibility = "FAIL"

    won = s["final_call"] == "target_brand"
    if s["brand_recommendation"] == "strong" and won:
        rec = "PASS"
    elif s["brand_recommendation"] in ("negative",) or s["final_call"] == "competitor":
        rec = "FAIL"
    else:
        rec = "MIXED"
    return category, visibility, rec


MARK = {"PASS": "PASS", "MIXED": "MIXED", "FAIL": "FAIL"}


def scorecard(audit: dict) -> list:
    """Three-behavior scorecard, one row per session. The five-second read."""
    brand = audit["brand"]
    multi_persona = len({s.get("persona") for s in audit["sessions"]}) > 1
    lines = [
        "## AI behavior scorecard",
        "",
        "Three questions per session: does AI route the problem to the category, "
        "does the brand surface inside it, and does AI actually endorse it under pressure.",
        "",
        *( ["| Scenario | Framing | Persona | Assistant | Category | Visibility | Recommendation |",
            "|---|---|---|---|---|---|---|"]
           if multi_persona else
           ["| Scenario | Framing | Assistant | Category | Visibility | Recommendation |",
            "|---|---|---|---|---|---|"] ),
    ]
    for s in audit["sessions"]:
        c, v, r = behavior_marks(brand, s)
        persona_cell = f"| {s.get('persona', '')} " if multi_persona else ""
        lines.append(
            f"| {s['scenario']} | {s.get('framing', 'operational')} {persona_cell}| {s['assistant']} "
            f"| {MARK[c]} | {MARK[v]} | {MARK[r]} |"
        )
    lines += ["", "PASS = works today. MIXED = surfaces but hedged. FAIL = the brand or category does not make it.", ""]
    return lines


def evidence_graph(audit: dict) -> list:
    """What every belief rests on, and who owns that source."""
    sessions = audit["sessions"]
    chains = [(s, e) for s in sessions for e in (s.get("evidence_chain") or [])]
    if not chains:
        return []

    counts = {}
    for _, e in chains:
        counts[e["provenance"]] = counts.get(e["provenance"], 0) + 1
    total = len(chains)
    flagged = sum(1 for _, e in chains if e["assistant_flagged_weakness"])

    lines = [
        "## Evidence graph: what the beliefs rest on",
        "",
        f"{total} claims traced across {len(sessions)} session(s). "
        f"{flagged} were caveated by the assistant itself as self-reported, unverified, or stale.",
        "",
        "| Provenance | Claims | Share |",
        "|---|---|---|",
    ]
    labels = {
        "first_party": "The brand's own content",
        "third_party": "Independent sources",
        "training_memory": "Training memory, nothing read",
        "unstated": "No basis given",
    }
    for key, label in labels.items():
        n = counts.get(key, 0)
        if n:
            lines.append(f"| {label} | {n} | {round(100 * n / total)}% |")

    lines += ["", "### Claim by claim", "", "| Claim | Rests on | Provenance | Assistant flagged it |", "|---|---|---|---|"]
    for s, e in chains:
        flag = "yes" if e["assistant_flagged_weakness"] else ""
        lines.append(
            f"| {e['claim']} | {e['source']} | {e['provenance'].replace('_', ' ')} | {flag} |"
        )

    quantified = sorted({q for s in sessions for q in (s.get("quantified_claims") or [])})
    if quantified:
        lines += [
            "", "### Numbers AI repeats about the brand", "",
            "These are memorized and doing work in the conversation. They are also the claims a competitor would need to counter.", "",
        ] + [f"- {q}" for q in quantified]

    counter = [(s, c) for s in sessions for c in (s.get("competitor_counter_evidence") or [])]
    if counter:
        lines += [
            "", "### Competitor assets used as counter-proof", "",
            "| Competitor | Asset AI reached for | Criterion it won |", "|---|---|---|",
        ] + [
            f"| {c['competitor']} | {c['asset']} | {c['criterion']} |" for _, c in counter
        ]

    depths = [s.get("citation_depth") for s in sessions if s.get("citation_depth") not in (None, "not_applicable")]
    if depths:
        deep = depths.count("deep_pages")
        lines += [
            "", "### Citation depth", "",
            f"{deep}/{len(depths)} session(s) cited specific product or use-case pages rather than the homepage alone. "
            "Deep-page citation means AI understands the product; homepage-only means it knows the brand exists.", "",
        ]
    lines.append("")
    return lines


STAGE_OF_TURN = ["problem", "problem", "vendors", "vendors", "brand", "brand", "pressure", "pressure"]


def compute_presence(transcript: str, brand: str, competitors: list) -> dict:
    """Scan a completed transcript for where the brand is present per turn.

    Deterministic local measurement, run once after a session completes. The
    signal that matters is the unprompted stages (problem, vendors): a brand
    named early that disappears once the conversation narrows to specific
    criteria is losing ground mid-conversation, which endpoint metrics miss.
    """
    brand = brand.lower()
    turns = [
        block.split("\n", 1)[1] if "\n" in block else ""
        for block in (transcript or "").split("[ASSISTANT]")[1:]
    ]
    turns = [t.split("[USER]")[0].lower() for t in turns]
    if not turns:
        return {}

    marks = ["Y" if brand in t else "-" for t in turns]
    rivals = [sum(1 for c in competitors if c.lower() in t) for t in turns]

    narrowing = None
    for i in (0, 2):  # problem stage, vendor stage
        if i + 1 < len(marks) and marks[i] == "Y" and marks[i + 1] == "-" and rivals[i + 1] > 0:
            narrowing = STAGE_OF_TURN[i]
            break

    return {
        "marks": marks,
        "rivals": rivals,
        "first_turn": next((i + 1 for i, m in enumerate(marks) if m == "Y"), None),
        "narrowing_stage": narrowing,
    }


def presence_trace(audit: dict) -> list:
    """Render the presence data captured at run time.

    Falls back to scanning the stored transcript for reports generated before
    presence was computed and stored.
    """
    rows, any_narrowing = [], False
    for s in audit["sessions"]:
        p = s.get("presence") or compute_presence(
            s.get("transcript", ""), audit["brand"], audit.get("competitors", [])
        )
        if not p:
            continue
        if p.get("narrowing_stage"):
            any_narrowing = True
        rows.append({
            "label": f"{s['scenario']} [{s.get('framing', 'operational')}] x {s['assistant']}",
            "marks": p["marks"],
            "rivals": p["rivals"],
            "first": p.get("first_turn"),
            "narrowing": p.get("narrowing_stage"),
        })

    if not rows:
        return []

    width = max(len(r["marks"]) for r in rows)
    header = " | ".join(f"T{i + 1}" for i in range(width))
    lines = [
        "## Where the brand falls out of the conversation",
        "",
        "Presence of the brand in each assistant turn, measured from the transcript. "
        "Turns 1 to 4 are unprompted: the buyer has not named the brand yet. "
        "Y = named, - = absent. The rivals row counts how many known competitors appear in that turn.",
        "",
        f"| Session | {header} | First appears | Narrowing |",
        "|---" * (width + 3) + "|",
    ]
    for r in rows:
        marks = r["marks"] + ["-"] * (width - len(r["marks"]))
        rivals = r["rivals"] + [0] * (width - len(r["rivals"]))
        cells = " | ".join(
            f"{m}" + (f" ({rv})" if rv else "") for m, rv in zip(marks, rivals)
        )
        first = f"turn {r['first']}" if r["first"] else "never unprompted"
        narrow = f"drops in {r['narrowing']} stage" if r["narrowing"] else ""
        lines.append(f"| {r['label']} | {cells} | {first} | {narrow} |")

    lines.append("")
    if any_narrowing:
        lines.append(
            "At least one session shows narrowing: the brand is named early, then drops out "
            "while competitors stay in the answer as the buyer presses on specifics. That is a "
            "mid-conversation loss, invisible to any metric that only looks at the first answer "
            "or the final call."
        )
    else:
        lines.append(
            "No narrowing detected: where the brand enters the conversation, it stays in it."
        )
    lines.append("")
    return lines


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
        *scorecard(audit),
        "## The funnel",
        "",
        "| Stage | Result |",
        "|---|---|",
    ]
    lines += [f"| {label} | {count}/{total} |" for label, count, total in stages]
    lines += ["", *journey_map(audit), *presence_trace(audit), *paraphrase_report(audit), *evidence_graph(audit), *verification_report(audit), "## Session summaries", ""]

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
    text = "\n".join(lines)
    # Model-generated content (synthesis, extracted fields) may use em dashes
    # even though our own copy never does; normalize on the way out.
    text = re.sub(r"\s*—\s*", ", ", text).replace("–", "-")
    with open(out_path, "w") as f:
        f.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a B2B AI brand perception audit.")
    parser.add_argument("config", nargs="?", help="Path to the audit config JSON (see --init)")
    parser.add_argument("--init", action="store_true", help="Write audit-config.json template and exit")
    parser.add_argument("--models", default=None, help="Comma-separated subset of: claude,chatgpt,gemini (default: all with keys)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--paraphrase", type=int, default=0, metavar="N",
                        help="Also probe paraphrase sensitivity: reword each scenario N ways and measure how much the vendor shortlist moves on wording alone (try 5)")
    parser.add_argument("--review-config", action="store_true",
                        help="Critique the config inputs and exit, without running an audit")
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

    if args.review_config:
        print("\nReviewing config inputs ...", file=sys.stderr)
        r = review_config(anthropic.Anthropic(), config)
        order = {"blocker": 0, "weakens_results": 1, "polish": 2}
        print(f"\nReadiness: {r['readiness'].replace('_', ' ')}\n{r['summary']}\n")
        for f in sorted(r["findings"], key=lambda x: order.get(x["severity"], 3)):
            print(f"[{f['severity'].replace('_', ' ').upper()}] {f['field']}")
            print(f"  problem: {f['problem']}")
            print(f"  fix:     {f['fix']}\n")
        return

    requested = [m.strip() for m in args.models.split(",")] if args.models else None
    providers, skipped = active_providers(requested, retrieval=args.retrieval)
    if not providers:
        sys.exit("No probe models available. Set ANTHROPIC_API_KEY at minimum.")

    preflight(providers, skipped, config, args.paraphrase)
    if args.preflight:
        return
    if not args.yes and sys.stdin.isatty():
        providers = confirm_selection(providers)

    audit = run_audit(config, providers, paraphrase=args.paraphrase)

    out_path = args.out or f"report-{config['brand'].lower().replace(' ', '-')}-{audit['date']}.md"
    write_report(audit, out_path)

    raw_path = out_path.replace(".md", ".json")
    with open(raw_path, "w") as f:
        json.dump(audit, f, indent=2)
    print(f"\nReport: {out_path}\nRaw data (incl. transcripts): {raw_path}")


if __name__ == "__main__":
    main()
