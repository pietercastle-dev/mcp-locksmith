#!/usr/bin/env bash
# mcp-locksmith — post-install setup for the mcp-secure plugin.
#
# The plugin (installed via /plugin install) provides the hooks, commands,
# bundles, and any global servers. This script does the two things a plugin
# can't do for you:
#   1. Put `mcp-secret` and `mcp-launch` on your PATH (~/.local/bin), so a
#      project's committed .mcp.json can use the bare `mcp-launch` command.
#   2. Write ~/.config/mcp-secret/config — your default secret backend.
#
# Idempotent. Run once per machine (and again if you change backends).
#   bash install.sh                 # interactive
#   bash install.sh --non-interactive
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="$REPO/plugins/mcp-secure/bin"
BIN_DIR="$HOME/.local/bin"
CFG_DIR="$HOME/.config/mcp-secret"
NONINTERACTIVE=0
[ "${1:-}" = "--non-interactive" ] && NONINTERACTIVE=1

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }

mkdir -p "$BIN_DIR" "$CFG_DIR"

# 1) Resolver + launcher on PATH (symlinked so `git pull` propagates).
for b in mcp-secret mcp-launch mcp-bundles mcp-doctor mcp-pin; do
  chmod +x "$BIN_SRC/$b"
  ln -sfn "$BIN_SRC/$b" "$BIN_DIR/$b"
  info "linked $BIN_DIR/$b"
done

# 2) Secret backend default.
avail=()
command -v op   >/dev/null 2>&1 && avail+=("op")
command -v sops >/dev/null 2>&1 && avail+=("sops")
command -v bw   >/dev/null 2>&1 && avail+=("bw")

CFG="$CFG_DIR/config"
if [ -e "$CFG" ]; then
  info "mcp-secret config kept (exists): $CFG"
elif [ "${#avail[@]}" -eq 0 ]; then
  warn "no secret backend CLI found (op / sops / bw). Install one, then create $CFG."
else
  default="${MCP_SECRET_BACKEND:-}"
  if [ -z "$default" ] && [ "$NONINTERACTIVE" -eq 0 ] && [ -r /dev/tty ]; then
    echo "Detected secret backends: ${avail[*]}"
    printf "Default backend for short refs [%s]: " "${avail[0]}"
    read -r default </dev/tty || true
  fi
  [ -z "$default" ] && default="${avail[0]}"
  {
    echo "# mcp-secret machine config — see the mcp-secure README"
    echo "MCP_SECRET_BACKEND=$default"
    case "$default" in
      op)   echo "MCP_OP_VAULT=${MCP_OP_VAULT:-Private}" ;;
      sops) echo "MCP_SOPS_FILE=${MCP_SOPS_FILE:-$CFG_DIR/secrets.sops.yaml}" ;;
    esac
  } > "$CFG"
  info "wrote $CFG (default backend: $default) — edit vault/file as needed"
fi

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) warn "$BIN_DIR is not on your PATH — add it so the resolver is reachable when MCP servers spawn." ;;
esac

echo
info "Done. If you haven't yet, install the plugin:"
echo "   /plugin marketplace add $REPO"
echo "   /plugin install mcp-secure@mcp-locksmith"
