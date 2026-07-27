#!/usr/bin/env node
/**
 * Bundle the repo's skills into src/content.ts so the Worker can serve them
 * without any runtime file access or external fetches.
 *
 * Run this after editing any SKILL.md, then redeploy — that's the whole
 * update loop. Whoever installed the MCP gets the new version immediately,
 * with nothing to pull or re-clone.
 *
 *   node scripts/bundle.mjs
 */
import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");

// SEO is deliberately excluded — it stays private to Dhruv for client work.
const INCLUDE = [
  "ai-brand-auditor",
  "competitive-intel-researcher",
  "meeting-transcriber",
  "live-meeting-transcriber",
];

// Config/reference files worth shipping alongside a skill, per skill.
const EXTRA_FILES = {
  "ai-brand-auditor": ["config/brand.json", "config/query_grid.json", "config/rubric.md"],
};

// Subagent definitions a skill dispatches to. Without these the auditor
// pipeline can't be reconstructed on someone else's machine.
const SUBAGENTS = {
  "ai-brand-auditor": [
    "audit-query-runner",
    "audit-perception-scorer",
    "audit-rubric-grader",
    "audit-reporter",
  ],
};

/**
 * The skills are written for their author — "Use whenever Dhruv asks…" — which
 * helps them trigger locally but reads oddly for anyone else. Rewrite to a
 * neutral second person for the shared copy only; the repo's SKILL.md files
 * are never modified.
 *
 * Explicit pairs rather than clever regex: verb agreement ("he names" →
 * "they name") is easy to get wrong automatically, and a wrong rewrite is
 * worse than none. Anything missed is caught by the leak check below.
 */
const NEUTRALIZE = [
  // Compound clauses first: "when he names X and asks Y" needs BOTH verbs
  // de-conjugated, and the simpler rule below would only catch the first.
  // The (?:\w+\s+)*? allows adverbs — "when he *just* drags … and asks".
  [
    /\bwhen he ((?:\w+\s+)*?)(\w+?)s\b([^.]*?)\band asks\b/g,
    (_m, adv, verb, mid) => `when they ${adv}${verb}${mid}and ask`,
  ],
  [/\bwhen he ((?:\w+\s+)*?)(\w+?)s\b/g, (_m, adv, verb) => `when they ${adv}${verb}`],
  [/\bDhruv's\b/g, "the user's"],
  [/\bDhruv\b(?=\s+(?:asks?|says?|mentions?|wants?|requests?))/g, "the user"],
  [/\bhe asks\b/g, "they ask"],
  [/\bhe names\b/g, "they name"],
  [/\bhe mentions\b/g, "they mention"],
  [/\bhe says\b/g, "they say"],
  [/\bhis\b/g, "their"],
  [/\bhim\b/g, "them"],
  // Links into the author's private repos 404 for everyone else. Swap the
  // gateway reference for the public vendor docs, and degrade any other
  // private link to its text so no broken URL ships.
  [
    /documented in the \[`ai-architecture`\]\([^)]+\) repo/g,
    "documented in Cloudflare's AI Gateway docs (https://developers.cloudflare.com/ai-gateway/)",
  ],
  [/\[([^\]]+)\]\(https:\/\/github\.com\/d-walia\/[^)]*\)/g, "$1"],
];

/**
 * Checked against the ORIGINAL text, before any rewriting.
 *
 * The formulaic "Use whenever Dhruv asks…" is safe to rewrite automatically.
 * Anything richer — a full name, an email, a personal aside — is not: the
 * catch-all would produce mangled prose like "the user Walia keeps their
 * recordings" and no post-hoc check could tell that apart from a clean
 * rewrite. So these stop the build and ask a human to reword instead.
 */
const NEEDS_HUMAN = [
  [/\bDhruv\s+Walia\b/i, "full name — reword the sentence generically"],
  [/\bWalia\b/i, "surname — reword the sentence generically"],
  [/[\w.+-]+@[\w-]+\.[\w.]+/, "email address"],
  [/\bdw-digital-consulting\b/i, "personal domain"],
];

// Checked AFTER rewriting: anything here means a rule was missed entirely.
const LEAK_PATTERNS = [/\bDhruv\b/i, /\bWalia\b/i, /\bhe\b/, /\bhis\b/, /\bhim\b/];

const humanNeeded = [];

/** Rewrite for a general audience, flagging anything too personal to automate. */
function neutralize(label, s) {
  if (typeof s !== "string") return s;

  let out = s;
  for (const [pattern, replacement] of NEUTRALIZE) out = out.replace(pattern, replacement);

  // Check the REWRITTEN text: whatever the rules handled is fine, and only
  // what survives needs a human. Checking the original would flag cases the
  // rules already fix.
  for (const line of out.split("\n")) {
    for (const [pattern, why] of NEEDS_HUMAN) {
      if (pattern.test(line)) {
        humanNeeded.push(`${label}: ${why}\n      ${line.trim().slice(0, 100)}`);
        break;
      }
    }
  }
  return out;
}

function findLeaks(label, s) {
  if (typeof s !== "string") return [];
  const leaks = [];
  for (const line of s.split("\n")) {
    for (const p of LEAK_PATTERNS) {
      if (p.test(line)) {
        leaks.push(`${label}: ${line.trim().slice(0, 110)}`);
        break;
      }
    }
  }
  return leaks;
}

function frontmatter(md) {
  const m = md.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return {};
  const out = {};
  // Only need name/description; values may wrap, so join continuation lines.
  let key = null;
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([a-zA-Z_-]+):\s*(.*)$/);
    if (kv) {
      key = kv[1];
      out[key] = kv[2].trim();
    } else if (key && line.trim()) {
      out[key] += " " + line.trim();
    }
  }
  return out;
}

const skills = [];

for (const slug of INCLUDE) {
  const dir = join(REPO, "agents", slug);
  const skillPath = join(dir, "SKILL.md");
  if (!existsSync(skillPath)) {
    console.error(`  ! skipping ${slug} — no SKILL.md`);
    continue;
  }
  const md = readFileSync(skillPath, "utf8");
  const fm = frontmatter(md);

  const scriptsDir = join(dir, "scripts");
  const scripts = {};
  if (existsSync(scriptsDir)) {
    for (const f of readdirSync(scriptsDir)) {
      if (f.endsWith(".py")) scripts[f] = readFileSync(join(scriptsDir, f), "utf8");
    }
  }

  const files = {};
  for (const rel of EXTRA_FILES[slug] ?? []) {
    const p = join(dir, rel);
    if (existsSync(p)) files[rel] = readFileSync(p, "utf8");
  }

  const agents = {};
  for (const a of SUBAGENTS[slug] ?? []) {
    const p = join(REPO, ".claude", "agents", `${a}.md`);
    if (existsSync(p)) agents[a] = readFileSync(p, "utf8");
  }

  const readmePath = join(dir, "README.md");

  const neutralAgents = {};
  for (const [k, v] of Object.entries(agents)) neutralAgents[k] = neutralize(`${slug}/${k}`, v);

  skills.push({
    name: slug,
    description: neutralize(`${slug}/description`, fm.description ?? ""),
    skill: neutralize(`${slug}/SKILL.md`, md),
    readme: existsSync(readmePath) ? neutralize(`${slug}/README.md`, readFileSync(readmePath, "utf8")) : null,
    scripts, // code, not prose — left byte-identical
    files,
    agents: neutralAgents,
  });

  const counts = [
    `${Object.keys(scripts).length} scripts`,
    `${Object.keys(files).length} config`,
    `${Object.keys(agents).length} subagents`,
  ].join(", ");
  console.log(`  ✓ ${slug.padEnd(30)} ${counts}`);
}

// Content too personal to rewrite safely — a human has to reword it.
if (humanNeeded.length) {
  console.error(`\n✗ ${humanNeeded.length} passage(s) need rewording by hand:\n`);
  for (const h of humanNeeded) console.error(`   ${h}\n`);
  console.error("Auto-rewriting these would produce mangled prose. Edit the source, then re-run.");
  process.exit(1);
}

// Fail loudly rather than shipping a personal reference. If this fires, a
// NEUTRALIZE rule is missing entirely.
const allLeaks = [];
for (const s of skills) {
  allLeaks.push(...findLeaks(`${s.name}/description`, s.description));
  allLeaks.push(...findLeaks(`${s.name}/SKILL.md`, s.skill));
  if (s.readme) allLeaks.push(...findLeaks(`${s.name}/README.md`, s.readme));
  for (const [k, v] of Object.entries(s.agents)) allLeaks.push(...findLeaks(`${s.name}/${k}`, v));
}
if (allLeaks.length) {
  console.error(`\n✗ ${allLeaks.length} personal reference(s) survived neutralization:\n`);
  for (const l of allLeaks) console.error(`   ${l}`);
  console.error("\nReword the skill, or add a rule to NEUTRALIZE in this file.");
  process.exit(1);
}
console.log("  ✓ no personal references leaked");

const out = `// GENERATED by scripts/bundle.mjs — do not edit by hand.
// Regenerate with: node scripts/bundle.mjs
// Source of truth is the SKILL.md files in ../agents/.
export const GENERATED_AT = ${JSON.stringify(new Date().toISOString())};
export const SKILLS = ${JSON.stringify(skills, null, 2)} as const;
`;

writeFileSync(join(HERE, "..", "src", "content.ts"), out);
const kb = (Buffer.byteLength(out) / 1024).toFixed(0);
console.log(`\nWrote src/content.ts — ${skills.length} skills, ${kb} KB`);
