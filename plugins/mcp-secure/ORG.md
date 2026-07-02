# Org configuration (optional)

For teams: point everyone at your internal MCP conventions. mcp-secure reads an
optional **`org.json`** and *surfaces* it in the flows — it never enforces
policy or routes traffic. Distribution is the org's job (onboarding script,
dotfiles, MDM, or an internal plugin).

## Location

`~/.config/mcp-secret/org.json` (default), or the path in `$MCP_ORG_CONFIG`.

## Schema

```json
{
  "org": "Acme",
  "docsUrl": "https://acme.example.com/wiki/mcp-patterns",
  "recommended": ["frontend", "acme-internal"],
  "gateway": { "url": "https://mcp-gw.acme.internal", "authRef": "op://Acme/mcp-gateway/token" },
  "policy": { "requireVetting": true, "preferGateway": true }
}
```

| Field | Status | Meaning |
|-------|--------|---------|
| `org` | ✅ surfaced | Display name, shown in `/mcp-secure:check`. |
| `docsUrl` | ✅ surfaced | Your internal page — shown in `check`, the nudge, `add`, `setup`. |
| `recommended` | ✅ surfaced | Bundle names offered first in `add`. Pair with private bundles (`~/.config/mcp-secret/bundles/`) so the sets are actually present. |
| `gateway.*` | ℹ️ info only | Shown as information; routing not built yet (see [ROADMAP.md](../../ROADMAP.md)). |
| `policy.*` | 🔒 reserved | Accepted, not enforced. Org policy will be advisory, like the guard. |
