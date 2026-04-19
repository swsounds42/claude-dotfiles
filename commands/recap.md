---
description: "Recap what you worked on recently. Queries Jarvis's observation layer, analyzes themes, renders a markdown digest. Example: /recap 4h or /recap today."
model: haiku
---

# /recap — Session Recap Orchestrator

You are a lightweight orchestrator for a Command → Agent → Skill workflow. Your job is only to coordinate — you don't analyze observations yourself.

## Workflow

1. **Parse the time window from `$ARGUMENTS`.** Defaults if empty:
   - `4h` or `4 hours` → last 4 hours
   - `today` → since midnight local
   - `week` or `7d` → last 7 days
   - `N hours` / `N days` → literal window
   - No arg → default to `24h`

2. **Invoke the `recap-analyst` agent** via the Agent tool. Pass the parsed time window as context. The agent will:
   - Query Jarvis's observation database for tool calls and subagent outcomes in the window
   - Group by theme (files touched, tools used, subagents spawned)
   - Extract what was worked on and what was shipped

3. **Wait for the agent's structured response.** It should return JSON-ish data about:
   - sessions_covered
   - top_themes (list of theme names + counts)
   - files_touched (list of distinct files + counts)
   - subagents_used (list of agent types + task summaries)
   - notable_observations (any entries that stand out)

4. **Invoke the `recap-formatter` skill** via the Skill tool. Pass the agent's structured response. The skill will render a polished markdown digest suitable for daily notes, Slack, or a personal log.

5. **Return the rendered markdown to the user.** Don't add commentary — the skill output is the answer.

## Critical

- You run on `haiku` to keep orchestration cheap.
- Do NOT query the observation database yourself. That's the agent's job.
- Do NOT format output yourself. That's the skill's job.
- If `$ARGUMENTS` is ambiguous or you can't parse a window, ask the user once for clarification before dispatching.

## Example calls

- `/recap` → 24-hour recap
- `/recap 2h` → last 2 hours (fast morning catch-up)
- `/recap today` → since midnight
- `/recap week` → week in review

## What this demonstrates

This is a Command → Agent → Skill orchestration pattern from the claude-code-best-practice repo:
- **Command** (you, haiku) = cheap orchestration + user interaction
- **Agent** (recap-analyst, sonnet) = domain work with access to observation layer
- **Skill** (recap-formatter) = independent output rendering

Each layer has one responsibility. You coordinate. The agent analyzes. The skill formats.
