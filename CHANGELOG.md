# Changelog

All notable changes to mcp-locksmith are documented here. This project adheres to
[Semantic Versioning](https://semver.org/). Plugin versions are tracked in each
plugin's `.claude-plugin/plugin.json`.

## [Unreleased]

### Added
- **Org config — pointer layer.** An optional `org.json`
  (`~/.config/mcp-secret/org.json` or `$MCP_ORG_CONFIG`) lets a team point everyone at
  internal MCP conventions: org name + an internal docs link (`docsUrl`) + `recommended`
  bundles, surfaced in `/mcp-secure:add`, `:setup`, `:check`, and the nudge. The plugin
  only *consumes* and *surfaces* it — distribution is the org's job. `gateway` fields are
  accepted and shown as info; routing/policy enforcement is **not** built yet (needs a
  real gateway to design against). See [`ORG.md`](plugins/mcp-secure/ORG.md) and
  [ROADMAP.md](ROADMAP.md).

## [0.2.0] — 2026-06-24

Validated end-to-end by a live dogfood — natural-language tool requests, SOPS secret
resolution, the guard, and a real OAuth add (Slack) all confirmed working — which also
turned up several fixes below.

### Added
- **Private (user/team) bundles.** Keep your own vetted server sets in
  `~/.config/mcp-secret/bundles/` (override `$MCP_USER_BUNDLES`) without committing them
  to the public plugin. `mcp-bundles --all` lists shipped + private; `/mcp-secure:add`
  and the nudge read both. (First step toward the org-config story.)

### Fixed
- **SOPS backend on macOS.** `sops`' default age-key location is platform-specific
  (`~/Library/Application Support/…` on macOS), so it never found the key `install.sh`
  writes to `~/.config/sops/age/keys.txt` — every SOPS secret failed to resolve while
  `mcp-doctor` misleadingly reported the key "present". `mcp-secret` now exports
  `SOPS_AGE_KEY_FILE` pointing at the managed key when the user hasn't set one.
- **install.sh validates the backend answer.** A pasted/fat-fingered response to the
  "default backend" prompt used to be written into the config verbatim (breaking every
  secret resolution). It's now validated against `op`/`sops`/`bw` and falls back to the
  detected backend; a re-run also flags an already-bogus config with recovery steps.
- **OAuth guidance corrected.** The add/vetting flow no longer implies OAuth "just
  works." Many official remote servers (Slack, GitHub, Entra-backed) don't support
  Dynamic Client Registration; the flow now points at supplying the provider's *public*
  `oauth.clientId` + `callbackPort` (PKCE means no client secret), with a token fallback
  only if there's no OAuth client. Verified live — Slack connected via the clientId.
- **Stray root `.mcp.json` gitignored.** A consumed `.mcp.json` written into the plugin
  repo (e.g. a setup flow run from the wrong dir) is no longer commit-able — it would
  leak the runner's server topology. Anchored so the `mcp-globals` template stays tracked.

## [0.1.1] — 2026-06-23

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
- **Path-traversal reject.** `sops://` references containing `..` are refused, so an
  untrusted config can't traverse to read other files on disk.

- **CI supply chain.** GitHub Actions are pinned to commit SHAs (not mutable `@v4`
  tags), and the workflow token is scoped to `contents: read` (least privilege).
  Dependabot keeps the pinned Actions patched (scoped to `github-actions` only, so
  vetted MCP server versions in bundles stay manually re-vetted).

### Added
- **No-typing UX via skills.** New `add-tool` / `remove-tool` / `audit-tools` skills
  auto-trigger the corresponding flow from plain-language requests ("add a Slack tool",
  "remove the GitHub server", "are my tool keys safe?") — the user no longer has to type
  a slash command. Skills route to the canonical command flow (single source of truth).
  A CLAUDE.md routing directive reinforces the same default behavior.
- **Proactive adoption nudge.** The SessionStart hook now also fires (once per project)
  when existing servers aren't adopted — a literal secret in config, or unpinned — and
  offers `/mcp-secure:audit`. Fast (local reads only) and marker-gated so it doesn't nag.
- **`/mcp-secure:audit`** — review **already-installed** servers (installing the plugin
  doesn't touch them) and adopt them into the harness: migrate inline secrets to
  references, pin versions/baselines, flag `http://`. Scoped as config hygiene, not a
  scanner — deep provenance/poisoning analysis is handed off to the tools in
  `VETTING.md`. `mcp-doctor` now also flags pre-existing literal secrets in config.
- **`/mcp-secure:remove`** — a guided removal flow that closes the tool lifecycle:
  unregister the server from its scope, `mcp-pin unpin` its baseline, and prompt to
  **revoke/rotate its secret** so a removed tool never leaves a live orphaned key.
- **`mcp-pin unpin <name…>` / `mcp-pin prune`** — drop the pin for a removed server
  (prune is dry-run unless `--yes`, since pin discovery is per-directory).
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

[0.2.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.2.0
[0.1.1]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.1.1
[0.1.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.1.0
