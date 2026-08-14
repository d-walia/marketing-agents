#!/usr/bin/env python3
"""Run the brand-audit query grid across Claude, OpenAI, and Gemini.

All calls route through the Cloudflare AI Gateway (base URLs + CF_AIG_TOKEN
from the environment). Raw responses land in runs/<timestamp>/raw/<provider>/,
one JSON file per query, plus a manifest.json for the downstream agents.

Usage:
  python3 scripts/run_queries.py            # full grid, all providers
  python3 scripts/run_queries.py --smoke    # first query only, capped tokens
  python3 scripts/run_queries.py --providers openai,gemini
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"


def env(name):
    v = os.environ.get(name, "")
    if not v:
        sys.exit(f"Missing env var {name} — source ~/.zshrc first.")
    return v


def gateway_headers():
    return {"cf-aig-authorization": f"Bearer {env('CF_AIG_TOKEN')}"}


def post_json(url, headers, body, timeout=120):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        # Cloudflare's bot protection 403s urllib's default UA (error 1010)
        headers={"content-type": "application/json", "user-agent": "brand-audit/1.0", **headers},
        method="POST",
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp), round(time.time() - started, 2)


def call_anthropic(model, prompt, max_tokens):
    data, latency = post_json(
        f"{env('ANTHROPIC_BASE_URL')}/v1/messages",
        {
            "x-api-key": env("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            **gateway_headers(),
        },
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return text, data.get("usage", {}), latency


def call_openai(model, prompt, max_tokens):
    data, latency = post_json(
        f"{env('OPENAI_BASE_URL')}/chat/completions",
        {"Authorization": f"Bearer {env('OPENAI_API_KEY')}", **gateway_headers()},
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    text = data["choices"][0]["message"]["content"]
    return text, data.get("usage", {}), latency


def call_gemini(model, prompt, max_tokens):
    data, latency = post_json(
        f"{env('GOOGLE_GEMINI_BASE_URL')}/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": env("GEMINI_API_KEY"), **gateway_headers()},
        {
            "contents": [{"parts": [{"text": prompt}]}],
            # Gemini "thinking" models spend output tokens on reasoning before the
            # visible answer — without headroom, responses truncate to fragments
            "generationConfig": {"maxOutputTokens": max_tokens + 1500},
        },
    )
    parts = data["candidates"][0]["content"].get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return text, data.get("usageMetadata", {}), latency


CALLERS = {"anthropic": call_anthropic, "openai": call_openai, "gemini": call_gemini}


def fill_placeholders(text, brand_cfg):
    mapping = {
        "brand": brand_cfg["brand"],
        "category": brand_cfg["category"],
        "category_short": brand_cfg["category_short"],
        "buyer_query_context": brand_cfg["buyer_query_context"],
    }
    for i, comp in enumerate(brand_cfg.get("competitors", [])):
        mapping[f"competitor_{i}"] = comp
    for key, value in mapping.items():
        text = text.replace("{" + key + "}", value)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="first query only, 150-token cap")
    ap.add_argument("--providers", default="anthropic,openai,gemini")
    args = ap.parse_args()

    brand_cfg = json.loads((CONFIG / "brand.json").read_text())
    unfilled = [k for k in ("brand", "category", "category_short", "buyer_query_context")
                if not brand_cfg.get(k, "").strip()]
    if len([c for c in brand_cfg.get("competitors", []) if c.strip()]) < 3:
        unfilled.append("competitors (need 3)")
    if unfilled:
        sys.exit(f"config/brand.json is an unfilled template — fill in: {', '.join(unfilled)}")
    grid = json.loads((CONFIG / "query_grid.json").read_text())["queries"]
    providers = [p.strip() for p in args.providers.split(",") if p.strip() in CALLERS]

    if args.smoke:
        grid = grid[:1]
    max_tokens = 150 if args.smoke else brand_cfg.get("max_tokens", 700)

    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = ROOT / "runs" / run_id
    results, failures = [], []

    for provider in providers:
        model = brand_cfg["models"][provider]
        out_dir = run_dir / "raw" / provider
        out_dir.mkdir(parents=True, exist_ok=True)
        for q in grid:
            prompt = fill_placeholders(q["text"], brand_cfg)
            record = {
                "query_id": q["id"],
                "query_type": q["type"],
                "prompt": prompt,
                "provider": provider,
                "model": model,
            }
            try:
                text, usage, latency = CALLERS[provider](model, prompt, max_tokens)
                record.update({"response": text, "usage": usage, "latency_s": latency})
                print(f"  ok  {provider}/{q['id']}  ({latency}s)")
            except urllib.error.HTTPError as e:
                record["error"] = f"HTTP {e.code}: {e.read().decode()[:300]}"
                failures.append(f"{provider}/{q['id']}")
                print(f"  FAIL {provider}/{q['id']}  {record['error'][:80]}")
            except Exception as e:  # noqa: BLE001 — record and continue the grid
                record["error"] = str(e)[:300]
                failures.append(f"{provider}/{q['id']}")
                print(f"  FAIL {provider}/{q['id']}  {record['error'][:80]}")
            (out_dir / f"{q['id']}.json").write_text(json.dumps(record, indent=2))
            results.append(record)

    manifest = {
        "run_id": run_id,
        "brand": brand_cfg["brand"],
        "smoke": args.smoke,
        "providers": {p: brand_cfg["models"][p] for p in providers},
        "queries": len(grid),
        "calls_ok": len(results) - len(failures),
        "calls_failed": failures,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nRun {run_id}: {manifest['calls_ok']} ok, {len(failures)} failed")
    print(f"Outputs: {run_dir}")
    if failures and len(failures) == len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
