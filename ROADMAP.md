# Roadmap

Shipped work is in [CHANGELOG.md](CHANGELOG.md). The detailed
milestone-by-milestone plan to feature-complete (v0.4 to v1.0) is
**[PLAN.md](PLAN.md)**: vision, definition of done, and per-release scope.

Deliberately deferred items, kept here so they aren't re-litigated:

## Plugin-scope server discovery in `mcp-pin`: deferred (post-1.0)

`mcp-pin` (and the hooks that mirror its discovery) reads `./.mcp.json` and
`~/.claude.json` only. Servers a *plugin* provides are invisible to it, so
they can't be pinned or drift-checked. Deferred in the 2026-07-02 descope:
plugin-provided servers ship inside code the user already chose to trust and
pin (the plugin itself), so the marginal win is small. Revisit if dogfooding
or users actually hit it.

## Bundle catalog: cut (2026-07-02 descope, see PLAN.md)

A curated many-server catalog competes where the market is already crowded
(Docker MCP Catalog, the official registry, Smithery) and creates a vetting
staleness treadmill with implied liability. The plugin ships a few *exemplar*
bundles that demonstrate the mcp-launch reference pattern; discovery of
everything else goes through the official registry in the `add` flow.

## Argument-level tool scoping: deferred (post-1.0)

Pins and native permissions gate *which tool* may be called, not *what it
targets*: there is no way to allow a send-message tool only into one channel,
or page edits only under one document, because permission globs stop at the
tool name. `mcp-pin` already records each server's tool surface at approval
time, so optional per-target allowlists derived from pins (enforced by the
existing call guard, ask-only as ever) are a natural extension. Deferred
because target-ID fields are vendor-specific: shipping this well means a
per-server mapping treadmill, the same shape as the cut bundle catalog.
Revisit post-1.0 if real usage demands it.

## Org gateway routing & policy enforcement: deferred

The org-config **pointer layer** shipped in v0.3.0 (`org.json`: docs link +
recommended bundles, surfaced in the flows, see
[`plugins/mcp-secure/ORG.md`](plugins/mcp-secure/ORG.md)). The rest waits until
there's a **real gateway deployment to design against**, not a guess:

- **Gateway routing, point-at only.** Default new servers through the org
  gateway; warn on direct adds. The plugin must never implement gateway
  protocol, auth brokering, or audit. That's infra the org runs.
- **Policy enforcement.** `policy.*` flags are accepted but not acted on. When
  built, they stay **advisory / best-effort**, like the guard.

**Non-goals:** don't build a gateway, a policy *enforcement* engine, or
org-config *distribution*. The plugin only reads a file an org provides.
