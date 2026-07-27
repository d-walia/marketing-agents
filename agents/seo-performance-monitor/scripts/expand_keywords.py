#!/usr/bin/env python3
"""Expand seed topics into real search demand using Google Suggest.

Google Suggest is the free autocomplete feed behind the search box. Every
suggestion it returns is a phrase real people actually type — no keyword-tool
subscription required. This script runs the "alphabet soup" technique (append
a-z, 0-9, and question/commercial modifiers to each seed), then buckets results
by *audience first* and intent second: job-seeker and off-market queries are
separated out, because high volume read by the wrong audience is worth nothing.

Usage:
    python3 expand_keywords.py --seeds "product marketing agency" "GTM consultant"
    python3 expand_keywords.py --config ../config/site.json --out ../runs/keywords
    python3 expand_keywords.py --seeds "ambient AI scribe" --depth 2

No API key. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
# Cloudflare-style bot filters 403 urllib's default UA; always send our own.
UA = "seo-performance-monitor/1.0 (+marketing-agents)"

QUESTION_MODIFIERS = [
    "how", "what", "why", "when", "where", "who", "which",
    "can", "does", "is", "are", "should", "do",
]
COMMERCIAL_MODIFIERS = [
    "best", "top", "vs", "versus", "alternative", "alternatives",
    "review", "reviews", "compare", "comparison",
]
# Category nouns. Great at *provoking* suggestions, useless for classifying
# intent — "what is a marketing agency" is a definition question, not a purchase.
CATEGORY_MODIFIERS = [
    "software", "tool", "tools", "platform", "vendor", "companies",
    "agency", "consultant", "services",
]

# Classification signals, checked in this order. Only genuine buying language
# counts as transactional; category nouns are deliberately absent.
BUYING_SIGNALS = [
    "pricing", "price", "cost", "costs", "hire", "hiring", "buy", "demo",
    "quote", "trial", "rates", "rate", "fees", "cheap", "affordable", "budget",
    "near me", "for hire", "freelance",
]
COMMERCIAL_SIGNALS = COMMERCIAL_MODIFIERS + [
    "example", "examples", "template", "templates", "case study", "case studies",
]
# Job-seeker queries. High volume, wrong audience for anyone selling a service —
# bucketed separately rather than silently dropped, because a deliberate
# recruiting or authority play may well want them.
CAREER_SIGNALS = [
    "salary", "salaries", "jobs", "job", "career", "careers", "resume", "cv",
    "interview", "interviews", "course", "courses", "certification", "certificate",
    "training", "degree", "internship", "intern", "bootcamp", "become",
    "qualifications", "apprenticeship", "full form", "abbreviation",
]
# Markets outside a US/English B2B focus. Suggest is global, so these arrive
# unbidden and skew the picture. Reported in their own bucket, never silently dropped.
OFFMARKET_SIGNALS = [
    "india", "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
    "pune", "kolkata", "pakistan", "karachi", "lahore", "nigeria", "lagos",
    "kenya", "nairobi", "philippines", "manila", "dubai", "uae", "bangladesh",
    "indonesia", "jakarta", "vietnam", "sri lanka", "nepal",
]


def suggest(query: str, timeout: float = 8.0) -> list[str]:
    """One Google Suggest call. Returns [] on any failure — never raises."""
    params = urllib.parse.urlencode({"client": "firefox", "hl": "en", "q": query})
    req = urllib.request.Request(
        f"{SUGGEST_URL}?{params}", headers={"User-Agent": UA}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        # Response shape: ["<query>", ["suggestion", ...], ...]
        return [s for s in data[1] if isinstance(s, str)] if len(data) > 1 else []
    except (urllib.error.URLError, json.JSONDecodeError, IndexError, TimeoutError):
        return []


def build_probes(seed: str, depth: int) -> list[str]:
    """The probe set for one seed: bare, modifier-prefixed, and alphabet soup."""
    probes = [seed]
    probes += [f"{m} {seed}" for m in QUESTION_MODIFIERS]
    probes += [f"{seed} {m}" for m in COMMERCIAL_MODIFIERS + CATEGORY_MODIFIERS]
    probes += [f"{seed} {m}" for m in ("pricing", "cost", "near me")]
    if depth >= 2:
        probes += [f"{seed} {c}" for c in string.ascii_lowercase]
        probes += [f"{seed} {d}" for d in "0123456789"]
    return probes


def matches(phrase: str, signals: list[str]) -> bool:
    """Multi-word signals need substring matching; single words match on token."""
    words = set(phrase.split())
    for s in signals:
        if " " in s:
            if s in phrase:
                return True
        elif s in words:
            return True
    return False


def classify(phrase: str) -> str:
    """Bucket by audience and intent. Career and off-market are audience
    filters, not intents — they come first because a job-seeker query is the
    wrong reader regardless of how commercial its wording looks."""
    p = phrase.lower()
    if matches(p, OFFMARKET_SIGNALS):
        return "offmarket"
    if matches(p, CAREER_SIGNALS):
        return "career"
    if matches(p, BUYING_SIGNALS):
        return "transactional"
    if matches(p, COMMERCIAL_SIGNALS):
        return "commercial"
    return "informational"


def expand(seeds: list[str], depth: int, delay: float, verbose: bool = True) -> dict:
    """Run every probe for every seed. Returns {phrase: [seeds it came from]}."""
    found: dict[str, set[str]] = defaultdict(set)
    probes_run = 0
    empty = 0

    for seed in seeds:
        probes = build_probes(seed, depth)
        if verbose:
            print(f"  {seed!r}: {len(probes)} probes", file=sys.stderr)
        for probe in probes:
            for s in suggest(probe):
                found[s.strip().lower()].add(seed)
            probes_run += 1
            if not found:
                empty += 1
            time.sleep(delay)

    if probes_run and not found:
        sys.exit(
            "error: every Google Suggest probe came back empty.\n"
            "Likely rate-limited or offline. Wait a few minutes, or raise --delay."
        )
    return {"phrases": found, "probes_run": probes_run}


STOPWORDS = {
    "a", "an", "the", "for", "of", "to", "in", "on", "and", "or", "is", "are",
    "do", "does", "can", "what", "how", "why", "when", "where", "who", "which",
    "with", "you", "your", "my", "it", "that", "this", "be", "as", "at", "by",
}


def cluster(phrases: dict[str, set[str]], seeds: list[str]) -> dict:
    """Group by audience/intent, flagging phrases that introduce new vocabulary."""
    by_intent: dict[str, list[dict]] = defaultdict(list)
    seed_words = {w for s in seeds for w in s.lower().split()}

    for phrase, origins in sorted(phrases.items()):
        content = [w for w in phrase.split() if w not in STOPWORDS]
        novel = [w for w in content if w not in seed_words]
        by_intent[classify(phrase)].append(
            {
                "phrase": phrase,
                "from_seeds": sorted(origins),
                "words": len(phrase.split()),
                "novel_words": novel,
                # Two or more content words the seeds never contained means a
                # genuinely adjacent topic, not a reworded seed.
                "is_novel": len(novel) >= 2,
            }
        )
    return by_intent


SECTIONS = [
    ("transactional", "Buying intent", "Closest to revenue — someone pricing or hiring."),
    ("commercial", "Evaluating", "Comparing options. Where a comparison page or case study lands."),
    ("informational", "Researching", "Top of funnel. Authority content, slower payback."),
    ("career", "Career / job-seeker",
     "Real demand, but the reader is looking for a job, not a vendor. "
     "Target deliberately or not at all — never by accident."),
    ("offmarket", "Off-market geography",
     "Google Suggest is global; these skew to markets outside a US/English B2B focus."),
]


def write_outputs(by_intent: dict, seeds: list[str], probes_run: int, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    total = sum(len(v) for v in by_intent.values())
    buyer = len(by_intent.get("transactional", [])) + len(by_intent.get("commercial", []))

    (out / "keywords.json").write_text(
        json.dumps(
            {
                "generated": date.today().isoformat(),
                "source": "Google Suggest (free autocomplete)",
                "seeds": seeds,
                "probes_run": probes_run,
                "total_phrases": total,
                "buyer_intent_phrases": buyer,
                "by_intent": by_intent,
            },
            indent=2,
        )
        + "\n"
    )

    lines = [
        "# Keyword expansion — Google Suggest",
        "",
        f"- **Generated:** {date.today().isoformat()}",
        f"- **Seeds:** {', '.join(seeds)}",
        f"- **Probes run:** {probes_run}  →  **{total} unique phrases**, "
        f"of which **{buyer} carry buyer intent**",
        "",
        "Every phrase below is one Google's autocomplete actually serves, so demand is",
        "demonstrated rather than estimated. Grouped by who is searching and why —",
        "audience first, because a high-volume phrase read by the wrong audience is",
        "worse than no phrase at all.",
        "",
    ]
    for key, title, blurb in SECTIONS:
        rows = by_intent.get(key, [])
        if not rows:
            continue
        lines += [f"## {title} ({len(rows)})", "", f"_{blurb}_", ""]
        rows = sorted(rows, key=lambda r: (not r["is_novel"], r["phrase"]))
        shown = rows if key in ("transactional", "commercial") else rows[:40]
        for r in shown:
            lines.append(f"- {r['phrase']}{' 🆕' if r['is_novel'] else ''}")
        if len(rows) > len(shown):
            lines.append(f"- _…{len(rows) - len(shown)} more in keywords.json_")
        lines.append("")
    lines += [
        "---",
        "",
        "🆕 = introduces two or more content words your seeds didn't contain — the",
        "likeliest place to find an adjacent topic you aren't covering yet.",
        "",
        "**Next step:** cross-reference these against a Search Console export. A phrase",
        "with demand that appears nowhere in your impressions is demand you're invisible",
        "for, which is the highest-value gap this toolchain can find.",
        "",
    ]
    (out / "keywords.md").write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description="Expand seeds via Google Suggest.")
    ap.add_argument("--seeds", nargs="+", help="seed topics")
    ap.add_argument("--config", type=Path, help="site.json with seed_topics")
    ap.add_argument("--out", type=Path, default=Path("keyword-run"))
    ap.add_argument("--depth", type=int, default=1, choices=[1, 2],
                    help="2 adds full a-z/0-9 alphabet soup (slower, wider)")
    ap.add_argument("--delay", type=float, default=0.15,
                    help="seconds between calls; raise if rate-limited")
    args = ap.parse_args()

    seeds = args.seeds or []
    if args.config:
        cfg = json.loads(args.config.read_text())
        seeds = seeds or cfg.get("seed_topics", [])
    if not seeds:
        sys.exit("error: give --seeds or a --config containing seed_topics.")

    print(f"Expanding {len(seeds)} seed(s) via Google Suggest…", file=sys.stderr)
    result = expand(seeds, args.depth, args.delay)
    by_intent = cluster(result["phrases"], seeds)
    write_outputs(by_intent, seeds, result["probes_run"], args.out)

    total = sum(len(v) for v in by_intent.values())
    print(f"\n{total} unique phrases from {result['probes_run']} probes", file=sys.stderr)
    for key, title, _ in SECTIONS:
        if by_intent.get(key):
            print(f"  {title:22} {len(by_intent[key])}", file=sys.stderr)
    buyer = len(by_intent.get("transactional", [])) + len(by_intent.get("commercial", []))
    print(f"  {'→ buyer intent':22} {buyer}", file=sys.stderr)
    print(f"Wrote {args.out}/keywords.json and keywords.md", file=sys.stderr)


if __name__ == "__main__":
    main()
