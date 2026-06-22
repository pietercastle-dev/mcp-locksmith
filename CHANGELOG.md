# Changelog

All notable changes to mcp-locksmith are documented here. This project adheres to
[Semantic Versioning](https://semver.org/). Plugin versions are tracked in each
plugin's `.claude-plugin/plugin.json`.

## [Unreleased]

### Security
- **No more sourcing the secret-backend config.** `mcp-secret` and `install.sh` now
  parse `~/.config/mcp-secret/config` as `KEY=VALUE` instead of `source`-ing it,
  removing a code-execution path if that file were ever attacker-writable. The
  config file is created `chmod 600` and its dir `700`.
- **age-key hardening.** `install.sh` creates the key dir `700` and tightens perms
  (`600`) on a pre-existing key, not just freshly generated ones.
- **Guard covers more credential shapes** — Google API keys (`AIza…`), PEM private
  keys, and connection strings / URLs with inline credentials (`scheme://user:pass@`).
  Deliberately not matching bare hex (git SHAs / content hashes are not secrets).
- **Guard scans structurally.** Write/Edit payloads that are valid JSON are walked as
  JSON (catching secrets in `args` arrays and behind escaped quotes) instead of
  regex-matched. `claude mcp import` is now gated alongside `add`.

### Added
- `SECURITY.md` — threat model, non-goals, and plugin pinning/update guidance.

## [0.1.0] — 2026-06-23

Initial release. A Claude Code plugin marketplace for adding MCP servers (tools)
safely, with secrets kept out of config and out of the model's context.

### Added
- **`mcp-secure` plugin** — the toolkit:
  - Commands: `/mcp-secure:setup` (guided first-time setup), `/mcp-secure:add`
    (add a ready-made bundle *or* vet & add a brand-new tool — auto-detected),
    `/mcp-secure:check` (one health check: secret chain resolves **and** no tool
    drifted), `/mcp-secure:verify` (focused drift-only check), `/mcp-secure:always-on`
    (set up an always-on / global tool).
  - `mcp-secret` / `mcp-launch` — resolve a secret *reference* from your vault and
    inject it at spawn, so config holds references, never literal secrets.
  - `mcp-doctor` — health-checks the chain and turns each gap into an actionable,
    secure fix (install command, auth command, BACKENDS.md pointer).
  - `mcp-pin` — pins each server's tool definitions and detects drift (rug-pull
    defense).
  - **Guard hook** — blocks literal secrets from reaching MCP config via
    `claude mcp add` (`-e` / `add-json`), shell redirects/tee into
    `*.mcp.json` / `~/.claude.json`, or Write/Edit (including secrets in `args`
    arrays); confirms global-scope changes. Defense-in-depth, fail-open.
  - Vetted, ready-to-add bundles (e.g. `frontend`).
  - `VETTING.md` — the add-time security checklist (provenance, version pinning,
    least privilege, tool-poisoning/rug-pull, supply chain).
  - `BACKENDS.md` — secure setup for 1Password, Bitwarden, and SOPS+age, including
    age-key generation and handling.
- **`mcp-globals` plugin** — template for a profile of always-on servers.
- `install.sh` — puts the helpers on PATH, records your default secret backend, and
  bootstraps an age key on the SOPS path.
- Secret backends: 1Password (`op`), Bitwarden (`bw`), SOPS+age (`sops`).

[0.1.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.1.0
