#!/usr/bin/env python3
"""Test suite for mcp-guard.py. Run: python test_guard.py  (exit 0 = all pass)."""
import json
import os
import subprocess
import sys

GUARD = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "mcp-guard.py")
HOME = os.path.expanduser("~")
A = "claude " + "mcp " + "add"  # avoid the literal trigger phrase in this file
IMP = "claude " + "mcp " + "import"

CASES = [
    ("Bash: add -s user (global)",      {"tool_name": "Bash", "tool_input": {"command": f"{A} -s user foo -- bar"}}, "ask"),
    ("Bash: add -s user WITH secret",   {"tool_name": "Bash", "tool_input": {"command": f"{A} -s user foo -e TOKEN=ghp_EXAMPLEONLYnotarealtoken00 -- bar"}}, "deny"),
    ("Bash: add -s project (fine)",     {"tool_name": "Bash", "tool_input": {"command": f"{A} -s project foo -- bar"}}, "allow"),
    ("Bash: add -e literal ghp secret", {"tool_name": "Bash", "tool_input": {"command": f"{A} foo -e GITHUB_TOKEN=ghp_EXAMPLEONLYnotarealtoken00 -- bar"}}, "deny"),
    ("Bash: add -e ${VAR} (safe)",      {"tool_name": "Bash", "tool_input": {"command": f"{A} foo -e API_TOKEN=${{MY_TOKEN}} -- bar"}}, "allow"),
    ("Bash: unrelated",                 {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}, "allow"),
    # add-json payload: secret in the inline JSON, not an -e flag
    ("Bash: add-json literal secret",   {"tool_name": "Bash", "tool_input": {"command": f"{A}-json foo '{{\"env\":{{\"TOKEN\":\"ghp_EXAMPLEONLYnotarealtoken00\"}}}}'"}}, "deny"),
    ("Bash: add-json op:// ref (safe)", {"tool_name": "Bash", "tool_input": {"command": f"{A}-json foo '{{\"env\":{{\"TOKEN\":\"op://Work/s/token\"}}}}'"}}, "allow"),
    # shell redirect / tee into config, bypasses the Write tool entirely
    ("Bash: redirect secret to .mcp.json", {"tool_name": "Bash", "tool_input": {"command": "echo '{\"env\":{\"TOKEN\":\"ghp_EXAMPLEONLYnotarealtoken00\"}}' > .mcp.json"}}, "deny"),
    ("Bash: tee secret to ~/.claude.json", {"tool_name": "Bash", "tool_input": {"command": "echo '{\"key\":\"sk-EXAMPLEONLYnotarealtoken00\"}' | tee ~/.claude.json"}}, "deny"),
    ("Bash: redirect ref to .mcp.json (safe)", {"tool_name": "Bash", "tool_input": {"command": "echo '{\"env\":{\"TOKEN\":\"op://Work/s/token\"}}' > .mcp.json"}}, "allow"),
    ("Bash: secret to non-config file",  {"tool_name": "Bash", "tool_input": {"command": "echo ghp_EXAMPLEONLYnotarealtoken00 > notes.txt"}}, "allow"),
    (".mcp.json literal sk- secret",    {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"API_KEY":"sk-EXAMPLEONLYnotarealtoken00"}}'}}, "deny"),
    # secret as a positional CLI arg in the args array, not an env key/value
    (".mcp.json secret in args array",  {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"mcpServers":{"s":{"command":"srv","args":["--api-key","sk-EXAMPLEONLYnotarealtoken00"]}}}'}}, "deny"),
    (".mcp.json ref in args array (safe)", {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"mcpServers":{"s":{"command":"mcp-launch","args":["--arg","--api-key=op://V/s/token","--","srv"]}}}'}}, "allow"),
    (".mcp.json op:// reference",       {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"API_KEY_REF":"op://Work/s/token"}}'}}, "allow"),
    (".mcp.json ${HOME} path val",      {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"OAUTH_CREDENTIAL":"${HOME}/.config/x.json"}}'}}, "allow"),
    ("~/.claude.json mcpServers edit",  {"tool_name": "Edit", "tool_input": {"file_path": f"{HOME}/.claude.json", "new_string": '"mcpServers": {"s":{}}'}}, "ask"),
    ("unrelated file w/ secret-ish",    {"tool_name": "Write", "tool_input": {"file_path": "/x/foo.txt", "content": "API_KEY=sk-EXAMPLEONLYnotarealtoken00"}}, "allow"),
    # newly-covered credential shapes
    (".mcp.json Google AIza key",       {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"G":"AIzaSyB1234567890abcdefghijklmnopqrstuv"}}'}}, "deny"),
    (".mcp.json DB connection string",  {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"DATABASE_URL":"postgres://user:hunter2pass@db.host:5432/app"}}'}}, "deny"),
    (".mcp.json PEM private key",       {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"KEYDATA":"-----BEGIN OPENSSH PRIVATE KEY-----\\nabc"}}'}}, "deny"),
    # false-positive regressions: these must NOT be flagged
    (".mcp.json git SHA (not secret)",  {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"COMMIT":"a3f1c9e8b2d4f6a8c1e3b5d7f9a1c3e5b7d9f1a3"}}'}}, "allow"),
    (".mcp.json plain https URL",       {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"ENDPOINT":"https://api.example.com/v1"}}'}}, "allow"),
    # escaped-quote value that the flat regex would have truncated: json walk catches it
    (".mcp.json escaped-quote secret",  {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"X":"ab\\"cd ghp_EXAMPLEONLYnotarealtoken00"}}'}}, "deny"),
    # `claude mcp import` with an inline secret (process substitution)
    ("Bash: mcp import inline secret",  {"tool_name": "Bash", "tool_input": {"command": IMP + " <(printf '{\"x\":\"ghp_EXAMPLEONLYnotarealtoken00\"}')"}}, "deny"),
    # --header on http adds: opaque bearer/API-key values have no token shape,
    # so the guard anchors on the header name
    ("Bash: add --header opaque bearer", {"tool_name": "Bash", "tool_input": {"command": f"{A} --transport http foo https://x.example --header 'Authorization: Bearer notarealopaquetokenvalue00'"}}, "deny"),
    ("Bash: add -H opaque api key",      {"tool_name": "Bash", "tool_input": {"command": f"{A} --transport http foo https://x.example -H 'X-Api-Key: notarealopaquekey00'"}}, "deny"),
    ("Bash: add --header ${VAR} (safe)", {"tool_name": "Bash", "tool_input": {"command": f"{A} --transport http foo https://x.example --header 'Authorization: Bearer ${{API_TOKEN}}'"}}, "allow"),
    ("Bash: add --header non-auth (safe)", {"tool_name": "Bash", "tool_input": {"command": f"{A} --transport http foo https://x.example --header 'Content-Type: application/json'"}}, "allow"),
    # stored auth header in a Write (structural scan anchors on the header name)
    (".mcp.json headers opaque bearer", {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"mcpServers":{"s":{"type":"http","url":"https://x.example","headers":{"Authorization":"Bearer notarealopaquetokenvalue00"}}}}'}}, "deny"),
    (".mcp.json headers ${VAR} (safe)", {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"mcpServers":{"s":{"type":"http","url":"https://x.example","headers":{"Authorization":"Bearer ${API_TOKEN}"}}}}'}}, "allow"),
]


def run(payload):
    p = subprocess.run([sys.executable, GUARD], input=json.dumps(payload), capture_output=True, text=True)
    out = p.stdout.strip()
    if not out:
        return "allow"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def main():
    ok = True
    for desc, payload, expect in CASES:
        got = run(payload)
        mark = "PASS" if got == expect else "FAIL"
        if got != expect:
            ok = False
        print(f"  [{mark}] {desc:36s} expect={expect:6s} got={got}")
    print("\nALL PASS" if ok else "\nSOME FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
