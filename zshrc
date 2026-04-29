
. "$HOME/.local/bin/env"

# direnv — auto-load .envrc files when cd'ing into directories
eval "$(direnv hook zsh)"

# Cap Claude Code's bash output buffer (default 30K → 15K cuts trailing noise tokens)
export BASH_MAX_OUTPUT_LENGTH=15000
