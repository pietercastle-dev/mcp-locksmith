# Vetting a new MCP server

Run this before adding any MCP server you haven't used before. `/mcp-add` walks
you through it; this file is the standard it enforces. The goal: nothing new gets
into a config without a deliberate, security-first look.

## Checklist

0. **Auth model first.** Does the server support OAuth / remote auth? If so, prefer
   it — Claude Code runs the flow and stores the token in its own credential store,
   so there's **no static secret at all**. Only fall back to a token (step 5) when
   OAuth isn't an option. The most secure secret is the one you never have to store.

1. **Provenance.** Who publishes it? Official vendor or a third party? Find the
   source repo. Check stars/activity and the last release. Be alert to
   typosquats (`@playwright/mcp`), no public source, or abandoned projects.

2. **Pin the version.** Never `@latest`, never an unpinned `npx -y <pkg>` (it
   refetches the newest build on every launch — a supply-chain and
   reproducibility hole). Pin an exact version, e.g. `pkg@1.2.3`.

3. **Least privilege.** Enumerate the tools the server exposes. Prefer read-only.
   Turn on destructive tools (delete/write/exec) only when you actually need them.
   Scope any API token to the minimum — a GitHub server doesn't need org-admin.

4. **Transport.** Prefer local `stdio`. For `http`, require TLS and verify the
   exact domain. Treat plain `http://` to anything non-local as a red flag.

5. **Secrets — never inline.** If it needs a token (and OAuth wasn't available):
   - Store the secret in your backend (1Password / SOPS / Bitwarden).
   - Launch via `mcp-launch`, passing a *reference* — never the value:
     ```json
     { "command": "mcp-launch",
       "args": ["--secret","TOKEN=op://Vault/item/field","--","<server>","<args>"] }
     ```
     Use `--arg FLAG=ref` for servers that only take the secret as a CLI flag.
   - `mcp-launch` resolves the ref at spawn; the config holds only references.
   - The guard hook blocks a literal secret in any `.mcp.json` anyway, but the
     point is to not write one in the first place.

6. **Network egress.** Know where it phones home. A "local" server that opens
   outbound connections to an unexpected host deserves scrutiny.

7. **Tool integrity (poisoning & rug-pulls).** MCP tool *descriptions* are injected
   into the model's context, so a malicious description can carry hidden
   instructions the model follows without the tool ever being called ("tool
   poisoning"). And a server can change its tool descriptions *after* you approve
   it ("rug pull" — e.g. the Sept 2025 Postmark incident, where an update silently
   BCC'd every email). So:
   - Read the actual tool descriptions, not just the README. Treat hidden/inline
     instructions, "ignore previous", or requests to read files/env as disqualifying.
   - **Pin the version** (step 2) — it's also your rug-pull defense: a pinned server
     can't silently change underneath you, and an update forces a re-vet.
   - Prefer servers that publish signed releases / stable tool schemas.
   - Re-vet on every version bump. See the OWASP MCP Top 10 and MCP Security Cheat
     Sheet for the broader threat list.

8. **Record it.** Once vetted, add it to a bundle (using references) so the team
   gets the vetted config, not a from-scratch re-derivation. Note the version and
   the date you vetted it in the PR/commit.

## Defense in depth (beyond add-time vetting)

Vetting catches what you can see when you add a server. Two more layers catch the
rest:

- **Install-time supply chain.** MCP servers usually launch via `npx -y pkg@ver` or
  `uvx pkg`, which pull packages from npm/PyPI — the supply-chain attack surface
  (cf. the 2025 npm compromises). [Socket Firewall](https://github.com/SocketDev/sfw-free)
  (`sfw`) is free, needs no token, and blocks confirmed-malicious packages at
  install: `npm i -g sfw`, then run the first fetch under it, e.g.
  `sfw npx -y <pkg>@<ver>`. Since you pin versions, that first fetch is the exposure
  window. Caveat: `sfw` doesn't support custom/private registries.
- **Optional deeper scanners** (on demand, not required — point-in-time poisoning
  scans, distinct from the ongoing rug-pull defense):
  - [Cisco `mcp-scanner`](https://github.com/cisco-ai-defense/mcp-scanner) —
    **local-first**: supports offline/static scanning of exported JSON (CI-friendly,
    air-gapped). Best fit for this harness's no-egress principle.
  - [Snyk `agent-scan`](https://github.com/snyk/agent-scan) — broadest coverage
    (15+ risks across agents/MCP/skills) but needs a `SNYK_TOKEN` and validates via
    Snyk's API, so tool descriptions/config leave the machine. Use only if you
    accept that.
  - Beware the name "mcp-guard" — there are two unrelated projects (a community
    static scanner and a runtime injection guard); prefer the two above.

## Why this exists

The two failure modes this prevents: (a) a credential getting baked into
`~/.claude.json` or a committed `.mcp.json` where it persists to disk and can reach
the model's context, and (b) an unvetted or unpinned server pulling untrusted code
into your agent's tool surface. Both are cheap to avoid up front and expensive to
clean up after.
