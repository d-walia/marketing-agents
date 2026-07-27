#!/usr/bin/env python3
"""Measure share of voice across a tracked keyword set.

Presence alone is a weak metric — ranking #1 is worth roughly ten times
ranking #9. So share of voice here is *position-weighted*: each ranking is
worth its expected click share, and a domain's share is its slice of the
total attention available across the tracked set.

Also records SERP features (AI overview, featured snippet, People Also Ask),
because a #1 ranking under an AI overview no longer means what it used to.

Two providers, auto-detected from whichever key is present:

  SearchAPI.io   SEARCHAPI_KEY   100 searches free (one-time), then paid
                 https://www.searchapi.io/
  SerpApi        SERPAPI_KEY     250 searches/month, recurring free
                 https://serpapi.com/manage-api-key

Store the key in ~/.marketing-agents.env. Their response shapes are close
enough that both normalize to the same internal structure.

Usage:
    python3 fetch_serp.py --config ../config/site.json --out ../runs/latest
    python3 fetch_serp.py --keywords "ai scribe" "clinical documentation" --domain example.com
    python3 fetch_serp.py --config ../config/site.json --dry-run   # cost check, no calls
    python3 fetch_serp.py --config ../config/site.json --provider serpapi

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ENV_FILE = Path.home() / ".marketing-agents.env"
UA = "seo-performance-monitor/1.0 (+marketing-agents)"

PROVIDERS = {
    "searchapi": {
        "env": "SEARCHAPI_KEY",
        "endpoint": "https://www.searchapi.io/api/v1/search",
        "key_url": "https://www.searchapi.io/",
        "free_tier": "100 searches free (one-time)",
    },
    "serpapi": {
        "env": "SERPAPI_KEY",
        "endpoint": "https://serpapi.com/search.json",
        "key_url": "https://serpapi.com/manage-api-key",
        "free_tier": "250 searches/month (recurring)",
    },
}

# Position → expected click share. Used to weight visibility, so that
# outranking someone counts more than merely appearing alongside them.
CTR_WEIGHT = {
    1: 0.280, 2: 0.150, 3: 0.110, 4: 0.080, 5: 0.060,
    6: 0.045, 7: 0.035, 8: 0.030, 9: 0.026, 10: 0.024,
}


def read_env(var: str) -> str | None:
    import os

    key = os.environ.get(var)
    if key:
        return key.strip()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export "):]
            if line.startswith(var + "="):
                val = line.partition("=")[2].strip().strip('"').strip("'")
                return val or None
    return None


def resolve_provider(preferred: str | None) -> tuple[str, str]:
    """Pick a provider from whichever key exists. Returns (name, key)."""
    if preferred:
        spec = PROVIDERS[preferred]
        key = read_env(spec["env"])
        if not key:
            sys.exit(
                f"error: --provider {preferred} needs {spec['env']} in {ENV_FILE}.\n"
                f"Get a key at {spec['key_url']} ({spec['free_tier']})."
            )
        return preferred, key

    for name, spec in PROVIDERS.items():
        key = read_env(spec["env"])
        if key:
            return name, key

    wanted = "\n".join(
        f"  {s['env']:15} {n:10} {s['free_tier']} — {s['key_url']}"
        for n, s in PROVIDERS.items()
    )
    sys.exit(
        "error: no SERP provider key found. Add one to "
        f"{ENV_FILE}:\n{wanted}\n"
        "Meanwhile, expand_keywords.py and analyze_gsc.py need no key at all."
    )


def root_domain(url_or_host: str) -> str:
    """Normalize to a comparable registrable-ish domain."""
    s = (url_or_host or "").strip().lower()
    if "//" in s:
        s = urllib.parse.urlparse(s).netloc or s
    s = s.split("/")[0].split("?")[0]
    if s.startswith("www."):
        s = s[4:]
    return s


def search(query: str, provider: str, key: str, location: str | None,
           timeout: float = 30.0) -> dict:
    """Both providers accept the same core parameters; only the host differs."""
    spec = PROVIDERS[provider]
    params = {
        "engine": "google",
        "q": query,
        "api_key": key,
        "num": 10,
        "hl": "en",
        "gl": "us",
    }
    if location:
        params["location"] = location
    req = urllib.request.Request(
        f"{spec['endpoint']}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        if e.code in (401, 403):
            sys.exit(
                f"error: {provider} rejected the key ({e.code}). "
                f"Check {spec['env']} in {ENV_FILE}.\n{body}"
            )
        if e.code == 429:
            sys.exit(
                f"error: {provider} quota exhausted or rate-limited (429). "
                f"Free tier is {spec['free_tier']}.\n{body}"
            )
        return {"_error": f"HTTP {e.code}: {body}", "organic_results": []}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"_error": f"network: {e}", "organic_results": []}


def parse_serp(data: dict) -> dict:
    organic = []
    for r in data.get("organic_results", []) or []:
        pos = r.get("position")
        link = r.get("link") or ""
        if not pos or not link:
            continue
        organic.append(
            {
                "position": int(pos),
                # SearchAPI.io returns `domain` directly; SerpApi doesn't.
                "domain": root_domain(r.get("domain") or link),
                "url": link,
                "title": r.get("title", ""),
            }
        )
    features = []
    if data.get("ai_overview"):
        features.append("ai_overview")
    if data.get("answer_box"):
        features.append("featured_snippet")
    if data.get("related_questions"):
        features.append("people_also_ask")
    if data.get("shopping_results"):
        features.append("shopping")
    if data.get("local_results"):
        features.append("local_pack")
    if data.get("video_results") or data.get("inline_videos"):
        features.append("video")

    paa = [q.get("question", "") for q in (data.get("related_questions") or []) if q.get("question")]
    related = [r.get("query", "") for r in (data.get("related_searches") or []) if r.get("query")]

    return {
        "organic": organic,
        "features": features,
        "people_also_ask": paa,
        "related_searches": related,
        "error": data.get("_error"),
    }


def score(results: dict, domain: str, competitors: list[str]) -> dict:
    """Position-weighted share of voice across the tracked keyword set."""
    tracked = [root_domain(d) for d in ([domain] if domain else []) + competitors]
    weights: dict[str, float] = {d: 0.0 for d in tracked}
    presence: dict[str, int] = {d: 0 for d in tracked}
    all_domains: dict[str, float] = {}
    positions: dict[str, list] = {d: [] for d in tracked}

    answered = [(kw, r) for kw, r in results.items() if r["organic"]]

    for kw, r in answered:
        seen_this_kw = set()
        for item in r["organic"]:
            w = CTR_WEIGHT.get(item["position"], 0.01)
            d = item["domain"]
            all_domains[d] = all_domains.get(d, 0.0) + w
            # Credit a domain once per keyword, at its best position.
            if d in weights and d not in seen_this_kw:
                weights[d] += w
                presence[d] += 1
                positions[d].append({"keyword": kw, "position": item["position"], "url": item["url"]})
                seen_this_kw.add(d)

    total_weight = sum(all_domains.values()) or 1.0
    n = len(answered) or 1

    sov = {
        d: {
            "share_of_voice": round(weights[d] / total_weight, 4),
            "presence_rate": round(presence[d] / n, 4),
            "keywords_ranked": presence[d],
            "keywords_tracked": n,
            "avg_position": round(
                sum(p["position"] for p in positions[d]) / len(positions[d]), 1
            ) if positions[d] else None,
            "rankings": sorted(positions[d], key=lambda p: p["position"]),
        }
        for d in tracked
    }

    leaders = sorted(all_domains.items(), key=lambda kv: -kv[1])[:15]
    return {
        "by_domain": sov,
        "serp_leaders": [
            {"domain": d, "share_of_voice": round(w / total_weight, 4)} for d, w in leaders
        ],
        "keywords_answered": n,
    }


def render(payload: dict) -> str:
    site = payload["domain"]
    s = payload["scores"]
    mine = s["by_domain"].get(root_domain(site), {}) if site else {}

    L = [
        f"# Share of voice — {site or 'tracked set'}",
        "",
        f"- **Generated:** {payload['generated']}",
        f"- **Keywords tracked:** {s['keywords_answered']}",
        f"- **Source:** Google via {payload.get('provider', 'SERP API')}, top 10 organic",
        "",
    ]
    if mine:
        L += [
            f"**{site}** holds **{mine['share_of_voice'] * 100:.1f}%** position-weighted share "
            f"of voice, appearing in **{mine['keywords_ranked']}/{mine['keywords_tracked']}** "
            f"tracked SERPs"
            + (f" at an average position of {mine['avg_position']}." if mine["avg_position"] else "."),
            "",
        ]

    L += ["## Share of voice — you vs tracked competitors", "",
          "| Domain | Share of voice | Appears in | Avg position |", "|---|---|---|---|"]
    ordered = sorted(s["by_domain"].items(), key=lambda kv: -kv[1]["share_of_voice"])
    for d, v in ordered:
        mark = " ← you" if site and root_domain(d) == root_domain(site) else ""
        pos = v["avg_position"] if v["avg_position"] else "—"
        L.append(
            f"| {d}{mark} | {v['share_of_voice'] * 100:.1f}% "
            f"| {v['keywords_ranked']}/{v['keywords_tracked']} | {pos} |"
        )
    L.append("")

    L += ["## Who actually owns these SERPs", "",
          "Everyone ranking across the tracked set, including domains you are not tracking. "
          "Names you don't recognize here are the competitors you didn't know you had.",
          "", "| Domain | Share of voice |", "|---|---|"]
    for r in payload["scores"]["serp_leaders"]:
        mark = " ← you" if site and r["domain"] == root_domain(site) else ""
        L.append(f"| {r['domain']}{mark} | {r['share_of_voice'] * 100:.1f}% |")
    L.append("")

    feat = payload.get("feature_counts", {})
    if feat:
        L += ["## SERP features", "",
              "Where these appear, organic clicks get suppressed — an AI overview or "
              "featured snippet can absorb the answer before anyone scrolls.",
              "", "| Feature | Keywords |", "|---|---|"]
        for f, c in sorted(feat.items(), key=lambda kv: -kv[1]):
            L.append(f"| {f.replace('_', ' ')} | {c} |")
        L.append("")

    paa = payload.get("all_paa", [])
    if paa:
        L += ["## People Also Ask — content prompts straight from the SERP", ""]
        for q in paa[:25]:
            L.append(f"- {q}")
        L.append("")

    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Share of voice via SerpApi.")
    ap.add_argument("--config", type=Path, help="site.json")
    ap.add_argument("--keywords", nargs="+", help="override tracked keywords")
    ap.add_argument("--domain", help="your domain")
    ap.add_argument("--competitors", nargs="+", default=[])
    ap.add_argument("--location", help='e.g. "United States"')
    ap.add_argument("--out", type=Path, default=Path("serp-run"))
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true", help="show call count, make none")
    ap.add_argument("--provider", choices=sorted(PROVIDERS),
                    help="force a provider; default is whichever key exists")
    args = ap.parse_args()

    keywords, domain, competitors, location = args.keywords or [], args.domain, args.competitors, args.location
    if args.config:
        cfg = json.loads(args.config.read_text())
        keywords = keywords or cfg.get("tracked_keywords", [])
        domain = domain or cfg.get("domain")
        competitors = competitors or cfg.get("competitors", [])
        location = location or cfg.get("location")

    if not keywords:
        sys.exit("error: no keywords. Use --keywords or set tracked_keywords in site.json.")

    if args.dry_run:
        detected = None
        for name, spec in PROVIDERS.items():
            if read_env(spec["env"]):
                detected = name
                break
        print(f"Would run {len(keywords)} searches (1 credit each).")
        if detected:
            print(f"Provider: {detected} — {PROVIDERS[detected]['free_tier']}")
        else:
            print("No provider key found yet; this would fail.")
        for k in keywords:
            print(f"  - {k}")
        return

    provider, key = resolve_provider(args.provider)
    spec = PROVIDERS[provider]

    print(f"Querying {len(keywords)} keywords via {provider} "
          f"({spec['free_tier']})…", file=sys.stderr)
    results, errors = {}, []
    for i, kw in enumerate(keywords, 1):
        parsed = parse_serp(search(kw, provider, key, location))
        results[kw] = parsed
        if parsed["error"]:
            errors.append((kw, parsed["error"]))
        print(f"  [{i}/{len(keywords)}] {kw}"
              + (f"  ⚠ {parsed['error'][:40]}" if parsed["error"] else
                 f"  {len(parsed['organic'])} results"), file=sys.stderr)
        if i < len(keywords):
            time.sleep(args.delay)

    feature_counts: dict[str, int] = {}
    all_paa: list[str] = []
    for r in results.values():
        for f in r["features"]:
            feature_counts[f] = feature_counts.get(f, 0) + 1
        for q in r["people_also_ask"]:
            if q not in all_paa:
                all_paa.append(q)

    payload = {
        "generated": date.today().isoformat(),
        "provider": provider,
        "domain": domain,
        "competitors": competitors,
        "scores": score(results, domain, competitors),
        "feature_counts": feature_counts,
        "all_paa": all_paa,
        "raw": {k: v for k, v in results.items()},
        "errors": errors,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "share-of-voice.json").write_text(json.dumps(payload, indent=2) + "\n")
    (args.out / "share-of-voice.md").write_text(render(payload))

    if errors:
        print(f"\n⚠ {len(errors)} keyword(s) failed — reported as gaps, not silently dropped.",
              file=sys.stderr)
    print(f"Wrote {args.out}/share-of-voice.md", file=sys.stderr)


if __name__ == "__main__":
    main()
