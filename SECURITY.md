# Security policy

mcp-locksmith is a security tool, so it is explicit about what it protects
against, what it does **not**, and how it expects to be trusted and updated.

## Threat model — what it defends against

1. **Secrets in config / context.** Config holds only *references*, resolved at
   spawn; a PreToolUse guard blocks the common ways a literal secret would get
   written into `~/.claude.json` or a committed `.mcp.json`.
2. **Unvetted / unpinned servers.** `VETTING.md` enforces provenance, version
   pinning, least privilege, and a tool-poisoning check.
3. **Rug-pulls.** `mcp-pin` records a tool baseline; `/mcp-secure:check` flags
   drift after approval.
4. **Install-time supply chain.** Optional Socket Firewall (`sfw`) blocks
   known-malicious packages during a server's first fetch.

## Trust model & non-goals — what it does NOT do

**Installing this plugin is a trust decision.** Its hooks run on every
`PreToolUse`, and `install.sh` puts `mcp-secret` / `mcp-launch` on your `PATH`,
where they resolve your vault secrets whenever an MCP server spawns.

It is **defense-in-depth, not a sandbox.** It does **not**:

- **Sandbox an approved server.** An approved server runs with whatever access
  you grant it; scope tokens to least privilege.
- **Catch every secret.** The guard is **fail-open** (an error, or missing
  `python3`, allows the action) and matches common credential shapes, not every
  conceivable one. It also can't un-expose a secret pasted directly into chat.
- **Protect a compromised machine.** It assumes your account, vault login, and
  age private key aren't already in an attacker's hands.
- **Replace your vault's security.** 1Password / Bitwarden / SOPS+age are the
  root of trust.

## Pinning & updating the plugin

`install.sh` **symlinks** the helpers, so a `git pull` silently swaps in new
code that runs with secret-resolution access — updates are an implicit re-trust.
Stay in control: **pin to a tagged release** (clone, `git checkout v0.x.y`, add
the marketplace from that path, run `install.sh` from it — the symlinks then
track the tag), **review diffs before updating** (especially `hooks/` and
`bin/`), and verify you cloned the real repo:
`github.com/pietercastle-dev/mcp-locksmith`.

## Reporting a vulnerability

Report **privately**: GitHub's private vulnerability reporting on this repo
(Security → "Report a vulnerability"), or a minimal public issue asking for a
private channel — without details. Include description, impact, and a
reproduction. We aim to acknowledge within a few days and credit reporters who
want it.
