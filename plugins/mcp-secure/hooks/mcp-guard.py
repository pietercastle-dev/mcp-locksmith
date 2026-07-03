#!/usr/bin/env python3
"""PreToolUse guard for the mcp-secure MCP harness.

Three rules (see README.md and the CLAUDE.md convention snippet):

1. No user/global-scope MCP servers: `claude mcp add -s user …` → DENY.
2. No plaintext secrets in MCP config. A secret-shaped value is blocked whether it
   reaches config via `claude mcp add -e/--env`, `claude mcp add-json '<payload>'`,
   a shell redirect/heredoc/tee into a `*.mcp.json` / `~/.claude.json`, OR a
   Write/Edit/MultiEdit into those files, including secrets tucked in an `args`
   array, not just `env` key/values. DENY, with a pointer to the mcp-launch pattern.
   This is the #1 documented MCP footgun.
3. Hand-editing ~/.claude.json's top-level mcpServers is the documented escape
   hatch, so it's allowed but surfaced via an `ask` confirmation.

This is defense-in-depth, not a sandbox: it fails OPEN (malformed input or an
unrecognized command shape is allowed) so it can't brick the user. Treat it as a
safety net that catches the common footguns, not a guarantee. The real rule is
"never write a literal secret into config in the first place" (see VETTING.md).

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

# Key names that mark a value as a credential (also matched against header names,
# so AUTHORIZATION/COOKIE are here even though they're headers, not env keys).
SECRET_KEY = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY|"
    r"CREDENTIAL|CLIENT_SECRET|AUTHORIZATION|\bCOOKIE\b|\bKEY\b|\bPAT\b)", re.I)
# Values that are obviously credentials regardless of key name or position.
SECRET_VAL = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|"
    r"AIza[0-9A-Za-z_\-]{30,}|"                              # Google API key
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----|"                   # PEM private key
    r"[a-z][a-z0-9+.\-]*://[^/?#@\s:]+:[^/?#@\s]+@)")        # creds in a URL/DSN
# NOTE: deliberately NOT matching bare high-entropy hex. Git SHAs and content
# hashes legitimately appear in configs and would be false positives.
# Forms that are SAFE: env expansion, a bare $VAR, or an mcp-secret reference,
# optionally behind an auth scheme, so `Bearer ${TOKEN}` reads as safe too.
SAFE_VAL = re.compile(
    r"^\s*(?:(?:Bearer|Basic|Token)\s+)?(\$\{[^}]+\}|\$[A-Za-z_]\w*|op://|sops://|bw://)",
    re.I)
# Basenames that identify an MCP config file written via the shell.
CONFIG_BASENAMES = (".mcp.json", ".claude.json")

WRAPPER_HINT = (
    "Don't put a literal secret in MCP config. It persists to disk and can reach "
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


def find_secret(blob):
    """Return a short label for the offending secret, or None.

    Catches a credential two ways: (a) a value-shaped token anywhere in the text.
    Covers `args` arrays, add-json payloads, and shell redirects where there's no
    key to anchor on; (b) a `"key": "value"` pair whose key implies a secret.
    """
    if not isinstance(blob, str) or not blob:
        return None
    if SECRET_VAL.search(blob):
        return "a credential-shaped value"
    for k, v in re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', blob):
        if looks_secret(k, v):
            return f"'{k}'"
    return None


def scan_json(obj, key=None):
    """Walk a parsed JSON value; return a label for the first secret, or None.

    Structural (not regex), so it sees secrets in `args` arrays and nested objects,
    and isn't fooled by escaped quotes / whitespace the way a flat `"k":"v"` regex is.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            r = scan_json(v, k)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = scan_json(v, key)
            if r:
                return r
    elif isinstance(obj, str):
        if SECRET_VAL.search(obj):
            return "a credential-shaped value"
        if looks_secret(key, obj):
            return f"'{key}'"
    return None


def writes_mcp_config(cmd):
    """True if the Bash command redirects/tees into an MCP config file."""
    for tgt in re.findall(r'(?:>>?|\btee\b(?:\s+-a)?)\s+"?([^\s"\';|&)]+)', cmd):
        if os.path.basename(tgt) in CONFIG_BASENAMES:
            return True
    return False


# ---- Bash: `claude mcp add …` and shell writes to MCP config ----
if tool == "Bash":
    cmd = ti.get("command", "")
    is_add = bool(re.search(r"\bclaude\b.+?\bmcp\b.+?\badd\b", cmd, re.S))
    # `import` ingests an external config file/stream into MCP config too.
    is_import = bool(re.search(r"\bclaude\b.+?\bmcp\b.+?\bimport\b", cmd, re.S))
    if is_add or is_import or writes_mcp_config(cmd):
        # Explicit `-e/--env NAME=literal`. Catches custom-named secrets that
        # aren't a recognizable token shape.
        for m in re.finditer(
                r"(?:-e|--env)[=\s]+([A-Za-z_]\w*)=('[^']*'|\"[^\"]*\"|[^\s]+)", cmd):
            k, v = m.group(1), m.group(2).strip("'\"")
            if looks_secret(k, v):
                out("deny", "Blocked: literal secret in `claude mcp add -e`. " + WRAPPER_HINT)
        # `--header/-H "Name: value"` on http/sse adds. An opaque bearer/API-key
        # value has no recognizable token shape, so anchor on the header name.
        for m in re.finditer(
                r"(?:-H|--header)[=\s]+('[^']*'|\"[^\"]*\"|[^\s]+)", cmd):
            name, sep, val = m.group(1).strip("'\"").partition(":")
            if sep and looks_secret(name.strip(), val.strip()):
                out("deny",
                    "Blocked: literal secret in `--header`. For a remote server "
                    "prefer OAuth (no static secret at all); if a header is "
                    "required, resolve it at connect time via a headersHelper + "
                    "mcp-secret instead of a stored value. See the mcp-secure README.")
        # Value-shaped secrets anywhere: add-json payloads, heredocs, redirects, tee.
        what = find_secret(cmd)
        if what:
            out("deny", f"Blocked: {what} looks like a literal secret headed into MCP "
                        f"config. " + WRAPPER_HINT)
    # Global/user scope is allowed but deliberate. It loads in EVERY repo, so
    # confirm. Reserve it for the curated "everywhere" set (e.g. Slack at work).
    if is_add and re.search(r"(?:-s|--scope)[=\s]+user\b", cmd):
        out("ask",
            "This adds a GLOBAL (user-scope) MCP server. It loads in every repo. "
            "That's intended only for the curated always-on set (e.g. Slack). For a "
            "server a single project needs, use -s project instead. Confirm if this "
            "really belongs everywhere; for a reproducible always-on set, use a "
            "globals plugin (see /mcp-secure:always-on).")
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

    # Prefer a structural scan: if the written blob is valid JSON (a full Write),
    # walk it so escaped quotes and args-array secrets can't hide. Fragments (most
    # Edits) aren't valid JSON on their own. Fall back to the text scan.
    try:
        what = scan_json(json.loads(blob))
    except Exception:
        what = find_secret(blob)
    if what:
        out("deny", f"Blocked: {what} looks like a literal secret in {base}. " + WRAPPER_HINT)

    if is_global and '"mcpServers"' in blob:
        out("ask",
            "This edits ~/.claude.json's global MCP scope, which loads in every repo. "
            "That's the documented escape hatch. Confirm you intend a global server "
            "rather than a project-scoped one.")
    sys.exit(0)

sys.exit(0)
