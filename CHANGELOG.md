# Changelog

All notable changes to mcp-locksmith are documented here. This project adheres to
[Semantic Versioning](https://semver.org/). Plugin versions are tracked in each
plugin's `.claude-plugin/plugin.json`.

## [Unreleased]

### Added
- **Real exemplars replace the placeholder.** The shipped set is now three
  vetted, exact-pinned demonstrations of the pattern: `frontend` (no secret),
  `github` (official GitHub remote tool over HTTP, read-only endpoint, PAT via
  `headersHelper` + `mcp-secret` reference — the header route is what makes it
  pinnable), and `notion` (official Notion npm server at an exact version via
  `mcp-launch --secret`, the live spawn-time injection demo).
  `example-secret.json` is gone. Each secret-backed exemplar records
  provenance and its vet date in a `_comment`.
- **Exemplar regression test** (`tests/test_bundles.py`): every shipped file
  must parse, exact-pin anything a fetching launcher runs, contain no
  credential-shaped literals (reuses the guard's `SECRET_VAL`/`SAFE_VAL` via
  AST extraction), route secrets through references, and carry a vet date.
- **Release integrity**: tags are SSH-signed from v1.0.0 on; verification
  material ships in-repo (`.github/allowed_signers` + fingerprint in
  SECURITY.md) with an honest "what this proves" note (TOFU + continuity), and
  a "Verify what you installed" recipe covers `git verify-tag` and diffing the
  installed plugin cache against the tagged tree. CI now runs
  `claude plugin validate --strict` (npm-pinned CLI) on every push.
- **Keep-in-sync test** (`tests/test_keep_in_sync.py`): the credential regexes
  (`SECRET_VAL`/`SECRET_KEY`/`SAFE_VAL`) and the server `identity()` hash are
  duplicated by design across five standalone scripts (mcp-guard.py,
  mcp-call-guard.py, mcp-nudge.py, mcp-doctor, mcp-pin), the most likely
  future-bug site. The test AST-extracts each copy (the scripts exit at import,
  so they can't be imported), asserts the shared patterns are byte-identical
  where duplicated and behave the same against one secret/safe corpus, and
  confirms the three `identity()` copies hash alike. A copy changed without
  mirroring the others now fails CI.

### Changed
- **Shipped bundles are now called exemplars** in user-facing docs and flows
  (add/setup/update, the nudge, the technical README): a handful of
  demonstrations of the pattern, never a catalog. Your private bundles and the
  `mcp-bundles` plumbing keep their names. The add flow's "save for reuse"
  step now writes to your private bundles instead of growing the shipped set.
- **`mcp-globals` folded into `mcp-secure`.** The always-on profile template was
  a second, `defaultEnabled: false` marketplace plugin that nobody installed as
  is (you copy it per profile), and the `always-on` flow pointed at it "in the
  marketplace repo", which plugin-install users never have on disk. It now ships
  as a bundled scaffold inside mcp-secure
  (`templates/globals-profile/`), so `/mcp-secure:always-on` stamps out a profile
  from a template that's actually on the machine. The marketplace now lists one
  plugin. No user action needed: a profile you already created is unaffected (it
  was always your own renamed copy, never the shipped template).

### Fixed
- **`install.sh` aborted with exit 2 on a machine with no vault CLI** (found
  in the v1.0 fresh-machine dogfood): under `pipefail`, the backend-parsing
  `grep` failed on the not-yet-existing config and killed the script after
  the symlink step, even though no-vault is a supported state ("you only need
  a vault if a tool requires a key"). A config missing its
  `MCP_SECRET_BACKEND` line would likewise have died on the very check meant
  to warn about it. Both parses now tolerate absence; regression tests in
  `tests/test_install.py` cover the no-vault and backend-less-config paths.
- **`mcp-pin` couldn't verify remote servers behind an edge WAF** (the
  cloudflare 403): `mcp.cloudflare.com` returns HTTP 403 to the default
  `Python-urllib/x.y` User-Agent before the request reaches the MCP server, so a
  server that connects fine in a live session failed `mcp-pin verify` with an
  opaque "HTTP 403 Forbidden". The auth token, `headersHelper`, and endpoint
  were all correct; only the UA was blocked. `mcp-pin` now sends a named
  `User-Agent` (`mcp-pin/0.1 (mcp-secure)`) on both the JSON-RPC and the DELETE
  teardown requests; a `headers`/`headersHelper` that sets its own User-Agent
  still wins. Covered by a WAF-simulating fixture knob (`FAKE_REJECT_UA`) and a
  new test.
- **`SECRET_KEY` drift between the write guard and the config scan**:
  mcp-guard.py matched `AUTHORIZATION`/`COOKIE` while mcp-doctor matched
  `AUTH`/`BEARER`, so a key named `COOKIE` was flagged on write but not by the
  existing-config scan, and `BEARER` the reverse. Reconciled both to the union
  (`AUTH` subsumes `AUTHORIZATION`; `BEARER` and `COOKIE` kept), so a
  credential-shaped key name is caught the same way on both paths. Frozen by the
  keep-in-sync test above.

## [0.4.0] - 2026-07-03

### Added
- **`mcp-pin pin --replace`**: one-step re-pin that supersedes the previous
  same-name pin. After a version bump / wrapper migration a server hashes to a
  new identity, and the old pin used to linger as an orphan (found dogfooding:
  a reverted migration left the *wrong* baseline live, a latent false-positive
  drift trap). `--replace` drops the stale same-name pin; the update flow now
  passes it. A bare `mcp-pin pin` stays conservative. It FLAGS the superseded
  pin and points at `--replace`/`unpin` rather than deleting it (a same-name
  pin may belong to that server in another repo, invisible from here). Three
  regression tests in test_pin.py.
- **HTTP pinning**: `mcp-pin` now reads `tools/list` over streamable HTTP
  (POST JSON-RPC; both `application/json` and `text/event-stream` response
  bodies; `Mcp-Session-Id` threading), honoring the config's `headers` and
  `headersHelper`, so drift detection covers the transport the docs recommend.
  Remote identity is name + url. The session nudge and the unpinned-tool
  tripwire now cover remote servers that carry `headers`/`headersHelper`, and
  deliberately stay quiet about remote servers with neither, since those
  likely authenticate via Claude Code's OAuth store, which `mcp-pin` can't
  reach (the documented gap; `mcp-pin` explains it on a 401 instead of
  pretending). Legacy `type: "sse"` servers are skipped with a note. Tested
  against a fake streamable-HTTP server fixture (auth, sessions, SSE bodies,
  drift across restarts).
- **`/mcp-secure:update` + `update-tool` skill**: "Dependabot for your MCP
  servers", closing the lifecycle gap where vetting pins a version and nothing
  ever moves it. Discovers versioned specs (incl. inside `mcp-launch … --`),
  checks npm/PyPI for newer versions, **previews the candidate's tool diff
  before any config changes** (added/changed descriptions get the
  tool-poisoning read), then bumps the version and re-pins. Unpinned `npx -y`
  servers get flagged and offered pinning; remote servers are noted as
  updating server-side.
- **`mcp-pin tools -- <command> [args…]`**: plumbing that launches an
  arbitrary command and prints its MCP tool list as JSON; what the update flow
  uses to diff a candidate version against the current one.

- **Runtime call guard** (`hooks/mcp-call-guard.py`): the missing runtime
  layer; every other defense fires before or between sessions. Two advisory
  checks, both `ask` (never deny), fail-open, pure local reads:
  - **Exfiltration guard** (`mcp__*` tools + WebFetch/WebSearch): asks when a
    credential-shaped value (GitHub/Slack tokens, `sk-…`, AWS keys, JWTs, PEM,
    creds-in-URL) is in an outbound tool call's arguments, the classic
    tool-poisoning payoff. Vault references pass; value shapes only, so
    ordinary payloads don't trigger it.
  - **Unpinned-tool tripwire**: first use per session of a server with no
    `mcp-pin` baseline asks once, pointing at `/mcp-secure:check`. Gated so
    non-adopters are never nagged (fires only if ≥1 pin exists, or org
    `policy.requireVetting` is set, the first, still advisory, consumer of
    that flag).
- **Test suite for the untested majority**: regression discovery for
  everything in `bin/` and `hooks/`, not just the config guard: a fake stdio
  MCP server fixture drives `mcp-pin` tests (pin, drift on changed/added/
  removed tools, version-bump-reads-as-new, unpin/prune, the `tools`
  subcommand); stubbed backend CLIs drive `mcp-secret` tests (ref parsing,
  short-ref expansion, and regressions for two shipped security fixes:
  `sops://` path-traversal reject and config parsed-not-executed);
  `mcp-launch` (env/arg injection, no-spawn on failed resolve), `mcp-doctor`
  (inline secrets in env/headers/args, reference resolution), `mcp-nudge`
  (all nudge/silence paths), and the new call guard (48 cases total across
  6 suites). CI now runs on **ubuntu and macos** (two shipped bugs were
  macOS-only) and adds `shellcheck`.

- **`/mcp-secure:fix` + `fix-tool` skill + `mcp-doctor --launch`**: the
  troubleshooting flow ("the Slack tool stopped working"). `--launch` spawns
  each stdio server briefly (via `mcp-pin tools`) and reports whether it starts
  and speaks MCP, including the server's own stderr, which `mcp-pin` now
  captures on launch failures (so "server closed stdout" becomes "missing
  FOO_TOKEN"). The fix flow maps the common failures (backend unauthed, bad
  ref, missing runtime, yanked version, expired OAuth) to their fixes.
- **Verify staleness.** `mcp-pin verify` stamps `lastVerified` on unchanged
  pins (`list` shows it), and the session nudge warns, at most once per
  `MCP_PIN_MAX_AGE` days (default 14) per project, when pinned tools haven't
  been drift-checked in that long. Remote servers no longer counted as
  "unpinned" by the nudge (they can't be pinned yet).
- **Registry discovery in `add`.** A capability request ("something for Jira")
  now searches the official MCP registry and presents candidates with
  provenance; a listing is discovery input, **not** trust. Full vetting still
  runs. Prefers first-party servers over rehosted proxies.
- **Least-privilege permissions offer in `add`.** After pinning, the flow can
  pre-approve just the read-only tools in the project's `.claude/settings.json`
  (native permission system; write/destructive tools keep prompting).

### Fixed
- **`mcp-pin unpin` name collision deleted a fresh re-pin** (found dogfooding
  a wrapper-to-`mcp-launch` migration): it matched pins by name only, so after a
  server's command changed and it was re-pinned under its new identity,
  `unpin <name>` removed the new baseline along with the stale one. With
  multiple matches it now keeps the pin for the server as configured in the
  current context and says so; a single match is still removed unconditionally
  (the deliberate "unpin this server" case).
- **`mcp-doctor` NameError on the no-config path**: it called an undefined
  `info()` when no MCP config files were found.
- **`mcp-secret` fragment-less sops ref crash on macOS** (found by the new
  tests): `sops://file` with no `#/key` fragment died with an unhelpful
  `parts[@]: unbound variable` under bash 3.2 (macOS default) instead of the
  intended "needs a key fragment" error, empty-array expansion under
  `set -u`. Same guard idiom `mcp-launch` already used.
- **`install.sh` age-key dir perms**: `mkdir -p -m 700` applies the mode only
  to the deepest directory (shellcheck SC2174); now chmods explicitly.

### Security
- **Guard covers `--header`.** `claude mcp add --transport http --header
  "Authorization: Bearer <token>"` previously slipped through. The `-e/--env`
  check didn't match headers, and an opaque token has no recognizable shape.
  The guard now anchors on auth-ish header names (Authorization, Cookie,
  X-Api-Key, …) in both the Bash path and stored `headers` objects in
  Write/Edit; `Bearer ${VAR}` and reference forms stay allowed. `mcp-doctor`
  and the nudge scan existing `headers` for inline secrets too.

_v0.4 scope from [PLAN.md](PLAN.md) is complete (update flow + runtime hooks +
header guard gap), with v0.6's test-suite item pulled forward. Org gateway
routing stays deferred ([ROADMAP.md](ROADMAP.md))._

## [0.3.0] - 2026-06-24

### Added
- **Org config: pointer layer.** An optional `org.json`
  (`~/.config/mcp-secret/org.json` or `$MCP_ORG_CONFIG`) lets a team point everyone at
  internal MCP conventions: org name + an internal docs link (`docsUrl`) + `recommended`
  bundles, surfaced in `/mcp-secure:add`, `:setup`, `:check`, and the nudge. The plugin
  only *consumes* and *surfaces* it. Distribution is the org's job. `gateway` fields are
  accepted and shown as info; routing/policy enforcement is **not** built yet (needs a
  real gateway to design against). See [`ORG.md`](plugins/mcp-secure/ORG.md) and
  [ROADMAP.md](ROADMAP.md).

## [0.2.0] - 2026-06-24

Validated end-to-end by a live dogfood: natural-language tool requests, SOPS secret
resolution, the guard, and a real OAuth add (Slack) all confirmed working, which also
turned up several fixes below.

### Added
- **Private (user/team) bundles.** Keep your own vetted server sets in
  `~/.config/mcp-secret/bundles/` (override `$MCP_USER_BUNDLES`) without committing them
  to the public plugin. `mcp-bundles --all` lists shipped + private; `/mcp-secure:add`
  and the nudge read both. (First step toward the org-config story.)

### Fixed
- **SOPS backend on macOS.** `sops`' default age-key location is platform-specific
  (`~/Library/Application Support/…` on macOS), so it never found the key `install.sh`
  writes to `~/.config/sops/age/keys.txt`. Every SOPS secret failed to resolve while
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
  only if there's no OAuth client. Verified live: Slack connected via the clientId.
- **Stray root `.mcp.json` gitignored.** A consumed `.mcp.json` written into the plugin
  repo (e.g. a setup flow run from the wrong dir) is no longer commit-able. It would
  leak the runner's server topology. Anchored so the `mcp-globals` template stays tracked.

## [0.1.1] - 2026-06-23

### Security
- **No more sourcing the secret-backend config.** `mcp-secret` and `install.sh` now
  parse `~/.config/mcp-secret/config` as `KEY=VALUE` instead of `source`-ing it,
  removing a code-execution path if that file were ever attacker-writable. The
  config file is created `chmod 600` and its dir `700`.
- **age-key hardening.** `install.sh` creates the key dir `700` and tightens perms
  (`600`) on a pre-existing key, not just freshly generated ones.
- **Guard covers more credential shapes**: Google API keys (`AIza…`), PEM private
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
  "remove the GitHub server", "are my tool keys safe?"), the user no longer has to type
  a slash command. Skills route to the canonical command flow (single source of truth).
  A CLAUDE.md routing directive reinforces the same default behavior.
- **Proactive adoption nudge.** The SessionStart hook now also fires (once per project)
  when existing servers aren't adopted (a literal secret in config, or unpinned) and
  offers `/mcp-secure:audit`. Fast (local reads only) and marker-gated so it doesn't nag.
- **`/mcp-secure:audit`**: review **already-installed** servers (installing the plugin
  doesn't touch them) and adopt them into the harness: migrate inline secrets to
  references, pin versions/baselines, flag `http://`. Scoped as config hygiene, not a
  scanner. Deep provenance/poisoning analysis is handed off to the tools in
  `VETTING.md`. `mcp-doctor` now also flags pre-existing literal secrets in config.
- **`/mcp-secure:remove`**: a guided removal flow that closes the tool lifecycle:
  unregister the server from its scope, `mcp-pin unpin` its baseline, and prompt to
  **revoke/rotate its secret** so a removed tool never leaves a live orphaned key.
- **`mcp-pin unpin <name…>` / `mcp-pin prune`**: drop the pin for a removed server
  (prune is dry-run unless `--yes`, since pin discovery is per-directory).
- `SECURITY.md`: threat model, non-goals, and plugin pinning/update guidance.

## [0.1.0] - 2026-06-23

Initial release. A Claude Code plugin marketplace for adding MCP servers (tools)
safely, with secrets kept out of config and out of the model's context.

### Added
- **`mcp-secure` plugin**: the toolkit:
  - Commands: `/mcp-secure:setup` (guided first-time setup), `/mcp-secure:add`
    (add a ready-made bundle *or* vet & add a brand-new tool, auto-detected),
    `/mcp-secure:check` (one health check: secret chain resolves **and** no tool
    drifted), `/mcp-secure:verify` (focused drift-only check), `/mcp-secure:always-on`
    (set up an always-on / global tool).
  - `mcp-secret` / `mcp-launch`: resolve a secret *reference* from your vault and
    inject it at spawn, so config holds references, never literal secrets.
  - `mcp-doctor`: health-checks the chain and turns each gap into an actionable,
    secure fix (install command, auth command, BACKENDS.md pointer).
  - `mcp-pin`: pins each server's tool definitions and detects drift (rug-pull
    defense).
  - **Guard hook**: blocks literal secrets from reaching MCP config via
    `claude mcp add` (`-e` / `add-json`), shell redirects/tee into
    `*.mcp.json` / `~/.claude.json`, or Write/Edit (including secrets in `args`
    arrays); confirms global-scope changes. Defense-in-depth, fail-open.
  - Vetted, ready-to-add bundles (e.g. `frontend`).
  - `VETTING.md`: the add-time security checklist (provenance, version pinning,
    least privilege, tool-poisoning/rug-pull, supply chain).
  - `BACKENDS.md`: secure setup for 1Password, Bitwarden, and SOPS+age, including
    age-key generation and handling.
- **`mcp-globals` plugin**: template for a profile of always-on servers.
- `install.sh`: puts the helpers on PATH, records your default secret backend, and
  bootstraps an age key on the SOPS path.
- Secret backends: 1Password (`op`), Bitwarden (`bw`), SOPS+age (`sops`).

[0.4.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.4.0
[0.3.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.3.0
[0.2.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.2.0
[0.1.1]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.1.1
[0.1.0]: https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.1.0
