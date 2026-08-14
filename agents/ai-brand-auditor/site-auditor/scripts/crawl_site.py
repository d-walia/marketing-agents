#!/usr/bin/env python3
"""Crawl a site into a structured page corpus.

Corpus builder, not issue finder: fetches pages politely and stores one JSON
record per page (structure, metadata, links). All auditing happens downstream
(check_site.py, analysis subagent) as reads of the corpus — which is what lets
the same crawl serve a technical audit today and competitor content analysis
later (--full-text).

Stdlib only. No JS rendering: this sees server HTML, which is fine for most
marketing sites; a client-rendered site will show thin/empty pages (that
finding is itself diagnostic — AI crawlers mostly don't render JS either).

Usage:
  python3 scripts/crawl_site.py example.com
  python3 scripts/crawl_site.py https://example.com --max-pages 100 --delay 0.5
  python3 scripts/crawl_site.py example.com --full-text        # store main text (layer-4 corpus)

Output: runs/<domain>/<timestamp>/  pages.jsonl, crawl-summary.json,
        sitemap-urls.json, robots.txt
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Cloudflare 403s urllib's default UA (error 1010) — send an identifying one.
UA = "Mozilla/5.0 (compatible; dw-site-auditor/0.1; +https://github.com/d-walia/marketing-agents)"

# AI crawlers/agents worth reporting robots.txt rules for. Access here decides
# whether a site can be read by answer engines at all — the AEO ground floor.
AI_BOTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "Claude-Web", "anthropic-ai",
    "PerplexityBot", "Perplexity-User",
    "Google-Extended", "CCBot", "Applebot-Extended",
    "meta-externalagent", "Bytespider",
]

SKIP_EXT = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".avif",
    ".mp4", ".mp3", ".mov", ".webm", ".zip", ".gz", ".dmg", ".exe",
    ".woff", ".woff2", ".ttf", ".otf", ".eot", ".css", ".js", ".xml", ".json",
    ".txt", ".rss", ".atom",
}

SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


class PageParser(HTMLParser):
    """Extract structure from one HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self.meta_description = None
        self.meta_robots = None
        self.canonical = None
        self.h1s = []
        self.headings = []          # [tag, text] for h1-h3, document order
        self.hrefs = []
        self.images_total = 0
        self.images_missing_alt = 0
        self.jsonld_raw = []
        self.text_parts = []
        self._in_title = False
        self._in_jsonld = False
        self._jsonld_buf = []
        self._skip_depth = 0
        self._heading = None        # (tag, [text chunks]) while inside h1-h3

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TEXT_TAGS:
            if tag == "script" and (a.get("type") or "").lower().startswith("application/ld+json"):
                self._in_jsonld = True
                self._jsonld_buf = []
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or "").strip().lower()
            if name == "description" and self.meta_description is None:
                self.meta_description = (a.get("content") or "").strip()
            elif name == "robots" and self.meta_robots is None:
                self.meta_robots = (a.get("content") or "").strip().lower()
        elif tag == "link":
            rels = (a.get("rel") or "").lower().split()
            if "canonical" in rels and self.canonical is None:
                self.canonical = (a.get("href") or "").strip()
        elif tag in ("h1", "h2", "h3"):
            self._heading = (tag, [])
        elif tag == "a":
            href = (a.get("href") or "").strip()
            if href:
                self.hrefs.append(href)
        elif tag == "img":
            self.images_total += 1
            alt = a.get("alt")
            if alt is None or not alt.strip():
                self.images_missing_alt += 1

    def handle_startendtag(self, tag, attrs):
        # void elements (<meta ...>, <img ... />) can arrive here instead
        if tag in ("meta", "link", "img"):
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            if tag == "script" and self._in_jsonld:
                self.jsonld_raw.append("".join(self._jsonld_buf))
                self._in_jsonld = False
            return
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3") and self._heading:
            heading_tag, chunks = self._heading
            text = " ".join("".join(chunks).split())
            if text and heading_tag == tag:
                self.headings.append([tag, text])
                if tag == "h1":
                    self.h1s.append(text)
            self._heading = None

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_buf.append(data)
            return
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title = (self.title or "") + data
        if self._heading:
            self._heading[1].append(data)
        if data.strip():
            self.text_parts.append(data.strip())


def jsonld_types(raw_blocks):
    types = []
    for raw in raw_blocks:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for node in item.get("@graph", [item]) if "@graph" in item else [item]:
                t = node.get("@type") if isinstance(node, dict) else None
                if isinstance(t, list):
                    types.extend(str(x) for x in t)
                elif t:
                    types.append(str(t))
    return sorted(set(types))


def normalize(url):
    url, _ = urllib.parse.urldefrag(url)
    parts = urllib.parse.urlsplit(url)
    path = parts.path or "/"
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def bare_host(netloc):
    host = netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def fetch(url, timeout=20, max_hops=5):
    """GET with manual redirect following. Returns a dict."""
    chain = []
    current = url
    for _ in range(max_hops + 1):
        req = urllib.request.Request(current, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en",
        })
        start = time.time()
        try:
            with OPENER.open(req, timeout=timeout) as resp:
                return {
                    "status": resp.status, "final_url": current, "chain": chain,
                    "content_type": resp.headers.get("Content-Type", ""),
                    "body": resp.read(), "elapsed_ms": int((time.time() - start) * 1000),
                    "error": None,
                }
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location") if e.headers else None
                if not loc:
                    return {"status": e.code, "final_url": current, "chain": chain,
                            "content_type": "", "body": b"", "elapsed_ms": 0,
                            "error": "redirect without Location"}
                chain.append([current, e.code])
                current = normalize(urllib.parse.urljoin(current, loc))
                continue
            return {"status": e.code, "final_url": current, "chain": chain,
                    "content_type": (e.headers.get("Content-Type", "") if e.headers else ""),
                    "body": b"", "elapsed_ms": int((time.time() - start) * 1000), "error": None}
        except Exception as e:
            return {"status": None, "final_url": current, "chain": chain, "content_type": "",
                    "body": b"", "elapsed_ms": 0, "error": f"{type(e).__name__}: {e}"}
    return {"status": None, "final_url": current, "chain": chain, "content_type": "",
            "body": b"", "elapsed_ms": 0, "error": "too many redirects"}


def decode(body, content_type):
    charset = "utf-8"
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def parse_robots_groups(text):
    """Return ([({agents}, [(directive, path)])], [sitemap urls])."""
    groups, sitemaps = [], []
    agents, rules, collecting_agents = [], [], True
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip().lower(), val.strip()
        if key == "user-agent":
            if not collecting_agents:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(val.lower())
            collecting_agents = True
        elif key in ("allow", "disallow"):
            rules.append((key, val))
            collecting_agents = False
        elif key == "sitemap":
            sitemaps.append(val)
    if agents:
        groups.append((agents, rules))
    return groups, sitemaps


def ai_bot_verdict(groups, bot):
    """How robots.txt treats one bot: blocked / partial / allowed (+ which group)."""
    bot_l = bot.lower()
    matched = None
    for agents, rules in groups:
        if bot_l in agents:
            matched = (bot, rules)
            break
    if matched is None:
        for agents, rules in groups:
            if "*" in agents:
                matched = ("*", rules)
                break
    if matched is None:
        return {"verdict": "allowed", "via": "no robots rules"}
    via, rules = matched
    disallows = [p for d, p in rules if d == "disallow" and p]
    if any(p == "/" for p in disallows):
        return {"verdict": "blocked", "via": f"user-agent: {via}"}
    if disallows:
        return {"verdict": "partial", "via": f"user-agent: {via}", "disallow": disallows[:10]}
    return {"verdict": "allowed", "via": f"user-agent: {via}"}


def collect_sitemap_urls(sitemap_url, seen=None, depth=0):
    """Fetch a sitemap (or index) and return page URLs. Regex-free, stdlib XML-lite."""
    if seen is None:
        seen = set()
    if depth > 2 or sitemap_url in seen or len(seen) > 20:
        return []
    seen.add(sitemap_url)
    result = fetch(sitemap_url)
    if result["status"] != 200:
        return []
    text = decode(result["body"], result["content_type"])
    locs = []
    pos = 0
    while True:
        start = text.find("<loc>", pos)
        if start == -1:
            break
        end = text.find("</loc>", start)
        if end == -1:
            break
        locs.append(text[start + 5:end].strip())
        pos = end + 6
    if "<sitemapindex" in text[:2000]:
        urls = []
        for child in locs:
            urls.extend(collect_sitemap_urls(child, seen, depth + 1))
        return urls
    return locs


def looks_crawlable(url):
    path = urllib.parse.urlsplit(url).path.lower()
    dot = path.rfind(".")
    if dot != -1 and path[dot:] in SKIP_EXT:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="Crawl a site into a page corpus.")
    ap.add_argument("site", help="domain or start URL, e.g. example.com")
    ap.add_argument("--max-pages", type=int, default=300)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--full-text", action="store_true",
                    help="store extracted page text (for content analysis / layer-4 corpus)")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="crawl URLs robots.txt disallows for our UA (still recorded either way)")
    args = ap.parse_args()

    start_url = args.site if args.site.startswith("http") else f"https://{args.site}"
    start_url = normalize(start_url)
    origin = urllib.parse.urlsplit(start_url)
    root_host = bare_host(origin.netloc)
    base = f"{origin.scheme}://{origin.netloc}"

    run_dir = ROOT / "runs" / root_host / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")

    # --- robots.txt: crawl permission for us, access verdicts for AI bots ---
    robots_result = fetch(f"{base}/robots.txt")
    robots_text = decode(robots_result["body"], robots_result["content_type"]) if robots_result["status"] == 200 else ""
    (run_dir / "robots.txt").write_text(robots_text or f"(status {robots_result['status']})")
    groups, robots_sitemaps = parse_robots_groups(robots_text)
    ai_access = {bot: ai_bot_verdict(groups, bot) for bot in AI_BOTS}

    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_text.splitlines())

    # --- llms.txt (emerging answer-engine convention) ---
    llms = {}
    for name in ("llms.txt", "llms-full.txt"):
        r = fetch(f"{base}/{name}")
        llms[name] = r["status"]
        time.sleep(args.delay / 2)

    # --- sitemap ---
    sitemap_candidates = robots_sitemaps or [f"{base}/sitemap.xml"]
    sitemap_urls = []
    for sm in sitemap_candidates[:5]:
        sitemap_urls.extend(collect_sitemap_urls(sm))
    sitemap_urls = [normalize(u) for u in sitemap_urls]
    (run_dir / "sitemap-urls.json").write_text(json.dumps(sitemap_urls, indent=1))

    def is_internal(url):
        parts = urllib.parse.urlsplit(url)
        return parts.scheme in ("http", "https") and bare_host(parts.netloc) == root_host

    # --- crawl: BFS from homepage, sitemap URLs appended as seeds ---
    queue = [start_url] + [u for u in sitemap_urls if is_internal(u) and looks_crawlable(u)]
    visited, robots_skipped, pages = set(), [], 0
    out = (run_dir / "pages.jsonl").open("w")
    print(f"Crawling {root_host} (max {args.max_pages} pages, {args.delay}s delay) -> {run_dir}")

    while queue and pages < args.max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if not args.ignore_robots and robots_text and not rp.can_fetch(UA, url):
            robots_skipped.append(url)
            continue

        result = fetch(url)
        visited.add(result["final_url"])
        record = {
            "url": url,
            "final_url": result["final_url"],
            "status": result["status"],
            "redirect_chain": result["chain"],
            "content_type": result["content_type"].split(";")[0].strip(),
            "elapsed_ms": result["elapsed_ms"],
            "error": result["error"],
            "in_sitemap": url in sitemap_urls,
        }

        is_html = "text/html" in result["content_type"] or "xhtml" in result["content_type"]
        if result["status"] == 200 and is_html and result["body"]:
            parser = PageParser()
            try:
                parser.feed(decode(result["body"], result["content_type"]))
            except Exception as e:
                record["parse_error"] = f"{type(e).__name__}: {e}"
            internal, external = [], set()
            for href in parser.hrefs:
                if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                    continue
                absolute = normalize(urllib.parse.urljoin(result["final_url"], href))
                if is_internal(absolute):
                    if absolute not in internal:
                        internal.append(absolute)
                else:
                    external.add(urllib.parse.urlsplit(absolute).netloc)
            text = " ".join(parser.text_parts)
            record.update({
                "title": " ".join(parser.title.split()) if parser.title else None,
                "meta_description": parser.meta_description,
                "meta_robots": parser.meta_robots,
                "canonical": normalize(urllib.parse.urljoin(result["final_url"], parser.canonical)) if parser.canonical else None,
                "h1s": parser.h1s,
                "headings": parser.headings,
                "word_count": len(text.split()),
                "internal_links": internal,
                "external_domains": sorted(external),
                "images_total": parser.images_total,
                "images_missing_alt": parser.images_missing_alt,
                "jsonld_types": jsonld_types(parser.jsonld_raw),
            })
            if args.full_text:
                record["text"] = text
            for link in internal:
                if link not in visited and looks_crawlable(link):
                    queue.append(link)

        out.write(json.dumps(record) + "\n")
        pages += 1
        if pages % 25 == 0:
            print(f"  {pages} pages, queue {len(queue)}")
        time.sleep(args.delay)

    out.close()

    # --- summary ---
    status_counts = {}
    for line in (run_dir / "pages.jsonl").read_text().splitlines():
        s = str(json.loads(line)["status"])
        status_counts[s] = status_counts.get(s, 0) + 1
    summary = {
        "domain": root_host,
        "start_url": start_url,
        "started_at": started_at,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pages_crawled": pages,
        "status_counts": status_counts,
        "queue_remaining": len(queue),
        "hit_page_cap": pages >= args.max_pages and len(queue) > 0,
        "robots_txt_status": robots_result["status"],
        "robots_skipped_urls": robots_skipped,
        "sitemap": {"candidates": sitemap_candidates, "url_count": len(sitemap_urls)},
        "llms_txt": llms,
        "ai_bot_access": ai_access,
        "full_text": args.full_text,
        "params": {"max_pages": args.max_pages, "delay": args.delay, "user_agent": UA},
    }
    (run_dir / "crawl-summary.json").write_text(json.dumps(summary, indent=2))

    blocked = [b for b, v in ai_access.items() if v["verdict"] == "blocked"]
    print(f"\nDone: {pages} pages ({status_counts}), sitemap {len(sitemap_urls)} URLs")
    if summary["hit_page_cap"]:
        print(f"NOTE: hit --max-pages with {len(queue)} URLs still queued — corpus is partial")
    print(f"AI bots blocked by robots.txt: {', '.join(blocked) if blocked else 'none'}")
    print(f"Run dir: {run_dir}")


if __name__ == "__main__":
    main()
