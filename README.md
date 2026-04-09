# claude-dotfiles

Portable backup of my `~/.claude/` configuration. Clone this on any machine to bootstrap a full Claude Code setup with all agents, skills, hooks, and commands in place.

## What's included

| Path | Contents |
|------|----------|
| `CLAUDE.md` | Global Claude instructions — Jarvis persona, auto-routing rules, working style |
| `agents/` | 142 specialist agent definitions (react-specialist, python-pro, devops-engineer, etc.) |
| `commands/` | 36 slash commands — n8n, content writing, design, SF attribution, HubSpot ops, prompts |
| `hooks/` | `context-statusline.js` and `context-watchdog.js` — context window monitoring |
| `skills/ui-ux-pro-max/` | UI/UX design intelligence + 58 brand design references (Stripe, Linear, Airbnb, etc.) |
| `skills/brand/` | Brand voice, visual identity, messaging frameworks |
| `skills/design-system/` | Token architecture, component specifications, spacing/typography scales |
| `skills/frontend-slides/` | Frontend slides skill for HTML presentation generation |
| `settings.json.template` | Claude settings with secrets and paths replaced by `{{PLACEHOLDER}}` variables |

**Installed by bootstrap (not stored in repo):**
- 143 marketplace skills via `npx skills add` (34 marketing, 14 superpowers, 95 Google Workspace)
- `commands/gsd/` — GSD installs this via `/gsd:update`
- `skills/slidev/` — Large skill, cloned separately
- `gws` CLI — Google Workspace CLI, installed via Homebrew
- All ephemeral dirs: `cache/`, `sessions/`, `projects/`, etc.

### Marketplace skills (auto-installed)

| Source | Count | What |
|--------|-------|------|
| `coreyhaines31/marketingskills` | 34 | RevOps, CRO suite, SEO, copywriting, pricing, churn, analytics, sales enablement |
| `obra/superpowers` | 14 | Systematic debugging, TDD, parallel agent dispatch, verification, code review |
| `googleworkspace/cli` | 95 | Gmail, Calendar, Drive, Docs, Sheets, Tasks, Meet + workflow automations + recipes |

## Quick start

```bash
git clone git@github.com:swsounds42/claude-dotfiles.git ~/Desktop/claude-dotfiles
cd ~/Desktop/claude-dotfiles
./bootstrap.sh
```

The bootstrap script will:
1. Detect your OS
2. Ask for optional Salesforce MCP credentials (skip if you don't use it)
3. Symlink `agents/`, `commands/`, `hooks/`, `skills/`, and `CLAUDE.md` into `~/.claude/`
4. Generate `~/.claude/settings.json` from the template with your paths and credentials filled in
5. Install 143 marketplace skills from skills.sh (marketing, superpowers, Google Workspace)
6. Optionally install Slidev skill and `gws` CLI

## After bootstrap

A few things that need manual setup:

**GSD (Get Shit Done)** — the structured planning skill system:
```
Open Claude Code -> run /gsd:update
```
This installs `commands/gsd/` and the `gsd-check-update.js` session hook.

**Google Workspace CLI** — if you want Gmail/Calendar/Drive automation:
```bash
# Auth setup (requires GCP project with OAuth client)
gws auth setup --login
```

**Salesforce MCP** — if you use the Salesforce integration:
```bash
cd ~/Desktop/personal-os-main/core/mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Plugins:**
```
claude plugin install slack@claude-plugins-official
```

## Total brain surface area

| Layer | Count |
|-------|-------|
| Skills (knowledge files) | 148 (5 custom + 143 marketplace) |
| Commands (slash commands) | 36 |
| Specialist agents | 142 |
| Brand design references | 58 (on-demand via `npx getdesign@latest add <name>`) |

## Keeping it up to date

When you update your Claude config on your main machine:

```bash
cd ~/Desktop/claude-dotfiles
git add -A
git commit -m "update: [what changed]"
git push
```

On another machine:
```bash
git pull
# Re-run bootstrap only if settings.json.template changed or new marketplace skills added
./bootstrap.sh
```

Since `agents/`, `commands/`, `hooks/`, and `skills/` are symlinked (not copied), any `git pull` immediately reflects in `~/.claude/` — no re-run needed for most changes.

## Repo is private

Contains personal configuration, agent routing logic, and workflow files. Keep it private.
