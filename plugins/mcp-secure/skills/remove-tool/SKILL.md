---
name: remove-tool
description: Remove, uninstall, disconnect, or delete an external tool / MCP server — e.g. "remove the GitHub server", "uninstall the Slack tool", "disconnect Postgres", "I don't use the browser tool anymore". Use whenever the user wants to take an existing tool out. Unregisters it AND makes sure its API key gets revoked so no live credential is left orphaned.
---

The user wants to remove a tool (an MCP server). The risky part isn't the config line —
it's a **forgotten-but-still-valid credential**. Run the mcp-secure *remove* flow.

Authoritative steps: read and follow `${CLAUDE_PLUGIN_ROOT}/commands/remove.md` in this
plugin (or find `commands/remove.md` under the mcp-secure plugin).

The essentials (apply even if you can't read the file):
1. **Find it and its scope** (project `.mcp.json` vs user `~/.claude.json`), and check
   whether it uses a secret reference. Confirm with the user before changing anything.
2. **Unregister** it from the scope it lives in (`claude mcp remove <name>` or edit the
   right config). Don't touch other servers.
3. **Revoke the secret — the point of this flow.** If it used a key, tell the user to
   revoke/rotate that token at the provider and delete the now-unused vault item, *only
   if no other tool still uses it*. Never delete vault items or revoke tokens yourself.
4. **Clean up the pin:** `mcp-pin unpin <name>`.
5. Remind them it takes effect on the next session start.
