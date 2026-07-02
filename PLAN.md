# Plan to feature-complete (v1.0)

**Vision:** a super easy to use, useful-for-everyone MCP harness that builds in
QoL *and* security improvements for all MCP installation and handling.

[ROADMAP.md](ROADMAP.md) holds the one deliberately deferred direction (org
gateway/policy); shipped items move to [CHANGELOG.md](CHANGELOG.md).

## Definition of feature-complete

A user who knows nothing about MCP can: **install** in ~2 minutes; **add any
tool** in plain language (vetted bundle catalog → public registry → vet-new),
with secrets always OAuth or vault references; **use tools** with invisible
runtime protection (`ask`, never `deny`; no felt latency); **fix** a broken tool
by saying so; **update** tools with a plain-language tool-diff before adopting;
**trust** drift detection across stdio *and* HTTP, told when checks go stale;
**remove** tools with the key revoked (✅ v0.1.1); **work as a team** via org
config + private bundles (✅ v0.2/v0.3); and **trust the plugin itself** —
everything in `bin/` and `hooks/` tested in CI, releases pinnable.

## Principles (every feature below)

- **Quiet by default** — runtime interventions `ask`, never `deny`; nudge once.
- **Fail open** — an erroring hook allows the action; defense-in-depth, not a sandbox.
- **No felt latency** — hooks do local reads only; never launch servers or hit the network.
- **Plain language** — users say "tool," not "MCP server."
- **Don't duplicate the platform** — integrate with Claude Code's permission
  system and OAuth store; generate config for them, don't re-implement them.

## v0.4 — Lifecycle & runtime guard

1. ✅ **`/mcp-secure:update` + `update-tool` skill (L).** "Dependabot for MCP
   servers" — vetting pins a version, then nothing ever moves it. Discover
   versioned specs (`npx pkg@x`, `uvx pkg==x`, incl. inside `mcp-launch … --`),
   check npm/PyPI for latest, **launch the candidate in isolation and diff its
   tools against the current pin** (plain-language: "the new version adds a
   `delete_repo` tool"), re-vet the diff only (VETTING.md step 7), then rewrite
   the version, re-pin, and offer to update the matching bundle.
   *Implementation:* `mcp-pin` gains a plumbing subcommand
   (`mcp-pin tools -- <cmd>…`) so no second MCP client is written. Remote
   servers skip until v0.6.
2. ✅ **Runtime hooks (M)** — the missing layer; today every defense fires before
   or between sessions.
   - ✅ **Exfil guard:** PreToolUse on `mcp__.*` (+ `WebFetch|WebSearch`); `ask`
     when a credential-shaped value heads out through a tool call (the classic
     tool-poisoning payoff). References pass.
   - ✅ **Unpinned-tool tripwire:** on an `mcp__<server>__*` call, check
     `pins.json` (pure file reads); `ask` once per server per session if
     unpinned. Gated: only fires if the user has ≥1 pin or org
     `policy.requireVetting` is set — never nags non-adopters. (First advisory
     consumer of `policy.requireVetting`.)
   - ✅ **Guard gap:** `claude mcp add --header "Authorization: Bearer <opaque>"`
     evaded both the `-e` regex and known token shapes — header check added.
   - ✅ Tests in CI; SECURITY.md/README gain the runtime layer.
   *Acceptance:* measured ~70ms/call, of which ~50ms is Python interpreter
   startup (the existing config guard pays the same floor) — imperceptible
   against a real tool call. Zero-unwarranted-asks still to confirm across a
   few real dogfood sessions.

## v0.5 — Useful for everyone

1. **Bundle catalog (M, ongoing).** From 2 bundles to the ~10 everyone wants:
   GitHub, browser, filesystem, Postgres, SQLite, fetch/search, Slack,
   notes/memory, Sentry, docs. Each vetted, exact-pinned, vet date recorded.
   Write the inclusion criteria into VETTING.md step 8.
2. ✅ **Registry discovery in `add` (S).** No bundle match → query the official
   MCP registry by capability, present matches with provenance signals, feed the
   pick into the existing vetting path. Registry listing is discovery input,
   **not** trust.
3. ✅ **`/mcp-secure:fix` + `fix-tool` skill (M).** `mcp-doctor --launch` (briefly
   spawns stdio servers via `mcp-pin tools`, surfaces the server's stderr) + a
   flow for "the Slack tool stopped working": doctor chain → launch check →
   guided fix (reauth, unlock vault, reinstall pin).
4. ✅ **Least-privilege permissions at add time (S).** Offer a suggested
   `.claude/settings.json` block: allow read-only tools, keep write/destructive
   on `ask`. Native mechanism, no runtime policy engine.
5. ✅ **Setup polish (S).** Already true: `setup` step 2 runs `install.sh` itself;
   the no-key path is zero-config. Metric (fresh machine → working browser tool
   in <5 min) to confirm at the v1.0 dogfood pass.

## v0.6 — Coverage & trust

1. **HTTP support in `mcp-pin` (M).** The advice "prefer OAuth remote servers"
   and "stdio only" are in tension — the recommended type is the one drift
   detection skips. Add `tools/list` over streamable HTTP honoring
   `headers`/`headersHelper`. OAuth tokens in Claude Code's store stay a
   documented gap — honest labeling over fake coverage.
2. ✅ **Verify staleness (S).** Pins get `lastVerified`; the nudge warns past
   `MCP_PIN_MAX_AGE` (default 14 days), at most once per period. No auto-verify
   per session (launches every server).
3. ✅ **Test the untested majority (L)** *(pulled forward into v0.4).* Fake stdio
   MCP server fixture → `mcp-pin` pin/verify/drift/unpin/prune tests; stub
   backends for `mcp-secret` (incl. `sops://` traversal-reject regression);
   stub `mcp-secret` for `mcp-launch`; nudge + runtime-hook + doctor tests;
   `shellcheck` in CI; ubuntu **and** macos matrix (the SOPS key-location bug
   was invisible to single-OS CI — and the suite immediately caught a second
   macOS-only bash-3.2 bug in `mcp-secret`).
4. ✅ **State platform scope (XS).** Native Windows unsupported (WSL works) —
   stated in README + SECURITY.md.

## v1.0 — Positioning & release trust

1. **README repositioning (S).** Lead with "the easiest way to give Claude
   tools — safe by default"; quickstart recording. Convenience is the hook,
   security the trust-builder.
2. **Release integrity (S).** Signed/verified tags, CHANGELOG per milestone,
   "verify what you installed" section.
3. **Full dogfood pass (M).** Clean machine, every flow, against the definition
   above as a literal checklist — the release gate (v0.2.0 proved it catches
   real bugs).

## Non-goals

No gateway / policy hard-enforcement (see [ROADMAP.md](ROADMAP.md)); no
sandboxing of approved servers; no PostToolUse result scanning (deferred to the
scanners VETTING.md points at); no org-config distribution; no native Windows.

## Risks

- **Exfil-guard false positives** → ask-only, known shapes, dogfood hunts for
  unwarranted asks before release.
- **HTTP pinning vs OAuth** → may stay partial; label it.
- **Update previews execute the new version** → that's the point (inspect
  before adopting), but frame it and recommend `sfw` for the fetch.
