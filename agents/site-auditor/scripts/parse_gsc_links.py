#!/usr/bin/env python3
"""Summarize a Google Search Console Links export into links-summary.json.

Own-site backlink data, free, no API: GSC > Links > Export external links
gives a ZIP of CSVs ("Top linking sites", "Top linked pages", "Top linking
text"). Point this script at the extracted folder (or individual CSVs) and it
writes a summary the analysis subagent folds into the audit.

Same philosophy as the SEO monitor's GSC analyzer: a CSV a client can email
you beats an API needing OAuth. Limitation is inherent to the source — GSC
only shows links to properties you (or the client) have verified. Competitor
backlinks are out of scope by design (see README: that's the paid-API
upgrade trigger, deliberately not built).

Usage:
  python3 scripts/parse_gsc_links.py ~/Downloads/gsc-links-export/ [--run runs/<domain>/<ts>]
  python3 scripts/parse_gsc_links.py "Top linking sites.csv" [--out links-summary.json]
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

TOP_N = 25


def classify(path, header):
    """Guess which GSC export a CSV is, from filename then header."""
    name = path.name.lower()
    joined = " ".join(header).lower()
    for key, label in (("linking site", "top_linking_sites"),
                       ("linked page", "top_linked_pages"),
                       ("linking text", "top_linking_text"),
                       ("target page", "top_linked_pages")):
        if key in name or key in joined:
            return label
    return path.stem.lower().replace(" ", "_")


def summarize_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return None
    header, data = rows[0], rows[1:]
    data = [r for r in data if r and r[0].strip()]

    def metric(row):
        for cell in row[1:]:
            try:
                return int(cell.replace(",", ""))
            except (ValueError, AttributeError):
                continue
        return 0

    ranked = sorted(data, key=metric, reverse=True)
    total = sum(metric(r) for r in data)
    top = [{"item": r[0], "count": metric(r)} for r in ranked[:TOP_N]]
    top3 = sum(e["count"] for e in top[:3])
    return {
        "file": path.name,
        "kind": classify(path, header),
        "columns": header,
        "rows": len(data),
        "metric_total": total,
        "top": top,
        "top3_share": round(top3 / total, 3) if total else None,
    }


def main():
    ap = argparse.ArgumentParser(description="Summarize GSC Links export CSVs.")
    ap.add_argument("paths", nargs="+", help="CSV file(s) or a folder of them")
    ap.add_argument("--run", help="run directory to write links-summary.json into")
    ap.add_argument("--out", help="explicit output path")
    args = ap.parse_args()

    csvs = []
    for p in args.paths:
        p = Path(p).expanduser()
        if p.is_dir():
            csvs.extend(sorted(p.glob("*.csv")))
        elif p.suffix.lower() == ".csv":
            csvs.append(p)
    if not csvs:
        sys.exit("No CSV files found in the given paths.")

    summaries = [s for s in (summarize_csv(p) for p in csvs) if s]
    result = {
        "source": "Google Search Console Links export (own-site backlinks)",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": summaries,
    }
    sites = next((s for s in summaries if s["kind"] == "top_linking_sites"), None)
    if sites:
        result["referring_domains"] = sites["rows"]
        result["top3_domain_share"] = sites["top3_share"]

    out = Path(args.out) if args.out else \
        (Path(args.run) / "links-summary.json" if args.run else Path("links-summary.json"))
    out.write_text(json.dumps(result, indent=2))

    print(f"Parsed {len(summaries)} CSV(s) -> {out}")
    if sites:
        print(f"  referring domains: {sites['rows']} (top-3 concentration {sites['top3_share']:.0%})")
        for e in sites["top"][:5]:
            print(f"    {e['item']}: {e['count']}")


if __name__ == "__main__":
    main()
