---
name: efficiency
description: One consolidated Claude/token efficiency dashboard — shells out to codeburn (spend, waste, model compare, yield), rtk (proxy savings), the model-router (routing mix), and cascade-brain (weak/dead skills), then synthesizes a single read. TRIGGER when user mentions "token efficiency", "where are my tokens going", "claude efficiency check", "token waste", "model usage", "routing mix", "efficiency dashboard", "am I wasting tokens", "claude code health". SKIP: tuning a single skill's description (use cascade-brain sharpen), compressing Claude's output (use caveman), discovering new tools to install (use cascade-discover).
---

# Efficiency — one consolidated token/efficiency dashboard

A thin orchestrator. It does **not** re-implement any analytics — it shells out to the CLIs you already have (`codeburn`, `rtk`, the model-router, `cascade-brain`) via one script, then **you** synthesize the raw feed into a single read. The skill body stays deliberately thin: the script gathers, the model reasons.

## Primary command

```bash
bash ~/.claude/skills/efficiency/dashboard.sh          # FAST — 5 sections, safe to run anytime
bash ~/.claude/skills/efficiency/dashboard.sh --deep   # FAST panel + 3 heavy codeburn analyses (slow)
```

**Fast panel** (always): spend (codeburn 30d), proxy savings (rtk), model routing mix, skill-stack health (weak/dead descriptions), enforcement-layer presence checks (router / RTK / caveman).
**Deep panel** (`--deep` only): token-waste audit, per-model compare, shipped-vs-reverted yield. Skip `--deep` for a quick check — it runs the slow `codeburn optimize/compare/yield` passes.

Every section is guarded — a missing tool prints `⚠ <tool> not installed — skipping` and the rest still runs.

## After running: synthesize (this is the point)

Do **not** just paste the raw output. Run the script, then collapse it into a tight consolidated read with these four parts:

1. **Where tokens are going** — spend trend (today vs month), rtk savings %, and which command classes dominate (e.g. `rtk read` vs curls). Call out the biggest line items.
2. **What's not firing** — from the skill-stack audit, the dead/weak skills (no TRIGGER/SKIP, name-not-in-desc, very short). Surface the worst offenders by name; these are routing dead weight.
3. **Are the passive layers earning their keep** — judge the model-router mix (is Haiku/Sonnet/Opus split sane, or is Opus over-firing?), the rtk savings rate, and whether router/RTK/caveman are all present (✓). Flag any layer that's installed but not paying off.
4. **What to cut / fix** — a short prioritized list: descriptions to sharpen, routing thresholds to tune, waste to eliminate (cite the `--deep` findings if it was run).

Keep the synthesis short and decision-oriented. The user wants the forest, not every tree.

## When to invoke

- "where are my tokens going" / "am I wasting tokens" / "token efficiency check"
- "claude code health" / "efficiency dashboard" / "model usage / routing mix"
- "token waste" → run with `--deep` to fold in the codeburn optimize/compare/yield analyses
- periodic check (e.g. weekly) on whether the passive efficiency layers are still pulling their weight

## Skip when

- Sharpening ONE skill's description, or auditing descriptions to then edit them → use `cascade-brain` (`sharpen` / `audit`); this skill only surfaces the weak list, it doesn't fix it.
- Compressing Claude's own output to save tokens in-session → use `caveman`.
- Finding net-new tools to install → use `cascade-discover`.

## Files this skill touches

| Path | Role |
|---|---|
| `~/.claude/skills/efficiency/dashboard.sh` | The gatherer — shells out to every CLI below; the only logic in this skill |
| `codeburn` (CLI, on PATH) | Spend (`status`), and deep: `optimize` / `compare` / `yield` |
| `rtk` (CLI, on PATH) | Proxy token savings (`rtk gain`) |
| `~/.claude/hooks/model-router.cjs` | Routing mix (`--stats`); also presence-checked in the enforcement layer |
| `~/.claude/skills/cascade-brain/brain.py` | Weak/dead skill audit (`audit --weak-only`) |
| `~/.claude/skills/caveman` | Presence-checked in the enforcement layer |

Read-only end to end — the script only reads telemetry and runs reports. It never writes to skill files or state.
