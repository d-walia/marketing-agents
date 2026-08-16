#!/usr/bin/env python3
"""Deterministic technical + AI-readability checks over a crawl corpus.

Reads a run directory produced by crawl_site.py, writes issues.json.
No LLM, no network — pure arithmetic over pages.jsonl, so re-running is free.
Interpretation and prioritization belong to the analysis subagent.

Usage:
  python3 scripts/check_site.py runs/<domain>/<timestamp>
  python3 scripts/check_site.py            # newest run
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TITLE_MAX = 60
META_MAX = 160
THIN_WORDS = 150
ITEM_CAP = 50  # per check, keep issues.json readable

# JSON-LD types answer engines actually consume for Q&A-shaped extraction
AI_SCHEMA_TYPES = {"FAQPage", "HowTo", "Article", "BlogPosting", "Product", "Organization"}


def newest_run():
    runs = sorted(ROOT.glob("runs/*/*/pages.jsonl"))
    if not runs:
        sys.exit("No runs found — run crawl_site.py first.")
    return runs[-1].parent


def check(severity, items, note=None):
    entry = {"severity": severity, "count": len(items), "items": items[:ITEM_CAP]}
    if len(items) > ITEM_CAP:
        entry["items_truncated"] = True
    if note:
        entry["note"] = note
    return entry


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_run()
    if not run_dir.is_absolute():
        run_dir = (Path.cwd() / run_dir).resolve()
    records = [json.loads(line) for line in (run_dir / "pages.jsonl").read_text().splitlines()]
    summary = json.loads((run_dir / "crawl-summary.json").read_text())
    sitemap_urls = set(json.loads((run_dir / "sitemap-urls.json").read_text()))

    # Index by requested and final URL, so redirect aliases resolve.
    by_url = {}
    for r in records:
        by_url.setdefault(r["url"], r)
        by_url.setdefault(r["final_url"], r)

    # HTML pages that returned 200 and were parsed ("word_count" only exists on those)
    html_ok = [r for r in records if r["status"] == 200 and "word_count" in r]
    start_url = summary["start_url"]

    # Inbound internal links per page (for orphan detection).
    inlinks = {}
    for r in html_ok:
        for target in r.get("internal_links", []):
            rec = by_url.get(target)
            key = rec["url"] if rec else target
            if key != r["url"]:
                inlinks[key] = inlinks.get(key, 0) + 1

    checks = {}

    broken, redirected_links = [], []
    for r in html_ok:
        for target in r.get("internal_links", []):
            rec = by_url.get(target)
            if rec is None:
                continue  # uncrawled (page cap) — unknown, not broken
            if rec["error"]:
                broken.append({"source": r["url"], "target": target, "problem": rec["error"]})
            elif rec["status"] and rec["status"] >= 400:
                broken.append({"source": r["url"], "target": target, "status": rec["status"]})
            elif rec["redirect_chain"] and rec["url"] == target:
                redirected_links.append({"source": r["url"], "target": target,
                                         "resolves_to": rec["final_url"]})
    checks["broken_internal_links"] = check("high", broken)
    checks["redirected_internal_links"] = check(
        "low", redirected_links, "links work but bounce through a redirect — link the final URL")

    checks["redirect_chains"] = check("medium", [
        {"url": r["url"], "hops": len(r["redirect_chain"]), "final": r["final_url"]}
        for r in records if len(r.get("redirect_chain", [])) >= 2])

    checks["error_pages"] = check("high", [
        {"url": r["url"], "status": r["status"], "error": r["error"]}
        for r in records if r["error"] or (r["status"] and r["status"] >= 400)])

    checks["missing_title"] = check("high", [
        {"url": r["url"]} for r in html_ok if not r.get("title")])

    titles = {}
    for r in html_ok:
        if r.get("title"):
            titles.setdefault(r["title"], []).append(r["url"])
    checks["duplicate_titles"] = check("medium", [
        {"title": t, "urls": urls} for t, urls in titles.items() if len(urls) > 1])

    checks["long_titles"] = check("low", [
        {"url": r["url"], "length": len(r["title"]), "title": r["title"]}
        for r in html_ok if r.get("title") and len(r["title"]) > TITLE_MAX],
        f"over {TITLE_MAX} chars — truncates in results")

    checks["missing_meta_description"] = check(
        "medium", [{"url": r["url"]} for r in html_ok if not r.get("meta_description")],
        "descriptions feed snippets and answer-engine summaries")

    metas = {}
    for r in html_ok:
        if r.get("meta_description"):
            metas.setdefault(r["meta_description"], []).append(r["url"])
    checks["duplicate_meta_descriptions"] = check("medium", [
        {"description": m[:120], "urls": urls} for m, urls in metas.items() if len(urls) > 1])

    checks["long_meta_descriptions"] = check("low", [
        {"url": r["url"], "length": len(r["meta_description"])}
        for r in html_ok if r.get("meta_description") and len(r["meta_description"]) > META_MAX])

    checks["missing_h1"] = check("medium", [
        {"url": r["url"]} for r in html_ok if not r.get("h1s")])
    checks["multiple_h1"] = check("low", [
        {"url": r["url"], "h1s": r["h1s"]} for r in html_ok if len(r.get("h1s", [])) > 1])

    checks["thin_content"] = check("medium", [
        {"url": r["url"], "word_count": r["word_count"]}
        for r in html_ok if r["word_count"] < THIN_WORDS],
        f"under {THIN_WORDS} words of server-rendered text — also what AI crawlers "
        "(mostly non-JS-rendering) see; a JS-heavy site shows up here wholesale")

    checks["orphan_pages"] = check("medium", [
        {"url": r["url"], "in_sitemap": r.get("in_sitemap", False)}
        for r in html_ok
        if r["url"] != start_url and r["final_url"] != start_url
        and inlinks.get(r["url"], 0) == 0],
        "no internal links point here — reachable only via sitemap")

    checks["noindex_in_sitemap"] = check("high", [
        {"url": r["url"], "meta_robots": r["meta_robots"]}
        for r in html_ok
        if r.get("meta_robots") and "noindex" in r["meta_robots"] and r["url"] in sitemap_urls],
        "sitemap invites crawlers in, meta robots turns them away — pick one")

    checks["noindex_pages"] = check("info", [
        {"url": r["url"], "meta_robots": r["meta_robots"]}
        for r in html_ok if r.get("meta_robots") and "noindex" in r["meta_robots"]])

    checks["canonical_missing"] = check("low", [
        {"url": r["url"]} for r in html_ok if not r.get("canonical")])
    checks["canonical_mismatch"] = check("medium", [
        {"url": r["url"], "canonical": r["canonical"]}
        for r in html_ok
        if r.get("canonical") and r["canonical"] not in (r["url"], r["final_url"])],
        "page claims a different canonical — deliberate for variants, a bug otherwise")

    checks["images_missing_alt"] = check("low", [
        {"url": r["url"], "missing": r["images_missing_alt"], "total": r["images_total"]}
        for r in html_ok if r.get("images_missing_alt", 0) > 0])

    checks["no_structured_data"] = check("medium", [
        {"url": r["url"]} for r in html_ok if not r.get("jsonld_types")],
        "no JSON-LD — answer engines extract entities and Q&A from structured data")

    # --- site level: can AI models reach and read this site ---
    ai_access = summary.get("ai_bot_access", {})
    blocked = sorted(b for b, v in ai_access.items() if v["verdict"] == "blocked")
    partial = sorted(b for b, v in ai_access.items() if v["verdict"] == "partial")
    schema_present = sorted({t for r in html_ok for t in r.get("jsonld_types", [])})
    pages_with_schema = sum(1 for r in html_ok if r.get("jsonld_types"))
    readability = {
        "ai_bots_blocked": blocked,
        "ai_bots_partial": partial,
        "ai_bots_allowed_count": len(ai_access) - len(blocked) - len(partial),
        "llms_txt": summary.get("llms_txt", {}),
        "sitemap_found": summary.get("sitemap", {}).get("url_count", 0) > 0,
        "schema_types_present": schema_present,
        "ai_schema_types_present": sorted(set(schema_present) & AI_SCHEMA_TYPES),
        "pages_with_structured_data": f"{pages_with_schema}/{len(html_ok)}",
        "meta_description_coverage":
            f"{sum(1 for r in html_ok if r.get('meta_description'))}/{len(html_ok)}",
    }

    issues = {
        "domain": summary["domain"],
        "run_dir": str(run_dir),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pages_checked": len(html_ok),
        "pages_crawled": summary["pages_crawled"],
        "corpus_partial": summary.get("hit_page_cap", False),
        "ai_readability": readability,
        "checks": checks,
    }
    (run_dir / "issues.json").write_text(json.dumps(issues, indent=2))

    print(f"{summary['domain']}: {len(html_ok)} HTML pages checked "
          f"({summary['pages_crawled']} crawled)")
    if issues["corpus_partial"]:
        print("NOTE: crawl hit its page cap — findings are a floor, not a census")
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    for name, c in sorted(checks.items(), key=lambda kv: (order[kv[1]["severity"]], kv[0])):
        if c["count"]:
            print(f"  [{c['severity']:6}] {name}: {c['count']}")
    print(f"AI readability: blocked bots {blocked or 'none'}, "
          f"llms.txt {readability['llms_txt']}, "
          f"schema on {readability['pages_with_structured_data']} pages")
    print(f"Wrote {run_dir / 'issues.json'}")


if __name__ == "__main__":
    main()
