# mcp-globals (template)

The **global tier**: a profile of always-on MCP servers, loaded in every repo when
this plugin is enabled. Use it for servers you genuinely want everywhere — Slack at
work, or a personal set at home. This is a template; copy it per profile, fill in
the real servers, and install it where it applies.

## Why a separate plugin

Globals are environment-specific. The machinery (`mcp-secure`) is installed
everywhere, but the always-on *servers* differ by context: a team set at work, a
small personal set at home, maybe none on a CI box. Keeping them in their own
plugin(s) means you install each profile only where you want it:

- **Work machine:** `mcp-secure` + `acme-globals` (your filled-in work copy).
- **Home machine:** `mcp-secure` + `home-globals` (your personal copy), or just add
  one-offs at user scope with `claude mcp add -s user`.

`defaultEnabled: false` ships it installed-but-off, so it loads only where you turn
it on.

## How to make a profile

1. Copy this directory, rename it (e.g. `acme-globals`, `home-globals`) and bump
   `name` in `.claude-plugin/plugin.json`. Add it to the marketplace `plugins` list.
2. Put your real servers in `.mcp.json`. For secrets, use `mcp-launch` with a
   **fully-qualified** ref (e.g. `op://Work/<item>/<field>`) so it's unambiguous
   across machines. Never put a literal token here.
3. The `bin/` launcher is symlinked from `mcp-secure` (the sanctioned way to share
   files across plugins). Keep both installed.
4. Pin server versions. Run `claude plugin validate` before publishing.

## Install

```
/plugin marketplace add <your-marketplace-repo>
/plugin install mcp-secure@<marketplace>
/plugin install <your-globals-profile>@<marketplace>
```
