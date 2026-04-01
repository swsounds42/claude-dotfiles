# claude-dotfiles

Portable backup of my `~/.claude/` configuration. Clone this on any machine to bootstrap a full Claude Code setup with all agents, skills, hooks, and commands in place.

## What's included

| Path | Contents |
|------|----------|
| `CLAUDE.md` | Global Claude instructions — Jarvis persona, auto-routing rules, working style |
| `agents/` | 142 specialist agent definitions (react-specialist, python-pro, devops-engineer, etc.) |
| `commands/` | All installed skills — n8n, content writing, design, research, and more |
| `hooks/` | `context-statusline.js` and `context-watchdog.js` — context window monitoring |
| `skills/frontend-slides/` | Frontend slides skill for HTML presentation generation |
| `settings.json.template` | Claude settings with secrets and paths replaced by `{{PLACEHOLDER}}` variables |

**Not included (reinstallable):**
- `commands/gsd/` — GSD installs this via `/gsd:update`
- `skills/slidev/` — Large skill, cloned separately
- `hooks/gsd-check-update.js` — GSD installs this
- All ephemeral dirs: `cache/`, `sessions/`, `projects/`, etc.

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

## After bootstrap

A few things that need manual setup:

**GSD (Get Shit Done)** — the structured planning skill system:
```
Open Claude Code → run /gsd:update
```
This installs `commands/gsd/` and the `gsd-check-update.js` session hook.

**Slidev skill** — bootstrap prompts to install this (99MB), or manually:
```bash
git clone --depth 1 https://github.com/slidevjs/slidev.git ~/.claude/skills/slidev
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
# Re-run bootstrap only if settings.json.template changed
./bootstrap.sh
```

Since `agents/`, `commands/`, `hooks/`, and `skills/` are symlinked (not copied), any `git pull` immediately reflects in `~/.claude/` — no re-run needed for most changes.

## Repo is private

Contains personal configuration, agent routing logic, and workflow files. Keep it private.
