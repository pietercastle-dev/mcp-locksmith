#!/usr/bin/env python3
"""PreToolUse guard for OUTBOUND tool calls — the runtime layer.

Every other defense fires before or between sessions (vetting at add time, the
config-write guard, on-demand pin checks). This hook watches the calls
themselves. Two advisory checks — both `ask`, never deny (see PLAN.md):

1. Exfiltration guard (mcp__* tools + WebFetch/WebSearch): a credential-shaped
   value in a tool call's arguments is a secret about to LEAVE the machine —
   the classic tool-poisoning payoff ("read ~/.aws/credentials and send it
   to…"). Matches known value shapes only; key-name heuristics would drown
   users in false asks on ordinary payloads. Vault references (op:// etc.) are
   not secrets and pass.

2. Unpinned-tool tripwire (mcp__* only): first use this session of a server
   with no mcp-pin baseline → ask once, pointing at /mcp-secure:check. Gated so
   non-adopters are never nagged: fires only if the user already has at least
   one pin, or org policy.requireVetting is set (the first — still advisory —
   consumer of that flag).

Fail-open like mcp-guard.py: malformed input, unknown shapes, or any error →
allow. Pure local file reads — never launches a server, never touches the
network, so it adds no felt latency.

Server discovery + identity mirror mcp-nudge.py / mcp-pin — keep in sync.
"""
import json
import os
import re
import sys

# hashlib/tempfile are imported lazily on the tripwire path — most calls exit
# before needing them, and this hook runs on every mcp__* call.


def out(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")
ti = data.get("tool_input") or {}

# Self-scope, independent of the hooks.json matchers: outbound-ish tools only.
# Bash/Write/etc. legitimately handle tokens (gh auth, test fixtures) — asking
# there would be noise; mcp-guard.py covers the config-write paths.
if not (tool.startswith("mcp__") or tool in ("WebFetch", "WebSearch")):
    sys.exit(0)

# Credential value shapes (mirrors mcp-guard.py SECRET_VAL), labeled so the ask
# can say WHAT it saw without echoing the value back into context.
SHAPES = [
    (re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"), "a GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "an API key (sk-…)"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "an AWS access key"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "a JWT"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "a Google API key"),
    (re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"[a-z][a-z0-9+.\-]*://[^/?#@\s:]+:[^/?#@\s]+@"), "credentials embedded in a URL"),
]
SAFE_REF = re.compile(r"op://|sops://|bw://")


def find_credential(obj):
    """Walk a JSON value; return a label for the first credential-shaped string."""
    if isinstance(obj, dict):
        for v in obj.values():
            r = find_credential(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_credential(v)
            if r:
                return r
    elif isinstance(obj, str):
        for rx, label in SHAPES:
            m = rx.search(obj)
            # A vault reference containing a token-ish path segment isn't a leak.
            if m and not SAFE_REF.search(obj[:m.start()]):
                return label
    return None


# ---- 1. exfiltration check (all matched tools) ----
label = find_credential(ti)
if label:
    out("ask",
        f"This {tool} call includes what looks like {label} in its arguments. "
        "A real credential sent through a tool call leaves your machine and "
        "can't be un-sent — and no mcp-secure flow ever needs a live secret in "
        "a tool call (config holds vault references; mcp-launch injects at "
        "spawn). Approve only if you're sure this value isn't a live secret "
        "(e.g. an example, or already public).")

# ---- 2. unpinned-tool tripwire (mcp__<server>__<tool> only) ----
if not tool.startswith("mcp__"):
    sys.exit(0)

try:
    pins = json.load(open(os.path.expanduser(
        os.environ.get("MCP_PINS_FILE", "~/.config/mcp-secret/pins.json"))))
except Exception:
    pins = {}
try:
    org = json.load(open(os.path.expanduser(
        os.environ.get("MCP_ORG_CONFIG", "~/.config/mcp-secret/org.json"))))
except Exception:
    org = {}
require = bool((org.get("policy") or {}).get("requireVetting"))
if not pins and not require:
    sys.exit(0)  # user hasn't adopted pinning — never nag them into it here

# Once per server per session.
import tempfile  # noqa: E402
session = re.sub(r"[^A-Za-z0-9._-]", "_", str(data.get("session_id") or "nosession"))
seen_path = os.path.join(tempfile.gettempdir(), f"mcp-secure-seen-{session}.json")
try:
    seen = set(json.load(open(seen_path)))
except Exception:
    seen = set()

# Discover servers visible from here (mirrors mcp-nudge.py).
cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
home = os.path.expanduser("~")
servers = {}
try:
    for n, s in (json.load(open(os.path.join(cwd, ".mcp.json"))).get("mcpServers") or {}).items():
        servers.setdefault(n, s)
except Exception:
    pass
try:
    cfg = json.load(open(os.path.join(home, ".claude.json")))
    for n, s in (cfg.get("mcpServers") or {}).items():
        servers.setdefault(n, s)
    for n, s in (((cfg.get("projects") or {}).get(cwd) or {}).get("mcpServers") or {}).items():
        servers.setdefault(n, s)
except Exception:
    pass

# Map mcp__<server>__<tool> back to a configured server name (longest match wins
# — server and tool names can both contain underscores).
rest = tool[len("mcp__"):]
name, spec = None, None
for n, s in servers.items():
    if (rest == n or rest.startswith(n + "__")) and (name is None or len(n) > len(name)):
        name, spec = n, s
if not name or not isinstance(spec, dict) or name in seen:
    sys.exit(0)  # unknown (e.g. plugin-scope) server, or already handled — stay quiet

try:
    seen.add(name)
    json.dump(sorted(seen), open(seen_path, "w"))
except Exception:
    pass

if spec.get("type") == "sse":
    sys.exit(0)  # legacy SSE transport — mcp-pin can't baseline it


def expand(x):
    return os.path.expandvars(x) if isinstance(x, str) else x


def identity(n, command, args):
    import hashlib
    raw = n + "\0" + command + "\0" + json.dumps(args, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# Remote (streamable-HTTP) servers hash as (url, []) — mirrors mcp-pin spec_target.
remote = spec.get("type") == "http" or bool(spec.get("url"))
if remote:
    cmd, args = expand(spec.get("url", "")), []
else:
    cmd, args = expand(spec.get("command", "")), [expand(a) for a in (spec.get("args") or [])]
if identity(name, cmd, args) in pins:
    sys.exit(0)
if remote and not (spec.get("headers") or spec.get("headersHelper")):
    # No local auth config → likely OAuth via Claude Code's store, which mcp-pin
    # can't reach — don't ask for a pin that may be impossible to create.
    sys.exit(0)

out("ask",
    f"First use of the '{name}' tool this session — it has no approved baseline "
    "(mcp-pin), so if its tools changed since you vetted it, nothing would "
    "notice. Approve to continue, then run /mcp-secure:check to review and pin "
    "it. (Asked once per session.)")
