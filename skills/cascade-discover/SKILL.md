---
name: cascade-discover
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

### Schedule it

```bash
# weekly via the schedule skill
schedule "weekly cascade discover" "python3 ~/.claude/skills/cascade-discover/discover.py --save"
```

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
