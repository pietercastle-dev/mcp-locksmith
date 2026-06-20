#!/usr/bin/env python3
"""PreToolUse guard for the mcp-secure MCP harness.

Three rules (see README.md and the CLAUDE.md convention snippet):

1. No user/global-scope MCP servers: `claude mcp add -s user …` → DENY.
2. No plaintext secrets in MCP config — both an `-e NAME=<secret>` on
   `claude mcp add` AND a secret-shaped value written into any `*.mcp.json` /
   `~/.claude.json` via Write/Edit/MultiEdit → DENY, with a pointer to the
   mcp-secret / wrapper pattern. This is the #1 documented MCP footgun.
3. Hand-editing ~/.claude.json's top-level mcpServers is the documented escape
   hatch, so it's allowed but surfaced via an `ask` confirmation.

Registered for both the Bash matcher and the Write|Edit|MultiEdit matcher; it
branches on tool_name.
"""
import json
import os
import re
import sys


def out(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")
ti = data.get("tool_input") or {}

# Key names that mark a value as a credential.
SECRET_KEY = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY|"
    r"CREDENTIAL|CLIENT_SECRET|\bKEY\b|\bPAT\b)", re.I)
# Values that are obviously credentials regardless of key name.
SECRET_VAL = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")
# Forms that are SAFE: env expansion, a bare $VAR, or an mcp-secret reference.
SAFE_VAL = re.compile(r"^\s*(\$\{[^}]+\}|\$[A-Za-z_]\w*|op://|sops://|bw://)")

WRAPPER_HINT = (
    "Don't put a literal secret in MCP config — it persists to disk and can reach "
    "Claude's context. Use the harness pattern: keep the secret in your backend and "
    "reference it via mcp-launch, e.g. command=mcp-launch, "
    "args=[\"--secret\",\"NAME=op://Vault/item/field\",\"--\",<server>...]. The token is "
    "resolved at spawn, never stored. See the mcp-secure README and VETTING.md.")


def looks_secret(key, val):
    if not isinstance(val, str) or not val.strip():
        return False
    if SAFE_VAL.search(val):
        return False
    if SECRET_VAL.search(val):
        return True
    if key and SECRET_KEY.search(key) and len(val.strip()) >= 12:
        return True
    return False


# ---- Bash: `claude mcp add …` ----
if tool == "Bash":
    cmd = ti.get("command", "")
    if re.search(r"\bclaude\b.+?\bmcp\b.+?\badd\b", cmd, re.S):
        # A literal secret is never OK, at any scope.
        for m in re.finditer(
                r"(?:-e|--env)[=\s]+([A-Za-z_]\w*)=('[^']*'|\"[^\"]*\"|[^\s]+)", cmd):
            k, v = m.group(1), m.group(2).strip("'\"")
            if looks_secret(k, v):
                out("deny", "Blocked: literal secret in `claude mcp add -e`. " + WRAPPER_HINT)
        # Global/user scope is allowed but deliberate — it loads in EVERY repo, so
        # confirm. Reserve it for the curated "everywhere" set (e.g. Slack at work).
        if re.search(r"(?:-s|--scope)[=\s]+user\b", cmd):
            out("ask",
                "This adds a GLOBAL (user-scope) MCP server — it loads in every repo. "
                "That's intended only for the curated always-on set (e.g. Slack). For a "
                "server a single project needs, use -s project instead. Confirm if this "
                "really belongs everywhere; for a reproducible always-on set, use a "
                "globals plugin (see /mcp-secure:mcp-global).")
    sys.exit(0)

# ---- Write/Edit/MultiEdit into MCP config files ----
if tool in ("Write", "Edit", "MultiEdit"):
    path = ti.get("file_path", "") or ""
    if not path:
        sys.exit(0)
    base = os.path.basename(path)
    is_mcp = base == ".mcp.json"
    is_global = os.path.realpath(path) == os.path.realpath(
        os.path.expanduser("~/.claude.json"))
    if not (is_mcp or is_global):
        sys.exit(0)

    chunks = []
    if isinstance(ti.get("content"), str):
        chunks.append(ti["content"])
    if isinstance(ti.get("new_string"), str):
        chunks.append(ti["new_string"])
    for e in ti.get("edits", []) or []:
        if isinstance(e, dict) and isinstance(e.get("new_string"), str):
            chunks.append(e["new_string"])
    blob = "\n".join(chunks)

    for k, v in re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', blob):
        if looks_secret(k, v):
            out("deny", f"Blocked: '{k}' looks like a literal secret in {base}. " + WRAPPER_HINT)

    if is_global and '"mcpServers"' in blob:
        out("ask",
            "This edits ~/.claude.json's global MCP scope, which loads in every repo. "
            "That's the documented escape hatch — confirm you intend a global server "
            "rather than a project-scoped one.")
    sys.exit(0)

sys.exit(0)
