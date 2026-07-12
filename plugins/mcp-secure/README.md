# mcp-secure

> **This page is the technical reference.** Start at the
> **[top-level README](../../README.md)** and `/mcp-secure:setup` if you're new;
> come back here for the design details.

A Claude Code plugin that makes MCP servers **secret-safe by default**:
credentials are resolved at spawn from your vault, never stored in config, and
never reach the model's context. It also adds a vetting flow for new servers and
guard hooks against the common leak vectors.

## What it provides

| Component | Purpose |
|-----------|---------|
| `bin/mcp-secret` | Resolves a secret *reference* to plaintext from 1Password / SOPS / Bitwarden. |
| `bin/mcp-launch` | Generic launcher: injects resolved secrets into a server at spawn (env or CLI flag), then execs it. |
| `bin/mcp-doctor` | Health-checks the chain: backend auth + every config reference resolves. `--launch` also spawns each stdio server and reports (with its stderr) whether it starts and speaks MCP. |
| `bin/mcp-pin` | Pins each server's tool definitions and detects drift (rug-pull defense). |
| `bin/mcp-bundles` | Lists ready-made locations (shipped exemplars + private bundles) for `/mcp-secure:add`. |
| `commands/` | `setup`, `add`, `update`, `fix`, `remove`, `audit`, `always-on`, `check`, `verify` (see the top README's table). |
| `skills/` | `add-tool` / `update-tool` / `fix-tool` / `remove-tool` / `audit-tools`, which route plain-language requests to the commands. |
| `hooks/` | Config guard (blocks literal secrets, confirms global scope), call guard (asks on credential-shaped values in outbound tool calls + first use of an unpinned server), session nudge. |
| `bundles/` | Shipped exemplars: a few vetted, exact-pinned demonstrations of the pattern (not a catalog). Private bundles: `~/.config/mcp-secret/bundles/`. |
| `VETTING.md` / `BACKENDS.md` / `ORG.md` | Vetting checklist / backend setup / optional team config. |

## Install

```
/plugin marketplace add pietercastle-dev/mcp-locksmith
/plugin install mcp-secure@mcp-locksmith
```

Then run `install.sh` from the cloned repo once (puts the resolver on PATH,
records your default backend). This is needed only for secret-backed servers.

## How secrets work

Config holds a **reference**, resolved at launch:

```jsonc
// in a server's .mcp.json entry
{
  "command": "mcp-launch",
  "args": ["--secret", "GITHUB_TOKEN=op://Work/github/token",
           "--", "github-mcp-server", "--read-only"]
}
```

`mcp-launch` resolves each `--secret NAME=ref` (or `--arg FLAG=ref` for
flag-only servers; prefer `--secret`, since argv is visible in `ps` and env is
not) via `mcp-secret`, injects it, and execs the server.

**Reference forms**

```
cloudflare/token            # short ref -> machine default backend
op://Work/cloudflare/token  # 1Password (explicit)
sops://~/secrets.sops.yaml#/cloudflare/token
bw://cloudflare/token       # Bitwarden
```

The machine default (`~/.config/mcp-secret/config`: `MCP_SECRET_BACKEND`, plus
`MCP_OP_VAULT` / `MCP_SOPS_FILE`) lets short refs resolve per environment, so
one config is portable across work/home.

**HTTP servers:** prefer OAuth (no static secret). If a remote server needs a
header, use a `headersHelper` that prints it as JSON, e.g.
`printf '{"Authorization":"Bearer %s"}\n' "$(mcp-secret op://Work/x/token)"`.

## Adding servers, in priority order

1. **OAuth-capable?** Use it, with no static secret (`/mcp-secure:add` checks this first).
2. **Token-only?** `mcp-launch` + a backend ref.
3. **Guard hook** is the backstop. It denies literal secrets in any `.mcp.json`
   and asks before a global (`-s user`) add.

## Tool pinning (rug-pull defense)

A server can change its tool descriptions *after* you approve it, and those
descriptions are injected into the model's context. `mcp-pin` defends locally:

```sh
mcp-pin pin       # record the approved tool baseline (after vetting)
mcp-pin verify    # re-check; flags DRIFT if a server's tools changed
mcp-pin list / unpin <name> / prune
```

It discovers servers from `./.mcp.json` and `~/.claude.json` and reads each
server's `tools/list` over the MCP protocol (stdio *and* streamable HTTP; the
config's `headers`/`headersHelper` are honored, so a server that connects in a
session authenticates identically here), then hashes each tool's
name/description/schema. Pins live at `~/.config/mcp-secret/pins.json`, keyed by
server identity (name + command + args, or name + url), so a version bump reads
as "new, re-pin". **Known gap, labeled honestly:** a remote server that
authenticates via Claude Code's OAuth store can't be pinned (that token isn't
ours to read), so `mcp-pin` says so on a 401, and the nudge/tripwire stay quiet
about such servers instead of nagging you toward the impossible. Legacy
`type: "sse"` servers are skipped with a note. `verify` stamps `lastVerified`;
the session nudge warns when pinned tools haven't been drift-checked in
`MCP_PIN_MAX_AGE` days (default 14). This nudge shows up inside Claude's **first
reply** of the session (it's a `SessionStart` hook), not as a separate popup.

Version bumps go through `/mcp-secure:update`: it diffs the candidate version's
tools against the current ones **before** the config changes (`mcp-pin tools --
<command>…` is the plumbing), re-vets what changed, then re-pins.

## Optional: install-time firewall

MCP servers usually launch via `npx`/`uvx`, which is a supply-chain surface.
[Socket Firewall](https://github.com/SocketDev/sfw-free) (`sfw`, free, tokenless)
blocks known-malicious packages; run a new server's first fetch under it:
`sfw npx -y some-mcp@1.2.3`. Wrapping *all* your installs (shell aliases) is a
personal opt-in; note that aliases only fire in interactive shells, and `sfw`
doesn't support custom/private registries. The harness never edits your rc for
you.

## Security model

- **At rest:** config holds references and `mcp-launch` invocations, never secrets.
- **In context:** secrets resolve in a subprocess; values never return to the
  model. The guard denies literal secrets written into MCP config via
  `claude mcp add`/`add-json`/`import`, shell redirects/tee, or Write/Edit,
  including secrets tucked in `args` arrays.
- **At runtime:** a second hook watches outbound calls (`mcp__*` tools,
  WebFetch/WebSearch) and `ask`s (never denies) when a credential-shaped value
  is in the arguments (exfiltration, the tool-poisoning payoff), or on the first
  use per session of a server with no pin baseline (gated: only if you use
  pinning, or org `policy.requireVetting` is set). Pure local reads, no latency.
- **Guards are defense-in-depth, not a sandbox.** They fail *open* and match the
  common shapes, not every possible one. The real rule stands: never write
  a literal secret into config.
- **Scope:** project by default; global is opt-in and confirmed.
- **Residual risk:** a secret passed via `--arg` is visible in `ps` while the
  server runs. Prefer `--secret` (env).

Full threat model, non-goals, and plugin pinning: **[../../SECURITY.md](../../SECURITY.md)**.

## Backends

| Backend | CLI | Reference | Auth |
|---------|-----|-----------|------|
| 1Password | `op` | `op://vault/item/field` | `op signin` |
| SOPS+age | `sops` | `sops://file#/key/path` | age key configured |
| Bitwarden | `bw` (+`jq`) | `bw://item/field` | `bw unlock` + `BW_SESSION` |

Secure step-by-step setup for each: **[`BACKENDS.md`](BACKENDS.md)**.
`/mcp-secure:check` reports exactly what's missing and how to fix it.
