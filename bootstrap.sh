#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# bootstrap.sh — Set up ~/.claude from claude-dotfiles
# ─────────────────────────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo ""
echo "Claude Dotfiles Bootstrap"
echo "========================="
echo "Repo: $REPO_DIR"
echo "Target: $CLAUDE_DIR"
echo ""

# ─── OS detection ────────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="linux"
fi
echo "Detected OS: $OS"

# ─── Create ~/.claude if it doesn't exist ────────────────────
mkdir -p "$CLAUDE_DIR"

# ─── Optional: Salesforce env vars ───────────────────────────
echo ""
echo "Salesforce MCP setup (press Enter to skip each):"
read -rp "  SALESFORCE_CLIENT_ID: " SF_CLIENT_ID
read -rp "  SALESFORCE_CLIENT_SECRET: " SF_CLIENT_SECRET
read -rp "  SALESFORCE_INSTANCE_URL (e.g. https://yourorg.my.salesforce.com): " SF_INSTANCE_URL
read -rp "  PERSONAL_OS_PATH (path to personal-os-main project, e.g. $HOME/Desktop/personal-os-main): " PERSONAL_OS_PATH

# Use defaults if blank
SF_CLIENT_ID="${SF_CLIENT_ID:-REPLACE_WITH_SALESFORCE_CLIENT_ID}"
SF_CLIENT_SECRET="${SF_CLIENT_SECRET:-REPLACE_WITH_SALESFORCE_CLIENT_SECRET}"
SF_INSTANCE_URL="${SF_INSTANCE_URL:-https://yourorg.my.salesforce.com}"
PERSONAL_OS_PATH="${PERSONAL_OS_PATH:-$HOME/Desktop/personal-os-main}"

# ─── Symlink directories ──────────────────────────────────────
echo ""
echo "Creating symlinks..."

link_dir() {
  local src="$REPO_DIR/$1"
  local dst="$CLAUDE_DIR/$1"

  if [[ ! -d "$src" ]]; then
    echo "  SKIP $1 (not found in repo)"
    return
  fi

  if [[ -L "$dst" ]]; then
    echo "  UPDATE symlink: $dst -> $src"
    rm "$dst"
  elif [[ -d "$dst" ]]; then
    echo "  BACKUP existing dir: $dst -> ${dst}.bak"
    mv "$dst" "${dst}.bak"
  fi

  ln -s "$src" "$dst"
  echo "  LINKED: $dst -> $src"
}

link_dir "commands"
link_dir "agents"
link_dir "hooks"
link_dir "skills"

# CLAUDE.md (file, not dir)
CLAUDE_MD_SRC="$REPO_DIR/CLAUDE.md"
CLAUDE_MD_DST="$CLAUDE_DIR/CLAUDE.md"
if [[ -f "$CLAUDE_MD_SRC" ]]; then
  if [[ -L "$CLAUDE_MD_DST" ]]; then
    rm "$CLAUDE_MD_DST"
  elif [[ -f "$CLAUDE_MD_DST" ]]; then
    mv "$CLAUDE_MD_DST" "${CLAUDE_MD_DST}.bak"
    echo "  BACKUP: ${CLAUDE_MD_DST}.bak"
  fi
  ln -s "$CLAUDE_MD_SRC" "$CLAUDE_MD_DST"
  echo "  LINKED: $CLAUDE_MD_DST -> $CLAUDE_MD_SRC"
fi

# ─── Generate settings.json from template ────────────────────
echo ""
echo "Generating settings.json..."

TEMPLATE="$REPO_DIR/settings.json.template"
SETTINGS_OUT="$CLAUDE_DIR/settings.json"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "  WARNING: settings.json.template not found, skipping"
else
  sed \
    -e "s|{{HOME}}|$HOME|g" \
    -e "s|{{PERSONAL_OS_PATH}}|$PERSONAL_OS_PATH|g" \
    -e "s|{{SALESFORCE_CLIENT_ID}}|$SF_CLIENT_ID|g" \
    -e "s|{{SALESFORCE_CLIENT_SECRET}}|$SF_CLIENT_SECRET|g" \
    -e "s|{{SALESFORCE_INSTANCE_URL}}|$SF_INSTANCE_URL|g" \
    "$TEMPLATE" > "$SETTINGS_OUT"
  echo "  CREATED: $SETTINGS_OUT"

  # Fix the python path — on a new machine this needs to point to the actual venv
  if [[ "$OS" == "macos" ]]; then
    PYTHON_PATH="$PERSONAL_OS_PATH/core/mcp/.venv/bin/python3"
    # Use python3.14 if available, fall back to python3
    if [[ -f "$PERSONAL_OS_PATH/core/mcp/.venv/bin/python3.14" ]]; then
      PYTHON_PATH="$PERSONAL_OS_PATH/core/mcp/.venv/bin/python3.14"
    fi
    # Patch the command field in settings.json
    if command -v python3 &>/dev/null; then
      sed -i.bak "s|{{HOME}}/.venv/bin/python3|$PYTHON_PATH|g" "$SETTINGS_OUT" 2>/dev/null || true
      rm -f "${SETTINGS_OUT}.bak"
    fi
  fi
fi

# ─── Post-install instructions ────────────────────────────────
echo ""
echo "======================================================"
echo "Bootstrap complete. A few things to finish manually:"
echo "======================================================"
echo ""
echo "1. Install GSD (Get Shit Done skill system):"
echo "   Open Claude Code and run: /gsd:update"
echo "   This installs commands/gsd/ and hooks/gsd-check-update.js"
echo ""
echo "2. Install the Slidev skill (large — cloned separately):"
echo "   git clone https://github.com/YOUR_SLIDEV_REPO ~/.claude/skills/slidev"
echo "   (Or ask Claude where to get it)"
echo ""
echo "3. Install plugins:"
echo "   Open Claude Code and run: claude plugin install slack@claude-plugins-official"
echo ""
echo "4. Salesforce MCP — if you use it:"
echo "   cd $PERSONAL_OS_PATH/core/mcp"
echo "   python3 -m venv .venv && source .venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "5. Verify settings.json looks correct:"
echo "   cat $CLAUDE_DIR/settings.json"
echo ""
echo "That's it. Open Claude Code and you should be good to go."
echo ""
