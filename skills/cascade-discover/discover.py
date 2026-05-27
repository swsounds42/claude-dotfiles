#!/usr/bin/env python3
"""
cascade-discover — find new Claude Code skills/agents/hooks/MCP servers,
auto-excluding what's already installed, ranked by stars × recency.

Usage:
  python3 discover.py                              # default queries, top 25
  python3 discover.py --top 50                     # show more
  python3 discover.py --min-stars 100              # higher signal floor
  python3 discover.py --queries "rust mcp,llm agents"
  python3 discover.py --inventory-only             # debug what's detected
  python3 discover.py --save                       # archive to ~/.claude/discover-reports/
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_HOME = Path.home() / ".claude"
REPORTS_DIR = CLAUDE_HOME / "discover-reports"
EXTRAS_FILE = CLAUDE_HOME / "skills" / "cascade-discover" / "inventory-extras.json"
LOCK_FILE = CLAUDE_HOME / "skills" / "cascade-discover" / "freshness-lock.json"

# Repos authored by Sam — never flagged as stale (he's the upstream).
OWN_OWNERS = {"swsounds42", "swsounds"}

DEFAULT_QUERIES = [
    "claude-code skills",
    "claude-code agents",
    "claude-code hooks",
    "claude-code plugin",
    "claude skills",
    "awesome claude code",
    "mcp-server productivity",
    "claude code workflow",
    "agentic personal os",
]


# ───────────────────────────────────────────────────────────────────
# Inventory: what's already installed?
# ───────────────────────────────────────────────────────────────────

GITHUB_URL_RE = re.compile(
    r"(?:https://github\.com/|git@github\.com:|github\.com/)([^/]+/[^/\s]+?)(?:\.git)?/?$"
)


def parse_origin_url(git_config: Path) -> str | None:
    """Read .git/config, return 'owner/name' for the origin remote, or None."""
    try:
        text = git_config.read_text()
    except (OSError, UnicodeDecodeError):
        return None
    in_origin = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == '[remote "origin"]':
            in_origin = True
            continue
        if line.startswith("[") and in_origin:
            in_origin = False
            continue
        if in_origin and line.startswith("url"):
            url = line.split("=", 1)[1].strip() if "=" in line else ""
            m = GITHUB_URL_RE.search(url)
            if m:
                return m.group(1).lower()
    return None


def find_git_root(start: Path, max_walk: int = 20) -> Path | None:
    """Walk up from start to find the nearest .git directory."""
    try:
        cur = start.resolve()
    except (OSError, RuntimeError):
        return None
    for _ in range(max_walk):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def build_inventory() -> tuple[set[str], dict[str, list[str]]]:
    """
    Return (installed_repos, sources) where:
      installed_repos = set of 'owner/name' (lowercased)
      sources = {repo: [reasons]} for transparency
    """
    installed: set[str] = set()
    sources: dict[str, list[str]] = {}

    def add(name: str | None, source: str) -> None:
        if not name:
            return
        name = name.lower()
        installed.add(name)
        sources.setdefault(name, []).append(source)

    # 1. Top-level cloned repos
    repos_dir = CLAUDE_HOME / "repos"
    if repos_dir.is_dir():
        for d in repos_dir.iterdir():
            if d.is_dir():
                add(parse_origin_url(d / ".git" / "config"), f"repos/{d.name}")

    # 2. Plugin marketplaces (cloned)
    mkts_dir = CLAUDE_HOME / "plugins" / "marketplaces"
    if mkts_dir.is_dir():
        for d in mkts_dir.iterdir():
            if d.is_dir():
                add(parse_origin_url(d / ".git" / "config"), f"marketplace/{d.name}")

    # 3. known_marketplaces.json registry
    km = CLAUDE_HOME / "plugins" / "known_marketplaces.json"
    if km.exists():
        try:
            data = json.loads(km.read_text())
            for mname, meta in data.items():
                src = (meta or {}).get("source", {})
                if src.get("source") == "github" and src.get("repo"):
                    add(src["repo"], f"known_marketplace/{mname}")
        except (json.JSONDecodeError, OSError):
            pass

    # 4. Walk skills/agents/commands symlinks → repo root → .git
    for tree in ("skills", "agents", "commands"):
        root = CLAUDE_HOME / tree
        if not root.exists():
            continue
        for entry in root.iterdir():
            if not entry.is_symlink():
                continue
            try:
                target = entry.resolve()
            except (OSError, RuntimeError):
                continue
            git_root = find_git_root(target)
            if git_root:
                add(parse_origin_url(git_root / ".git" / "config"), f"{tree}/{entry.name}")

    # 5. installed_plugins.json (rare — name@marketplace, marketplace already covered)
    ip = CLAUDE_HOME / "plugins" / "installed_plugins.json"
    if ip.exists():
        try:
            data = json.loads(ip.read_text())
            # plugins keyed as "plugin-name@marketplace" — marketplace already in #3
            for key in data.get("plugins", {}):
                if "@" in key:
                    sources.setdefault(f"plugin/{key}", []).append(key)
        except (json.JSONDecodeError, OSError):
            pass

    # 6. Manual extras (plugin-loaded skills, bundled installs that can't be auto-detected)
    if EXTRAS_FILE.exists():
        try:
            extras = json.loads(EXTRAS_FILE.read_text())
            for repo in extras.get("installed", []):
                add(repo, "extras (manual)")
        except (json.JSONDecodeError, OSError):
            pass

    return installed, sources


# ───────────────────────────────────────────────────────────────────
# Discovery: gh search
# ───────────────────────────────────────────────────────────────────


@dataclass
class Repo:
    full_name: str
    stars: int = 0
    pushed_at: str = ""
    description: str = ""
    url: str = ""
    matched_queries: list[str] = field(default_factory=list)

    @property
    def days_since_push(self) -> int:
        if not self.pushed_at:
            return 365
        try:
            ts = datetime.fromisoformat(self.pushed_at.replace("Z", "+00:00"))
            return max((datetime.now(timezone.utc) - ts).days, 0)
        except ValueError:
            return 365

    @property
    def score(self) -> float:
        """Stars × exp(-days_since_push / 90). Recent + popular wins."""
        return self.stars * math.exp(-self.days_since_push / 90)


def gh_search(query: str, limit: int = 30, min_stars: int = 30) -> list[Repo]:
    args = [
        "gh", "search", "repos",
        query,
        "--sort", "stars",
        "--limit", str(limit),
        "--json", "fullName,stargazersCount,pushedAt,description,url",
    ]
    try:
        out = subprocess.check_output(args, text=True, timeout=30, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"  gh search failed for {query!r}: {e.stderr.strip()[:200]}", file=sys.stderr)
        return []
    except subprocess.TimeoutExpired:
        print(f"  gh search timed out for {query!r}", file=sys.stderr)
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    repos: list[Repo] = []
    for r in data:
        stars = r.get("stargazersCount", 0)
        if stars < min_stars:
            continue
        repos.append(Repo(
            full_name=(r.get("fullName") or "").lower(),
            stars=stars,
            pushed_at=r.get("pushedAt", ""),
            description=(r.get("description") or "").strip(),
            url=r.get("url", ""),
            matched_queries=[query],
        ))
    return repos


def discover(queries: list[str], inventory: set[str], min_stars: int, limit: int) -> list[Repo]:
    by_name: dict[str, Repo] = {}
    for q in queries:
        print(f"  searching: {q!r}", file=sys.stderr)
        for r in gh_search(q, limit=limit, min_stars=min_stars):
            if r.full_name in inventory:
                continue
            if r.full_name in by_name:
                # merge query attribution
                by_name[r.full_name].matched_queries.append(q)
            else:
                by_name[r.full_name] = r
    return sorted(by_name.values(), key=lambda r: r.score, reverse=True)


# ───────────────────────────────────────────────────────────────────
# Freshness: are the installed repos stale vs upstream?
# ───────────────────────────────────────────────────────────────────
#
# discover() finds NET-NEW tooling and throws away anything installed.
# Freshness asks the opposite question: of the repos I *already* have,
# which ones shipped upstream changes since my baseline? Baseline is
# stored per-repo in freshness-lock.json and only advances when Sam
# acknowledges an update (--refresh-lock), so drift nags until acted on.


def load_own_repos() -> set[str]:
    """Explicit 'owner/name' repos Sam authors (from inventory-extras.json 'own')."""
    if not EXTRAS_FILE.exists():
        return set()
    try:
        data = json.loads(EXTRAS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    return {r.lower() for r in data.get("own", [])}


def load_lock() -> dict:
    """Read freshness-lock.json → {'repos': {repo: {...}}, 'muted': [...]}."""
    if not LOCK_FILE.exists():
        return {"repos": {}, "muted": []}
    try:
        data = json.loads(LOCK_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"repos": {}, "muted": []}
    data.setdefault("repos", {})
    data.setdefault("muted", [])
    return data


def save_lock(lock: dict) -> None:
    lock["_updated_at"] = datetime.now(timezone.utc).isoformat()
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def gh_json(path: str, jq: str | None = None) -> object | None:
    """Call `gh api <path>` (optionally with --jq). Return parsed JSON, the raw
    jq string, or None on any error (404, network, timeout, bad auth)."""
    args = ["gh", "api", path]
    if jq:
        args += ["--jq", jq]
    try:
        out = subprocess.check_output(
            args, text=True, timeout=20, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    if not out:
        return None
    if jq:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def probe_repo(repo: str) -> dict | None:
    """Latest default-branch commit + latest release for a repo.
    Returns {sha, commit_date, release, release_date} or None if the commit
    probe fails (repo gone / renamed / private / rate-limited)."""
    commit = gh_json(
        f"repos/{repo}/commits?per_page=1",
        jq='.[0].sha + "\t" + .[0].commit.committer.date',
    )
    if not isinstance(commit, str) or "\t" not in commit:
        return None
    sha, commit_date = commit.split("\t", 1)

    release = release_date = None
    rel = gh_json(  # 404s for repos with no releases — that's fine
        f"repos/{repo}/releases/latest",
        jq='.tag_name + "\t" + (.published_at // "")',
    )
    if isinstance(rel, str) and "\t" in rel:
        r_tag, r_date = rel.split("\t", 1)
        release = r_tag or None
        release_date = r_date or None

    return {
        "sha": sha,
        "commit_date": commit_date,
        "release": release,
        "release_date": release_date,
    }


def compare_ahead(repo: str, base_sha: str, head_sha: str) -> int | None:
    """How many commits head is ahead of base. None if the compare fails
    (e.g. base was force-pushed away). 0 if identical."""
    if not base_sha or base_sha == head_sha:
        return 0
    val = gh_json(f"repos/{repo}/compare/{base_sha}...{head_sha}", jq=".ahead_by")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def check_freshness(
    installed: set[str],
    *,
    refresh_lock: bool = False,
    dry_run: bool = False,
    mute: str | None = None,
    unmute: str | None = None,
) -> dict:
    """Probe every tracked installed repo for upstream drift vs its baseline.

    Returns a result dict with `stale` rows, `errors`, and counts. Side effect:
    seeds the lockfile for repos seen for the first time and prunes uninstalled
    ones (unless dry_run). Existing baselines only advance when refresh_lock.
    """
    own = OWN_OWNERS, load_own_repos()
    own_owners, own_repos = own
    tracked = sorted(
        r for r in installed
        if r.split("/", 1)[0] not in own_owners and r not in own_repos
    )

    lock = load_lock()
    repos_lock: dict = lock["repos"]
    muted: set[str] = {m.lower() for m in lock.get("muted", [])}
    if mute:
        muted.add(mute.lower())
    if unmute:
        muted.discard(unmute.lower())
    lock["muted"] = sorted(muted)

    # Prune lock entries for repos no longer installed.
    tracked_set = set(tracked)
    for gone in [r for r in repos_lock if r not in tracked_set]:
        repos_lock.pop(gone, None)

    effective = [r for r in tracked if r not in muted]

    stale: list[dict] = []
    errors: list[str] = []
    seeded = 0

    for repo in effective:
        cur = probe_repo(repo)
        if cur is None:
            errors.append(repo)
            continue
        baseline = repos_lock.get(repo)
        if baseline is None:
            repos_lock[repo] = {**cur, "seen_at": datetime.now(timezone.utc).isoformat()}
            seeded += 1
            continue

        commits_changed = cur["sha"] != baseline.get("sha")
        release_changed = bool(cur["release"]) and cur["release"] != baseline.get("release")
        if commits_changed or release_changed:
            behind = compare_ahead(repo, baseline.get("sha", ""), cur["sha"]) if commits_changed else 0
            base_short = (baseline.get("sha") or "")[:10]
            head_short = cur["sha"][:10]
            stale.append({
                "repo": repo,
                "behind": behind,                       # int or None
                "latest_sha": head_short,
                "commit_date": cur["commit_date"],
                "baseline_sha": base_short,
                "baseline_date": baseline.get("commit_date"),
                "release_changed": release_changed,
                "release": cur["release"],
                "baseline_release": baseline.get("release"),
                "compare_url": f"https://github.com/{repo}/compare/{base_short}...{head_short}",
            })

        if refresh_lock:
            repos_lock[repo] = {**cur, "seen_at": datetime.now(timezone.utc).isoformat()}

    if not dry_run:
        save_lock(lock)

    stale.sort(key=lambda r: (r["behind"] is None, -(r["behind"] or 0), r["repo"]))
    return {
        "tracked": len(tracked),
        "checked": len(effective),
        "seeded": seeded,
        "muted": sorted(muted),
        "stale": stale,
        "errors": errors,
        "lock_written": not dry_run,
        "baseline_advanced": refresh_lock and not dry_run,
    }


def render_freshness_markdown(result: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    stale = result["stale"]
    lines = [
        f"# Cascade Freshness Report — {today}",
        "",
        f"**Tracked:** {result['tracked']} · "
        f"**Stale:** {len(stale)} · "
        f"**Newly seeded:** {result['seeded']} · "
        f"**Muted:** {len(result['muted'])} · "
        f"**Errors:** {len(result['errors'])}"
        + ("  ·  _baseline advanced_" if result.get("baseline_advanced") else ""),
        "",
    ]
    if stale:
        lines += [
            "| # | Repo | Behind | Latest commit | New release | Upstream pushed | Compare |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, r in enumerate(stale, 1):
            behind = f"{r['behind']} commits" if isinstance(r["behind"], int) and r["behind"] > 0 else (
                "release only" if r["release_changed"] and r["behind"] == 0 else
                "?" if r["behind"] is None else "—"
            )
            rel = (
                f"{r['baseline_release'] or '—'} → **{r['release']}**"
                if r["release_changed"] else "—"
            )
            pushed = (r["commit_date"] or "?")[:10]
            lines.append(
                f"| {i} | `{r['repo']}` | {behind} | `{r['latest_sha']}` | {rel} | "
                f"{pushed} | [diff]({r['compare_url']}) |"
            )
    else:
        lines.append(f"✅ All {result['checked']} checked repos are current with their baseline.")

    if result["errors"]:
        lines += ["", "**Could not probe** (renamed / private / rate-limited): "
                  + ", ".join(f"`{e}`" for e in result["errors"])]
    if result["muted"]:
        lines += ["", "_Muted (not tracked):_ " + ", ".join(f"`{m}`" for m in result["muted"])]
    return "\n".join(lines) + "\n"


# ───────────────────────────────────────────────────────────────────
# Render
# ───────────────────────────────────────────────────────────────────


def render_markdown(repos: list[Repo], inventory_size: int, queries: list[str], top_n: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Cascade Discovery Report — {today}",
        "",
        f"**Already installed:** {inventory_size} repos · "
        f"**New candidates found:** {len(repos)} · "
        f"**Showing top:** {min(top_n, len(repos))}",
        "",
        f"**Queries:** `" + "` · `".join(queries) + "`",
        "",
        "| # | Repo | ★ | Last push | Score | Description |",
        "|---|---|---:|---|---:|---|",
    ]
    for i, r in enumerate(repos[:top_n], 1):
        pushed = r.pushed_at[:10] if r.pushed_at else "?"
        desc = r.description.replace("|", "\\|").replace("\n", " ")[:140]
        if not desc:
            desc = "_(no description)_"
        lines.append(
            f"| {i} | [{r.full_name}]({r.url}) | {r.stars:,} | {pushed} | {r.score:.0f} | {desc} |"
        )
    if not repos:
        lines.append("| — | _(no new candidates above threshold)_ | | | | |")
    return "\n".join(lines) + "\n"


def render_inventory(installed: set[str], sources: dict[str, list[str]]) -> str:
    lines = [f"# Installed inventory ({len(installed)} repos)\n"]
    for name in sorted(installed):
        srcs = sources.get(name, [])
        srcs_str = ", ".join(srcs[:3]) + (f" +{len(srcs)-3}" if len(srcs) > 3 else "")
        lines.append(f"- **{name}** — {srcs_str}")
    return "\n".join(lines) + "\n"


# ───────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", help="Comma-separated queries (overrides defaults)")
    p.add_argument("--inventory-only", action="store_true", help="Just print what's installed")
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--min-stars", type=int, default=30)
    p.add_argument("--limit-per-query", type=int, default=30)
    p.add_argument("--save", nargs="?", const="auto", help="Save report (default: dated file in ~/.claude/discover-reports/)")
    p.add_argument("--json", action="store_true", help="Emit structured JSON instead of markdown (for cascade-brain analyze)")
    p.add_argument("--check-updates", action="store_true", help="Freshness mode: report installed repos with upstream drift vs baseline")
    p.add_argument("--refresh-lock", action="store_true", help="Freshness: advance all baselines to current (acknowledge you've updated)")
    p.add_argument("--dry-run", action="store_true", help="Freshness: probe + report but don't write the lockfile")
    p.add_argument("--mute", help="Freshness: stop tracking this owner/name repo")
    p.add_argument("--unmute", help="Freshness: resume tracking this owner/name repo")
    args = p.parse_args()

    print("Building inventory...", file=sys.stderr)
    installed, sources = build_inventory()
    print(f"  found {len(installed)} installed repos", file=sys.stderr)

    if args.inventory_only:
        print(render_inventory(installed, sources))
        return 0

    if args.check_updates:
        print("Checking freshness vs upstream...", file=sys.stderr)
        result = check_freshness(
            installed,
            refresh_lock=args.refresh_lock,
            dry_run=args.dry_run,
            mute=args.mute,
            unmute=args.unmute,
        )
        print(
            f"  tracked={result['tracked']} checked={result['checked']} "
            f"stale={len(result['stale'])} seeded={result['seeded']} "
            f"errors={len(result['errors'])}",
            file=sys.stderr,
        )
        if args.json:
            print(json.dumps(result, indent=2))
            return 0
        report = render_freshness_markdown(result)
        if args.save:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            if args.save == "auto":
                path = REPORTS_DIR / f"freshness-{datetime.now().strftime('%Y-%m-%d')}.md"
            else:
                path = Path(args.save).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report)
            print(f"Saved to {path}", file=sys.stderr)
        print(report)
        return 0

    queries = (
        [q.strip() for q in args.queries.split(",") if q.strip()]
        if args.queries
        else DEFAULT_QUERIES
    )

    print(f"Discovering across {len(queries)} queries...", file=sys.stderr)
    candidates = discover(queries, installed, args.min_stars, args.limit_per_query)
    print(f"  {len(candidates)} new candidates after dedup + crosscheck", file=sys.stderr)

    if args.json:
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "queries": queries,
            "inventory": {
                "size": len(installed),
                "repos": sorted(installed),
            },
            "candidates": [
                {
                    "full_name": r.full_name,
                    "stars": r.stars,
                    "pushed_at": r.pushed_at,
                    "days_since_push": r.days_since_push,
                    "score": round(r.score, 1),
                    "description": r.description,
                    "url": r.url,
                    "matched_queries": r.matched_queries,
                }
                for r in candidates[: args.top]
            ],
        }
        print(json.dumps(out, indent=2))
        return 0

    report = render_markdown(candidates, len(installed), queries, args.top)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if args.save == "auto":
            path = REPORTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        else:
            path = Path(args.save).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report)
        print(f"Saved to {path}", file=sys.stderr)

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
