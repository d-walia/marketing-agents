# Marketing Agents

Working agents for real GTM problems, built with Claude — each replacing a paid SaaS tool. The public face of these lives at [dhruvwalia.com](https://dhruvwalia.com/#agents).

> **TL;DR** — Seven public agents (site + AI-crawler audits, competitive intel, meeting transcription as a two-part pair, SEO, account intelligence, landing page mocks), four planned, plus the AI Brand Auditor, which graduated to its own private repo as a product. Each agent folder has a `SKILL.md` front door (auto-triggers in Claude Code) and a `README.md` explaining the design. Some have examples. Install by symlinking into `~/.claude/skills/`.

## What's inside

| Agent | What it does | Replaces | Status | Where |
|---|---|---|---|---|
| AI Brand Auditor | 4-subagent pipeline measuring what AI models say about a brand — described how, recommended or not, how accurately | Profound, AthenaHQ | Built; productized in a separate private repo | `d-walia/ai-brand-auditor` (private) |
| Competitive Intel Researcher | Competitor analysis → sourced report, sales battlecard, delta memo | Klue, Crayon | Built | [`agents/competitive-intel-researcher/`](agents/competitive-intel-researcher/) |
| Meeting Transcriber | **Capture half 1 of 2 — a recording that already exists.** Audio or video file in → structured notes out, via the free Groq Whisper API. Owns the notes step both halves share | Otter, Fireflies | Built | [`agents/meeting-transcriber/`](agents/meeting-transcriber/) |
| Live Meeting Transcriber | **Capture half 2 of 2 — a call happening right now.** Near-real-time from the Mac's mic (+ BlackHole for the far side). Produces a raw transcript, then hands it to the Meeting Transcriber notes step | Otter, Fireflies | Built | [`agents/live-meeting-transcriber/`](agents/live-meeting-transcriber/) |
| SEO Performance Monitor | Page performance from a Search Console export, position-weighted share of voice, keyword discovery via Google Suggest | Ahrefs, Semrush | Built | [`agents/seo-performance-monitor/`](agents/seo-performance-monitor/) |
| Site Auditor | Polite stdlib crawler → page corpus → technical checks + AI-crawler readiness (bot access, server-rendered content, structured data, llms.txt); own-site backlinks via GSC export | Screaming Frog | Built | [`agents/site-auditor/`](agents/site-auditor/) |
| Account Intelligence Agent | Claude drives the Clay web UI: seed CSV → enrichment waterfalls → research columns → contacts → email waterfall | A GTM engineer / Clay consultant | Built | [`agents/account-intelligence-agent/`](agents/account-intelligence-agent/) |
| Landing Page Builder | Brand capture (tokens + voice, two-pass extraction) → true-to-life HTML page mocks with copy in place, on stable share links | Figma comps, screenshot stitching | Built | [`agents/landing-page-builder/`](agents/landing-page-builder/) |
| Intelligent Copywriter | On-brand copy from the brand-pack input layer | Writer, Jasper | Planned | — |
| Customer Researcher | — | Wynter, UserTesting | Planned | — |
| Content Agents | — | Canva, Adobe GenStudio | Planned | — |
| Competitor Content Analyzer | Reads Site Auditor `--full-text` corpora of competitor sites → content gaps, decision factors, citation-worthy pages | The crawl stack AEO teams build in-house | Planned | — |
| Transcript Router | Routes a finished transcript to the agent that should act on it — competitor mentions → `intel/`, discovery calls → `brand-pack/` voice-of-customer, interviews → the PMM evaluator rubric | Nothing; hosted transcribers can't see your other tooling | Planned | — |

### Why transcription is two agents, not one

They are **one pipeline with two front doors**, not two competing tools. Pick by where the audio is coming from:

| Your situation | Use | Runs where |
|---|---|---|
| A recording that already exists (file dragged in, video, or a raw transcript to clean up) | `meeting-transcriber` | Anywhere — portable, no hardware needed |
| A call happening right now ("transcribe as I go") | `live-meeting-transcriber` → hands off | Only in Claude Code on the Mac — needs the mic |

Both end in the same place: the `meeting-transcriber` notes step, which does speaker attribution and writes the TL;DR, decisions, and action items. The live agent produces raw material, never a deliverable.

This started as one agent. Live capture was folded in on 2026-07-24, then split back out on 2026-07-26, because the two halves have incompatible constraints: live capture is **hardware-bound** (it needs the Mac's microphone, and a BlackHole aggregate device to hear the far side of a call), so it can never run in a cloud session. Keeping it inside the portable agent made the portable agent look unportable. They share one Groq implementation — `live_transcribe.py` imports its upload plumbing from `transcribe.py` — so the folders must stay siblings.

### Why not just use Otter or Granola

Honest version, because it decides when to reach for these and when not to:

**What these do that the SaaS tools don't.** Output is Markdown in your own filesystem (`~/Desktop/Claude Outputs/`), not rows in someone's cloud you have to export from. Transcription is free (Groq Whisper) and every call is cost-attributed through the Cloudflare AI Gateway. Most importantly, the notes step runs a strict **anti-fabrication standard** that hosted transcribers do not: never invent a speaker name, `[inaudible]` rather than a plausible guess, `*[speaker unclear]*` on genuinely ambiguous turns, and a header stating plainly that labels are inferred from context rather than heard from the audio. A confidently wrong label fabricates a quote — that risk is the whole reason the rule exists.

**Where Otter and Granola still win.** They do real diarization from the audio; this stack infers turns from context and says so. They capture zero-touch off your calendar; this one you invoke. They keep a searchable history across every meeting you've ever had. For everyday meeting capture, Granola is the tool in use, and this stack is the one to reach for when a transcript needs to become a *deliverable* rather than a record.

The gap worth closing is the **Transcript Router** in the planned table above. Today both transcribers dead-end at a notes file; nothing carries a transcript into `intel/`, `brand-pack/`, or the competitive researcher. That handoff is the one thing a hosted transcriber structurally cannot do, because Otter and Granola have no view of the rest of this repo — which makes it the differentiator worth building, rather than trying to out-transcribe them at transcription.

## How the agents fit together

The practitioner stack has four layers ([the framing](https://www.linkedin.com/in/jimmypark/) big-brand operators use: three you can buy, one they build). This repo's answer to each:

| Layer | The job | Buyable as | Here |
|---|---|---|---|
| 1. Search fundamentals | Rankings, keywords, technical site health | Semrush, Ahrefs, Screaming Frog | SEO Performance Monitor + Site Auditor. Search volumes and backlink indexes can't be replicated free; own-site backlinks come from the GSC Links export, and the paid trigger is documented in the [Site Auditor README](agents/site-auditor/README.md) |
| 2. What models say | How a brand is described and recommended in LLM answers | Profound, PromptWatch | AI Brand Auditor: the layer big brands buy, built as a 4-subagent pipeline. Productized in its own private repo; this repo keeps the free supporting layers |
| 3. Context files + agents | Client positioning, decision factors, competitor set, feeding agent research passes | (proprietary per team) | The architecture exists (`brand-pack/`, `intel/`, config, subagents); the client intake guide moved to the private auditor repo with the pipeline |
| 4. Crawling + data processing | Competitor site corpora → content gaps, decision factors, citation references | Nobody sells it; teams build it | The Site Auditor's corpus design (`--full-text`) is the collection half; the Competitor Content Analyzer (planned) is the analysis half |

How they connect: layer 2 finds the problem ("models recommend competitors"), layer 4 explains it and prescribes the fix ("here's the content they cite that you don't have"), layer 3 is the client knowledge both need, and layer 1 is the ground floor. A site AI crawlers can't read can't be cited at all.

## Quickstart

Symlink an agent into the skills directory, then ask for the job in plain language ("audit example.com", "build a battlecard for Klue"):

```bash
ln -s ~/github/marketing-agents/agents/site-auditor ~/.claude/skills/site-auditor
```

The repo stays the source of truth — edits here are live everywhere the skill runs. Agents with subagents (the Site Auditor's analyst) load from this repo's `.claude/agents/`, so run those with the repo root as the working directory.

## Layout

| Directory | What lives there |
|---|---|
| `agents/` | Every agent, one folder each: `SKILL.md` (the auto-trigger front door) + `README.md` (the design writeup), whether the work behind it is one skill or a multi-agent pipeline |
| `.claude/agents/` | Subagent definitions Claude Code loads when running from this repo |
| `brand-pack/` | Positioning, voice rules, ICPs — the input layer for the Copywriter |
| `intel/` | Existing competitive intel; one folder per competitor |
| `sample-data/` | Synthetic datasets for demos |
| `outputs/` | Public demo artifacts produced by the agents |

## Conventions

- API keys live in `~/.marketing-agents.env` — never in this repo. Client-site run data is gitignored.
- Every AI API call routes through the Cloudflare AI Gateway (setup documented in [`ai-architecture`](https://github.com/d-walia/ai-architecture/tree/main/cloudflare-ai-gateway)), so every run has a visible, attributable cost.
- Deliverables are shareable beyond the repo: agents render self-contained HTML reports the recipient opens with only a browser.
- Retired work is deleted, not kept as dead weight: an earlier single-script Python prototype of the Brand Auditor gave way to the multi-agent version, which now lives in its own private repo.
