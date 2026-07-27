#!/usr/bin/env python3
"""Render a brand-audit run into a single self-contained, shareable HTML file.

The pipeline's deliverable (report.md) is written for people who open markdown.
Most stakeholders don't. This script turns a completed run directory into one
HTML file — inline CSS, no external assets, light/dark aware — that can be
emailed, published to outputs/, or dropped on a site as-is.

Usage:
    python3 render_report.py runs/2026-07-25_141530
    python3 render_report.py runs/2026-07-25_141530 --out ~/Desktop/audit.html

Reads report.md (required) and manifest.json (optional, powers the header band)
from the run directory. Standard library only; no pip installs. Rendering is
free — re-run it as often as you like, it never touches an API.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent  # scripts/ -> ai-brand-auditor/ -> agents/ -> repo


# ---------------------------------------------------------------------------
# Minimal markdown -> HTML (the subset audit-reporter actually emits:
# headers, tables, lists, bold/italic/code, links, blockquotes, fences, hr)
# ---------------------------------------------------------------------------

def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" rel="noopener">\1</a>',
        text,
    )
    return text


def _table(rows: list[str]) -> str:
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]] if len(rows) > 2 else []
    out = ["<table>", "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in head]
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            row += [""] * (len(head) - len(row))  # ragged row: pad, never drop
            out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row[: len(head)]) + "</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "".join(out)


_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def md_to_html(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    para: list[str] = []
    list_stack: list[str] = []  # open list tags, "ul"/"ol"

    def flush_para() -> None:
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    def close_lists() -> None:
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # fenced code
        if stripped.startswith("```"):
            flush_para()
            close_lists()
            block: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            i += 1
            continue

        # table: a pipe row followed by a separator row
        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and _SEPARATOR.match(lines[i + 1] or "")
        ):
            flush_para()
            close_lists()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows))
            continue

        # headers
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush_para()
            close_lists()
            level = min(len(m.group(1)) + 1, 5)  # report h1 -> page h2 etc.
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # hr
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush_para()
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            flush_para()
            close_lists()
            quote: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{_inline(' '.join(q for q in quote if q))}</p></blockquote>")
            continue

        # lists (one level is all the reporter emits; nested items flatten safely)
        m = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            flush_para()
            kind = "ol" if m.group(1)[0].isdigit() else "ul"
            if not list_stack or list_stack[-1] != kind:
                close_lists()
                out.append(f"<{kind}>")
                list_stack.append(kind)
            out.append(f"<li>{_inline(m.group(2))}</li>")
            i += 1
            continue

        # blank
        if not stripped:
            flush_para()
            close_lists()
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para()
    close_lists()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

CSS = """
:root {
  color-scheme: light;
  --surface: #fcfcfb; --card: #f4f3f1; --border: #e3e2de;
  --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #7a7975;
  --accent: #2a78d6; --serious: #c93f3e;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --surface: #1a1a19; --card: #242423; --border: #383835;
    --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #8f8e87;
    --accent: #3987e5; --serious: #e66767;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--surface); color: var(--ink);
  font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 760px; margin: 0 auto; padding: 48px 24px 96px; }
header.audit { border-bottom: 2px solid var(--ink); padding-bottom: 24px; margin-bottom: 8px; }
.kicker { font-size: 13px; letter-spacing: .18em; text-transform: uppercase; color: var(--ink-3); margin: 0 0 8px; }
h1 { font-size: 34px; line-height: 1.15; margin: 0 0 6px; }
.meta { color: var(--ink-2); font-size: 14px; margin: 0; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 24px 0 8px; }
.tile { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }
.tile .n { font-size: 26px; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
.tile .l { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-3); margin-top: 4px; }
.tile.bad .n { color: var(--serious); }
h2 { font-size: 24px; margin: 40px 0 12px; }
h3 { font-size: 19px; margin: 32px 0 10px; }
h4, h5 { font-size: 16px; margin: 24px 0 8px; }
p { margin: 0 0 14px; }
a { color: var(--accent); }
table { width: 100%; border-collapse: collapse; margin: 16px 0 20px; font-size: 14.5px; }
th { text-align: left; font-size: 12.5px; letter-spacing: .05em; text-transform: uppercase; color: var(--ink-2); }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
thead tr { border-bottom: 2px solid var(--ink); }
code { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; font-size: .88em; }
pre { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; overflow-x: auto; }
pre code { background: none; border: none; padding: 0; }
blockquote { margin: 16px 0; padding: 4px 18px; border-left: 3px solid var(--accent); color: var(--ink-2); }
ul, ol { margin: 0 0 14px; padding-left: 24px; }
li { margin-bottom: 5px; }
hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--ink-3); font-size: 13px; }
@media print { body { background: #fff; } main { padding-top: 12px; } }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<main>
<header class="audit">
<p class="kicker">AI Brand Audit &middot; GEO / AEO</p>
<h1>{brand}</h1>
<p class="meta">{meta_line}</p>
{tiles}
</header>
{body}
<footer>Generated {generated} by the AI Brand Auditor pipeline &mdash; query collection, perception scoring, and rubric grading run as independent steps; disagreements between analyses are reported, not smoothed over.</footer>
</main>
</body>
</html>
"""


def build_tiles(manifest: dict) -> str:
    if not manifest:
        return ""
    tiles = []
    providers = manifest.get("providers") or {}
    if providers:
        tiles.append(("Models audited", str(len(providers))))
    if manifest.get("queries") is not None:
        tiles.append(("Queries per model", str(manifest["queries"])))
    if manifest.get("calls_ok") is not None:
        tiles.append(("Calls succeeded", str(manifest["calls_ok"])))
    failed = manifest.get("calls_failed")
    failed_n = len(failed) if isinstance(failed, list) else failed
    html_tiles = "".join(
        f'<div class="tile"><div class="n">{html.escape(n)}</div><div class="l">{html.escape(l)}</div></div>'
        for l, n in tiles
    )
    if failed_n:
        html_tiles += (
            f'<div class="tile bad"><div class="n">{failed_n}</div>'
            f'<div class="l">Calls failed</div></div>'
        )
    return f'<div class="tiles">{html_tiles}</div>' if html_tiles else ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a run's report.md as shareable HTML.")
    ap.add_argument("run_dir", type=Path, help="runs/<run_id> directory")
    ap.add_argument("--out", type=Path, help="output HTML path (default: outputs/<brand>-ai-audit-<run_id>.html)")
    args = ap.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    report_path = run_dir / "report.md"
    if not report_path.exists():
        sys.exit(
            f"error: {report_path} not found.\n"
            "Rendering needs a completed run — dispatch audit-reporter first."
        )

    manifest: dict = {}
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            print(f"warn: {manifest_path} is not valid JSON — header band will be minimal", file=sys.stderr)

    brand = manifest.get("brand") or "Brand audit"
    run_id = manifest.get("run_id") or run_dir.name
    providers = manifest.get("providers") or {}
    models = ", ".join(providers.values()) if providers else None
    meta_bits = [f"Run {run_id}"]
    if models:
        meta_bits.append(models)
    if manifest.get("smoke"):
        meta_bits.append("smoke run — partial grid, not a full audit")

    report_md = report_path.read_text()
    # The header band already names the brand and run — drop a duplicate
    # top-level title if report.md opens with one.
    lines = report_md.lstrip().split("\n", 1)
    if lines[0].startswith("# "):
        report_md = lines[1] if len(lines) > 1 else ""
    body = md_to_html(report_md)

    page = PAGE.format(
        title=html.escape(f"{brand} — AI Brand Audit"),
        css=CSS,
        brand=html.escape(brand),
        meta_line=html.escape("  ·  ".join(meta_bits)),
        tiles=build_tiles(manifest),
        body=body,
        generated=datetime.now().strftime("%Y-%m-%d"),
    )

    slug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-") or "brand"
    out = args.out or (REPO_ROOT / "outputs" / f"{slug}-ai-audit-{run_id}.html")
    out = out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
