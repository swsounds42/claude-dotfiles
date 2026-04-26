---
name: cascade-brain
description: Discovery + editorial engine for Cascade — runs `gh search` across multiple queries, fetches curated awesome-lists, cross-checks against installed inventory, and editorializes each candidate (HIGH/MED/SKIP with rationale). Also includes utility subcommands for skill description sharpening, telemetry stats, audit, rebuild, trace. TRIGGER when user mentions "cascade brain", "cascade analysis", "deep skill research", "what should I install next", "skill audit", "sharpen description", "lurking skills", "rebuild index", "trace routing", "why didn't X fire", "cascade health". SKIP: quick gh-only search (use cascade-discover), one-off code edits to hook files (use direct edits).
---

# Cascade Brain — discovery, editorial, and tuning

The companion to `cascade-discover`. Where discover is fast/breadth (gh search → ranked list), **brain is depth + editorial** — pulls in curated awesome-lists, cross-references against installed inventory, and produces a thoughtful HIGH/MED/SKIP table with rationale.

## Primary command — `analyze`

```bash
python3 ~/.claude/skills/cascade-brain/brain.py analyze [--top 30] [--min-stars 30]
```

Outputs a research brief with three sections:

1. **GitHub search candidates** (via `cascade-discover --json`) — top N repos ranked by stars × recency, already cross-checked against installed inventory, with `closest_installed` annotation per candidate (heuristic redundancy hint)
2. **Curated awesome-lists** to fetch — URLs to `hesreallyhim/awesome-claude-code`, `wshobson/agents`, `ComposioHQ/awesome-claude-skills`, etc.
3. **Editorial framing for Claude** — explicit instructions to bucket every candidate into HIGH / MED / SKIP with one-line rationale, scoped to your RevOps/sales workflow

### Workflow when invoked

When you (Claude) run `cascade-brain analyze`:

1. The script outputs the structured brief to stdout
2. **You** then `WebFetch` each curated list URL listed in section 2
3. Parse those READMEs for repos NOT in the inventory list
4. Merge: gh-search candidates + curated-list net-new entries
5. For each candidate, decide:
   - **HIGH** = net-new gap-filler, recommend installing
   - **MED** = complement to existing skill X, worth watching
   - **SKIP** = redundant / niche / stale / low-quality
6. Save the final markdown report to `~/.claude/discover-reports/analysis-<date>.md`

The script is data infrastructure; **the editorial reasoning is yours**.

## Secondary command — `sharpen`

Improve a SKILL.md description using the `TRIGGER when:` / `SKIP:` pattern.

### Inspect mode (default)
```bash
python3 ~/.claude/skills/cascade-brain/brain.py sharpen <skill-name>
```
Outputs the current description, score, body excerpt, and a template. You read it, draft a sharpened version.

### Apply mode
```bash
python3 ~/.claude/skills/cascade-brain/brain.py sharpen <skill-name> --apply "description: New text. TRIGGER when..."
```
Writes the new description to the SKILL.md, prints before/after score. Run `cascade-brain rebuild` afterward to refresh the index.

### Workflow
1. `cascade-brain audit --weak-only` to find candidates
2. For each weak skill: `cascade-brain sharpen <name>` to read context
3. Draft new description following the template (one line, includes `TRIGGER when` quoted phrases and `SKIP:` alternatives)
4. `cascade-brain sharpen <name> --apply "<new desc>"` to write
5. `cascade-brain rebuild` once batch is done

## Utility subcommands

| Command | What it does |
|---|---|
| `audit [--weak-only] [--top N]` | Score every SKILL.md for length / TRIGGER / SKIP / name-in-desc |
| `stats [--lurkers]` | Top recommendations from `skill-recommendations.jsonl` + lurking skills |
| `rebuild` | Re-init the intelligence index (run after sharpen edits) |
| `health` | Index size, telemetry events, patterns, hook status |
| `trace "prompt"` | Run a prompt through the route hook live — see exactly what fires |

## When to invoke

**Use this skill when:**
- "what should I install next" / "do a deep cascade analysis" / "research new claude tools" → `analyze`
- "sharpen X" / "fix the description for X" / "audit weak skills" → `sharpen` / `audit`
- "why didn't X fire" / "trace routing for Y" → `trace`
- "cascade health" / "rebuild index" / "lurking skills" → `health` / `rebuild` / `stats`

**Skip when:**
- Quick gh-only search without editorial → use `cascade-discover` directly
- One-off code edit to hooks → just edit
- Installing a specific named skill → use the existing install flow

## Schedule weekly analysis

```bash
schedule "weekly cascade analysis" "python3 ~/.claude/skills/cascade-brain/brain.py analyze --top 50 > ~/.claude/discover-reports/weekly-$(date +%F).md"
```
Then on Friday morning Claude reviews the file and produces the editorial report.

## Files this skill touches

| Path | Role |
|---|---|
| `~/.claude/skills/cascade-discover/discover.py` | Invoked via `--json` for candidate generation |
| `~/Desktop/personal-os-main/.cascade/intelligence/skill-recommendations.jsonl` | Telemetry (read by `stats`) |
| `~/Desktop/personal-os-main/.cascade/intelligence/ranked-context.json` | Index metadata (read by `health`) |
| `~/Desktop/personal-os-main/scripts/hooks/intelligence.cjs` | Re-init on `rebuild` |
| `~/Desktop/personal-os-main/scripts/hooks/hook-handler.cjs` | Route handler (invoked by `trace`) |
| `~/.claude/skills/*/SKILL.md` | Read by `audit`; **modified** by `sharpen --apply` |

`sharpen --apply` is the only command that writes to skill files. Everything else is read-only.
