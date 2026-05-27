---
name: cascade-discover
version: 1.1.0
description: Discover new Claude Code skills/agents/hooks/plugins/MCP servers ranked by stars × recency, auto-excluding what's already installed. Use when the user asks "what new Claude tools should I install?", "discover new skills", "what's hot in the Claude ecosystem?", or "scan GitHub for Claude-Code stuff worth adding."
---

# Cascade Discover

Find new Claude Code tooling without re-recommending what's already in the stack.

## When to invoke

- "What new Claude Code tools should I install?"
- "Discover new skills / agents / hooks"
- "Cascade discover"
- "What's new in the Claude ecosystem?"
- Weekly periodic check (recommended)

## How it works

1. **Inventory** — scans `~/.claude/repos/`, `~/.claude/plugins/marketplaces/`, all skill/agent/command symlinks, and `known_marketplaces.json`. Resolves each to a GitHub `owner/name` via `.git/config`. Builds the installed-set.
2. **Discovery** — runs `gh search repos` against 9 default queries (claude-code skills/agents/hooks/plugin, mcp-server productivity, awesome lists, agentic personal os, etc.).
3. **Crosscheck** — filters out anything in the installed-set.
4. **Rank** — scores each by `stars × exp(-days_since_push / 90)`. Recent + popular wins; old high-star repos decay.
5. **Render** — markdown table with rank, repo, stars, last push, score, description.

## Invocation

```bash
python3 ~/.claude/skills/cascade-discover/discover.py
```

### Flags

| Flag | Purpose |
|---|---|
| `--top 50` | Show more results (default 25) |
| `--min-stars 100` | Raise signal floor (default 30) |
| `--queries "rust mcp,llm agents"` | Custom search terms |
| `--inventory-only` | Debug what's detected as installed |
| `--save` | Archive to `~/.claude/discover-reports/<date>.md` |
| `--save path.md` | Save to specific path |
| `--limit-per-query 50` | More candidates per query (default 30) |
| `--check-updates` | **Freshness mode** — report installed repos that drifted upstream (see below) |
| `--refresh-lock` | Freshness: advance baselines to current (run after you've updated) |
| `--dry-run` | Freshness: probe + report but don't write the lockfile |
| `--mute owner/name` | Freshness: stop tracking a repo (intentional pin) |
| `--unmute owner/name` | Freshness: resume tracking |

### Schedule it

```bash
# weekly via the schedule skill
schedule "weekly cascade discover" "python3 ~/.claude/skills/cascade-discover/discover.py --save"
```

## Freshness mode (`--check-updates`)

Discovery finds *net-new* tooling and throws away anything installed. Freshness asks the
opposite question: **of the repos I already have, which shipped upstream changes since my
baseline?** Answers "am I running stale skills/agents?"

```bash
python3 ~/.claude/skills/cascade-discover/discover.py --check-updates          # report drift
python3 ~/.claude/skills/cascade-discover/discover.py --check-updates --json   # for brain analyze
python3 ~/.claude/skills/cascade-discover/discover.py --check-updates --refresh-lock  # ack updates
```

How it works:

1. **Inventory** — same installed-set as discovery, minus repos Sam authors (owners `swsounds42/*`,
   `swsounds/*`, plus the `own` list in `inventory-extras.json`).
2. **Probe** — for each repo, `gh api` for latest default-branch commit (sha + date) and latest release.
3. **Compare to baseline** — `freshness-lock.json` stores the last-acknowledged sha/release per repo.
   New commits or a new release tag ⇒ **STALE**. Stale rows show commits-behind (`gh compare`) + a diff link.
4. **Baseline lifecycle** — first sight of a repo **seeds** its baseline (not flagged). Baselines only
   **advance** on `--refresh-lock`, so drift keeps nagging until you actually update + acknowledge.
   Uninstalled repos are pruned; `--mute` pins a repo you intentionally hold back.

**Granularity caveat:** this is repo-level, not skill-level. All 95 `gws-*` skills come from one repo
(`googleworkspace/cli`), so a hit reads "googleworkspace/cli: 12 new commits" — a prompt to go look,
not "gws-gmail-triage changed."

`cascade-brain analyze` calls this automatically (non-dry, so the weekly scan seeds/prunes the lock)
and folds an "Updates available" section + a **STALE** editorial bucket into the brief.

## Output

```
# Cascade Discovery Report — 2026-04-26

**Already installed:** 14 repos · **New candidates:** 47 · **Showing top:** 25

| # | Repo | ★ | Last push | Score | Description |
|---|---|---:|---|---:|---|
| 1 | [owner/repo](https://...) | 1,432 | 2026-04-22 | 1,348 | What it does |
```

## Implementation notes

- **Inventory dedup is by GitHub owner/name** (lowercased). Symlinks pointing into a repo subdirectory still resolve to the parent repo via `find_git_root`.
- **Score formula** balances popularity vs freshness — a 1k-star repo last pushed 30 days ago beats a 5k-star repo from 2 years ago.
- **Rate limits** — `gh search` is rate-limited to ~30 req/min for authenticated users. The default 9 queries take ~10 seconds.
- **Saved reports** live at `~/.claude/discover-reports/<date>.md` for trend tracking.
