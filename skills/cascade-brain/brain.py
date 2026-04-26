#!/usr/bin/env python3
"""
cascade-brain: introspect & tune the Cascade routing brain.

Subcommands:
  stats          — analyze skill-recommendations.jsonl (top skills, avg scores, lurkers)
  audit          — score each SKILL.md description for trigger/skip/length quality
  rebuild        — re-init the intelligence index
  health         — full system status (index, telemetry, patterns, hooks)
  trace PROMPT   — run a single prompt through the route hook to see what fires

Usage:
  python3 ~/.claude/skills/cascade-brain/brain.py stats --top 20 --lurkers
  python3 ~/.claude/skills/cascade-brain/brain.py audit --weak-only
  python3 ~/.claude/skills/cascade-brain/brain.py rebuild
  python3 ~/.claude/skills/cascade-brain/brain.py health
  python3 ~/.claude/skills/cascade-brain/brain.py trace "write a soql query"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
PROJECT_ROOT = HOME / "Desktop" / "personal-os-main"
INTEL_DIR = PROJECT_ROOT / ".cascade" / "intelligence"
RECS_LOG = INTEL_DIR / "skill-recommendations.jsonl"
RANKED_CTX = INTEL_DIR / "ranked-context.json"
PATTERNS_FILE = INTEL_DIR / "learned-patterns.json"
SKILLS_DIR = HOME / ".claude" / "skills"
HOOK_HANDLER = PROJECT_ROOT / "scripts" / "hooks" / "hook-handler.cjs"
INTEL_CJS = PROJECT_ROOT / "scripts" / "hooks" / "intelligence.cjs"
DISCOVER_PY = HOME / ".claude" / "skills" / "cascade-discover" / "discover.py"

# Curated awesome-lists Claude should fetch during `analyze`.
# These provide humans-already-filtered signal that gh search alone misses.
CURATED_LISTS = [
    {
        "url": "https://github.com/hesreallyhim/awesome-claude-code",
        "name": "hesreallyhim/awesome-claude-code",
        "focus": "Skills, hooks, slash-commands, agent orchestrators, plugins",
    },
    {
        "url": "https://github.com/davidteren/awesome-claude-code-agents",
        "name": "davidteren/awesome-claude-code-agents",
        "focus": "Subagents and agent collections",
    },
    {
        "url": "https://github.com/wshobson/agents",
        "name": "wshobson/agents",
        "focus": "184 agents + 150 skills + plugin eval framework",
    },
    {
        "url": "https://github.com/rohitg00/awesome-claude-code-toolkit",
        "name": "rohitg00/awesome-claude-code-toolkit",
        "focus": "Meta-registry: 135 agents + 35 skills + 20 hooks + 176 plugins",
    },
    {
        "url": "https://github.com/ComposioHQ/awesome-claude-skills",
        "name": "ComposioHQ/awesome-claude-skills",
        "focus": "Curated skills directory (community-driven)",
    },
    {
        "url": "https://github.com/tolkonepiu/best-of-mcp-servers",
        "name": "tolkonepiu/best-of-mcp-servers",
        "focus": "MCP server registry, weekly-ranked",
    },
]


# ───────────────────────────────────────────────────────────────────
# stats
# ───────────────────────────────────────────────────────────────────


def cmd_stats(args: argparse.Namespace) -> int:
    if not RECS_LOG.exists():
        print(f"No recommendations log at {RECS_LOG}")
        print("(Empty until the route hook surfaces a skill match. Try `cascade-brain trace 'some prompt'`)")
        return 1

    recs_per_skill: Counter[str] = Counter()
    score_sum: dict[str, float] = defaultdict(float)
    score_count: dict[str, int] = defaultdict(int)
    prompts_per_skill: dict[str, set[str]] = defaultdict(set)
    total_events = 0
    earliest: int | None = None
    latest: int | None = None

    with open(RECS_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            total_events += 1
            ts = entry.get("ts")
            if ts:
                if earliest is None or ts < earliest:
                    earliest = ts
                if latest is None or ts > latest:
                    latest = ts
            for rec in entry.get("recs", []):
                # Skill name from summary "name — desc..." or from id "skill-name"
                name = (rec.get("summary") or "").split(" —")[0].strip()
                if not name:
                    name = (rec.get("id") or "").removeprefix("skill-")
                if not name:
                    continue
                recs_per_skill[name] += 1
                score = rec.get("score", 0)
                score_sum[name] += score
                score_count[name] += 1
                prompts_per_skill[name].add((entry.get("prompt") or "")[:60])

    print(f"📊 Cascade Brain Telemetry — {total_events} prompts logged")
    if earliest and latest:
        e = datetime.fromtimestamp(earliest / 1000, tz=timezone.utc).isoformat()[:16]
        l = datetime.fromtimestamp(latest / 1000, tz=timezone.utc).isoformat()[:16]
        print(f"   Range: {e} → {l}")
    print()

    print(f"🏆 Top {args.top} most-recommended skills:")
    for name, count in recs_per_skill.most_common(args.top):
        avg_score = score_sum[name] / score_count[name] if score_count[name] else 0
        unique_prompts = len(prompts_per_skill[name])
        print(f"  {count:3d}× ({avg_score:.2f} avg)  {name:40s}  [{unique_prompts} unique prompts]")

    if args.lurkers:
        print()
        installed: set[str] = set()
        for p in SKILLS_DIR.iterdir():
            if p.name == "skill-resources":
                continue
            if p.is_dir() or p.is_symlink():
                installed.add(p.name)
        recommended = set(recs_per_skill.keys())
        lurkers = sorted(installed - recommended)
        print(f"💤 Lurking skills (installed but never surfaced): {len(lurkers)}")
        for s in lurkers[: args.lurker_limit]:
            print(f"   {s}")
        if len(lurkers) > args.lurker_limit:
            print(f"   ...and {len(lurkers) - args.lurker_limit} more — pass --lurker-limit N to see more")

    return 0


# ───────────────────────────────────────────────────────────────────
# audit
# ───────────────────────────────────────────────────────────────────


TRIGGER_RE = re.compile(r"\bTRIGGER\s+when\b", re.IGNORECASE)
SKIP_RE = re.compile(r"(?:^|[\s.])SKIP[:\s]", re.IGNORECASE)

# Skills to exclude from audit (infrastructure, sub-resources, internal lookups,
# and namespace-prefixed plugin skills that auto-generate functional descriptions
# the audit heuristic mis-flags as weak).
# Pass --include-all to override.
AUDIT_EXCLUDE_PATTERNS = [
    re.compile(r"^skill-resources:"),     # Sub-resource pages (themes, examples, refs)
    re.compile(r"^subagent-catalog:"),    # Internal catalog lookup tools
]

# GSD command names that are internal-only (used by GSD itself, not by user prompts).
# These don't benefit from TRIGGER/SKIP descriptions.
GSD_INTERNAL = {
    "gsd-help", "gsd-update", "gsd-from-gsd2", "gsd-stats", "gsd-settings",
    "gsd-set-profile", "gsd-join-discord", "gsd-reapply-patches", "gsd-cleanup",
    "gsd-new-workspace", "gsd-remove-workspace", "gsd-list-workspaces",
    "gsd-insert-phase", "gsd-remove-phase", "gsd-add-phase",
    "gsd-complete-milestone", "gsd-new-milestone", "gsd-audit-milestone",
    "gsd-secure-phase", "gsd-extract_learnings", "gsd-undo",
    "gsd-check-todos", "gsd-review-backlog", "gsd-add-backlog",
    "gsd-plan-milestone-gaps", "gsd-do",
    "gsd-pr-branch", "gsd-thread", "gsd-graphify", "gsd-intel",
    "gsd-list-phase-assumptions", "gsd-session-report",
}


def parse_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    m = re.match(r"^---\s*\n([\s\S]*?)\n---", text)
    if not m:
        return None
    fm = m.group(1)
    name_m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    # description can be single line or multi-line (YAML | or ")
    desc_m = re.search(r"description:\s*([\s\S]+?)(?=\n[a-zA-Z_-]+:\s|\Z)", fm)
    desc = ""
    if desc_m:
        desc = desc_m.group(1).strip()
        # Strip YAML scalar markers and outer quotes
        desc = re.sub(r"^[|>]\s*\n?", "", desc)
        desc = desc.strip().strip('"').strip()
        desc = re.sub(r"\s+", " ", desc)

    # user-invocable: false → not user-facing, exclude from audit
    user_inv_m = re.search(r"^user-invocable:\s*(\S+)$", fm, re.MULTILINE)
    user_invocable = True
    if user_inv_m:
        val = user_inv_m.group(1).strip().lower()
        user_invocable = val not in ("false", "no", "0")

    return {
        "name": (name_m.group(1).strip() if name_m else path.parent.name),
        "description": desc,
        "user_invocable": user_invocable,
    }


def _is_audit_excluded(name: str) -> bool:
    """True if this skill should be skipped from the audit."""
    if any(p.match(name) for p in AUDIT_EXCLUDE_PATTERNS):
        return True
    if name in GSD_INTERNAL:
        return True
    return False


def score_description(name: str, desc: str) -> tuple[int, list[str]]:
    flags: list[str] = []
    score = 0

    if not desc:
        return 0, ["no description"]

    desc_len = len(desc)
    if desc_len >= 100:
        score += 1
    else:
        flags.append(f"short ({desc_len}c)")

    if TRIGGER_RE.search(desc):
        score += 2
    else:
        flags.append("no TRIGGER")

    if SKIP_RE.search(desc):
        score += 1
    else:
        flags.append("no SKIP")

    name_words = name.lower().replace("-", " ").split()
    desc_lower = desc.lower()
    if all(w in desc_lower for w in name_words):
        score += 1
    elif name_words and name_words[0] in desc_lower:
        pass  # partial credit, no flag
    else:
        flags.append("name not in desc")

    return score, flags


def cmd_audit(args: argparse.Namespace) -> int:
    if not SKILLS_DIR.exists():
        print(f"No skills dir at {SKILLS_DIR}")
        return 1

    skills = []
    excluded_count = 0
    for p in SKILLS_DIR.iterdir():
        if p.name == "skill-resources":
            continue
        if not (p.is_dir() or p.is_symlink()):
            continue
        skill_md = p / "SKILL.md"
        try:
            real = skill_md.resolve()
        except OSError:
            continue
        if not real.exists():
            continue
        fm = parse_frontmatter(real)
        if not fm:
            continue

        # Skip excluded skills unless --include-all
        if not getattr(args, "include_all", False):
            if _is_audit_excluded(fm["name"]):
                excluded_count += 1
                continue
            if not fm.get("user_invocable", True):
                excluded_count += 1
                continue

        score, flags = score_description(fm["name"], fm["description"])
        skills.append(
            {
                "name": fm["name"],
                "score": score,
                "flags": flags,
                "len": len(fm["description"]),
            }
        )

    # Sort: weakest first (lowest score, then shortest)
    skills.sort(key=lambda s: (s["score"], s["len"]))

    weak_threshold = 2
    weak_total = sum(1 for s in skills if s["score"] <= weak_threshold)
    medium_total = sum(1 for s in skills if weak_threshold < s["score"] <= 3)
    strong_total = sum(1 for s in skills if s["score"] > 3)

    print(f"🔍 SKILL.md description audit — {len(skills)} skills"
          + (f" ({excluded_count} excluded as infrastructure / not user-invocable; pass --include-all to see)"
             if excluded_count else ""))
    print(f"   {weak_total} weak / {medium_total} medium / {strong_total} strong")
    print()
    print(f"{'STRENGTH':<10} {'SCORE':<6} {'LEN':<5} {'NAME':<42} FLAGS")
    print("-" * 110)

    shown = 0
    for s in skills:
        if args.weak_only and s["score"] > weak_threshold:
            break
        if shown >= args.top:
            print(f"  ...and {len(skills) - shown} more (use --top N to see more)")
            break
        strength = "WEAK" if s["score"] <= weak_threshold else "MED" if s["score"] <= 3 else "STRONG"
        flags_str = ", ".join(s["flags"]) if s["flags"] else "—"
        print(f"{strength:<10} {s['score']:<6} {s['len']:<5} {s['name']:<42} {flags_str}")
        shown += 1

    return 0


# ───────────────────────────────────────────────────────────────────
# rebuild
# ───────────────────────────────────────────────────────────────────


def cmd_rebuild(_args: argparse.Namespace) -> int:
    if not INTEL_CJS.exists():
        print(f"❌ Hook intelligence not found at {INTEL_CJS}")
        return 1

    print("Rebuilding Cascade intelligence index...")
    result = subprocess.run(
        ["node", str(INTEL_CJS), "init"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()

    if result.returncode != 0:
        print(f"❌ Failed (exit {result.returncode}): {err}")
        return 1

    # Try to parse the JSON output
    try:
        # First valid JSON line
        json_block = ""
        depth = 0
        for ch in out:
            json_block += ch
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
        data = json.loads(json_block)
        nodes = data.get("nodes", 0)
        cats = data.get("categories", {})
        mode = data.get("searchMode", "?")
        print(f"✅ Indexed {nodes} entries (mode: {mode})")
        for k, v in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"   {k:15s} {v:5d}")
    except (json.JSONDecodeError, ValueError):
        print(out)
    return 0


# ───────────────────────────────────────────────────────────────────
# health
# ───────────────────────────────────────────────────────────────────


def cmd_health(_args: argparse.Namespace) -> int:
    print("🩺 Cascade Brain Health\n")

    # Index
    if RANKED_CTX.exists():
        try:
            d = json.loads(RANKED_CTX.read_text())
            count = d.get("count", len(d.get("entries", [])))
            ts = d.get("computedAt")
            ago = "?"
            if ts:
                ago_min = (datetime.now(timezone.utc).timestamp() * 1000 - ts) / 1000 / 60
                if ago_min < 60:
                    ago = f"{ago_min:.0f}m ago"
                elif ago_min < 1440:
                    ago = f"{ago_min / 60:.1f}h ago"
                else:
                    ago = f"{ago_min / 1440:.1f}d ago"
            print(f"  Index:       {count} entries (computed {ago})")
        except Exception as e:
            print(f"  Index:       ERROR ({e})")
    else:
        print("  Index:       missing — run `cascade-brain rebuild`")

    # Telemetry log
    if RECS_LOG.exists():
        size_kb = RECS_LOG.stat().st_size / 1024
        line_count = sum(1 for _ in open(RECS_LOG))
        print(f"  Telemetry:   {line_count} events ({size_kb:.1f} KB)")
    else:
        print("  Telemetry:   empty (logged after first skill recommendation)")

    # Patterns
    if PATTERNS_FILE.exists():
        try:
            d = json.loads(PATTERNS_FILE.read_text())
            short = len(d.get("shortTerm", []))
            long_t = len(d.get("longTerm", []))
            print(f"  Patterns:    {short} short-term · {long_t} long-term")
        except Exception:
            print("  Patterns:    parse error")
    else:
        print("  Patterns:    none yet")

    # Skills
    if SKILLS_DIR.exists():
        skill_count = sum(
            1
            for p in SKILLS_DIR.iterdir()
            if (p.is_dir() or p.is_symlink()) and p.name != "skill-resources"
        )
        print(f"  Skills:      {skill_count} installed")

    # Hook handler
    if HOOK_HANDLER.exists():
        print(f"  Hook:        ✅ {HOOK_HANDLER.relative_to(HOME)}")
    else:
        print("  Hook:        ❌ missing — Cascade hooks not wired")

    return 0


# ───────────────────────────────────────────────────────────────────
# trace
# ───────────────────────────────────────────────────────────────────


def cmd_trace(args: argparse.Namespace) -> int:
    prompt = (args.prompt or "").strip()
    if not prompt:
        print('Usage: cascade-brain trace "your prompt here"')
        return 1
    if not HOOK_HANDLER.exists():
        print(f"❌ Hook handler not found at {HOOK_HANDLER}")
        return 1

    payload = json.dumps({"prompt": prompt})
    result = subprocess.run(
        ["node", str(HOOK_HANDLER), "route"],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )

    print(f"📍 Trace: {prompt!r}\n")
    if result.stdout.strip():
        print(result.stdout.strip())
    err = "\n".join(
        line
        for line in (result.stderr or "").splitlines()
        if "Experimental" not in line and "trace-warnings" not in line
    ).strip()
    if err:
        print(f"\n[stderr]\n{err}")
    return 0


# ───────────────────────────────────────────────────────────────────
# analyze — primary use case: gh search + curated lists + cross-check + editorial brief
# ───────────────────────────────────────────────────────────────────


def _load_skill_descriptions() -> dict[str, str]:
    """Map of installed skill name → description (first 200 chars)."""
    out = {}
    if not SKILLS_DIR.exists():
        return out
    for p in SKILLS_DIR.iterdir():
        if p.name == "skill-resources":
            continue
        if not (p.is_dir() or p.is_symlink()):
            continue
        skill_md = p / "SKILL.md"
        try:
            real = skill_md.resolve()
        except OSError:
            continue
        if not real.exists():
            continue
        fm = parse_frontmatter(real)
        if fm and fm.get("description"):
            out[fm["name"]] = fm["description"][:200]
    return out


def _closest_installed(candidate_desc: str, skill_descs: dict[str, str], k: int = 3) -> list[str]:
    """Crude text-overlap match — find skills whose description shares the most words."""
    if not candidate_desc:
        return []
    cand_words = set(re.findall(r"[a-z0-9]+", candidate_desc.lower()))
    cand_words = {w for w in cand_words if len(w) > 3}
    scored = []
    for name, desc in skill_descs.items():
        skill_words = set(re.findall(r"[a-z0-9]+", desc.lower()))
        skill_words = {w for w in skill_words if len(w) > 3}
        if not cand_words or not skill_words:
            continue
        overlap = len(cand_words & skill_words)
        if overlap >= 2:
            scored.append((name, overlap))
    scored.sort(key=lambda x: -x[1])
    return [name for name, _ in scored[:k]]


def cmd_analyze(args: argparse.Namespace) -> int:
    """Build a research brief that Claude (in chat) editorializes."""
    if not DISCOVER_PY.exists():
        print(f"❌ cascade-discover not found at {DISCOVER_PY}")
        return 1

    print("🔬 Cascade Brain — Discovery & Analysis Brief", flush=True)
    print(f"   Generated {datetime.now(timezone.utc).isoformat()[:19]}Z\n")

    # 1. Run cascade-discover in JSON mode
    print(f"## 1. GitHub search (top {args.top} candidates)\n", flush=True)
    print(f"_Running `discover.py --json --top {args.top}`..._\n", flush=True)
    cmd = ["python3", str(DISCOVER_PY), "--top", str(args.top), "--min-stars", str(args.min_stars), "--json"]
    if args.queries:
        cmd.extend(["--queries", args.queries])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print("❌ discover.py timed out after 180s")
        return 1
    if result.returncode != 0:
        print(f"❌ discover.py failed: {result.stderr[:300]}")
        return 1

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ Could not parse discover.py JSON: {e}")
        return 1

    inventory = data.get("inventory", {})
    candidates = data.get("candidates", [])
    queries = data.get("queries", [])

    # 2. Annotate each candidate with closest installed skill (redundancy hint)
    skill_descs = _load_skill_descriptions()
    for c in candidates:
        c["closest_installed"] = _closest_installed(c.get("description", ""), skill_descs)

    print(f"**Inventory size:** {inventory.get('size', 0)} repos already installed (cross-check baseline)")
    print(f"**Queries used:** `{', '.join(queries)}`")
    print(f"**Candidates returned:** {len(candidates)} (after dedup + crosscheck)\n")

    print("| # | Repo | ★ | Pushed | Score | Description | Closest installed (redundancy?) |")
    print("|---|---|---:|---|---:|---|---|")
    for i, c in enumerate(candidates, 1):
        repo_link = f"[{c['full_name']}]({c['url']})"
        desc = (c.get("description") or "_(no desc)_").replace("|", "\\|").replace("\n", " ")[:120]
        pushed = (c.get("pushed_at") or "?")[:10]
        closest = ", ".join(c.get("closest_installed", [])) or "—"
        print(f"| {i} | {repo_link} | {c['stars']:,} | {pushed} | {c['score']:.0f} | {desc} | {closest} |")

    # 3. Curated lists for Claude to fetch
    print(f"\n## 2. Curated awesome-lists to consult\n")
    print("_These are humans-already-filtered. Cascade can't fetch them server-side from this script — "
          "**Claude (in chat) should `WebFetch` each URL** to extract entries that aren't in our inventory yet._\n")
    for lst in CURATED_LISTS:
        print(f"- **[{lst['name']}]({lst['url']})** — {lst['focus']}")

    # 4. Editorial instructions (this is what Claude actually does)
    print(f"\n## 3. Editorial — Claude does this part\n")
    print("For the candidates above AND any net-new entries from the curated lists, produce a")
    print("prioritized table with three buckets:\n")
    print("- **HIGH** — net-new gap-filler, install now (give 1-line rationale + estimated install effort)")
    print("- **MED** — complement to existing skill X, worth watching (note what it adds beyond X)")
    print("- **SKIP** — redundant with X / niche / stale / low-quality (one-line dismissal)\n")
    print("**Cross-check carefully against inventory** ({} installed). The `closest_installed` column".format(inventory.get("size", 0)))
    print("above is a heuristic hint — read the candidate's actual description to confirm redundancy.\n")
    print("**Cascade fit lens:** RevOps / sales analyst at Homebot.ai, daily tools = SF + HubSpot + Gong +")
    print("Notion + Slack + Gmail + Calendar + GitHub. Writes content (samwarren.io). Builds n8n + Python")
    print("automations. Bias toward skills that compound with what's installed, not parallel duplicates.\n")
    print("Render output as a single markdown table with columns:")
    print("`| Bucket | Repo | ★ | Why (or why not) | Notes |`\n")
    print("Save the final report to `~/.claude/discover-reports/analysis-$(date +%F).md`.\n")

    return 0


# ───────────────────────────────────────────────────────────────────
# sharpen — improve a SKILL.md description (TRIGGER/SKIP pattern)
# ───────────────────────────────────────────────────────────────────


def _find_skill_md(skill_name: str) -> Path | None:
    """Resolve skill name to its SKILL.md path. Handles symlinks + bare files."""
    # Try as-is in skills/
    candidate_dir = SKILLS_DIR / skill_name / "SKILL.md"
    if candidate_dir.exists():
        return candidate_dir
    # Try as bare file in commands/ (homebot-forecast-checker.md style)
    candidate_file = HOME / ".claude" / "commands" / f"{skill_name}.md"
    if candidate_file.exists():
        return candidate_file
    # Try as dir in commands/
    candidate_cmd = HOME / ".claude" / "commands" / skill_name / "SKILL.md"
    if candidate_cmd.exists():
        return candidate_cmd
    # Resolve symlink target
    sym = SKILLS_DIR / skill_name
    if sym.is_symlink():
        try:
            real = sym.resolve()
            md = real / "SKILL.md"
            if md.exists():
                return md
        except OSError:
            pass
    return None


def cmd_sharpen(args: argparse.Namespace) -> int:
    skill_name = (args.skill or "").strip()
    if not skill_name:
        print('Usage: cascade-brain sharpen <skill-name> [--apply "new description text"]')
        return 1

    skill_md = _find_skill_md(skill_name)
    if not skill_md:
        print(f"❌ Could not find SKILL.md for {skill_name!r} in ~/.claude/skills/ or ~/.claude/commands/")
        return 1

    fm = parse_frontmatter(skill_md.resolve())
    if not fm:
        print(f"❌ No YAML frontmatter in {skill_md}")
        return 1

    current_desc = fm["description"]
    score, flags = score_description(skill_name, current_desc)

    # ── Apply mode ──
    if args.apply:
        new_desc = args.apply.strip()
        if not new_desc:
            print("❌ --apply requires a non-empty description")
            return 1

        try:
            text = skill_md.resolve().read_text()
        except OSError as e:
            print(f"❌ Could not read {skill_md}: {e}")
            return 1

        # Replace the description line(s) in frontmatter.
        # Match: "description:" followed by content up to next ^[a-z_-]+: line or ---
        new_text, n = re.subn(
            r"^(description:\s*)([\s\S]+?)(?=\n[a-zA-Z_-]+:\s|\n---)",
            lambda m: f"{m.group(1)}{new_desc}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:
            print(f"❌ Could not locate description line in frontmatter")
            return 1

        skill_md.resolve().write_text(new_text)
        new_score, new_flags = score_description(skill_name, new_desc)
        old_strength = "WEAK" if score <= 2 else "MED" if score <= 3 else "STRONG"
        new_strength = "WEAK" if new_score <= 2 else "MED" if new_score <= 3 else "STRONG"
        print(f"✅ Updated {skill_name}")
        print(f"   {old_strength} ({score}) → {new_strength} ({new_score})")
        if new_flags:
            print(f"   Remaining flags: {', '.join(new_flags)}")
        print()
        print("Run `cascade-brain rebuild` to refresh the index.")
        return 0

    # ── Inspect mode (default) — output context for Claude to draft a new description ──
    try:
        body_text = skill_md.resolve().read_text()
    except OSError:
        body_text = ""
    body_excerpt = re.sub(r"^---[\s\S]*?---\n", "", body_text).strip()
    body_excerpt = body_excerpt[:1200]

    strength = "WEAK" if score <= 2 else "MED" if score <= 3 else "STRONG"
    print(f"# Sharpen draft — `{skill_name}`\n")
    print(f"**Path:** `{skill_md}`")
    print(f"**Current strength:** {strength} (score {score}, {len(current_desc)}c)")
    print(f"**Flags:** {', '.join(flags) if flags else '—'}\n")
    print("## Current description\n")
    print(f"```\n{current_desc}\n```\n")
    print("## Body excerpt (first 1200 chars)\n")
    print(f"```\n{body_excerpt}\n```\n")
    print("## Sharpening template\n")
    print("```")
    print("description: <one-line summary of what the skill does>. "
          "TRIGGER when user mentions \"<phrase 1>\", \"<phrase 2>\", \"<phrase 3>\". "
          "SKIP: <when not to use — point to alternative skills>.")
    print("```\n")
    print("## What Claude should do\n")
    print("1. Read the body excerpt above to understand the skill's purpose & scope.")
    print("2. Draft a sharpened description following the template (under 500 chars).")
    print(f"3. Apply it: `python3 ~/.claude/skills/cascade-brain/brain.py sharpen {skill_name} --apply \"<new desc>\"`")
    print("4. Run `cascade-brain rebuild` afterward.\n")
    return 0


# ───────────────────────────────────────────────────────────────────
# main
# ───────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd")

    # PRIMARY: discovery + curated lists + editorial brief
    an = sub.add_parser("analyze", help="Build a discovery + editorial research brief (PRIMARY use case)")
    an.add_argument("--top", type=int, default=30, help="GitHub candidates to surface")
    an.add_argument("--min-stars", type=int, default=30)
    an.add_argument("--queries", help="Comma-separated gh search queries (overrides defaults)")

    sh = sub.add_parser("sharpen", help="Improve a SKILL.md description")
    sh.add_argument("skill", nargs="?", default="", help="Skill name (e.g., gws-gmail)")
    sh.add_argument("--apply", help='Write a new description. e.g., --apply "Send email. TRIGGER when..."')

    # UTILITY subcommands
    s = sub.add_parser("stats", help="Analyze skill-recommendations.jsonl")
    s.add_argument("--top", type=int, default=20)
    s.add_argument("--lurkers", action="store_true", help="Show installed-but-never-surfaced skills")
    s.add_argument("--lurker-limit", type=int, default=30)

    a = sub.add_parser("audit", help="Score SKILL.md description quality")
    a.add_argument("--top", type=int, default=50)
    a.add_argument("--weak-only", action="store_true", help="Show only weak descriptions")
    a.add_argument("--include-all", action="store_true",
                   help="Include infrastructure / non-user-invocable skills (default: hide)")

    sub.add_parser("rebuild", help="Re-init the intelligence index")
    sub.add_parser("health", help="System status")

    t = sub.add_parser("trace", help="Run a prompt through the route hook")
    t.add_argument("prompt", nargs="?", default="")

    args = p.parse_args()

    handlers = {
        "analyze": cmd_analyze,
        "sharpen": cmd_sharpen,
        "stats": cmd_stats,
        "audit": cmd_audit,
        "rebuild": cmd_rebuild,
        "health": cmd_health,
        "trace": cmd_trace,
    }
    if args.cmd in handlers:
        return handlers[args.cmd](args) or 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
