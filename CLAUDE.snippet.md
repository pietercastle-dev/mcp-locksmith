<!-- Paste this block into your ~/.claude/CLAUDE.md to document the convention.
     Requires the mcp-secure plugin (commands are namespaced mcp-secure:*). -->

## MCP server organization

MCP servers come in two tiers. **Project is the default; global is curated and
deliberate.** Managed by the `mcp-secure` plugin.

- **Project tier (most servers):** each repo declares what it needs in a committed
  `.mcp.json`. Vetted sets ship as bundles with the plugin — `/mcp-secure:mcp-setup`
  adds them to the current repo; `/mcp-secure:mcp-add` vets and adds a brand-new
  server (runs the plugin's VETTING.md).
- **Global tier (the few always-on servers, e.g. Slack at work):** team-shared
  globals live in a dedicated globals plugin (loaded in every repo when enabled);
  personal one-offs go in user scope. Manage with `/mcp-secure:mcp-global`. Keep it
  small — if a single project needs a server, it's project tier.

**Secrets never go in config.** Prefer OAuth where the server supports it (no static
secret). Otherwise keep the credential in your backend (1Password / SOPS /
Bitwarden) and launch via `mcp-launch`, passing a *reference* (short ref or
`op://` / `sops://` / `bw://`) — resolved at spawn, never stored. A PreToolUse guard
blocks literal secrets in any `.mcp.json`; global-scope (`-s user`) adds are allowed
but confirmed.

**Adding a server:** default to project scope. Use `-s user` only for the curated
always-on set (the guard will ask you to confirm). Route any secret through
`mcp-launch` — never `-e TOKEN=<literal>`.
