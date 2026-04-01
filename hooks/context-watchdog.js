#!/usr/bin/env node
/**
 * PostToolUse hook: warns when context window crosses a threshold.
 * Only outputs text when there's something actionable — silent otherwise.
 * Tracks last-warned threshold in a temp file to avoid spam.
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

const LIMIT = 1_000_000;
const STATE_FILE = path.join(os.tmpdir(), "claude-context-watchdog.json");

const THRESHOLDS = [
  { pct: 40, level: "AMBER", msg: "Context at 60% — wrapping up large tasks is wise." },
  { pct: 25, level: "RED", msg: "Context at 75% — consider saving state for a fresh session." },
  { pct: 15, level: "CRITICAL", msg: "Context at 85% — save work now. Exhaustion is close." },
];

function findCurrentSession() {
  const projectsDir = path.join(os.homedir(), ".claude", "projects");
  if (!fs.existsSync(projectsDir)) return null;

  let newest = null;
  let newestMtime = 0;

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

function getContextPct(sessionPath) {
  const content = fs.readFileSync(sessionPath, "utf-8");
  const lines = content.split("\n");

  let lastUsage = null;
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const record = JSON.parse(line);
      if (record.type !== "assistant") continue;
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

  return Math.round(((LIMIT - total) / LIMIT) * 100);
}

function getLastWarned() {
  try {
    const data = JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"));
    return data.lastLevel || null;
  } catch {
    return null;
  }
}

function setLastWarned(level) {
  fs.writeFileSync(STATE_FILE, JSON.stringify({ lastLevel: level, ts: Date.now() }));
}

try {
  const session = findCurrentSession();
  if (!session) process.exit(0);

  const pctRemaining = getContextPct(session);
  if (pctRemaining === null) process.exit(0);

  const lastWarned = getLastWarned();

  // Find the most severe threshold we've crossed
  let triggered = null;
  for (const t of THRESHOLDS) {
    if (pctRemaining <= t.pct) {
      triggered = t;
    }
  }

  if (!triggered) process.exit(0);

  // Only warn once per threshold level
  const severity = THRESHOLDS.map((t) => t.level);
  const lastIdx = lastWarned ? severity.indexOf(lastWarned) : -1;
  const currentIdx = severity.indexOf(triggered.level);

  if (currentIdx <= lastIdx) process.exit(0);

  setLastWarned(triggered.level);
  process.stdout.write(`\n⚠️  [${triggered.level}] ${triggered.msg}\n`);
} catch {
  // Silent failure — never block the user's workflow
  process.exit(0);
}
