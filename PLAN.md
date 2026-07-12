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

## Status (2026-07-11) & the v1.0 spec

**v0.4.0 SHIPPED (2026-07-03).** Tag and GitHub release are published:
https://github.com/pietercastle-dev/mcp-locksmith/releases/tag/v0.4.0. Gate 1
dogfood is complete; all six checklist items were validated on real config. The
release bundles the planned v0.4-v0.6 scope: HTTP pinning, the update flow, the
runtime call guard, the fix flow, and the `mcp-pin pin --replace` UX fix.

Gate 1 checklist, all green (evidence of record):

1. **Exfil guard**: silent across every dogfood session, zero unwarranted asks.
2. **Tripwire**: validated LIVE against real config + pins: `slack`
   (OAuth-store) silent, `cloudflare` (headersHelper, unpinned) asks once,
   `opnsense` (pinned) silent, once per session. Plus 10 unit cases.
3. **Break a tool / fix flow**: `mcp-doctor --launch` named all four real causes
   (missing runtime, unresolvable `sops://` ref surfacing the server's stderr,
   `${…}` plugin-scope leak, remote HTTP-verify routing). fix.md maps each.
4. **Update flow**: playwright/chrome-devtools bumped with a correct tool-diff,
   re-pinned; the unpin name-collision fix exercised live.
5. **Nudge**: fires at most once, says something true.
6. **HTTP pinning**: homeassistant + portainer verified over streamable HTTP.

Done 2026-07-03 (session 2): keep-in-sync CI test (Gate 2 item 2, caught and
fixed a real `SECRET_KEY` drift) and the mcp-globals fold into mcp-secure.
Done 2026-07-03/04: the cloudflare 403 (edge WAF rejected the default
`Python-urllib` User-Agent; `mcp-pin` now sends a named UA, WAF-simulating
fixture test added) and the README "How it compares" table. Done 2026-07-11:
docs hardening — SECURITY.md non-goals now state that tool *output* is not
hookable and that hooks share Claude Code's in-process trust boundary;
CLAUDE.md warns that the `plugin.json` version is the install cache key (a
change shipped without a bump is invisible to plugin-install users); ROADMAP
adds the argument-level tool scoping deferral.

What remains to v1.0 is specified below: exemplars (Gate 2 item 1 + the folded
rename), release integrity (Gate 2 item 4), then Gate 3 (clean-machine
dogfood, v1.0.0, marketplace submission).

### Spec A: exemplars (Gate 2 item 1 + the bundles-to-exemplars reframing)

**Goal:** the shipped bundles demonstrate every secret pattern with real,
exact-pinned servers, and user-facing docs frame them as *exemplars of the
pattern* — never a catalog.

Ship exactly three files in `plugins/mcp-secure/bundles/`:

1. **`frontend.json`** (exists, keep): playwright + chrome-devtools, exact-
   pinned, no secrets. The no-secret exemplar.
2. **`github.json`** (new): the official GitHub remote MCP
   (`https://api.githubcopilot.com/mcp`), PAT supplied via `headersHelper`
   calling `mcp-secret` with a vault reference. Demonstrates the secret-
   reference pattern for HTTP servers (and exercises HTTP pinning, shipped
   v0.4.0).
3. **`notion.json`** (new): Notion's official stdio server from npm at an
   exact version, launched via `mcp-launch --secret <ENV>=<ref>`. The live
   `mcp-launch` demonstration the `example-secret` placeholder stood in for.
   Verify the current package name, exact version, and expected env var at
   build time; vet per VETTING.md.

Then **delete `example-secret.json`**. Why two secret-backed exemplars when
the plan said one: GitHub's official server is remote-HTTP-only outside
Docker, so a GitHub exemplar cannot demonstrate `mcp-launch` (spawn-time env
injection into a local process). One exemplar per secret pattern is the
minimum that leaves no pattern undemonstrated; three files total stays within
the 3-4 budget. Each new exemplar records provenance and its vet date in a
`_comment`.

**Reframing (user-facing prose only).** The *shipped set* is called
"exemplars"; the JSON file format, the `mcp-bundles` command, the `bundles/`
paths, `MCP_USER_BUNDLES`, and "your private bundles" keep their names. Known
touch points: `commands/add.md`, `commands/setup.md`, `commands/update.md`,
`skills/add-tool/SKILL.md`, the `mcp-nudge.py` message, the `mcp-doctor` tip
string, the plugin README table, the top-level README, `ORG.md`, `VETTING.md`.
The framing sentence to land everywhere it fits: exemplars demonstrate the
pattern; discovery of everything else goes through the registry in `add`.

**New test `tests/test_bundles.py`:** every shipped exemplar parses as JSON
with an `mcpServers` object; every npm/PyPI-launched server pins an exact
version (no `latest`, no bare package name); no config value looks like a
literal credential (reuse the test corpus style from `test_keep_in_sync.py`);
any server that needs a secret routes it through `mcp-launch --secret` or a
`headersHelper` reference. This is what keeps "exemplar" from regressing to
"placeholder".

**Acceptance:** the add flow offers all three exemplars by name; adding
`github` and `notion` on a real machine resolves secrets from the vault and
pins clean; no shipped doc calls the set a catalog; suite green.

### Spec B: release integrity (Gate 2 item 4)

Context (verified 2026-07-11 against the plugin-marketplace docs): the plugin
ecosystem has no signing convention; distribution integrity is git tags plus
the community catalog pinning approved plugins to a commit SHA. So the story
is tags users can verify, plus mechanical validation:

1. **Sign tags from v1.0.0 on** (SSH signing key). Publish verification
   material in-repo: an `allowed_signers` file plus the key fingerprint in
   SECURITY.md.
2. **"Verify what you installed"** section in SECURITY.md, linked from the
   README trust section: the `git verify-tag` recipe against `allowed_signers`,
   and how to diff the installed plugin cache
   (`~/.claude/plugins/cache/...`) against the tagged tree.
3. **`claude plugin validate --strict`** as a CI step and pre-submission
   checklist item. Fill out `plugin.json` metadata completely (author,
   repository, homepage, license, keywords) — the submission pipeline wants
   it, and it is what users see in `/plugin`.

**Acceptance:** CI green including validate; `git verify-tag v1.0.0` passes
using only material published in the repo; SECURITY.md explains verification
in plain language.

### Spec C: Gate 3 — dogfood, release, submit

1. **Clean-machine dogfood (M):** fresh HOME and fresh clone (true clean
   machine preferred), walking the definition of feature-complete below as a
   literal checklist. Metric: fresh machine to working browser tool in under
   5 minutes. Every command in the README must work exactly as written.
2. **Stage v1.0.0** per the CLAUDE.md release pattern — bump `plugin.json`
   (the cache key), date the CHANGELOG, **signed** tag, GitHub release.
3. **Submit to the community marketplace**: run `claude plugin validate
   --strict`, then submit the repo through the individual-author plugin
   submission form on platform.claude.com. Approved plugins land pinned to a
   commit SHA in `anthropics/claude-plugins-community`; the public catalog
   syncs nightly, so check the listing after a day. Submission and tag push
   are outward-facing: operator confirms before each.

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

**Released as v0.4.0 (2026-07-03):** bumped
`plugins/mcp-secure/.claude-plugin/plugin.json`, dated the CHANGELOG, tagged, and
published the GitHub release. Next release is v0.5.0 or v1.0.0 after Gate 2.

## Gate 2: v1.0 hardening (small and bounded)

1. **Exemplar bundles, not a catalog (S).** Replace the `example-secret`
   placeholder with ONE real secret-backed bundle (GitHub is the obvious pick:
   exact-pinned, vet date recorded) so the `mcp-launch` reference pattern has a
   live demonstration. Keep `frontend.json`. 3-4 bundles total, presented as
   *exemplars of the pattern* in the README, never as a curated catalog.
2. **Keep-in-sync CI test (S). ✅ DONE (2026-07-03).** `tests/test_keep_in_sync.py`
   asserts the `SECRET_VAL`/`SECRET_KEY`/`SAFE_VAL` regexes and the `identity()`
   scheme match across their copies (guard, call-guard, nudge, doctor, pin) and
   behave the same against a shared corpus. It surfaced a real `SECRET_KEY` drift
   (guard `AUTHORIZATION`/`COOKIE` vs doctor `AUTH`/`BEARER`), now reconciled to
   the union. The "keep in sync" comments are enforceable.
3. **README repositioning (S). ✅ mostly DONE (2026-07-04).** Hero already led
   with "the easiest way to give Claude tools, safe by default." Sharpened the
   incumbent contrast: the hero names the *shapes* (cloud scanner / container
   runtime / proxy gateway) without naming rivals (durable), and a new "How it
   compares" table names them for SEO and comparison shoppers (mcp-scan needs a
   Snyk account + token and shares tool metadata; ToolHive needs Docker/Podman;
   gateways need a deployed service), each with an honest "strongest at" so the
   section builds credibility instead of overclaiming. Documented that the drift
   reminder appears in Claude's first reply, not a popup. **Remaining:** the
   bundles-to-exemplars rename, deliberately folded into item 1 (it spans the add
   flow + technical README, so it belongs with the exemplar-bundle work).
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
