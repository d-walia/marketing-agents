#!/usr/bin/env python3
"""Turn a Google Search Console export into prioritized SEO opportunities.

GSC tells you what happened. It does not tell you what to do about it. This
script does the arithmetic that turns one into the other:

  striking distance   pages ranking 8-20 — the cheapest traffic you can buy
                      with effort, because rank 11 → 8 crosses to page one
  CTR underperformers ranking well but under-clicked for that position, which
                      is a title/meta problem, not a ranking problem
  cannibalization     two of your pages competing for one query, splitting
                      signals so neither wins
  decay               (with a second period) what you are quietly losing

Input is the CSV you download from Search Console — no API, no OAuth. Export
Performance → the table → the download button. Works on any property you or a
client can open, which is the point.

Usage:
    python3 analyze_gsc.py Queries.csv
    python3 analyze_gsc.py current.csv --previous last-quarter.csv
    python3 analyze_gsc.py pages-queries.csv --site example.com --out ../runs/latest

Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

# Share of clicks by organic position — industry-average curve. Used only to
# spot outliers (actual vs expected), never reported as a prediction.
CTR_CURVE = {
    1: 0.280, 2: 0.150, 3: 0.110, 4: 0.080, 5: 0.060,
    6: 0.045, 7: 0.035, 8: 0.030, 9: 0.026, 10: 0.024,
}
PAGE_ONE_TARGET = 3  # the position we price "what if this ranked well" against


def expected_ctr(position: float) -> float:
    p = max(1.0, position)
    if p <= 10:
        lo, hi = int(p), min(int(p) + 1, 10)
        frac = p - lo
        return CTR_CURVE[lo] + (CTR_CURVE[hi] - CTR_CURVE[lo]) * frac
    if p <= 20:
        return 0.010
    return 0.005


def parse_pct(value: str) -> float:
    """GSC writes CTR as '5.26%' in UI exports and 0.0526 via API."""
    if value is None:
        return 0.0
    v = str(value).strip().replace("%", "").replace(",", "")
    if not v:
        return 0.0
    try:
        n = float(v)
    except ValueError:
        return 0.0
    return n / 100 if "%" in str(value) else (n if n <= 1 else n / 100)


def parse_num(value: str) -> float:
    if value is None:
        return 0.0
    v = str(value).strip().replace(",", "").replace("%", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def find_column(headers: list[str], *candidates: str) -> str | None:
    """GSC localizes and renames headers; match loosely on substrings."""
    norm = {h: re.sub(r"[^a-z]", "", h.lower()) for h in headers}
    for cand in candidates:
        c = re.sub(r"[^a-z]", "", cand.lower())
        for original, cleaned in norm.items():
            if cleaned == c:
                return original
    for cand in candidates:
        c = re.sub(r"[^a-z]", "", cand.lower())
        for original, cleaned in norm.items():
            if c and c in cleaned:
                return original
    return None


def load(path: Path) -> list[dict]:
    """Read a GSC CSV (UI export) or JSON (API rows) into normalized records."""
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text())
        rows = raw.get("rows", raw) if isinstance(raw, dict) else raw
        out = []
        for r in rows:
            keys = r.get("keys", [])
            out.append(
                {
                    "query": keys[0] if keys else "",
                    "page": keys[1] if len(keys) > 1 else "",
                    "clicks": float(r.get("clicks", 0)),
                    "impressions": float(r.get("impressions", 0)),
                    "ctr": float(r.get("ctr", 0)),
                    "position": float(r.get("position", 0)),
                }
            )
        return out

    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            sys.exit(f"error: {path.name} has no header row.")
        h = reader.fieldnames
        q_col = find_column(h, "top queries", "query", "queries", "search query")
        p_col = find_column(h, "top pages", "page", "pages", "landing page", "url", "address")
        c_col = find_column(h, "clicks", "url clicks")
        i_col = find_column(h, "impressions", "impr")
        ctr_col = find_column(h, "ctr", "click through rate")
        pos_col = find_column(h, "position", "average position", "avg position")

        if not (c_col and i_col):
            sys.exit(
                f"error: {path.name} has no Clicks/Impressions columns.\n"
                f"Found: {h}\nExport the Performance table from Search Console."
            )
        if not (q_col or p_col):
            sys.exit(f"error: {path.name} has neither a query nor a page column.")

        records = []
        for row in reader:
            imp = parse_num(row.get(i_col))
            if imp <= 0:
                continue
            clicks = parse_num(row.get(c_col))
            ctr = parse_pct(row.get(ctr_col)) if ctr_col else (clicks / imp)
            records.append(
                {
                    "query": (row.get(q_col) or "").strip() if q_col else "",
                    "page": (row.get(p_col) or "").strip() if p_col else "",
                    "clicks": clicks,
                    "impressions": imp,
                    "ctr": ctr,
                    "position": parse_num(row.get(pos_col)) if pos_col else 0.0,
                }
            )
        return records


def key_of(r: dict) -> str:
    return f"{r['query']}||{r['page']}"


def striking_distance(rows: list[dict], min_impressions: float) -> list[dict]:
    out = []
    for r in rows:
        pos = r["position"]
        if not (8 <= pos <= 20) or r["impressions"] < min_impressions:
            continue
        upside = r["impressions"] * (CTR_CURVE[PAGE_ONE_TARGET] - r["ctr"])
        if upside <= 0:
            continue
        out.append({**r, "clicks_upside": round(upside, 1)})
    return sorted(out, key=lambda r: -r["clicks_upside"])


def ctr_underperformers(rows: list[dict], min_impressions: float) -> list[dict]:
    out = []
    for r in rows:
        pos = r["position"]
        if pos <= 0 or pos > 10 or r["impressions"] < min_impressions:
            continue
        exp = expected_ctr(pos)
        # Only flag a real shortfall, not noise around the curve.
        if r["ctr"] >= exp * 0.6:
            continue
        out.append(
            {
                **r,
                "expected_ctr": round(exp, 4),
                "ctr_gap": round(exp - r["ctr"], 4),
                "clicks_upside": round(r["impressions"] * (exp - r["ctr"]), 1),
            }
        )
    return sorted(out, key=lambda r: -r["clicks_upside"])


def cannibalization(rows: list[dict], min_impressions: float) -> list[dict]:
    """Same query, multiple pages — only detectable with query+page data."""
    by_query: dict[str, list[dict]] = {}
    for r in rows:
        if not r["query"] or not r["page"]:
            continue
        by_query.setdefault(r["query"], []).append(r)

    out = []
    for query, group in by_query.items():
        pages = {g["page"]: g for g in group}
        if len(pages) < 2:
            continue
        total_imp = sum(g["impressions"] for g in group)
        if total_imp < min_impressions:
            continue
        ranked = sorted(group, key=lambda g: g["position"] or 999)
        out.append(
            {
                "query": query,
                "pages": len(pages),
                "total_impressions": total_imp,
                "total_clicks": sum(g["clicks"] for g in group),
                "best_position": ranked[0]["position"],
                "competing": [
                    {"page": g["page"], "position": g["position"],
                     "impressions": g["impressions"], "clicks": g["clicks"]}
                    for g in ranked[:4]
                ],
            }
        )
    return sorted(out, key=lambda r: -r["total_impressions"])


def compare_periods(cur: list[dict], prev: list[dict], min_impressions: float) -> dict:
    prev_by = {key_of(r): r for r in prev}
    cur_by = {key_of(r): r for r in cur}

    decayed, grown, lost = [], [], []
    for k, c in cur_by.items():
        p = prev_by.get(k)
        if not p:
            continue
        if max(c["impressions"], p["impressions"]) < min_impressions:
            continue
        d_clicks = c["clicks"] - p["clicks"]
        d_pos = (c["position"] - p["position"]) if (c["position"] and p["position"]) else 0.0
        rec = {
            "query": c["query"], "page": c["page"],
            "clicks_now": c["clicks"], "clicks_before": p["clicks"],
            "clicks_delta": round(d_clicks, 1),
            "impressions_now": c["impressions"], "impressions_before": p["impressions"],
            "position_now": round(c["position"], 1), "position_before": round(p["position"], 1),
            # Positive position delta = ranking got worse (higher number).
            "position_delta": round(d_pos, 1),
        }
        if p["clicks"] >= 1 and d_clicks < 0 and abs(d_clicks) / max(p["clicks"], 1) >= 0.2:
            decayed.append(rec)
        elif d_clicks > 0 and d_clicks / max(p["clicks"], 1) >= 0.2:
            grown.append(rec)

    for k, p in prev_by.items():
        if k not in cur_by and p["impressions"] >= min_impressions:
            lost.append({"query": p["query"], "page": p["page"],
                         "clicks_before": p["clicks"], "impressions_before": p["impressions"]})

    return {
        "decayed": sorted(decayed, key=lambda r: r["clicks_delta"])[:50],
        "grown": sorted(grown, key=lambda r: -r["clicks_delta"])[:25],
        "dropped_out": sorted(lost, key=lambda r: -r["impressions_before"])[:25],
    }


def totals(rows: list[dict]) -> dict:
    clicks = sum(r["clicks"] for r in rows)
    imp = sum(r["impressions"] for r in rows)
    weighted_pos = sum(r["position"] * r["impressions"] for r in rows if r["position"])
    pos_imp = sum(r["impressions"] for r in rows if r["position"])
    return {
        "rows": len(rows),
        "clicks": round(clicks),
        "impressions": round(imp),
        "ctr": round(clicks / imp, 4) if imp else 0.0,
        "avg_position": round(weighted_pos / pos_imp, 1) if pos_imp else 0.0,
    }


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render(analysis: dict, site: str | None) -> str:
    t = analysis["totals"]
    L = [
        f"# SEO performance — {site or 'Search Console export'}",
        "",
        f"- **Generated:** {date.today().isoformat()}",
        f"- **Source:** {analysis['source_file']}"
        + (f" vs {analysis['previous_file']}" if analysis.get("previous_file") else ""),
        f"- **Totals:** {t['clicks']:,} clicks · {t['impressions']:,} impressions "
        f"· {pct(t['ctr'])} CTR · avg position {t['avg_position']}",
        "",
    ]

    sd = analysis["striking_distance"]
    L += ["## Striking distance — ranking 8-20", ""]
    if sd:
        L += [
            f"{len(sd)} queries sit just off page one. Ranked by clicks gained if each "
            f"reached position {PAGE_ONE_TARGET}. This is usually the cheapest traffic "
            "available: the page already ranks, it just needs a push.",
            "",
            "| Query | Page | Pos | Impressions | Est. clicks gained |",
            "|---|---|---|---|---|",
        ]
        for r in sd[:20]:
            page = (r["page"] or "—")[:60]
            L.append(
                f"| {r['query'] or '—'} | {page} | {r['position']:.1f} "
                f"| {int(r['impressions']):,} | +{r['clicks_upside']:.0f} |"
            )
        L += ["", f"_Total opportunity: **+{sum(r['clicks_upside'] for r in sd):.0f} clicks**_", ""]
    else:
        L += ["Nothing in the 8-20 band above the impression threshold.", ""]

    cu = analysis["ctr_underperformers"]
    L += ["## Under-clicked for their position", ""]
    if cu:
        L += [
            "These rank on page one but get materially fewer clicks than that position "
            "normally earns. That is a title/description problem, not a ranking problem — "
            "the fix is a rewrite, not a backlink.",
            "",
            "| Query | Pos | Actual CTR | Expected | Impressions | Est. clicks gained |",
            "|---|---|---|---|---|---|",
        ]
        for r in cu[:15]:
            L.append(
                f"| {r['query'] or r['page'][:50]} | {r['position']:.1f} | {pct(r['ctr'])} "
                f"| {pct(r['expected_ctr'])} | {int(r['impressions']):,} | +{r['clicks_upside']:.0f} |"
            )
        L.append("")
    else:
        L += ["No significant CTR shortfalls found.", ""]

    cn = analysis["cannibalization"]
    if cn:
        L += [
            "## Cannibalization — multiple pages, one query",
            "",
            "Two or more of your pages compete for the same query, splitting relevance "
            "signals so neither ranks as well as one consolidated page would.",
            "",
        ]
        for r in cn[:8]:
            L.append(
                f"**{r['query']}** — {r['pages']} pages, {int(r['total_impressions']):,} impressions, "
                f"best position {r['best_position']:.1f}"
            )
            for c in r["competing"]:
                L.append(f"  - `{c['page'][:70]}` — pos {c['position']:.1f}, {int(c['impressions']):,} impr")
            L.append("")
    elif analysis.get("cannibalization_checked"):
        L += ["## Cannibalization", "", "None detected.", ""]

    cmp_ = analysis.get("comparison")
    if cmp_:
        L += ["## Period over period", ""]
        if cmp_["decayed"]:
            L += [
                f"**Declining ({len(cmp_['decayed'])})** — lost 20%+ of clicks. "
                "Position moving up = ranking got worse.",
                "",
                "| Query | Clicks | Δ | Pos before → now |",
                "|---|---|---|---|",
            ]
            for r in cmp_["decayed"][:15]:
                L.append(
                    f"| {r['query'] or r['page'][:45]} | {r['clicks_before']:.0f} → {r['clicks_now']:.0f} "
                    f"| {r['clicks_delta']:.0f} | {r['position_before']} → {r['position_now']} |"
                )
            L.append("")
        if cmp_["dropped_out"]:
            L += [f"**Dropped out entirely ({len(cmp_['dropped_out'])})** — had impressions before, none now.", ""]
            for r in cmp_["dropped_out"][:10]:
                L.append(f"- {r['query'] or r['page'][:60]} — was {int(r['impressions_before']):,} impr")
            L.append("")
        if cmp_["grown"]:
            L += [f"**Growing ({len(cmp_['grown'])})** — worth doubling down on.", ""]
            for r in cmp_["grown"][:10]:
                L.append(f"- {r['query'] or r['page'][:60]} — +{r['clicks_delta']:.0f} clicks")
            L.append("")

    L += [
        "---",
        "",
        "_Estimated click gains use an industry-average CTR-by-position curve, so treat "
        "them as relative priorities, not forecasts. Your actual curve varies by SERP "
        "features, brand strength, and intent._",
        "",
    ]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze a Search Console export.")
    ap.add_argument("current", type=Path, help="GSC CSV/JSON export (current period)")
    ap.add_argument("--previous", type=Path, help="earlier export, enables decay analysis")
    ap.add_argument("--site", help="label for the report")
    ap.add_argument("--out", type=Path, default=Path("seo-run"))
    ap.add_argument("--min-impressions", type=float, default=10,
                    help="ignore rows below this; raise it on large sites")
    args = ap.parse_args()

    if not args.current.exists():
        sys.exit(f"error: no such file: {args.current}")

    rows = load(args.current)
    if not rows:
        sys.exit(f"error: no usable rows in {args.current.name} (all zero impressions?).")

    has_pages = any(r["page"] for r in rows)
    has_queries = any(r["query"] for r in rows)

    analysis = {
        "generated": date.today().isoformat(),
        "site": args.site,
        "source_file": args.current.name,
        "totals": totals(rows),
        "striking_distance": striking_distance(rows, args.min_impressions),
        "ctr_underperformers": ctr_underperformers(rows, args.min_impressions),
        "cannibalization": cannibalization(rows, args.min_impressions) if (has_pages and has_queries) else [],
        "cannibalization_checked": has_pages and has_queries,
    }

    if args.previous:
        if not args.previous.exists():
            sys.exit(f"error: no such file: {args.previous}")
        analysis["previous_file"] = args.previous.name
        analysis["comparison"] = compare_periods(rows, load(args.previous), args.min_impressions)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    (args.out / "performance.md").write_text(render(analysis, args.site))

    t = analysis["totals"]
    print(f"Rows analyzed: {t['rows']:,} | {t['clicks']:,} clicks, {t['impressions']:,} impressions",
          file=sys.stderr)
    print(f"Striking distance : {len(analysis['striking_distance'])}", file=sys.stderr)
    print(f"CTR shortfalls    : {len(analysis['ctr_underperformers'])}", file=sys.stderr)
    print(f"Cannibalized      : {len(analysis['cannibalization'])}"
          + ("" if analysis["cannibalization_checked"] else " (needs query+page export)"),
          file=sys.stderr)
    if not has_pages:
        print("note: no page column — export with Pages dimension for cannibalization.", file=sys.stderr)
    print(f"Wrote {args.out}/performance.md and analysis.json", file=sys.stderr)


if __name__ == "__main__":
    main()
