# Plan to v1.0: ship it

**Vision:** a super easy to use, useful-for-everyone MCP harness that builds in
QoL *and* security improvements for all MCP installation and handling.

**Positioning (decided 2026-07-02, distribution assessment):** the product is
the **harness** (vault-reference secrets, tool pinning, runtime guards,
plain-language flows), local, no cloud, no containers, inside Claude Code.
Every incumbent imposes one of those costs (Snyk cloud for mcp-scan, Docker for
ToolHive, deployed infra for the gateways), and no other Claude Code plugin
covers this niche. The main risk is **time, not competition**: native `op://`
resolution and tool-change re-approval are open, assigned Claude Code feature
requests. Ship before the gap closes.

[ROADMAP.md](ROADMAP.md) holds deferred directions; shipped items live in
[CHANGELOG.md](CHANGELOG.md). Completed milestone detail (v0.4-v0.6) was
removed from this file 2026-07-02. See CHANGELOG and git history.

## Status (2026-07-03 end of session) & next session

**Gate 1 dogfood is COMPLETE. All six checklist items validated on real
config. Ready to stage v0.4.0** (pending two minor loose ends, below, that can
be confirmed or explicitly deferred).

Gate 1 checklist, all green:

1. **Exfil guard**: silent across every dogfood session, zero unwarranted
   asks. ✅ (keep watching)
2. **Tripwire**: validated LIVE against real config + pins (2026-07-03):
   `slack` (OAuth-store, no headers) silent, `cloudflare` (headersHelper,
   unpinned) asks once, `opnsense` (pinned) silent, second cloudflare call
   silent. Plus 10 unit cases in test_call_guard.py. ✅
3. **Break a tool / fix flow**: `mcp-doctor --launch` validated against a
   deliberately-broken config: named all four real causes precisely (missing
   runtime, unresolvable `sops://` ref, surfacing the server's OWN stderr,
   `${…}` plugin-scope leak, remote-to-HTTP-verify routing), each with the right
   fix tip. fix.md maps each to a documented remedy. ✅
4. **Update flow**: playwright/chrome-devtools bumped with a correct tool-diff
   preview; re-pinned; the unpin name-collision fix (`47552c6`) exercised live
   under a real multi-pin collision. ✅ (2026-07-03)
5. **Nudge**: fires at most once, says something true. ✅
6. **HTTP pinning**: homeassistant + portainer verified over streamable HTTP
   via `headersHelper`; slack correctly reported as the OAuth-store gap. ✅

Bonus dogfood (2026-07-03): **add** (context7, keyless user-scope, pinned) and
**audit** (unifi migrated wrapper to `mcp-launch --secret`; portainer/cloudflare/
homeassistant correctly ruled NOT migration candidates) both ran clean.

**UX fix shipped this session (2026-07-03):** orphan pins accumulated silently
after every identity change (version bump / migration / revert). 2 real
orphans (`google-sheets`, a stale `portainer`) built up over ~10 days, and the
reverted portainer migration left the WRONG (14-tool) baseline live while the
102-tool pin orphaned, a latent false-positive drift trap. Added
`mcp-pin pin --replace` (supersedes the same-name prior pin in one step; the
re-pin flows pass it; a bare pin now FLAGS the orphan instead of leaving it
silent) + 3 regression tests; `update.md` re-pin now uses `--replace`.

Next session, in order:

1. ✅ **Confirmed live (2026-07-03, fresh session):** opnsense
   (`test_connection` returned 26.1.10, real interfaces) and unifi-network
   (`list_devices` returned 3 real devices) both connect via their `sops://` chains.
   The `unifi-mcp-wrapper.sh` fallback can now be deleted.
2. **Real-orphan housekeeping**: `mcp-pin prune` still shows `google-sheets`
   + stale `portainer`; sweep them, and re-pin portainer fresh with `--replace`
   so its LIVE baseline matches what the server actually serves (else `verify`
   false-alarms). Heed prune's cross-repo warning.
3. **Chase the cloudflare 403**: `mcp-pin` can't list tools at
   `mcp.cloudflare.com` with the headersHelper token, yet sessions connect
   (likely OAuth-store auth + a stale/underscoped helper token). The tripwire
   correctly asks about it because it's genuinely unpinned. Either fix the
   token or drop the helper (accepting the documented no-pin gap).
4. **Stage v0.4.0**: bump plugin.json, date CHANGELOG, tag, GitHub release.
   Gate 1 is done; 1-3 are confirmations/housekeeping, not blockers.

Optional dogfood fodder: migrate the portainer-stdio wrapper (`--arg`, still no
real-world user) and slim the headers scripts to `mcp-secret` one-liners.

## Descoped 2026-07-02 (do not re-add before 1.0)

- **Bundle catalog** (was "~10 vetted bundles, ongoing"). Catalogs are the
  *crowded* part of the market (Docker MCP Catalog, official registry,
  Smithery, mcpm) and per-server vetting is a staleness treadmill with implied
  liability. The harness's value is making *any* server safe to adopt;
  registry discovery in `add` (shipped) covers finding them. Keep only
  **exemplars** (Gate 2).
- **Plugin-scope server discovery in `mcp-pin`**: post-1.0 candidate, noted
  in ROADMAP if the gap ever bites.
- **Quickstart recording**: nice-to-have, not release-blocking.

## Gate 1: dogfood, then release v0.4.0 ✅ COMPLETE (2026-07-03)

All six items validated on real config. See the Status block above for the
per-item evidence. Kept here as the checklist of record:

Real-world MCP-heavy sessions (2026-07-02 to 2026-07-03):

1. The **exfil guard** must produce zero unwarranted asks. Note every ask it
   raises and whether it was warranted.
2. The **tripwire** must stay silent with no pins; then `mcp-pin pin` one
   server and confirm exactly one ask per session for *unpinned* servers only.
3. Break a tool on purpose (rename a vault item, or lock the vault), then
   "the X tool is broken" should route to the fix flow and `mcp-doctor
   --launch` should name the real cause.
4. Ask "are my tools up to date?" then the update flow should find the pinned
   versions, diff a candidate's tools, and re-pin cleanly.
5. Confirm the SessionStart nudge fires at most once and says something true.
6. HTTP pinning: pin a remote server with `headers`; confirm OAuth-store
   servers are skipped quietly, never nagged. (Needs a headers-based remote
   server in `./.mcp.json` or `~/.claude.json`. Plugin-scope servers are
   invisible to `mcp-pin`, see descope note.)

Findings so far (2026-07-02):

- A session that exits at the trust dialog never runs hooks, so the nudge
  can't fire, correct behavior, not a bug. And the nudge surfaces in Claude's
  **first reply**, not as a startup prompt. Set that expectation in the
  README (Gate 2, item 3).
- Real wrapper-to-mcp-launch migration (opnsense, both repos): guard correctly
  allowed `sops://` refs into `.mcp.json`; `mcp-pin tools` proved the new
  entry end-to-end; prune's cwd-relative warning was true and useful.
- **BUG (✅ fixed 2026-07-02): `mcp-pin unpin <name>` matched by name only**.
  After a re-pin under a new identity (the standard migration flow), it
  deleted the NEW pin along with the stale one. Now keeps the live-identity
  pin when a name matches several; regression test in test_pin.py; CHANGELOG
  under Fixed.
- **UX (✅ fixed 2026-07-03): orphan pins accumulated silently.** Every
  identity change left a stale same-name pin; 2 built up over ~10 days and a
  reverted portainer migration left the wrong baseline live (latent
  false-positive drift). Added `mcp-pin pin --replace` (one-step supersede;
  re-pin flows pass it; bare pin now flags the orphan) + 3 regression tests;
  `update.md` updated. CHANGELOG under Added.

**If clean, then** stage **v0.4.0**: bump
`plugins/mcp-secure/.claude-plugin/plugin.json`, date the CHANGELOG
`[Unreleased]` section (+ link at bottom), tag, GitHub release.
**If not, then** fix, add a regression test, re-dogfood.

## Gate 2: v1.0 hardening (small and bounded)

1. **Exemplar bundles, not a catalog (S).** Replace the `example-secret`
   placeholder with ONE real secret-backed bundle (GitHub is the obvious pick:
   exact-pinned, vet date recorded) so the `mcp-launch` reference pattern has a
   live demonstration. Keep `frontend.json`. 3-4 bundles total, presented as
   *exemplars of the pattern* in the README, never as a curated catalog.
2. **Keep-in-sync CI test (S).** Assert the `SECRET_VAL`/`SECRET_KEY`/
   `SAFE_VAL` regexes and the `identity()` scheme are byte-identical across
   their five copies (mcp-guard.py, mcp-call-guard.py, mcp-nudge.py,
   mcp-doctor, mcp-pin). This duplication is the most likely future-bug site;
   the test makes the "keep in sync" comments enforceable.
3. **README repositioning (S).** Lead with "the easiest way to give Claude
   tools, safe by default"; convenience is the hook, security the
   trust-builder. Position explicitly against the incumbents' costs (no cloud,
   no containers, no gateway). Rename bundles to exemplars. Document that the
   SessionStart nudge appears in Claude's first reply.
4. **Release integrity (S).** Signed/verified tags; a "verify what you
   installed" section; CHANGELOG per milestone.

## Gate 3: release v1.0.0 & distribute

1. **Full clean-machine dogfood pass (M)**: every flow, against the
   definition of feature-complete below as a literal checklist. This is the
   release gate (the v0.2.0 pass proved it catches real bugs; fresh machine to
   working browser tool in <5 min is the setup metric).
2. Tag **v1.0.0**, GitHub release.
3. **Submit to the community marketplace**
   (`anthropics/claude-plugins-community`): automated safety screening plus
   listing is the cheapest credibility and discovery available, and directly
   addresses the trust-bootstrap problem (a security plugin from an
   unestablished author).

## Definition of feature-complete (v1.0)

A user who knows nothing about MCP can: **install** in ~2 minutes; **add any
tool** in plain language (exemplar bundle to public registry to vet-new), with
secrets always OAuth or vault references; **use tools** with invisible runtime
protection (`ask`, never `deny`; no felt latency); **fix** a broken tool by
saying so; **update** tools with a plain-language tool-diff before adopting;
**trust** drift detection across stdio *and* HTTP, told when checks go stale;
**remove** tools with the key revoked; **work as a team** via org config +
private bundles; and **trust the plugin itself**: everything in `bin/` and
`hooks/` tested in CI, releases pinnable and verifiable.

## Principles

- **Quiet by default**: runtime interventions `ask`, never `deny`; nudge once.
- **Fail open**: an erroring hook allows the action; defense-in-depth, not a sandbox.
- **No felt latency**: hooks do local reads only; never launch servers or hit the network.
- **Plain language**: users say "tool," not "MCP server."
- **Don't duplicate the platform**: integrate with Claude Code's permission
  system and OAuth store; generate config for them, don't re-implement them.

## Non-goals

No bundle catalog (exemplars only, see descope); no gateway / policy
hard-enforcement (see [ROADMAP.md](ROADMAP.md)); no sandboxing of approved
servers; no PostToolUse result scanning (deferred to the scanners VETTING.md
points at); no org-config distribution; no native Windows.

## Risks

- **Obsolescence by the platform**: native `op://` resolution and tool-change
  re-approval are open, assigned upstream issues. Mitigation: ship now;
  multi-backend support and the flows survive either landing.
- **Exfil-guard false positives**: ask-only, known shapes, dogfood hunts for
  unwarranted asks before release.
- **HTTP pinning vs OAuth** stays partial; label it honestly.
- **Update previews execute the new version**: that's the point (inspect
  before adopting), but frame it and recommend `sfw` for the fetch.
