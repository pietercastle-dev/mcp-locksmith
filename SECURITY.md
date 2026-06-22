# Security policy

mcp-locksmith is a security tool, so it should be explicit about what it protects
against, what it does **not**, and how it expects to be trusted and updated.

## Threat model — what it defends against

1. **Secrets in config / context.** Credentials baked into `~/.claude.json` or a
   committed `.mcp.json` persist to disk and can reach the model's context. The
   harness keeps only *references* in config and resolves them at spawn; a PreToolUse
   guard blocks the common ways a literal secret would get written there.
2. **Unvetted / unpinned servers.** New MCP servers are code you run. `VETTING.md`
   enforces provenance, version pinning, least privilege, and a tool-poisoning check.
3. **Rug-pulls.** A server can change its tool descriptions after you approve it.
   `mcp-pin` records a baseline and `/mcp-secure:check` flags drift.
4. **Install-time supply chain.** Optional Socket Firewall (`sfw`) blocks
   known-malicious packages during a server's first fetch.

## Trust model & non-goals — what it does NOT do

**Installing this plugin is a trust decision.** Its hooks run on every `PreToolUse`,
and `install.sh` puts `mcp-secret` / `mcp-launch` on your `PATH`, where they execute
(and resolve your vault secrets) whenever an MCP server spawns. Treat the plugin's
code with the same scrutiny you'd give any tool that can read your secrets.

It is **defense-in-depth, not a sandbox.** Specifically, it does **not**:

- **Sandbox an approved server.** Once you approve a server, it runs with whatever
  access you grant it; a secret you route into a malicious server is exposed to it.
  Scope tokens to least privilege.
- **Catch every secret.** The guard is a **fail-open** PreToolUse hook (if it errors,
  or `python3` is missing, the action is allowed). It matches common credential
  shapes and write paths — not every conceivable one. The real rule stands: never
  write a literal secret into config. It also cannot un-expose a secret you paste
  directly into the chat — that's already in context before any tool runs.
- **Protect a compromised machine.** It assumes your account, your vault login, and
  your age private key are not already in an attacker's hands.
- **Replace your vault's security.** 1Password / Bitwarden / SOPS+age are the root of
  trust; protect those credentials accordingly.

## Pinning & updating the plugin

The marketplace tracks the repo, and `install.sh` **symlinks** the helpers into
`~/.local/bin` — so a `git pull` silently swaps in new code that runs with
secret-resolution access. That's convenient, but it means updates are an implicit
re-trust. To stay in control:

- **Pin to a tagged release.** Clone the repo, `git checkout v0.1.0` (see
  [CHANGELOG.md](CHANGELOG.md) for releases), then add the marketplace from that local
  path and run `install.sh` from it. The symlinks then track the checked-out tag, so
  the executed code is pinned too.
- **Review before updating.** Diff the changes (`git log`/`git diff` against your
  pinned tag) before `git pull` / checking out a newer tag — especially anything
  under `hooks/` and `bin/`.
- Verify you cloned the **real** repo: `github.com/pietercastle-dev/mcp-locksmith`.

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue:

- Use GitHub's **private vulnerability reporting** on this repository
  (Security → "Report a vulnerability"), or
- open a minimal public issue asking for a private channel — without details.

Please include a description, impact, and a reproduction. We aim to acknowledge
within a few days and will credit reporters who want it.
