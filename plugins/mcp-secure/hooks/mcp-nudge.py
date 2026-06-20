#!/usr/bin/env python3
"""SessionStart hook: nudge when a git repo has no MCP servers configured.

Stays silent unless the current project is a git repo with neither a committed
.mcp.json nor any local (private) MCP servers. When it fires, it injects context
telling Claude to offer the /mcp-setup bundle picker.
"""
import glob
import json
import os
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

# Already carries a committed bundle.
if os.path.exists(os.path.join(cwd, ".mcp.json")):
    sys.exit(0)

# Already has local (private) servers configured for this path.
try:
    cfg = json.load(open(os.path.join(home, ".claude.json")))
    if cfg.get("projects", {}).get(cwd, {}).get("mcpServers"):
        sys.exit(0)
except Exception:
    pass

# Bundles ship inside the plugin; CLAUDE_PLUGIN_ROOT is set for plugin hooks.
plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
bundle_dir = (os.path.join(plugin_root, "bundles") if plugin_root
              else os.path.join(home, ".claude", "mcp-bundles"))
bundles = sorted(
    os.path.splitext(os.path.basename(p))[0]
    for p in glob.glob(os.path.join(bundle_dir, "*.json"))
)
if not bundles:
    sys.exit(0)

msg = (
    "This git repo has no MCP servers configured yet. Available bundles: "
    + ", ".join(bundles)
    + ". Briefly let the user know, and if they want any, run /mcp-secure:mcp-setup "
    "to pick and install them into this repo's .mcp.json. To add a brand new "
    "(un-vetted) server, use /mcp-secure:mcp-add, which runs the security vetting flow."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": msg,
    }
}))
sys.exit(0)
