#!/usr/bin/env python3
"""Render an audit's raw JSON into a designed, self-contained HTML report.

Usage:
    python report_html.py sample-report.json              # -> sample-report.html
    python report_html.py sample-report.json -o out.html
"""

import argparse
import html
import json
import re

VERDICT_COLORS = {
    "strong": "ok", "qualified": "warn", "lukewarm": "warn",
    "negative": "bad", "not_assessed": "muted",
}
PRESSURE_LABELS = {
    "objections_dissolved": ("Objections dissolved", "ok"),
    "caveats_stand": ("Caveats stand", "warn"),
    "hardened_to_dealbreaker": ("Hardened to dealbreaker", "bad"),
    "switched_to_competitor": ("Switched to competitor", "bad"),
    "no_objections_raised": ("No objections raised", "ok"),
}

CSS = """
:root {
  --paper: #F7F8FA; --ink: #181C24; --muted: #5B6372; --line: #DDE1E8;
  --card: #FFFFFF; --accent: #0F766E; --accent-soft: #E4F0EE;
  --ok: #2F7D45; --ok-soft: #E3F0E6; --warn: #B0791B; --warn-soft: #F7EEDC;
  --bad: #BE3D2E; --bad-soft: #F8E6E2; --mut-soft: #EBEDF1;
}
@media (prefers-color-scheme: dark) { :root {
  --paper: #12151B; --ink: #E8EAEE; --muted: #9AA2B0; --line: #2A2F3A;
  --card: #191D26; --accent: #3ECFBE; --accent-soft: #15302D;
  --ok: #5CBF77; --ok-soft: #1A2C1F; --warn: #D9A44A; --warn-soft: #2E2617;
  --bad: #E06A5A; --bad-soft: #331D19; --mut-soft: #232834;
} }
:root[data-theme="light"] {
  --paper: #F7F8FA; --ink: #181C24; --muted: #5B6372; --line: #DDE1E8;
  --card: #FFFFFF; --accent: #0F766E; --accent-soft: #E4F0EE;
  --ok: #2F7D45; --ok-soft: #E3F0E6; --warn: #B0791B; --warn-soft: #F7EEDC;
  --bad: #BE3D2E; --bad-soft: #F8E6E2; --mut-soft: #EBEDF1;
}
:root[data-theme="dark"] {
  --paper: #12151B; --ink: #E8EAEE; --muted: #9AA2B0; --line: #2A2F3A;
  --card: #191D26; --accent: #3ECFBE; --accent-soft: #15302D;
  --ok: #5CBF77; --ok-soft: #1A2C1F; --warn: #D9A44A; --warn-soft: #2E2617;
  --bad: #E06A5A; --bad-soft: #331D19; --mut-soft: #232834;
}
* { box-sizing: border-box; }
body { background: var(--paper); }
.rpt {
  color: var(--ink); max-width: 880px; margin: 0 auto; padding: 48px 24px 96px;
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
.rpt h1, .rpt h2 {
  font-family: Palatino, "Palatino Linotype", "Book Antiqua", Georgia, serif;
  text-wrap: balance; line-height: 1.2;
}
.rpt h1 { font-size: 40px; margin: 8px 0 4px; font-weight: 600; }
.rpt h2 { font-size: 26px; margin: 56px 0 16px; font-weight: 600; }
.rpt h3 { font-size: 17px; margin: 32px 0 10px; font-weight: 650; }
.rpt h4 { font-size: 15px; margin: 24px 0 8px; font-weight: 650; }
.eyebrow {
  font: 600 12px/1 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .14em; text-transform: uppercase; color: var(--accent);
}
.sub { color: var(--muted); margin: 4px 0 0; }
.meta {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1px; background: var(--line); border: 1px solid var(--line);
  border-radius: 6px; overflow: hidden; margin-top: 28px;
}
.meta > div { background: var(--card); padding: 12px 16px; }
.meta .k {
  font: 600 11px/1 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
}
.meta .v { margin-top: 5px; font-size: 14px; line-height: 1.5; }
/* Funnel */
.funnel { display: flex; flex-direction: column; gap: 10px; margin-top: 20px; }
.stage { display: grid; grid-template-columns: 220px 1fr 90px; gap: 14px; align-items: center; }
.stage .lbl { font-size: 14px; text-align: right; color: var(--ink); }
.stage .bar-track { background: var(--mut-soft); border-radius: 4px; height: 26px; position: relative; }
.stage .bar { height: 100%; border-radius: 4px; background: var(--accent); min-width: 2px; }
.stage.lost .bar { background: var(--bad); }
.stage .n {
  font: 600 14px/1 ui-monospace, "SF Mono", Menlo, monospace;
  font-variant-numeric: tabular-nums; color: var(--muted);
}
.divert { margin: 14px 0 0 234px; font-size: 14px; color: var(--bad); }
/* Session cards */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; margin-top: 20px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 18px 20px; }
.card .who { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.card .sid { font: 650 15px/1.3 -apple-system, sans-serif; }
.card .asst {
  font: 600 11px/1 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
}
.pills { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.pill {
  font: 600 11.5px/1 ui-monospace, "SF Mono", Menlo, monospace;
  padding: 5px 9px; border-radius: 99px; letter-spacing: .03em;
}
.pill.ok { background: var(--ok-soft); color: var(--ok); }
.pill.warn { background: var(--warn-soft); color: var(--warn); }
.pill.bad { background: var(--bad-soft); color: var(--bad); }
.pill.muted { background: var(--mut-soft); color: var(--muted); }
.pill.accent { background: var(--accent-soft); color: var(--accent); }
.card dl { margin: 0; font-size: 13.5px; }
.card dt {
  font: 600 10.5px/1 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin-top: 12px;
}
.card dd { margin: 4px 0 0; line-height: 1.55; }
/* Analysis prose */
.prose { max-width: 720px; }
.prose p { margin: 0 0 14px; }
.prose li { margin: 0 0 6px; }
.prose strong { font-weight: 650; }
.table-wrap { overflow-x: auto; margin: 16px 0; }
.rpt table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
.rpt th {
  text-align: left; font: 600 11px/1.4 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
  border-bottom: 2px solid var(--line); padding: 8px 12px 8px 0;
}
.rpt td { border-bottom: 1px solid var(--line); padding: 10px 12px 10px 0; vertical-align: top; line-height: 1.5; }
.rpt td:first-child { font-variant-numeric: tabular-nums; white-space: nowrap; }
.foot { margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }
@media (max-width: 640px) {
  .stage { grid-template-columns: 1fr; gap: 4px; }
  .stage .lbl { text-align: left; }
  .divert { margin-left: 0; }
  .rpt h1 { font-size: 30px; }
}
"""


def esc(s):
    return html.escape(str(s if s is not None else ""))


def md_inline(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def md_to_html(md: str) -> str:
    """Minimal markdown renderer for the synthesis section."""
    out, para, table, ul = [], [], [], []

    def flush_para():
        if para:
            out.append(f"<p>{md_inline(' '.join(para))}</p>")
            para.clear()

    def flush_ul():
        if ul:
            out.append("<ul>" + "".join(f"<li>{md_inline(i)}</li>" for i in ul) + "</ul>")
            ul.clear()

    def flush_table():
        if table:
            head, *rows = [r for r in table if not re.match(r"^[\s|:-]+$", r)]
            cells = lambda r: [c.strip() for c in r.strip("|").split("|")]
            th = "".join(f"<th>{md_inline(c)}</th>" for c in cells(head))
            trs = "".join(
                "<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in cells(r)) + "</tr>"
                for r in rows
            )
            out.append(f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            table.clear()

    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            flush_para(); flush_ul(); table.append(stripped); continue
        flush_table()
        m = re.match(r"^(#{2,4})\s+(.*)", stripped)
        if m:
            flush_para(); flush_ul()
            level = len(m.group(1))
            out.append(f"<h{level}>{md_inline(m.group(2))}</h{level}>")
        elif re.match(r"^[-*]\s+", stripped):
            flush_para(); ul.append(re.sub(r"^[-*]\s+", "", stripped))
        elif re.match(r"^\d+\.\s+", stripped):
            flush_para(); ul.append(re.sub(r"^\d+\.\s+", "", stripped))
        elif not stripped:
            flush_para(); flush_ul()
        else:
            flush_ul(); para.append(stripped)
    flush_para(); flush_ul(); flush_table()
    return "\n".join(out)


def funnel_stages(audit: dict) -> list:
    sessions = audit["sessions"]
    brand = audit["brand"].lower()
    return [
        ("Category proposed", sum(s["category_proposed"] for s in sessions)),
        ("Brand mentioned unprompted", sum(s["unprompted_brand_mention"] for s in sessions)),
        ("Brand shortlisted", sum(any(brand in v.lower() for v in s["shortlist"]) for s in sessions)),
        ("Strong recommendation", sum(s["brand_recommendation"] == "strong" for s in sessions)),
        ("Final call under pressure", sum(s["final_call"] == "target_brand" for s in sessions)),
    ]


def render_funnel(audit: dict) -> str:
    n = len(audit["sessions"])
    rows = []
    for label, count in funnel_stages(audit):
        pct = max((count / n) * 100 if n else 0, 1.5)
        cls = "stage lost" if count == 0 else "stage"
        rows.append(
            f'<div class="{cls}"><div class="lbl">{esc(label)}</div>'
            f'<div class="bar-track"><div class="bar" style="width:{pct:.0f}%"></div></div>'
            f'<div class="n">{count}/{n}</div></div>'
        )
    diverted = sorted({
        s["final_call_vendor"] for s in audit["sessions"]
        if s["final_call"] == "competitor" and s["final_call_vendor"]
    })
    divert = (
        f'<div class="divert">Final calls diverted to: <strong>{esc(", ".join(diverted))}</strong></div>'
        if diverted else ""
    )
    return f'<div class="funnel">{"".join(rows)}</div>{divert}'


def render_card(audit: dict, s: dict) -> str:
    verdict_cls = VERDICT_COLORS.get(s["brand_recommendation"], "muted")
    p_label, p_cls = PRESSURE_LABELS.get(s["pressure_outcome"], (s["pressure_outcome"], "muted"))
    if s["final_call"] == "target_brand":
        final = f'<span class="pill ok">Final call: {esc(audit["brand"])}</span>'
    elif s["final_call"] == "competitor":
        final = f'<span class="pill bad">Final call: {esc(s["final_call_vendor"] or "competitor")}</span>'
    else:
        final = '<span class="pill muted">Final call: deferred</span>'
    rows = [
        ("Shortlist", ", ".join(s["shortlist"]) or "none given"),
        ("Preferred over the brand", (
            f"{s['competitor_preferred']} — {s['competitor_preferred_reason']}"
            if s["competitor_preferred"] else "none"
        )),
        ("Dealbreakers", "; ".join(s["dealbreakers"]) or "none"),
        ("Would change its mind if", s["flip_condition"] or "nothing named"),
    ]
    dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows)
    return (
        f'<div class="card"><div class="who"><span class="sid">{esc(s["scenario"])}</span>'
        f'<span class="asst">{esc(s["assistant"])} · {esc(s["assistant_model"])}</span></div>'
        f'<div class="pills"><span class="pill {verdict_cls}">Verdict: {esc(s["brand_recommendation"])}</span>'
        f'<span class="pill {p_cls}">{esc(p_label)}</span>{final}</div>'
        f"<dl>{dl}</dl></div>"
    )


def build_fragment(audit: dict) -> str:
    icp = audit["icp"]
    n = len(audit["sessions"])
    assistants = ", ".join(sorted({s["assistant"] for s in audit["sessions"]}))
    meta = [
        ("Category", audit["category"]),
        ("Buyer persona", f"{icp['role']} — {icp['description']}"),
        ("Jobs to be done", "; ".join(icp["jobs_to_be_done"])),
        ("Priorities", "; ".join(icp["priorities"])),
        ("Scenarios", ", ".join(s["id"] for s in audit["scenarios"])),
        ("Coverage", f"{assistants} · {n} sessions · {audit['date']}"),
    ]
    meta_html = "".join(
        f'<div><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>' for k, v in meta
    )
    cards = "".join(render_card(audit, s) for s in audit["sessions"])
    return f"""<style>{CSS}</style>
<main class="rpt">
  <div class="eyebrow">AI Brand Perception Audit</div>
  <h1>{esc(audit["brand"])}</h1>
  <p class="sub">How AI assistants judge {esc(audit["brand"])} when its buyers ask for help — and what would change their answer.</p>
  <div class="meta">{meta_html}</div>

  <h2>The buyer journey funnel</h2>
  {render_funnel(audit)}

  <h2>Sessions at a glance</h2>
  <div class="cards">{cards}</div>

  <div class="prose">{md_to_html(audit["analysis"])}</div>

  <div class="foot">
    Method: multi-turn buyer-journey chat sessions (4 stages, question + follow-up each) run as the ICP persona
    against each assistant's default-tier model at medium effort. Probes never name the brand or category before
    the assistant does. Extraction and synthesis by Claude. Beliefs reported are the assistants' own, verbatim
    from session transcripts — treat as perception data, not market fact.
  </div>
</main>"""


def main():
    parser = argparse.ArgumentParser(description="Render audit JSON as a designed HTML report.")
    parser.add_argument("json_path")
    parser.add_argument("-o", "--out", default=None)
    args = parser.parse_args()

    with open(args.json_path) as f:
        audit = json.load(f)
    fragment = build_fragment(audit)
    doc = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>AI Brand Perception Audit — {esc(audit['brand'])}</title></head>"
        f"<body style='margin:0'>{fragment}</body></html>"
    )
    out = args.out or args.json_path.replace(".json", ".html")
    with open(out, "w") as f:
        f.write(doc)
    print(f"Report: {out}")


if __name__ == "__main__":
    main()
