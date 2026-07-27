# Marketing Agents MCP

Serves the skills in this repo over the Model Context Protocol, so someone can
install them by pasting a URL into Claude instead of cloning the repo, fixing
paths, and re-pulling every time something changes.

The idea is [MKT1's](https://newsletter.mkt1.co/): an MCP doesn't have to wrap a
product. It can distribute methodology. These skills *are* the product.

## What it exposes

| Tool | Returns |
|---|---|
| `list_skills` | The menu — every skill with its description and what it ships |
| `get_skill` | A skill's full `SKILL.md`, which Claude then follows |
| `get_script` | Python source for skills that run local scripts |
| `get_resource` | Subagent definitions, config files, READMEs |

Four skills: `ai-brand-auditor`, `competitive-intel-researcher`,
`meeting-transcriber`, `live-meeting-transcriber`.

**`seo-performance-monitor` is deliberately excluded** — it stays private for
client work. The exclusion lives in `INCLUDE` at the top of
[`scripts/bundle.mjs`](scripts/bundle.mjs).

## What this can and can't carry

MCP distributes *instructions* perfectly and *local file access* not at all.

| Skill | Works for someone who only has the MCP? |
|---|---|
| `competitive-intel-researcher` | ✅ Fully — pure methodology, no scripts |
| `ai-brand-auditor` | ⚠️ Skill, subagents, and scripts all transfer; they supply their own API keys and Cloudflare AI Gateway env |
| `meeting-transcriber` | ⚠️ Script transfers, but they run it locally with their own `GROQ_API_KEY` |
| `live-meeting-transcriber` | ⚠️ Also needs ffmpeg, and BlackHole for both sides of a call |

Nothing here executes anything on the server or supplies keys. It hands over
instructions and source; the recipient runs what they choose to run.

## Architecture

A plain Cloudflare Worker — no Durable Objects, no KV, no bindings, so it fits
the free tier. Skills are compiled into the bundle at build time by
`scripts/bundle.mjs`, so requests are answered from memory with no file access
or external fetches.

Transport is Streamable HTTP: `POST /mcp` with JSON-RPC. Server-initiated
streams aren't offered, so `GET /mcp` returns 405 — which the spec permits.
`src/content.ts` is generated and gitignored; `npm run deploy` regenerates it.

## Local development

```bash
npm install
npm run dev            # bundles, then serves on localhost:8787
```

Exercise it without a client:

```bash
curl -s -X POST localhost:8787/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_skills","arguments":{}}}'
```

## Deploying

```bash
npm run deploy         # bundles, then wrangler deploy
```

**The update loop:** edit a `SKILL.md` → `npm run deploy`. Anyone who installed
the connector gets the new version on their next call. Nothing to re-send, no
version drift — the problem that makes sharing skills through git tedious.

## Access control

By default the endpoint is **open to anyone with the URL**. The URL is
unguessable, but it isn't a secret, and these skills come from a private repo.
To require a shared token:

```bash
npx wrangler secret put MCP_TOKEN
```

Once set, requests need `Authorization: Bearer <token>`. Note that Claude's
custom-connector UI may not offer a header field, so the practical options are
an unguessable URL, or moving to OAuth if this ever needs real access control.

## Installing it in Claude

Settings → Connectors → Add custom connector → paste `https://<worker-url>/mcp`.

No directory approval is needed for a custom connector by URL; approval only
matters for appearing in the public connector list.

Then: *"what skills do you have from marketing-agents?"*
