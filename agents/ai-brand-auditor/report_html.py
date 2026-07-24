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
  --paper: #FAFAF9; --ink: #1C1E22; --muted: #62666D; --line: #DEDFE2;
  --card: #FFFFFF; --bad: #A33C30; --mut-soft: #EDEEEF;
}
@media (prefers-color-scheme: dark) { :root {
  --paper: #17181B; --ink: #E6E7E9; --muted: #9B9EA4; --line: #2E3034;
  --card: #1D1F23; --bad: #D07162; --mut-soft: #26282C;
} }
:root[data-theme="light"] {
  --paper: #FAFAF9; --ink: #1C1E22; --muted: #62666D; --line: #DEDFE2;
  --card: #FFFFFF; --bad: #A33C30; --mut-soft: #EDEEEF;
}
:root[data-theme="dark"] {
  --paper: #17181B; --ink: #E6E7E9; --muted: #9B9EA4; --line: #2E3034;
  --card: #1D1F23; --bad: #D07162; --mut-soft: #26282C;
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
  letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
}
.sub { color: var(--muted); margin: 4px 0 0; }
.meta {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1px; background: var(--line); border: 1px solid var(--line);
  border-radius: 3px; overflow: hidden; margin-top: 28px;
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
.stage .bar-track { background: var(--mut-soft); border-radius: 2px; height: 22px; position: relative; }
.stage .bar { height: 100%; border-radius: 2px; background: var(--muted); min-width: 2px; }
.stage.lost .bar { background: var(--bad); }
.stage .n {
  font: 600 14px/1 ui-monospace, "SF Mono", Menlo, monospace;
  font-variant-numeric: tabular-nums; color: var(--muted);
}
.divert { margin: 14px 0 0 234px; font-size: 14px; color: var(--bad); }

/* Scorecard */
.score { width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 13.5px; }
.score th { text-align: left; font: 600 10.5px/1.4 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .09em; text-transform: uppercase; color: var(--muted);
  border-bottom: 1px solid var(--line); padding: 0 10px 8px 0; }
.score td { border-bottom: 1px solid var(--line); padding: 9px 10px 9px 0; vertical-align: middle; }
.score td.sess { font-weight: 550; }
.score td.frm { color: var(--muted); font-size: 12.5px; }
.verdict { display: inline-block; min-width: 58px; text-align: center;
  font: 600 11px/1 ui-monospace, "SF Mono", Menlo, monospace; letter-spacing: .06em;
  padding: 5px 8px; border-radius: 3px; border: 1px solid var(--line); color: var(--muted); }
.verdict.pass { color: var(--ink); border-color: var(--ink); }
.verdict.mixed { color: var(--ink); }
.verdict.fail { color: var(--bad); border-color: var(--bad); }
.legend { margin-top: 10px; font-size: 12px; color: var(--muted); }
/* Presence trace */
.trace { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }
.trace th { text-align: center; font: 600 10.5px/1.4 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .06em; color: var(--muted); border-bottom: 1px solid var(--line); padding: 0 4px 8px; }
.trace th.lbl, .trace td.lbl { text-align: left; padding-right: 12px; }
.trace td { border-bottom: 1px solid var(--line); padding: 9px 4px; text-align: center;
  font-variant-numeric: tabular-nums; }
.t-on { display: inline-block; width: 20px; height: 20px; line-height: 20px; border-radius: 3px;
  background: var(--ink); color: var(--paper); font: 600 11px/20px ui-monospace, Menlo, monospace; }
.t-off { display: inline-block; width: 20px; height: 20px; line-height: 20px; border-radius: 3px;
  background: var(--mut-soft); color: var(--muted); font: 400 11px/20px ui-monospace, Menlo, monospace; }
.rivals { display: block; font-size: 10px; color: var(--muted); margin-top: 2px; }
.narrow { color: var(--bad); font-size: 12.5px; }
/* Evidence graph */
.prov { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
.prov-row { display: grid; grid-template-columns: 220px 1fr 74px; gap: 12px; align-items: center; }
.prov-row .pl { font-size: 13px; }
.prov-track { background: var(--mut-soft); border-radius: 2px; height: 20px; }
.prov-bar { height: 100%; border-radius: 2px; background: var(--muted); min-width: 2px; }
.prov-row.own .prov-bar { background: var(--ink); }
.prov-row .pn { font: 600 12.5px/1 ui-monospace, Menlo, monospace; color: var(--muted);
  font-variant-numeric: tabular-nums; }
.flagnote { margin-top: 14px; padding: 12px 14px; border: 1px solid var(--bad);
  border-radius: 3px; font-size: 13px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.chip { font: 500 11.5px/1 ui-monospace, "SF Mono", Menlo, monospace; padding: 6px 9px;
  border: 1px solid var(--line); border-radius: 3px; color: var(--ink); }
/* Session cards */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; margin-top: 20px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 3px; padding: 18px 20px; }
.card .who { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.card .sid { font: 650 15px/1.3 -apple-system, sans-serif; }
.card .asst {
  font: 600 11px/1 ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
}
.pills { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.pill {
  font: 500 11.5px/1 ui-monospace, "SF Mono", Menlo, monospace;
  padding: 5px 8px; border-radius: 3px; border: 1px solid var(--line); color: var(--ink);
}
.pill.ok { border-color: var(--ink); font-weight: 650; }
.pill.warn { color: var(--ink); }
.pill.bad { color: var(--bad); border-color: var(--bad); }
.pill.muted { color: var(--muted); }
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
    """Escape for HTML, scrubbing em/en dashes into plain punctuation."""
    s = str(s if s is not None else "")
    s = re.sub(r"\s*—\s*", ", ", s)
    s = s.replace("–", "-")
    return html.escape(s)


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
            f"{s['competitor_preferred']}: {s['competitor_preferred_reason']}"
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



def _audit_mod():
    """Import audit.py lazily so the two renderers share one source of truth."""
    import importlib, os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    return importlib.import_module("audit")


def render_scorecard(audit: dict) -> str:
    try:
        marks_fn = _audit_mod().behavior_marks
    except Exception:
        return ""
    rows = []
    for s in audit["sessions"]:
        c, v, r = marks_fn(audit["brand"], s)
        cells = "".join(
            f'<td><span class="verdict {m.lower()}">{m}</span></td>' for m in (c, v, r)
        )
        rows.append(
            f'<tr><td class="sess">{esc(s["scenario"])}</td>'
            f'<td class="frm">{esc(s.get("framing", "operational"))}</td>'
            f'<td class="frm">{esc(s["assistant"])}</td>{cells}</tr>'
        )
    return f"""<table class="score">
  <thead><tr><th>Scenario</th><th>Framing</th><th>Assistant</th>
  <th>Category</th><th>Visibility</th><th>Recommendation</th></tr></thead>
  <tbody>{"".join(rows)}</tbody></table>
  <p class="legend">Does AI route the problem to the category, does the brand surface inside it,
  and does AI endorse it under pressure. PASS works today. MIXED surfaces but hedged.
  FAIL means the brand or category does not make it.</p>"""


def render_presence(audit: dict) -> str:
    try:
        compute = _audit_mod().compute_presence
    except Exception:
        return ""
    rows, any_narrow = [], False
    for s in audit["sessions"]:
        p = s.get("presence") or compute(
            s.get("transcript", ""), audit["brand"], audit.get("competitors", [])
        )
        if not p:
            continue
        if p.get("narrowing_stage"):
            any_narrow = True
        cells = ""
        for m, rv in zip(p["marks"], p["rivals"]):
            cls = "t-on" if m == "Y" else "t-off"
            rival = f'<span class="rivals">{rv}</span>' if rv else '<span class="rivals">&nbsp;</span>'
            cells += f'<td><span class="{cls}">{m}</span>{rival}</td>'
        narrow = (
            f'<td class="narrow">drops in {esc(p["narrowing_stage"])}</td>'
            if p.get("narrowing_stage") else "<td></td>"
        )
        rows.append(
            f'<td class="lbl">{esc(s["scenario"])} <span class="frm">'
            f'[{esc(s.get("framing", "operational"))}] {esc(s["assistant"])}</span></td>'
            + cells + narrow
        )
    if not rows:
        return ""
    width = max(len(audit["sessions"][0].get("presence", {}).get("marks", [])) or 8, 8)
    head = "".join(f"<th>T{i + 1}</th>" for i in range(width))
    body = "".join(f"<tr>{r}</tr>" for r in rows)
    note = (
        "The brand is named early, then drops out while competitors stay in the answer as the buyer "
        "presses on specifics. A mid-conversation loss, invisible to first-answer and final-call metrics."
        if any_narrow else
        "Where the brand enters the conversation, it stays in it."
    )
    cls = ' class="flagnote"' if any_narrow else ' class="legend"'
    return f"""<table class="trace">
  <thead><tr><th class="lbl">Session</th>{head}<th>Narrowing</th></tr></thead>
  <tbody>{body}</tbody></table>
  <p class="legend">Brand presence per assistant turn, measured from the transcript.
  Turns 1 to 4 are unprompted. The small figure counts known competitors in that turn.</p>
  <p{cls}>{note}</p>"""


def render_evidence(audit: dict) -> str:
    chains = [(s, e) for s in audit["sessions"] for e in (s.get("evidence_chain") or [])]
    if not chains:
        return ""
    total = len(chains)
    flagged = sum(1 for _, e in chains if e.get("assistant_flagged_weakness"))
    counts = {}
    for _, e in chains:
        counts[e["provenance"]] = counts.get(e["provenance"], 0) + 1

    labels = [
        ("first_party", "The brand's own content", "own"),
        ("third_party", "Independent sources", ""),
        ("training_memory", "Training memory, nothing read", ""),
        ("unstated", "No basis given", ""),
    ]
    bars = ""
    for key, label, extra in labels:
        n = counts.get(key, 0)
        if not n:
            continue
        pct = round(100 * n / total)
        bars += (
            f'<div class="prov-row {extra}"><div class="pl">{esc(label)}</div>'
            f'<div class="prov-track"><div class="prov-bar" style="width:{max(pct, 1)}%"></div></div>'
            f'<div class="pn">{n} · {pct}%</div></div>'
        )

    claim_rows = "".join(
        f'<tr><td>{esc(e["claim"])}</td><td>{esc(e["source"])}</td>'
        f'<td>{esc(e["provenance"].replace("_", " "))}</td>'
        f'<td>{"flagged" if e.get("assistant_flagged_weakness") else ""}</td></tr>'
        for _, e in chains
    )
    out = f"""<div class="prov">{bars}</div>
  <p class="legend">{total} claims traced across {len(audit["sessions"])} session(s).</p>"""
    if flagged:
        out += (
            f'<p class="flagnote">{flagged} of {total} claims were caveated by the assistant itself '
            "as self-reported, unverified, or stale. Proof that is read and discounted in the same "
            "breath is a structural weakness, not just a gap.</p>"
        )
    out += f"""
  <h3>Claim by claim</h3>
  <div class="table-wrap"><table><thead><tr><th>Claim</th><th>Rests on</th>
  <th>Provenance</th><th>Assistant flagged</th></tr></thead>
  <tbody>{claim_rows}</tbody></table></div>"""

    quantified = sorted({q for s in audit["sessions"] for q in (s.get("quantified_claims") or [])})
    if quantified:
        chips = "".join(f'<span class="chip">{esc(q)}</span>' for q in quantified)
        out += f"""<h3>Numbers AI repeats about the brand</h3>
  <p>Memorized and doing work in buying conversations. Also the claims a competitor must counter.</p>
  <div class="chips">{chips}</div>"""

    counter = [c for s in audit["sessions"] for c in (s.get("competitor_counter_evidence") or [])]
    if counter:
        rows = "".join(
            f'<tr><td>{esc(c["competitor"])}</td><td>{esc(c["asset"])}</td><td>{esc(c["criterion"])}</td></tr>'
            for c in counter
        )
        out += f"""<h3>Competitor assets used as counter-proof</h3>
  <p>Named rival material AI reached for, and the criterion each one won. An out-publish list.</p>
  <div class="table-wrap"><table><thead><tr><th>Competitor</th><th>Asset AI reached for</th>
  <th>Criterion it won</th></tr></thead><tbody>{rows}</tbody></table></div>"""

    depths = [
        s.get("citation_depth") for s in audit["sessions"]
        if s.get("citation_depth") not in (None, "not_applicable")
    ]
    if depths:
        deep = depths.count("deep_pages")
        out += f"""<h3>Citation depth</h3>
  <p>{deep} of {len(depths)} session(s) cited specific product or use-case pages rather than the
  homepage alone. Deep-page citation means AI understands the product; homepage-only means it
  knows the brand exists.</p>"""
    return out



def render_verification(audit: dict) -> str:
    checks = audit.get("fact_checks") or []
    if not checks:
        return ""
    order = {"fabricated": 0, "distorted": 1, "accurate": 2, "unverifiable": 3}
    checks = sorted(checks, key=lambda c: order.get(c["verdict"], 4))
    label = {"accurate": "accurate", "distorted": "distorted", "fabricated": "fabricated", "unverifiable": "not covered"}
    cls = {"accurate": "pass", "distorted": "fail", "fabricated": "fail", "unverifiable": "muted"}
    counts = {}
    for c in checks:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    wrong = counts.get("fabricated", 0) + counts.get("distorted", 0)
    summary = ", ".join(f"{counts[k]} {label[k]}" for k in ["accurate", "distorted", "fabricated", "unverifiable"] if counts.get(k))
    intro = (f'<p class="flagnote">{wrong} claim(s) AI repeats to buyers are wrong. A confidently '
             "false number in circulation is more urgent than a missing one.</p>") if wrong else ""
    rows = "".join(
        f'<tr><td><span class="verdict {cls[c["verdict"]]}">{label[c["verdict"]]}</span></td>'
        f'<td>{esc(c["ai_claim"])}</td><td>{esc(c["matched_fact"] or "no matching fact")}</td>'
        f'<td>{esc(c["note"])}</td></tr>'
        for c in checks
    )
    return (f'<p class="legend">Every number and specific claim AI stated, graded against the '
            f'brand-provided facts. {summary}.</p>{intro}'
            '<div class="table-wrap"><table><thead><tr><th>Verdict</th><th>AI\'s claim</th>'
            '<th>Checked against</th><th>Note</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def build_fragment(audit: dict) -> str:
    icp = audit["icp"]
    n = len(audit["sessions"])
    assistants = ", ".join(sorted({s["assistant"] for s in audit["sessions"]}))
    retrieval_on = any(s.get("retrieval_enabled") for s in audit["sessions"])
    mode = ("live web search: beliefs AI forms when it can look"
            if retrieval_on else
            "parametric: beliefs from training memory, no browsing")
    failed = audit.get("failed_sessions") or []
    personas = audit.get("personas_run") or []
    meta = [
        ("Category", audit["category"]),
        ("Buyer persona", f"{icp['role']}. {icp['description']}"),
        ("Jobs to be done", "; ".join(icp["jobs_to_be_done"])),
        ("Priorities", "; ".join(icp["priorities"])),
        ("Scenarios", ", ".join(s["id"] for s in audit["scenarios"])),
        ("Probe mode", mode),
        ("Coverage", f"{assistants} · {n} sessions · {audit['date']}"),
    ]
    if len(personas) > 1:
        meta.append(("Personas swept", ", ".join(personas)))
    if failed:
        meta.append((
            "Excluded (failed)",
            ", ".join(f"{f['scenario']} [{f.get('framing', 'operational')}] {f['assistant']}" for f in failed),
        ))
    meta_html = "".join(
        f'<div><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>' for k, v in meta
    )
    cards = "".join(render_card(audit, s) for s in audit["sessions"])
    _p = render_presence(audit)
    presence_block = f"<h2>Where the brand falls out of the conversation</h2>{_p}" if _p else ""
    _e = render_evidence(audit)
    evidence_block = f"<h2>Evidence graph: what the beliefs rest on</h2>{_e}" if _e else ""
    _v = render_verification(audit)
    verify_block = f"<h2>Fact check: is what AI says about you true</h2>{_v}" if _v else ""
    return f"""<style>{CSS}</style>
<main class="rpt">
  <div class="eyebrow">AI Brand Perception Audit</div>
  <h1>{esc(audit["brand"])}</h1>
  <p class="sub">What AI assistants tell buyers about {esc(audit["brand"])}, and what would change their answer.</p>
  <div class="meta">{meta_html}</div>

  <h2>AI behavior scorecard</h2>
  {render_scorecard(audit)}

  <h2>The buyer journey funnel</h2>
  {render_funnel(audit)}

  {presence_block}
  {evidence_block}
  {verify_block}
  <h2>Sessions at a glance</h2>
  <div class="cards">{cards}</div>

  <div class="prose">{md_to_html(audit["analysis"])}</div>

  <div class="foot">
    Method: multi-turn buyer-journey chat sessions (4 stages, question + follow-up each) run as the ICP persona
    against each assistant's default-tier model at medium effort. Probes never name the brand or category before
    the assistant does. Extraction and synthesis by Claude. Beliefs reported are the assistants' own, verbatim
    from session transcripts. Treat them as perception data, not market fact.
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
        f"<title>AI Brand Perception Audit: {esc(audit['brand'])}</title></head>"
        f"<body style='margin:0'>{fragment}</body></html>"
    )
    out = args.out or args.json_path.replace(".json", ".html")
    with open(out, "w") as f:
        f.write(doc)
    print(f"Report: {out}")


if __name__ == "__main__":
    main()
