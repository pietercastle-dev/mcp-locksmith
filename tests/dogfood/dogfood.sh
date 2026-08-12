#!/usr/bin/env bash
# Fresh-machine dogfood: the automatable slice of the v1.0 feature-complete
# checklist, on a truly clean Linux box. The repo is mounted read-only at /repo.
# Trigger-looking strings are built by concatenation on purpose.
set -u
T0=$(date +%s)
NPASS=0; NFAIL=0; FAILS=""
say()  { printf '\n== %s\n' "$*"; }
ok()   { echo "  PASS: $*"; NPASS=$((NPASS+1)); }
bad()  { echo "  FAIL: $*"; NFAIL=$((NFAIL+1)); FAILS="${FAILS}
- $*"; }

say "fresh clone (nothing preinstalled, no config, empty HOME)"
git clone -q /repo "$HOME/repo" || { bad "git clone"; exit 1; }
R="$HOME/repo"; ok "cloned"

say "install.sh with NO backend CLI on PATH (v1.0 regression: must survive)"
mkdir -p /home/dog/h1
out=$(env -i HOME=/home/dog/h1 PATH=/usr/bin:/bin bash "$R/install.sh" --non-interactive 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "exit 0" || bad "exit $rc: $(echo "$out" | tail -2)"
echo "$out" | grep -q "no secret backend CLI found" && ok "no-backend warning shown" || bad "no-backend warning missing"
[ -L /home/dog/h1/.local/bin/mcp-secret ] && ok "helpers linked" || bad "helpers not linked"

say "install.sh with sops+age available (Linux ranking: sops is the only option)"
export HOME=/home/dog/h2; mkdir -p "$HOME"; cd "$HOME" || exit 1
bash "$R/install.sh" --non-interactive >/tmp/i2.log 2>&1 && ok "exit 0" || bad "install: $(tail -2 /tmp/i2.log)"
export PATH="$HOME/.local/bin:$PATH"
grep -q "^MCP_SECRET_BACKEND=sops$" "$HOME/.config/mcp-secret/config" 2>/dev/null \
  && ok "config written, backend=sops" || bad "backend config wrong: $(cat "$HOME/.config/mcp-secret/config" 2>/dev/null)"

say "sops round-trip: encrypt, resolve full ref + short ref"
VAL="dogfood-not-a-real-secret-123"
KEY="$HOME/.config/sops/age/keys.txt"
if [ ! -f "$KEY" ]; then mkdir -p "$(dirname "$KEY")"; age-keygen -o "$KEY" 2>/dev/null; chmod 600 "$KEY"; fi
REC=$(age-keygen -y "$KEY")
SFILE="$HOME/.config/mcp-secret/secrets.sops.yaml"
printf 'DOG_SECRET: %s\n' "$VAL" > /tmp/plain.yaml
sops --encrypt --age "$REC" /tmp/plain.yaml > "$SFILE" && ok "encrypted" || bad "sops encrypt failed"
rm -f /tmp/plain.yaml
got=$(mcp-secret "sops://$SFILE#/DOG_SECRET" 2>/tmp/ms.err)
[ "$got" = "$VAL" ] && ok "full ref resolves" || bad "full ref: $(cat /tmp/ms.err)"
got2=$(mcp-secret DOG_SECRET 2>/tmp/ms2.err)
[ "$got2" = "$VAL" ] && ok "short ref resolves via machine default" || bad "short ref: $(cat /tmp/ms2.err)"

say "mcp-launch: value reaches the child process env, never the config"
printf 'import os,sys\nsys.exit(0 if os.environ.get("DOG_SECRET")=="%s" else 1)\n' "$VAL" > /tmp/checker.py
mcp-launch --secret "DOG_SECRET=sops://$SFILE#/DOG_SECRET" -- python3 /tmp/checker.py \
  && ok "spawn-time injection works" || bad "spawn-time injection failed"

say "pin, verify, and the rug-pull tripwire (env-driven fixture)"
mkdir -p "$HOME/proj"; cd "$HOME/proj" || exit 1
printf '{"mcpServers":{"fake":{"type":"stdio","command":"python3","args":["%s"]}}}\n' \
  "$R/plugins/mcp-secure/tests/fake_mcp_server.py" > .mcp.json
FAKE_TOOLS="alpha,beta" mcp-pin pin fake >/tmp/pin.log 2>&1 \
  && grep -q "pinned 2 tool" /tmp/pin.log && ok "pinned 2 tools" || bad "pin: $(tail -2 /tmp/pin.log)"
FAKE_TOOLS="alpha,beta" mcp-pin verify >/tmp/v1.log 2>&1 \
  && ok "verify: unchanged" || bad "clean verify failed: $(tail -2 /tmp/v1.log)"
FAKE_TOOLS="alpha,beta,gamma" mcp-pin verify >/tmp/v2.log 2>&1; rc=$?
# A non-zero exit alone isn't proof of drift detection — a crash or unreadable
# config also exits non-zero. Require BOTH: non-zero exit AND the literal
# DRIFT token mcp-pin prints on an actual tool-surface change.
if [ "$rc" -ne 0 ] && grep -q "DRIFT" /tmp/v2.log; then
  ok "rug-pull flagged: $(grep -o 'DRIFT.*' /tmp/v2.log | head -1)"
else
  bad "rug-pull NOT flagged (exit=$rc, DRIFT token present=$(grep -q DRIFT /tmp/v2.log && echo yes || echo no)): $(tail -5 /tmp/v2.log)"
fi

say "hooks fire from a plain clone (the dead-call-guard regression class)"
G="$R/plugins/mcp-secure/hooks/mcp-guard.py"
[ -x "$G" ] && ok "guard is executable" || bad "guard not executable"
A=$(printf '%s %s %s' "claude" "mcp" "add")           # concatenated on purpose
TOK=$(printf '%s%s' "ghp_" "EXAMPLEONLYnotarealtoken00")
ev() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
outd=$(ev "$A -s user foo -e TOKEN=$TOK -- bar" | python3 "$G" 2>&1)
echo "$outd" | grep -q '"deny"' && ok "literal secret in a config write -> deny" || bad "guard did not deny literal secret: $outd"
outa=$(ev "$A foo -e TOKEN_REF=keychain://svc/acct -- bar" | python3 "$G" 2>&1); rca=$?
# A crashing guard also produces output with no "deny" in it — that's not the
# same as a considered allow. Require a clean exit and no traceback too.
if [ "$rca" -ne 0 ] || echo "$outa" | grep -q "Traceback"; then
  bad "guard crashed on keychain ref (exit=$rca): $outa"
elif echo "$outa" | grep -q '"deny"'; then
  bad "keychain ref wrongly denied"
else
  ok "keychain ref allowed"
fi

say "doctor on the fresh setup"
if mcp-doctor >/tmp/doc.log 2>&1; then ok "doctor: all good"; else bad "doctor: $(grep -m2 -v '^$' /tmp/doc.log | tail -1)"; fi

say "Claude Code CLI slice: validate, marketplace add, plugin install"
claude --version >/dev/null 2>&1 && ok "claude CLI present ($(claude --version 2>/dev/null | head -1))" || bad "claude CLI missing"
if (cd "$R" && claude plugin validate --strict . >/tmp/val.log 2>&1); then
  ok "plugin validate --strict"
else bad "validate: $(tail -2 /tmp/val.log)"; fi
if claude plugin marketplace add "$R" >/tmp/mkt.log 2>&1; then
  ok "marketplace add from local clone"
  if claude plugin install mcp-secure@mcp-locksmith >/tmp/inst.log 2>&1; then
    ok "plugin install"
    hookcopy=$(find "$HOME/.claude" -name mcp-guard.py 2>/dev/null | head -1)
    if [ -n "$hookcopy" ]; then
      [ -x "$hookcopy" ] && ok "installed hook copy is executable" || bad "installed hook copy NOT executable (the 644 bug)"
    else bad "installed plugin: hook copy not found under ~/.claude"; fi
  else bad "plugin install: $(tail -2 /tmp/inst.log)"; fi
else bad "marketplace add: $(tail -2 /tmp/mkt.log)"; fi

ELAPSED=$(( $(date +%s) - T0 ))
say "SUMMARY: $NPASS passed, $NFAIL failed, ${ELAPSED}s elapsed (metric target: <300s + human time)"
[ -n "$FAILS" ] && printf 'Failures:%s\n' "$FAILS"
[ "$NFAIL" -eq 0 ]
