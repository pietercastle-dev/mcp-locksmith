---
description: Add MCP server bundle(s) to the current repo's .mcp.json
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`) — say "tool" rather than "MCP server", explain the *why* in
everyday terms, don't paste raw output or jargon without translating it, and match
their technical level. The numbered steps below are for you, not the user.

Add one or more ready-made **tools** (vetted bundles that ship with the plugin) to
**this project's** config (`.mcp.json`).

Steps:

1. Find the bundles directory by running `mcp-bundles` (a helper on PATH that prints the path), then list it: `ls "$(mcp-bundles)"/*.json`. Read each bundle. Ignore any `_comment` key — it's documentation.
2. **Validate** each bundle before offering it: valid JSON shaped `{ "mcpServers": { ... } }`. If a bundle contains a literal secret (an `env`/`args` value that isn't a `${VAR}`, an `op://`/`sops://`/`bw://` ref, or an `mcp-launch --secret/--arg` ref), warn — bundles must resolve secrets via `mcp-launch`, never inline them.
3. Read the current repo's `.mcp.json` if present (repo root / `$CLAUDE_PROJECT_DIR`). Note which servers already exist.
4. Use **AskUserQuestion** (multiSelect) so the user picks which tool(s) to add. For each option, describe in plain terms what it gives them (e.g. "a web browser Claude can drive"), and mark any already added.
5. Merge the chosen bundles' `mcpServers` into the repo's `.mcp.json` (drop `_comment`):
   - Create the file if missing, shaped `{ "mcpServers": { ... } }`.
   - Preserve existing servers; don't overwrite one without confirming.
6. If a chosen bundle uses `mcp-launch` for secrets, remind the user that `mcp-launch` must be on PATH for the spawned server — that's what the one-time `install.sh` in the marketplace repo sets up (symlinks `mcp-launch`/`mcp-secret` into `~/.local/bin`). Also remind them to put the referenced secret in their backend.
7. Tell the user `.mcp.json` changes load on the next session start; they'll be prompted to approve new servers.

Constraints:
- Only edit the **current repo's** `.mcp.json`. Never touch `~/.claude.json` or user/global config.
- If `$ARGUMENTS` names bundles directly (e.g. `frontend`), skip the question and add those.
- This installs **already-vetted** bundles. For a brand-new server use `/mcp-secure:mcp-add`. For team always-on servers use `/mcp-secure:mcp-global`.
