# Roadmap

Shipped work is in [CHANGELOG.md](CHANGELOG.md). The detailed
milestone-by-milestone plan to feature-complete (v0.4 → v1.0) is
**[PLAN.md](PLAN.md)** — vision, definition of done, and per-release scope.

One deliberately deferred item, kept here so it isn't re-litigated:

## Org gateway routing & policy enforcement — deferred

The org-config **pointer layer** shipped in v0.3.0 (`org.json`: docs link +
recommended bundles, surfaced in the flows — see
[`plugins/mcp-secure/ORG.md`](plugins/mcp-secure/ORG.md)). The rest waits until
there's a **real gateway deployment to design against**, not a guess:

- **Gateway routing — point-at only.** Default new servers through the org
  gateway; warn on direct adds. The plugin must never implement gateway
  protocol, auth brokering, or audit — that's infra the org runs.
- **Policy enforcement.** `policy.*` flags are accepted but not acted on. When
  built, they stay **advisory / best-effort**, like the guard.

**Non-goals:** don't build a gateway, a policy *enforcement* engine, or
org-config *distribution* — the plugin only reads a file an org provides.
