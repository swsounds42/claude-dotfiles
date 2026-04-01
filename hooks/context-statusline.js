#!/usr/bin/env node
/**
 * Status line: shows context window health at the bottom of Claude Code.
 * Reads the current session JSONL and extracts token usage.
 * Runs on every render — must be fast (<100ms).
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

const LIMIT = 1_000_000; // Opus context window

function findCurrentSession() {
  const projectsDir = path.join(os.homedir(), ".claude", "projects");
  if (!fs.existsSync(projectsDir)) return null;

  let newest = null;
  let newestMtime = 0;

  // Walk one level of project dirs
  for (const proj of fs.readdirSync(projectsDir)) {
    const projPath = path.join(projectsDir, proj);
    if (!fs.statSync(projPath).isDirectory()) continue;

    for (const file of fs.readdirSync(projPath)) {
      if (!file.endsWith(".jsonl")) continue;
      const filePath = path.join(projPath, file);
      const mtime = fs.statSync(filePath).mtimeMs;
      if (mtime > newestMtime) {
        newestMtime = mtime;
        newest = filePath;
      }
    }
  }
  return newest;
}

function getUsage(sessionPath) {
  const content = fs.readFileSync(sessionPath, "utf-8");
  const lines = content.split("\n");

  let lastUsage = null;
  let turns = 0;

  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const record = JSON.parse(line);
      if (record.type !== "assistant") continue;
      turns++;
      if (record.message && record.message.usage) {
        lastUsage = record.message.usage;
      }
    } catch {
      continue;
    }
  }

  if (!lastUsage) return null;

  const input = lastUsage.input_tokens || 0;
  const cacheCreation = lastUsage.cache_creation_input_tokens || 0;
  const cacheRead = lastUsage.cache_read_input_tokens || 0;
  const total = input + cacheCreation + cacheRead;

  return { total, turns };
}

function statusIcon(pct) {
  if (pct >= 75) return "●";  // green dot
  if (pct >= 60) return "◐";  // half dot (amber)
  if (pct >= 40) return "○";  // empty dot (red)
  return "✕";                  // critical
}

try {
  const session = findCurrentSession();
  if (!session) {
    process.stdout.write("");
    process.exit(0);
  }

  const usage = getUsage(session);
  if (!usage) {
    process.stdout.write("");
    process.exit(0);
  }

  const pct = Math.round(((LIMIT - usage.total) / LIMIT) * 100);
  const used = Math.round(usage.total / 1000);
  const icon = statusIcon(pct);

  process.stdout.write(`${icon} ${pct}% ctx (${used}k tok, ${usage.turns} turns)`);
} catch {
  process.stdout.write("");
}
