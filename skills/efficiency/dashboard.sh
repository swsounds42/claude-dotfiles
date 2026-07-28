#!/usr/bin/env bash
#
# efficiency/dashboard.sh — gather Claude/token efficiency telemetry into ONE feed.
# The script gathers; Claude (via SKILL.md) synthesizes. Keep it dumb and resilient.
#
# Usage:
#   bash dashboard.sh          # FAST panel only (5 sections) — safe, quick
#   bash dashboard.sh --deep   # FAST panel + 3 heavy codeburn analyses (slow)
#
# Every section is guarded so one missing tool / one failure never aborts the rest.

set -uo pipefail

DEEP=0
for arg in "$@"; do
  case "$arg" in
    --deep) DEEP=1 ;;
    *) ;;
  esac
done

ROUTER="$HOME/.claude/hooks/model-router.cjs"
BRAIN="$HOME/.claude/skills/cascade-brain/brain.py"
CAVEMAN_DIR="$HOME/.claude/skills/caveman"

# --- helpers --------------------------------------------------------------

hr() { printf '%s\n' "------------------------------------------------------------"; }

section() { printf '\n## %s\n' "$1"; }

# run <label> <tool-name> -- <command...>
# Skips with a warning if the tool isn't installed; never aborts the script.
run() {
  local label="$1"; shift
  local tool="$1"; shift
  [ "$1" = "--" ] && shift
  section "$label"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '⚠ %s not installed — skipping\n' "$tool"
    return 0
  fi
  "$@" </dev/null 2>&1 || printf '⚠ %s errored (exit %s) — continuing\n' "$tool" "$?"
}

mark() { # mark <name> <path-to-test>
  if [ -e "$2" ]; then printf '%s ✓\n' "$1"; else printf '%s ✗ (missing: %s)\n' "$1" "$2"; fi
}

mark_path() { # mark_path <name> <tool-on-PATH>
  if command -v "$2" >/dev/null 2>&1; then printf '%s ✓\n' "$1"; else printf '%s ✗ (not on PATH)\n' "$1"; fi
}

# --- header banner --------------------------------------------------------

hr
printf '  CLAUDE / TOKEN EFFICIENCY DASHBOARD\n'
printf '  %s' "$(date '+%Y-%m-%d %H:%M %Z')"
if [ "$DEEP" -eq 1 ]; then printf '   [mode: DEEP]\n'; else printf '   [mode: FAST]\n'; fi
hr

# ==========================================================================
# FAST PANEL — always runs
# ==========================================================================

# 1. Spend  (note: `status` uses --period, not -p; the deep subcommands below use -p)
run "SPEND (codeburn, 30d)" codeburn -- codeburn status --period 30days --provider claude

# 2. Proxy savings
run "PROXY SAVINGS (rtk)" rtk -- rtk gain

# 3. Model routing mix
run "MODEL ROUTING MIX" node -- node "$ROUTER" --stats

# 4. Skill stack health (weak/dead descriptions)
run "SKILL STACK HEALTH" python3 -- python3 "$BRAIN" audit --weak-only

# 5. Enforcement layer — static presence checks for the passive efficiency layers
section "ENFORCEMENT LAYER"
mark      "router"  "$ROUTER"
mark_path "RTK"     "rtk"
mark      "caveman" "$CAVEMAN_DIR"

# ==========================================================================
# DEEP PANEL — only with --deep (slow; runs the heavy codeburn analyses)
# ==========================================================================

if [ "$DEEP" -eq 1 ]; then
  hr
  printf '  DEEP PANEL (slow analyses)\n'
  hr

  # 6. Token waste audit
  run "DEEP: TOKEN WASTE" codeburn -- codeburn optimize --provider claude -p 30days

  # 7. Per-model comparison — `codeburn compare` requires an interactive TTY and hangs when
  #    piped, with no --json/--plain escape. Derive per-model stats from the export JSON instead
  #    (write to a temp file so we don't litter the cwd, then print and clean up).
  section "DEEP: MODEL COMPARE (per-model, via export json)"
  if command -v codeburn >/dev/null 2>&1; then
    _cb_tmp="$(mktemp -t codeburn-export)"
    codeburn export --format json --provider claude -o "$_cb_tmp" </dev/null 2>&1 \
      || printf '⚠ codeburn export errored — continuing\n'
    [ -s "$_cb_tmp" ] && cat "$_cb_tmp"
    rm -f "$_cb_tmp"
  else
    printf '⚠ codeburn not installed — skipping\n'
  fi

  # 8. Shipped vs reverted yield
  run "DEEP: SHIPPED VS REVERTED" codeburn -- codeburn yield -p 30days
fi

printf '\n'
hr
printf '  END OF DASHBOARD\n'
hr
