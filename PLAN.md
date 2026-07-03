# Plan to v1.0 — ship it

**Vision:** a super easy to use, useful-for-everyone MCP harness that builds in
QoL *and* security improvements for all MCP installation and handling.

**Positioning (decided 2026-07-02, distribution assessment):** the product is
the **harness** — vault-reference secrets, tool pinning, runtime guards,
plain-language flows — local, no cloud, no containers, inside Claude Code.
Every incumbent imposes one of those costs (Snyk cloud for mcp-scan, Docker for
ToolHive, deployed infra for the gateways), and no other Claude Code plugin
covers this niche. The main risk is **time, not competition**: native `op://`
resolution and tool-change re-approval are open, assigned Claude Code feature
requests. Ship before the gap closes.

[ROADMAP.md](ROADMAP.md) holds deferred directions; shipped items live in
[CHANGELOG.md](CHANGELOG.md). Completed milestone detail (v0.4–v0.6) was
removed from this file 2026-07-02 — see CHANGELOG and git history.

## Descoped 2026-07-02 (do not re-add before 1.0)

- **Bundle catalog** (was "~10 vetted bundles, ongoing"). Catalogs are the
  *crowded* part of the market (Docker MCP Catalog, official registry,
  Smithery, mcpm) and per-server vetting is a staleness treadmill with implied
  liability. The harness's value is making *any* server safe to adopt;
  registry discovery in `add` (shipped) covers finding them. Keep only
  **exemplars** (Gate 2).
- **Plugin-scope server discovery in `mcp-pin`** — post-1.0 candidate, noted
  in ROADMAP if the gap ever bites.
- **Quickstart recording** — nice-to-have, not release-blocking.

## Gate 1 — dogfood, then release v0.5.0

Real-world MCP-heavy sessions (in progress since 2026-07-02):

1. The **exfil guard** must produce zero unwarranted asks — note every ask it
   raises and whether it was warranted.
2. The **tripwire** must stay silent with no pins; then `mcp-pin pin` one
   server and confirm exactly one ask per session for *unpinned* servers only.
3. Break a tool on purpose (rename a vault item, or lock the vault) →
   "the X tool is broken" should route to the fix flow and `mcp-doctor
   --launch` should name the real cause.
4. Ask "are my tools up to date?" → the update flow should find the pinned
   versions, diff a candidate's tools, and re-pin cleanly.
5. Confirm the SessionStart nudge fires at most once and says something true.
6. HTTP pinning: pin a remote server with `headers`; confirm OAuth-store
   servers are skipped quietly, never nagged. (Needs a headers-based remote
   server in `./.mcp.json` or `~/.claude.json` — plugin-scope servers are
   invisible to `mcp-pin`, see descope note.)

Finding so far (2026-07-02): a session that exits at the trust dialog never
runs hooks, so the nudge can't fire — correct behavior, not a bug. And the
nudge surfaces in Claude's **first reply**, not as a startup prompt — set that
expectation in the README (Gate 2, item 3).

**If clean →** stage **v0.5.0**: bump
`plugins/mcp-secure/.claude-plugin/plugin.json`, date the CHANGELOG
`[Unreleased]` section (+ link at bottom), tag, GitHub release.
**If not →** fix, add a regression test, re-dogfood.

## Gate 2 — v1.0 hardening (small and bounded)

1. **Exemplar bundles, not a catalog (S).** Replace the `example-secret`
   placeholder with ONE real secret-backed bundle (GitHub is the obvious pick:
   exact-pinned, vet date recorded) so the `mcp-launch` reference pattern has a
   live demonstration. Keep `frontend.json`. 3–4 bundles total, presented as
   *exemplars of the pattern* in the README — never as a curated catalog.
2. **Keep-in-sync CI test (S).** Assert the `SECRET_VAL`/`SECRET_KEY`/
   `SAFE_VAL` regexes and the `identity()` scheme are byte-identical across
   their five copies (mcp-guard.py, mcp-call-guard.py, mcp-nudge.py,
   mcp-doctor, mcp-pin). This duplication is the most likely future-bug site;
   the test makes the "keep in sync" comments enforceable.
3. **README repositioning (S).** Lead with "the easiest way to give Claude
   tools — safe by default"; convenience is the hook, security the
   trust-builder. Position explicitly against the incumbents' costs (no cloud,
   no containers, no gateway). Rename bundles → exemplars. Document that the
   SessionStart nudge appears in Claude's first reply.
4. **Release integrity (S).** Signed/verified tags; a "verify what you
   installed" section; CHANGELOG per milestone.

## Gate 3 — release v1.0.0 & distribute

1. **Full clean-machine dogfood pass (M)** — every flow, against the
   definition of feature-complete below as a literal checklist. This is the
   release gate (the v0.2.0 pass proved it catches real bugs; fresh machine →
   working browser tool in <5 min is the setup metric).
2. Tag **v1.0.0**, GitHub release.
3. **Submit to the community marketplace**
   (`anthropics/claude-plugins-community`) — automated safety screening plus
   listing is the cheapest credibility and discovery available, and directly
   addresses the trust-bootstrap problem (a security plugin from an
   unestablished author).

## Definition of feature-complete (v1.0)

A user who knows nothing about MCP can: **install** in ~2 minutes; **add any
tool** in plain language (exemplar bundle → public registry → vet-new), with
secrets always OAuth or vault references; **use tools** with invisible runtime
protection (`ask`, never `deny`; no felt latency); **fix** a broken tool by
saying so; **update** tools with a plain-language tool-diff before adopting;
**trust** drift detection across stdio *and* HTTP, told when checks go stale;
**remove** tools with the key revoked; **work as a team** via org config +
private bundles; and **trust the plugin itself** — everything in `bin/` and
`hooks/` tested in CI, releases pinnable and verifiable.

## Principles

- **Quiet by default** — runtime interventions `ask`, never `deny`; nudge once.
- **Fail open** — an erroring hook allows the action; defense-in-depth, not a sandbox.
- **No felt latency** — hooks do local reads only; never launch servers or hit the network.
- **Plain language** — users say "tool," not "MCP server."
- **Don't duplicate the platform** — integrate with Claude Code's permission
  system and OAuth store; generate config for them, don't re-implement them.

## Non-goals

No bundle catalog (exemplars only — see descope); no gateway / policy
hard-enforcement (see [ROADMAP.md](ROADMAP.md)); no sandboxing of approved
servers; no PostToolUse result scanning (deferred to the scanners VETTING.md
points at); no org-config distribution; no native Windows.

## Risks

- **Obsolescence by the platform** — native `op://` resolution and tool-change
  re-approval are open, assigned upstream issues. Mitigation: ship now;
  multi-backend support and the flows survive either landing.
- **Exfil-guard false positives** → ask-only, known shapes, dogfood hunts for
  unwarranted asks before release.
- **HTTP pinning vs OAuth** → stays partial; label it honestly.
- **Update previews execute the new version** → that's the point (inspect
  before adopting), but frame it and recommend `sfw` for the fetch.
