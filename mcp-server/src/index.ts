/**
 * Marketing Agents MCP — serves Dhruv's Claude skills over the Model Context
 * Protocol so they can be installed by URL instead of cloned from git.
 *
 * A plain Worker: no Durable Objects, no session state, so it runs on the
 * Cloudflare free tier. Every request is answered from content compiled in at
 * build time (src/content.ts), which makes responses fast and side-effect free.
 *
 * Transport: Streamable HTTP (POST /mcp). Server-initiated streams aren't
 * offered, so GET /mcp returns 405 — the spec explicitly allows that.
 */
import { SKILLS, GENERATED_AT } from "./content";

interface Env {
  /** Optional. When set, requests must send `Authorization: Bearer <token>`. */
  MCP_TOKEN?: string;
}

// Versions this server knows how to speak. The client's choice is echoed back
// when we recognize it, otherwise we answer with our preferred version and let
// the client decide whether to proceed.
const SUPPORTED_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"];
const PREFERRED_VERSION = "2025-06-18";

const SERVER_INFO = { name: "marketing-agents", version: "1.0.0" };

type Json = Record<string, unknown>;

const TOOLS = [
  {
    name: "list_skills",
    description:
      "List the marketing agent skills available here, with a one-line summary of each. " +
      "Call this first when asked what this server can do, or when choosing which skill fits a task.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_skill",
    description:
      "Fetch the full instructions for one skill. Returns the complete methodology — " +
      "pipeline, verification rules, output format — which you should then follow. " +
      "Use after list_skills, or directly when the skill name is known.",
    inputSchema: {
      type: "object",
      properties: {
        name: {
          type: "string",
          description: "Skill name, e.g. 'competitive-intel-researcher'",
          enum: SKILLS.map((s) => s.name),
        },
      },
      required: ["name"],
      additionalProperties: false,
    },
  },
  {
    name: "get_script",
    description:
      "Fetch the source of a Python script a skill depends on. Some skills run local " +
      "scripts (transcription, API collection); this returns the source so it can be " +
      "written to disk and run locally. Call list_skills first to see which scripts exist.",
    inputSchema: {
      type: "object",
      properties: {
        skill: { type: "string", description: "Skill the script belongs to", enum: SKILLS.map((s) => s.name) },
        script: { type: "string", description: "Filename, e.g. 'transcribe.py'" },
      },
      required: ["skill", "script"],
      additionalProperties: false,
    },
  },
  {
    name: "get_resource",
    description:
      "Fetch a supporting file for a skill: a config file (e.g. 'config/brand.json'), " +
      "a subagent definition (e.g. 'audit-query-runner'), or the skill's README. " +
      "Needed to reconstruct multi-agent pipelines. list_skills reports what each skill has.",
    inputSchema: {
      type: "object",
      properties: {
        skill: { type: "string", description: "Skill the resource belongs to", enum: SKILLS.map((s) => s.name) },
        resource: {
          type: "string",
          description: "Config path, subagent name, or 'README'",
        },
      },
      required: ["skill", "resource"],
      additionalProperties: false,
    },
  },
];

function text(s: string): Json {
  return { content: [{ type: "text", text: s }] };
}

function findSkill(name: unknown) {
  if (typeof name !== "string") return undefined;
  const wanted = name.trim().toLowerCase();
  return SKILLS.find((s) => s.name.toLowerCase() === wanted);
}

function skillNames(): string {
  return SKILLS.map((s) => `  - ${s.name}`).join("\n");
}

function callTool(name: string, args: Json): Json {
  if (name === "list_skills") {
    const lines = [
      "# Marketing Agents — available skills",
      "",
      "Each skill is a complete methodology. Fetch one with `get_skill` and follow it.",
      "",
    ];
    for (const s of SKILLS) {
      lines.push(`## ${s.name}`, "", s.description || "_(no description)_", "");
      const scripts = Object.keys(s.scripts);
      const agents = Object.keys(s.agents);
      const files = Object.keys(s.files);
      if (scripts.length) lines.push(`- **Scripts** (via \`get_script\`): ${scripts.join(", ")}`);
      if (agents.length) lines.push(`- **Subagents** (via \`get_resource\`): ${agents.join(", ")}`);
      if (files.length) lines.push(`- **Config** (via \`get_resource\`): ${files.join(", ")}`);
      if (s.readme) lines.push("- **README** available via `get_resource` with `README`");
      lines.push("");
    }
    lines.push(
      "---",
      "",
      "Skills that run local scripts need their own API keys — none are supplied by this server.",
      `Bundled ${GENERATED_AT}.`,
    );
    return text(lines.join("\n"));
  }

  if (name === "get_skill") {
    const s = findSkill(args.name);
    if (!s) return text(`No skill named "${String(args.name)}". Available:\n${skillNames()}`);
    return text(s.skill);
  }

  if (name === "get_script") {
    const s = findSkill(args.skill);
    if (!s) return text(`No skill named "${String(args.skill)}". Available:\n${skillNames()}`);
    const scripts = s.scripts as Record<string, string>;
    const want = String(args.script ?? "").trim();
    const key = Object.keys(scripts).find(
      (k) => k.toLowerCase() === want.toLowerCase() || k.toLowerCase() === `${want.toLowerCase()}.py`,
    );
    if (!key) {
      const avail = Object.keys(scripts);
      return text(
        avail.length
          ? `"${want}" not found in ${s.name}. Available: ${avail.join(", ")}`
          : `${s.name} has no scripts — it runs entirely through Claude.`,
      );
    }
    return text(`# ${s.name}/scripts/${key}\n\n\`\`\`python\n${scripts[key]}\n\`\`\``);
  }

  if (name === "get_resource") {
    const s = findSkill(args.skill);
    if (!s) return text(`No skill named "${String(args.skill)}". Available:\n${skillNames()}`);
    const want = String(args.resource ?? "").trim();

    if (/^readme$/i.test(want)) {
      return text(s.readme ?? `${s.name} has no README.`);
    }
    const agents = s.agents as Record<string, string>;
    const agentKey = Object.keys(agents).find(
      (k) => k.toLowerCase() === want.toLowerCase() || `${k}.md`.toLowerCase() === want.toLowerCase(),
    );
    if (agentKey) return text(agents[agentKey]);

    const files = s.files as Record<string, string>;
    const fileKey = Object.keys(files).find(
      (k) => k.toLowerCase() === want.toLowerCase() || k.toLowerCase().endsWith(`/${want.toLowerCase()}`),
    );
    if (fileKey) return text(`# ${s.name}/${fileKey}\n\n\`\`\`\n${files[fileKey]}\n\`\`\``);

    const options = [
      ...Object.keys(agents),
      ...Object.keys(files),
      ...(s.readme ? ["README"] : []),
    ];
    return text(
      options.length
        ? `"${want}" not found in ${s.name}. Available: ${options.join(", ")}`
        : `${s.name} has no supporting resources.`,
    );
  }

  throw { code: -32601, message: `Unknown tool: ${name}` };
}

function handleRpc(msg: Json): Json | null {
  const { method, id, params } = msg as { method?: string; id?: unknown; params?: Json };

  // Notifications carry no id and get no response body.
  if (id === undefined || id === null) return null;

  const reply = (result: Json): Json => ({ jsonrpc: "2.0", id, result });
  const fail = (code: number, message: string): Json => ({
    jsonrpc: "2.0",
    id,
    error: { code, message },
  });

  try {
    switch (method) {
      case "initialize": {
        const asked = (params?.protocolVersion as string) ?? "";
        return reply({
          protocolVersion: SUPPORTED_VERSIONS.includes(asked) ? asked : PREFERRED_VERSION,
          capabilities: { tools: { listChanged: false } },
          serverInfo: SERVER_INFO,
          instructions:
            "Marketing agent skills by Dhruv Walia. Call list_skills to see what's here, " +
            "then get_skill to load a full methodology and follow it. Skills that run " +
            "local scripts expose their source via get_script; you'll need your own API keys.",
        });
      }
      case "ping":
        return reply({});
      case "tools/list":
        return reply({ tools: TOOLS });
      case "tools/call": {
        const toolName = params?.name as string;
        const args = (params?.arguments as Json) ?? {};
        if (!toolName) return fail(-32602, "Missing tool name");
        return reply(callTool(toolName, args));
      }
      // Declared unsupported rather than erroring, so clients that probe
      // these during startup get a clean empty list.
      case "resources/list":
        return reply({ resources: [] });
      case "prompts/list":
        return reply({ prompts: [] });
      default:
        return fail(-32601, `Method not found: ${method}`);
    }
  } catch (e: unknown) {
    const err = e as { code?: number; message?: string };
    return fail(err.code ?? -32603, err.message ?? "Internal error");
  }
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
  "Access-Control-Expose-Headers": "Mcp-Session-Id",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    // A human-readable landing page, so hitting the URL in a browser explains
    // itself instead of returning a bare 404.
    if (url.pathname === "/" || url.pathname === "") {
      return new Response(
        [
          "Marketing Agents MCP server",
          "",
          `Skills: ${SKILLS.map((s) => s.name).join(", ")}`,
          `Bundled: ${GENERATED_AT}`,
          "",
          "Add this URL as a custom connector in Claude:",
          `  ${url.origin}/mcp`,
          "",
          "Then ask Claude: \"what skills do you have from marketing-agents?\"",
        ].join("\n"),
        { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8", ...CORS } },
      );
    }

    if (url.pathname !== "/mcp") {
      return json({ error: "Not found. The MCP endpoint is /mcp" }, 404);
    }

    // Optional shared secret. Unset → open; set → required.
    if (env.MCP_TOKEN) {
      const auth = request.headers.get("Authorization") ?? "";
      const supplied = auth.replace(/^Bearer\s+/i, "").trim();
      if (supplied !== env.MCP_TOKEN) {
        return json({ error: "Unauthorized" }, 401);
      }
    }

    // No server-initiated streams; the spec allows declining the GET stream.
    if (request.method === "GET") {
      return new Response("This server does not offer an SSE stream. POST JSON-RPC to /mcp.", {
        status: 405,
        headers: { Allow: "POST, OPTIONS", ...CORS },
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "POST, OPTIONS", ...CORS },
      });
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400);
    }

    // A batch of messages gets a batch of responses; notification-only
    // batches get 202 with no body.
    if (Array.isArray(body)) {
      const results = body.map((m) => handleRpc(m as Json)).filter((r): r is Json => r !== null);
      return results.length ? json(results) : new Response(null, { status: 202, headers: CORS });
    }

    const result = handleRpc(body as Json);
    return result ? json(result) : new Response(null, { status: 202, headers: CORS });
  },
};
