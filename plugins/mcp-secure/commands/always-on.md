---
description: Set up always-on (global) MCP servers that load in every repo
---

**How to talk to the user:** plain, friendly language (same tone as
`/mcp-secure:setup`). Frame this as "always-on tools", ones available in every
project automatically (like Slack), rather than per-project. The mechanics below
are for you; explain choices to the user simply.

Help the user set up **always-on tools**, ones that load in *every* project (e.g.
Slack at work). Reserve it for things genuinely useful everywhere; most tools belong
to one project via `/mcp-secure:add`.

There are two ways to run a global server. Recommend based on the situation:

**A) A profile of globals (e.g. team set at work, personal set at home) belongs in a
globals plugin.** If a set of servers should always be on in some environment, they belong
in a dedicated plugin; its own enable/disable is what makes it on-here-not-there. Scaffold
one from the bundled template at `${CLAUDE_PLUGIN_ROOT}/templates/globals-profile/`:
1. Copy that template into the user's marketplace repo, rename it per profile
   (e.g. `acme-globals` / `home-globals`), set `name` in its
   `.claude-plugin/plugin.json`, and add it to the marketplace `plugins` list.
2. Vet each server against `VETTING.md` (provenance, pinned version, least privilege). A
   global server runs everywhere. Vet it at least as hard as a project one.
3. Add servers to that plugin's `.mcp.json` using `${CLAUDE_PLUGIN_ROOT}/bin/mcp-launch`
   with a fully-qualified secret ref (e.g. `op://Work/<item>/<field>`). Never inline a token.
4. Give the profile a `bin/mcp-launch` by symlinking `mcp-secure`'s copy (the sanctioned
   cross-plugin share); the template README shows the command.
5. Publish the plugin; teammates install it on the machines where it applies.

**B) Personal globals (home, just a few) belong in user scope.** For one or two personal
always-on servers, skip the plugin overhead:
1. Vet it the same way.
2. `claude mcp add -s user <name> -- mcp-launch --secret NAME=<ref> -- <server> <args>`
   (the guard will ask you to confirm the global scope). For secrets, route through
   `mcp-launch` exactly as above. Never `-e TOKEN=<literal>`.

Always: keep the global set small and deliberate; project scope is the default.
Remind the user that user-scope / plugin changes load on the next session start.
