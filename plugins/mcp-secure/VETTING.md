# Vetting a new MCP server

Run this before adding any MCP server you haven't used before. `/mcp-secure:add`
walks you through it; this file is the standard it enforces — nothing new gets
into config without a deliberate, security-first look. (Why: the two failure
modes are a credential baked into config where it persists and can reach the
model's context, and an unvetted/unpinned server pulling untrusted code into
your agent's tool surface.)

## Checklist

0. **Auth model first.** Prefer OAuth / remote auth — Claude Code runs the flow
   and stores the token itself, so there's **no static secret at all**. Only fall
   back to a token (step 5) when OAuth isn't an option.
   *Caveat:* Claude Code auto-registers via Dynamic Client Registration
   (RFC 7591), but many official servers (Slack, GitHub, Entra-backed) don't
   support it. Usual fix: supply the provider's pre-registered `oauth.clientId`
   + `callbackPort` (the client id is public; PKCE means no client secret). Only
   fall back to a token via `mcp-launch` if there's no OAuth client at all.
   (Known SDK bug: Claude Code may attempt DCR before honoring a provided
   clientId.)

1. **Provenance.** Who publishes it — official vendor or third party? Find the
   source repo; check activity and last release. Flag typosquats, no public
   source, abandonment.

2. **Pin the version.** Never `@latest`, never an unpinned `npx -y <pkg>` (it
   refetches on every launch). Pin exact: `pkg@1.2.3`.

3. **Least privilege.** Enumerate the exposed tools. Prefer read-only; enable
   destructive tools only when actually needed. Scope any API token to the
   minimum.

4. **Transport.** Prefer local `stdio`. For `http`, require TLS and verify the
   exact domain; plain `http://` to anything non-local is a red flag.

5. **Secrets — never inline.** If it needs a token: store it in your backend and
   launch via `mcp-launch` with a *reference*:
   ```json
   { "command": "mcp-launch",
     "args": ["--secret","TOKEN=op://Vault/item/field","--","<server>","<args>"] }
   ```
   Use `--arg FLAG=ref` only when the server takes the secret solely as a CLI
   flag (argv is visible in `ps`; env is not). The guard hook blocks literal
   secrets anyway — the point is to never write one.

6. **Network egress.** Know where it phones home. A "local" server with
   unexpected outbound connections deserves scrutiny.

7. **Tool integrity (poisoning & rug-pulls).** Tool *descriptions* are injected
   into the model's context, so a malicious description can carry hidden
   instructions without the tool ever being called — and a server can change its
   descriptions *after* approval (e.g. the Sept 2025 Postmark incident). So:
   read the actual tool descriptions, not just the README — hidden instructions,
   "ignore previous", or requests to read files/env are disqualifying; pin the
   version (step 2); re-vet on every version bump (`/mcp-secure:update` walks
   this — it diffs the new version's tools before adopting). See the OWASP MCP
   Top 10.

8. **Record it.** Add the vetted config to a bundle (references only) so the
   team gets it without re-deriving. Note the version and vet date.

## Defense in depth (beyond add-time vetting)

- **Install-time supply chain.** `npx`/`uvx`/`pip` fetches are the attack
  surface. [Socket Firewall](https://github.com/SocketDev/sfw-free) (`sfw`,
  free, tokenless) blocks confirmed-malicious packages — run the first fetch
  under it: `sfw npx -y <pkg>@<ver>`. (No custom/private registry support.)
- **Optional deeper scanners** (point-in-time poisoning scans):
  [Cisco `mcp-scanner`](https://github.com/cisco-ai-defense/mcp-scanner) —
  local-first, CI-friendly, best fit for this harness's no-egress principle;
  [Snyk `agent-scan`](https://github.com/snyk/agent-scan) — broadest coverage
  but needs a `SNYK_TOKEN` and sends tool descriptions to Snyk's API.

## Removing a server (the other end of the lifecycle)

A token for a tool nobody uses is a forgotten credential waiting to leak.
`/mcp-secure:remove` walks it: **unregister** from its scope, **revoke/rotate
the token** at the provider and delete the vault item (unless another tool still
references it — this is the step people forget), and **drop its pin**
(`mcp-pin unpin` / `prune`).
