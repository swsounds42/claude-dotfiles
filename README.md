# claude-dotfiles

A portable backup of a working `~/.claude/` configuration. Clone on any
machine, run `bootstrap.sh`, and you have a full Claude Code setup — agents,
skills, hooks, and slash commands — wired up in under a minute.

This is the tooling layer behind [samwarren.io](https://samwarren.io) and the
**Cascade** personal operations system.

## What you get

| Path | Contents |
|------|----------|
| `CLAUDE.md` | Global auto-routing rules — which skill handles which kind of request |
| `agents/` | 167 specialist subagent definitions (react-specialist, python-pro, devops-engineer, etc.) |
| `commands/` | 39 slash commands — n8n, content writing, design, prompts, Slack |
| `hooks/` | `context-statusline.js` + `context-watchdog.js` (context window monitoring), `model-router.cjs` (per-prompt Claude tier recommendation), `rtk-bootstrap.js` |
| `skills/` (design) | `ui-ux-pro-max`, `design-system`, `brand`, `frontend-slides`, `slides`, `banner-design`, `ui-styling`, `design` — UI/UX intelligence, token architecture, brand voice, presentation generation |
| `skills/` (writing) | `humanizer` (removes AI-writing tells), `last30days` (social sentiment research across Reddit, X, YouTube, HN) |
| `skills/` (job search) | `job-search-kit` — cover-letter tailoring, interview prep, and round debriefs driven off a personal proof bank + style card. Truth-preserving (never claims a tool you haven't used) and voice-preserving (won't sand off your writing signatures) |
| `skills/` (cascade meta) | `cascade-brain` (brain introspection + stats), `cascade-discover` (new-tool discovery) |
| `skills/` (dev workflow) | `grill-with-docs`, `improve-codebase-architecture`, `caveman` |
| `settings.json.template` | Claude settings with secrets and paths replaced by `{{PLACEHOLDER}}` variables |

**Installed by `bootstrap.sh` (not stored in this repo):**

- **143 marketplace skills** via `npx skills add`:
  - `coreyhaines31/marketingskills` (34 skills — RevOps, CRO, SEO, copywriting)
  - `obra/superpowers` (14 skills — systematic debugging, TDD, parallel agent dispatch)
  - `googleworkspace/cli` (95 skills — Gmail, Calendar, Drive, Docs, Sheets)
- `commands/gsd/` (GSD installs itself via `/gsd:update`)
- `skills/slidev/` (large, cloned separately)
- `gws` CLI (Google Workspace CLI, via Homebrew)
- Everything ephemeral: `cache/`, `sessions/`, `projects/`, `todos/`, `telemetry/`

## Quick start

```bash
git clone git@github.com:swsounds42/claude-dotfiles.git ~/Desktop/claude-dotfiles
cd ~/Desktop/claude-dotfiles
./bootstrap.sh
```

The bootstrap script will:

1. Detect your OS (macOS or Linux)
2. Ask for optional Salesforce MCP credentials (press Enter to skip)
3. Symlink `agents/`, `commands/`, `hooks/`, `skills/`, and `CLAUDE.md` into `~/.claude/`
4. Generate `~/.claude/settings.json` from the template, substituting your paths and credentials
5. Install 143 marketplace skills
6. Optionally install Slidev + the `gws` CLI

## After bootstrap

A few things need manual setup:

**GSD (Get Shit Done)** — the structured planning skill system that turns big projects into goal-backward plans with atomic commits:

```
Open Claude Code → run /gsd:update
```

This installs `commands/gsd/` and the `gsd-check-update.js` session hook.

**Google Workspace CLI** — if you want Gmail/Calendar/Drive automation:

```bash
gws auth setup --login
```

(Requires a GCP project with an OAuth client.)

**Plugins:**

```
claude plugin install slack@claude-plugins-official
```

## Why symlinks instead of copies?

`bootstrap.sh` symlinks `agents/`, `commands/`, `hooks/`, `skills/`, and
`CLAUDE.md` into `~/.claude/` rather than copying. So when you update this
repo, the changes are live in `~/.claude/` immediately — no re-run needed.

On your main machine:

```bash
cd ~/Desktop/claude-dotfiles
git add -A
git commit -m "update: [what changed]"
git push
```

On any other machine:

```bash
git pull
```

Re-run `bootstrap.sh` only if `settings.json.template` changed or new
marketplace skills got added to `skills.sh`.

## Surface area

| Layer | Count |
|-------|-------|
| Skills (knowledge files) | 159 (16 custom + 143 marketplace) |
| Commands (slash commands) | 39 |
| Specialist agents | 167 |
| Brand design references | 58 (via `npx getdesign@latest add <name>`) |

## What's not included

Proprietary skills and workflows tied to specific companies or revenue
systems aren't in this repo — they live in private repos owned by whoever
built them. This repo is the portable, company-neutral toolkit: the agent
library, the skills catalog, the hook runtime, and the bootstrap plumbing.

If you're looking for the full Cascade architecture, the orchestration
layer that sits above this, start here:
[samwarren.io/projects/cascade](https://samwarren.io/projects/cascade).

## License

MIT. See `LICENSE`.

## Contributing

If you find a bug in a hook, the bootstrap script, or one of the custom
skills — open an issue or a PR. If you want to swap in your own agents or
skills, fork and go. The routing table in `CLAUDE.md` is the contract;
everything else is composable.
