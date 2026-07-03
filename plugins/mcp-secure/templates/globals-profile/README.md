# Always-on profile (scaffold template)

This is the **scaffold** the `/mcp-secure:always-on` flow copies to create a
profile of always-on MCP servers: the servers you genuinely want in *every* repo
(Slack at work, or a personal set at home). It ships inside `mcp-secure` so the
flow can stamp out a profile on your machine without you cloning anything.

You don't edit this copy. The flow copies it out, renames it, and helps you fill
it in. If you're doing it by hand, the steps are below.

## Why a profile is its own plugin

A plugin's enable/disable is the right lever for "on here, not there." The
machinery (`mcp-secure`) is installed everywhere, but the always-on *servers*
differ by context: a team set at work, a small personal set at home, none on a
CI box. A profile per context means you install each only where it applies:

- **Work machine:** `mcp-secure` + `acme-globals` (your filled-in work copy).
- **Home machine:** `mcp-secure` + `home-globals`, or just add one-offs at user
  scope with `claude mcp add -s user`.

`defaultEnabled: false` ships a profile installed-but-off, so it loads only where
you turn it on.

## Make a profile by hand

1. Copy this directory to your marketplace repo, rename it (e.g. `acme-globals`,
   `home-globals`) and set `name` in `.claude-plugin/plugin.json`. Add it to the
   marketplace `plugins` list.
2. Put your real servers in `.mcp.json`. For secrets, use `mcp-launch` with a
   **fully-qualified** ref (e.g. `op://Work/<item>/<field>`) so it's unambiguous
   across machines. Never put a literal token here.
3. Give the profile a `bin/mcp-launch` (and `bin/mcp-secret`) by symlinking
   `mcp-secure`'s copies. That's the sanctioned way to share the launcher across
   plugins; keep both installed. From the profile dir:
   `ln -s ../../mcp-secure/bin/mcp-launch bin/mcp-launch`
   (adjust the relative path to wherever `mcp-secure` sits in your repo).
4. Pin server versions. Run `claude plugin validate` before publishing.
