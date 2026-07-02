#!/usr/bin/env python3
"""SessionStart hook for mcp-secure — fast, and at most one nudge per repo.

Two cases, otherwise silent:
  - The git repo has NO MCP servers yet → suggest /mcp-secure:setup or :add.
  - Servers exist but aren't adopted into the harness (a literal secret sits in
    config, or some aren't pinned) → suggest /mcp-secure:audit, ONCE per project
    (a marker file stops it from nagging every session).

Only reads local files + regex — no subprocess — so it stays fast at session start.
"""
import glob
import hashlib
import json
import os
import re
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
home = os.path.expanduser("~")

# Only nudge inside a git repo.
if not os.path.isdir(os.path.join(cwd, ".git")):
    sys.exit(0)


def emit(msg):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": msg + org_suffix()}}))
    sys.exit(0)


def org_suffix():
    """If an org.json is present, append a pointer to the team's internal MCP docs."""
    p = os.path.expanduser(os.environ.get("MCP_ORG_CONFIG", "~/.config/mcp-secret/org.json"))
    try:
        org = json.load(open(p))
    except Exception:
        return ""
    bits = []
    if org.get("docsUrl"):
        bits.append(f"your org's MCP guide is at {org['docsUrl']}")
    if org.get("recommended"):
        bits.append(f"recommended tools: {', '.join(org['recommended'])}")
    return (" (" + "; ".join(bits) + ")") if bits else ""


# --- gather servers visible from here (project .mcp.json + user/project ~/.claude.json) ---
servers = {}
mcp_json = os.path.join(cwd, ".mcp.json")
if os.path.exists(mcp_json):
    try:
        for n, s in (json.load(open(mcp_json)).get("mcpServers") or {}).items():
            servers.setdefault(n, s)
    except Exception:
        pass
try:
    cfg = json.load(open(os.path.join(home, ".claude.json")))
    for n, s in (cfg.get("mcpServers") or {}).items():
        servers.setdefault(n, s)
    for n, s in (((cfg.get("projects") or {}).get(cwd) or {}).get("mcpServers") or {}).items():
        servers.setdefault(n, s)
except Exception:
    pass

# --- NO servers: the original "get started" nudge ---
if not servers:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    dirs = []
    if plugin_root:
        dirs.append(os.path.join(plugin_root, "bundles"))
    # the user's private bundles (their own / team vetted sets)
    dirs.append(os.environ.get("MCP_USER_BUNDLES") or
                os.path.join(home, ".config", "mcp-secret", "bundles"))
    bundles = sorted({os.path.splitext(os.path.basename(p))[0]
                      for d in dirs for p in glob.glob(os.path.join(d, "*.json"))})
    if not bundles:
        sys.exit(0)
    emit("This git repo has no MCP servers (tools) configured yet. Available bundles: "
         + ", ".join(bundles) + ". Briefly let the user know. If they're new to this, "
         "suggest /mcp-secure:setup for a guided walkthrough. Otherwise /mcp-secure:add "
         "adds a tool to this repo — a ready-made bundle, or a brand-new one it "
         "safety-checks first.")

# --- servers EXIST: nudge to adopt them, at most once per project ---
SEEN = os.path.expanduser("~/.config/mcp-secret/nudge-seen.json")
try:
    seen = json.load(open(SEEN))
except Exception:
    seen = {}
if seen.get(cwd):
    sys.exit(0)

# A literal credential already sitting in config (mirrors mcp-guard.py shapes).
SECRET_VAL = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|AIza[0-9A-Za-z_\-]{30,}|"
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----|[a-z][a-z0-9+.\-]*://[^/?#@\s:]+:[^/?#@\s]+@)")


def has_inline_secret(s):
    vals = (list((s.get("env") or {}).values()) + list(s.get("args") or [])
            + list((s.get("headers") or {}).values()))
    return any(isinstance(v, str) and SECRET_VAL.search(v) for v in vals)


inline = any(has_inline_secret(s) for s in servers.values() if isinstance(s, dict))

# Servers with no pin baseline (best-effort; matches mcp-pin's identity scheme).
try:
    pins = json.load(open(os.path.expanduser("~/.config/mcp-secret/pins.json")))
except Exception:
    pins = {}


def expand(x):
    return os.path.expandvars(x) if isinstance(x, str) else x


def identity(name, command, args):
    raw = name + "\0" + command + "\0" + json.dumps(args, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


unpinned = []
for n, s in servers.items():
    if not isinstance(s, dict):
        continue
    cmd = expand(s.get("command", "")); args = [expand(a) for a in (s.get("args") or [])]
    if identity(n, cmd, args) not in pins:
        unpinned.append(n)

if not (inline or unpinned):
    sys.exit(0)  # everything already adopted — stay silent

# Record so we don't nudge this project again.
try:
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    seen[cwd] = True
    json.dump(seen, open(SEEN, "w"))
except Exception:
    pass

parts = []
if inline:
    parts.append("at least one has a credential sitting in plain text in its config")
if unpinned:
    n = len(unpinned)
    parts.append(("1 isn't" if n == 1 else f"{n} aren't") + " pinned/adopted yet")
emit("This project already has MCP tools that mcp-secure hasn't adopted — "
     + "; ".join(parts) + ". Installing the plugin doesn't change pre-existing tools on "
     "its own. Briefly let the user know and offer to run /mcp-secure:audit — it moves "
     "any plaintext secret into their vault and pins the tools. Offer once; don't push.")
