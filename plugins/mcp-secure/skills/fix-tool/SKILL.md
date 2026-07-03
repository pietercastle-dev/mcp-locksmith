---
name: fix-tool
description: Diagnose and fix an external tool / MCP server that isn't working, e.g. "the Slack tool stopped working", "my browser tool is broken", "the database server won't connect", "why is this MCP erroring?". Use when an installed tool fails, errors, times out, or disappeared. Runs launch diagnostics that surface the server's own error output, then walks the matching fix.
---

The user has a broken tool (MCP server). **Diagnose from evidence, don't
guess-edit config**: run the mcp-secure *fix* flow.

Authoritative steps: read and follow `${CLAUDE_PLUGIN_ROOT}/commands/fix.md` in
this plugin (if that path doesn't resolve, find `commands/fix.md` under the
mcp-secure plugin).

Non-negotiable safety rules (apply even if you can't read the file):
- Diagnose with `mcp-doctor` and `mcp-doctor --launch` (read-only; `--launch`
  shows the failing server's own stderr, usually the answer).
- **Never inline a secret to "test"**: references stay references; if a ref is
  wrong, fix the ref or the vault item.
- If the tool works again but its tools drifted (`mcp-pin verify`), re-vet
  before re-pinning.
