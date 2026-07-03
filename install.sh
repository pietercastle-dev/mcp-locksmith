#!/usr/bin/env bash
# mcp-locksmith: post-install setup for the mcp-secure plugin.
#
# The plugin (installed via /plugin install) provides the hooks, commands,
# bundles, and any global servers. This script does the two things a plugin
# can't do for you:
#   1. Put `mcp-secret` and `mcp-launch` on your PATH (~/.local/bin), so a
#      project's committed .mcp.json can use the bare `mcp-launch` command.
#   2. Write ~/.config/mcp-secret/config, your default secret backend.
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
chmod 700 "$CFG_DIR"   # the config names your vault/file, keep it owner-only

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
  # Sanity-check a kept config so a previously-bogus backend gets flagged.
  kept_backend="$(grep -E '^[[:space:]]*MCP_SECRET_BACKEND[[:space:]]*=' "$CFG" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '[:space:]')"
  case "$kept_backend" in
    op|sops|bw) ;;
    "") warn "no MCP_SECRET_BACKEND in $CFG. Short refs won't resolve. Edit it, or 'rm $CFG' and re-run." ;;
    *)  warn "MCP_SECRET_BACKEND in $CFG is '$kept_backend', not a valid backend (op/sops/bw). 'rm $CFG' and re-run, or fix it by hand." ;;
  esac
elif [ "${#avail[@]}" -eq 0 ]; then
  warn "no secret backend CLI found (op / sops / bw). Install one, then create $CFG."
else
  default="${MCP_SECRET_BACKEND:-}"
  if [ -z "$default" ] && [ "$NONINTERACTIVE" -eq 0 ] && [ -r /dev/tty ]; then
    echo "Detected secret backends: ${avail[*]}"
    printf "Default backend for short refs [%s]: " "${avail[0]}"
    read -r default </dev/tty || true
  fi
  # Strip stray whitespace, then validate: a backend MUST be op/sops/bw. This
  # guards against a fat-fingered or pasted answer landing in the config as a
  # bogus backend (which would break every secret resolution).
  default="$(printf '%s' "$default" | tr -d '[:space:]')"
  [ -z "$default" ] && default="${avail[0]}"
  case "$default" in
    op|sops|bw) ;;
    *) warn "'$default' isn't a known backend (op/sops/bw); using ${avail[0]} instead."
       default="${avail[0]}" ;;
  esac
  {
    echo "# mcp-secret machine config, see the mcp-secure README"
    echo "MCP_SECRET_BACKEND=$default"
    case "$default" in
      op)   echo "MCP_OP_VAULT=${MCP_OP_VAULT:-Private}" ;;
      sops) echo "MCP_SOPS_FILE=${MCP_SOPS_FILE:-$CFG_DIR/secrets.sops.yaml}" ;;
    esac
  } > "$CFG"
  info "wrote $CFG (default backend: $default). Edit vault/file as needed"
fi
[ -f "$CFG" ] && chmod 600 "$CFG"

# 2b) SOPS path: make sure an age private key exists (the root of trust).
# Read the backend by PARSING the config (grep), never by sourcing it.
ACTIVE_BACKEND="$(grep -E '^[[:space:]]*MCP_SECRET_BACKEND[[:space:]]*=' "$CFG" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '[:space:]')"
if [ "$ACTIVE_BACKEND" = "sops" ]; then
  AGE_KEY="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
  if [ -n "${SOPS_AGE_KEY:-}" ] || [ -f "$AGE_KEY" ]; then
    if [ -f "$AGE_KEY" ]; then          # tighten perms even on a pre-existing key
      chmod 700 "$(dirname "$AGE_KEY")" 2>/dev/null || true
      chmod 600 "$AGE_KEY" 2>/dev/null || true
    fi
    info "age key present: $AGE_KEY"
  elif ! command -v age-keygen >/dev/null 2>&1; then
    warn "SOPS backend selected but 'age' isn't installed. Run 'brew install sops age' (see plugins/mcp-secure/BACKENDS.md), then re-run."
  else
    do_gen=1
    if [ "$NONINTERACTIVE" -eq 0 ] && [ -r /dev/tty ]; then
      printf "No age key found. Generate one now at %s? [Y/n]: " "$AGE_KEY"
      read -r ans </dev/tty || true
      case "$ans" in [Nn]*) do_gen=0 ;; esac
    fi
    if [ "$do_gen" -eq 1 ]; then
      # mkdir -p -m applies the mode only to the deepest dir (SC2174); chmod
      # explicitly so the key dir is 700 even when parents pre-existed.
      mkdir -p "$(dirname "$AGE_KEY")"
      chmod 700 "$(dirname "$AGE_KEY")"
      ( umask 077; age-keygen -o "$AGE_KEY" >/dev/null 2>&1 )
      chmod 600 "$AGE_KEY"
      info "generated age key (chmod 600): $AGE_KEY"
      pub="$(age-keygen -y "$AGE_KEY" 2>/dev/null || true)"
      [ -n "$pub" ] && echo "   public key (use as the recipient in .sops.yaml):"
      [ -n "$pub" ] && echo "     $pub"
      warn "NEVER commit $AGE_KEY (the private key). Add it to .gitignore and back it up. Lose it and your secrets are unrecoverable."
    else
      info "skipped age-key generation. See plugins/mcp-secure/BACKENDS.md when ready."
    fi
  fi
fi

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) warn "$BIN_DIR is not on your PATH. Add it so the resolver is reachable when MCP servers spawn." ;;
esac

echo
info "All set on the command-line side."
echo "   Next, in Claude Code just run:  /mcp-secure:setup"
echo "   It'll walk you through the rest in plain language."
echo "   Setting up a secret vault (1Password / Bitwarden / SOPS)? See"
echo "   plugins/mcp-secure/BACKENDS.md for the secure step-by-step."
echo
echo "   (If you haven't installed the plugin yet:"
echo "      /plugin marketplace add $REPO"
echo "      /plugin install mcp-secure@mcp-locksmith )"
