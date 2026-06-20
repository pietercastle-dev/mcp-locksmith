#!/usr/bin/env python3
"""Test suite for mcp-guard.py. Run: python test_guard.py  (exit 0 = all pass)."""
import json
import os
import subprocess
import sys

GUARD = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "mcp-guard.py")
HOME = os.path.expanduser("~")
A = "claude " + "mcp " + "add"  # avoid the literal trigger phrase in this file

CASES = [
    ("Bash: add -s user (global)",      {"tool_name": "Bash", "tool_input": {"command": f"{A} -s user foo -- bar"}}, "ask"),
    ("Bash: add -s user WITH secret",   {"tool_name": "Bash", "tool_input": {"command": f"{A} -s user foo -e TOKEN=ghp_EXAMPLEONLYnotarealtoken00 -- bar"}}, "deny"),
    ("Bash: add -s project (fine)",     {"tool_name": "Bash", "tool_input": {"command": f"{A} -s project foo -- bar"}}, "allow"),
    ("Bash: add -e literal ghp secret", {"tool_name": "Bash", "tool_input": {"command": f"{A} foo -e GITHUB_TOKEN=ghp_EXAMPLEONLYnotarealtoken00 -- bar"}}, "deny"),
    ("Bash: add -e ${VAR} (safe)",      {"tool_name": "Bash", "tool_input": {"command": f"{A} foo -e API_TOKEN=${{MY_TOKEN}} -- bar"}}, "allow"),
    ("Bash: unrelated",                 {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}, "allow"),
    (".mcp.json literal sk- secret",    {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"API_KEY":"sk-EXAMPLEONLYnotarealtoken00"}}'}}, "deny"),
    (".mcp.json op:// reference",       {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"API_KEY_REF":"op://Work/s/token"}}'}}, "allow"),
    (".mcp.json ${HOME} path val",      {"tool_name": "Write", "tool_input": {"file_path": "/x/.mcp.json", "content": '{"env":{"OAUTH_CREDENTIAL":"${HOME}/.config/x.json"}}'}}, "allow"),
    ("~/.claude.json mcpServers edit",  {"tool_name": "Edit", "tool_input": {"file_path": f"{HOME}/.claude.json", "new_string": '"mcpServers": {"s":{}}'}}, "ask"),
    ("unrelated file w/ secret-ish",    {"tool_name": "Write", "tool_input": {"file_path": "/x/foo.txt", "content": "API_KEY=sk-EXAMPLEONLYnotarealtoken00"}}, "allow"),
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
