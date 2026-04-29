#!/usr/bin/env node
/**
 * rtk-bootstrap.js — Cascade SessionStart hook
 *
 * Drops .rtk/filters.toml into Sam-owned git repos that don't have one.
 * Sources the canonical filter content from the user-global RTK filters file.
 *
 * Safety profile:
 *   - Only acts when cwd is inside a git repo
 *   - Only acts when origin URL matches a known Sam owner (no polluting external repos)
 *   - No-op if .rtk/filters.toml already exists (idempotent across resumes)
 *   - Never commits — file shows as untracked, you decide
 *   - Silent unless action is taken
 *
 * To disable: remove the SessionStart entry in ~/.claude/settings.json.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SAM_OWNERS = [
  'swsounds42',
  'swsounds',
  'homebot-labs',
  'homebot.ai',
  'sam-warren',
  'samwarren',
];

const SOURCE_FILE = path.join(
  process.env.HOME,
  'Library',
  'Application Support',
  'rtk',
  'filters.toml',
);

function safeExec(cmd, opts = {}) {
  try {
    return execSync(cmd, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], ...opts }).trim();
  } catch {
    return null;
  }
}

function readPayload() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return JSON.parse(raw || '{}');
  } catch {
    return {};
  }
}

function main() {
  const payload = readPayload();
  const cwd = payload.cwd || process.cwd();

  // 1. Must be a git repo
  const topLevel = safeExec('git rev-parse --show-toplevel', { cwd });
  if (!topLevel || !fs.existsSync(topLevel)) return;

  // 2. Already has filters? No-op.
  const target = path.join(topLevel, '.rtk', 'filters.toml');
  if (fs.existsSync(target)) return;

  // 3. Check origin ownership — stay out of external repos
  const originUrl = safeExec('git remote get-url origin', { cwd: topLevel });
  if (!originUrl) return; // no origin → skip rather than guess
  const ownsThis = SAM_OWNERS.some((o) =>
    originUrl.toLowerCase().includes(o.toLowerCase()),
  );
  if (!ownsThis) return;

  // 4. Need source file to copy from
  if (!fs.existsSync(SOURCE_FILE)) return;

  // 5. Drop the file (no commit — let Sam decide)
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(SOURCE_FILE, target);

  // 6. Brief notice (goes to transcript, not Claude's context)
  process.stderr.write(
    `[rtk-bootstrap] created .rtk/filters.toml in ${path.basename(topLevel)} (untracked — commit when ready)\n`,
  );
}

main();
