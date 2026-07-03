<!-- Paste this block into your ~/.claude/CLAUDE.md to document the convention.
     Requires the mcp-secure plugin (commands are namespaced mcp-secure:*). -->

## MCP server organization

MCP servers come in two tiers. **Project is the default; global is curated and
deliberate.** Managed by the `mcp-secure` plugin.

- **Project tier (most servers):** each repo declares what it needs in a committed
  `.mcp.json`. Vetted sets ship as bundles with the plugin. `/mcp-secure:add`
  adds a tool to the current repo: a ready-made bundle, or a brand-new server it
  vets first (runs the plugin's VETTING.md). Your own/team private bundles live in
  `~/.config/mcp-secret/bundles/` and are offered alongside the shipped ones.
- **Global tier (the few always-on servers, e.g. Slack at work):** team-shared
  globals live in a dedicated globals plugin (loaded in every repo when enabled);
  personal one-offs go in user scope. Manage with `/mcp-secure:always-on`. Keep it
  small. If a single project needs a server, it's project tier.

**Secrets never go in config.** Prefer OAuth where the server supports it (no static
secret). Otherwise keep the credential in your backend (1Password / SOPS /
Bitwarden) and launch via `mcp-launch`, passing a *reference* (short ref or
`op://` / `sops://` / `bw://`), resolved at spawn, never stored. A PreToolUse guard
blocks literal secrets in any `.mcp.json`; global-scope (`-s user`) adds are allowed
but confirmed.

**Adding a server:** default to project scope. Use `-s user` only for the curated
always-on set (the guard will ask you to confirm). Route any secret through
`mcp-launch`, never `-e TOKEN=<literal>`.

**Plain-language requests route through the safe flow.** When the user asks (in their
own words) to add/connect/install, remove/disconnect, or review an external tool or
MCP server (e.g. "add a Slack tool", "remove the GitHub server", "are my tool keys
safe?"), handle it via the mcp-secure flow, not ad hoc. The mcp-secure plugin ships
skills (`add-tool`, `remove-tool`, `audit-tools`) that trigger on these intents; let
them. If they don't fire: vet a new server (provenance, pin the version, least
privilege, see VETTING.md), keep any secret in the backend and launch via `mcp-launch`
with a reference, offer to pin the baseline, and on removal prompt to revoke the token.
The user should not need to type a slash command.
